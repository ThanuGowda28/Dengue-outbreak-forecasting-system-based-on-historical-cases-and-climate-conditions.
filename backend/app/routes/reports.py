from datetime import date

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..extensions import db
from ..models import WeatherHistory
from ..services.weather import rate_limited

reports_blueprint = Blueprint("reports", __name__)


@reports_blueprint.get("/reports/statistics")
@jwt_required()
@rate_limited
def weather_statistics():
    user_id = get_jwt_identity()
    start_date, end_date, error = _date_filters()
    if error:
        return error
    district = request.args.get("district", "").strip().casefold()
    records = _weather_report_records(user_id, end_date)
    filtered = [
        (record, _filtered_payload(record, start_date, end_date, district))
        for record in records
    ]
    filtered = [(record, payload) for record, payload in filtered if payload is not None]
    observations = _weather_observations(
        [
            _serialize_report_with_payload(record, payload)
            for record, payload in filtered
        ]
    )
    by_type = {key: 0 for key in ("current", "forecast", "history")}
    for record, _payload in filtered:
        if record.record_type in by_type:
            by_type[record.record_type] += 1
    monthly = {}
    for observation in observations:
        month = observation["weather_date"][:7]
        monthly.setdefault(month, []).append(observation)
    monthly_weather = [
        _average_observations(month, rows)
        for month, rows in sorted(monthly.items())
    ]
    return jsonify(
        {
            "statistics": {
                "total_weather_records": len(filtered),
                "records_by_type": by_type,
                "distinct_locations": len({record.location_name for record, _ in filtered}),
                "monthly_weather": monthly_weather,
                "rainfall_trend": _metric_trend(observations, "rainfall"),
                "temperature_trend": _metric_trend(observations, "temperature"),
                "humidity_trend": _metric_trend(observations, "humidity"),
            }
        }
    ), 200


def _weather_observations(records):
    observations = []
    for record in records:
        payload = record.get("weather", {})
        payload = payload if isinstance(payload, dict) else {}
        weather = payload.get("current")
        items = payload.get("items")
        if isinstance(weather, dict):
            items = [weather]
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or not item.get("weather_date"):
                continue
            observations.append(
                {
                    "weather_date": str(item["weather_date"])[:10],
                    "temperature": item.get("temperature"),
                    "humidity": item.get("humidity"),
                    "rainfall": item.get("rainfall"),
                    "pressure": item.get("pressure"),
                    "wind_speed": item.get("wind_speed"),
                    "cloud_cover": item.get("cloud_cover"),
                }
            )
    return sorted(observations, key=lambda item: item["weather_date"])


def _average_observations(month, rows):
    result = {"month": month}
    for key in ("temperature", "humidity", "rainfall", "pressure", "wind_speed", "cloud_cover"):
        values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
        result[key] = round(sum(values) / len(values), 1) if values else None
    return result


def _metric_trend(observations, metric):
    return [
        {"weather_date": row["weather_date"], metric: row[metric]}
        for row in observations
        if row.get(metric) is not None
    ]


def _serialize_report_with_payload(record, payload):
    payload = payload if isinstance(payload, dict) else {}
    raw_location = payload.get("location", {})
    return {
        "id": record.id,
        "location": {
            "district": raw_location.get("district"),
            "city": raw_location.get("city"),
            "state": raw_location.get("state"),
            "latitude": record.latitude,
            "longitude": record.longitude,
        },
        "record_type": record.record_type,
        "source": record.provider,
        "observed_at": record.observed_at.isoformat(),
        "created_at": record.created_at.isoformat(),
        "weather": payload,
    }


@reports_blueprint.get("/reports/weather")
@jwt_required()
@rate_limited
def weather_report():
    record_type = request.args.get("type")
    if record_type is not None and record_type not in {"current", "forecast", "history"}:
        return (
            jsonify(
                {
                    "message": "type must be one of current, forecast, or history.",
                    "errors": {"type": "Unsupported record type."},
                }
            ),
            400,
        )
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        return jsonify({"message": "limit must be an integer from 1 to 100."}), 400
    if not 1 <= limit <= 100:
        return jsonify({"message": "limit must be an integer from 1 to 100."}), 400
    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        return jsonify({"message": "page must be an integer greater than or equal to 1."}), 400
    if page < 1:
        return jsonify({"message": "page must be an integer greater than or equal to 1."}), 400
    start_date, end_date, error = _date_filters()
    if error:
        return error
    district = request.args.get("district", "").strip().casefold()
    reports = []
    total_items = 0
    offset = (page - 1) * limit
    for record in _weather_report_records(get_jwt_identity(), end_date, record_type):
        payload = _filtered_payload(record, start_date, end_date, district)
        if payload is None:
            continue
        if offset <= total_items < offset + limit:
            reports.append(_serialize_report_with_payload(record, payload))
        total_items += 1
    total_pages = (total_items + limit - 1) // limit
    return jsonify(
        {
            "reports": reports,
            "pagination": {
                "page": page,
                "per_page": limit,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1 and total_items > 0,
            },
        }
    ), 200


def _date_filters():
    start_value = request.args.get("start_date")
    end_value = request.args.get("end_date")
    try:
        start_date = date.fromisoformat(start_value) if start_value else None
        end_date = date.fromisoformat(end_value) if end_value else None
    except ValueError:
        return None, None, (
            jsonify({"message": "Dates must use ISO format YYYY-MM-DD."}), 400
        )
    if start_date and end_date and start_date > end_date:
        return None, None, (
            jsonify({"message": "start_date must not be after end_date."}), 400
        )
    return start_date, end_date, None


def _weather_report_records(user_id, end_date=None, record_type=None):
    query = WeatherHistory.query.filter_by(user_id=user_id)
    if record_type:
        query = query.filter_by(record_type=record_type)
    if end_date:
        query = query.filter(WeatherHistory.weather_date <= end_date)
    return query.order_by(
        WeatherHistory.created_at.desc(), WeatherHistory.id.desc()
    ).yield_per(250)


def _filtered_payload(record, start_date, end_date, district):
    payload = record.payload if isinstance(record.payload, dict) else {}
    raw_location = payload.get("location", {})
    if not isinstance(raw_location, dict):
        raw_location = {}
    location_name = (
        raw_location.get("district")
        or raw_location.get("city")
        or record.location_name
        or ""
    )
    if district and str(location_name).casefold() != district:
        return None

    weather = dict(payload)
    entries = payload.get("items")
    current = payload.get("current")
    if isinstance(entries, list):
        if start_date is None and end_date is None:
            filtered_entries = entries
        else:
            filtered_entries = [
                item
                for item in entries
                if isinstance(item, dict)
                and _date_is_in_range(
                    item.get("weather_date") or record.weather_date,
                    start_date,
                    end_date,
                )
            ]
        if not filtered_entries:
            return None
        weather["items"] = filtered_entries
    elif isinstance(current, dict):
        if (start_date or end_date) and not _date_is_in_range(
            current.get("weather_date") or record.weather_date,
            start_date,
            end_date,
        ):
            return None
    elif (start_date or end_date) and not _date_is_in_range(
        record.weather_date, start_date, end_date
    ):
        return None
    return weather


def _date_is_in_range(value, start_date, end_date):
    try:
        observed_date = date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return False
    return (start_date is None or observed_date >= start_date) and (
        end_date is None or observed_date <= end_date
    )
