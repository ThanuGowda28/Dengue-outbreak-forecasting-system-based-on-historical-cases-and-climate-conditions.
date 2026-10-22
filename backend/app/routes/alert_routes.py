from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timedelta, timezone

from flask import Blueprint, current_app, jsonify, make_response, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import AlertHistory, AlertPreference, PredictionHistory, User
from ..services.alert_service import queue_prediction_alerts, serialize_alert
from ..services.weather import rate_limited

alert_blueprint = Blueprint("alerts", __name__)
ALERT_SETTING_FIELDS = {
    "email_alerts",
    "sms_alerts",
    "daily_notifications",
    "high_risk_notifications",
    "weather_alerts",
}
DEFAULT_ALERT_SETTINGS = {
    "email_alerts": True,
    "sms_alerts": False,
    "daily_notifications": False,
    "high_risk_notifications": True,
    "weather_alerts": True,
}
ALERT_TYPES = {"email", "sms", "in_app"}
ALERT_STATUSES = {"queued", "sending", "retrying", "sent", "failed"}


def _current_user():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)


def _serialize_settings(settings):
    if settings is None:
        return dict(DEFAULT_ALERT_SETTINGS)
    return {field: getattr(settings, field) for field in ALERT_SETTING_FIELDS}


def _base_query(user_id=None):
    query = AlertHistory.query
    if user_id is not None:
        query = query.filter(AlertHistory.user_id == user_id)
    return query


def _parse_date(value, field):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{field} must be a valid YYYY-MM-DD date.")


def _filter_alerts(query):
    alert_type = request.args.get("type")
    status = request.args.get("status")
    search = request.args.get("search", "").strip()[:100]
    if alert_type:
        if alert_type.casefold() not in ALERT_TYPES:
            raise ValueError("type must be email or sms.")
        query = query.filter(AlertHistory.alert_type == alert_type.casefold())
    if status:
        if status.casefold() not in ALERT_STATUSES:
            raise ValueError("status must be queued, sending, retrying, sent, or failed.")
        query = query.filter(AlertHistory.status == status.casefold())

    try:
        start_date = _parse_date(request.args.get("start_date"), "start_date")
        end_date = _parse_date(request.args.get("end_date"), "end_date")
    except ValueError as error:
        raise error
    if start_date:
        start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        query = query.filter(AlertHistory.created_at >= start)
    if end_date:
        end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
        query = query.filter(AlertHistory.created_at < end)
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must be on or before end_date.")
    if search:
        query = query.join(User).filter(
            or_(
                AlertHistory.recipient.ilike(f"%{search}%"),
                AlertHistory.message.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
        )
    return query.order_by(AlertHistory.created_at.desc(), AlertHistory.id.desc())


@alert_blueprint.get("/alerts/settings")
@jwt_required()
def get_alert_settings():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    settings = db.session.get(AlertPreference, user.id)
    return jsonify({"preferences": _serialize_settings(settings)}), 200


@alert_blueprint.put("/alerts/settings")
@jwt_required()
def update_alert_settings():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "A JSON object is required."}), 400
    errors = {}
    for field in ALERT_SETTING_FIELDS - data.keys():
        errors[field] = "This preference is required."
    for field in data.keys() - ALERT_SETTING_FIELDS:
        errors[field] = "This preference is not allowed."
    for field in data.keys() & ALERT_SETTING_FIELDS:
        if not isinstance(data[field], bool):
            errors[field] = "This preference must be a boolean."
    if errors:
        return jsonify({"message": "Validation failed.", "errors": errors}), 400

    settings = db.session.get(AlertPreference, user.id)
    if settings is None:
        settings = AlertPreference(user_id=user.id)
        db.session.add(settings)
    for field in ALERT_SETTING_FIELDS:
        setattr(settings, field, data[field])
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not save alert settings user_id=%s", user.id)
        return jsonify({"message": "Alert preferences could not be saved."}), 500
    return jsonify({"message": "Alert preferences saved.", "preferences": _serialize_settings(settings)}), 200


@alert_blueprint.post("/alerts/send")
@jwt_required()
@rate_limited
def send_prediction_alerts():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"prediction_id"}:
        return jsonify({"message": "A JSON object with prediction_id is required."}), 400
    prediction_id = data.get("prediction_id")
    if isinstance(prediction_id, bool) or not isinstance(prediction_id, int) or prediction_id < 1:
        return jsonify({"message": "prediction_id must be a positive integer."}), 400
    prediction = PredictionHistory.query.filter_by(
        id=prediction_id,
        user_id=user.id,
    ).first()
    if prediction is None:
        return jsonify({"message": "Prediction not found."}), 404
    try:
        alerts = queue_prediction_alerts(user, prediction)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Could not queue alerts user_id=%s prediction_id=%s",
            user.id,
            prediction.id,
        )
        return jsonify({"message": "Alerts could not be queued."}), 500
    return jsonify({
        "message": "Eligible alerts queued." if alerts else "No alert is eligible for this prediction and your saved preferences.",
        "alerts": alerts,
    }), 202


@alert_blueprint.get("/alerts/history")
@jwt_required()
@rate_limited
def alert_history():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "20"))
        if page < 1 or not 1 <= per_page <= 100:
            raise ValueError("page must be >= 1 and per_page must be between 1 and 100.")
        query = _filter_alerts(_base_query(user.id))
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    try:
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    except SQLAlchemyError:
        current_app.logger.exception("Could not retrieve alert history user_id=%s", user.id)
        return jsonify({"message": "Alert history could not be retrieved."}), 500
    return jsonify({
        "items": [serialize_alert(alert) for alert in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
        },
    }), 200


def _admin_user():
    user = _current_user()
    return user if user and user.role.casefold() == "admin" else None


@alert_blueprint.get("/alerts/admin/history")
@jwt_required()
@rate_limited
def admin_alert_history():
    admin = _admin_user()
    if admin is None:
        return jsonify({"message": "Administrator access is required."}), 403
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "50"))
        if page < 1 or not 1 <= per_page <= 100:
            raise ValueError("page must be >= 1 and per_page must be between 1 and 100.")
        query = _filter_alerts(_base_query())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except SQLAlchemyError:
        current_app.logger.exception("Could not retrieve admin alert history")
        return jsonify({"message": "Alert history could not be retrieved."}), 500
    return jsonify({
        "items": [serialize_alert(alert, include_owner=True) for alert in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
        },
    }), 200


@alert_blueprint.get("/alerts/admin/export")
@jwt_required()
@rate_limited
def export_alert_history():
    if _admin_user() is None:
        return jsonify({"message": "Administrator access is required."}), 403
    try:
        alerts = _filter_alerts(_base_query()).all()
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except SQLAlchemyError:
        current_app.logger.exception("Could not export admin alert history")
        return jsonify({"message": "Alert history could not be exported."}), 500

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "user_id", "user_name", "user_email", "prediction_id",
        "alert_type", "status", "recipient", "message", "failure_reason",
        "attempts", "created_at", "sent_at",
    ])
    for alert in alerts:
        row = [
            alert.id,
            alert.user_id,
            alert.user.full_name if alert.user else "",
            alert.user.email if alert.user else "",
            alert.prediction_id or "",
            alert.alert_type,
            alert.status,
            alert.recipient,
            alert.message,
            alert.failure_reason or "",
            alert.attempts,
            alert.created_at.isoformat(),
            alert.sent_at.isoformat() if alert.sent_at else "",
        ]
        writer.writerow([_csv_safe(value) for value in row])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=dengue-alert-history.csv"
    return response


def _csv_safe(value):
    text = str(value)
    return f"'{text}" if text.startswith(("=", "+", "-", "@", "\t", "\r")) else text
