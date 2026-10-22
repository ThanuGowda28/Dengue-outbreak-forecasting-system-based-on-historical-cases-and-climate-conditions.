import io
import unittest
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import Hospital, User


class TestConfig:
    TESTING = True
    SECRET_KEY = "hospital-test-secret-key-000000001"
    JWT_SECRET_KEY = "hospital-test-jwt-secret-key-00001"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"
    HOSPITAL_OVERPASS_URL = "https://overpass.test/api/interpreter"
    HOSPITAL_NOMINATIM_URL = "https://nominatim.test"
    HOSPITAL_USER_AGENT = "HospitalApiTests/1.0"
    HOSPITAL_PROVIDER_TIMEOUT_SECONDS = 1


class HospitalApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(
            full_name="Hospital User",
            email="hospital-user@example.test",
            password_hash="unused",
            phone="1234567890",
            district="Mysuru",
            state="Karnataka",
            role="user",
        )
        self.admin = User(
            full_name="Hospital Admin",
            email="hospital-admin@example.test",
            password_hash="unused",
            phone="1234567891",
            district="Bengaluru Urban",
            state="Karnataka",
            role="admin",
        )
        db.session.add_all([self.user, self.admin])
        db.session.commit()
        self.user_headers = {
            "Authorization": f"Bearer {create_access_token(identity=str(self.user.id))}"
        }
        self.admin_headers = {
            "Authorization": f"Bearer {create_access_token(identity=str(self.admin.id))}"
        }
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    @staticmethod
    def facility(**overrides):
        record = {
            "external_id": "osm:node:42",
            "name": "Mysuru District Hospital",
            "address": "Hospital Road, Mysuru",
            "district": "Mysuru",
            "city": "Mysuru",
            "state": "Karnataka",
            "pincode": "570001",
            "latitude": 12.305,
            "longitude": 76.655,
            "phone": "+918212222222",
            "ambulance_phone": None,
            "email": None,
            "rating": None,
            "hospital_type": "Government",
            "emergency": True,
            "icu": True,
            "blood_bank": True,
            "ambulance": True,
            "opening_hours": "24/7",
            "website": None,
            "source": "openstreetmap",
        }
        record.update(overrides)
        return record

    def test_nearby_returns_distance_and_emergency_summary_from_osm_records(self):
        with patch(
            "backend.app.routes.hospital_routes.find_osm_facilities",
            return_value=[self.facility()],
        ):
            response = self.client.get(
                "/api/hospitals/nearby?latitude=12.2958&longitude=76.6394",
                headers=self.user_headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["count"], 1)
        hospital = response.json["items"][0]
        self.assertEqual(hospital["name"], "Mysuru District Hospital")
        self.assertGreater(hospital["distance_km"], 0)
        self.assertTrue(hospital["blood_bank"])
        self.assertIsNotNone(response.json["emergency"])
        self.assertGreater(response.json["emergency"]["estimated_travel_minutes"], 0)

    def test_nearby_supports_geocoded_manual_location_and_filters(self):
        db.session.add(Hospital(**self.facility(external_id=None)))
        db.session.commit()
        with patch(
            "backend.app.routes.hospital_routes.geocode",
            return_value={
                "latitude": 12.2958,
                "longitude": 76.6394,
                "district": "Mysuru",
                "state": "Karnataka",
            },
        ), patch(
            "backend.app.routes.hospital_routes.find_osm_facilities",
            return_value=[],
        ):
            response = self.client.get(
                "/api/hospitals/nearby?location=570001&emergency=true&distance_km=15",
                headers=self.user_headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["location"]["district"], "Mysuru")
        self.assertEqual(len(response.json["items"]), 1)

    def test_nearby_validates_coordinates_radius_and_filters(self):
        invalid = self.client.get(
            "/api/hospitals/nearby?latitude=100&longitude=0",
            headers=self.user_headers,
        )
        bad_filter = self.client.get(
            "/api/hospitals/nearby?latitude=12&longitude=76&icu=yes",
            headers=self.user_headers,
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(bad_filter.status_code, 400)

    def test_hospital_apis_require_authentication_and_admin_management_is_protected(self):
        self.assertEqual(self.client.get("/api/hospitals/nearby").status_code, 401)
        self.assertEqual(
            self.client.get("/api/hospitals/manage", headers=self.user_headers).status_code,
            403,
        )

    def test_search_details_and_missing_facility(self):
        hospital = Hospital(**self.facility(external_id=None))
        db.session.add(hospital)
        db.session.commit()
        response = self.client.get(
            "/api/hospitals/search?query=570001",
            headers=self.user_headers,
        )
        details = self.client.get(
            f"/api/hospitals/details/{hospital.id}",
            headers=self.user_headers,
        )
        missing = self.client.get(
            "/api/hospitals/details/999",
            headers=self.user_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["items"][0]["id"], hospital.id)
        self.assertEqual(details.json["phone"], "+918212222222")
        self.assertEqual(missing.status_code, 404)

    def test_location_reverse_geocoding(self):
        with patch(
            "backend.app.routes.hospital_routes.reverse_geocode",
            return_value={"district": "Mysuru", "city": "Mysuru", "state": "Karnataka", "pincode": "570001"},
        ):
            response = self.client.get(
                "/api/hospitals/location?latitude=12.3&longitude=76.6",
                headers=self.user_headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["district"], "Mysuru")

    def test_admin_create_edit_delete_and_csv_import_export(self):
        payload = self.facility(external_id=None)
        payload.pop("source")
        created = self.client.post(
            "/api/hospitals/manage",
            json=payload,
            headers=self.admin_headers,
        )
        self.assertEqual(created.status_code, 201)
        hospital_id = created.json["id"]
        edited = self.client.put(
            f"/api/hospitals/manage/{hospital_id}",
            json={"name": "Updated Mysuru Hospital", "latitude": 12.31, "longitude": 76.66},
            headers=self.admin_headers,
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json["name"], "Updated Mysuru Hospital")

        csv_file = io.BytesIO(
            b"name,latitude,longitude,city,hospital_type\n"
            b"CSV Clinic,12.4,76.7,Mysuru,Clinic\n"
        )
        imported = self.client.post(
            "/api/hospitals/manage/import",
            data={"file": (csv_file, "facilities.csv")},
            headers=self.admin_headers,
            content_type="multipart/form-data",
        )
        exported = self.client.get(
            "/api/hospitals/manage/export",
            headers=self.admin_headers,
        )
        stats = self.client.get(
            "/api/hospitals/manage/statistics",
            headers=self.admin_headers,
        )
        deleted = self.client.delete(
            f"/api/hospitals/manage/{hospital_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(imported.status_code, 201)
        self.assertEqual(imported.json["imported"], 1)
        self.assertEqual(exported.status_code, 200)
        self.assertIn("CSV Clinic", exported.get_data(as_text=True))
        self.assertEqual(stats.json["total"], 2)
        self.assertEqual(deleted.status_code, 200)

    def test_admin_rejects_invalid_coordinates_and_csv_headers(self):
        invalid = self.client.post(
            "/api/hospitals/manage",
            json={"name": "Invalid", "latitude": 100, "longitude": 0},
            headers=self.admin_headers,
        )
        bad_csv = self.client.post(
            "/api/hospitals/manage/import",
            data={"file": (io.BytesIO(b"title,address\nHospital,Here\n"), "bad.csv")},
            headers=self.admin_headers,
            content_type="multipart/form-data",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(bad_csv.status_code, 400)

    def test_location_provider_failure_returns_service_unavailable(self):
        from backend.app.services.hospital_service import HospitalProviderError

        with patch(
            "backend.app.routes.hospital_routes.geocode",
            side_effect=HospitalProviderError("Location service down."),
        ):
            response = self.client.get(
                "/api/hospitals/nearby?location=Mysuru",
                headers=self.user_headers,
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"], "hospital_provider_unavailable")


if __name__ == "__main__":
    unittest.main()
