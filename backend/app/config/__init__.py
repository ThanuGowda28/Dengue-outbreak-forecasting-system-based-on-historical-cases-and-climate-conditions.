import os
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import URL


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEMO_SQLITE_PATH = PROJECT_ROOT / "instance" / "dengue_local.sqlite"


def _database_uri():
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.lower().startswith("sqlite:"):
        if os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower() == "production":
            raise RuntimeError("Production DATABASE_URL must use MySQL; SQLite is not supported.")
        if database_url.lower() in {"sqlite://", "sqlite:///:memory:"}:
            return database_url
        return URL.create("sqlite", database=str(DEMO_SQLITE_PATH))
    if database_url:
        if database_url.lower().startswith("mysql://"):
            return "mysql+pymysql://" + database_url[len("mysql://") :]
        return database_url
    return URL.create(
        "mysql+pymysql",
        username=os.getenv("DB_USER", "dengue_app"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "dengue_forecasting"),
    )


class BaseConfig:
    LOCAL_DEMO_MODE = (
        os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower()
        == "development"
        and os.getenv("LOCAL_DEMO_MODE", "true").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development-jwt-secret-change-me")
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
    NASA_POWER_URL = os.getenv(
        "NASA_POWER_URL",
        "https://power.larc.nasa.gov/api/temporal/daily/point",
    )
    WEATHER_CACHE_TTL_SECONDS = int(os.getenv("WEATHER_CACHE_TTL_SECONDS", "300"))
    WEATHER_RATE_LIMIT_PER_MINUTE = int(
        os.getenv("WEATHER_RATE_LIMIT_PER_MINUTE", "30")
    )
    ML_MODEL_DIR = os.getenv("ML_MODEL_DIR")
    ML_PROCESSED_DIR = os.getenv("ML_PROCESSED_DIR")
    ML_MAX_EPOCHS = int(os.getenv("ML_MAX_EPOCHS", "80"))
    ML_BATCH_SIZE = int(os.getenv("ML_BATCH_SIZE", "32"))
    ML_TRAINING_UPLOAD_MAX_BYTES = int(
        os.getenv("ML_TRAINING_UPLOAD_MAX_BYTES", str(30 * 1024 * 1024))
    )
    MOSQUITO_DETECTOR_PATH = os.getenv(
        "MOSQUITO_DETECTOR_PATH",
        str(Path(__file__).resolve().parents[1] / "ml" / "models" / "mosquito_detector.pt"),
    )
    MOSQUITO_UPLOAD_DIR = os.getenv("MOSQUITO_UPLOAD_DIR", "")
    MOSQUITO_MAX_IMAGE_BYTES = 10 * 1024 * 1024
    HOSPITAL_OVERPASS_URL = os.getenv(
        "HOSPITAL_OVERPASS_URL", "https://overpass-api.de/api/interpreter"
    )
    HOSPITAL_NOMINATIM_URL = os.getenv(
        "HOSPITAL_NOMINATIM_URL", "https://nominatim.openstreetmap.org"
    )
    HOSPITAL_USER_AGENT = os.getenv(
        "HOSPITAL_USER_AGENT", "DengueWatchHospitalFinder/1.0"
    )
    HOSPITAL_PROVIDER_TIMEOUT_SECONDS = int(
        os.getenv("HOSPITAL_PROVIDER_TIMEOUT_SECONDS", "15")
    )
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_TIMEOUT_SECONDS = int(os.getenv("MAIL_TIMEOUT_SECONDS", "15"))
    REDIS_URL = os.getenv("REDIS_URL", "")
    CELERY_BROKER_URL = (
        os.getenv("CELERY_BROKER_URL", "").strip()
        or REDIS_URL
        or "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND = (
        os.getenv("CELERY_RESULT_BACKEND", "").strip()
        or REDIS_URL
        or CELERY_BROKER_URL
    )
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")
    ALERT_RETRY_DELAY_SECONDS = int(os.getenv("ALERT_RETRY_DELAY_SECONDS", "10"))
    CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = _database_uri()
    AUTO_MIGRATE_DATABASE = os.getenv("AUTO_MIGRATE_DATABASE", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    AUTH_RATE_LIMIT_PER_MINUTE = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "10"))
    ADMIN_LOGIN_RATE_LIMIT_PER_MINUTE = int(
        os.getenv("ADMIN_LOGIN_RATE_LIMIT_PER_MINUTE", "5")
    )
    MAX_CONTENT_LENGTH = ML_TRAINING_UPLOAD_MAX_BYTES


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    LOCAL_DEMO_MODE = False
    SQLALCHEMY_DATABASE_URI = "sqlite://"


class ProductionConfig(BaseConfig):
    DEBUG = False
    LOCAL_DEMO_MODE = False
    AUTO_MIGRATE_DATABASE = False
    REQUIRE_MODEL_AT_STARTUP = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True


def get_config():
    environment = os.getenv("APP_ENV", os.getenv("FLASK_ENV", "development")).lower()
    if environment == "testing":
        return TestingConfig
    if environment == "production":
        secret_key = os.getenv("SECRET_KEY", "")
        jwt_secret_key = os.getenv("JWT_SECRET_KEY", "")
        database_url = os.getenv("DATABASE_URL", "").strip()
        if database_url:
            parsed_database_url = urlsplit(database_url)
            if parsed_database_url.scheme not in {"mysql", "mysql+pymysql"}:
                raise RuntimeError(
                    "Production DATABASE_URL must use mysql:// or mysql+pymysql://."
                )
            if (
                not parsed_database_url.hostname
                or not parsed_database_url.username
                or not parsed_database_url.password
                or not parsed_database_url.path.strip("/")
            ):
                raise RuntimeError(
                    "Production DATABASE_URL must include a MySQL host, database, user, and password."
                )
            try:
                database_port = parsed_database_url.port
            except ValueError as error:
                raise RuntimeError(
                    "Production DATABASE_URL must include a valid MySQL port."
                ) from error
            if database_port is not None and not 1 <= database_port <= 65535:
                raise RuntimeError(
                    "Production DATABASE_URL port must be between 1 and 65535."
                )
        database_fields = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
        if not database_url:
            missing_database_fields = [
                name
                for name in database_fields
                if not os.getenv(name, "").strip()
            ]
        else:
            missing_database_fields = []
        broker_url = (
            os.getenv("CELERY_BROKER_URL", "").strip()
            or os.getenv("REDIS_URL", "").strip()
        )
        result_backend = (
            os.getenv("CELERY_RESULT_BACKEND", "").strip() or broker_url
        )
        missing = [
            name
            for name in (
                "FRONTEND_ORIGIN",
                "OPENWEATHER_API_KEY",
                "MAIL_SERVER",
                "MAIL_PORT",
                "MAIL_USE_TLS",
                "MAIL_USERNAME",
                "MAIL_PASSWORD",
                "MAIL_DEFAULT_SENDER",
            )
            if not os.getenv(name, "").strip()
        ]
        if not broker_url:
            missing.append("REDIS_URL or CELERY_BROKER_URL")
        missing.extend(missing_database_fields)
        if (
            len(secret_key) < 32
            or len(jwt_secret_key) < 32
            or secret_key == jwt_secret_key
        ):
            raise RuntimeError(
                "Production requires distinct SECRET_KEY and JWT_SECRET_KEY values "
                "that are each at least 32 characters long."
            )
        placeholders = [
            name
            for name in (
                "SECRET_KEY",
                "JWT_SECRET_KEY",
                "DATABASE_URL",
                "DB_HOST",
                "DB_NAME",
                "DB_USER",
                "DB_PASSWORD",
                "REDIS_URL",
                "CELERY_BROKER_URL",
                "CELERY_RESULT_BACKEND",
                "FRONTEND_ORIGIN",
                "OPENWEATHER_API_KEY",
                "MAIL_SERVER",
                "MAIL_DEFAULT_SENDER",
                "MAIL_USERNAME",
                "MAIL_PASSWORD",
            )
            if any(
                marker in os.getenv(name, "").strip().upper()
                for marker in ("GENERATE-", "SET-", "YOUR-", "REPLACE-")
            )
        ]
        if placeholders:
            raise RuntimeError(
                "Replace placeholder values for production environment variables: "
                + ", ".join(placeholders)
            )
        if missing:
            raise RuntimeError(
                "Production requires these environment variables: "
                + ", ".join(missing)
            )
        if urlsplit(broker_url).scheme not in {"redis", "rediss"}:
            raise RuntimeError(
                "Production REDIS_URL or CELERY_BROKER_URL must use Redis or TLS Redis (rediss)."
            )
        parsed_broker_url = urlsplit(broker_url)
        if not parsed_broker_url.hostname:
            raise RuntimeError(
                "Production REDIS_URL or CELERY_BROKER_URL must include a Redis host."
            )
        if urlsplit(result_backend).scheme not in {"redis", "rediss"}:
            raise RuntimeError(
                "Production CELERY_RESULT_BACKEND must use Redis or TLS Redis (rediss)."
            )
        if not urlsplit(result_backend).hostname:
            raise RuntimeError(
                "Production CELERY_RESULT_BACKEND must include a Redis host."
            )
        try:
            mail_port = int(os.getenv("MAIL_PORT", "587"))
        except ValueError as error:
            raise RuntimeError("Production MAIL_PORT must be an integer.") from error
        if not 1 <= mail_port <= 65535:
            raise RuntimeError("Production MAIL_PORT must be between 1 and 65535.")
        mail_use_tls = os.getenv("MAIL_USE_TLS", "true").lower()
        mail_use_ssl = os.getenv("MAIL_USE_SSL", "false").lower()
        if mail_use_tls not in {"true", "false"}:
            raise RuntimeError("Production MAIL_USE_TLS must be true or false.")
        if mail_use_ssl not in {"true", "false"}:
            raise RuntimeError("Production MAIL_USE_SSL must be true or false.")
        if (
            mail_use_tls == "true" and mail_use_ssl == "true"
        ):
            raise RuntimeError(
                "Production MAIL_USE_TLS and MAIL_USE_SSL cannot both be enabled."
            )
        if mail_use_tls != "true" and mail_use_ssl != "true":
            raise RuntimeError(
                "Production SMTP must enable MAIL_USE_TLS or MAIL_USE_SSL."
            )
        try:
            db_port = int(os.getenv("DB_PORT", "3306"))
        except ValueError as error:
            raise RuntimeError("Production DB_PORT must be an integer.") from error
        if not 1 <= db_port <= 65535:
            raise RuntimeError("Production DB_PORT must be between 1 and 65535.")

        origins = [
            origin.strip()
            for origin in os.getenv("FRONTEND_ORIGIN", "").split(",")
            if origin.strip()
        ]
        if not origins:
            raise RuntimeError(
                "Production requires FRONTEND_ORIGIN with one or more HTTPS origins."
            )
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "https"
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.hostname in {"localhost", "127.0.0.1", "::1"}
            ):
                raise RuntimeError(
                    "Production FRONTEND_ORIGIN values must be HTTPS origins "
                    "without paths or localhost hosts."
                )
        ProductionConfig.SQLALCHEMY_DATABASE_URI = _database_uri()
        ProductionConfig.CELERY_BROKER_URL = broker_url
        ProductionConfig.CELERY_RESULT_BACKEND = result_backend
        return ProductionConfig
    if environment != "development":
        raise RuntimeError(
            "APP_ENV must be 'development', 'testing', or 'production'."
        )
    return DevelopmentConfig
