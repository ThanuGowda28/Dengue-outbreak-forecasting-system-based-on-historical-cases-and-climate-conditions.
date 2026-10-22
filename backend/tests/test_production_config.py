import os
import unittest
from unittest.mock import patch

from backend.app.config import get_config


class ProductionConfigTests(unittest.TestCase):
    def setUp(self):
        self.environment = {
            "APP_ENV": "production",
            "SECRET_KEY": "production-secret-key-with-at-least-32-characters",
            "JWT_SECRET_KEY": "different-production-jwt-secret-32-characters",
            "FRONTEND_ORIGIN": "https://dengue.example.com",
            "DB_HOST": "mysql.example.com",
            "DB_PORT": "3306",
            "DB_NAME": "dengue_forecasting",
            "DB_USER": "dengue_app",
            "DB_PASSWORD": "not-a-real-password",
            "OPENWEATHER_API_KEY": "not-a-real-weather-key",
            "MAIL_SERVER": "smtp.example.com",
            "MAIL_PORT": "587",
            "MAIL_USERNAME": "smtp-user@example.com",
            "MAIL_PASSWORD": "not-a-real-mail-password",
            "MAIL_DEFAULT_SENDER": "noreply@example.com",
            "MAIL_USE_TLS": "true",
            "MAIL_USE_SSL": "false",
            "CELERY_BROKER_URL": "rediss://redis.example.com:6380/0",
            "CELERY_RESULT_BACKEND": "rediss://redis.example.com:6380/1",
        }
        self.patcher = patch.dict(os.environ, self.environment, clear=True)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_accepts_complete_production_environment(self):
        config = get_config()
        self.assertFalse(config.DEBUG)
        self.assertFalse(config.LOCAL_DEMO_MODE)
        self.assertTrue(config.REQUIRE_MODEL_AT_STARTUP)

    def test_requires_database_provider_and_mail_settings(self):
        for name in (
            "DB_HOST",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "FRONTEND_ORIGIN",
            "OPENWEATHER_API_KEY",
            "MAIL_SERVER",
            "MAIL_DEFAULT_SENDER",
            "MAIL_USERNAME",
            "MAIL_PASSWORD",
            "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND",
        ):
            with self.subTest(name=name):
                with patch.dict(os.environ, {name: ""}):
                    with self.assertRaisesRegex(RuntimeError, name):
                        get_config()

    def test_rejects_insecure_production_frontend_origins(self):
        for origin in ("http://dengue.example.com", "http://localhost:5173"):
            with self.subTest(origin=origin):
                with patch.dict(os.environ, {"FRONTEND_ORIGIN": origin}):
                    with self.assertRaisesRegex(RuntimeError, "FRONTEND_ORIGIN"):
                        get_config()

    def test_rejects_placeholder_secret_and_provider_values(self):
        with patch.dict(os.environ, {"OPENWEATHER_API_KEY": "SET-THROUGH-SECRET-MANAGER"}):
            with self.assertRaisesRegex(RuntimeError, "OPENWEATHER_API_KEY"):
                get_config()

    def test_rejects_invalid_database_port_and_smtp_configuration(self):
        with patch.dict(os.environ, {"DB_PORT": "invalid"}):
            with self.assertRaisesRegex(RuntimeError, "DB_PORT"):
                get_config()
        with patch.dict(os.environ, {"MAIL_PASSWORD": ""}):
            with self.assertRaisesRegex(RuntimeError, "MAIL_PASSWORD"):
                get_config()
        with patch.dict(os.environ, {"MAIL_USE_SSL": "true"}):
            with self.assertRaisesRegex(RuntimeError, "MAIL_USE_TLS"):
                get_config()
        with patch.dict(
            os.environ, {"MAIL_USE_TLS": "false", "MAIL_USE_SSL": "false"}
        ):
            with self.assertRaisesRegex(RuntimeError, "SMTP must enable"):
                get_config()
        with patch.dict(os.environ, {"MAIL_PORT": "invalid"}):
            with self.assertRaisesRegex(RuntimeError, "MAIL_PORT"):
                get_config()


if __name__ == "__main__":
    unittest.main()
