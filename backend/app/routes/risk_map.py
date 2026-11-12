from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import jwt_required

from ..services.districts import ALL_DISTRICTS
from ..services.prediction import (
    ModelUnavailableError,
    PredictionInputError,
    PredictionServiceError,
)
from ..services.weather import (
    get_weather_provider,
    provider_call,
    provider_error_response,
    rate_limited,
)
from ..services.weather_provider import WeatherProviderError

risk_map_blueprint = Blueprint("risk_map", __name__)

MINIMUM_CLIMATE_DAYS = 300
MINIMUM_RAINFALL_DAYS = 250
MAX_DAILY_RAINFALL_MM = 250

CLIMATE_FIELDS = {
    "temperature": "temperature_c",
    "humidity": "humidity_pct",
    "rainfall": "precipitation_mm",
    "wind_speed": "wind_speed_mps",
    "pressure": "pressure_hpa",
    "solar_radiation": "solar_radiation_mj_m2_day",
}
RISK_LEVELS = {
    "low": "Low",
    "moderate": "Medium",
    "medium": "Medium",
    "high": "High",
    "very high": "Very High",
}
RECOMMENDATIONS = {
    "Low": ["Continue routine mosquito source reduction.", "Seek medical advice if symptoms appear."],
    "Medium": ["Remove stagnant water regularly.", "Use mosquito repellents and seek medical advice if symptoms appear."],
    "High": ["Remove stagnant water immediately.", "Use mosquito repellents.", "Visit a nearby hospital if symptoms appear."],
    "Very High": ["Remove stagnant water immediately and alert local health workers.", "Use mosquito repellents.", "Visit a nearby hospital if symptoms appear."],
}


def _rolling_climate(provider, district, start_date, end_date, app):
    cache_key = (
        "risk-map-climate",
        district["latitude"],
        district["longitude"],
        start_date.isoformat(),
        end_date.isoformat(),
    )
    with app.app_context():
        return provider_call(
            cache_key,
            lambda: provider.history(
                district["latitude"],
                district["longitude"],
                start_date,
                end_date,
            ),
        )


def _aggregate_climate(observations):
    if len(observations) < MINIMUM_CLIMATE_DAYS:
        raise WeatherProviderError(
            "At least 300 days of historical climate data are required to calculate a district risk score.",
            503,
        )

    aggregates = {}
    for field, observation_key in CLIMATE_FIELDS.items():
        values = [
            float(value)
            for item in observations
            if isinstance(item, dict)
            and isinstance((value := item.get(observation_key)), (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        ]
        minimum_days = MINIMUM_CLIMATE_DAYS
        if field == "rainfall":
            # Exclude daily spikes beyond the range observed in the model's training climate data.
            values = [value for value in values if value <= MAX_DAILY_RAINFALL_MM]
            minimum_days = MINIMUM_RAINFALL_DAYS
        if len(values) < minimum_days:
            raise WeatherProviderError(
                f"At least {minimum_days} valid {field} observations are required to calculate a district risk score.",
                503,
            )
        aggregates[field] = sum(values) if field == "rainfall" else sum(values) / len(values)
    return aggregates


def _map_risk_level(value):
    label = str(value).strip().removesuffix(" Risk").casefold()
    risk = RISK_LEVELS.get(label)
    if risk is None:
        raise PredictionServiceError(
            f"The prediction model returned an unsupported risk level: {value!r}."
        )
    return risk


@risk_map_blueprint.get("/risk-map")
@jwt_required()
@rate_limited
def get_risk_map():
    app = current_app._get_current_object()
    service = current_app.extensions.get("prediction_service")
    if service is None or not service.available:
        reason = service.load_error if service else "Prediction service was not initialized."
        return jsonify({"message": "Prediction model is unavailable.", "error": reason}), 503

    provider = get_weather_provider()
    # The ensemble expects annual aggregates, so avoid passing a single-day snapshot.
    climate_end = datetime.now(timezone.utc).date() - timedelta(days=4)
    climate_start = climate_end - timedelta(days=364)
    generated_at = datetime.now(timezone.utc).isoformat()
    results = {}
    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(
                    _rolling_climate,
                    provider,
                    district,
                    climate_start,
                    climate_end,
                    app,
                ): district
                for district in ALL_DISTRICTS
            }
            for future, district in futures.items():
                observations = future.result()
                climate = _aggregate_climate(observations)
                prediction = service.predict(
                    {
                        "state": district["state"],
                        **climate,
                        "year": climate_end.year,
                    }
                )
                risk = _map_risk_level(prediction.get("risk_level"))
                score = prediction.get("confidence")
                if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
                    raise PredictionServiceError(
                        "The prediction model returned an invalid risk score."
                    )
                results[(district["state"], district["district"])] = {
                    "district": district["district"],
                    "state": district["state"],
                    "latitude": district["latitude"],
                    "longitude": district["longitude"],
                    "last_updated": generated_at,
                    "risk": risk,
                    "temperature": round(climate["temperature"], 1),
                    "humidity": round(climate["humidity"], 1),
                    "rainfall": round(climate["rainfall"], 1),
                    "prediction": round(float(score), 2),
                    "recommendations": RECOMMENDATIONS[risk],
                }
    except WeatherProviderError as error:
        current_app.logger.warning("Could not calculate complete district risk map: %s", error)
        return provider_error_response(error)
    except PredictionInputError as error:
        current_app.logger.exception("Risk map climate data was rejected by the prediction model")
        return jsonify({"message": str(error), "error": "invalid_prediction_input"}), 503
    except ModelUnavailableError as error:
        return jsonify({"message": "Prediction model is unavailable.", "error": str(error)}), 503
    except PredictionServiceError as error:
        current_app.logger.exception("Could not calculate district risk")
        return jsonify({"message": str(error), "error": "prediction_failed"}), 500

    return jsonify(
        [results[(district["state"], district["district"])] for district in ALL_DISTRICTS]
    ), 200
