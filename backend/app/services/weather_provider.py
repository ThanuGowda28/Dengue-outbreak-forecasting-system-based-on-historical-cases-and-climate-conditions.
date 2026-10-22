import json
import math
from datetime import date, datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from flask import current_app


class WeatherProviderError(Exception):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def _request_json(url, params, timeout=10):
    if not isinstance(url, str):
        raise WeatherProviderError("Weather provider URL is not configured correctly.", 503)
    try:
        parts = urlsplit(url)
    except ValueError:
        raise WeatherProviderError("Weather provider URL is not configured correctly.", 503)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise WeatherProviderError("Weather provider URL is not configured correctly.", 503)
    query = "&".join(part for part in (parts.query, urlencode(params)) if part)
    request = Request(
        urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment)),
        headers={"Accept": "application/json", "User-Agent": "DengueWeatherAPI/1.0"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response_status = getattr(response, "status", 200)
            current_app.logger.debug(
                "Weather provider response: url=%s status=%s",
                urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")),
                response_status,
            )
            try:
                payload = json.loads(response.read().decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                current_app.logger.error(
                    "Weather provider returned invalid JSON: url=%s status=%s",
                    urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")),
                    response_status,
                )
                raise WeatherProviderError("Weather provider returned invalid JSON data.", 502)
            if not isinstance(payload, (dict, list)):
                current_app.logger.error(
                    "Weather provider returned an invalid payload: url=%s status=%s",
                    urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")),
                    response_status,
                )
                raise WeatherProviderError("Weather provider returned invalid data.", 502)
            return payload
    except HTTPError as error:
        try:
            error_body = json.loads(
                error.read(4096).decode("utf-8", errors="replace")
            )
            provider_message = (
                error_body.get("message")
                if isinstance(error_body, dict)
                else None
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            provider_message = None
        provider_message = str(provider_message or error.reason)
        safe_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        current_app.logger.error(
            "Weather provider request failed: url=%s status=%s error=%s",
            safe_url,
            error.code,
            provider_message,
        )
        if error.code in (401, 403):
            raise WeatherProviderError("Weather provider rejected its API credentials.", 503)
        if error.code == 404:
            raise WeatherProviderError("The requested location was not found.", 404)
        if error.code == 429:
            raise WeatherProviderError("Weather provider rate limit exceeded.", 503)
        raise WeatherProviderError("Weather provider request failed.", 502)
    except (URLError, TimeoutError, OSError) as error:
        safe_url = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        current_app.logger.error(
            "Weather provider request failed: url=%s status=none error=%s",
            safe_url,
            getattr(error, "reason", str(error)),
        )
        raise WeatherProviderError("Weather provider is temporarily unavailable.", 503)


class WeatherProvider:
    """OpenWeather geocoding/current/forecast and NASA POWER historical data."""

    def __init__(self, openweather_api_key=None, nasa_power_url=None):
        self.api_key = (
            openweather_api_key
            if openweather_api_key is not None
            else current_app.config.get("OPENWEATHER_API_KEY", "")
        )
        self.nasa_power_url = (
            nasa_power_url
            if nasa_power_url is not None
            else current_app.config.get(
                "NASA_POWER_URL", "https://power.larc.nasa.gov/api/temporal/daily/point"
            )
        )

    def geocode(self, query):
        if not self.api_key:
            raise WeatherProviderError(
                "Location search requires OPENWEATHER_API_KEY to be configured.", 503
            )
        results = _request_json(
            "https://api.openweathermap.org/geo/1.0/direct",
            {"q": query, "limit": 5, "appid": self.api_key},
        )
        if not isinstance(results, list):
            raise WeatherProviderError("Location provider returned invalid data.", 502)
        return [
            {
                "name": item.get("name"),
                "state": item.get("state"),
                "country": item.get("country"),
                "latitude": item.get("lat"),
                "longitude": item.get("lon"),
            }
            for item in results
            if isinstance(item, dict)
            and isinstance(item.get("lat"), (int, float))
            and isinstance(item.get("lon"), (int, float))
        ]

    def reverse_geocode(self, latitude, longitude):
        if not self.api_key:
            return None
        results = _request_json(
            "https://api.openweathermap.org/geo/1.0/reverse",
            {
                "lat": latitude,
                "lon": longitude,
                "limit": 1,
                "appid": self.api_key,
            },
        )
        if not isinstance(results, list):
            raise WeatherProviderError("Location provider returned invalid data.", 502)
        if not results:
            return None
        item = results[0]
        if not isinstance(item, dict):
            raise WeatherProviderError("Location provider returned invalid data.", 502)
        return ", ".join(
            value for value in (item.get("name"), item.get("state"), item.get("country")) if value
        )

    def current(self, latitude, longitude):
        payload = self._openweather(
            "https://api.openweathermap.org/data/2.5/weather", latitude, longitude
        )
        weather = _weather_conditions(payload)
        main = _mapping(payload.get("main"), "current weather")
        wind = _optional_mapping(payload.get("wind"), "current weather")
        clouds = _optional_mapping(payload.get("clouds"), "current weather")
        system = _optional_mapping(payload.get("sys"), "current weather")
        temperature = _number(main.get("temp"))
        if temperature is None:
            raise WeatherProviderError("Weather provider returned no valid temperature.", 502)
        timestamp = _utc_datetime(payload.get("dt"))
        return {
            "observed_at": timestamp.isoformat(),
            "temperature_c": temperature,
            "feels_like_c": _number(main.get("feels_like")),
            "humidity_pct": _number(main.get("humidity")),
            "pressure_hpa": _number(main.get("pressure")),
            "wind_speed_mps": _number(wind.get("speed")),
            "wind_direction_deg": _number(wind.get("deg")),
            "precipitation_mm": _precipitation(payload),
            "cloud_cover": _number(clouds.get("all")),
            "sunrise": _optional_timestamp(system.get("sunrise")),
            "sunset": _optional_timestamp(system.get("sunset")),
            "uv_index": None,
            "condition": weather.get("main"),
            "description": weather.get("description"),
            "icon": weather.get("icon"),
        }

    def forecast(self, latitude, longitude, days=5):
        payload = self._openweather(
            "https://api.openweathermap.org/data/2.5/forecast", latitude, longitude
        )
        forecast_items = payload.get("list")
        if not isinstance(forecast_items, list) or not forecast_items:
            raise WeatherProviderError("Weather provider returned no forecast data.", 502)
        entries = []
        for item in forecast_items:
            if not isinstance(item, dict):
                raise WeatherProviderError("Weather provider returned invalid forecast data.", 502)
            weather = _weather_conditions(item)
            main = _mapping(item.get("main"), "forecast")
            wind = _optional_mapping(item.get("wind"), "forecast")
            clouds = _optional_mapping(item.get("clouds"), "forecast")
            temperature = _number(main.get("temp"))
            if temperature is None:
                raise WeatherProviderError("Weather provider returned invalid forecast data.", 502)
            entries.append(
                {
                    "observed_at": _utc_datetime(item.get("dt")).isoformat(),
                    "temperature_c": temperature,
                    "feels_like_c": _number(main.get("feels_like")),
                    "humidity_pct": _number(main.get("humidity")),
                    "pressure_hpa": _number(main.get("pressure")),
                    "wind_speed_mps": _number(wind.get("speed")),
                    "wind_direction_deg": _number(wind.get("deg")),
                    "precipitation_mm": _precipitation(item),
                    "cloud_cover": _number(clouds.get("all")),
                    "sunrise": None,
                    "sunset": None,
                    "uv_index": None,
                    "condition": weather.get("main"),
                    "description": weather.get("description"),
                    "icon": weather.get("icon"),
                }
            )
        return entries[: max(1, min(days, 5)) * 8]

    def history(self, latitude, longitude, start_date, end_date):
        parameters = {
            "latitude": latitude,
            "longitude": longitude,
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "community": "AG",
            "parameters": "T2M,RH2M,PRECTOTCORR,WS2M,PS,ALLSKY_SFC_SW_DWN",
            "format": "JSON",
        }
        payload = _request_json(self.nasa_power_url, parameters)
        if not isinstance(payload, dict):
            raise WeatherProviderError("Historical weather data was unavailable.", 502)
        try:
            data = payload["properties"]["parameter"]
        except (KeyError, TypeError):
            raise WeatherProviderError("Historical weather data was unavailable.", 502)
        if not isinstance(data, dict) or not isinstance(data.get("T2M"), dict):
            raise WeatherProviderError("Historical weather data was unavailable.", 502)
        for key in ("RH2M", "PRECTOTCORR", "WS2M", "PS", "ALLSKY_SFC_SW_DWN"):
            if key in data and not isinstance(data[key], dict):
                raise WeatherProviderError("Historical weather data was invalid.", 502)

        daily = []
        dates = sorted(data.get("T2M", {}).keys())
        if not dates:
            raise WeatherProviderError("Historical weather data was unavailable.", 502)
        for date_key in dates:
            if not isinstance(date_key, str):
                raise WeatherProviderError("Historical weather data was invalid.", 502)
            try:
                observed_at = datetime.strptime(date_key, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                raise WeatherProviderError("Historical weather data was invalid.", 502)
            temperature = _number(data["T2M"].get(date_key))
            if temperature is None:
                continue
            daily.append(
                {
                    "observed_at": observed_at.isoformat(),
                    "temperature_c": temperature,
                    "feels_like_c": None,
                    "humidity_pct": _number(data.get("RH2M", {}).get(date_key)),
                    "pressure_hpa": _pressure_hpa(data.get("PS", {}).get(date_key)),
                    "wind_speed_mps": _number(data.get("WS2M", {}).get(date_key)),
                    "wind_direction_deg": None,
                    "precipitation_mm": _number(
                        data.get("PRECTOTCORR", {}).get(date_key)
                    ),
                    "solar_radiation_mj_m2_day": _number(
                        data.get("ALLSKY_SFC_SW_DWN", {}).get(date_key)
                    ),
                    "condition": None,
                    "description": None,
                    "icon": None,
                }
            )
        if not daily:
            raise WeatherProviderError(
                "Historical observations are not available for this date range yet.",
                503,
            )
        return daily

    def _openweather(self, url, latitude, longitude):
        if not self.api_key:
            raise WeatherProviderError(
                "Current and forecast weather require OPENWEATHER_API_KEY to be configured.",
                503,
            )
        payload = _request_json(
            url,
            {
                "lat": latitude,
                "lon": longitude,
                "appid": self.api_key,
                "units": "metric",
            },
        )
        if not isinstance(payload, dict):
            raise WeatherProviderError("Weather provider returned invalid data.", 502)
        return payload


def _number(value):
    if value is None or value == -999 or value == -9999:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _mapping(value, description):
    if not isinstance(value, dict):
        raise WeatherProviderError(f"Weather provider returned invalid {description} data.", 502)
    return value


def _optional_mapping(value, description):
    if value is None:
        return {}
    return _mapping(value, description)


def _weather_conditions(payload):
    weather = payload.get("weather")
    if weather is None:
        return {}
    if not isinstance(weather, list) or any(not isinstance(item, dict) for item in weather):
        raise WeatherProviderError("Weather provider returned invalid condition data.", 502)
    return weather[0] if weather else {}


def _pressure_hpa(value):
    pressure_kpa = _number(value)
    return round(pressure_kpa * 10, 1) if pressure_kpa is not None else None


def _utc_datetime(timestamp):
    if isinstance(timestamp, bool):
        raise WeatherProviderError("Weather provider returned an invalid observation time.", 502)
    try:
        parsed = datetime.fromtimestamp(int(timestamp), timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        raise WeatherProviderError("Weather provider returned an invalid observation time.", 502)
    if timestamp is None or str(timestamp).strip() == "":
        raise WeatherProviderError("Weather provider returned an invalid observation time.", 502)
    return parsed


def _optional_timestamp(timestamp):
    try:
        return datetime.fromtimestamp(int(timestamp), timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _precipitation(payload):
    rain = payload.get("rain") or {}
    snow = payload.get("snow") or {}
    rainfall = _number(rain.get("1h", rain.get("3h", 0)))
    if rainfall is not None:
        return rainfall
    return _number(snow.get("1h", snow.get("3h", 0)))


def default_history_range(days=7):
    end_date = date.today() - timedelta(days=1)
    return end_date - timedelta(days=days - 1), end_date
