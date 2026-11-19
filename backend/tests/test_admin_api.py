import unittest
from io import BytesIO
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from flask_jwt_extended import create_access_token

from backend.app import create_app
from backend.app.extensions import bcrypt, db
from backend.app.models import PredictionHistory, User, WeatherHistory


class AdminTestConfig:
    TESTING = True
    SECRET_KEY = "admin-test-secret-key-at-least-32-bytes"
    JWT_SECRET_KEY = "admin-test-jwt-secret-key-at-least-32"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"


class AdminApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(AdminTestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.admin = self._create_user("admin@example.test", "admin", "AdminPass1!")
        self.user = self._create_user("user@example.test", "user", "UserPass1!")
        self.client = self.app.test_client()
        self.admin_headers = self._headers(self.admin.id)
        self.user_headers = self._headers(self.user.id)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def _create_user(self, email, role, password):
        user = User(
            full_name=email.split("@")[0],
            email=email,
            password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
            phone="+1 555 555 1212",
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
        token = create_access_token(identity=str(user_id))
        return {"Authorization": f"Bearer {token}"}

    def _prediction(self, owner):
        record = PredictionHistory(
            user_id=owner.id,
            state="Karnataka",
            temperature=25,
            humidity=70,
            rainfall=100,
            wind_speed=2,
            pressure=1008,
            solar_radiation=18,
            year=2025,
            prediction="High",
            confidence=90,
            class_probabilities={"High": 0.9, "Moderate": 0.08, "Low": 0.02},
            recommendations=[],
            prediction_time=datetime.now(timezone.utc),
        )
        db.session.add(record)
        db.session.commit()
        return record

    def test_admin_login_requires_admin_role_and_valid_password(self):
        self.assertEqual(
            self.client.post(
                "/api/admin/auth/login",
                json={"email": self.user.email, "password": "UserPass1!"},
            ).status_code,
            401,
        )
        response = self.client.post(
            "/api/admin/auth/login",
            json={"email": " ADMIN@example.test ", "password": "AdminPass1!"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["user"]["role"], "admin")
        self.assertIn("access_token", response.json)
        self.assertIn("refresh_token", response.json)

        self.admin.is_verified = False
        db.session.commit()
        unverified = self.client.post(
            "/api/admin/auth/login",
            json={"email": self.admin.email, "password": "AdminPass1!"},
        )
        self.assertEqual(unverified.status_code, 403)
        self.assertEqual(unverified.json["error"], "email_not_verified")

    def test_admin_login_is_rate_limited(self):
        self.app.config["ADMIN_LOGIN_RATE_LIMIT_PER_MINUTE"] = 1
        payload = {"email": self.admin.email, "password": "AdminPass1!"}
        self.assertEqual(
            self.client.post("/api/admin/auth/login", json=payload).status_code,
            200,
        )
        limited = self.client.post("/api/admin/auth/login", json=payload)
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.headers["Retry-After"], "60")

    def test_admin_dashboard_users_and_reports_are_protected_and_database_backed(self):
        self.assertEqual(self.client.get("/api/admin/dashboard").status_code, 401)
        self.assertEqual(
            self.client.get("/api/admin/users", headers=self.user_headers).status_code,
            403,
        )
        record = self._prediction(self.user)
        dashboard = self.client.get("/api/admin/dashboard", headers=self.admin_headers)
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json["metrics"]["user_count"], 2)
        self.assertEqual(dashboard.json["metrics"]["prediction_count"], 1)
        self.assertEqual(dashboard.json["recent_predictions"][0]["id"], record.id)

        reports = self.client.get("/api/admin/reports", headers=self.admin_headers)
        self.assertEqual(reports.status_code, 200)
        self.assertEqual(reports.json["summary"]["predictions"], 1)
        self.assertEqual(reports.json["predictions_by_risk"]["High"], 1)
        self.assertEqual(len(reports.json["monthly_predictions"]), 1)

        analytics = self.client.get(
            "/api/admin/analytics", headers=self.admin_headers
        )
        self.assertEqual(analytics.status_code, 200)
        self.assertEqual(
            analytics.json["predictions_by_state"],
            [
                {
                    "state": "Karnataka",
                    "count": 1,
                    "average_confidence": 90.0,
                }
            ],
        )
        self.assertEqual(
            analytics.json["predictions_by_year"], [{"year": 2025, "count": 1}]
        )
        self.assertEqual(analytics.json["users_by_role"], {"admin": 1, "user": 1})
        self.assertEqual(analytics.json["weather_by_provider"], {})

        users = self.client.get("/api/admin/users?search=user", headers=self.admin_headers)
        self.assertEqual(users.status_code, 200)
        self.assertEqual([item["email"] for item in users.json["users"]], [self.user.email])

    def test_admin_reports_filter_all_accounts_by_date_and_remain_role_protected(self):
        today = datetime.now(timezone.utc).date()
        recent_prediction = self._prediction(self.user)
        recent_prediction.prediction_time = datetime.now(timezone.utc)
        older_prediction = self._prediction(self.admin)
        older_prediction.prediction = "Low"
        older_prediction.prediction_time = datetime.now(timezone.utc) - timedelta(days=60)

        for owner, observed_date in (
            (self.user, today),
            (self.admin, today - timedelta(days=60)),
        ):
            db.session.add(
                WeatherHistory(
                    user_id=owner.id,
                    location_name="Mysuru",
                    district="Mysuru",
                    latitude=12.3,
                    longitude=76.6,
                    weather_date=observed_date,
                    record_type="current",
                    provider="openweather",
                    observed_at=datetime.combine(
                        observed_date, datetime.min.time(), tzinfo=timezone.utc
                    ),
                    payload={
                        "location": {"district": "Mysuru", "state": "Karnataka"},
                        "current": {
                            "weather_date": observed_date.isoformat(),
                            "temperature": 25,
                        },
                    },
                )
            )
        db.session.commit()

        query = f"start_date={today.isoformat()}&end_date={today.isoformat()}"
        response = self.client.get(
            f"/api/admin/reports?{query}", headers=self.admin_headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["summary"]["registered_users"], 2)
        self.assertEqual(response.json["summary"]["predictions"], 1)
        self.assertEqual(response.json["summary"]["weather_records"], 1)
        self.assertEqual(response.json["predictions_by_risk"], {"High": 1})
        self.assertEqual(response.json["weather_records_by_type"], {"current": 1})

        forbidden = self.client.get(
            f"/api/admin/reports?{query}", headers=self.user_headers
        )
        invalid = self.client.get(
            "/api/admin/reports?start_date=invalid", headers=self.admin_headers
        )
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(invalid.status_code, 400)

    def test_user_and_prediction_management_create_update_filter_delete(self):
        payload = {
            "full_name": "New account",
            "email": "new@example.test",
            "password": "NewPass1!",
            "phone": "+1 555 555 3333",
            "district": "Mysuru",
            "state": "Karnataka",
            "role": "user",
        }
        created = self.client.post(
            "/api/admin/users", json=payload, headers=self.admin_headers
        )
        self.assertEqual(created.status_code, 201)
        new_id = created.json["user"]["id"]
        promoted = self.client.patch(
            f"/api/admin/users/{new_id}",
            json={
                "role": "admin",
                "full_name": "Updated account",
                "district": "Bengaluru",
            },
            headers=self.admin_headers,
        )
        self.assertEqual(promoted.status_code, 200)
        self.assertEqual(promoted.json["user"]["role"], "admin")
        self.assertEqual(promoted.json["user"]["full_name"], "Updated account")
        self.assertEqual(promoted.json["user"]["district"], "Bengaluru")

        prediction = self._prediction(self.user)
        listing = self.client.get(
            "/api/admin/predictions?risk=High", headers=self.admin_headers
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json["predictions"][0]["id"], prediction.id)
        self.assertEqual(
            self.client.get(
                f"/api/admin/predictions/{prediction.id}", headers=self.admin_headers
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/admin/predictions/{prediction.id}", headers=self.admin_headers
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/admin/users/{new_id}", headers=self.admin_headers
            ).status_code,
            200,
        )
        self.assertIsNone(db.session.get(User, new_id))

    def test_admin_inventory_climate_and_model_status_apis(self):
        db.session.add(
            WeatherHistory(
                user_id=self.user.id,
                location_name="Mysuru",
                district="Mysuru",
                temperature=27.5,
                humidity=70,
                rainfall=1.2,
                latitude=12.3,
                longitude=76.6,
                weather_date=datetime.now(timezone.utc).date(),
                record_type="current",
                provider="openweather",
                observed_at=datetime.now(timezone.utc),
                payload={},
            )
        )
        db.session.commit()

        datasets = self.client.get(
            "/api/admin/datasets", headers=self.admin_headers
        )
        self.assertEqual(datasets.status_code, 200)
        self.assertIn("datasets", datasets.json)
        self.assertGreater(datasets.json["total_items"], 0)

        climate = self.client.get(
            "/api/admin/climate-data?district=Mysuru&provider=openweather",
            headers=self.admin_headers,
        )
        self.assertEqual(climate.status_code, 200)
        self.assertEqual(climate.json["pagination"]["total_items"], 1)
        self.assertEqual(climate.json["records"][0]["location_name"], "Mysuru")

        invalid_climate = self.client.get(
            "/api/admin/climate-data?start_date=not-a-date",
            headers=self.admin_headers,
        )
        self.assertEqual(invalid_climate.status_code, 400)
        invalid_provider = self.client.get(
            "/api/admin/climate-data?provider=unknown",
            headers=self.admin_headers,
        )
        self.assertEqual(invalid_provider.status_code, 400)

        model_status = self.client.get(
            "/api/admin/model-status", headers=self.admin_headers
        )
        self.assertEqual(model_status.status_code, 200)
        self.assertIn("inference_artifacts_present", model_status.json)
        self.assertFalse(model_status.json["runtime_load_verified"])
        self.assertTrue(model_status.json["training_job_available"])

    def test_new_admin_read_only_apis_require_administrator_access(self):
        for endpoint in (
            "/api/admin/datasets",
            "/api/admin/climate-data",
            "/api/admin/model-status",
            "/api/admin/analytics",
        ):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.client.get(endpoint).status_code, 401)
                self.assertEqual(
                    self.client.get(endpoint, headers=self.user_headers).status_code,
                    403,
                )

    def test_admin_can_upload_and_delete_only_csv_datasets(self):
        rejected = self.client.post(
            "/api/admin/datasets",
            data={"file": (BytesIO(b"not a model\n"), "unsafe.pkl")},
            headers=self.admin_headers,
            content_type="multipart/form-data",
        )
        self.assertEqual(rejected.status_code, 400)

        uploaded = self.client.post(
            "/api/admin/datasets",
            data={
                "file": (
                    BytesIO(b"state,year,risk\nKarnataka,2025,Low\n"),
                    "sample.csv",
                )
            },
            headers=self.admin_headers,
            content_type="multipart/form-data",
        )
        self.assertEqual(uploaded.status_code, 201)
        relative_path = uploaded.json["dataset"]["relative_path"]
        try:
            self.assertEqual(relative_path.split("/")[0], "uploads")
            deleted = self.client.delete(
                f"/api/admin/datasets/{relative_path}",
                headers=self.admin_headers,
            )
            self.assertEqual(deleted.status_code, 200)
        finally:
            leftover = (
                Path(__file__).resolve().parents[1]
                / "app"
                / "ml"
                / "dataset"
                / relative_path
            )
            leftover.unlink(missing_ok=True)
            try:
                leftover.parent.rmdir()
            except OSError:
                pass

    def test_model_training_requires_admin_and_processed_data(self):
        denied = self.client.post(
            "/api/admin/model-training", headers=self.user_headers
        )
        self.assertEqual(denied.status_code, 403)

        with TemporaryDirectory() as temporary_directory:
            self.app.config["ML_PROCESSED_DIR"] = str(
                Path(temporary_directory) / "missing"
            )
            response = self.client.post(
                "/api/admin/model-training", headers=self.admin_headers
            )
        self.assertEqual(response.status_code, 409)
        self.assertIn("processed train.csv and test.csv", response.json["message"])

    def test_user_deletion_cleans_related_records_and_cannot_remove_last_admin(self):
        prediction = self._prediction(self.user)
        db.session.add(
            WeatherHistory(
                user_id=self.user.id,
                location_name="Mysuru",
                latitude=12.3,
                longitude=76.6,
                record_type="current",
                provider="test",
                observed_at=datetime.now(timezone.utc),
                payload={},
            )
        )
        db.session.commit()
        prediction_id = prediction.id
        deleted = self.client.delete(
            f"/api/admin/users/{self.user.id}", headers=self.admin_headers
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertIsNone(db.session.get(PredictionHistory, prediction_id))
        self.assertEqual(WeatherHistory.query.filter_by(user_id=self.user.id).count(), 0)
        self.assertEqual(
            self.client.delete(
                f"/api/admin/users/{self.admin.id}", headers=self.admin_headers
            ).status_code,
            409,
        )


if __name__ == "__main__":
    unittest.main()
