import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from ..extensions import db
from ..models import User
from ..repositories.weather_history import save_weather_result
from .districts import ALL_DISTRICTS
from .weather_provider import (
    WeatherProvider,
    WeatherProviderError,
    default_history_range,
)


class TTLCache:
    def __init__(self):
        self._values = {}
        self._lock = threading.Lock()

    def get_or_create(self, key, factory):
        now = time.monotonic()
        with self._lock:
            cached = self._values.get(key)
            if cached and cached[0] > now:
                return cached[1], True
        value = factory()
        ttl = max(0, int(current_app.config.get("WEATHER_CACHE_TTL_SECONDS", 300)))
        if ttl:
            with self._lock:
                if len(self._values) >= 1024:
                    self._values = {
                        cache_key: entry
                        for cache_key, entry in self._values.items()
                        if entry[0] > time.monotonic()
                    }
                    if len(self._values) >= 1024:
                        self._values.pop(next(iter(self._values)))
                self._values[key] = (time.monotonic() + ttl, value)
        return value, False


class UserRateLimiter:
    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, user_id):
        now = time.monotonic()
        limit = max(1, int(current_app.config.get("WEATHER_RATE_LIMIT_PER_MINUTE", 30)))
        key = str(user_id)
        with self._lock:
            if key not in self._hits and len(self._hits) >= 1024:
                expired_users = [
                    user_key
                    for user_key, user_hits in self._hits.items()
                    if not user_hits or user_hits[-1] <= now - 60
                ]
                for user_key in expired_users:
                    del self._hits[user_key]
                if len(self._hits) >= 1024:
                    oldest_user = min(
                        self._hits,
                        key=lambda user_key: self._hits[user_key][-1]
                        if self._hits[user_key]
                        else float("-inf"),
                    )
                    del self._hits[oldest_user]
            hits = self._hits[key]
            while hits and hits[0] <= now - 60:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True


def _cache():
    cache = current_app.extensions.get("weather_cache")
    if cache is None:
        cache = TTLCache()
        current_app.extensions["weather_cache"] = cache
    return cache


def _limiter():
    limiter = current_app.extensions.get("weather_rate_limiter")
    if limiter is None:
        limiter = UserRateLimiter()
        current_app.extensions["weather_rate_limiter"] = limiter
    return limiter


def rate_limited(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            user_id = int(get_jwt_identity())
        except (TypeError, ValueError):
            return jsonify({"message": "User not found."}), 401
        if db.session.get(User, user_id) is None:
            return jsonify({"message": "User not found."}), 401
        if not _limiter().allow(user_id):
            return (
                jsonify(
                    {
                        "message": "Weather API request limit exceeded.",
                        "error": "rate_limit_exceeded",
                    }
                ),
                429,
                {"Retry-After": "60"},
            )
        return view(*args, **kwargs)

    return wrapped


def provider_call(key, factory):
    value, _ = provider_call_with_status(key, factory)
    return value


def provider_call_with_status(key, factory):
    return _cache().get_or_create(key, factory)


def persist(user_id, location, record_type, provider, payload, observed_at):
    return save_weather_result(
        user_id=int(user_id),
        location_name=(
            location.get("city")
            or location.get("district")
            or location.get("state")
            or "Coordinates"
        ),
        latitude=location["latitude"],
        longitude=location["longitude"],
        record_type=record_type,
        provider=provider,
        observed_at=observed_at,
        payload=payload,
    )


def provider_error_response(error):
    return jsonify({"message": str(error), "error": "weather_provider_error"}), error.status_code


def resolve_location(data, provider):
    latitude = data.get("lat", data.get("latitude"))
    longitude = data.get("lon", data.get("longitude"))
    district_value = data.get("district")
    city_value = data.get("city")
    state_value = data.get("state")
    if latitude is not None or longitude is not None:
        try:
            latitude, longitude = float(latitude), float(longitude)
        except (TypeError, ValueError):
            return None, {"coordinates": "Both latitude and longitude must be numbers."}
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return None, {"coordinates": "Latitude must be -90..90 and longitude -180..180."}
        for key in ("district", "city", "state"):
            label = data.get(key)
            if label is not None and (
                not isinstance(label, str) or len(label.strip()) > 100
            ):
                return None, {key: "Location labels must be at most 100 characters."}
        return {
            "district": district_value.strip() if isinstance(district_value, str) else None,
            "city": city_value.strip() if isinstance(city_value, str) else None,
            "state": state_value.strip() if isinstance(state_value, str) else None,
            "latitude": latitude,
            "longitude": longitude,
        }, None

    if isinstance(district_value, str) and district_value.strip():
        district = next(
            (
                item
                for item in ALL_DISTRICTS
                if item["district"].casefold() == district_value.strip().casefold()
            ),
            None,
        )
        if district:
            return {
                "district": district["district"],
                "city": city_value.strip() if isinstance(city_value, str) and city_value.strip() else None,
                "state": state_value.strip() if isinstance(state_value, str) and state_value.strip() else district["state"],
                "latitude": district["lat"],
                "longitude": district["lon"],
            }, None

    query = _location_query(data)
    if not query:
        return None, {
            "location": "Provide location, city, district, or both latitude and longitude."
        }
    if len(query) > 160:
        return None, {"location": "Location query must be 160 characters or fewer."}
    matches = provider_call(("geocode", query.casefold()), lambda: provider.geocode(query))
    if not matches:
        return None, {"location": "No matching location was found."}
    match = matches[0]
    matched_district = next(
        (
            item["district"]
            for item in ALL_DISTRICTS
            if item["district"].casefold() == str(match.get("name", "")).casefold()
        ),
        None,
    )
    return {
        "district": district_value.strip() if isinstance(district_value, str) and district_value.strip() else matched_district,
        "city": city_value.strip() if isinstance(city_value, str) and city_value.strip() else match.get("name"),
        "state": state_value.strip() if isinstance(state_value, str) and state_value.strip() else match.get("state"),
        "latitude": float(match["latitude"]),
        "longitude": float(match["longitude"]),
    }, None


def _location_query(data):
    for key in ("location", "q"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    parts = []
    for key in ("district", "city", "state"):
        value = data.get(key)
        if value is not None:
            if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
                return ""
            parts.append(value.strip())
    return ", ".join(parts)


def get_weather_provider():
    return WeatherProvider()


def parse_location(provider):
    data = request.args.to_dict()
    return resolve_location(data, provider)
