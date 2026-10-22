import unittest
from unittest.mock import patch

from backend.app import create_app


class ContactTestConfig:
    TESTING = True
    SECRET_KEY = "contact-test-secret-key-at-least-32-bytes"
    JWT_SECRET_KEY = "contact-test-jwt-secret-key-at-least-32"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    MAIL_SERVER = "smtp.test"
    MAIL_USERNAME = "smtp-user@example.test"
    MAIL_PASSWORD = "smtp-test-password"
    MAIL_DEFAULT_SENDER = "noreply@example.test"
    CONTACT_EMAIL = "team@example.test"


class ContactApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(ContactTestConfig)
        self.client = self.app.test_client()

    @patch("backend.app.routes.contact.send_email")
    def test_contact_message_is_delivered_to_configured_recipient(self, send_email):
        response = self.client.post(
            "/api/contact",
            json={
                "name": "Test Person",
                "email": "person@example.test",
                "message": "Project feedback",
            },
        )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(send_email.call_args.args[0], "team@example.test")
        self.assertIn("person@example.test", send_email.call_args.args[2])

    def test_contact_message_validates_inputs_and_mail_configuration(self):
        invalid = self.client.post("/api/contact", json={"name": "", "email": "bad", "message": ""})
        self.assertEqual(invalid.status_code, 400)

        self.app.config["CONTACT_EMAIL"] = ""
        unavailable = self.client.post(
            "/api/contact",
            json={
                "name": "Test Person",
                "email": "person@example.test",
                "message": "Project feedback",
            },
        )
        self.assertEqual(unavailable.status_code, 503)


if __name__ == "__main__":
    unittest.main()
