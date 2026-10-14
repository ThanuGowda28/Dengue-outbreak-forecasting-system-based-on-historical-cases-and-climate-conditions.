from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import PredictionHistory, User
from ..repositories.prediction_history import delete_prediction, latest_prediction, list_predictions, save_prediction
from ..services.prediction import (
    ModelUnavailableError,
    PredictionInputError,
    PredictionServiceError,
)
from ..services.weather import rate_limited

prediction_blueprint = Blueprint("prediction", __name__)


def _user_context():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None, None, (jsonify({"message": "User not found."}), 401)
    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not load prediction user context")
        return None, None, (jsonify({"message": "Prediction request could not be authorized.", "error": "database_error"}), 500)
    if user is None:
        return None, None, (jsonify({"message": "User not found."}), 401)
    return user_id, user, None


def _serialize(record: PredictionHistory, include_owner: bool = False) -> dict:
    result = {
        "id": record.id,
        "state": record.state,
        "temperature": record.temperature,
        "humidity": record.humidity,
        "rainfall": record.rainfall,
        "wind_speed": record.wind_speed,
        "pressure": record.pressure,
        "solar_radiation": record.solar_radiation,
        "year": record.year,
        "risk_level": record.prediction,
        "prediction": record.prediction,
        "confidence": record.confidence,
        "class_probabilities": record.class_probabilities,
        "recommendations": record.recommendations,
        "prediction_time": record.prediction_time.isoformat(),
    }
    if include_owner:
        result["user_id"] = record.user_id
    return result


@prediction_blueprint.post("/prediction/predict")
@jwt_required()
@rate_limited
def predict_dengue_risk():
    user_id, _, failure = _user_context()
    if failure:
        return failure
    service = current_app.extensions.get("prediction_service")
    if service is None or not service.available:
        reason = service.load_error if service else "Prediction service was not initialized."
        return jsonify({"message": "Prediction model is unavailable.", "error": reason}), 503
    payload = request.get_json(silent=True)
    try:
        prediction = service.predict(payload)
    except PredictionInputError as error:
        return jsonify({"message": str(error), "error": "invalid_input"}), 400
    except ModelUnavailableError as error:
        return jsonify({"message": "Prediction model is unavailable.", "error": str(error)}), 503
    except PredictionServiceError as error:
        current_app.logger.exception("Prediction service failed")
        return jsonify({"message": str(error), "error": "prediction_failed"}), 500

    prediction_time = datetime.now(timezone.utc)
    prediction.update({
        "prediction_time": prediction_time.isoformat(),
        "input": {key: payload[key] for key in ("state", "temperature", "humidity", "rainfall", "wind_speed", "pressure", "solar_radiation", "year")},
    })
    database_payload = {
        **prediction["input"],
        "state": prediction["state"],
        "risk_level": prediction["risk_level"],
        "confidence": prediction["confidence"],
        "class_probabilities": prediction["class_probabilities"],
        "recommendations": prediction["recommendations"],
        "prediction_time": prediction_time,
    }
    try:
        record = save_prediction(user_id, database_payload)
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not persist prediction history")
        return jsonify({"message": "Prediction completed but could not be saved.", "error": "database_error"}), 500
    prediction["id"] = record.id
    return jsonify(prediction), 200


@prediction_blueprint.get("/prediction/history")
@jwt_required()
@rate_limited
def prediction_history():
    user_id, user, failure = _user_context()
    if failure:
        return failure
    try:
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", request.args.get("limit", "10")))
    except ValueError:
        return jsonify({"message": "page and per_page must be integers."}), 400
    if page < 1 or not 1 <= per_page <= 100:
        return jsonify({"message": "page must be >= 1 and per_page must be between 1 and 100."}), 400
    search = request.args.get("search", "").strip()[:100] or None
    risk = request.args.get("risk")
    if risk is not None:
        risk = risk.removesuffix(" Risk")
        if risk not in {"Low", "Moderate", "High"}:
            return jsonify({"message": "risk must be Low, Moderate, or High."}), 400
    try:
        admin = user.role.casefold() == "admin"
        requested_user = request.args.get("user_id")
        if requested_user and not admin:
            return jsonify({"message": "Only admins can filter history by user_id."}), 403
        query_user_id = None if admin else user_id
        if requested_user:
            try:
                query_user_id = int(requested_user)
            except ValueError:
                return jsonify({"message": "user_id must be an integer."}), 400
        pagination = list_predictions(query_user_id, page, per_page, search, risk)
        return jsonify({
            "items": [_serialize(item, include_owner=admin) for item in pagination.items],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total_items": pagination.total,
                "total_pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_previous": pagination.has_prev,
            },
        }), 200
    except SQLAlchemyError:
        current_app.logger.exception("Could not retrieve prediction history")
        return jsonify({"message": "Prediction history could not be retrieved.", "error": "database_error"}), 500


@prediction_blueprint.delete("/prediction/history/<int:prediction_id>")
@jwt_required()
@rate_limited
def delete_prediction_history(prediction_id):
    user_id, user, failure = _user_context()
    if failure:
        return failure
    try:
        deleted = delete_prediction(
            prediction_id,
            None if user.role.casefold() == "admin" else user_id,
        )
        if not deleted:
            return jsonify({"message": "Prediction history record not found."}), 404
        return jsonify({
            "message": "Prediction history record deleted.",
            "id": prediction_id,
        }), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not delete prediction history record")
        return jsonify({
            "message": "Prediction history record could not be deleted.",
            "error": "database_error",
        }), 500


@prediction_blueprint.get("/prediction/latest")
@jwt_required()
@rate_limited
def latest_prediction_result():
    user_id, user, failure = _user_context()
    if failure:
        return failure
    try:
        record = latest_prediction(None if user.role.casefold() == "admin" else user_id)
        return jsonify({"prediction": _serialize(record, include_owner=user.role.casefold() == "admin") if record else None}), 200
    except SQLAlchemyError:
        current_app.logger.exception("Could not retrieve latest prediction")
        return jsonify({"message": "Latest prediction could not be retrieved.", "error": "database_error"}), 500


@prediction_blueprint.get("/prediction/model-info")
@jwt_required()
@rate_limited
def prediction_model_info():
    service = current_app.extensions.get("prediction_service")
    if service is None:
        return jsonify({"available": False, "message": "Prediction service was not initialized."}), 200
    if not service.available:
        return jsonify({"available": False, "message": "Prediction model is unavailable.", "error": service.load_error}), 200
    return jsonify({
        "available": True,
        "model": "Ensemble Neural Network (soft voting)",
        "components": ["ANN1", "ANN2", "ANN3"],
        "classes": [str(value).removesuffix(" Risk") for value in service.label_encoder.classes_],
        "supported_states": sorted({column.removeprefix("state_ut_") for column in service.feature_columns if column.startswith("state_ut_")}),
        "feature_count": len(service.feature_columns),
        "input_temporal_resolution": "annual",
        "input_units": {
            "temperature": "annual mean °C",
            "humidity": "annual mean %",
            "rainfall": "annual total mm",
            "wind_speed": "annual mean m/s",
            "pressure": "hPa (converted to kPa for model)",
            "solar_radiation": "annual mean MJ/m²/day",
            "year": "2021-2026",
        },
        "warning": "Annual climate aggregate classifier; softmax scores are not calibrated confidence estimates. Research output only, not medical advice.",
    }), 200


@prediction_blueprint.route("/prediction", methods=["GET", "POST"])
@jwt_required()
@rate_limited
def legacy_prediction_status():
    return jsonify({
        "message": "This legacy endpoint does not create or list predictions.",
        "error": "endpoint_deprecated",
        "predict_endpoint": "/api/prediction/predict",
        "history_endpoint": "/api/prediction/history",
    }), 410
