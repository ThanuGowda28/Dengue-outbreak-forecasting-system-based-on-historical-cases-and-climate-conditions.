from backend.app import create_app
from backend.app.config import get_config


class CeleryWorkerConfig(get_config()):
    LOAD_PREDICTION_SERVICE = False
    AUTO_MIGRATE_DATABASE = False


flask_app = create_app(CeleryWorkerConfig)
celery = flask_app.extensions["celery"]
