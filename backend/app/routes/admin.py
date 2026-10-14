import json
import re
import subprocess
import sys
import threading
import uuid
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from werkzeug.utils import secure_filename

from ..extensions import bcrypt, db
from ..models import (
    EmergencyContact,
    PredictionHistory,
    PrescriptionRecord,
    TokenBlocklist,
    User,
    WeatherHistory,
)

admin_blueprint = Blueprint("admin", __name__)
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_PATTERN = re.compile(r"^[0-9+().\-\s]+$")
_USER_FIELDS = {"full_name", "email", "password", "phone", "district", "state", "role"}
_USER_PATCH_FIELDS = {"full_name", "phone", "district", "state", "role"}
_training_lock = threading.Lock()


def _json_object():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else None


def _admin_user():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    user = db.session.get(User, user_id)
    return user if user and user.role.casefold() == "admin" else None


def _serialize_user(user):
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "district": user.district,
        "state": user.state,
        "role": user.role,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


def _serialize_prediction(record):
    return {
        "id": record.id,
        "user_id": record.user_id,
        "state": record.state,
        "temperature": record.temperature,
        "humidity": record.humidity,
        "rainfall": record.rainfall,
        "wind_speed": record.wind_speed,
        "pressure": record.pressure,
        "solar_radiation": record.solar_radiation,
        "year": record.year,
        "risk_level": record.prediction,
        "confidence": record.confidence,
        "class_probabilities": record.class_probabilities,
        "prediction_time": record.prediction_time.isoformat(),
    }


def _serialize_weather_record(record):
    return {
        "id": record.id,
        "user_id": record.user_id,
        "location_name": record.location_name,
        "district": record.district,
        "temperature": record.temperature,
        "humidity": record.humidity,
        "rainfall": record.rainfall,
        "pressure": record.pressure,
        "wind_speed": record.wind_speed,
        "weather_date": record.weather_date.isoformat() if record.weather_date else None,
        "record_type": record.record_type,
        "provider": record.provider,
        "observed_at": record.observed_at.isoformat(),
    }


def _admin_required():
    if _admin_user() is None:
        return jsonify({"message": "Administrator access is required."}), 403
    return None


@admin_blueprint.post("/admin/auth/login")
def admin_login():
    data = _json_object()
    if data is None or set(data) != {"email", "password"}:
        return jsonify({"message": "A JSON object with email and password is required."}), 400
    email = data.get("email")
    password = data.get("password")
    normalized_email = email.strip().lower() if isinstance(email, str) else ""
    password_valid = isinstance(password, str) and _password_fits_bcrypt(password)
    if (
        not _EMAIL_PATTERN.fullmatch(normalized_email)
        or not password_valid
    ):
        return jsonify({"message": "Invalid email or password."}), 401
    user = User.query.filter_by(email=normalized_email).first()
    if (
        user is None
        or user.role.casefold() != "admin"
        or not bcrypt.check_password_hash(user.password_hash, password)
    ):
        return jsonify({"message": "Invalid email or password."}), 401
    if not user.is_verified:
        return (
            jsonify(
                {
                    "message": "Verify your email address before signing in.",
                    "error": "email_not_verified",
                }
            ),
            403,
        )
    identity = str(user.id)
    return jsonify(
        {
            "message": "Administrator login successful.",
            "user": _serialize_user(user),
            "access_token": create_access_token(identity=identity),
            "refresh_token": create_refresh_token(identity=identity),
        }
    ), 200


@admin_blueprint.get("/admin/dashboard")
@jwt_required()
def admin_dashboard():
    denied = _admin_required()
    if denied:
        return denied
    try:
        risk_rows = (
            db.session.query(PredictionHistory.prediction, func.count(PredictionHistory.id))
            .group_by(PredictionHistory.prediction)
            .all()
        )
        recent_predictions = (
            PredictionHistory.query.order_by(
                PredictionHistory.prediction_time.desc(), PredictionHistory.id.desc()
            )
            .limit(10)
            .all()
        )
        recent_users = User.query.order_by(User.created_at.desc(), User.id.desc()).limit(5).all()
        return jsonify(
            {
                "metrics": {
                    "user_count": User.query.count(),
                    "prediction_count": PredictionHistory.query.count(),
                    "weather_record_count": WeatherHistory.query.count(),
                    "administrator_count": User.query.filter_by(role="admin").count(),
                },
                "risk_distribution": {risk: int(count) for risk, count in risk_rows},
                "recent_predictions": [_serialize_prediction(item) for item in recent_predictions],
                "recent_users": [_serialize_user(item) for item in recent_users],
            }
        ), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not load administrator dashboard")
        return jsonify({"message": "Administrator dashboard could not be loaded."}), 500


@admin_blueprint.get("/admin/users")
@jwt_required()
def list_users():
    denied = _admin_required()
    if denied:
        return denied
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
    except ValueError:
        return jsonify({"message": "page and per_page must be integers."}), 400
    if page < 1 or not 1 <= per_page <= 100:
        return jsonify({"message": "page must be >= 1 and per_page must be between 1 and 100."}), 400
    query = User.query
    search = request.args.get("search", "").strip()[:100]
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(User.full_name.ilike(pattern), User.email.ilike(pattern))
        )
    role = request.args.get("role")
    if role:
        if role not in {"user", "admin"}:
            return jsonify({"message": "role must be user or admin."}), 400
        query = query.filter_by(role=role)
    pagination = query.order_by(User.created_at.desc(), User.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify(
        {
            "users": [_serialize_user(user) for user in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_previous": pagination.has_prev,
            },
        }
    ), 200


@admin_blueprint.post("/admin/users")
@jwt_required()
def create_user():
    denied = _admin_required()
    if denied:
        return denied
    data = _json_object()
    if data is None:
        return jsonify({"message": "A JSON object is required."}), 400
    errors = {
        field: "This field is required."
        for field in _USER_FIELDS - {"role"}
        if field not in data
    }
    for field in data.keys() - _USER_FIELDS:
        errors[field] = "This field is not allowed."
    name = data.get("full_name")
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 150:
        errors["full_name"] = "Full name must contain 2 to 150 characters."
    email = data.get("email")
    normalized_email = email.strip().lower() if isinstance(email, str) else ""
    if len(normalized_email) > 254 or not _EMAIL_PATTERN.fullmatch(normalized_email):
        errors["email"] = "A valid email address is required."
    password = data.get("password")
    if not _valid_password(password):
        errors["password"] = "Password must be 8–72 UTF-8 bytes with upper, lower, number, and symbol."
    phone = data.get("phone")
    if not _valid_phone(phone):
        errors["phone"] = "Enter a valid phone number."
    for field in ("district", "state"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
            errors[field] = f"{field.title()} must contain 1 to 100 characters."
    role = data.get("role", "user")
    if role not in {"user", "admin"}:
        errors["role"] = "role must be user or admin."
    if errors:
        return jsonify({"message": "Validation failed.", "errors": errors}), 400
    user = User(
        full_name=name.strip(),
        email=normalized_email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        phone=phone.strip(),
        district=data["district"].strip(),
        state=data["state"].strip(),
        role=role,
        is_verified=False,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if User.query.filter_by(email=normalized_email).first():
            return jsonify({"message": "An account with this email already exists."}), 409
        raise
    return jsonify({"user": _serialize_user(user)}), 201


@admin_blueprint.patch("/admin/users/<int:user_id>")
@jwt_required()
def update_user(user_id):
    denied = _admin_required()
    if denied:
        return denied
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"message": "User not found."}), 404
    data = _json_object()
    if not data:
        return jsonify({"message": "A non-empty JSON object is required."}), 400
    errors = {
        field: "This field cannot be changed."
        for field in data.keys() - _USER_PATCH_FIELDS
    }
    for field, value in data.items():
        if field == "full_name" and (
            not isinstance(value, str) or not 2 <= len(value.strip()) <= 150
        ):
            errors[field] = "Full name must contain 2 to 150 characters."
        elif field == "phone" and not _valid_phone(value):
            errors[field] = "Enter a valid phone number."
        elif field in {"district", "state"} and (
            not isinstance(value, str) or not value.strip() or len(value.strip()) > 100
        ):
            errors[field] = f"{field.title()} must contain 1 to 100 characters."
        elif field == "role" and value not in {"user", "admin"}:
            errors[field] = "role must be user or admin."
    if errors:
        return jsonify({"message": "Validation failed.", "errors": errors}), 400
    if (
        user.role == "admin"
        and data.get("role") == "user"
        and User.query.filter_by(role="admin").count() <= 1
    ):
        return jsonify({"message": "The last administrator cannot be demoted."}), 409
    for field, value in data.items():
        setattr(user, field, value.strip() if isinstance(value, str) else value)
    db.session.commit()
    return jsonify({"user": _serialize_user(user)}), 200


@admin_blueprint.delete("/admin/users/<int:user_id>")
@jwt_required()
def delete_user(user_id):
    admin = _admin_user()
    if admin is None:
        return jsonify({"message": "Administrator access is required."}), 403
    if admin.id == user_id:
        return jsonify({"message": "You cannot delete your own administrator account."}), 409
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"message": "User not found."}), 404
    if user.role == "admin" and User.query.filter_by(role="admin").count() <= 1:
        return jsonify({"message": "The last administrator cannot be deleted."}), 409
    try:
        TokenBlocklist.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        PredictionHistory.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        WeatherHistory.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        EmergencyContact.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        PrescriptionRecord.query.filter_by(user_id=user.id).delete(synchronize_session=False)
        db.session.delete(user)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not delete administrator-managed user")
        return jsonify({"message": "User could not be deleted."}), 500
    return jsonify({"message": "User and associated records deleted."}), 200


@admin_blueprint.get("/admin/predictions")
@jwt_required()
def list_predictions():
    denied = _admin_required()
    if denied:
        return denied
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
    except ValueError:
        return jsonify({"message": "page and per_page must be integers."}), 400
    if page < 1 or not 1 <= per_page <= 100:
        return jsonify({"message": "page must be >= 1 and per_page must be between 1 and 100."}), 400
    query = PredictionHistory.query
    state = request.args.get("state", "").strip()[:100]
    if state:
        query = query.filter(PredictionHistory.state.ilike(f"%{state}%"))
    risk = request.args.get("risk")
    if risk:
        risk = risk.removesuffix(" Risk")
        if risk not in {"Low", "Moderate", "High"}:
            return jsonify({"message": "risk must be Low, Moderate, or High."}), 400
        query = query.filter(PredictionHistory.prediction == risk)
    pagination = query.order_by(
        PredictionHistory.prediction_time.desc(), PredictionHistory.id.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            "predictions": [_serialize_prediction(row) for row in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
            },
        }
    ), 200


@admin_blueprint.get("/admin/predictions/<int:prediction_id>")
@jwt_required()
def get_prediction(prediction_id):
    denied = _admin_required()
    if denied:
        return denied
    prediction = db.session.get(PredictionHistory, prediction_id)
    if prediction is None:
        return jsonify({"message": "Prediction not found."}), 404
    return jsonify({"prediction": _serialize_prediction(prediction)}), 200


@admin_blueprint.delete("/admin/predictions/<int:prediction_id>")
@jwt_required()
def delete_prediction(prediction_id):
    denied = _admin_required()
    if denied:
        return denied
    prediction = db.session.get(PredictionHistory, prediction_id)
    if prediction is None:
        return jsonify({"message": "Prediction not found."}), 404
    db.session.delete(prediction)
    db.session.commit()
    return jsonify({"message": "Prediction deleted."}), 200


@admin_blueprint.get("/admin/reports")
@jwt_required()
def admin_reports():
    denied = _admin_required()
    if denied:
        return denied
    start_value = request.args.get("start_date")
    end_value = request.args.get("end_date")
    try:
        start_date = date.fromisoformat(start_value) if start_value else None
        end_date = date.fromisoformat(end_value) if end_value else None
    except ValueError:
        return jsonify({"message": "Dates must use ISO format YYYY-MM-DD."}), 400
    if start_date and end_date and start_date > end_date:
        return jsonify({"message": "start_date must not be after end_date."}), 400

    prediction_query = PredictionHistory.query
    weather_query = WeatherHistory.query
    if start_date:
        start_time = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        prediction_query = prediction_query.filter(
            PredictionHistory.prediction_time >= start_time
        )
        weather_query = weather_query.filter(
            WeatherHistory.weather_date >= start_date
        )
    if end_date:
        end_time = datetime.combine(
            end_date + timedelta(days=1), time.min, tzinfo=timezone.utc
        )
        prediction_query = prediction_query.filter(
            PredictionHistory.prediction_time < end_time
        )
        weather_query = weather_query.filter(
            WeatherHistory.weather_date <= end_date
        )
    risk_rows = (
        db.session.query(PredictionHistory.prediction, func.count(PredictionHistory.id))
        .filter(PredictionHistory.id.in_(prediction_query.with_entities(PredictionHistory.id)))
        .group_by(PredictionHistory.prediction)
        .all()
    )
    weather_rows = (
        db.session.query(WeatherHistory.record_type, func.count(WeatherHistory.id))
        .filter(WeatherHistory.id.in_(weather_query.with_entities(WeatherHistory.id)))
        .group_by(WeatherHistory.record_type)
        .all()
    )
    if db.engine.dialect.name == "sqlite":
        month_expression = func.strftime("%Y-%m", PredictionHistory.prediction_time)
    else:
        month_expression = func.date_format(PredictionHistory.prediction_time, "%Y-%m")
    monthly_predictions = (
        db.session.query(month_expression, func.count(PredictionHistory.id))
        .filter(PredictionHistory.id.in_(prediction_query.with_entities(PredictionHistory.id)))
        .group_by(month_expression)
        .order_by(month_expression)
        .all()
    )
    return jsonify(
        {
            "summary": {
                "registered_users": User.query.count(),
                "predictions": prediction_query.count(),
                "weather_records": weather_query.count(),
            },
            "predictions_by_risk": {risk: int(count) for risk, count in risk_rows},
            "weather_records_by_type": {kind: int(count) for kind, count in weather_rows},
            "monthly_predictions": [
                {"month": month, "count": int(count)}
                for month, count in monthly_predictions
                if month is not None
            ],
        }
    ), 200


@admin_blueprint.get("/admin/analytics")
@jwt_required()
def admin_analytics():
    denied = _admin_required()
    if denied:
        return denied
    try:
        predictions_by_state = (
            db.session.query(
                PredictionHistory.state,
                func.count(PredictionHistory.id),
                func.avg(PredictionHistory.confidence),
            )
            .group_by(PredictionHistory.state)
            .order_by(func.count(PredictionHistory.id).desc(), PredictionHistory.state)
            .all()
        )
        predictions_by_year = (
            db.session.query(
                PredictionHistory.year,
                func.count(PredictionHistory.id),
            )
            .group_by(PredictionHistory.year)
            .order_by(PredictionHistory.year)
            .all()
        )
        users_by_role = (
            db.session.query(User.role, func.count(User.id))
            .group_by(User.role)
            .all()
        )
        weather_by_provider = (
            db.session.query(WeatherHistory.provider, func.count(WeatherHistory.id))
            .group_by(WeatherHistory.provider)
            .all()
        )
        return jsonify(
            {
                "predictions_by_state": [
                    {
                        "state": state,
                        "count": int(count),
                        "average_confidence": float(average_confidence),
                    }
                    for state, count, average_confidence in predictions_by_state
                ],
                "predictions_by_year": [
                    {"year": int(year), "count": int(count)}
                    for year, count in predictions_by_year
                ],
                "users_by_role": {role: int(count) for role, count in users_by_role},
                "weather_by_provider": {
                    provider: int(count) for provider, count in weather_by_provider
                },
            }
        ), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not load administrator analytics")
        return jsonify({"message": "Administrator analytics could not be loaded."}), 500


@admin_blueprint.get("/admin/datasets")
@jwt_required()
def list_datasets():
    denied = _admin_required()
    if denied:
        return denied
    dataset_root = Path(current_app.root_path) / "ml" / "dataset"
    try:
        files = []
        for category in ("raw", "merged", "processed", "uploads"):
            category_root = dataset_root / category
            if not category_root.is_dir():
                continue
            for path in sorted(category_root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in {".csv", ".pkl"}:
                    continue
                stat = path.stat()
                files.append(
                    {
                        "name": path.name,
                        "category": category,
                        "relative_path": path.relative_to(dataset_root).as_posix(),
                        "size_bytes": stat.st_size,
                        "updated_at": datetime.fromtimestamp(
                            stat.st_mtime, timezone.utc
                        ).isoformat(),
                    }
                )
    except OSError:
        current_app.logger.exception("Could not inspect administrator dataset files")
        return jsonify({"message": "Dataset inventory could not be loaded."}), 500
    return jsonify({"datasets": files, "total_items": len(files)}), 200


@admin_blueprint.post("/admin/datasets")
@jwt_required()
def upload_dataset():
    denied = _admin_required()
    if denied:
        return denied
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"message": "Choose a CSV file to upload."}), 400
    safe_name = secure_filename(uploaded.filename)
    if not safe_name or Path(safe_name).suffix.lower() != ".csv":
        return jsonify({"message": "Only CSV files can be uploaded."}), 400
    upload_dir = Path(current_app.root_path) / "ml" / "dataset" / "uploads"
    path = upload_dir / f"{uuid.uuid4().hex}_{safe_name}"
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
        uploaded.save(path)
        if path.stat().st_size == 0:
            path.unlink()
            return jsonify({"message": "The uploaded CSV file is empty."}), 400
        with path.open("r", encoding="utf-8-sig", newline="") as dataset_file:
            if not dataset_file.readline().strip():
                path.unlink()
                return jsonify({"message": "The uploaded CSV file has no header."}), 400
    except (OSError, UnicodeError):
        path.unlink(missing_ok=True)
        current_app.logger.exception("Could not store administrator dataset upload")
        return jsonify({"message": "Dataset upload could not be stored or validated."}), 400
    return jsonify(
        {
            "message": "CSV dataset uploaded.",
            "dataset": {
                "name": path.name,
                "category": "uploads",
                "relative_path": f"uploads/{path.name}",
                "size_bytes": path.stat().st_size,
            },
        }
    ), 201


@admin_blueprint.delete("/admin/datasets/<path:relative_path>")
@jwt_required()
def delete_uploaded_dataset(relative_path):
    denied = _admin_required()
    if denied:
        return denied
    dataset_root = (Path(current_app.root_path) / "ml" / "dataset").resolve()
    upload_root = (dataset_root / "uploads").resolve()
    target = (dataset_root / relative_path).resolve()
    if (
        target.parent != upload_root
        or target.suffix.lower() != ".csv"
        or not target.is_file()
    ):
        return jsonify({"message": "Only uploaded CSV datasets can be deleted."}), 400
    try:
        target.unlink()
    except OSError:
        current_app.logger.exception("Could not delete uploaded dataset")
        return jsonify({"message": "Uploaded dataset could not be deleted."}), 500
    return jsonify({"message": "Uploaded dataset deleted."}), 200


def _training_status(job):
    process = job["process"]
    if job["status"] == "running" and process.poll() is not None:
        job["status"] = "completed" if process.returncode == 0 else "failed"
        metrics_path = job["output_dir"] / "training_metrics.json"
        if job["status"] == "completed" and metrics_path.is_file():
            try:
                job["metrics"] = json.loads(metrics_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                current_app.logger.exception("Could not read model training metrics")
                job["status"] = "failed"
                job["error"] = "Training completed but its metrics report is invalid."
        elif job["status"] == "completed":
            job["status"] = "failed"
            job["error"] = "Training completed without producing a metrics report."
        if job["status"] == "failed":
            job["error"] = "Training process failed. Review the output log."
    try:
        log = job["log_path"].read_text(encoding="utf-8", errors="replace")
    except OSError:
        log = ""
    return {
        "id": job["id"],
        "status": job["status"],
        "started_at": job["started_at"],
        "error": job.get("error"),
        "log": log[-12000:],
        "metrics": job.get("metrics"),
        "output_is_staged": job["status"] == "completed",
    }


@admin_blueprint.post("/admin/model-training")
@jwt_required()
def start_model_training():
    denied = _admin_required()
    if denied:
        return denied
    jobs = current_app.extensions.setdefault("admin_training_jobs", {})
    with _training_lock:
        active_job = next(
            (job for job in jobs.values() if job["process"].poll() is None), None
        )
        if active_job:
            return jsonify(
                {"message": "A model training job is already running.", "job": _training_status(active_job)}
            ), 409

        app_root = Path(current_app.root_path)
        processed_dir = Path(
            current_app.config.get("ML_PROCESSED_DIR")
            or app_root / "ml" / "dataset" / "processed"
        ).resolve()
        train_path = processed_dir / "train.csv"
        test_path = processed_dir / "test.csv"
        scaler_path = processed_dir / "scaler.pkl"
        encoder_path = processed_dir / "label_encoder.pkl"
        missing = [str(path) for path in (train_path, test_path) if not path.is_file()]
        if missing:
            return jsonify(
                {"message": "Training requires processed train.csv and test.csv files.", "missing": missing}
            ), 409

        job_id = uuid.uuid4().hex
        job_dir = Path(current_app.instance_path) / "model-training" / job_id
        output_dir = job_dir / "artifacts"
        log_path = job_dir / "training.log"
        job_dir.mkdir(parents=True, exist_ok=False)
        script_path = app_root / "ml" / "training.py"
        args = [
            sys.executable,
            str(script_path),
            "--train", str(train_path),
            "--test", str(test_path),
            "--scaler", str(scaler_path),
            "--encoder", str(encoder_path),
            "--output-dir", str(output_dir),
        ]
        try:
            with log_path.open("w", encoding="utf-8") as log_file:
                process = subprocess.Popen(
                    args,
                    cwd=str(app_root.parent),
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                )
        except OSError:
            current_app.logger.exception("Could not start model training process")
            return jsonify({"message": "Model training process could not be started."}), 503
        job = {
            "id": job_id,
            "process": process,
            "output_dir": output_dir,
            "log_path": log_path,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
        }
        jobs[job_id] = job
    return jsonify({"message": "Model training started in an isolated staging directory.", "job": _training_status(job)}), 202


@admin_blueprint.get("/admin/model-training/<job_id>")
@jwt_required()
def get_model_training_status(job_id):
    denied = _admin_required()
    if denied:
        return denied
    job = current_app.extensions.get("admin_training_jobs", {}).get(job_id)
    if job is None:
        return jsonify({"message": "Training job not found in this application process."}), 404
    return jsonify({"job": _training_status(job)}), 200


@admin_blueprint.get("/admin/climate-data")
@jwt_required()
def list_climate_data():
    denied = _admin_required()
    if denied:
        return denied
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
    except ValueError:
        return jsonify({"message": "page and per_page must be integers."}), 400
    if page < 1 or not 1 <= per_page <= 100:
        return jsonify({"message": "page must be >= 1 and per_page must be between 1 and 100."}), 400

    query = WeatherHistory.query
    district = request.args.get("district", "").strip()[:100]
    provider = request.args.get("provider", "").strip()[:32]
    record_type = request.args.get("record_type", "").strip()[:16]
    start_value = request.args.get("start_date")
    end_value = request.args.get("end_date")
    try:
        start_date = date.fromisoformat(start_value) if start_value else None
        end_date = date.fromisoformat(end_value) if end_value else None
    except ValueError:
        return jsonify({"message": "Dates must use ISO format YYYY-MM-DD."}), 400
    if start_date and end_date and start_date > end_date:
        return jsonify({"message": "start_date must not be after end_date."}), 400
    if provider and provider not in {"openweather", "nasa_power"}:
        return jsonify({"message": "provider must be openweather or nasa_power."}), 400
    if record_type and record_type not in {"current", "forecast", "history"}:
        return jsonify({"message": "record_type must be current, forecast, or history."}), 400
    if district:
        query = query.filter(WeatherHistory.district.ilike(f"%{district}%"))
    if provider:
        query = query.filter(WeatherHistory.provider == provider)
    if record_type:
        query = query.filter(WeatherHistory.record_type == record_type)
    if start_date:
        query = query.filter(WeatherHistory.weather_date >= start_date)
    if end_date:
        query = query.filter(WeatherHistory.weather_date <= end_date)
    try:
        pagination = query.order_by(
            WeatherHistory.observed_at.desc(), WeatherHistory.id.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not load administrator climate data")
        return jsonify({"message": "Climate data could not be loaded."}), 500
    return jsonify(
        {
            "records": [_serialize_weather_record(row) for row in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_previous": pagination.has_prev,
            },
        }
    ), 200


@admin_blueprint.get("/admin/model-status")
@jwt_required()
def admin_model_status():
    denied = _admin_required()
    if denied:
        return denied
    app_root = Path(current_app.root_path)
    model_root = Path(
        current_app.config.get("ML_MODEL_DIR") or app_root / "ml" / "models"
    )
    required = {"ensemble_model.keras", "scaler.pkl", "label_encoder.pkl"}
    visible_artifacts = {
        *required,
        "ann1.keras",
        "ann2.keras",
        "ann3.keras",
        "training_metrics.json",
        "training_report.html",
    }
    try:
        artifacts = []
        for name in sorted(visible_artifacts):
            path = model_root / name
            exists = path.is_file()
            artifact = {"name": name, "available": exists, "required_for_inference": name in required}
            if exists:
                stat = path.stat()
                artifact["size_bytes"] = stat.st_size
                artifact["updated_at"] = datetime.fromtimestamp(
                    stat.st_mtime, timezone.utc
                ).isoformat()
            artifacts.append(artifact)
    except OSError:
        current_app.logger.exception("Could not inspect administrator model artifacts")
        return jsonify({"message": "Model status could not be loaded."}), 500
    required_present = all(
        (model_root / name).is_file() for name in required
    )
    return jsonify(
        {
            "inference_artifacts_present": required_present,
            "runtime_load_verified": bool(
                current_app.extensions.get("prediction_service")
                and current_app.extensions["prediction_service"].available
            ),
            "training_job_available": (
                (app_root / "ml" / "training.py").is_file()
                and (Path(current_app.config.get("ML_PROCESSED_DIR") or app_root / "ml" / "dataset" / "processed") / "train.csv").is_file()
                and (Path(current_app.config.get("ML_PROCESSED_DIR") or app_root / "ml" / "dataset" / "processed") / "test.csv").is_file()
            ),
            "artifacts": artifacts,
        }
    ), 200


def _valid_password(password):
    if not isinstance(password, str):
        return False
    try:
        if not 8 <= len(password.encode("utf-8")) <= 72:
            return False
    except UnicodeEncodeError:
        return False
    return (
        any(char.islower() for char in password)
        and any(char.isupper() for char in password)
        and any(char.isdigit() for char in password)
        and any(not char.isalnum() for char in password)
    )


def _password_fits_bcrypt(password):
    try:
        return isinstance(password, str) and bool(password) and len(password.encode("utf-8")) <= 72
    except UnicodeEncodeError:
        return False


def _valid_phone(value):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 32:
        return False
    digits = sum(char.isdigit() for char in value)
    return bool(_PHONE_PATTERN.fullmatch(value.strip())) and 7 <= digits <= 15
