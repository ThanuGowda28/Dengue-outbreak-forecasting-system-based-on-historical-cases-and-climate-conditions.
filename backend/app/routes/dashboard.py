from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import db
from ..models import User, UserPreference
from ..repositories.prediction_history import latest_prediction, prediction_count, risk_distribution, list_predictions
from ..repositories.weather_history import (
    latest_weather_result,
    list_weather_results,
    weather_result_count,
)
from ..services.weather import rate_limited

dashboard_blueprint = Blueprint("dashboard", __name__)


@dashboard_blueprint.get("/dashboard")
@jwt_required()
@rate_limited
def dashboard_summary():
    user_id = get_jwt_identity()
    recent = list_weather_results(user_id, limit=5)
    current_record = latest_weather_result(user_id, "current")
    db_user = None
    try:
        db_user = db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        pass
    if current_record:
        stored = current_record.payload
        location = stored.get("location") or {
            "district": None,
            "city": current_record.location_name,
            "state": None,
            "latitude": current_record.latitude,
            "longitude": current_record.longitude,
        }
        current = _standard_current(stored.get("current", stored))
        source = current_record.provider
        cached = True
    else:
        location = {
            "district": db_user.district if db_user else None,
            "city": None,
            "state": db_user.state if db_user else None,
            "latitude": None,
            "longitude": None,
        }
        current = {
            "weather_date": None,
            "temperature": None,
            "humidity": None,
            "rainfall": None,
            "pressure": None,
            "wind_speed": None,
            "cloud_cover": None,
            "sunrise": None,
            "sunset": None,
            "uv_index": None,
            "description": None,
            "icon": None,
        }
        source = None
        cached = False
    is_admin = bool(db_user and db_user.role.casefold() == "admin")
    prediction_user_id = None if is_admin else int(user_id)
    prediction_records = list_predictions(prediction_user_id, page=1, per_page=5).items
    latest = latest_prediction(prediction_user_id)
    now_utc = datetime.now(timezone.utc)
    latest_time = latest.prediction_time if latest else None
    if latest_time and latest_time.tzinfo is None:
        latest_time = latest_time.replace(tzinfo=timezone.utc)
    today_risk = latest.prediction if latest_time and latest_time.date() == now_utc.date() else None
    latest_payload = _serialize_prediction(latest, include_owner=is_admin) if latest else None
    preferences = db.session.get(UserPreference, db_user.id) if db_user else None
    alerts_enabled = preferences.alerts if preferences else True
    alerts = _build_dashboard_alerts(latest, today_risk) if alerts_enabled else []
    return (
        jsonify(
            {
                "weather_record_count": weather_result_count(user_id),
                "recent_weather": [_serialize(item) for item in recent],
                "weather": {
                    "location": _location_shape(location),
                    "current": current,
                    "source": source,
                    "cached": cached,
                },
                "recent_predictions": [_serialize_prediction(item, include_owner=is_admin) for item in prediction_records],
                "latest_prediction": latest_payload,
                "prediction_count": prediction_count(prediction_user_id),
                "risk_distribution": {
                    (f"{risk} Risk" if risk in {"Low", "Moderate", "High"} else risk): count
                    for risk, count in risk_distribution(prediction_user_id).items()
                },
                "today_risk": today_risk,
                "alerts": alerts,
                "risk_summary": {
                    "available": latest is not None,
                    "status": latest.prediction if latest else "unavailable",
                    "risk_level": today_risk,
                    "score": latest.confidence if latest else None,
                    "message": "Latest model result is shown for context only; this is not medical advice." if latest else "No saved model prediction is available.",
                },
            }
        ),
        200,
    )


def _build_dashboard_alerts(latest, today_risk):
    if latest is None or today_risk not in {"Moderate", "High"}:
        return []
    severity = "high" if today_risk == "High" else "medium"
    return [
        {
            "id": f"prediction-{latest.id}",
            "type": "model_assessment",
            "severity": severity,
            "title": f"{today_risk} model assessment",
            "message": (
                f"A saved dengue-risk model assessment for {latest.state} is "
                f"{today_risk}. This research output is not a verified outbreak "
                "alert or medical advice."
            ),
            "created_at": latest.prediction_time.isoformat(),
            "source": "prediction_model",
        }
    ]


def _serialize_prediction(record, include_owner=False):
    result = {
        "id": record.id,
        "state": record.state,
        "district": record.state,
        "risk": record.prediction,
        "risk_level": record.prediction,
        "confidence": f"{record.confidence:.2f}%",
        "confidence_value": record.confidence,
        "date": record.prediction_time.isoformat(),
        "prediction_time": record.prediction_time.isoformat(),
        "class_probabilities": record.class_probabilities,
    }
    if include_owner:
        result["user_id"] = record.user_id
    return result


def _serialize(record):
    payload = record.payload
    raw_location = payload.get("location", {}) if isinstance(payload, dict) else {}
    return {
        "id": record.id,
        "location": _location_shape(
            {
                "district": raw_location.get("district"),
                "city": raw_location.get("city"),
                "state": raw_location.get("state"),
                "latitude": record.latitude,
                "longitude": record.longitude,
            }
        ),
        "record_type": record.record_type,
        "source": record.provider,
        "observed_at": record.observed_at.isoformat(),
        "created_at": record.created_at.isoformat(),
        "weather": payload,
    }


def _location_shape(location):
    return {
        "district": location.get("district"),
        "city": location.get("city"),
        "state": location.get("state"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
    }


def _standard_current(item):
    observed_at = item.get("weather_date", item.get("observed_at"))
    if observed_at:
        try:
            weather_date = observed_at.replace("Z", "+00:00")
            weather_date = datetime.fromisoformat(weather_date).date().isoformat()
        except (TypeError, ValueError):
            weather_date = str(observed_at)[:10]
    else:
        weather_date = None
    return {
        "weather_date": weather_date,
        "temperature": item.get("temperature", item.get("temperature_c")),
        "humidity": item.get("humidity", item.get("humidity_pct")),
        "rainfall": item.get("rainfall", item.get("precipitation_mm")),
        "pressure": item.get("pressure", item.get("pressure_hpa")),
        "wind_speed": item.get("wind_speed", item.get("wind_speed_mps")),
        "cloud_cover": item.get("cloud_cover"),
        "sunrise": item.get("sunrise"),
        "sunset": item.get("sunset"),
        "uv_index": item.get("uv_index"),
        "description": item.get("description", item.get("condition")),
        "icon": item.get("icon"),
    }
