from sqlalchemy import func

from ..extensions import db
from ..models import WeatherHistory


def save_weather_result(
    *,
    user_id,
    location_name,
    latitude,
    longitude,
    record_type,
    provider,
    observed_at,
    payload,
):
    observation = payload.get("current") if isinstance(payload, dict) else None
    entries = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(observation, dict):
        observation = next(
            (item for item in entries or [] if isinstance(item, dict)), {}
        )
    raw_location = payload.get("location", {}) if isinstance(payload, dict) else {}
    record = WeatherHistory(
        user_id=user_id,
        location_name=location_name,
        district=raw_location.get("district"),
        temperature=_number(observation.get("temperature")),
        humidity=_number(observation.get("humidity")),
        rainfall=_number(observation.get("rainfall")),
        pressure=_number(observation.get("pressure")),
        wind_speed=_number(observation.get("wind_speed")),
        cloud_cover=_number(observation.get("cloud_cover")),
        latitude=latitude,
        longitude=longitude,
        weather_date=_weather_date(observation.get("weather_date"), observed_at),
        record_type=record_type,
        provider=provider,
        observed_at=observed_at,
        payload=payload,
    )
    db.session.add(record)
    db.session.commit()
    return record


def _number(value):
    return float(value) if isinstance(value, (int, float)) else None


def _weather_date(value, observed_at):
    if value:
        try:
            from datetime import date

            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None
    return observed_at.date()


def list_weather_results(user_id, record_type=None, limit=20):
    query = WeatherHistory.query.filter_by(user_id=user_id)
    if record_type:
        query = query.filter_by(record_type=record_type)
    return query.order_by(WeatherHistory.created_at.desc()).limit(limit).all()


def latest_weather_result(user_id, record_type=None):
    query = WeatherHistory.query.filter_by(user_id=user_id)
    if record_type:
        query = query.filter_by(record_type=record_type)
    return query.order_by(WeatherHistory.created_at.desc()).first()


def weather_result_count(user_id):
    return WeatherHistory.query.filter_by(user_id=user_id).count()


def weather_result_counts_by_type(user_id):
    rows = (
        db.session.query(WeatherHistory.record_type, func.count(WeatherHistory.id))
        .filter(WeatherHistory.user_id == user_id)
        .group_by(WeatherHistory.record_type)
        .all()
    )
    return {record_type: count for record_type, count in rows}


def weather_location_count(user_id):
    return (
        db.session.query(func.count(func.distinct(WeatherHistory.location_name)))
        .filter(WeatherHistory.user_id == user_id)
        .scalar()
        or 0
    )
