from __future__ import annotations

from math import isfinite

import requests
from flask import current_app
from geopy.distance import geodesic
from sqlalchemy import or_

from ..extensions import db
from ..models import Hospital


class HospitalProviderError(RuntimeError):
    pass


def parse_coordinates(latitude, longitude):
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError) as error:
        raise ValueError("Latitude and longitude must be valid numbers.") from error
    if not isfinite(lat) or not isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Latitude or longitude is outside its valid range.")
    return lat, lon


def geocode(query):
    query = (query or "").strip()
    if not query or len(query) > 200:
        raise ValueError("Enter a location of 1 to 200 characters.")
    base = current_app.config["HOSPITAL_NOMINATIM_URL"].rstrip("/")
    try:
        response = requests.get(
            f"{base}/search",
            params={"q": query, "format": "jsonv2", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": current_app.config["HOSPITAL_USER_AGENT"]},
            timeout=current_app.config["HOSPITAL_PROVIDER_TIMEOUT_SECONDS"],
        )
        response.raise_for_status()
        locations = response.json()
    except (requests.RequestException, ValueError) as error:
        raise HospitalProviderError("The location search service is unavailable.") from error
    if not locations:
        return None
    item = locations[0]
    address = item.get("address") or {}
    return {
        "latitude": float(item["lat"]),
        "longitude": float(item["lon"]),
        "district": address.get("state_district") or address.get("county"),
        "city": address.get("city") or address.get("town") or address.get("village"),
        "state": address.get("state"),
        "pincode": address.get("postcode"),
        "display_name": item.get("display_name", query),
    }


def reverse_geocode(latitude, longitude):
    base = current_app.config["HOSPITAL_NOMINATIM_URL"].rstrip("/")
    try:
        response = requests.get(
            f"{base}/reverse",
            params={"lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 1},
            headers={"User-Agent": current_app.config["HOSPITAL_USER_AGENT"]},
            timeout=current_app.config["HOSPITAL_PROVIDER_TIMEOUT_SECONDS"],
        )
        response.raise_for_status()
        address = response.json().get("address") or {}
    except (requests.RequestException, ValueError) as error:
        raise HospitalProviderError("The reverse location service is unavailable.") from error
    return {
        "district": address.get("state_district") or address.get("county"),
        "city": address.get("city") or address.get("town") or address.get("village"),
        "state": address.get("state"),
        "pincode": address.get("postcode"),
    }


def _facility_type(tags):
    amenity = tags.get("amenity", "").casefold()
    operator = tags.get("operator:type", "").casefold()
    if amenity == "blood_bank" or tags.get("healthcare") == "blood_bank":
        return "Blood Bank"
    if amenity in {"hospital", "clinic", "doctors"} or tags.get("healthcare") in {
        "hospital", "clinic", "doctor", "centre", "center",
    }:
        if operator in {"government", "public"} or tags.get("operator", "").casefold() in {
            "government", "public", "state government",
        }:
            return "Government"
        if operator in {"private", "commercial"}:
            return "Private"
        return "Hospital" if amenity == "hospital" or tags.get("healthcare") == "hospital" else "Clinic"
    if amenity in {"laboratory", "diagnostic"} or tags.get("healthcare") in {"laboratory", "diagnostic"}:
        return "Diagnostic Lab"
    return "Other"


def _osm_record(element):
    tags = element.get("tags") or {}
    coordinates = element.get("center") or element
    if not tags.get("name") or "lat" not in coordinates or "lon" not in coordinates:
        return None
    address_parts = [
        tags.get("addr:housenumber"),
        tags.get("addr:street"),
        tags.get("addr:suburb"),
        tags.get("addr:city"),
        tags.get("addr:postcode"),
    ]
    speciality = " ".join(
        tags.get(key, "") for key in ("healthcare:speciality", "healthcare:specialty", "medical_service")
    ).casefold()
    emergency = tags.get("emergency", "").casefold() in {"yes", "24/7"}
    hours = tags.get("opening_hours")
    return {
        "external_id": f"osm:{element.get('type')}:{element.get('id')}",
        "name": tags["name"][:200],
        "address": ", ".join(part for part in address_parts if part)[:500],
        "district": (tags.get("addr:district") or tags.get("addr:county") or "")[:100] or None,
        "city": (tags.get("addr:city") or tags.get("addr:town") or tags.get("addr:village") or "")[:100] or None,
        "state": (tags.get("addr:state") or "")[:100] or None,
        "pincode": (tags.get("addr:postcode") or "")[:12] or None,
        "latitude": float(coordinates["lat"]),
        "longitude": float(coordinates["lon"]),
        "phone": (tags.get("phone") or tags.get("contact:phone") or "")[:40] or None,
        "ambulance_phone": (tags.get("ambulance:phone") or "")[:40] or None,
        "email": (tags.get("email") or tags.get("contact:email") or "")[:254] or None,
        "rating": None,
        "hospital_type": _facility_type(tags),
        "emergency": emergency,
        "icu": any(value in speciality for value in ("intensive", "icu", "critical_care")),
        "blood_bank": tags.get("blood_bank", "").casefold() in {"yes", "true"}
        or tags.get("healthcare") == "blood_bank" or tags.get("amenity") == "blood_bank",
        "ambulance": tags.get("ambulance", "").casefold() in {"yes", "designated"}
        or bool(tags.get("ambulance:phone")),
        "opening_hours": (hours or "")[:500] or None,
        "website": (tags.get("website") or tags.get("contact:website") or "")[:500] or None,
        "source": "openstreetmap",
    }


def find_osm_facilities(latitude, longitude, radius_m):
    query = (
        f'[out:json][timeout:12];('
        f'nwr(around:{radius_m},{latitude},{longitude})["amenity"~"^(hospital|clinic|doctors|blood_bank|laboratory|diagnostic)$"];'
        f'nwr(around:{radius_m},{latitude},{longitude})["healthcare"~"^(hospital|clinic|doctor|centre|center|blood_bank|laboratory|diagnostic)$"];'
        ");out center tags;"
    )
    try:
        response = requests.post(
            current_app.config["HOSPITAL_OVERPASS_URL"],
            data={"data": query},
            headers={"User-Agent": current_app.config["HOSPITAL_USER_AGENT"]},
            timeout=current_app.config["HOSPITAL_PROVIDER_TIMEOUT_SECONDS"],
        )
        response.raise_for_status()
        elements = response.json().get("elements", [])
    except (requests.RequestException, ValueError) as error:
        raise HospitalProviderError("The hospital data service is unavailable.") from error
    records = [_osm_record(item) for item in elements]
    return [record for record in records if record]


def save_osm_facilities(records):
    hospitals = []
    for values in records:
        hospital = Hospital.query.filter_by(external_id=values["external_id"]).first()
        if hospital is None:
            hospital = Hospital(external_id=values["external_id"])
            db.session.add(hospital)
        for field, value in values.items():
            if field != "external_id":
                setattr(hospital, field, value)
        hospitals.append(hospital)
    if hospitals:
        db.session.commit()
    return hospitals


def hospital_distance(hospital, latitude, longitude):
    return round(geodesic((latitude, longitude), (hospital.latitude, hospital.longitude)).km, 2)


def filter_facilities(query, args):
    hospital_type = (args.get("type") or "").strip().casefold()
    if hospital_type in {"government", "private"}:
        query = query.filter(Hospital.hospital_type.ilike(hospital_type))
    for key, column in (
        ("emergency", Hospital.emergency),
        ("icu", Hospital.icu),
        ("blood_bank", Hospital.blood_bank),
        ("ambulance", Hospital.ambulance),
    ):
        value = args.get(key)
        if value is not None:
            if value.casefold() not in {"true", "false"}:
                raise ValueError(f"{key} must be true or false.")
            if value.casefold() == "true":
                query = query.filter(column.is_(True))
    if args.get("open_24x7", "").casefold() == "true":
        query = query.filter(Hospital.opening_hours.ilike("%24/7%"))
    rating = args.get("min_rating")
    if rating:
        try:
            minimum_rating = float(rating)
        except ValueError as error:
            raise ValueError("min_rating must be between 0 and 5.") from error
        if not 0 <= minimum_rating <= 5:
            raise ValueError("min_rating must be between 0 and 5.")
        query = query.filter(Hospital.rating >= minimum_rating)
    return query


def serialize_hospital(hospital, latitude=None, longitude=None):
    item = {
        "id": hospital.id,
        "name": hospital.name,
        "address": hospital.address,
        "district": hospital.district,
        "city": hospital.city,
        "state": hospital.state,
        "pincode": hospital.pincode,
        "latitude": hospital.latitude,
        "longitude": hospital.longitude,
        "phone": hospital.phone,
        "ambulance_phone": hospital.ambulance_phone,
        "email": hospital.email,
        "rating": hospital.rating,
        "hospital_type": hospital.hospital_type,
        "emergency": hospital.emergency,
        "icu": hospital.icu,
        "blood_bank": hospital.blood_bank,
        "ambulance": hospital.ambulance,
        "opening_hours": hospital.opening_hours,
        "website": hospital.website,
        "source": hospital.source,
        "last_updated": hospital.last_updated.isoformat() if hospital.last_updated else None,
    }
    if latitude is not None and longitude is not None:
        item["distance_km"] = hospital_distance(hospital, latitude, longitude)
    return item


def matching_facilities(query):
    term = f"%{query.strip()}%"
    return Hospital.query.filter(
        or_(
            Hospital.name.ilike(term),
            Hospital.address.ilike(term),
            Hospital.district.ilike(term),
            Hospital.city.ilike(term),
            Hospital.pincode.ilike(term),
        )
    )
