import unittest

from backend.app import create_app
from backend.app.extensions import db


class HealthTestConfig:
    TESTING = True
    SECRET_KEY = "health-test-secret-key-at-least-32-bytes"
    JWT_SECRET_KEY = "health-test-jwt-secret-key-at-least-32"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    OPENWEATHER_API_KEY = "test-key"


class HealthApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(HealthTestConfig)
        self.client = self.app.test_client()
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_liveness_and_dependency_health(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.assertEqual(self.client.get("/api/health/database").json["status"], "ok")
        self.assertEqual(self.client.get("/api/health/weather").status_code, 200)
        self.assertEqual(self.client.get("/api/health/model").status_code, 503)

    def test_system_health_and_security_headers(self):
        response = self.client.get("/api/health/system")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["database"], "available")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(
            response.headers["Permissions-Policy"],
            "camera=(self), microphone=(self), geolocation=(self)",
        )

    def test_api_not_found_returns_json(self):
        response = self.client.get("/api/not-a-route")
        self.assertEqual(response.status_code, 404)
        self.assertIn("message", response.json)

    def test_openapi_specification_is_served(self):
        response = self.client.get("/api/openapi.yaml")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn("application/yaml", response.content_type)
            self.assertIn(b"openapi: 3.0.3", response.data)
        finally:
            response.close()

    def test_swagger_ui_is_served(self):
        response = self.client.get("/api/docs")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.content_type)
        self.assertIn(b"swagger-ui-bundle.js", response.data)
        self.assertIn(b"/api/openapi.yaml", response.data)


if __name__ == "__main__":
    unittest.main()
