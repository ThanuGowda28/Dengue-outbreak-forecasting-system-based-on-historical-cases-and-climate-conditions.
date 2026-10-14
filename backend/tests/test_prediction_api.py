import unittest
from datetime import datetime, timezone

from flask_jwt_extended import create_access_token

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import PredictionHistory, User, UserPreference
from backend.app.services.prediction import PredictionInputError


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-for-flask-tests-0001"
    JWT_SECRET_KEY = "test-jwt-secret-key-for-flask-tests-0001"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    WEATHER_RATE_LIMIT_PER_MINUTE = 300


class StubPredictionService:
    available = True
    load_error = None

    class Encoder:
        classes_ = ["High Risk", "Low Risk", "Moderate Risk"]

    label_encoder = Encoder()
    feature_columns = ["year", "state_ut_Karnataka"]

    def predict(self, payload):
        if not isinstance(payload, dict) or not all(key in payload for key in (
            "state", "temperature", "humidity", "rainfall", "wind_speed",
            "pressure", "solar_radiation", "year"
        )):
            raise PredictionInputError("Required prediction fields are missing.")
        return {
            "state": payload["state"],
            "risk_level": "High",
            "confidence": 90.0,
            "class_probabilities": {"High": 0.9, "Low": 0.02, "Moderate": 0.08},
            "recommendations": ["Increase mosquito source reduction"],
            "model_warning": "Research output only.",
        }


class PredictionApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app.extensions["prediction_service"] = StubPredictionService()
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = self._create_user("user@example.test", "user")
        self.other = self._create_user("other@example.test", "user")
        self.admin = self._create_user("admin@example.test", "admin")
        self.client = self.app.test_client()
        self.user_headers = self._headers(self.user.id)
        self.other_headers = self._headers(self.other.id)
        self.admin_headers = self._headers(self.admin.id)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def _create_user(self, email, role):
        user = User(full_name="Test User", email=email, password_hash="x", phone="1234567890", district="Mysuru", state="Karnataka", role=role)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def _headers(user_id):
        token = create_access_token(identity=str(user_id))
        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _payload():
        return {"state": "Karnataka", "temperature": 25.4, "humidity": 68.2, "rainfall": 1250, "wind_speed": 2.8, "pressure": 1008.6, "solar_radiation": 18.2, "year": 2025}

    def test_prediction_is_persisted_and_returned(self):
        response = self.client.post("/api/prediction/predict", json=self._payload(), headers=self.user_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["risk_level"], "High")
        self.assertEqual(response.json["class_probabilities"]["High"], 0.9)
        self.assertEqual(PredictionHistory.query.count(), 1)

    def test_missing_input_and_unauthorized_requests_are_rejected(self):
        self.assertEqual(self.client.post("/api/prediction/predict", json={}, headers=self.user_headers).status_code, 400)
        self.assertEqual(self.client.get("/api/prediction/history").status_code, 401)

    def test_users_are_scoped_and_admin_can_view_all_history(self):
        response = self.client.post("/api/prediction/predict", json=self._payload(), headers=self.user_headers)
        self.assertEqual(response.status_code, 200)
        user_history = self.client.get("/api/prediction/history", headers=self.other_headers)
        self.assertEqual(user_history.json["pagination"]["total_items"], 0)
        admin_history = self.client.get("/api/prediction/history", headers=self.admin_headers)
        self.assertEqual(admin_history.json["pagination"]["total_items"], 1)
        self.assertIn("user_id", admin_history.json["items"][0])

    def test_history_filters_and_pagination(self):
        for state in ("Karnataka", "Goa", "Tamil Nadu"):
            payload = {**self._payload(), "state": state}
            self.assertEqual(
                self.client.post(
                    "/api/prediction/predict",
                    json=payload,
                    headers=self.user_headers,
                ).status_code,
                200,
            )

        second_page = self.client.get(
            "/api/prediction/history?page=2&per_page=1",
            headers=self.user_headers,
        )
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(second_page.json["pagination"]["page"], 2)
        self.assertEqual(second_page.json["pagination"]["total_items"], 3)
        self.assertEqual(len(second_page.json["items"]), 1)

        filtered = self.client.get(
            "/api/prediction/history?search=goa&risk=High",
            headers=self.user_headers,
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json["pagination"]["total_items"], 1)
        self.assertEqual(filtered.json["items"][0]["state"], "Goa")

        invalid_filter = self.client.get(
            "/api/prediction/history?risk=Critical",
            headers=self.user_headers,
        )
        self.assertEqual(invalid_filter.status_code, 400)

    def test_history_delete_is_authenticated_and_owner_scoped(self):
        created = self.client.post(
            "/api/prediction/predict",
            json=self._payload(),
            headers=self.user_headers,
        )
        prediction_id = created.json["id"]

        unauthorized = self.client.delete(
            f"/api/prediction/history/{prediction_id}"
        )
        forbidden_by_scope = self.client.delete(
            f"/api/prediction/history/{prediction_id}",
            headers=self.other_headers,
        )
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(forbidden_by_scope.status_code, 404)
        self.assertEqual(PredictionHistory.query.count(), 1)

        deleted = self.client.delete(
            f"/api/prediction/history/{prediction_id}",
            headers=self.user_headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json["id"], prediction_id)
        self.assertEqual(PredictionHistory.query.count(), 0)

        missing = self.client.delete(
            f"/api/prediction/history/{prediction_id}",
            headers=self.user_headers,
        )
        self.assertEqual(missing.status_code, 404)

    def test_admin_can_delete_prediction_visible_in_admin_history(self):
        created = self.client.post(
            "/api/prediction/predict",
            json=self._payload(),
            headers=self.user_headers,
        )
        prediction_id = created.json["id"]
        deleted = self.client.delete(
            f"/api/prediction/history/{prediction_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(PredictionHistory.query.count(), 0)

    def test_dashboard_contains_prediction_summary(self):
        self.client.post("/api/prediction/predict", json=self._payload(), headers=self.user_headers)
        response = self.client.get("/api/dashboard", headers=self.user_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["prediction_count"], 1)
        self.assertEqual(response.json["latest_prediction"]["risk_level"], "High")
        self.assertIn("High Risk", response.json["risk_distribution"])
        self.assertEqual(len(response.json["alerts"]), 1)
        self.assertEqual(response.json["alerts"][0]["type"], "model_assessment")
        self.assertEqual(response.json["alerts"][0]["severity"], "high")
        self.assertIn("not a verified outbreak alert", response.json["alerts"][0]["message"])

        other_dashboard = self.client.get(
            "/api/dashboard", headers=self.other_headers
        )
        self.assertEqual(other_dashboard.json["alerts"], [])

        db.session.add(
            UserPreference(
                user_id=self.user.id,
                alerts=False,
                weekly_summary=False,
                dark_mode=False,
            )
        )
        db.session.commit()
        opted_out = self.client.get("/api/dashboard", headers=self.user_headers)
        self.assertEqual(opted_out.json["alerts"], [])

    def test_model_unavailable_returns_service_unavailable(self):
        service = self.app.extensions["prediction_service"]
        service.available = False
        service.load_error = "model files missing"
        response = self.client.post("/api/prediction/predict", json=self._payload(), headers=self.user_headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"], "model files missing")

    def test_legacy_endpoint_reports_gone_instead_of_placeholder_data(self):
        responses = (
            self.client.get("/api/prediction", headers=self.user_headers),
            self.client.post(
                "/api/prediction", json=self._payload(), headers=self.user_headers
            ),
        )
        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertEqual(response.status_code, 410)
                self.assertEqual(response.json["error"], "endpoint_deprecated")
                self.assertNotIn("predictions", response.json)
                self.assertEqual(
                    response.json["predict_endpoint"], "/api/prediction/predict"
                )
                self.assertEqual(
                    response.json["history_endpoint"], "/api/prediction/history"
                )


if __name__ == "__main__":
    unittest.main()
