from pathlib import Path

from dotenv import load_dotenv

project_env = Path(__file__).resolve().parents[2] / ".env"
backend_env = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(project_env if project_env.is_file() else backend_env)

from datetime import timedelta

from flask import Flask, jsonify, request
from flask_cors import CORS

from .config import get_config
from .cli import admin as admin_cli
from .extensions import bcrypt, db, jwt, migrate
from .celery_app import init_celery
from .logging_config import configure_logging
from .models import TokenBlocklist, User
from .routes import api_blueprint
from .services.prediction import initialize_prediction_service
from .services.detection_model import DetectionModel


@jwt.token_in_blocklist_loader
def is_token_revoked(jwt_header, jwt_payload):
    return (
        db.session.query(TokenBlocklist.id)
        .filter_by(jti=jwt_payload["jti"])
        .first()
        is not None
    )


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return {"message": "The authentication token has expired."}, 401


@jwt.invalid_token_loader
def invalid_token_callback(reason):
    return {"message": "The authentication token is invalid."}, 401


@jwt.unauthorized_loader
def missing_token_callback(reason):
    return {"message": "Authentication is required."}, 401


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return {"message": "The authentication token has been revoked."}, 401


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or get_config())
    configure_logging(app)
    init_celery(app)
    app.extensions["mosquito_detection_model"] = DetectionModel(
        app.config.get(
            "MOSQUITO_DETECTOR_PATH",
            str(Path(__file__).resolve().parent / "ml" / "models" / "mosquito_detector.pt"),
        )
    )

    db.init_app(app)
    migrate.init_app(
        app,
        db,
        directory=str(Path(__file__).resolve().parent.parent / "migrations"),
    )
    app.config.setdefault("JWT_TOKEN_LOCATION", ["headers"])
    app.config.setdefault("JWT_HEADER_NAME", "Authorization")
    app.config.setdefault("JWT_HEADER_TYPE", "Bearer")
    app.config.setdefault("JWT_ACCESS_TOKEN_EXPIRES", timedelta(minutes=15))
    app.config.setdefault("JWT_REFRESH_TOKEN_EXPIRES", timedelta(days=30))
    app.config.setdefault("JWT_BLOCKLIST_ENABLED", True)
    jwt.init_app(app)
    bcrypt.init_app(app)
    origins = app.config.get("FRONTEND_ORIGIN", "http://localhost:5173")
    if isinstance(origins, str):
        origins = [origin.strip() for origin in origins.split(",") if origin.strip()]
    CORS(
        app,
        resources={r"/api/*": {"origins": origins}},
        allow_headers=["Authorization", "Content-Type"],
        methods=["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"],
    )

    app.register_blueprint(api_blueprint, url_prefix="/api")
    app.cli.add_command(admin_cli)
    if not app.testing and app.config.get("LOAD_PREDICTION_SERVICE", True):
        prediction_service = initialize_prediction_service(app)
        if app.config.get("REQUIRE_MODEL_AT_STARTUP") and not prediction_service.available:
            raise RuntimeError(
                "Production startup aborted because the dengue prediction model "
                f"could not be loaded: {prediction_service.load_error}"
            )

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(self), microphone=(self), geolocation=(self)",
        )
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/api/"):
            return jsonify({"message": "The requested API resource was not found."}), 404
        return error

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Unhandled request error", exc_info=error)
        if request.path.startswith("/api/"):
            return jsonify({"message": "An internal server error occurred."}), 500
        return error

    return app
