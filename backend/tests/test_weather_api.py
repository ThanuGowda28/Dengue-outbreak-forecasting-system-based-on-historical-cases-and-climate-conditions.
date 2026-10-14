import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from flask_jwt_extended import create_access_token

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models import User, WeatherHistory
from backend.app.services.weather_provider import WeatherProvider, WeatherProviderError


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-for-flask-tests-0001"
    JWT_SECRET_KEY = "test-jwt-secret-key-for-flask-tests-0001"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    FRONTEND_ORIGIN = "http://localhost:5173"
    OPENWEATHER_API_KEY = "mock-key"
    NASA_POWER_URL = "https://example.invalid/power"
    WEATHER_CACHE_TTL_SECONDS = 300
    WEATHER_RATE_LIMIT_PER_MINUTE = 30


class FakeWeatherProvider:
    def geocode(self, query):
        return [
            {
                "name": "Mysuru",
                "state": "Karnataka",
                "country": "IN",
                "latitude": 12.2958,
                "longitude": 76.6394,
            }
        ]

    def reverse_geocode(self, latitude, longitude):
        return "Mysuru, Karnataka, IN"

    def current(self, latitude, longitude):
        return {
            "observed_at": "2026-09-28T12:00:00+00:00",
            "temperature_c": 28.5,
            "feels_like_c": 30.0,
            "humidity_pct": 68.0,
            "pressure_hpa": 1008.0,
            "wind_speed_mps": 2.4,
            "wind_direction_deg": 180.0,
            "precipitation_mm": 0.0,
            "cloud_cover": 42,
            "sunrise": "2026-09-28T01:00:00+00:00",
            "sunset": "2026-09-28T13:00:00+00:00",
            "uv_index": None,
            "condition": "Clouds",
            "description": "scattered clouds",
            "icon": "03d",
        }

    def forecast(self, latitude, longitude, days):
        return [{"observed_at": "2026-09-29T12:00:00+00:00", "temperature_c": 29.0}]

    def history(self, latitude, longitude, start_date, end_date):
        return [{"observed_at": "2026-09-27T00:00:00+00:00", "temperature_c": 27.0}]


class WeatherApiTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = self._create_user("first@example.test")
        self.other_user = self._create_user("second@example.test")
        self.client = self.app.test_client()
        self.token = create_access_token(identity=str(self.user.id))
        self.other_token = create_access_token(identity=str(self.other_user.id))

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def _create_user(self, email):
        user = User(
            full_name="Weather Test",
            email=email,
            password_hash="not-used",
            phone="1234567890",
            district="Mysuru",
            state="Karnataka",
            role="user",
            is_verified=False,
        )
        db.session.add(user)
        db.session.commit()
        return user

    def _headers(self, token=None):
        return {"Authorization": f"Bearer {token or self.token}"}

    @patch("backend.app.routes.weather.get_weather_provider", return_value=FakeWeatherProvider())
    def test_weather_routes_normalize_and_persist_per_user(self, provider_factory):
        response = self.client.get(
            "/api/weather/current?location=Mysuru%2C%20Karnataka",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["current"]["temperature"], 28.5)
        self.assertEqual(
            set(response.json["current"]),
            {
                "weather_date",
                "temperature",
                "humidity",
                "rainfall",
                "pressure",
                "wind_speed",
                "cloud_cover",
                "sunrise",
                "sunset",
                "uv_index",
                "description",
                "icon",
            },
        )
        self.assertFalse(response.json["cached"])
        stored = WeatherHistory.query.filter_by(user_id=self.user.id).one()
        self.assertEqual(stored.district, "Mysuru")
        self.assertEqual(stored.temperature, 28.5)
        self.assertEqual(stored.humidity, 68.0)
        self.assertEqual(stored.weather_date.isoformat(), "2026-09-28")

        report = self.client.get("/api/reports/weather", headers=self._headers(self.other_token))
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json["reports"], [])

        dashboard = self.client.get("/api/dashboard", headers=self._headers())
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json["weather_record_count"], 1)
        self.assertEqual(dashboard.json["weather"]["current"]["temperature"], 28.5)
        self.assertEqual(dashboard.json["recent_predictions"], [])
        self.assertEqual(dashboard.json["alerts"], [])
        self.assertFalse(dashboard.json["risk_summary"]["available"])
        self.assertIsNone(dashboard.json["risk_summary"]["score"])
        self.assertNotIn("risk_score", dashboard.json["risk_summary"])
        provider_factory.assert_called_once()

    def test_statistics_shape_is_user_scoped(self):
        db.session.add(
            WeatherHistory(
                user_id=self.user.id,
                location_name="Mysuru",
                latitude=12.30,
                longitude=76.65,
                record_type="current",
                provider="openweather",
                observed_at=datetime.now(timezone.utc),
                payload={
                    "location": {"district": "Mysuru"},
                    "current": {
                        "weather_date": "2026-09-27",
                        "temperature": 28,
                        "humidity": 65,
                        "rainfall": 1.2,
                    },
                },
            )
        )
        db.session.commit()
        response = self.client.get(
            "/api/reports/statistics", headers=self._headers()
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {
                "statistics": {
                    "total_weather_records": 1,
                    "records_by_type": {"current": 1, "forecast": 0, "history": 0},
                    "distinct_locations": 1,
                    "monthly_weather": [
                        {
                            "month": "2026-09",
                            "temperature": 28.0,
                            "humidity": 65.0,
                            "rainfall": 1.2,
                            "pressure": None,
                            "wind_speed": None,
                            "cloud_cover": None,
                        }
                    ],
                    "temperature_trend": [
                        {"weather_date": "2026-09-27", "temperature": 28}
                    ],
                    "humidity_trend": [
                        {"weather_date": "2026-09-27", "humidity": 65}
                    ],
                    "rainfall_trend": [
                        {"weather_date": "2026-09-27", "rainfall": 1.2}
                    ],
                }
            },
        )
        other = self.client.get(
            "/api/reports/statistics", headers=self._headers(self.other_token)
        )
        self.assertEqual(other.json["statistics"]["total_weather_records"], 0)

    def test_openweather_current_request_and_missing_key_failure(self):
        with patch(
            "backend.app.services.weather_provider._request_json",
            return_value={
                "dt": 1790596800,
                "main": {"temp": 28.5, "feels_like": 30, "humidity": 68, "pressure": 1008},
                "wind": {"speed": 2.4, "deg": 180},
                "rain": {"1h": 0.4},
                "clouds": {"all": 42},
                "weather": [{"main": "Clouds", "description": "scattered clouds", "icon": "03d"}],
                "sys": {"sunrise": 1790576400, "sunset": 1790620000},
            },
        ) as request_json:
            weather = WeatherProvider().current(12.2958, 76.6394)
        self.assertEqual(weather["temperature_c"], 28.5)
        self.assertEqual(weather["precipitation_mm"], 0.4)
        request_json.assert_called_once()

        self.app.config["OPENWEATHER_API_KEY"] = ""
        unavailable = self.client.get(
            "/api/weather/current?latitude=12.2958&longitude=76.6394",
            headers=self._headers(),
        )
        self.assertEqual(unavailable.status_code, 503)
        self.assertIn("OPENWEATHER_API_KEY", unavailable.json["message"])
        with self.assertRaises(WeatherProviderError):
            WeatherProvider().current(12.2958, 76.6394)

    def test_authenticated_weather_endpoints_integrate_with_provider_and_cache(self):
        history_date = datetime.now(timezone.utc).date() - timedelta(days=1)
        history_key = history_date.strftime("%Y%m%d")

        def provider_response(url, _params):
            if url.endswith("/data/2.5/weather"):
                return {
                    "dt": 1790596800,
                    "main": {
                        "temp": 28.5,
                        "feels_like": 30,
                        "humidity": 68,
                        "pressure": 1008,
                    },
                    "wind": {"speed": 2.4, "deg": 180},
                    "rain": {"1h": 0.4},
                    "clouds": {"all": 42},
                    "weather": [
                        {"main": "Clouds", "description": "scattered clouds", "icon": "03d"}
                    ],
                    "sys": {"sunrise": 1790576400, "sunset": 1790620000},
                }
            if url.endswith("/data/2.5/forecast"):
                return {
                    "list": [
                        {
                            "dt": 1790596800 + index * 10800,
                            "main": {
                                "temp": 25 + index,
                                "humidity": 70,
                                "pressure": 1008,
                            },
                            "weather": [
                                {"main": "Clouds", "description": "cloudy", "icon": "03d"}
                            ],
                        }
                        for index in range(8)
                    ]
                }
            if url == self.app.config["NASA_POWER_URL"]:
                return {
                    "properties": {
                        "parameter": {
                            "T2M": {history_key: 27.0},
                            "RH2M": {history_key: 65.0},
                            "PRECTOTCORR": {history_key: 1.2},
                            "WS2M": {history_key: 2.1},
                            "PS": {history_key: 100.84},
                        }
                    }
                }
            self.fail(f"Unexpected weather provider URL: {url}")

        with patch(
            "backend.app.services.weather_provider._request_json",
            side_effect=provider_response,
        ) as request_json:
            current_url = "/api/weather/current?district=Mysuru"
            current = self.client.get(current_url, headers=self._headers())
            current_cached = self.client.get(current_url, headers=self._headers())
            forecast_url = "/api/weather/forecast?district=Mysuru&days=1"
            forecast = self.client.get(forecast_url, headers=self._headers())
            forecast_cached = self.client.get(forecast_url, headers=self._headers())
            history_url = (
                "/api/weather/history?district=Mysuru"
                f"&start_date={history_date.isoformat()}&end_date={history_date.isoformat()}"
            )
            history = self.client.get(history_url, headers=self._headers())
            history_cached = self.client.get(history_url, headers=self._headers())

        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.json["source"], "openweather")
        self.assertEqual(current.json["current"]["temperature"], 28.5)
        self.assertFalse(current.json["cached"])
        self.assertTrue(current_cached.json["cached"])

        self.assertEqual(forecast.status_code, 200)
        self.assertEqual(forecast.json["source"], "openweather")
        self.assertEqual(len(forecast.json["forecast"]), 8)
        self.assertEqual(forecast.json["forecast"][0]["temperature"], 25)
        self.assertFalse(forecast.json["cached"])
        self.assertTrue(forecast_cached.json["cached"])

        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json["source"], "nasa_power")
        self.assertEqual(history.json["history"][0]["temperature"], 27.0)
        self.assertEqual(history.json["history"][0]["pressure"], 1008.4)
        self.assertFalse(history.json["cached"])
        self.assertTrue(history_cached.json["cached"])
        self.assertEqual(request_json.call_count, 3)
        self.assertEqual(
            WeatherHistory.query.filter_by(user_id=self.user.id).count(), 6
        )

    def test_provider_network_failure_is_returned_as_service_unavailable(self):
        from urllib.error import URLError

        with patch(
            "backend.app.services.weather_provider.urlopen",
            side_effect=URLError("connection failed"),
        ):
            response = self.client.get(
                "/api/weather/current?district=Mysuru", headers=self._headers()
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"], "weather_provider_error")
        self.assertIn("temporarily unavailable", response.json["message"])

    def test_invalid_openweather_credentials_are_returned_as_service_unavailable(self):
        from urllib.error import HTTPError

        unauthorized = HTTPError(
            "https://api.openweathermap.org/data/2.5/weather",
            401,
            "Unauthorized",
            None,
            None,
        )
        with patch(
            "backend.app.services.weather_provider.urlopen",
            side_effect=unauthorized,
        ):
            current = self.client.get(
                "/api/weather/current?lat=12.3&lon=76.6",
                headers=self._headers(),
            )
            forecast = self.client.get(
                "/api/weather/forecast?lat=12.3&lon=76.6&days=1",
                headers=self._headers(),
            )

        for response in (current, forecast):
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json["error"], "weather_provider_error")
            self.assertIn("rejected its API credentials", response.json["message"])
            self.assertNotIn("mock-key", response.get_data(as_text=True))

    @patch(
        "backend.app.services.weather_provider._request_json",
        return_value={
            "dt": 1790596800,
            "list": [
                {
                    "dt": 1790596800 + index * 10800,
                    "main": {"temp": 25 + index, "humidity": 70, "pressure": 1008},
                    "weather": [{"main": "Clouds", "description": "cloudy", "icon": "03d"}],
                }
                for index in range(16)
            ],
        },
    )
    def test_openweather_forecast_parses_three_hour_items_and_limits_days(self, request_json):
        forecast = WeatherProvider("mock-key").forecast(12.3, 76.6, days=1)
        self.assertEqual(len(forecast), 8)
        self.assertEqual(forecast[0]["temperature_c"], 25)
        self.assertEqual(forecast[0]["condition"], "Clouds")
        request_json.assert_called_once()
        self.assertEqual(
            request_json.call_args.args[0],
            "https://api.openweathermap.org/data/2.5/forecast",
        )
        self.assertEqual(request_json.call_args.args[1]["units"], "metric")

    def test_provider_rejects_missing_or_malformed_weather_fields(self):
        provider = WeatherProvider("mock-key")
        with patch(
            "backend.app.services.weather_provider._request_json",
            return_value={"main": {"temp": 28.0}},
        ):
            with self.assertRaisesRegex(WeatherProviderError, "observation time"):
                provider.current(12.3, 76.6)

        with patch(
            "backend.app.services.weather_provider._request_json",
            return_value={"dt": 1790596800, "main": {"temp": "invalid"}},
        ):
            with self.assertRaisesRegex(WeatherProviderError, "temperature"):
                provider.current(12.3, 76.6)

        with patch(
            "backend.app.services.weather_provider._request_json",
            return_value={"list": []},
        ):
            with self.assertRaisesRegex(WeatherProviderError, "no forecast"):
                provider.forecast(12.3, 76.6)

    @patch(
        "backend.app.services.weather_provider._request_json",
        return_value={"properties": {"parameter": {"T2M": {}}}},
    )
    def test_nasa_history_rejects_empty_temperature_series(self, _request_json):
        with self.assertRaisesRegex(WeatherProviderError, "unavailable"):
            WeatherProvider("mock-key", "https://example.invalid/power").history(
                12.3,
                76.6,
                datetime(2026, 9, 27).date(),
                datetime(2026, 9, 27).date(),
            )

    def test_historical_route_reports_unpublished_observations_as_unavailable(self):
        history_date = datetime.now(timezone.utc).date() - timedelta(days=1)
        history_key = history_date.strftime("%Y%m%d")
        with patch(
            "backend.app.services.weather_provider._request_json",
            return_value={
                "properties": {
                    "parameter": {
                        "T2M": {history_key: -999},
                        "RH2M": {history_key: -999},
                        "PRECTOTCORR": {history_key: -999},
                        "WS2M": {history_key: -999},
                        "PS": {history_key: -999},
                    }
                }
            },
        ):
            response = self.client.get(
                "/api/weather/history?"
                f"district=Mysuru&start_date={history_date.isoformat()}"
                f"&end_date={history_date.isoformat()}",
                headers=self._headers(),
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"], "weather_provider_error")
        self.assertIn("not available", response.json["message"])

    @patch("backend.app.services.weather_provider.urlopen")
    def test_provider_rejects_non_utf8_json_response(self, urlopen_mock):
        class InvalidUtf8Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            @staticmethod
            def read():
                return b"\xff"

        urlopen_mock.return_value = InvalidUtf8Response()
        from backend.app.services.weather_provider import _request_json

        with self.assertRaisesRegex(WeatherProviderError, "invalid JSON"):
            _request_json("https://example.test/weather", {})

    def test_invalid_historical_provider_url_returns_actionable_error(self):
        self.app.config["NASA_POWER_URL"] = None
        response = self.client.get(
            "/api/weather/history?latitude=12.2958&longitude=76.6394&days=1",
            headers=self._headers(),
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"], "weather_provider_error")
        self.assertIn("URL", response.json["message"])

    def test_weather_report_uses_frontend_shape(self):
        db.session.add(
            WeatherHistory(
                user_id=self.user.id,
                location_name="Mysuru",
                latitude=12.30,
                longitude=76.65,
                record_type="current",
                provider="openweather",
                observed_at=datetime.now(timezone.utc),
                payload={
                    "location": {
                        "district": "Mysuru",
                        "city": None,
                        "state": "Karnataka",
                    },
                    "current": {"temperature": 28},
                },
            )
        )
        db.session.commit()
        response = self.client.get("/api/reports/weather", headers=self._headers())
        entry = response.json["reports"][0]
        self.assertEqual(
            set(entry),
            {
                "id",
                "location",
                "record_type",
                "source",
                "observed_at",
                "created_at",
                "weather",
            },
        )
        self.assertEqual(entry["location"]["district"], "Mysuru")
        self.assertEqual(response.json["pagination"]["total_items"], 1)
        self.assertFalse(response.json["pagination"]["has_next"])

    def test_weather_report_paginates_all_matching_records(self):
        for index in range(2):
            db.session.add(
                WeatherHistory(
                    user_id=self.user.id,
                    location_name=f"District {index}",
                    district=f"District {index}",
                    latitude=12.3,
                    longitude=76.6,
                    record_type="current",
                    provider="openweather",
                    observed_at=datetime.now(timezone.utc),
                    payload={
                        "location": {"district": f"District {index}"},
                        "current": {"temperature": 25 + index},
                    },
                )
            )
        db.session.commit()

        first_page = self.client.get(
            "/api/reports/weather?limit=1&page=1",
            headers=self._headers(),
        )
        second_page = self.client.get(
            "/api/reports/weather?limit=1&page=2",
            headers=self._headers(),
        )
        invalid_page = self.client.get(
            "/api/reports/weather?page=0",
            headers=self._headers(),
        )

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(second_page.status_code, 200)
        self.assertEqual(first_page.json["pagination"]["total_items"], 2)
        self.assertEqual(first_page.json["pagination"]["total_pages"], 2)
        self.assertTrue(first_page.json["pagination"]["has_next"])
        self.assertFalse(second_page.json["pagination"]["has_next"])
        self.assertNotEqual(
            first_page.json["reports"][0]["id"],
            second_page.json["reports"][0]["id"],
        )
        self.assertEqual(invalid_page.status_code, 400)

    def test_weather_reports_and_statistics_filter_observations_by_date_and_owner(self):
        today = datetime.now(timezone.utc).date()
        older_date = today - timedelta(days=3)
        selected_date = today - timedelta(days=2)
        newest_date = today - timedelta(days=1)
        observations = [
            {
                "weather_date": value.isoformat(),
                "temperature": temperature,
                "humidity": 60,
                "rainfall": 1,
            }
            for value, temperature in (
                (older_date, 20),
                (selected_date, 25),
                (newest_date, 30),
            )
        ]
        db.session.add(
            WeatherHistory(
                user_id=self.user.id,
                location_name="Mysuru",
                district="Mysuru",
                latitude=12.3,
                longitude=76.6,
                weather_date=older_date,
                record_type="history",
                provider="nasa_power",
                observed_at=datetime.now(timezone.utc),
                payload={
                    "location": {"district": "Mysuru", "state": "Karnataka"},
                    "items": observations,
                },
            )
        )
        db.session.add(
            WeatherHistory(
                user_id=self.other_user.id,
                location_name="Mysuru",
                district="Mysuru",
                latitude=12.3,
                longitude=76.6,
                weather_date=selected_date,
                record_type="current",
                provider="openweather",
                observed_at=datetime.now(timezone.utc),
                payload={
                    "location": {"district": "Mysuru", "state": "Karnataka"},
                    "current": {
                        "weather_date": selected_date.isoformat(),
                        "temperature": 99,
                    },
                },
            )
        )
        db.session.commit()
        query = (
            f"start_date={selected_date.isoformat()}&end_date={selected_date.isoformat()}"
            "&district=Mysuru"
        )

        response = self.client.get(
            f"/api/reports/weather?{query}", headers=self._headers()
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["reports"]), 1)
        report_items = response.json["reports"][0]["weather"]["items"]
        self.assertEqual(len(report_items), 1)
        self.assertEqual(report_items[0]["weather_date"], selected_date.isoformat())
        self.assertEqual(report_items[0]["temperature"], 25)

        statistics = self.client.get(
            f"/api/reports/statistics?{query}", headers=self._headers()
        )
        self.assertEqual(statistics.status_code, 200)
        self.assertEqual(
            statistics.json["statistics"]["total_weather_records"], 1
        )
        self.assertEqual(
            statistics.json["statistics"]["temperature_trend"],
            [{"weather_date": selected_date.isoformat(), "temperature": 25}],
        )

        other_user_report = self.client.get(
            f"/api/reports/weather?{query}",
            headers=self._headers(self.other_token),
        )
        self.assertEqual(other_user_report.status_code, 200)
        self.assertEqual(
            other_user_report.json["reports"][0]["weather"]["current"]["temperature"],
            99,
        )

    def test_report_date_filters_reject_invalid_and_reversed_ranges(self):
        invalid = self.client.get(
            "/api/reports/weather?start_date=not-a-date",
            headers=self._headers(),
        )
        reversed_range = self.client.get(
            "/api/reports/statistics?start_date=2026-10-12&end_date=2026-10-01",
            headers=self._headers(),
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(reversed_range.status_code, 400)

    def test_public_static_district_catalog_and_district_query(self):
        districts = self.client.get("/api/weather/districts")
        self.assertEqual(districts.status_code, 200)
        self.assertEqual(len(districts.json["districts"]), 31)
        mysuru = next(
            item for item in districts.json["districts"] if item["district"] == "Mysuru"
        )
        self.assertEqual(
            set(mysuru),
            {"state", "name", "district", "latitude", "longitude", "lat", "lon"},
        )
        self.assertEqual(mysuru["lat"], 12.30)
        self.assertEqual(mysuru["lon"], 76.65)
        self.assertEqual(mysuru["latitude"], 12.30)
        self.assertEqual(mysuru["longitude"], 76.65)

    @patch("backend.app.routes.weather.get_weather_provider")
    def test_state_search_returns_district_choices_without_provider_credentials(self, provider_factory):
        self.app.config["OPENWEATHER_API_KEY"] = ""
        response = self.client.get(
            "/api/weather/search?q=Karnataka", headers=self._headers()
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["locations"]), 31)
        self.assertTrue(
            all(item["state"] == "Karnataka" for item in response.json["locations"])
        )
        self.assertTrue(
            any(item["name"] == "Mysuru" for item in response.json["locations"])
        )
        provider_factory.assert_not_called()

    @patch("backend.app.routes.weather.get_weather_provider", return_value=FakeWeatherProvider())
    def test_weather_accepts_district_and_new_history_date_parameter_names(self, _provider):
        current = self.client.get(
            "/api/weather/current?district=Mysuru&state=Karnataka",
            headers=self._headers(),
        )
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.json["location"]["district"], "Mysuru")
        self.assertEqual(current.json["location"]["state"], "Karnataka")
        self.assertEqual(current.json["location"]["latitude"], 12.30)

        from datetime import date, timedelta

        end = date.today() - timedelta(days=1)
        start = end - timedelta(days=1)
        history = self.client.get(
            "/api/weather/history?"
            f"district=Mysuru&start_date={start.isoformat()}&end_date={end.isoformat()}",
            headers=self._headers(),
        )
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json["history"][0]["temperature"], 27.0)

    @patch("backend.app.routes.weather.get_weather_provider", return_value=FakeWeatherProvider())
    def test_search_forecast_and_history(self, _provider_factory):
        headers = self._headers()
        search = self.client.get("/api/weather/search?q=Mysuru", headers=headers)
        self.assertEqual(search.status_code, 200)
        self.assertEqual(search.json["locations"][0]["state"], "Karnataka")
        coordinate_search = self.client.get(
            "/api/weather/search?lat=12.29&lon=76.63", headers=headers
        )
        self.assertEqual(coordinate_search.status_code, 200)
        self.assertIn("Mysuru", coordinate_search.json["locations"][0]["name"])

        forecast = self.client.get(
            "/api/weather/forecast?lat=12.29&lon=76.63&days=1", headers=headers
        )
        self.assertEqual(forecast.status_code, 200)
        self.assertIn("temperature", forecast.json["forecast"][0])
        self.assertIn("cloud_cover", forecast.json["forecast"][0])

        history = self.client.get(
            "/api/weather/history?lat=12.29&lon=76.63&days=2", headers=headers
        )
        self.assertEqual(history.status_code, 200)
        self.assertIsNone(history.json["history"][0].get("pressure"))
        self.assertEqual(WeatherHistory.query.filter_by(user_id=self.user.id).count(), 2)

    def test_auth_validation_and_legacy_prediction_endpoint_is_gone(self):
        self.assertEqual(self.client.get("/api/weather/current").status_code, 401)
        invalid = self.client.get(
            "/api/weather/current?lat=92&lon=76", headers=self._headers()
        )
        self.assertEqual(invalid.status_code, 400)

        prediction = self.client.get("/api/prediction", headers=self._headers())
        self.assertEqual(prediction.status_code, 410)
        self.assertEqual(prediction.json["error"], "endpoint_deprecated")
        self.assertEqual(
            prediction.json["predict_endpoint"], "/api/prediction/predict"
        )
        self.assertEqual(
            prediction.json["history_endpoint"], "/api/prediction/history"
        )

    def test_missing_provider_key_returns_actionable_error(self):
        self.app.config["OPENWEATHER_API_KEY"] = ""
        response = self.client.get(
            "/api/weather/current?lat=12.29&lon=76.63", headers=self._headers()
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("OPENWEATHER_API_KEY", response.json["message"])
        geocode_error = self.client.get(
            "/api/weather/current?city=Mysuru&state=Karnataka",
            headers=self._headers(),
        )
        self.assertEqual(geocode_error.status_code, 503)

    @patch("backend.app.routes.weather.get_weather_provider", return_value=FakeWeatherProvider())
    def test_current_cache_flag_marks_cached_data(self, provider_factory):
        first = self.client.get(
            "/api/weather/current?lat=12.3&lon=76.6", headers=self._headers()
        )
        second = self.client.get(
            "/api/weather/current?lat=12.3&lon=76.6", headers=self._headers()
        )
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json["cached"])
        self.assertTrue(second.json["cached"])
        self.assertEqual(provider_factory.call_count, 2)

    @patch("backend.app.routes.weather.get_weather_provider", return_value=FakeWeatherProvider())
    def test_user_scoped_rate_limit(self, provider_factory):
        self.app.config["WEATHER_RATE_LIMIT_PER_MINUTE"] = 1
        first = self.client.get(
            "/api/weather/current?lat=12.3&lon=76.6", headers=self._headers()
        )
        second = self.client.get(
            "/api/weather/current?lat=12.3&lon=76.6", headers=self._headers()
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.headers["Retry-After"], "60")
        provider_factory.assert_called_once()

    @patch(
        "backend.app.services.weather_provider._request_json",
        return_value={
            "properties": {
                "parameter": {
                    "T2M": {"20260927": 27.0},
                    "RH2M": {"20260927": 65.0},
                    "PRECTOTCORR": {"20260927": 1.2},
                    "WS2M": {"20260927": 2.1},
                    "PS": {"20260927": 100.84},
                }
            }
        },
    )
    def test_nasa_history_includes_surface_pressure(self, request_json):
        provider = WeatherProvider("mock-key", "https://example.invalid/power")
        history = provider.history(
            12.3,
            76.6,
            datetime(2026, 9, 27).date(),
            datetime(2026, 9, 27).date(),
        )
        self.assertEqual(history[0]["pressure_hpa"], 1008.4)
        self.assertIn("PS", request_json.call_args.args[1]["parameters"])

    @patch("backend.app.routes.weather.get_weather_provider", return_value=FakeWeatherProvider())
    def test_report_filter_and_limits(self, _provider_factory):
        record = WeatherHistory(
            user_id=self.user.id,
            location_name="Mysuru",
            latitude=12.29,
            longitude=76.63,
            record_type="current",
            provider="openweather",
            observed_at=datetime.now(timezone.utc),
            payload={"temperature_c": 28},
        )
        db.session.add(record)
        db.session.commit()
        response = self.client.get(
            "/api/reports/weather?type=invalid", headers=self._headers()
        )
        self.assertEqual(response.status_code, 400)
        own = self.client.get(
            "/api/reports/weather?type=current&limit=1", headers=self._headers()
        )
        self.assertEqual(own.status_code, 200)
        self.assertEqual(len(own.json["reports"]), 1)


if __name__ == "__main__":
    unittest.main()
