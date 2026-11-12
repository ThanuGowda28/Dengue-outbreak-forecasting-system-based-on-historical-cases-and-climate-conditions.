import unittest

from flask_jwt_extended import create_access_token

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import PredictionHistory, User


class TestConfig:
    TESTING = False
    SECRET_KEY = "prediction-integration-secret-0001"
    JWT_SECRET_KEY = "prediction-integration-jwt-secret-0001"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    WEATHER_RATE_LIMIT_PER_MINUTE = 300
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"


class PredictionModelIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        service = self.app.extensions.get("prediction_service")
        self.assertIsNotNone(service)
        if (
            not service.available
            and service.load_error
            and "Application Control policy has blocked this file" in service.load_error
        ):
            self.skipTest(
                "TensorFlow is blocked by Windows Application Control: "
                f"{service.load_error}"
            )
        self.assertTrue(service.available, service.load_error)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        user = User(
            full_name="Prediction Integration Test",
            email="prediction-integration@example.test",
            password_hash="test-hash",
            phone="1234567890",
            district="Mysuru",
            state="Karnataka",
            role="user",
        )
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        self.client = self.app.test_client()
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_trained_model_prediction_is_returned_and_saved_to_history(self):
        service = self.app.extensions["prediction_service"]
        self.assertEqual(len(service.feature_columns), 48)
        self.assertEqual(len(service.scaler_columns), 47)
        self.assertEqual(
            list(service.label_encoder.classes_),
            ["High Risk", "Low Risk", "Moderate Risk"],
        )

        payload = {
            "state": "Karnataka",
            "temperature": 25.4,
            "humidity": 68.2,
            "rainfall": 1250,
            "wind_speed": 2.8,
            "pressure": 1008.6,
            "solar_radiation": 18.2,
            "year": 2026,
        }
        prediction_response = self.client.post(
            "/api/prediction/predict", json=payload, headers=self.headers
        )

        self.assertEqual(prediction_response.status_code, 200)
        prediction = prediction_response.json
        self.assertIn(prediction["risk_level"], {"High", "Low", "Moderate"})
        self.assertAlmostEqual(sum(prediction["class_probabilities"].values()), 1.0, places=5)
        self.assertGreaterEqual(prediction["confidence"], 0)
        self.assertLessEqual(prediction["confidence"], 100)
        self.assertIn("not calibrated", prediction["model_warning"])
        self.assertEqual(PredictionHistory.query.count(), 1)

        history_response = self.client.get(
            "/api/prediction/history", headers=self.headers
        )
        latest_response = self.client.get(
            "/api/prediction/latest", headers=self.headers
        )
        filtered_history_response = self.client.get(
            f"/api/prediction/history?search=Karnataka&risk={prediction['risk_level']}",
            headers=self.headers,
        )
        model_info_response = self.client.get(
            "/api/prediction/model-info", headers=self.headers
        )
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json["pagination"]["total_items"], 1)
        self.assertEqual(history_response.json["items"][0]["id"], prediction["id"])
        self.assertEqual(history_response.json["items"][0]["year"], 2026)
        self.assertEqual(latest_response.status_code, 200)
        self.assertEqual(
            latest_response.json["prediction"]["id"], prediction["id"]
        )
        self.assertEqual(filtered_history_response.status_code, 200)
        self.assertEqual(
            filtered_history_response.json["pagination"]["total_items"], 1
        )
        self.assertEqual(model_info_response.status_code, 200)
        self.assertTrue(model_info_response.json["available"])
        self.assertEqual(model_info_response.json["feature_count"], 48)
        self.assertIn("Karnataka", model_info_response.json["supported_states"])


if __name__ == "__main__":
    unittest.main()
