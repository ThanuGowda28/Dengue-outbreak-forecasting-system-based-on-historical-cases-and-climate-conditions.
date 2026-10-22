import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import User
from backend.app.services.districts import ALL_DISTRICTS
from backend.app.services.weather_provider import WeatherProviderError


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-for-flask-tests-0001"
    JWT_SECRET_KEY = "test-jwt-secret-key-for-flask-tests-0001"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    WEATHER_RATE_LIMIT_PER_MINUTE = 30
    WEATHER_CACHE_TTL_SECONDS = 300
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"


class StubPredictionService:
    available = True
    load_error = None

    def __init__(self):
        self.inputs = []

    def predict(self, payload):
        self.inputs.append(payload)
        return {
            "risk_level": "Moderate",
            "confidence": 82.5,
        }


class StubWeatherProvider:
    def history(self, latitude, longitude, start_date, end_date):
        return [
            {
                "temperature_c": 28,
                "humidity_pct": 70,
                "precipitation_mm": 1.2,
                "wind_speed_mps": 2,
                "pressure_hpa": 1008,
                "solar_radiation_mj_m2_day": 18,
            }
            for _ in range(365)
        ]


class RiskMapApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        user = User(
            full_name="Risk Map Test",
            email="risk-map@example.test",
            password_hash="not-used",
            phone="1234567890",
            district="Mysuru",
            state="Karnataka",
            role="user",
        )
        db.session.add(user)
        db.session.commit()
        self.headers = {
            "Authorization": f"Bearer {create_access_token(identity=str(user.id))}"
        }
        self.client = self.app.test_client()
        self.prediction_service = StubPredictionService()
        self.app.extensions["prediction_service"] = self.prediction_service

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_risk_map_returns_climate_model_scores_for_karnataka_and_andhra_pradesh(self):
        with patch(
            "backend.app.routes.risk_map.get_weather_provider",
            return_value=StubWeatherProvider(),
        ):
            response = self.client.get("/api/risk-map", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), len(ALL_DISTRICTS))
        self.assertEqual(
            sum(item["state"] == "Karnataka" for item in response.json),
            31,
        )
        self.assertEqual(
            sum(item["state"] == "Andhra Pradesh" for item in response.json),
            28,
        )
        bengaluru = next(item for item in response.json if item["district"] == "Bengaluru Urban")
        self.assertEqual(bengaluru["risk"], "Medium")
        self.assertEqual(bengaluru["temperature"], 28)
        self.assertEqual(bengaluru["humidity"], 70)
        self.assertEqual(bengaluru["rainfall"], 438)
        self.assertEqual(bengaluru["prediction"], 82.5)
        self.assertTrue(bengaluru["recommendations"])
        self.assertEqual(bengaluru["last_updated"], response.json[0]["last_updated"])
        self.assertEqual(
            {payload["state"] for payload in self.prediction_service.inputs},
            {"Karnataka", "Andhra Pradesh"},
        )
        self.assertEqual(len(self.prediction_service.inputs), len(ALL_DISTRICTS))
        self.assertEqual(self.prediction_service.inputs[0]["solar_radiation"], 18)
        self.assertTrue(
            any(
                item["district"] == "Visakhapatnam"
                and item["state"] == "Andhra Pradesh"
                for item in response.json
            )
        )
        self.assertTrue(
            {"Markapuram", "Polavaram"}.issubset(
                {
                    item["district"]
                    for item in response.json
                    if item["state"] == "Andhra Pradesh"
                }
            )
        )

    def test_risk_map_requires_authentication(self):
        response = self.client.get("/api/risk-map")
        self.assertEqual(response.status_code, 401)

    def test_risk_map_reports_incomplete_climate_data(self):
        class IncompleteWeatherProvider:
            def history(self, latitude, longitude, start_date, end_date):
                return [{"temperature_c": 28}]

        with patch(
            "backend.app.routes.risk_map.get_weather_provider",
            return_value=IncompleteWeatherProvider(),
        ):
            response = self.client.get("/api/risk-map", headers=self.headers)

        self.assertEqual(response.status_code, 503)
        self.assertIn("300 days", response.json["message"])
        self.assertEqual(self.prediction_service.inputs, [])

    def test_risk_map_returns_service_unavailable_without_model(self):
        self.app.extensions["prediction_service"].available = False
        with patch("backend.app.routes.risk_map.get_weather_provider") as provider_factory:
            response = self.client.get("/api/risk-map", headers=self.headers)

        self.assertEqual(response.status_code, 503)
        provider_factory.assert_not_called()

    def test_risk_map_returns_weather_provider_errors(self):
        class FailedWeatherProvider:
            def history(self, latitude, longitude, start_date, end_date):
                raise WeatherProviderError("Historical weather service is unavailable.", 503)

        with patch(
            "backend.app.routes.risk_map.get_weather_provider",
            return_value=FailedWeatherProvider(),
        ):
            response = self.client.get("/api/risk-map", headers=self.headers)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"], "weather_provider_error")


if __name__ == "__main__":
    unittest.main()
