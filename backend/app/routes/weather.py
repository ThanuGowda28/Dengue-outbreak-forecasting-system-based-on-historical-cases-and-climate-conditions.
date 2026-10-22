from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from ..services.weather import (
    get_weather_provider,
    parse_location,
    persist,
    provider_call,
    provider_call_with_status,
    provider_error_response,
    rate_limited,
)
from ..services.weather_provider import WeatherProviderError, default_history_range
from ..services.districts import ALL_DISTRICTS

weather_blueprint = Blueprint("weather", __name__)


@weather_blueprint.get("/weather/districts")
def karnataka_districts():
    return jsonify({"districts": list(ALL_DISTRICTS)}), 200


def _weather_location(location):
    return {
        "district": location.get("district"),
        "city": location.get("city"),
        "state": location.get("state"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
    }


@weather_blueprint.get("/weather/search")
@jwt_required()
@rate_limited
def search_locations():
    latitude = request.args.get("lat", request.args.get("latitude"))
    longitude = request.args.get("lon", request.args.get("longitude"))
    if latitude is not None or longitude is not None:
        try:
            latitude, longitude = float(latitude), float(longitude)
        except (TypeError, ValueError):
            return jsonify({"message": "Both lat and lon must be numbers."}), 400
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return jsonify({"message": "Latitude must be -90..90 and longitude -180..180."}), 400
        try:
            provider = get_weather_provider()
            name = provider_call(
                ("reverse-geocode", latitude, longitude),
                lambda: provider.reverse_geocode(latitude, longitude),
            )
            return jsonify(
                {
                    "locations": [
                        {
                            "name": name or "Coordinates",
                            "latitude": latitude,
                            "longitude": longitude,
                        }
                    ]
                }
            ), 200
        except WeatherProviderError as error:
            return provider_error_response(error)
    query = request.args.get("q", request.args.get("location", "")).strip()
    if not query or len(query) > 160:
        return (
            jsonify(
                {
                    "message": "Provide a location search between 1 and 160 characters.",
                    "errors": {"q": "A valid search query is required."},
                }
            ),
            400,
        )
    state_districts = [
        district
        for district in ALL_DISTRICTS
        if district["state"].casefold() == query.casefold()
    ]
    if state_districts:
        return jsonify(
            {
                "locations": [
                    {
                        "name": district["name"],
                        "state": district["state"],
                        "country": "IN",
                        "latitude": district["latitude"],
                        "longitude": district["longitude"],
                    }
                    for district in state_districts
                ]
            }
        ), 200
    try:
        provider = get_weather_provider()
        locations = provider_call(
            ("geocode", query.casefold()), lambda: provider.geocode(query)
        )
        return jsonify({"locations": locations}), 200
    except WeatherProviderError as error:
        return provider_error_response(error)


def _location_payload(provider):
    try:
        location, errors = parse_location(provider)
    except WeatherProviderError as error:
        return None, provider_error_response(error)
    if errors:
        return None, (jsonify({"message": "Validation failed.", "errors": errors}), 400)
    return location, None


@weather_blueprint.get("/weather/current")
@jwt_required()
@rate_limited
def current_weather():
    provider = get_weather_provider()
    location, failure = _location_payload(provider)
    if failure:
        return failure
    try:
        weather, cached = provider_call_with_status(
            ("current", location["latitude"], location["longitude"]),
            lambda: provider.current(location["latitude"], location["longitude"]),
        )
        current = _standard_weather(weather)
        persist(
            get_jwt_identity(),
            location,
            "current",
            "openweather",
            {"location": location, "current": current},
            datetime.now(timezone.utc),
        )
        return jsonify(
            {
                "location": _weather_location(location),
                "current": current,
                "last_updated": weather.get("observed_at"),
                "source": "openweather",
                "cached": cached,
            }
        ), 200
    except WeatherProviderError as error:
        return provider_error_response(error)


@weather_blueprint.get("/weather/forecast")
@jwt_required()
@rate_limited
def weather_forecast():
    try:
        days = int(request.args.get("days", "5"))
    except ValueError:
        return jsonify({"message": "days must be an integer from 1 to 5."}), 400
    if not 1 <= days <= 5:
        return jsonify({"message": "days must be an integer from 1 to 5."}), 400

    provider = get_weather_provider()
    location, failure = _location_payload(provider)
    if failure:
        return failure
    try:
        provider_forecast, cached = provider_call_with_status(
            ("forecast", location["latitude"], location["longitude"], days),
            lambda: provider.forecast(location["latitude"], location["longitude"], days),
        )
        forecast = [_standard_weather(item) for item in provider_forecast]
        persist(
            get_jwt_identity(),
            location,
            "forecast",
            "openweather",
            {"location": location, "items": forecast},
            datetime.now(timezone.utc),
        )
        return jsonify(
            {
                "location": _weather_location(location),
                "source": "openweather",
                "cached": cached,
                "forecast": forecast,
            }
        ), 200
    except WeatherProviderError as error:
        return provider_error_response(error)


@weather_blueprint.get("/weather/history")
@jwt_required()
@rate_limited
def historical_weather():
    start_value = request.args.get(
        "start_date", request.args.get("start", request.args.get("startDate"))
    )
    end_value = request.args.get(
        "end_date", request.args.get("end", request.args.get("endDate"))
    )
    try:
        if start_value or end_value:
            if not (start_value and end_value):
                raise ValueError
            start_date = date.fromisoformat(start_value)
            end_date = date.fromisoformat(end_value)
        else:
            days = int(request.args.get("days", "7"))
            if not 1 <= days <= 90:
                raise ValueError
            start_date, end_date = default_history_range(days)
    except ValueError:
        return (
            jsonify(
                {
                    "message": "Provide valid start/end ISO dates or days from 1 to 90.",
                    "errors": {"date_range": "Invalid historical date range."},
                }
            ),
            400,
        )
    today = date.today()
    if start_date > end_date or end_date >= today or (end_date - start_date).days >= 90:
        return (
            jsonify(
                {
                    "message": "History must cover at most 90 past days and cannot include today.",
                    "errors": {"date_range": "Invalid historical date range."},
                }
            ),
            400,
        )

    provider = get_weather_provider()
    location, failure = _location_payload(provider)
    if failure:
        return failure
    try:
        provider_history, cached = provider_call_with_status(
            (
                "history",
                location["latitude"],
                location["longitude"],
                start_date.isoformat(),
                end_date.isoformat(),
            ),
            lambda: provider.history(
                location["latitude"], location["longitude"], start_date, end_date
            ),
        )
        history = [_standard_weather(item) for item in provider_history]
        persist(
            get_jwt_identity(),
            location,
            "history",
            "nasa_power",
            {
                "location": location,
                "items": history,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            datetime.now(timezone.utc),
        )
        return jsonify(
            {
                "location": _weather_location(location),
                "source": "nasa_power",
                "cached": cached,
                "history": history,
            }
        ), 200
    except WeatherProviderError as error:
        return provider_error_response(error)


def _standard_weather(item):
    observed_at = item.get("weather_date", item.get("observed_at"))
    if observed_at:
        try:
            weather_date = datetime.fromisoformat(
                observed_at.replace("Z", "+00:00")
            ).date().isoformat()
        except (TypeError, ValueError):
            weather_date = str(observed_at)[:10]
    else:
        weather_date = None
    return {
        "weather_date": weather_date,
        "temperature": item.get("temperature", item.get("temperature_c")),
        "humidity": item.get("humidity", item.get("humidity_pct")),
        "rainfall": item.get("rainfall", item.get("precipitation_mm")),
        "pressure": item.get("pressure", item.get("pressure_hpa")),
        "wind_speed": item.get("wind_speed", item.get("wind_speed_mps")),
        "cloud_cover": item.get("cloud_cover"),
        "sunrise": item.get("sunrise"),
        "sunset": item.get("sunset"),
        "uv_index": item.get("uv_index"),
        "description": item.get("description", item.get("condition")),
        "icon": item.get("icon"),
    }
