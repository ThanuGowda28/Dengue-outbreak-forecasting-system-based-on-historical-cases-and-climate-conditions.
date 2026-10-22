from datetime import date
from io import BytesIO

from flask import Blueprint, current_app, jsonify, make_response, request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import RequestEntityTooLarge

from ..extensions import db
from ..models import MosquitoDetection, User
from ..services.alert_service import queue_mosquito_detection_alerts
from ..services.detection_model import IncompatibleDetectorError, ModelUnavailableError
from ..services.detection_service import (
    HIGH_RISK,
    InvalidDetectionImage,
    analyze_and_save,
    csv_report,
    delete_detection,
    generate_report,
    image_file,
    list_detections,
    serialize_detection,
    validate_image,
)

mosquito_detection_blueprint = Blueprint("mosquito_detection", __name__)
RISK_LEVELS = {
    HIGH_RISK,
    "Medium Risk Breeding Site",
    "Low Risk",
    "No Breeding Site Detected",
}


@mosquito_detection_blueprint.errorhandler(RequestEntityTooLarge)
def upload_too_large(_error):
    current_app.logger.info("Rejected oversized mosquito image request: %s", _error)
    return jsonify({"message": "Image exceeds the 10 MB upload limit."}), 413


def _current_user():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)


def _is_admin(user):
    return bool(user and user.role.casefold() == "admin")


def _owned_or_admin(detection_id, user):
    query = MosquitoDetection.query.filter_by(id=detection_id)
    if not _is_admin(user):
        query = query.filter_by(user_id=user.id)
    return query.first()


def _date_filter_args():
    start = request.args.get("start_date", "")
    end = request.args.get("end_date", "")
    for field, value in (("start_date", start), ("end_date", end)):
        if value:
            try:
                date.fromisoformat(value)
            except ValueError as error:
                raise ValueError(f"{field} must be a valid YYYY-MM-DD date.") from error
    return start, end


def _paged(query, default_size=20):
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", str(default_size)))
    except ValueError as error:
        raise ValueError("page and per_page must be integers.") from error
    if page < 1 or not 1 <= per_page <= 100:
        raise ValueError("page must be >= 1 and per_page must be between 1 and 100.")
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return pagination


def _image_location(form):
    district = (form.get("district") or "").strip()
    latitude = form.get("latitude")
    longitude = form.get("longitude")
    if district and len(district) > 100:
        raise ValueError("district must be 100 characters or fewer.")
    if latitude in (None, "") and longitude in (None, ""):
        return None, None, district or None
    if latitude in (None, "") or longitude in (None, ""):
        raise ValueError("latitude and longitude must be provided together.")
    try:
        latitude, longitude = float(latitude), float(longitude)
    except (TypeError, ValueError) as error:
        raise ValueError("latitude and longitude must be valid numbers.") from error
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ValueError("latitude or longitude is outside its valid range.")
    return latitude, longitude, district or None


@mosquito_detection_blueprint.post("/mosquito-detection/analyze")
@jwt_required()
def analyze_mosquito_image():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    try:
        image, extension, original = validate_image(request.files.get("image"))
        latitude, longitude, district = _image_location(request.form)
        record = analyze_and_save(
            user,
            image,
            extension,
            original,
            latitude=latitude,
            longitude=longitude,
            district=district,
        )
    except InvalidDetectionImage as error:
        return jsonify({"message": str(error)}), 400
    except ValueError as error:
        db.session.rollback()
        return jsonify({"message": str(error)}), 400
    except ModelUnavailableError as error:
        current_app.logger.warning("Mosquito detector unavailable: %s", error)
        return jsonify({
            "message": "Mosquito image analysis is unavailable until a compatible trained detector is installed.",
            "code": "model_unavailable",
        }), 503
    except IncompatibleDetectorError as error:
        current_app.logger.exception("Configured mosquito detector is incompatible")
        return jsonify({
            "message": "The configured mosquito detector is incompatible with this service.",
            "code": "model_unavailable",
        }), 503
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not save mosquito detection")
        return jsonify({"message": "The analysis could not be saved."}), 500
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Mosquito image inference failed user_id=%s", user.id)
        return jsonify({"message": "Image analysis failed. Please try again later."}), 500

    alerts = []
    alert_message = None
    if record.prediction == HIGH_RISK:
        try:
            alerts = queue_mosquito_detection_alerts(user, record)
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception(
                "Could not queue mosquito detection alerts detection_id=%s",
                record.id,
            )
            alert_message = "Analysis completed, but notifications could not be queued."
    return jsonify({
        **serialize_detection(record),
        "alerts": alerts,
        "alert_message": alert_message,
    }), 201


@mosquito_detection_blueprint.post("/mosquito-detection/<int:detection_id>/alerts")
@jwt_required()
def retry_detection_alerts(detection_id):
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    record = MosquitoDetection.query.filter_by(
        id=detection_id,
        user_id=user.id,
    ).first()
    if record is None:
        return jsonify({"message": "Detection record not found."}), 404
    try:
        alerts = queue_mosquito_detection_alerts(user, record)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Could not retry mosquito detection alerts detection_id=%s",
            detection_id,
        )
        return jsonify({"message": "Detection alerts could not be queued."}), 500
    return jsonify({"message": "Eligible alerts queued.", "alerts": alerts}), 202


@mosquito_detection_blueprint.get("/mosquito-detection/history")
@jwt_required()
def detection_history():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    try:
        start_date, end_date = _date_filter_args()
        risk = request.args.get("risk", "").strip()
        if risk and risk not in RISK_LEVELS:
            raise ValueError("risk is not a supported mosquito detection risk level.")
        query = list_detections(
            user.id,
            search=request.args.get("search", "").strip()[:100],
            risk=risk,
            start_date=start_date,
            end_date=end_date,
        )
        pagination = _paged(query)
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except SQLAlchemyError:
        current_app.logger.exception("Could not load mosquito detection history user_id=%s", user.id)
        return jsonify({"message": "Detection history could not be retrieved."}), 500
    return jsonify({
        "items": [serialize_detection(item) for item in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
        },
    }), 200


@mosquito_detection_blueprint.get("/mosquito-detection/high-risk-locations")
@jwt_required()
def high_risk_locations():
    user = _current_user()
    if user is None or not _is_admin(user):
        return jsonify({"message": "Administrator access is required."}), 403
    try:
        records = MosquitoDetection.query.filter(
            MosquitoDetection.prediction == HIGH_RISK,
            MosquitoDetection.latitude.is_not(None),
            MosquitoDetection.longitude.is_not(None),
        ).order_by(MosquitoDetection.created_at.desc()).limit(500).all()
    except SQLAlchemyError:
        current_app.logger.exception("Could not load high-risk mosquito locations")
        return jsonify({"message": "High-risk breeding-site locations could not be retrieved."}), 500
    return jsonify([
        {
            "id": item.id,
            "district": item.district,
            "latitude": item.latitude,
            "longitude": item.longitude,
            "prediction": item.prediction,
            "confidence": item.confidence,
            "objects_detected": item.objects_detected or [],
            "created_at": item.created_at.isoformat(),
        }
        for item in records
    ]), 200


@mosquito_detection_blueprint.get("/mosquito-detection/<int:detection_id>/image")
@jwt_required()
def detection_image(detection_id):
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    record = _owned_or_admin(detection_id, user)
    if record is None:
        return jsonify({"message": "Detection record not found."}), 404
    try:
        path = image_file(record, annotated=request.args.get("kind") == "annotated")
    except FileNotFoundError as error:
        return jsonify({"message": str(error)}), 404
    return send_file(path, conditional=True, max_age=0)


@mosquito_detection_blueprint.delete("/mosquito-detection/<int:detection_id>")
@jwt_required()
def remove_detection(detection_id):
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    record = _owned_or_admin(detection_id, user)
    if record is None:
        return jsonify({"message": "Detection record not found."}), 404
    try:
        delete_detection(record)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not delete mosquito detection id=%s", detection_id)
        return jsonify({"message": "Detection record could not be deleted."}), 500
    return jsonify({"message": "Detection record deleted."}), 200


@mosquito_detection_blueprint.get("/mosquito-detection/<int:detection_id>/report.pdf")
@jwt_required()
def detection_report(detection_id):
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    record = _owned_or_admin(detection_id, user)
    if record is None:
        return jsonify({"message": "Detection record not found."}), 404
    try:
        report = generate_report(record)
    except Exception:
        current_app.logger.exception("Could not generate mosquito report id=%s", detection_id)
        return jsonify({"message": "The detection report could not be generated."}), 500
    return send_file(
        BytesIO(report),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"mosquito-detection-{record.id}.pdf",
    )


@mosquito_detection_blueprint.get("/mosquito-detection/admin/reports")
@jwt_required()
def admin_detection_reports():
    user = _current_user()
    if user is None or not _is_admin(user):
        return jsonify({"message": "Administrator access is required."}), 403
    try:
        start_date, end_date = _date_filter_args()
        risk = request.args.get("risk", "").strip()
        if risk and risk not in RISK_LEVELS:
            raise ValueError("risk is not a supported mosquito detection risk level.")
        query = list_detections(
            search=request.args.get("search", "").strip()[:100],
            risk=risk,
            start_date=start_date,
            end_date=end_date,
        )
        pagination = _paged(query, default_size=50)
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except SQLAlchemyError:
        current_app.logger.exception("Could not load admin mosquito detection reports")
        return jsonify({"message": "Detection reports could not be retrieved."}), 500
    return jsonify({
        "items": [serialize_detection(item, include_user=True) for item in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
        },
    }), 200


@mosquito_detection_blueprint.get("/mosquito-detection/admin/export")
@jwt_required()
def export_detection_reports():
    user = _current_user()
    if user is None or not _is_admin(user):
        return jsonify({"message": "Administrator access is required."}), 403
    try:
        start_date, end_date = _date_filter_args()
        risk = request.args.get("risk", "").strip()
        if risk and risk not in RISK_LEVELS:
            raise ValueError("risk is not a supported mosquito detection risk level.")
        records = list_detections(
            search=request.args.get("search", "").strip()[:100],
            risk=risk,
            start_date=start_date,
            end_date=end_date,
        ).all()
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except SQLAlchemyError:
        current_app.logger.exception("Could not export mosquito detection reports")
        return jsonify({"message": "Detection reports could not be exported."}), 500
    response = make_response(csv_report(records))
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = (
        "attachment; filename=mosquito-detection-reports.csv"
    )
    return response
