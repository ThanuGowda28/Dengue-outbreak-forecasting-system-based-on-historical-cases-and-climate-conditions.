import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask_jwt_extended import create_access_token
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.test import encode_multipart

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import AlertHistory, AlertPreference, MosquitoDetection, User
from backend.app.services.detection_model import DetectionModel
from backend.app.services.alert_service import deliver_alert


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-for-flask-tests-0001"
    JWT_SECRET_KEY = "test-jwt-secret-key-for-flask-tests-0001"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
    MOSQUITO_DETECTOR_PATH = "missing-mosquito-model.pt"
    MOSQUITO_MAX_IMAGE_BYTES = 10 * 1024 * 1024


class FakeDetectionModel:
    def __init__(self, prediction="High Risk Breeding Site"):
        self.prediction = prediction
        self.calls = 0

    def analyze(self, image):
        self.calls += 1
        return {
            "prediction": self.prediction,
            "confidence": 96.8,
            "objects_detected": ["Standing Water", "Plastic Bucket"],
            "recommendation": ["Drain stagnant water immediately."],
            "annotated_image": None,
        }


class MosquitoDetectionApiTests(unittest.TestCase):
    def setUp(self):
        self.upload_dir = tempfile.TemporaryDirectory()
        self.app = create_app(TestConfig)
        self.app.config["MOSQUITO_UPLOAD_DIR"] = self.upload_dir.name
        self.app.extensions["mosquito_detection_model"] = FakeDetectionModel()
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = self._create_user("site@example.test", "user")
        self.other = self._create_user("other@example.test", "user")
        self.admin = self._create_user("admin@example.test", "admin")
        self.user_headers = self._headers(self.user.id)
        self.other_headers = self._headers(self.other.id)
        self.admin_headers = self._headers(self.admin.id)
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.upload_dir.cleanup()

    def _create_user(self, email, role):
        user = User(
            full_name="Detection Test",
            email=email,
            password_hash="x",
            phone="+14155550123",
            district="Mysuru",
            state="Karnataka",
            role=role,
            is_verified=True,
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def _headers(user_id):
        return {
            "Authorization": f"Bearer {create_access_token(identity=str(user_id))}"
        }

    @staticmethod
    def _image_bytes(format="JPEG"):
        image = Image.new("RGB", (24, 20), color=(30, 120, 80))
        output = io.BytesIO()
        image.save(output, format=format)
        return output.getvalue()

    def _upload(self, image=None, headers=None, **form):
        response = self.client.post(
            "/api/mosquito-detection/analyze",
            data={
                "image": (io.BytesIO(image or self._image_bytes()), "site.jpg"),
                **form,
            },
            headers=headers or self.user_headers,
            content_type="multipart/form-data",
        )
        self.addCleanup(response.close)
        return response

    def test_analysis_saves_result_alerts_and_private_images(self):
        db.session.add(
            AlertPreference(
                user_id=self.user.id,
                email_alerts=True,
                sms_alerts=False,
                daily_notifications=False,
                high_risk_notifications=True,
                weather_alerts=True,
            )
        )
        db.session.commit()
        with patch("backend.app.services.alert_service.deliver_alert.apply_async") as enqueue:
            response = self._upload(latitude="12.3", longitude="76.6", district="Mysuru")

        self.assertEqual(response.status_code, 201)
        result = response.json
        self.assertEqual(result["prediction"], "High Risk Breeding Site")
        self.assertEqual(result["confidence"], 96.8)
        self.assertEqual(result["objects_detected"], ["Standing Water", "Plastic Bucket"])
        self.assertEqual(result["latitude"], 12.3)
        self.assertEqual(result["district"], "Mysuru")
        self.assertEqual(len(response.json["alerts"]), 2)
        self.assertEqual(AlertHistory.query.filter_by(alert_type="in_app").count(), 1)
        self.assertEqual(enqueue.call_count, 1)
        site_id = result["id"]
        forbidden_sites = self.client.get(
            "/api/mosquito-detection/high-risk-locations",
            headers=self.user_headers,
        )
        high_risk_sites = self.client.get(
            "/api/mosquito-detection/high-risk-locations",
            headers=self.admin_headers,
        )
        self.assertEqual(forbidden_sites.status_code, 403)
        self.assertEqual([site["id"] for site in high_risk_sites.json], [site_id])

        image = self.client.get(
            f"/api/mosquito-detection/{result['id']}/image",
            headers=self.user_headers,
        )
        hidden_from_other_user = self.client.get(
            f"/api/mosquito-detection/{result['id']}/image",
            headers=self.other_headers,
        )
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image.mimetype, "image/jpeg")
        self.assertEqual(hidden_from_other_user.status_code, 404)
        image.close()
        hidden_from_other_user.close()

    def test_rejects_corrupt_unsupported_large_images_and_partial_location(self):
        corrupt = self._upload(image=b"not an image")
        unsupported = self._upload(image=self._image_bytes("WEBP"))
        boundary, oversized_body = encode_multipart(
            {
                "image": FileStorage(
                    io.BytesIO(b"x" * (10 * 1024 * 1024 + 1)),
                    filename="site.jpg",
                )
            }
        )
        oversized = self.client.post(
            "/api/mosquito-detection/analyze",
            data=oversized_body,
            headers=self.user_headers,
            content_type=f"multipart/form-data; boundary={boundary}",
        )
        self.addCleanup(oversized.close)
        partial_location = self._upload(latitude="12.3")
        self.assertEqual(corrupt.status_code, 400)
        self.assertIn("corrupted", corrupt.json["message"].lower())
        self.assertEqual(unsupported.status_code, 400)
        self.assertIn("only jpg", unsupported.json["message"].lower())
        self.assertEqual(oversized.status_code, 400)
        self.assertIn("10 mb", oversized.json["message"].lower())
        self.assertEqual(partial_location.status_code, 400)
        self.assertEqual(MosquitoDetection.query.count(), 0)

    def test_missing_detector_returns_clear_model_unavailable(self):
        self.app.extensions["mosquito_detection_model"] = DetectionModel(
            "missing-mosquito-model.pt"
        )
        response = self._upload()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["code"], "model_unavailable")
        self.assertEqual(MosquitoDetection.query.count(), 0)

    def test_user_history_search_admin_reports_csv_and_delete(self):
        self.app.extensions["mosquito_detection_model"] = FakeDetectionModel("Low Risk")
        analyzed = self._upload()
        detection_id = analyzed.json["id"]
        user_history = self.client.get(
            "/api/mosquito-detection/history?search=Plastic",
            headers=self.user_headers,
        )
        admin_history = self.client.get(
            "/api/mosquito-detection/admin/reports?risk=Low%20Risk",
            headers=self.admin_headers,
        )
        forbidden = self.client.get(
            "/api/mosquito-detection/admin/reports",
            headers=self.user_headers,
        )
        export = self.client.get(
            "/api/mosquito-detection/admin/export",
            headers=self.admin_headers,
        )

        self.assertEqual(user_history.status_code, 200)
        self.assertEqual(len(user_history.json["items"]), 1)
        self.assertEqual(admin_history.status_code, 200)
        self.assertEqual(admin_history.json["items"][0]["user"]["email"], self.user.email)
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export.content_type)
        self.assertIn("Low Risk", export.get_data(as_text=True))

        record = db.session.get(MosquitoDetection, detection_id)
        stored_image = Path(self.upload_dir.name) / record.image_path
        self.assertTrue(stored_image.exists())
        deleted = self.client.delete(
            f"/api/mosquito-detection/{detection_id}",
            headers=self.user_headers,
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(stored_image.exists())
        self.assertIsNone(db.session.get(MosquitoDetection, detection_id))

    def test_pdf_report_contains_pdf_document(self):
        response = self._upload()
        detection_id = response.json["id"]
        report = self.client.get(
            f"/api/mosquito-detection/{detection_id}/report.pdf",
            headers=self.user_headers,
        )
        self.addCleanup(report.close)
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.mimetype, "application/pdf")
        self.assertTrue(report.data.startswith(b"%PDF"))

    def test_high_risk_detection_sends_opted_in_email_and_sms_asynchronously(self):
        db.session.add(
            AlertPreference(
                user_id=self.user.id,
                email_alerts=True,
                sms_alerts=True,
                daily_notifications=False,
                high_risk_notifications=True,
                weather_alerts=True,
            )
        )
        db.session.commit()
        with patch("backend.app.services.alert_service.deliver_alert.apply_async") as enqueue:
            response = self._upload()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            {entry["alert_type"] for entry in response.json["alerts"]},
            {"email", "sms", "in_app"},
        )
        self.assertEqual(enqueue.call_count, 2)
        email = AlertHistory.query.filter_by(alert_type="email").one()
        sms = AlertHistory.query.filter_by(alert_type="sms").one()
        with (
            patch(
                "backend.app.services.alert_service.send_mosquito_detection_alert"
            ) as send_email,
            patch("backend.app.services.alert_service.send_sms") as send_sms,
        ):
            deliver_alert.run(email.id)
            deliver_alert.run(sms.id)

        send_email.assert_called_once()
        send_sms.assert_called_once_with(sms.recipient, sms.message)
        db.session.refresh(email)
        db.session.refresh(sms)
        self.assertEqual(email.status, "sent")
        self.assertEqual(sms.status, "sent")


if __name__ == "__main__":
    unittest.main()
