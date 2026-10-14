import unittest
from datetime import date

from flask_jwt_extended import create_access_token

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import EmergencyContact, PrescriptionRecord, User


class RecordsTestConfig:
    TESTING = True
    SECRET_KEY = "records-test-secret-key-at-least-32-bytes"
    JWT_SECRET_KEY = "records-test-jwt-secret-key-at-least-32"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class PatientRecordsApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(RecordsTestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = self._create_user("patient@example.test")
        self.other = self._create_user("other@example.test")
        self.client = self.app.test_client()
        self.headers = self._headers(self.user.id)
        self.other_headers = self._headers(self.other.id)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def _create_user(self, email):
        user = User(
            full_name="Patient User",
            email=email,
            password_hash="unused",
            phone="1234567890",
            district="Mysuru",
            state="Karnataka",
            role="user",
        )
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def _headers(user_id):
        token = create_access_token(identity=str(user_id))
        return {"Authorization": f"Bearer {token}"}

    def test_emergency_contact_crud_is_user_scoped(self):
        payload = {"name": "Emergency Contact", "phone": "+1 555 555 0000"}
        unauthenticated = self.client.get("/api/profile/emergency-contact")
        self.assertEqual(unauthenticated.status_code, 401)

        saved = self.client.put(
            "/api/profile/emergency-contact", json=payload, headers=self.headers
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json["contact"]["name"], payload["name"])
        self.assertEqual(
            self.client.get(
                "/api/profile/emergency-contact", headers=self.other_headers
            ).json["contact"],
            None,
        )
        updated = self.client.put(
            "/api/profile/emergency-contact",
            json={"name": "Updated Contact", "phone": "555 123 4567"},
            headers=self.headers,
        )
        self.assertEqual(updated.json["contact"]["name"], "Updated Contact")
        self.assertEqual(
            self.client.delete(
                "/api/profile/emergency-contact", headers=self.headers
            ).status_code,
            200,
        )
        self.assertEqual(EmergencyContact.query.count(), 0)

    def test_prescription_crud_is_user_scoped_and_does_not_generate_advice(self):
        payload = {
            "medication": "Clinician supplied entry",
            "dose": "as written on prescription",
            "instructions": "Transcribed instructions only",
            "prescriber": "Dr Example",
            "prescribed_date": "2026-10-01",
        }
        created = self.client.post(
            "/api/prescriptions", json=payload, headers=self.headers
        )
        self.assertEqual(created.status_code, 201)
        record_id = created.json["prescription"]["id"]
        self.assertEqual(created.json["prescription"]["prescribed_date"], "2026-10-01")
        self.assertEqual(
            self.client.get("/api/prescriptions", headers=self.other_headers).json[
                "prescriptions"
            ],
            [],
        )
        self.assertEqual(
            self.client.put(
                f"/api/prescriptions/{record_id}",
                json={**payload, "medication": "Edited clinician entry"},
                headers=self.other_headers,
            ).status_code,
            404,
        )
        updated = self.client.put(
            f"/api/prescriptions/{record_id}",
            json={**payload, "medication": "Edited clinician entry"},
            headers=self.headers,
        )
        self.assertEqual(
            updated.json["prescription"]["medication"], "Edited clinician entry"
        )
        self.assertEqual(
            self.client.delete(
                f"/api/prescriptions/{record_id}", headers=self.headers
            ).status_code,
            200,
        )
        self.assertEqual(PrescriptionRecord.query.count(), 0)
        self.assertEqual(date.fromisoformat(payload["prescribed_date"]).isoformat(), "2026-10-01")

    def test_rejects_invalid_contact_and_prescription_payloads(self):
        invalid_contact = self.client.put(
            "/api/profile/emergency-contact",
            json={"name": "Contact", "phone": "12"},
            headers=self.headers,
        )
        self.assertEqual(invalid_contact.status_code, 400)
        invalid_prescription = self.client.post(
            "/api/prescriptions",
            json={"medication": "Example", "prescriber": "Clinician"},
            headers=self.headers,
        )
        self.assertEqual(invalid_prescription.status_code, 400)
        self.assertIn("prescribed_date", invalid_prescription.json["errors"])


if __name__ == "__main__":
    unittest.main()
