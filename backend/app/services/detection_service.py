from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from flask import current_app
from PIL import Image, UnidentifiedImageError
from sqlalchemy import String, cast, or_
from werkzeug.datastructures import FileStorage

from ..extensions import db
from ..models import MosquitoDetection, User
from .detection_model import IncompatibleDetectorError

ALLOWED_FORMATS = {"JPEG": ".jpg", "PNG": ".png"}
HIGH_RISK = "High Risk Breeding Site"


class InvalidDetectionImage(ValueError):
    pass


def validate_image(upload: FileStorage) -> tuple[Image.Image, str, bytes]:
    maximum = int(current_app.config.get("MOSQUITO_MAX_IMAGE_BYTES", 10 * 1024 * 1024))
    if not upload or not upload.filename:
        raise InvalidDetectionImage("Select a JPG, JPEG, or PNG image.")
    content = upload.stream.read(maximum + 1)
    if len(content) > maximum:
        raise InvalidDetectionImage("Image exceeds the 10 MB upload limit.")
    if not content:
        raise InvalidDetectionImage("The selected image is empty.")
    try:
        image = Image.open(io.BytesIO(content))
        image_format = image.format
        if image_format not in ALLOWED_FORMATS:
            raise InvalidDetectionImage("Only JPG, JPEG, and PNG images are supported.")
        if image.width * image.height > 40_000_000:
            raise InvalidDetectionImage("Image dimensions exceed the supported limit.")
        image.verify()
        image = Image.open(io.BytesIO(content))
        image.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise InvalidDetectionImage("The image is corrupted or cannot be decoded.") from error
    if image.width * image.height > 40_000_000:
        raise InvalidDetectionImage("Image dimensions exceed the supported limit.")
    return image.convert("RGB"), ALLOWED_FORMATS[image_format], content


def upload_directory() -> Path:
    configured = current_app.config.get("MOSQUITO_UPLOAD_DIR")
    root = Path(configured) if configured else Path(current_app.instance_path) / "mosquito_detections"
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def analyze_and_save(
    user: User,
    image: Image.Image,
    extension: str,
    original: bytes,
    latitude=None,
    longitude=None,
    district=None,
):
    detector = current_app.extensions["mosquito_detection_model"]
    result = detector.analyze(image)
    if result["prediction"] not in {
        "High Risk Breeding Site",
        "Medium Risk Breeding Site",
        "Low Risk",
        "No Breeding Site Detected",
    }:
        raise IncompatibleDetectorError("The detector returned an unsupported risk class.")
    confidence = result.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise IncompatibleDetectorError("The detector returned an invalid confidence score.")
    confidence = float(confidence)
    if not 0 <= confidence <= 100:
        raise IncompatibleDetectorError("The detector confidence must be between 0 and 100.")

    directory = upload_directory()
    identifier = uuid.uuid4().hex
    image_name = f"{identifier}{extension}"
    annotated_name = None
    image_path = directory / image_name
    annotated_path = None
    try:
        image_path.write_bytes(original)
        annotation = result.get("annotated_image")
        if annotation is not None:
            annotated_name = f"{identifier}_annotated{extension}"
            annotated_path = directory / annotated_name
            from PIL import Image as PILImage

            annotated = PILImage.fromarray(annotation[:, :, ::-1].copy())
            annotated.save(annotated_path, format="JPEG" if extension == ".jpg" else "PNG")
        record = MosquitoDetection(
            user_id=user.id,
            image_path=image_name,
            annotated_image_path=annotated_name,
            prediction=result["prediction"],
            confidence=confidence,
            objects_detected=result.get("objects_detected", []),
            recommendation=result.get("recommendation", []),
            latitude=latitude,
            longitude=longitude,
            district=district,
        )
        db.session.add(record)
        db.session.commit()
        return record
    except Exception:
        db.session.rollback()
        image_path.unlink(missing_ok=True)
        if annotated_path:
            annotated_path.unlink(missing_ok=True)
        raise


def serialize_detection(record: MosquitoDetection, include_user=False) -> dict:
    item = {
        "id": record.id,
        "prediction": record.prediction,
        "risk_level": record.prediction,
        "confidence": record.confidence,
        "objects_detected": record.objects_detected or [],
        "recommendation": record.recommendation or [],
        "created_at": _iso(record.created_at),
        "has_annotation": bool(record.annotated_image_path),
        "district": record.district,
        "latitude": record.latitude,
        "longitude": record.longitude,
    }
    if include_user:
        item["user"] = {
            "id": record.user_id,
            "name": record.user.full_name if record.user else None,
            "email": record.user.email if record.user else None,
        }
    return item


def _iso(value):
    return value.isoformat() if value.tzinfo else value.isoformat() + "Z"


def list_detections(user_id=None, *, search="", risk="", start_date="", end_date=""):
    query = MosquitoDetection.query
    if user_id is not None:
        query = query.filter(MosquitoDetection.user_id == user_id)
    if risk:
        query = query.filter(MosquitoDetection.prediction == risk)
    if search:
        term = f"%{search[:100]}%"
        query = query.join(User).filter(
            or_(
                User.full_name.ilike(term),
                User.email.ilike(term),
                MosquitoDetection.district.ilike(term),
                MosquitoDetection.prediction.ilike(term),
                cast(MosquitoDetection.objects_detected, String).ilike(term),
            )
        )
    if start_date:
        start = datetime.combine(date.fromisoformat(start_date), time.min, tzinfo=timezone.utc)
        query = query.filter(MosquitoDetection.created_at >= start)
    if end_date:
        end = datetime.combine(
            date.fromisoformat(end_date) + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        query = query.filter(MosquitoDetection.created_at < end)
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")
    return query.order_by(MosquitoDetection.created_at.desc(), MosquitoDetection.id.desc())


def image_file(record: MosquitoDetection, annotated=False) -> Path:
    name = record.annotated_image_path if annotated else record.image_path
    if not name:
        raise FileNotFoundError("No annotated image is available.")
    directory = upload_directory()
    path = (directory / name).resolve()
    if path.parent != directory or not path.is_file():
        raise FileNotFoundError("The stored detection image is unavailable.")
    return path


def delete_detection(record: MosquitoDetection) -> None:
    paths = [record.image_path, record.annotated_image_path]
    directory = upload_directory()
    db.session.delete(record)
    db.session.commit()
    for name in paths:
        if name:
            path = (directory / name).resolve()
            if path.parent == directory:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    current_app.logger.exception(
                        "Could not remove mosquito detection image id=%s", record.id
                    )


def generate_report(record: MosquitoDetection) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=letter)
    page_width, page_height = letter
    y = page_height - 54
    pdf.setTitle(f"Mosquito detection report {record.id}")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(48, y, "Mosquito Breeding Site Analysis")
    y -= 30
    pdf.setFont("Helvetica", 11)
    for line in (
        f"Prediction: {record.prediction}",
        f"Confidence: {record.confidence:.2f}%",
        f"Date: {_iso(record.created_at)}",
        f"Detected objects: {', '.join(record.objects_detected or []) or 'None'}",
    ):
        pdf.drawString(48, y, line[:110])
        y -= 20
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(48, y, "Recommendations")
    y -= 18
    pdf.setFont("Helvetica", 10)
    for recommendation in record.recommendation or []:
        pdf.drawString(56, y, f"- {recommendation}"[:110])
        y -= 16

    image_y = max(48, y - 300)
    with image_file(record).open("rb") as image_stream:
        pdf.drawImage(
            ImageReader(image_stream),
            48,
            image_y,
            width=page_width - 96,
            height=min(280, max(120, image_y - 40)),
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
    pdf.showPage()
    pdf.save()
    return output.getvalue()


def csv_report(records) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["id", "user_id", "user_name", "user_email", "prediction", "confidence",
         "objects_detected", "recommendation", "district", "created_at"]
    )
    for record in records:
        values = [
            record.id,
            record.user_id,
            record.user.full_name if record.user else "",
            record.user.email if record.user else "",
            record.prediction,
            record.confidence,
            ", ".join(record.objects_detected or []),
            "; ".join(record.recommendation or []),
            record.district or "",
            _iso(record.created_at),
        ]
        writer.writerow(
            [f"'{value}" if str(value).startswith(("=", "+", "-", "@", "\t", "\r")) else value for value in values]
        )
    return output.getvalue()
