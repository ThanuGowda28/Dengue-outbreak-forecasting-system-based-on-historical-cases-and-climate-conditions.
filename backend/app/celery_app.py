from celery import Celery
from celery.schedules import crontab

celery = Celery("dengue_forecasting")


def init_celery(app):
    celery.conf.update(
        broker_url=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        result_backend=app.config.get(
            "CELERY_RESULT_BACKEND",
            app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        ),
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        task_track_started=True,
        timezone="UTC",
        enable_utc=True,
        beat_schedule={
            "send-daily-alert-summaries": {
                "task": "backend.app.services.alert_service.queue_daily_alert_summaries",
                "schedule": crontab(hour=9, minute=0),
            }
        },
    )

    class FlaskContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = FlaskContextTask
    app.extensions["celery"] = celery
    return celery
