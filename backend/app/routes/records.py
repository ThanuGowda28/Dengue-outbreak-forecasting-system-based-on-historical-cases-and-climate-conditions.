import re
from datetime import date

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import EmergencyContact, PrescriptionRecord, User

records_blueprint = Blueprint("records", __name__)
_PHONE_PATTERN = re.compile(r"^[0-9+().\-\s]+$")


def _current_user():
    try:
        return db.session.get(User, int(get_jwt_identity()))
    except (TypeError, ValueError):
        return None


def _contact_json(contact):
    if contact is None:
        return None
    return {
        "name": contact.name,
        "phone": contact.phone,
        "updated_at": contact.updated_at.isoformat(),
    }


def _prescription_json(record):
    return {
        "id": record.id,
        "medication": record.medication,
        "dose": record.dose,
        "instructions": record.instructions,
        "prescriber": record.prescriber,
        "prescribed_date": record.prescribed_date.isoformat(),
        "created_at": record.created_at.isoformat(),
    }


def _validate_contact(data):
    errors = {}
    name = data.get("name")
    phone = data.get("phone")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 150:
        errors["name"] = "Contact name must contain 1 to 150 characters."
    if (
        not isinstance(phone, str)
        or not phone.strip()
        or len(phone.strip()) > 32
        or not _PHONE_PATTERN.fullmatch(phone.strip())
        or not 7 <= sum(char.isdigit() for char in phone) <= 15
    ):
        errors["phone"] = "Enter a valid phone number."
    return errors


def _validate_prescription(data):
    errors = {}
    allowed = {"medication", "dose", "instructions", "prescriber", "prescribed_date"}
    for key in data.keys() - allowed:
        errors[key] = "This field is not allowed."
    for key, maximum in (("medication", 200), ("prescriber", 150)):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
            errors[key] = f"{key.replace('_', ' ').title()} must contain 1 to {maximum} characters."
    for key, maximum in (("dose", 200), ("instructions", 2000)):
        value = data.get(key, "")
        if not isinstance(value, str) or len(value) > maximum:
            errors[key] = f"{key.title()} must be at most {maximum} characters."
    prescribed_date = data.get("prescribed_date")
    try:
        prescribed_date = date.fromisoformat(prescribed_date)
    except (TypeError, ValueError):
        errors["prescribed_date"] = "Provide the prescription date as YYYY-MM-DD."
        prescribed_date = None
    return errors, prescribed_date


@records_blueprint.get("/profile/emergency-contact")
@jwt_required()
def get_emergency_contact():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    return jsonify({"contact": _contact_json(EmergencyContact.query.filter_by(user_id=user.id).first())}), 200


@records_blueprint.put("/profile/emergency-contact")
@jwt_required()
def save_emergency_contact():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"name", "phone"}:
        return jsonify({"message": "Provide only the emergency contact name and phone."}), 400
    errors = _validate_contact(data)
    if errors:
        return jsonify({"message": "Validation failed.", "errors": errors}), 400
    contact = EmergencyContact.query.filter_by(user_id=user.id).first()
    if contact is None:
        contact = EmergencyContact(user_id=user.id, name=data["name"].strip(), phone=data["phone"].strip())
        db.session.add(contact)
    else:
        contact.name = data["name"].strip()
        contact.phone = data["phone"].strip()
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not save emergency contact")
        return jsonify({"message": "Emergency contact could not be saved."}), 500
    return jsonify({"contact": _contact_json(contact)}), 200


@records_blueprint.delete("/profile/emergency-contact")
@jwt_required()
def delete_emergency_contact():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    contact = EmergencyContact.query.filter_by(user_id=user.id).first()
    if contact is None:
        return jsonify({"message": "Emergency contact not found."}), 404
    db.session.delete(contact)
    db.session.commit()
    return jsonify({"message": "Emergency contact deleted."}), 200


@records_blueprint.get("/prescriptions")
@jwt_required()
def list_prescriptions():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    records = PrescriptionRecord.query.filter_by(user_id=user.id).order_by(
        PrescriptionRecord.prescribed_date.desc(), PrescriptionRecord.id.desc()
    ).all()
    return jsonify({"prescriptions": [_prescription_json(record) for record in records]}), 200


@records_blueprint.post("/prescriptions")
@jwt_required()
def create_prescription():
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "A JSON object is required."}), 400
    errors, prescribed_date = _validate_prescription(data)
    if errors:
        return jsonify({"message": "Validation failed.", "errors": errors}), 400
    record = PrescriptionRecord(
        user_id=user.id,
        medication=data["medication"].strip(),
        dose=data.get("dose", "").strip(),
        instructions=data.get("instructions", "").strip(),
        prescriber=data["prescriber"].strip(),
        prescribed_date=prescribed_date,
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"prescription": _prescription_json(record)}), 201


@records_blueprint.put("/prescriptions/<int:record_id>")
@jwt_required()
def update_prescription(record_id):
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    record = PrescriptionRecord.query.filter_by(id=record_id, user_id=user.id).first()
    if record is None:
        return jsonify({"message": "Prescription record not found."}), 404
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"message": "A JSON object is required."}), 400
    errors, prescribed_date = _validate_prescription(data)
    if errors:
        return jsonify({"message": "Validation failed.", "errors": errors}), 400
    record.medication = data["medication"].strip()
    record.dose = data.get("dose", "").strip()
    record.instructions = data.get("instructions", "").strip()
    record.prescriber = data["prescriber"].strip()
    record.prescribed_date = prescribed_date
    db.session.commit()
    return jsonify({"prescription": _prescription_json(record)}), 200


@records_blueprint.delete("/prescriptions/<int:record_id>")
@jwt_required()
def delete_prescription(record_id):
    user = _current_user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    record = PrescriptionRecord.query.filter_by(id=record_id, user_id=user.id).first()
    if record is None:
        return jsonify({"message": "Prescription record not found."}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": "Prescription record deleted."}), 200
