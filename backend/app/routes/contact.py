import re
import smtplib

from flask import Blueprint, current_app, jsonify, request

from ..services.email import email_is_configured, public_request_allowed, send_email

contact_blueprint = Blueprint("contact", __name__)
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@contact_blueprint.post("/contact")
def submit_contact_message():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"name", "email", "message"}:
        return jsonify({"message": "Name, email, and message are required."}), 400

    name = data["name"].strip() if isinstance(data["name"], str) else ""
    email = data["email"].strip().lower() if isinstance(data["email"], str) else ""
    message = data["message"].strip() if isinstance(data["message"], str) else ""
    errors = {}
    if not name or len(name) > 100:
        errors["name"] = "Name must be between 1 and 100 characters."
    if not email or len(email) > 254 or not _EMAIL_PATTERN.fullmatch(email):
        errors["email"] = "A valid email address is required."
    if not message or len(message) > 5000:
        errors["message"] = "Message must be between 1 and 5000 characters."
    if errors:
        return jsonify({"message": "Validation failed.", "errors": errors}), 400
    if not public_request_allowed():
        return jsonify({"message": "Too many requests. Try again later."}), 429
    if not email_is_configured("CONTACT_EMAIL"):
        return jsonify({"message": "Contact message delivery is not configured."}), 503

    try:
        send_email(
            current_app.config["CONTACT_EMAIL"],
            f"Website contact message from {name}",
            f"Name: {name}\nEmail: {email}\n\n{message}\n",
        )
    except (OSError, RuntimeError, smtplib.SMTPException):
        current_app.logger.exception("Could not send contact form message")
        return jsonify({"message": "Contact message could not be delivered."}), 503
    return jsonify({"message": "Your message has been sent."}), 202
