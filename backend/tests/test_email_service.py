import unittest
from unittest.mock import patch

from flask import Flask

from backend.app.services.email import email_is_configured, send_email


class EmailServiceTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            MAIL_SERVER="smtp.gmail.com",
            MAIL_PORT=587,
            MAIL_USE_TLS=True,
            MAIL_USE_SSL=False,
            MAIL_USERNAME="sender@gmail.com",
            MAIL_PASSWORD="gmail-app-password",
            MAIL_DEFAULT_SENDER="sender@gmail.com",
            MAIL_TIMEOUT_SECONDS=15,
        )

    @patch("backend.app.services.email.smtplib.SMTP")
    def test_send_email_uses_configured_gmail_starttls_credentials(self, smtp_class):
        smtp = smtp_class.return_value.__enter__.return_value

        with self.app.app_context():
            self.assertTrue(email_is_configured())
            send_email("recipient@example.test", "Test subject", "Test body")

        smtp_class.assert_called_once_with("smtp.gmail.com", 587, timeout=15)
        smtp.starttls.assert_called_once_with()
        smtp.login.assert_called_once_with("sender@gmail.com", "gmail-app-password")
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["From"], "sender@gmail.com")
        self.assertEqual(message["To"], "recipient@example.test")
        self.assertEqual(message["Subject"], "Test subject")

    def test_email_requires_complete_smtp_authentication_configuration(self):
        with self.app.app_context():
            self.app.config["MAIL_PASSWORD"] = ""
            self.assertFalse(email_is_configured())
            with self.assertRaisesRegex(RuntimeError, "not configured"):
                send_email("recipient@example.test", "Test", "Body")


if __name__ == "__main__":
    unittest.main()
