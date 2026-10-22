import unittest
import re
from datetime import timedelta
from unittest.mock import patch

from backend.app import create_app
from backend.app.extensions import bcrypt, db
from backend.app.models import (
    EmailVerificationToken,
    PasswordResetToken,
    User,
    UserPreference,
    utcnow,
)


class AuthTestConfig:
    TESTING = True
    LOCAL_DEMO_MODE = True
    SECRET_KEY = "auth-test-secret-key-at-least-32-bytes"
    JWT_SECRET_KEY = "auth-test-jwt-secret-key-at-least-32"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    MAIL_SERVER = "smtp.test"
    MAIL_PORT = 587
    MAIL_USERNAME = "smtp-user@example.test"
    MAIL_PASSWORD = "smtp-test-password"
    MAIL_DEFAULT_SENDER = "noreply@example.test"
    MAIL_USE_TLS = True


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(AuthTestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()
        self.send_email_patcher = patch("backend.app.routes.auth.send_email")
        self.send_email = self.send_email_patcher.start()

    def tearDown(self):
        self.send_email_patcher.stop()
        db.session.remove()
        db.drop_all()
        self.context.pop()

    @staticmethod
    def registration_payload():
        return {
            "full_name": "Test User",
            "email": "test@example.test",
            "phone": "+1 555 555 1234",
            "district": "Mysuru",
            "state": "Karnataka",
            "password": "StrongPass1!",
            "confirm_password": "StrongPass1!",
        }

    def _register(self, payload=None):
        payload = payload or self.registration_payload()
        response = self.client.post(
            "/api/auth/register", json=payload
        )
        self.assertEqual(response.status_code, 201)
        token = self._verification_token()
        verified = self.client.post(
            "/api/auth/email-verification", json={"token": token}
        )
        self.assertEqual(verified.status_code, 200)
        login = self.client.post(
            "/api/auth/login",
            json={"email": payload["email"], "password": payload["password"]},
        )
        self.assertEqual(login.status_code, 200)
        return login.json

    def _verification_token(self):
        email_body = self.send_email.call_args.args[2]
        match = re.search(r"/verify-email\?token=([^\s]+)", email_body)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_registration_requires_verification_before_login(self):
        response = self.client.post(
            "/api/auth/register", json=self.registration_payload()
        )
        self.assertEqual(response.status_code, 201)
        self.send_email.assert_called_once()
        self.assertEqual(self.send_email.call_args.args[0], "test@example.test")
        self.assertIn(
            "http://localhost:5173/verify-email?token=",
            self.send_email.call_args.args[2],
        )
        self.assertNotIn("access_token", response.json)
        self.assertNotIn("refresh_token", response.json)
        self.assertFalse(response.json["user"]["is_verified"])

        user = User.query.filter_by(email="test@example.test").one()
        token_record = EmailVerificationToken.query.filter_by(user_id=user.id).one()
        token = self._verification_token()
        self.assertNotEqual(token_record.token_hash, token)
        self.assertEqual(
            self.client.post(
                "/api/auth/login",
                json={"email": user.email, "password": "StrongPass1!"},
            ).status_code,
            403,
        )

        tampered = self.client.post(
            "/api/auth/email-verification", json={"token": token + "tampered"}
        )
        self.assertEqual(tampered.status_code, 400)
        self.assertFalse(user.is_verified)

        verified = self.client.post(
            "/api/auth/email-verification", json={"token": token}
        )
        self.assertEqual(verified.status_code, 200)
        self.assertTrue(user.is_verified)
        self.assertIsNone(
            EmailVerificationToken.query.filter_by(user_id=user.id).first()
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/email-verification", json={"token": token}
            ).status_code,
            400,
        )
        login = self.client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "StrongPass1!"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json["access_token"])

    def test_expired_verification_token_is_rejected_and_can_be_resent(self):
        response = self.client.post(
            "/api/auth/register", json=self.registration_payload()
        )
        self.assertEqual(response.status_code, 201)
        user = User.query.filter_by(email="test@example.test").one()
        old_token = self._verification_token()
        record = EmailVerificationToken.query.filter_by(user_id=user.id).one()
        record.expires_at = utcnow() - timedelta(seconds=1)
        db.session.commit()

        expired = self.client.post(
            "/api/auth/email-verification", json={"token": old_token}
        )
        self.assertEqual(expired.status_code, 400)
        self.assertIn("expired", expired.json["message"].lower())
        self.assertFalse(user.is_verified)

        resent = self.client.post(
            "/api/auth/email-verification/resend",
            json={"email": user.email},
            environ_base={"REMOTE_ADDR": "192.0.2.21"},
        )
        self.assertEqual(resent.status_code, 202)
        new_token = self._verification_token()
        self.assertNotEqual(old_token, new_token)
        verified = self.client.post(
            "/api/auth/email-verification", json={"token": new_token}
        )
        self.assertEqual(verified.status_code, 200)

    def test_resend_is_enumeration_resistant_and_rotates_tokens(self):
        self.client.post("/api/auth/register", json=self.registration_payload())
        old_token = self._verification_token()
        existing = self.client.post(
            "/api/auth/email-verification/resend",
            json={"email": "test@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.22"},
        )
        unknown = self.client.post(
            "/api/auth/email-verification/resend",
            json={"email": "unknown@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.23"},
        )
        self.assertEqual(existing.status_code, 202)
        self.assertEqual(existing.json, unknown.json)
        new_token = self._verification_token()
        self.assertNotEqual(old_token, new_token)
        self.assertEqual(
            self.client.post(
                "/api/auth/email-verification", json={"token": old_token}
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                "/api/auth/email-verification", json={"token": new_token}
            ).status_code,
            200,
        )

    def test_registration_requires_email_delivery_configuration(self):
        self.app.config["MAIL_SERVER"] = ""
        self.app.config["LOCAL_DEMO_MODE"] = False
        response = self.client.post(
            "/api/auth/register", json=self.registration_payload()
        )
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(User.query.filter_by(email="test@example.test").first())

    def test_debug_registration_without_smtp_auto_verifies_and_allows_login(self):
        self.app.config["DEBUG"] = True
        for setting in (
            "MAIL_SERVER",
            "MAIL_USERNAME",
            "MAIL_PASSWORD",
            "MAIL_DEFAULT_SENDER",
        ):
            self.app.config[setting] = ""

        response = self.client.post(
            "/api/auth/register", json=self.registration_payload()
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json["user"]["is_verified"])
        self.assertIn("Local demo mode verified", response.json["message"])
        self.send_email.assert_not_called()
        self.assertIsNone(
            EmailVerificationToken.query.filter_by(
                user_id=response.json["user"]["id"]
            ).first()
        )

        login = self.client.post(
            "/api/auth/login",
            json={
                "email": "test@example.test",
                "password": "StrongPass1!",
            },
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json["access_token"])

    def test_registration_auto_verifies_when_smtp_delivery_fails_in_demo_mode(self):
        self.send_email.side_effect = RuntimeError("SMTP unavailable")
        response = self.client.post(
            "/api/auth/register", json=self.registration_payload()
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json["user"]["is_verified"])
        self.assertIn("Local demo mode verified", response.json["message"])
        user = User.query.filter_by(email="test@example.test").one()
        self.assertIsNone(
            EmailVerificationToken.query.filter_by(user_id=user.id).first()
        )
        login = self.client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "StrongPass1!"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json["access_token"])

    def test_registration_hashes_password_and_rejects_duplicate_email(self):
        response = self.client.post(
            "/api/auth/register", json=self.registration_payload()
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["user"]["role"], "user")
        self.assertNotIn("password_hash", response.json["user"])
        self.assertNotIn("password", response.json)

        user = User.query.filter_by(email="test@example.test").one()
        self.assertNotEqual(user.password_hash, "StrongPass1!")
        duplicate = self.client.post(
            "/api/auth/register", json=self.registration_payload()
        )
        self.assertEqual(duplicate.status_code, 409)

    def test_password_reset_uses_expiring_single_use_token(self):
        self._register()
        requested = self.client.post(
            "/api/auth/password-reset-request",
            json={"email": "test@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.10"},
        )
        self.assertEqual(requested.status_code, 202)
        self.assertIn("If an account exists", requested.json["message"])
        email_body = self.send_email.call_args.args[2]
        token = re.search(r"token=([^\s]+)", email_body).group(1)
        self.assertIn("http://localhost:5173/reset-password?token=", email_body)
        user = User.query.filter_by(email="test@example.test").one()
        token_record = PasswordResetToken.query.filter_by(user_id=user.id).one()
        self.assertNotEqual(token_record.token_hash, token)

        changed = self.client.post(
            "/api/auth/password-reset",
            json={
                "token": token,
                "password": "NewStrongPass2!",
                "confirm_password": "NewStrongPass2!",
            },
        )
        self.assertEqual(changed.status_code, 200)
        self.assertTrue(bcrypt.check_password_hash(user.password_hash, "NewStrongPass2!"))
        self.assertIsNone(
            PasswordResetToken.query.filter_by(user_id=user.id).first()
        )
        reused = self.client.post(
            "/api/auth/password-reset",
            json={
                "token": token,
                "password": "AnotherStrong3!",
                "confirm_password": "AnotherStrong3!",
            },
        )
        self.assertEqual(reused.status_code, 400)
        self.assertEqual(
            self.client.post(
                "/api/auth/login",
                json={"email": user.email, "password": "StrongPass1!"},
            ).status_code,
            401,
        )
        login = self.client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "NewStrongPass2!"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json["access_token"])

    def test_password_reset_rejects_tampered_and_expired_tokens(self):
        self._register()
        requested = self.client.post(
            "/api/auth/password-reset-request",
            json={"email": "test@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.12"},
        )
        self.assertEqual(requested.status_code, 202)
        token = re.search(
            r"token=([^\s]+)", self.send_email.call_args.args[2]
        ).group(1)
        payload = {
            "token": token + "tampered",
            "password": "NewStrongPass2!",
            "confirm_password": "NewStrongPass2!",
        }
        tampered = self.client.post("/api/auth/password-reset", json=payload)
        self.assertEqual(tampered.status_code, 400)
        self.assertIn("invalid", tampered.json["message"].lower())

        user = User.query.filter_by(email="test@example.test").one()
        record = PasswordResetToken.query.filter_by(user_id=user.id).one()
        record.expires_at = utcnow() - timedelta(seconds=1)
        db.session.commit()
        payload["token"] = token
        expired = self.client.post("/api/auth/password-reset", json=payload)
        self.assertEqual(expired.status_code, 400)
        self.assertIn("expired", expired.json["message"].lower())
        self.assertIsNone(
            PasswordResetToken.query.filter_by(user_id=user.id).first()
        )

    def test_password_change_invalidates_pending_reset_token(self):
        registered = self._register()
        self.client.post(
            "/api/auth/password-reset-request",
            json={"email": "test@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.13"},
        )
        token = re.search(
            r"token=([^\s]+)", self.send_email.call_args.args[2]
        ).group(1)
        changed = self.client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {registered['access_token']}"},
            json={
                "current_password": "StrongPass1!",
                "new_password": "NewStrongPass2!",
                "confirm_password": "NewStrongPass2!",
            },
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(
            self.client.post(
                "/api/auth/password-reset",
                json={
                    "token": token,
                    "password": "AnotherStrong3!",
                    "confirm_password": "AnotherStrong3!",
                },
            ).status_code,
            400,
        )

    def test_password_reset_response_does_not_reveal_unknown_accounts(self):
        self._register()
        existing = self.client.post(
            "/api/auth/password-reset-request",
            json={"email": "test@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.14"},
        )
        unknown = self.client.post(
            "/api/auth/password-reset-request",
            json={"email": "unknown@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.15"},
        )
        self.assertEqual(existing.status_code, 202)
        self.assertEqual(unknown.status_code, 202)
        self.assertEqual(existing.json, unknown.json)
        self.assertEqual(self.send_email.call_count, 3)

    def test_password_recovery_reports_missing_email_configuration(self):
        self.app.config["MAIL_SERVER"] = ""
        self.app.config["LOCAL_DEMO_MODE"] = False
        response = self.client.post(
            "/api/auth/password-reset-request",
            json={"email": "test@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.11"},
        )
        self.assertEqual(response.status_code, 503)

    def test_local_demo_password_reset_works_without_smtp(self):
        self._register()
        for setting in (
            "MAIL_SERVER",
            "MAIL_USERNAME",
            "MAIL_PASSWORD",
            "MAIL_DEFAULT_SENDER",
        ):
            self.app.config[setting] = ""

        requested = self.client.post(
            "/api/auth/password-reset-request",
            json={"email": "test@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.16"},
        )
        self.assertEqual(requested.status_code, 202)
        self.assertIn("demo_reset_url", requested.json)
        token = re.search(r"token=([^\s]+)", requested.json["demo_reset_url"]).group(1)

        changed = self.client.post(
            "/api/auth/password-reset",
            json={
                "token": token,
                "password": "DemoResetPass2!",
                "confirm_password": "DemoResetPass2!",
            },
        )
        self.assertEqual(changed.status_code, 200)
        login = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.test", "password": "DemoResetPass2!"},
        )
        self.assertEqual(login.status_code, 200)

    def test_local_demo_password_reset_falls_back_when_smtp_fails(self):
        self._register()
        self.send_email.side_effect = RuntimeError("SMTP unavailable")
        requested = self.client.post(
            "/api/auth/password-reset-request",
            json={"email": "test@example.test"},
            environ_base={"REMOTE_ADDR": "192.0.2.17"},
        )

        self.assertEqual(requested.status_code, 202)
        self.assertIn("demo_reset_url", requested.json)
        self.assertIn("Email delivery is unavailable", requested.json["message"])

    def test_registration_and_login_validation(self):
        payload = self.registration_payload()
        payload["password"] = "weak"
        payload["confirm_password"] = "weak"
        invalid = self.client.post("/api/auth/register", json=payload)
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("password", invalid.json["errors"])

        self._register()
        invalid_login = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.test", "password": "WrongPass1!"},
        )
        self.assertEqual(invalid_login.status_code, 401)

        login = self.client.post(
            "/api/auth/login",
            json={"email": " TEST@example.test ", "password": "StrongPass1!"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json["access_token"])
        self.assertTrue(login.json["refresh_token"])
        self.assertEqual(login.json["user"]["email"], "test@example.test")

        access_headers = {
            "Authorization": f"Bearer {login.json['access_token']}"
        }
        profile = self.client.get("/api/auth/profile", headers=access_headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json["user"]["email"], "test@example.test")
        self.assertTrue(profile.json["user"]["is_verified"])

        refresh_headers = {
            "Authorization": f"Bearer {login.json['refresh_token']}"
        }
        refreshed = self.client.post("/api/auth/refresh", headers=refresh_headers)
        self.assertEqual(refreshed.status_code, 200)
        self.assertTrue(refreshed.json["access_token"])
        self.assertTrue(refreshed.json["refresh_token"])
        self.assertNotEqual(refreshed.json["refresh_token"], login.json["refresh_token"])

        refreshed_profile = self.client.get(
            "/api/auth/profile",
            headers={
                "Authorization": f"Bearer {refreshed.json['access_token']}"
            },
        )
        self.assertEqual(refreshed_profile.status_code, 200)

        reused_refresh = self.client.post(
            "/api/auth/refresh", headers=refresh_headers
        )
        self.assertEqual(reused_refresh.status_code, 401)

        rotated_refresh = self.client.post(
            "/api/auth/refresh",
            headers={
                "Authorization": f"Bearer {refreshed.json['refresh_token']}"
            },
        )
        self.assertEqual(rotated_refresh.status_code, 200)

    def test_profile_is_authenticated_and_email_cannot_be_changed(self):
        result = self._register()
        headers = {"Authorization": f"Bearer {result['access_token']}"}
        unauthenticated = self.client.get("/api/auth/profile")
        self.assertEqual(unauthenticated.status_code, 401)

        profile = self.client.get("/api/auth/profile", headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json["user"]["email"], "test@example.test")
        self.assertTrue(profile.json["user"]["is_verified"])

        update = self.client.put(
            "/api/auth/profile",
            json={"full_name": "Updated User"},
            headers=headers,
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.json["user"]["full_name"], "Updated User")

        email_update = self.client.put(
            "/api/auth/profile",
            json={"email": "new@example.test"},
            headers=headers,
        )
        self.assertEqual(email_update.status_code, 400)
        self.assertIn("email", email_update.json["errors"])

    def test_settings_are_authenticated_validated_and_persisted_per_user(self):
        registered = self._register()
        headers = {"Authorization": f"Bearer {registered['access_token']}"}

        unauthorized = self.client.get("/api/auth/settings")
        self.assertEqual(unauthorized.status_code, 401)

        defaults = self.client.get("/api/auth/settings", headers=headers)
        self.assertEqual(defaults.status_code, 200)
        self.assertEqual(
            defaults.json["preferences"],
            {"alerts": True, "weekly_summary": False, "dark_mode": False},
        )
        self.assertEqual(UserPreference.query.count(), 0)

        saved = self.client.put(
            "/api/auth/settings",
            json={"alerts": False, "weekly_summary": True, "dark_mode": True},
            headers=headers,
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(
            saved.json["preferences"],
            {"alerts": False, "weekly_summary": True, "dark_mode": True},
        )
        self.assertEqual(UserPreference.query.count(), 1)

        loaded = self.client.get("/api/auth/settings", headers=headers)
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json["preferences"], saved.json["preferences"])

        invalid = self.client.put(
            "/api/auth/settings",
            json={"alerts": "false", "weekly_summary": True, "dark_mode": True},
            headers=headers,
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn("alerts", invalid.json["errors"])
        self.assertEqual(
            self.client.get("/api/auth/settings", headers=headers).json["preferences"],
            saved.json["preferences"],
        )

        unknown = self.client.put(
            "/api/auth/settings",
            json={
                "alerts": False,
                "weekly_summary": True,
                "dark_mode": True,
                "email": "other@example.test",
            },
            headers=headers,
        )
        self.assertEqual(unknown.status_code, 400)
        self.assertIn("email", unknown.json["errors"])

        other_user = self.registration_payload()
        other_user["email"] = "other@example.test"
        other = self._register(other_user)
        other_headers = {"Authorization": f"Bearer {other['access_token']}"}
        other_loaded = self.client.get("/api/auth/settings", headers=other_headers)
        self.assertEqual(
            other_loaded.json["preferences"],
            {"alerts": True, "weekly_summary": False, "dark_mode": False},
        )

    def test_password_change_requires_current_password_and_updates_login(self):
        result = self._register()
        headers = {"Authorization": f"Bearer {result['access_token']}"}
        incorrect_current_password = self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": "WrongPass1!",
                "new_password": "NewStrongPass2!",
                "confirm_password": "NewStrongPass2!",
            },
            headers=headers,
        )
        self.assertEqual(incorrect_current_password.status_code, 400)

        changed = self.client.post(
            "/api/auth/change-password",
            json={
                "current_password": "StrongPass1!",
                "new_password": "NewStrongPass2!",
                "confirm_password": "NewStrongPass2!",
            },
            headers=headers,
        )
        self.assertEqual(changed.status_code, 200)

        old_password_login = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.test", "password": "StrongPass1!"},
        )
        new_password_login = self.client.post(
            "/api/auth/login",
            json={"email": "test@example.test", "password": "NewStrongPass2!"},
        )
        self.assertEqual(old_password_login.status_code, 401)
        self.assertEqual(new_password_login.status_code, 200)

    def test_logout_revokes_access_and_refresh_tokens(self):
        result = self._register()
        headers = {"Authorization": f"Bearer {result['access_token']}"}
        logout = self.client.post(
            "/api/auth/logout",
            json={"refresh_token": result["refresh_token"]},
            headers=headers,
        )
        self.assertEqual(logout.status_code, 200)
        self.assertEqual(
            self.client.get("/api/auth/profile", headers=headers).status_code, 401
        )

        refresh = self.client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {result['refresh_token']}"},
        )
        self.assertEqual(refresh.status_code, 401)


if __name__ == "__main__":
    unittest.main()
