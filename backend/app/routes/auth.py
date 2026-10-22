import hashlib
import re
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_jwt_extended.exceptions import JWTExtendedException
from sqlalchemy.exc import IntegrityError

from ..extensions import bcrypt, db
from ..models import (
    EmailVerificationToken,
    PasswordResetToken,
    TokenBlocklist,
    User,
    UserPreference,
    utcnow,
)
from ..services.email import email_is_configured, public_request_allowed, send_email

auth_blueprint = Blueprint("auth", __name__)

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_PATTERN = re.compile(r"^[0-9+().\-\s]+$")
_REGISTRATION_FIELDS = {
    "full_name",
    "email",
    "password",
    "confirm_password",
    "phone",
    "district",
    "state",
}
_PROFILE_FIELDS = {"full_name", "phone", "district", "state"}
_SETTINGS_FIELDS = {"alerts", "weekly_summary", "dark_mode"}
_DEFAULT_SETTINGS = {
    "alerts": True,
    "weekly_summary": False,
    "dark_mode": False,
}
_PASSWORD_RESET_MAX_AGE_SECONDS = 3600
_EMAIL_VERIFICATION_MAX_AGE_SECONDS = 24 * 60 * 60


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_verification_token(user):
    token = secrets.token_urlsafe(32)
    token_record = EmailVerificationToken.query.filter_by(user_id=user.id).first()
    if token_record is None:
        token_record = EmailVerificationToken(user_id=user.id)
        db.session.add(token_record)
    token_record.token_hash = _token_hash(token)
    token_record.expires_at = utcnow() + timedelta(
        seconds=_EMAIL_VERIFICATION_MAX_AGE_SECONDS
    )
    db.session.commit()
    return token


def _send_verification_email(user):
    token = _issue_verification_token(user)
    frontend_origin = current_app.config["FRONTEND_ORIGIN"].split(",")[0].strip().rstrip("/")
    verification_url = f"{frontend_origin}/verify-email?token={quote(token, safe='')}"
    send_email(
        user.email,
        "Verify your DengueWatch account",
        "Use the link below within 24 hours to verify your email address. "
        "If you did not create this account, you can ignore this message.\n\n"
        f"{verification_url}\n",
    )


def _validation_error(errors):
    return jsonify({"message": "Validation failed.", "errors": errors}), 400


def _json_object():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _valid_password(password):
    if not isinstance(password, str) or len(password) < 8:
        return False
    try:
        if len(password.encode("utf-8")) > 72:
            return False
    except UnicodeEncodeError:
        return False
    return (
        any(char.islower() for char in password)
        and any(char.isupper() for char in password)
        and any(char.isdigit() for char in password)
        and any(not char.isalnum() for char in password)
    )


def _issue_password_reset_token(user):
    token = secrets.token_urlsafe(32)
    token_record = PasswordResetToken.query.filter_by(user_id=user.id).first()
    if token_record is None:
        token_record = PasswordResetToken(user_id=user.id)
        db.session.add(token_record)
    token_record.token_hash = _token_hash(token)
    token_record.expires_at = utcnow() + timedelta(
        seconds=_PASSWORD_RESET_MAX_AGE_SECONDS
    )
    db.session.commit()
    return token


def _password_fits_bcrypt(password):
    try:
        return len(password.encode("utf-8")) <= 72
    except UnicodeEncodeError:
        return False


def _user_from_identity():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)


def _serialize_datetime(value):
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.isoformat()


def _serialize_user(user):
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "district": user.district,
        "state": user.state,
        "role": user.role,
        "is_verified": user.is_verified,
        "created_at": _serialize_datetime(user.created_at),
        "updated_at": _serialize_datetime(user.updated_at),
    }


def _tokens_for(user):
    identity = str(user.id)
    return {
        "access_token": create_access_token(identity=identity),
        "refresh_token": create_refresh_token(identity=identity),
    }


def _revoke_token(payload):
    expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc)
    db.session.add(
        TokenBlocklist(
            jti=payload["jti"],
            token_type=payload["type"],
            user_id=int(payload["sub"]),
            expires_at=expires_at,
        )
    )


def _serialize_settings(settings):
    if settings is None:
        return dict(_DEFAULT_SETTINGS)
    return {
        "alerts": settings.alerts,
        "weekly_summary": settings.weekly_summary,
        "dark_mode": settings.dark_mode,
    }


@auth_blueprint.post("/auth/register")
def register():
    data = _json_object()
    if data is None:
        return _validation_error({"body": "A JSON object is required."})

    errors = {}
    for field in sorted(_REGISTRATION_FIELDS):
        if field not in data:
            errors[field] = "This field is required."

    full_name = data.get("full_name")
    if "full_name" in data:
        if not isinstance(full_name, str) or not full_name.strip():
            errors["full_name"] = "Full name is required."
        elif len(full_name.strip()) > 150:
            errors["full_name"] = "Full name must be 150 characters or fewer."
        elif len(full_name.strip()) < 2:
            errors["full_name"] = "Full name must be at least 2 characters."

    email = data.get("email")
    normalized_email = email.strip().lower() if isinstance(email, str) else ""
    if "email" in data:
        if not isinstance(email, str) or not normalized_email:
            errors["email"] = "A valid email address is required."
        elif len(normalized_email) > 254 or not _EMAIL_PATTERN.fullmatch(normalized_email):
            errors["email"] = "A valid email address is required."

    phone = data.get("phone")
    if "phone" in data:
        if not isinstance(phone, str) or not phone.strip():
            errors["phone"] = "Phone is required."
        else:
            digits = sum(char.isdigit() for char in phone)
            if (
                len(phone.strip()) > 32
                or not _PHONE_PATTERN.fullmatch(phone.strip())
                or not 7 <= digits <= 15
            ):
                errors["phone"] = "Enter a valid phone number."

    for field in ("district", "state"):
        value = data.get(field)
        if field in data:
            if not isinstance(value, str) or not value.strip():
                errors[field] = f"{field.title()} is required."
            elif len(value.strip()) > 100:
                errors[field] = f"{field.title()} must be 100 characters or fewer."

    password = data.get("password")
    if "password" in data and not _valid_password(password):
        errors["password"] = (
            "Password must be 8–72 UTF-8 bytes and include lowercase, uppercase, "
            "a number, and a special character."
        )
    if "confirm_password" in data:
        if not isinstance(data.get("confirm_password"), str):
            errors["confirm_password"] = "Password confirmation is required."
        elif password != data.get("confirm_password"):
            errors["confirm_password"] = "Passwords do not match."

    for field in data.keys() - _REGISTRATION_FIELDS:
        errors[field] = "This field is not allowed."
    if errors:
        return _validation_error(errors)

    mail_configured = email_is_configured()
    local_demo_mode = bool(current_app.config.get("LOCAL_DEMO_MODE", False))
    local_demo_auto_verify = local_demo_mode and not mail_configured
    if not mail_configured and not local_demo_mode:
        return jsonify({"message": "Account registration email is not configured."}), 503

    user = User(
        full_name=full_name.strip(),
        email=normalized_email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        phone=phone.strip(),
        district=data["district"].strip(),
        state=data["state"].strip(),
        role="user",
        is_verified=local_demo_auto_verify,
    )
    if User.query.filter_by(email=normalized_email).first() is not None:
        return (
            jsonify(
                {
                    "message": "An account with this email already exists.",
                    "errors": {"email": "Email is already registered."},
                }
            ),
            409,
        )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if User.query.filter_by(email=normalized_email).first() is not None:
            return (
                jsonify(
                    {
                        "message": "An account with this email already exists.",
                        "errors": {"email": "Email is already registered."},
                    }
                ),
                409,
            )
        raise

    if mail_configured:
        try:
            _send_verification_email(user)
        except (OSError, RuntimeError, smtplib.SMTPException):
            current_app.logger.exception("Could not send account verification email")
            if not local_demo_mode:
                return (
                    jsonify(
                        {
                            "message": "Your account was created, but the verification email could not be sent. Request another verification email to continue.",
                            "error": "verification_email_failed",
                            "account_created": True,
                        }
                    ),
                    503,
                )
            user.is_verified = True
            verification_token = EmailVerificationToken.query.filter_by(
                user_id=user.id
            ).first()
            if verification_token is not None:
                db.session.delete(verification_token)
            db.session.commit()
            local_demo_auto_verify = True
    else:
        current_app.logger.info(
            "Email verification skipped for %s because local demo mode is enabled "
            "and SMTP is not configured.",
            normalized_email,
        )

    return (
        jsonify(
            {
                "message": (
                    "Registration successful. Local demo mode verified your account; "
                    "you can now sign in."
                    if local_demo_auto_verify
                    else "Registration successful. Check your email for a verification link."
                ),
                "user": _serialize_user(user),
            }
        ),
        201,
    )


@auth_blueprint.post("/auth/email-verification")
def verify_email():
    data = _json_object()
    if data is None or set(data) != {"token"}:
        return _validation_error({"token": "A verification token is required."})
    token = data.get("token")
    if not isinstance(token, str) or not token or len(token) > 256:
        return _validation_error({"token": "A valid verification token is required."})
    if not public_request_allowed():
        return jsonify({"message": "Too many requests. Try again later."}), 429

    token_record = EmailVerificationToken.query.filter_by(
        token_hash=_token_hash(token)
    ).first()
    if token_record is None:
        return jsonify({"message": "Verification link is invalid or has already been used."}), 400

    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= utcnow():
        db.session.delete(token_record)
        db.session.commit()
        return jsonify({"message": "Verification link has expired. Request a new link."}), 400

    user = db.session.get(User, token_record.user_id)
    if user is None:
        db.session.delete(token_record)
        db.session.commit()
        return jsonify({"message": "Verification link is invalid or has already been used."}), 400

    user.is_verified = True
    db.session.delete(token_record)
    db.session.commit()
    return jsonify({"message": "Email verified. You can now sign in."}), 200


@auth_blueprint.post("/auth/email-verification/resend")
def resend_email_verification():
    data = _json_object()
    if data is None or set(data) != {"email"}:
        return _validation_error({"email": "A valid email address is required."})
    email = data.get("email")
    normalized_email = email.strip().lower() if isinstance(email, str) else ""
    if (
        not normalized_email
        or len(normalized_email) > 254
        or not _EMAIL_PATTERN.fullmatch(normalized_email)
    ):
        return _validation_error({"email": "A valid email address is required."})
    if not public_request_allowed():
        return jsonify({"message": "Too many requests. Try again later."}), 429
    if not email_is_configured():
        return jsonify({"message": "Verification email delivery is not configured."}), 503

    generic_response = {
        "message": "If an unverified account exists for this address, a verification email has been sent."
    }
    user = User.query.filter_by(email=normalized_email).first()
    if user is None or user.is_verified:
        return jsonify(generic_response), 202

    try:
        _send_verification_email(user)
    except (OSError, RuntimeError, smtplib.SMTPException):
        current_app.logger.exception("Could not resend account verification email")
        return jsonify({"message": "Verification email could not be sent."}), 503
    return jsonify(generic_response), 202


@auth_blueprint.post("/auth/login")
def login():
    data = _json_object()
    if data is None:
        return _validation_error({"body": "A JSON object is required."})

    errors = {}
    email = data.get("email")
    password = data.get("password")
    normalized_email = email.strip().lower() if isinstance(email, str) else ""
    if not normalized_email or len(normalized_email) > 254 or not _EMAIL_PATTERN.fullmatch(normalized_email):
        errors["email"] = "A valid email address is required."
    if not isinstance(password, str) or not password:
        errors["password"] = "Password is required."
    elif not _password_fits_bcrypt(password):
        errors["password"] = "Password must not exceed 72 UTF-8 bytes."
    if data.keys() - {"email", "password"}:
        for field in data.keys() - {"email", "password"}:
            errors[field] = "This field is not allowed."
    if errors:
        return _validation_error(errors)

    user = User.query.filter_by(email=normalized_email).first()
    if user is None or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid email or password."}), 401
    if not user.is_verified:
        return (
            jsonify(
                {
                    "message": "Verify your email address before signing in.",
                    "error": "email_not_verified",
                }
            ),
            403,
        )

    return (
        jsonify(
            {
                "message": "Login successful.",
                "user": _serialize_user(user),
                **_tokens_for(user),
            }
        ),
        200,
    )


@auth_blueprint.post("/auth/password-reset-request")
def request_password_reset():
    data = _json_object()
    if data is None or set(data) != {"email"}:
        return _validation_error({"email": "A valid email address is required."})
    email = data.get("email")
    normalized_email = email.strip().lower() if isinstance(email, str) else ""
    if (
        not normalized_email
        or len(normalized_email) > 254
        or not _EMAIL_PATTERN.fullmatch(normalized_email)
    ):
        return _validation_error({"email": "A valid email address is required."})
    if not public_request_allowed():
        return jsonify({"message": "Too many requests. Try again later."}), 429
    local_demo_mode = bool(current_app.config.get("LOCAL_DEMO_MODE", False))
    mail_configured = email_is_configured()
    if not mail_configured and not local_demo_mode:
        return jsonify({"message": "Password recovery email is not configured."}), 503

    user = User.query.filter_by(email=normalized_email).first()
    token = (
        _issue_password_reset_token(user)
        if user is not None
        else secrets.token_urlsafe(32)
    )
    reset_url = current_app.config["FRONTEND_ORIGIN"].split(",")[0].strip().rstrip("/")
    reset_url = f"{reset_url}/reset-password?token={quote(token, safe='')}"
    if mail_configured:
        try:
            send_email(
                normalized_email,
                "Password reset request",
                "A password reset was requested for this address. If an account is "
                "registered, use the link below within one hour. If you did not request "
                "this, you can ignore this message.\n\n"
                f"{reset_url}\n",
            )
        except (OSError, RuntimeError, smtplib.SMTPException):
            current_app.logger.exception("Could not send password reset email")
            if not local_demo_mode:
                return jsonify({"message": "Password recovery email could not be sent."}), 503
            if user is not None:
                return jsonify(
                    {
                        "message": "Email delivery is unavailable. Use this local demo reset link.",
                        "demo_reset_url": reset_url,
                    }
                ), 202
            return jsonify(
                {"message": "If an account exists, password reset instructions are ready."}
            ), 202
    elif local_demo_mode and user is not None:
        current_app.logger.info(
            "Password reset link generated for local demo account user_id=%s",
            user.id,
        )
        return jsonify(
            {
                "message": "Email delivery is unavailable. Use this local demo reset link.",
                "demo_reset_url": reset_url,
            }
        ), 202
    else:
        current_app.logger.info(
            "Password reset requested for an unknown address in local demo mode."
        )
    return jsonify(
        {"message": "If an account exists, password reset instructions have been sent."}
    ), 202


@auth_blueprint.post("/auth/password-reset")
def reset_password():
    data = _json_object()
    if data is None or set(data) != {"token", "password", "confirm_password"}:
        return _validation_error({"body": "A reset token and matching passwords are required."})
    token = data.get("token")
    password = data.get("password")
    confirm_password = data.get("confirm_password")
    errors = {}
    if not isinstance(token, str) or not token or len(token) > 256:
        errors["token"] = "A password reset token is required."
    if not _valid_password(password):
        errors["password"] = (
            "Password must be 8–72 UTF-8 bytes and include lowercase, uppercase, "
            "a number, and a special character."
        )
    if not isinstance(confirm_password, str) or password != confirm_password:
        errors["confirm_password"] = "Passwords do not match."
    if errors:
        return _validation_error(errors)

    token_record = PasswordResetToken.query.filter_by(
        token_hash=_token_hash(token)
    ).first()
    if token_record is None:
        return jsonify({"message": "Password reset link is invalid or already used."}), 400
    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= utcnow():
        db.session.delete(token_record)
        db.session.commit()
        return jsonify({"message": "Password reset link has expired."}), 400

    user = db.session.get(User, token_record.user_id)
    if user is None:
        db.session.delete(token_record)
        db.session.commit()
        return jsonify({"message": "Password reset link is invalid or already used."}), 400
    user.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    db.session.delete(token_record)
    db.session.commit()
    return jsonify({"message": "Password reset successfully."}), 200


@auth_blueprint.get("/auth/profile")
@jwt_required()
def get_profile():
    user = _user_from_identity()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    return jsonify({"user": _serialize_user(user)}), 200


@auth_blueprint.put("/auth/profile")
@jwt_required()
def update_profile():
    user = _user_from_identity()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    data = _json_object()
    if data is None:
        return _validation_error({"body": "A JSON object is required."})
    if not data:
        return _validation_error({"body": "At least one profile field is required."})

    errors = {}
    for field in data.keys() - _PROFILE_FIELDS:
        if field == "email":
            errors[field] = "Email cannot be changed."
        else:
            errors[field] = "This field cannot be changed."

    for field, value in data.items():
        if field not in _PROFILE_FIELDS:
            continue
        if not isinstance(value, str) or not value.strip():
            errors[field] = f"{field.replace('_', ' ').title()} is required."
        elif field == "full_name" and len(value.strip()) > 150:
            errors[field] = "Full name must be 150 characters or fewer."
        elif field == "full_name" and len(value.strip()) < 2:
            errors[field] = "Full name must be at least 2 characters."
        elif field == "phone":
            digits = sum(char.isdigit() for char in value)
            if (
                len(value.strip()) > 32
                or not _PHONE_PATTERN.fullmatch(value.strip())
                or not 7 <= digits <= 15
            ):
                errors[field] = "Enter a valid phone number."
        elif field in {"district", "state"} and len(value.strip()) > 100:
            errors[field] = f"{field.title()} must be 100 characters or fewer."

    if errors:
        return _validation_error(errors)

    for field, value in data.items():
        setattr(user, field, value.strip())
    db.session.commit()
    return jsonify({"user": _serialize_user(user)}), 200


@auth_blueprint.get("/auth/settings")
@jwt_required()
def get_settings():
    user = _user_from_identity()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    settings = db.session.get(UserPreference, user.id)
    return jsonify({"preferences": _serialize_settings(settings)}), 200


@auth_blueprint.put("/auth/settings")
@jwt_required()
def update_settings():
    user = _user_from_identity()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    data = _json_object()
    if data is None:
        return _validation_error({"body": "A JSON object is required."})

    errors = {}
    for field in _SETTINGS_FIELDS - data.keys():
        errors[field] = "This preference is required."
    for field in data.keys() - _SETTINGS_FIELDS:
        errors[field] = "This preference is not allowed."
    for field in data.keys() & _SETTINGS_FIELDS:
        if not isinstance(data[field], bool):
            errors[field] = "This preference must be a boolean."
    if errors:
        return _validation_error(errors)

    settings = db.session.get(UserPreference, user.id)
    if settings is None:
        settings = UserPreference(user_id=user.id)
        db.session.add(settings)
    settings.alerts = data["alerts"]
    settings.weekly_summary = data["weekly_summary"]
    settings.dark_mode = data["dark_mode"]
    db.session.commit()
    return (
        jsonify(
            {
                "message": "Preferences saved.",
                "preferences": _serialize_settings(settings),
            }
        ),
        200,
    )


@auth_blueprint.post("/auth/logout")
@jwt_required()
def logout():
    user = _user_from_identity()
    if user is None:
        return jsonify({"message": "User not found."}), 401

    access_payload = get_jwt()
    refresh_token = _json_object()
    if refresh_token is not None:
        if set(refresh_token) != {"refresh_token"} or not isinstance(
            refresh_token.get("refresh_token"), str
        ):
            return _validation_error(
                {"refresh_token": "Only a valid refresh_token may be supplied."}
            )
        try:
            refresh_payload = decode_token(refresh_token["refresh_token"])
        except JWTExtendedException:
            return jsonify({"message": "Invalid refresh token."}), 400
        if (
            refresh_payload.get("type") != "refresh"
            or refresh_payload.get("sub") != str(user.id)
            or db.session.query(TokenBlocklist.id)
            .filter_by(jti=refresh_payload.get("jti"))
            .first()
            is not None
        ):
            return jsonify({"message": "Invalid refresh token."}), 400
        _revoke_token(refresh_payload)
    elif request.data:
        return jsonify({"message": "A JSON object is required."}), 400

    _revoke_token(access_payload)
    db.session.commit()
    return jsonify({"message": "Logout successful."}), 200


@auth_blueprint.post("/auth/refresh")
@jwt_required(refresh=True)
def refresh():
    user = _user_from_identity()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    if not user.is_verified:
        return jsonify({"message": "Email verification is required."}), 403
    _revoke_token(get_jwt())
    tokens = _tokens_for(user)
    db.session.commit()
    return jsonify({"message": "Token refreshed.", **tokens}), 200


@auth_blueprint.post("/auth/change-password")
@jwt_required()
def change_password():
    user = _user_from_identity()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    data = _json_object()
    if data is None:
        return _validation_error({"body": "A JSON object is required."})

    errors = {}
    for field in ("current_password", "new_password", "confirm_password"):
        if not isinstance(data.get(field), str) or not data[field]:
            errors[field] = "This field is required."
    current_password = data.get("current_password")
    if isinstance(current_password, str) and not _password_fits_bcrypt(current_password):
        errors["current_password"] = "Password must not exceed 72 UTF-8 bytes."
    for field in data.keys() - {"current_password", "new_password", "confirm_password"}:
        errors[field] = "This field is not allowed."
    if "new_password" in data and not _valid_password(data["new_password"]):
        errors["new_password"] = (
            "Password must be 8–72 UTF-8 bytes and include lowercase, uppercase, "
            "a number, and a special character."
        )
    if (
        isinstance(data.get("new_password"), str)
        and isinstance(data.get("confirm_password"), str)
        and data["new_password"] != data["confirm_password"]
    ):
        errors["confirm_password"] = "Passwords do not match."
    if errors:
        return _validation_error(errors)
    if not bcrypt.check_password_hash(user.password_hash, data["current_password"]):
        return jsonify({"message": "Current password is incorrect."}), 400
    if data["current_password"] == data["new_password"]:
        return _validation_error(
            {"new_password": "New password must differ from current password."}
        )

    user.password_hash = bcrypt.generate_password_hash(data["new_password"]).decode(
        "utf-8"
    )
    pending_reset = PasswordResetToken.query.filter_by(user_id=user.id).first()
    if pending_reset is not None:
        db.session.delete(pending_reset)
    db.session.commit()
    return jsonify({"message": "Password changed successfully."}), 200
