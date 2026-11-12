import unittest

from flask_jwt_extended import create_access_token

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import ForecastHistory, User
from backend.app.services.forecasting import ForecastingService


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-for-flask-tests-0001"
    JWT_SECRET_KEY = "test-jwt-secret-key-for-flask-tests-0001"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"


class ForecastingApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(
            full_name="Forecast Test",
            email="forecast@example.test",
            password_hash="unused",
            phone="1234567890",
            district="Mysuru",
            state="Karnataka",
            role="user",
            is_verified=True,
        )
        db.session.add(self.user)
        db.session.commit()
        self.headers = {
            "Authorization": f"Bearer {create_access_token(identity=str(self.user.id))}"
        }
        self.client = self.app.test_client()
        self.service = ForecastingService()
        self.app.extensions["forecasting_service"] = self.service

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_forecast_options_and_trends_are_authenticated(self):
        options = self.client.get("/api/forecast/options", headers=self.headers)
        self.assertEqual(options.status_code, 200)
        self.assertIn("Karnataka", options.json["states"])
        self.assertIn("Andhra Pradesh", options.json["states"])
        self.assertEqual(options.json["forecast_years"], [2026, 2027, 2028, 2029, 2030])

        trends = self.client.get(
            "/api/forecast/trends?state=Karnataka&years=10",
            headers=self.headers,
        )
        self.assertEqual(trends.status_code, 200)
        self.assertGreaterEqual(trends.json["years_available"], 3)
        self.assertTrue(
            {"temperature", "humidity", "rainfall", "wind_speed", "solar_radiation"}
            .issubset(trends.json["history"][0])
        )
        self.assertEqual(
            self.client.get("/api/forecast/options").status_code,
            401,
        )

    def test_forecast_is_persisted_in_isolated_history_and_pdf_can_be_downloaded(self):
        response = self.client.post(
            "/api/forecast",
            headers=self.headers,
            json={
                "state": "Karnataka",
                "district": "Mysuru",
                "forecast_year": 2027,
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn(response.json["risk"], {"Low", "Moderate", "High", "Very High"})
        self.assertEqual(response.json["district"], "Mysuru")
        self.assertTrue(response.json["timeline"])
        self.assertTrue(response.json["recommendations"])
        self.assertEqual(ForecastHistory.query.count(), 1)

        history = self.client.get("/api/forecast/history", headers=self.headers)
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json["items"]), 1)
        self.assertEqual(history.json["pagination"]["page"], 1)
        self.assertEqual(history.json["pagination"]["total_items"], 1)
        invalid_history = self.client.get(
            "/api/forecast/history?page=0", headers=self.headers
        )
        self.assertEqual(invalid_history.status_code, 400)

        report = self.client.get(
            f"/api/forecast/history/{response.json['id']}/report.pdf",
            headers=self.headers,
        )
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.mimetype, "application/pdf")
        self.assertTrue(report.data.startswith(b"%PDF"))

    def test_forecasts_can_be_generated_for_2026_and_2027(self):
        for year in (2026, 2027):
            with self.subTest(year=year):
                response = self.client.post(
                    "/api/forecast",
                    headers=self.headers,
                    json={
                        "state": "Karnataka",
                        "district": "Mysuru",
                        "forecast_year": year,
                    },
                )
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json["forecast_year"], year)
                self.assertEqual(response.json["timeline"][-1]["year"], year)

        history = self.client.get("/api/forecast/history", headers=self.headers)
        self.assertEqual(
            {item["forecast_year"] for item in history.json["items"]},
            {2026, 2027},
        )

    def test_forecast_map_contains_supported_states(self):
        for year in (2026, 2027):
            with self.subTest(year=year):
                response = self.client.get(
                    f"/api/forecast/map?year={year}",
                    headers=self.headers,
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["forecast_year"], year)
                self.assertGreater(response.json["count"], 25)
                self.assertTrue(
                    any(item["state"] == "Karnataka" for item in response.json["items"])
                )
                self.assertTrue(
                    any(item["state"] == "Andhra Pradesh" for item in response.json["items"])
                )

    def test_forecast_rejects_unsupported_location_and_year(self):
        unsupported_state = self.client.post(
            "/api/forecast",
            headers=self.headers,
            json={"state": "Atlantis", "forecast_year": 2027},
        )
        unsupported_year = self.client.post(
            "/api/forecast",
            headers=self.headers,
            json={"state": "Karnataka", "forecast_year": 2025},
        )
        future_year = self.client.post(
            "/api/forecast",
            headers=self.headers,
            json={"state": "Karnataka", "forecast_year": 2031},
        )
        self.assertEqual(unsupported_state.status_code, 400)
        self.assertEqual(unsupported_year.status_code, 400)
        self.assertEqual(future_year.status_code, 400)


if __name__ == "__main__":
    unittest.main()
