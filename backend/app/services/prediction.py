from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

from ..ml.dataset.climate_data_acquisition import STATE_UT_COORDINATES, canonical_state_name

logger = logging.getLogger(__name__)
REQUIRED_FIELDS = ("state", "temperature", "humidity", "rainfall", "wind_speed", "pressure", "solar_radiation", "year")
MIN_PREDICTION_YEAR = 2026
MAX_PREDICTION_YEAR = 2030
RECOMMENDATIONS = {
    "Low": ["Continue routine mosquito source reduction", "Avoid stagnant water", "Seek medical advice if symptoms appear"],
    "Moderate": ["Increase mosquito source reduction", "Monitor suspected cases", "Avoid stagnant water", "Seek medical advice if symptoms appear"],
    "High": ["Increase mosquito source reduction", "Monitor suspected cases", "Avoid stagnant water", "Seek medical advice if symptoms appear"],
}


class PredictionServiceError(RuntimeError):
    """Base error for model inference failures."""


class ModelUnavailableError(PredictionServiceError):
    """Raised when model artifacts could not be loaded at application startup."""


class PredictionInputError(ValueError):
    """Raised for invalid request features."""


class PredictionService:
    def __init__(self, model_dir: str | Path, processed_dir: str | Path):
        self.model_dir = Path(model_dir)
        self.processed_dir = Path(processed_dir)
        self.model = None
        self.scaler = None
        self.label_encoder = None
        self.feature_columns: list[str] = []
        self.scaler_columns: list[str] = []
        self.load_error: str | None = None
        self._load_lock = threading.Lock()
        self._load_attempted = False

    @property
    def available(self) -> bool:
        return self.model is not None and self.scaler is not None and self.label_encoder is not None

    def load_once(self) -> None:
        with self._load_lock:
            if self._load_attempted:
                return
            self._load_attempted = True
            model_path = self.model_dir / "ensemble_model.keras"
            scaler_path = self.model_dir / "scaler.pkl"
            encoder_path = self.model_dir / "label_encoder.pkl"
            metrics_path = self.model_dir / "training_metrics.json"
            try:
                missing = [str(path) for path in (model_path, scaler_path, encoder_path) if not path.is_file()]
                if missing:
                    raise FileNotFoundError("Required trained model artifacts are missing: " + ", ".join(missing))
                self.scaler = joblib.load(scaler_path)
                self.label_encoder = joblib.load(encoder_path)
                if not isinstance(self.scaler, StandardScaler):
                    raise TypeError("scaler.pkl must contain a fitted StandardScaler.")
                if not isinstance(self.label_encoder, LabelEncoder):
                    raise TypeError("label_encoder.pkl must contain a fitted LabelEncoder.")
                if not hasattr(self.label_encoder, "classes_"):
                    raise ValueError("label_encoder.pkl is not fitted.")
                metadata = {}
                if metrics_path.is_file():
                    metadata = json.loads(metrics_path.read_text(encoding="utf-8"))
                self.feature_columns = metadata.get("dataset_summary", {}).get("feature_columns", [])
                if not self.feature_columns:
                    train_csv = self.processed_dir / "train.csv"
                    if not train_csv.is_file():
                        raise FileNotFoundError("No training feature schema was saved with the model.")
                    columns = pd.read_csv(train_csv, nrows=0).columns.tolist()
                    target_column = metadata.get("dataset_summary", {}).get("target_column", "outbreak_risk")
                    self.feature_columns = [column for column in columns if column != target_column]
                if not self.feature_columns:
                    raise ValueError("The trained model feature schema is empty.")
                if hasattr(self.scaler, "feature_names_in_"):
                    self.scaler_columns = list(self.scaler.feature_names_in_)
                else:
                    self.scaler_columns = [column for column in self.feature_columns if column != "year"]
                if len(self.scaler_columns) != int(self.scaler.n_features_in_):
                    raise ValueError("Scaler input dimension does not match its feature schema.")
                absent = set(self.scaler_columns) - set(self.feature_columns)
                if absent:
                    raise ValueError(f"Scaler features missing from model schema: {sorted(absent)}")
                from tensorflow import keras

                self.model = keras.models.load_model(model_path, compile=False)
                model_features = int(self.model.input_shape[-1])
                model_classes = int(self.model.output_shape[-1])
                if model_features != len(self.feature_columns):
                    raise ValueError(f"Model expects {model_features} features, metadata has {len(self.feature_columns)}.")
                if model_classes != len(self.label_encoder.classes_):
                    raise ValueError("Model output classes do not match label_encoder.pkl.")
            except Exception as error:
                self.model = None
                self.load_error = str(error)
                logger.exception("Could not load dengue ensemble artifacts")

    def require_available(self) -> None:
        if not self.available:
            raise ModelUnavailableError(self.load_error or "Prediction model is unavailable.")

    def validate_and_build_features(self, payload: Any) -> tuple[dict[str, Any], pd.DataFrame]:
        if not isinstance(payload, dict):
            raise PredictionInputError("A JSON object is required.")
        missing = [field for field in REQUIRED_FIELDS if field not in payload]
        if missing:
            raise PredictionInputError("Required fields are missing: " + ", ".join(missing))

        if not isinstance(payload["state"], str):
            raise PredictionInputError("state must be a recognized Indian State/UT name.")
        unexpected = set(payload) - set(REQUIRED_FIELDS)
        if unexpected:
            raise PredictionInputError("Unsupported input fields: " + ", ".join(sorted(unexpected)))
        state = canonical_state_name(payload["state"])
        if not state or state not in STATE_UT_COORDINATES:
            raise PredictionInputError("state must be a recognized Indian State/UT.")
        values: dict[str, Any] = {"state": state}
        bounds = {
            "temperature": (-90, 65),
            "humidity": (0, 100),
            "rainfall": (0, 20000),
            "wind_speed": (0, 100),
            "pressure": (300, 1200),
            "solar_radiation": (0, 60),
            "year": (MIN_PREDICTION_YEAR, MAX_PREDICTION_YEAR),
        }
        for name, (minimum, maximum) in bounds.items():
            value = payload[name]
            if isinstance(value, bool):
                raise PredictionInputError(f"{name} must be a number between {minimum} and {maximum}.")
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise PredictionInputError(f"{name} must be a number between {minimum} and {maximum}.")
            if not np.isfinite(number) or not minimum <= number <= maximum:
                raise PredictionInputError(f"{name} must be a number between {minimum} and {maximum}.")
            if name == "year" and not number.is_integer():
                raise PredictionInputError(
                    f"year must be an integer between {MIN_PREDICTION_YEAR} and {MAX_PREDICTION_YEAR}."
                )
            values[name] = int(number) if name == "year" else number

        # The model uses annual climate aggregates. API pressure is received in hPa;
        # NASA POWER training pressure is kPa. Rainfall must be an annual total in mm.
        model_values: dict[str, float] = {
            "year": float(values["year"]),
            "average_temperature_c": float(values["temperature"]),
            "average_relative_humidity_pct": float(values["humidity"]),
            "total_rainfall_mm": float(values["rainfall"]),
            "average_wind_speed_m_s": float(values["wind_speed"]),
            "average_surface_pressure_kpa": float(values["pressure"]) / 10.0,
            "average_solar_radiation_mj_m2_day": float(values["solar_radiation"]),
            "temperature_humidity_interaction": float(values["temperature"]) * float(values["humidity"]),
        }
        for column in self.feature_columns:
            model_values.setdefault(column, 0.0)
        state_column = f"state_ut_{state}"
        if state_column not in self.feature_columns:
            raise PredictionInputError(f"The trained model does not support State/UT '{state}'.")
        model_values[state_column] = 1.0
        one_hot_values = {
            "season_Annual": 1.0,
            f"rainfall_category_{self._rainfall_category(values['rainfall'])}": 1.0,
            f"humidity_category_{self._humidity_category(values['humidity'])}": 1.0,
            f"temperature_category_{self._temperature_category(values['temperature'])}": 1.0,
        }
        for column, value in one_hot_values.items():
            if column in model_values:
                model_values[column] = value
        raw_frame = pd.DataFrame([[model_values[column] for column in self.feature_columns]], columns=self.feature_columns)
        to_scale = raw_frame.loc[:, self.scaler_columns]
        scaled = self.scaler.transform(to_scale)
        for index, column in enumerate(self.scaler_columns):
            raw_frame.loc[:, column] = scaled[:, index]
        return values, raw_frame

    @staticmethod
    def _rainfall_category(value: float) -> str:
        return "Low" if value < 500 else "Moderate" if value < 1500 else "High"

    @staticmethod
    def _humidity_category(value: float) -> str:
        return "Low" if value < 40 else "Moderate" if value < 70 else "High"

    @staticmethod
    def _temperature_category(value: float) -> str:
        return "Cool" if value < 20 else "Moderate" if value < 30 else "Hot"

    def predict(self, payload: Any) -> dict[str, Any]:
        self.require_available()
        values, feature_frame = self.validate_and_build_features(payload)
        try:
            probabilities = np.asarray(self.model.predict(feature_frame.to_numpy(dtype=np.float32), verbose=0))[0]
        except Exception as error:
            logger.exception("Dengue ensemble inference failed")
            raise PredictionServiceError("The prediction model failed to process this request.") from error
        if probabilities.ndim != 1 or len(probabilities) != len(self.label_encoder.classes_) or not np.isfinite(probabilities).all():
            raise PredictionServiceError("The prediction model returned invalid probabilities.")
        probabilities = np.clip(probabilities, 0.0, 1.0)
        total = float(probabilities.sum())
        if total <= 0:
            raise PredictionServiceError("The prediction model returned an empty probability distribution.")
        probabilities /= total
        index = int(np.argmax(probabilities))
        encoded_class = str(self.label_encoder.classes_[index])
        risk_level = encoded_class.removesuffix(" Risk")
        return {
            "state": values["state"],
            "risk_level": risk_level,
            "confidence": round(float(probabilities[index] * 100), 2),
            "class_probabilities": {
                str(label).removesuffix(" Risk"): round(float(probability), 6)
                for label, probability in zip(self.label_encoder.classes_, probabilities)
            },
            "recommendations": RECOMMENDATIONS.get(risk_level, RECOMMENDATIONS["Moderate"]),
            "model_warning": "The top-class softmax probability is not calibrated confidence. Model features are annual climate aggregates; rainfall must be annual total (mm), and other climate values should be annual averages. Predictions are research outputs, not medical advice.",
        }


def initialize_prediction_service(app) -> PredictionService:
    model_dir = Path(app.config.get("ML_MODEL_DIR") or Path(__file__).resolve().parents[1] / "ml" / "models")
    processed_dir = Path(app.config.get("ML_PROCESSED_DIR") or model_dir.parent / "dataset" / "processed")
    service = PredictionService(model_dir, processed_dir)
    service.load_once()
    app.extensions["prediction_service"] = service
    if not service.available:
        app.logger.error("Dengue prediction service unavailable at startup: %s", service.load_error)
    else:
        app.logger.info("Dengue ensemble loaded once from %s", model_dir)
    return service
