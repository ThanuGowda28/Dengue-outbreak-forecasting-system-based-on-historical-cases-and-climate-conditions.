from datetime import datetime, timezone
from pathlib import Path
import shutil

from flask import Blueprint, Response, current_app, jsonify, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import User

health_blueprint = Blueprint("health", __name__)


@health_blueprint.get("/openapi.yaml")
def openapi_specification():
    specification = Path(__file__).resolve().parents[2] / "openapi.yaml"
    return send_file(specification, mimetype="application/yaml")


@health_blueprint.get("/docs")
def api_documentation():
    return Response(
        """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dengue Forecasting API</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.addEventListener("load", () => SwaggerUIBundle({
        url: "/api/openapi.yaml",
        dom_id: "#swagger-ui",
        deepLinking: true
      }));
    </script>
  </body>
</html>""",
        mimetype="text/html",
    )


@health_blueprint.get("/health")
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}), 200


@health_blueprint.get("/health/database")
def database_health():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "available"}), 200
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Database health check failed")
        return jsonify({"status": "unavailable", "database": "unavailable"}), 503


@health_blueprint.get("/health/model")
def model_health():
    service = current_app.extensions.get("prediction_service")
    available = bool(service and service.available)
    return jsonify({"status": "ok" if available else "unavailable", "model": "available" if available else "unavailable"}), 200 if available else 503


@health_blueprint.get("/health/weather")
def weather_health():
    configured = bool(current_app.config.get("OPENWEATHER_API_KEY"))
    return jsonify({"status": "ok" if configured else "degraded", "provider": "openweather", "configured": configured, "historical_provider": "nasa_power"}), 200 if configured else 503


@health_blueprint.get("/health/system")
@jwt_required()
def system_health():
    try:
        user = db.session.get(User, int(get_jwt_identity()))
    except (TypeError, ValueError):
        user = None
    if user is None:
        return jsonify({"message": "Authentication is required."}), 401
    if user.role.casefold() != "admin":
        return jsonify({"message": "Access denied."}), 403
    try:
        import psutil

        usage = shutil.disk_usage(current_app.root_path)
        return jsonify({
            "status": "ok",
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": round(usage.used / usage.total * 100, 2) if usage.total else None,
            "database": "available" if db.session.execute(text("SELECT 1")).scalar() == 1 else "unavailable",
            "model": "available" if getattr(current_app.extensions.get("prediction_service"), "available", False) else "unavailable",
        }), 200
    except (ImportError, OSError, SQLAlchemyError):
        db.session.rollback()
        current_app.logger.exception("System health check failed")
        return jsonify({"status": "unavailable"}), 503
