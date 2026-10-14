import os
from urllib.parse import urlsplit

from sqlalchemy import URL


class BaseConfig:
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
    MAIL_SERVER = os.getenv("MAIL_SERVER", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "")
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_TIMEOUT_SECONDS = int(os.getenv("MAIL_TIMEOUT_SECONDS", "15"))
    CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = URL.create(
        "mysql+pymysql",
        username=os.getenv("DB_USER", "dengue_app"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "dengue_forecasting"),
    )
    MAX_CONTENT_LENGTH = ML_TRAINING_UPLOAD_MAX_BYTES


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"


class ProductionConfig(BaseConfig):
    DEBUG = False
    REQUIRE_MODEL_AT_STARTUP = True
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
        missing = [
            name
            for name in (
                "DB_HOST",
                "DB_NAME",
                "DB_USER",
                "DB_PASSWORD",
                "FRONTEND_ORIGIN",
                "OPENWEATHER_API_KEY",
                "MAIL_SERVER",
                "MAIL_FROM",
            )
            if not os.getenv(name, "").strip()
        ]
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
                "DB_HOST",
                "DB_PASSWORD",
                "OPENWEATHER_API_KEY",
                "MAIL_SERVER",
                "MAIL_FROM",
            )
            if os.getenv(name, "").strip().upper().startswith(
                ("GENERATE-", "SET-", "YOUR-")
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
        if bool(os.getenv("MAIL_USERNAME")) != bool(os.getenv("MAIL_PASSWORD")):
            raise RuntimeError(
                "Production MAIL_USERNAME and MAIL_PASSWORD must either both be "
                "set or both be empty."
            )
        if (
            os.getenv("MAIL_USE_TLS", "true").lower() == "true"
            and os.getenv("MAIL_USE_SSL", "false").lower() == "true"
        ):
            raise RuntimeError(
                "Production MAIL_USE_TLS and MAIL_USE_SSL cannot both be enabled."
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
        return ProductionConfig
    if environment != "development":
        raise RuntimeError(
            "APP_ENV must be 'development', 'testing', or 'production'."
        )
    return DevelopmentConfig
