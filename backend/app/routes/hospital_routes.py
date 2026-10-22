import csv
import io
from math import ceil

from flask import Blueprint, Response, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import Hospital, User
from ..services.hospital_service import (
    HospitalProviderError,
    filter_facilities,
    find_osm_facilities,
    geocode,
    matching_facilities,
    parse_coordinates,
    reverse_geocode,
    save_osm_facilities,
    serialize_hospital,
)

hospital_blueprint = Blueprint("hospitals", __name__)
_BOOLEAN_FIELDS = ("emergency", "icu", "blood_bank", "ambulance")
_TEXT_LIMITS = {
    "name": 200,
    "address": 500,
    "district": 100,
    "city": 100,
    "state": 100,
    "pincode": 12,
    "phone": 40,
    "ambulance_phone": 40,
    "email": 254,
    "hospital_type": 40,
    "opening_hours": 500,
    "website": 500,
}


def _user():
    try:
        user_id = int(get_jwt_identity())
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)


def _admin():
    user = _user()
    return user if user and user.role.casefold() == "admin" else None


def _admin_required():
    if _admin() is None:
        return jsonify({"message": "Administrator access is required."}), 403
    return None


def _json_data():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def _location_for_request(user):
    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")
    if latitude is not None or longitude is not None:
        if latitude is None or longitude is None:
            raise ValueError("latitude and longitude must be provided together.")
        lat, lon = parse_coordinates(latitude, longitude)
        return {"latitude": lat, "longitude": lon}
    query = (request.args.get("location") or "").strip()
    if not query:
        district = (request.args.get("district") or user.district or "").strip()
        city = (request.args.get("city") or "").strip()
        pincode = (request.args.get("pincode") or "").strip()
        query = ", ".join(part for part in (pincode, city, district, user.state) if part)
    if not query:
        raise ValueError("Provide coordinates or a district, city, or PIN code.")
    return geocode(query)


def _radius():
    try:
        radius = float(request.args.get("distance_km", "25"))
    except ValueError as error:
        raise ValueError("distance_km must be a number between 1 and 100.") from error
    if not 1 <= radius <= 100:
        raise ValueError("distance_km must be between 1 and 100.")
    return radius


def _nearby_records(latitude, longitude, radius, filters):
    radius_m = int(radius * 1000)
    provider_error = None
    try:
        save_osm_facilities(find_osm_facilities(latitude, longitude, radius_m))
    except HospitalProviderError as error:
        provider_error = str(error)

    lat_delta = radius / 110.5
    lon_delta = radius / max(1, 111.32 * abs(__import__("math").cos(__import__("math").radians(latitude))))
    query = Hospital.query.filter(
        Hospital.latitude.between(latitude - lat_delta, latitude + lat_delta),
        Hospital.longitude.between(longitude - lon_delta, longitude + lon_delta),
    )
    query = filter_facilities(query, filters)
    hospitals = query.all()
    located = [
        (hospital, serialize_hospital(hospital, latitude, longitude)["distance_km"])
        for hospital in hospitals
    ]
    located = [(hospital, distance) for hospital, distance in located if distance <= radius]
    located.sort(key=lambda pair: pair[1])
    if provider_error and not located:
        raise HospitalProviderError(provider_error)
    return [hospital for hospital, _distance in located], provider_error


@hospital_blueprint.get("/hospitals/nearby")
@jwt_required()
def nearby_hospitals():
    user = _user()
    if user is None:
        return jsonify({"message": "User not found."}), 401
    try:
        radius = _radius()
        location = _location_for_request(user)
        if location is None:
            return jsonify({"message": "No matching location was found."}), 404
        latitude, longitude = parse_coordinates(location["latitude"], location["longitude"])
        hospitals, provider_warning = _nearby_records(
            latitude, longitude, radius, request.args
        )
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except HospitalProviderError as error:
        current_app.logger.warning("Hospital provider unavailable: %s", error)
        return jsonify({
            "message": str(error),
            "error": "hospital_provider_unavailable",
        }), 503
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not retrieve nearby hospitals")
        return jsonify({"message": "Nearby hospitals could not be retrieved."}), 500

    nearest = hospitals[0] if hospitals else None
    results = [serialize_hospital(item, latitude, longitude) for item in hospitals]
    if nearest:
        nearest_result = results[0]
        nearest_result["estimated_travel_minutes"] = max(
            1, ceil(nearest_result["distance_km"] / 25 * 60)
        )
    return jsonify({
        "items": results,
        "count": len(results),
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "district": location.get("district"),
            "city": location.get("city"),
            "state": location.get("state"),
            "pincode": location.get("pincode"),
            "display_name": location.get("display_name"),
        },
        "distance_km": radius,
        "provider_warning": provider_warning,
        "emergency": nearest_result if nearest else None,
    })


@hospital_blueprint.get("/hospitals/location")
@jwt_required()
def hospital_location_details():
    if _user() is None:
        return jsonify({"message": "User not found."}), 401
    try:
        latitude, longitude = parse_coordinates(
            request.args.get("latitude"), request.args.get("longitude")
        )
        location = reverse_geocode(latitude, longitude)
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except HospitalProviderError as error:
        current_app.logger.warning("Reverse geocoding unavailable: %s", error)
        return jsonify({"message": str(error), "error": "location_service_unavailable"}), 503
    return jsonify({"latitude": latitude, "longitude": longitude, **location})


@hospital_blueprint.get("/hospitals/search")
@jwt_required()
def search_hospitals():
    if _user() is None:
        return jsonify({"message": "User not found."}), 401
    term = (request.args.get("query") or "").strip()
    if len(term) < 2 or len(term) > 200:
        return jsonify({"message": "query must contain between 2 and 200 characters."}), 400
    try:
        query = filter_facilities(matching_facilities(term), request.args)
        hospitals = query.order_by(Hospital.name.asc()).limit(100).all()
        location = None
        provider_warning = None
        if not hospitals:
            location = geocode(term)
            if location:
                hospitals, provider_warning = _nearby_records(
                    location["latitude"],
                    location["longitude"],
                    25,
                    request.args,
                )
    except ValueError as error:
        return jsonify({"message": str(error)}), 400
    except HospitalProviderError as error:
        current_app.logger.warning("Hospital search provider unavailable: %s", error)
        return jsonify({
            "message": str(error),
            "error": "hospital_provider_unavailable",
        }), 503
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not search hospitals")
        return jsonify({"message": "Hospital search could not be completed."}), 500
    return jsonify({
        "items": [
            serialize_hospital(item, location["latitude"], location["longitude"])
            if location else serialize_hospital(item)
            for item in hospitals
        ],
        "count": len(hospitals),
        "location": location,
        "provider_warning": provider_warning,
    })


@hospital_blueprint.get("/hospitals/details/<int:hospital_id>")
@jwt_required()
def hospital_details(hospital_id):
    if _user() is None:
        return jsonify({"message": "User not found."}), 401
    hospital = db.session.get(Hospital, hospital_id)
    if hospital is None:
        return jsonify({"message": "Hospital was not found."}), 404
    return jsonify(serialize_hospital(hospital))


def _validated_hospital(data, hospital=None):
    if not isinstance(data, dict):
        raise ValueError("A JSON object is required.")
    target = hospital or Hospital(name="", address="", latitude=0, longitude=0)
    if "name" in data:
        name = data["name"].strip() if isinstance(data["name"], str) else ""
        if not name or len(name) > 200:
            raise ValueError("name must contain between 1 and 200 characters.")
        target.name = name
    elif hospital is None:
        raise ValueError("name is required.")
    for field, limit in _TEXT_LIMITS.items():
        if field not in data or field == "name":
            continue
        value = data[field]
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field} must be text.")
        value = value.strip() if value else None
        if value and len(value) > limit:
            raise ValueError(f"{field} cannot exceed {limit} characters.")
        setattr(target, field, value)
    for field in _BOOLEAN_FIELDS:
        if field in data:
            if not isinstance(data[field], bool):
                raise ValueError(f"{field} must be true or false.")
            setattr(target, field, data[field])
        elif hospital is None:
            setattr(target, field, False)
    if "latitude" in data:
        target.latitude, target.longitude = parse_coordinates(
            data.get("latitude"), data.get("longitude")
        )
    elif hospital is None:
        raise ValueError("latitude and longitude are required.")
    if "rating" in data:
        rating = data["rating"]
        if rating is None or rating == "":
            target.rating = None
        else:
            try:
                rating = float(rating)
            except (TypeError, ValueError) as error:
                raise ValueError("rating must be between 0 and 5.") from error
            if not 0 <= rating <= 5:
                raise ValueError("rating must be between 0 and 5.")
            target.rating = rating
    source = data.get("source")
    if source is not None and source not in {"admin", "openstreetmap"}:
        raise ValueError("source is invalid.")
    if hospital is None:
        target.source = source or "admin"
    return target


@hospital_blueprint.get("/hospitals/manage")
@jwt_required()
def admin_list_hospitals():
    denied = _admin_required()
    if denied:
        return denied
    query = Hospital.query.order_by(Hospital.name.asc())
    try:
        page = max(1, int(request.args.get("page", "1")))
        per_page = min(100, max(1, int(request.args.get("per_page", "20"))))
    except ValueError:
        return jsonify({"message": "page and per_page must be integers."}), 400
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        "items": [serialize_hospital(item) for item in pagination.items],
        "pagination": {
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total_items": pagination.total,
            "total_pages": pagination.pages,
        },
    })


@hospital_blueprint.post("/hospitals/manage")
@jwt_required()
def create_hospital():
    denied = _admin_required()
    if denied:
        return denied
    try:
        hospital = _validated_hospital(_json_data())
        db.session.add(hospital)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return jsonify({"message": str(error)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not create hospital")
        return jsonify({"message": "Hospital could not be created."}), 500
    return jsonify(serialize_hospital(hospital)), 201


@hospital_blueprint.route("/hospitals/manage/<int:hospital_id>", methods=["PUT", "DELETE"])
@jwt_required()
def update_or_delete_hospital(hospital_id):
    denied = _admin_required()
    if denied:
        return denied
    hospital = db.session.get(Hospital, hospital_id)
    if hospital is None:
        return jsonify({"message": "Hospital was not found."}), 404
    if request.method == "DELETE":
        db.session.delete(hospital)
        db.session.commit()
        return jsonify({"message": "Hospital deleted."})
    try:
        _validated_hospital(_json_data(), hospital)
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return jsonify({"message": str(error)}), 400
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not update hospital id=%s", hospital_id)
        return jsonify({"message": "Hospital could not be updated."}), 500
    return jsonify(serialize_hospital(hospital))


@hospital_blueprint.post("/hospitals/manage/import")
@jwt_required()
def import_hospitals():
    denied = _admin_required()
    if denied:
        return denied
    upload = request.files.get("file")
    if not upload or not upload.filename or not upload.filename.casefold().endswith(".csv"):
        return jsonify({"message": "Select a CSV file."}), 400
    content = upload.stream.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        return jsonify({"message": "CSV file exceeds the 5 MB upload limit."}), 413
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        required = {"name", "latitude", "longitude"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError("CSV must include name, latitude, and longitude columns.")
        imported = 0
        for row_number, row in enumerate(reader, start=2):
            if row_number > 5002:
                raise ValueError("CSV cannot contain more than 5,000 hospital rows.")
            values = dict(row)
            for field in _BOOLEAN_FIELDS:
                if field in values:
                    values[field] = str(values[field]).strip().casefold() in {
                        "true", "yes", "1",
                    }
            if values.get("rating", "").strip():
                values["rating"] = float(values["rating"])
            hospital = _validated_hospital(values)
            hospital.source = "admin"
            db.session.add(hospital)
            imported += 1
        db.session.commit()
    except (UnicodeDecodeError, csv.Error, ValueError) as error:
        db.session.rollback()
        return jsonify({"message": f"CSV import failed: {error}"}), 400
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Could not import hospital CSV")
        return jsonify({"message": "CSV import could not be completed."}), 500
    return jsonify({"message": f"Imported {imported} hospitals.", "imported": imported}), 201


@hospital_blueprint.get("/hospitals/manage/export")
@jwt_required()
def export_hospitals():
    denied = _admin_required()
    if denied:
        return denied
    fields = [
        "name", "address", "district", "city", "state", "pincode", "latitude",
        "longitude", "phone", "ambulance_phone", "email", "rating", "hospital_type",
        "emergency", "icu", "blood_bank", "ambulance", "opening_hours", "website",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for hospital in Hospital.query.order_by(Hospital.name.asc()).all():
        writer.writerow({field: getattr(hospital, field) for field in fields})
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=hospitals.csv"},
    )


@hospital_blueprint.get("/hospitals/manage/statistics")
@jwt_required()
def hospital_statistics():
    denied = _admin_required()
    if denied:
        return denied
    by_type = db.session.query(
        Hospital.hospital_type, func.count(Hospital.id)
    ).group_by(Hospital.hospital_type).all()
    return jsonify({
        "total": Hospital.query.count(),
        "emergency": Hospital.query.filter_by(emergency=True).count(),
        "icu": Hospital.query.filter_by(icu=True).count(),
        "blood_bank": Hospital.query.filter_by(blood_bank=True).count(),
        "ambulance": Hospital.query.filter_by(ambulance=True).count(),
        "by_type": [{"hospital_type": name, "count": count} for name, count in by_type],
    })
