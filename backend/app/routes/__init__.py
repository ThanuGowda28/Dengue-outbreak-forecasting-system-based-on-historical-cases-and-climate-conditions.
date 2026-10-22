from flask import Blueprint

from .auth import auth_blueprint
from .admin import admin_blueprint
from .dashboard import dashboard_blueprint
from .contact import contact_blueprint
from .alert_routes import alert_blueprint
from .risk_map import risk_map_blueprint
from .detection_routes import mosquito_detection_blueprint
from .hospital_routes import hospital_blueprint
from .health import health_blueprint
from .prediction import prediction_blueprint
from .records import records_blueprint
from .reports import reports_blueprint
from .weather import weather_blueprint

api_blueprint = Blueprint("api", __name__)
api_blueprint.register_blueprint(health_blueprint)
api_blueprint.register_blueprint(auth_blueprint)
api_blueprint.register_blueprint(admin_blueprint)
api_blueprint.register_blueprint(records_blueprint)
api_blueprint.register_blueprint(weather_blueprint)
api_blueprint.register_blueprint(prediction_blueprint)
api_blueprint.register_blueprint(dashboard_blueprint)
api_blueprint.register_blueprint(reports_blueprint)
api_blueprint.register_blueprint(contact_blueprint)
api_blueprint.register_blueprint(alert_blueprint)
api_blueprint.register_blueprint(risk_map_blueprint)
api_blueprint.register_blueprint(mosquito_detection_blueprint)
api_blueprint.register_blueprint(hospital_blueprint)
