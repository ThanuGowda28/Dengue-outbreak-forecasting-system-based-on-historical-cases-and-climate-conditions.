import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import AlertHistory, AlertPreference, PredictionHistory, User
from backend.app.services.alert_service import deliver_alert


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-for-flask-tests-0001"
    JWT_SECRET_KEY = "test-jwt-secret-key-for-flask-tests-0001"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    WEATHER_RATE_LIMIT_PER_MINUTE = 300
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"


class AlertApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = self._create_user("user@example.test", "user")
        self.other = self._create_user("other@example.test", "user")
        self.admin = self._create_user("admin@example.test", "admin")
        self.user_headers = self._headers(self.user.id)
        self.other_headers = self._headers(self.other.id)
        self.admin_headers = self._headers(self.admin.id)
        self.client = self.app.test_client()
        self.prediction = self._create_prediction(self.user)
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

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def _create_user(self, email, role):
        user = User(
            full_name="Alert Test",
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
        return {"Authorization": f"Bearer {create_access_token(identity=str(user_id))}"}

    @staticmethod
    def _create_prediction(user):
        prediction = PredictionHistory(
            user_id=user.id,
            state="Karnataka",
            temperature=31,
            humidity=84,
            rainfall=120,
            wind_speed=2,
            pressure=1008,
            solar_radiation=18,
            year=2026,
            prediction="High",
            confidence=92,
            class_probabilities={"High": 0.92, "Low": 0.02, "Moderate": 0.06},
            recommendations=["Remove stagnant water nearby", "Wear mosquito repellent"],
        )
        db.session.add(prediction)
        db.session.commit()
        return prediction

    def test_high_risk_prediction_queues_email_and_sms(self):
        with patch("backend.app.services.alert_service.deliver_alert.apply_async") as enqueue:
            response = self.client.post(
                "/api/alerts/send",
                json={"prediction_id": self.prediction.id},
                headers=self.user_headers,
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual({item["alert_type"] for item in response.json["alerts"]}, {"email", "sms"})
        self.assertEqual(AlertHistory.query.count(), 2)
        self.assertEqual(enqueue.call_count, 2)
        email = AlertHistory.query.filter_by(alert_type="email").one()
        sms = AlertHistory.query.filter_by(alert_type="sms").one()
        self.assertIn("Temperature: 31°C", email.message)
        self.assertIn("HIGH (92%)", sms.message)
        self.assertEqual(email.status, "queued")
        self.assertEqual(sms.status, "queued")

    def test_prediction_alert_auto_dispatch_is_idempotent(self):
        with patch("backend.app.services.alert_service.deliver_alert.apply_async") as enqueue:
            first = self.client.post(
                "/api/alerts/send",
                json={"prediction_id": self.prediction.id},
                headers=self.user_headers,
            )
            second = self.client.post(
                "/api/alerts/send",
                json={"prediction_id": self.prediction.id},
                headers=self.user_headers,
            )

        self.assertEqual(first.status_code, 202)
        self.assertEqual(second.status_code, 202)
        self.assertEqual(AlertHistory.query.count(), 2)
        self.assertEqual(enqueue.call_count, 2)

    def test_alert_history_is_scoped_to_user_and_settings_are_saved(self):
        self.client.post(
            "/api/alerts/send",
            json={"prediction_id": self.prediction.id},
            headers=self.user_headers,
        )
        mine = self.client.get("/api/alerts/history", headers=self.user_headers)
        theirs = self.client.get("/api/alerts/history", headers=self.other_headers)
        self.assertEqual(len(mine.json["items"]), 2)
        self.assertEqual(theirs.json["items"], [])

        updated = self.client.put(
            "/api/alerts/settings",
            json={
                "email_alerts": True,
                "sms_alerts": False,
                "daily_notifications": True,
                "high_risk_notifications": True,
                "weather_alerts": False,
            },
            headers=self.user_headers,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json["preferences"]["sms_alerts"])
        fetched = self.client.get("/api/alerts/settings", headers=self.user_headers)
        self.assertTrue(fetched.json["preferences"]["daily_notifications"])

    def test_admin_can_filter_and_export_alerts_but_user_cannot(self):
        with patch("backend.app.services.alert_service.deliver_alert.apply_async"):
            self.client.post(
                "/api/alerts/send",
                json={"prediction_id": self.prediction.id},
                headers=self.user_headers,
            )
        forbidden = self.client.get("/api/alerts/admin/history", headers=self.user_headers)
        admin = self.client.get(
            "/api/alerts/admin/history?type=email&status=queued",
            headers=self.admin_headers,
        )
        export = self.client.get(
            "/api/alerts/admin/export?type=sms",
            headers=self.admin_headers,
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(admin.status_code, 200)
        self.assertEqual(len(admin.json["items"]), 1)
        self.assertEqual(admin.json["items"][0]["user_email"], self.user.email)
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export.content_type)
        self.assertIn("sms", export.get_data(as_text=True))

    def test_invalid_alert_setting_and_foreign_prediction_are_rejected(self):
        invalid = self.client.put(
            "/api/alerts/settings",
            json={"email_alerts": "yes"},
            headers=self.user_headers,
        )
        foreign_prediction = self.client.post(
            "/api/alerts/send",
            json={"prediction_id": self.prediction.id},
            headers=self.other_headers,
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(foreign_prediction.status_code, 404)
        self.assertEqual(AlertHistory.query.count(), 0)

    def test_sms_is_disabled_by_default_until_user_opts_in(self):
        preference = db.session.get(AlertPreference, self.other.id)
        self.assertIsNone(preference)
        settings = self.client.get("/api/alerts/settings", headers=self.other_headers)
        self.assertFalse(settings.json["preferences"]["sms_alerts"])

    def test_worker_marks_a_successfully_delivered_email_as_sent(self):
        alert = AlertHistory(
            user_id=self.user.id,
            prediction_id=self.prediction.id,
            alert_type="email",
            status="queued",
            recipient=self.user.email,
            message="Test email alert",
        )
        db.session.add(alert)
        db.session.commit()

        with patch("backend.app.services.alert_service.send_prediction_alert") as send:
            deliver_alert.run(alert.id)

        send.assert_called_once_with(self.user, self.prediction, self.user.email)
        db.session.refresh(alert)
        self.assertEqual(alert.status, "sent")
        self.assertEqual(alert.attempts, 1)
        self.assertIsNotNone(alert.sent_at)

    def test_worker_records_failure_and_schedules_retry(self):
        alert = AlertHistory(
            user_id=self.user.id,
            prediction_id=self.prediction.id,
            alert_type="email",
            status="queued",
            recipient=self.user.email,
            message="Test email alert",
        )
        db.session.add(alert)
        db.session.commit()

        with (
            patch(
                "backend.app.services.alert_service.send_prediction_alert",
                side_effect=RuntimeError("SMTP unavailable"),
            ),
            patch(
                "backend.app.services.alert_service.deliver_alert.retry",
                side_effect=RuntimeError("retry scheduled"),
            ) as retry,
        ):
            with self.assertRaisesRegex(RuntimeError, "retry scheduled"):
                deliver_alert.run(alert.id)

        retry.assert_called_once()
        db.session.refresh(alert)
        self.assertEqual(alert.status, "retrying")
        self.assertEqual(alert.attempts, 1)
        self.assertEqual(alert.failure_reason, "SMTP unavailable")


if __name__ == "__main__":
    unittest.main()
