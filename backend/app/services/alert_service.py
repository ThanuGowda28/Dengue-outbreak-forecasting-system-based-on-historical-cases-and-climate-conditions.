from datetime import datetime, timedelta, timezone

from celery import shared_task
from flask import current_app
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import AlertHistory, AlertPreference, PredictionHistory, User
from .email_service import (
    send_daily_summary,
    send_mosquito_detection_alert,
    send_prediction_alert,
)
from .sms_service import send_sms

HIGH_RISK_LEVELS = {"high", "very high"}


def _alert_message(prediction, user):
    level = prediction.prediction.removesuffix(" Risk").upper()
    recommendations = prediction.recommendations or [
        "Remove stagnant water nearby.",
        "Wear mosquito repellent.",
        "Drink enough fluids.",
        "Visit the nearest hospital if symptoms worsen.",
    ]
    return (
        "⚠ Dengue Alert\n\n"
        f"Hello {user.full_name},\n"
        f"Prediction Risk: {level} ({prediction.confidence:g}%)\n"
        f"Temperature: {prediction.temperature:g}°C\n"
        f"Humidity: {prediction.humidity:g}%\n"
        f"Rainfall: {prediction.rainfall:g} mm\n\n"
        "Recommendations:\n"
        + "\n".join(f"• {item}" for item in recommendations)
        + "\n\nPlease take preventive measures immediately. "
        "Visit a nearby hospital if symptoms persist. Stay Safe."
    )


def _sms_message(prediction):
    level = prediction.prediction.removesuffix(" Risk").upper()
    return (
        "⚠ Dengue Alert\n\n"
        f"Prediction Risk:\n{level} ({prediction.confidence:g}%)\n\n"
        "Please take preventive measures immediately.\n"
        "Visit a nearby hospital if symptoms persist.\n\nStay Safe."
    )


def _risk_triggered(prediction, preferences):
    risk = prediction.prediction.removesuffix(" Risk").casefold()
    high_risk = preferences.high_risk_notifications and risk in HIGH_RISK_LEVELS
    weather_risk = (
        preferences.weather_alerts
        and prediction.humidity > 80
        and prediction.rainfall > 100
        and prediction.confidence > 80
    )
    return high_risk or weather_risk


def _channel_eligible(channel, prediction, preferences):
    if channel == "email":
        return preferences.email_alerts
    risk = prediction.prediction.removesuffix(" Risk").casefold()
    return preferences.sms_alerts and (
        prediction.confidence > 80 or risk in HIGH_RISK_LEVELS
    )


def _dispatch(alert):
    try:
        deliver_alert.apply_async(args=[alert.id])
    except Exception as error:
        current_app.logger.exception("Could not queue alert delivery id=%s", alert.id)
        alert.status = "failed"
        alert.failure_reason = f"Alert could not be queued: {error}"[:1000]
        alert.sent_at = datetime.now(timezone.utc)
        db.session.commit()


def queue_prediction_alerts(user, prediction):
    preferences = db.session.get(AlertPreference, user.id) or AlertPreference(
        user_id=user.id,
        email_alerts=True,
        sms_alerts=False,
        daily_notifications=False,
        high_risk_notifications=True,
        weather_alerts=True,
    )
    if not _risk_triggered(prediction, preferences):
        return []

    queued = []
    for channel in ("email", "sms"):
        if not _channel_eligible(channel, prediction, preferences):
            continue
        if channel == "email" and not user.is_verified:
            continue
        existing = AlertHistory.query.filter_by(
            prediction_id=prediction.id,
            alert_type=channel,
        ).first()
        should_dispatch = False
        if existing is None:
            recipient = user.email if channel == "email" else user.phone
            message = (
                _alert_message(prediction, user)
                if channel == "email"
                else _sms_message(prediction)
            )
            existing = AlertHistory(
                user_id=user.id,
                prediction_id=prediction.id,
                alert_type=channel,
                status="queued",
                recipient=recipient,
                message=message,
            )
            db.session.add(existing)
            try:
                db.session.commit()
                should_dispatch = True
            except IntegrityError:
                db.session.rollback()
                existing = AlertHistory.query.filter_by(
                    prediction_id=prediction.id,
                    alert_type=channel,
                ).first()
                if existing is None:
                    raise
        elif existing.status == "failed":
            existing.status = "queued"
            existing.failure_reason = None
            existing.attempts = 0
            existing.sent_at = None
            db.session.commit()
            should_dispatch = True

        if should_dispatch:
            _dispatch(existing)
        queued.append(serialize_alert(existing))
    return queued


def queue_mosquito_detection_alerts(user, detection):
    if detection.prediction != "High Risk Breeding Site":
        return []
    preferences = db.session.get(AlertPreference, user.id) or AlertPreference(
        user_id=user.id,
        email_alerts=True,
        sms_alerts=False,
        daily_notifications=False,
        high_risk_notifications=True,
        weather_alerts=True,
    )
    message = (
        f"⚠ Mosquito breeding-site alert: {detection.prediction} "
        f"({detection.confidence:.2f}%). "
        f"Detected: {', '.join(detection.objects_detected or []) or 'potential breeding site'}. "
        + " ".join(detection.recommendation or [])
    )
    records = []
    in_app = AlertHistory.query.filter_by(
        mosquito_detection_id=detection.id,
        alert_type="in_app",
    ).first()
    if in_app is None:
        in_app = AlertHistory(
            user_id=user.id,
            mosquito_detection_id=detection.id,
            alert_type="in_app",
            status="sent",
            recipient=f"user:{user.id}",
            message=message,
            sent_at=datetime.now(timezone.utc),
        )
        db.session.add(in_app)
        db.session.commit()
    records.append(serialize_alert(in_app))

    channels = []
    if preferences.email_alerts and user.is_verified:
        channels.append(("email", user.email))
    if preferences.sms_alerts and user.phone:
        channels.append(("sms", user.phone))
    for channel, recipient in channels:
        existing = AlertHistory.query.filter_by(
            mosquito_detection_id=detection.id,
            alert_type=channel,
        ).first()
        should_dispatch = False
        if existing is None:
            existing = AlertHistory(
                user_id=user.id,
                mosquito_detection_id=detection.id,
                alert_type=channel,
                status="queued",
                recipient=recipient,
                message=message,
            )
            db.session.add(existing)
            try:
                db.session.commit()
                should_dispatch = True
            except IntegrityError:
                db.session.rollback()
                existing = AlertHistory.query.filter_by(
                    mosquito_detection_id=detection.id,
                    alert_type=channel,
                ).first()
                if existing is None:
                    raise
        elif existing.status == "failed":
            existing.status = "queued"
            existing.failure_reason = None
            existing.attempts = 0
            existing.sent_at = None
            db.session.commit()
            should_dispatch = True
        if should_dispatch:
            _dispatch(existing)
        records.append(serialize_alert(existing))
    return records


def serialize_alert(alert, include_owner=False):
    result = {
        "id": alert.id,
        "prediction_id": alert.prediction_id,
        "mosquito_detection_id": alert.mosquito_detection_id,
        "alert_type": alert.alert_type,
        "status": alert.status,
        "recipient": alert.recipient,
        "message": alert.message,
        "message_preview": alert.message[:180],
        "failure_reason": alert.failure_reason,
        "attempts": alert.attempts,
        "created_at": _iso(alert.created_at),
        "sent_at": _iso(alert.sent_at),
    }
    if include_owner:
        result["user_id"] = alert.user_id
        result["user_name"] = alert.user.full_name if alert.user else None
        result["user_email"] = alert.user.email if alert.user else None
    return result


def _iso(value):
    if value is None:
        return None
    return value.isoformat() if value.tzinfo else value.isoformat() + "Z"


@shared_task(bind=True, name="backend.app.services.alert_service.deliver_alert", max_retries=3)
def deliver_alert(self, alert_id):
    alert = db.session.get(AlertHistory, alert_id)
    if alert is None or alert.status == "sent":
        return

    alert.status = "sending"
    alert.attempts += 1
    alert.failure_reason = None
    db.session.commit()
    try:
        user = db.session.get(User, alert.user_id)
        if user is None:
            raise RuntimeError("Alert recipient account no longer exists.")
        if alert.alert_type == "email":
            if alert.mosquito_detection is not None:
                send_mosquito_detection_alert(
                    user, alert.mosquito_detection, alert.recipient
                )
            elif alert.prediction is None:
                send_daily_summary(user, alert.recipient, alert.message)
            else:
                send_prediction_alert(user, alert.prediction, alert.recipient)
        elif alert.alert_type == "sms":
            send_sms(alert.recipient, alert.message)
        else:
            raise RuntimeError(f"Unsupported alert channel: {alert.alert_type}")
    except Exception as error:
        current_app.logger.exception(
            "Alert delivery failed alert_id=%s attempt=%s",
            alert.id,
            alert.attempts,
        )
        alert.failure_reason = str(error)[:1000] or "Delivery failed."
        if self.request.retries < self.max_retries:
            alert.status = "retrying"
            db.session.commit()
            delay = int(current_app.config.get("ALERT_RETRY_DELAY_SECONDS", 10))
            raise self.retry(exc=error, countdown=min(delay * (2 ** self.request.retries), 300))
        alert.status = "failed"
        alert.sent_at = datetime.now(timezone.utc)
        db.session.commit()
        return

    alert.status = "sent"
    alert.failure_reason = None
    alert.sent_at = datetime.now(timezone.utc)
    db.session.commit()


@shared_task(name="backend.app.services.alert_service.queue_daily_alert_summaries")
def queue_daily_alert_summaries():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    summary_date = now.date().isoformat()
    preferences = db.session.scalars(
        select(AlertPreference).where(
            AlertPreference.daily_notifications.is_(True),
            AlertPreference.email_alerts.is_(True),
        )
    ).all()

    for preference in preferences:
        user = db.session.get(User, preference.user_id)
        if user is None or not user.is_verified:
            continue
        dedupe_key = f"daily:{user.id}:{summary_date}"
        if AlertHistory.query.filter_by(dedupe_key=dedupe_key).first():
            continue
        predictions = PredictionHistory.query.filter(
            PredictionHistory.user_id == user.id,
            PredictionHistory.prediction_time >= start,
            PredictionHistory.prediction_time <= now,
        ).order_by(PredictionHistory.prediction_time.desc()).all()
        if not predictions:
            continue
        latest = predictions[0]
        summary = (
            f"You completed {len(predictions)} prediction(s) in the past day. "
            f"Your latest result was {latest.prediction.removesuffix(' Risk')} "
            f"with {latest.confidence:g}% model confidence."
        )
        db.session.add(
            AlertHistory(
                user_id=user.id,
                alert_type="email",
                status="queued",
                recipient=user.email,
                message=summary,
                dedupe_key=dedupe_key,
            )
        )
    db.session.commit()
    pending_ids = db.session.scalars(
        select(AlertHistory.id).where(
            AlertHistory.dedupe_key.like(f"daily:%:{summary_date}"),
            AlertHistory.status == "queued",
        )
    ).all()
    for alert_id in pending_ids:
        alert = db.session.get(AlertHistory, alert_id)
        if alert:
            _dispatch(alert)


send_daily_alert_summaries = queue_daily_alert_summaries
