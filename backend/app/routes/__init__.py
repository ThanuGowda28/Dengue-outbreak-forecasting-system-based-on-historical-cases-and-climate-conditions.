from flask import Blueprint

from .auth import auth_blueprint
from .admin import admin_blueprint
from .dashboard import dashboard_blueprint
from .contact import contact_blueprint
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
