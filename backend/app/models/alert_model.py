from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, Index, UniqueConstraint

from ..extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class AlertPreference(db.Model):
    __tablename__ = "alert_preferences"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    email_alerts = db.Column(db.Boolean, nullable=False, default=True)
    sms_alerts = db.Column(db.Boolean, nullable=False, default=False)
    daily_notifications = db.Column(db.Boolean, nullable=False, default=False)
    high_risk_notifications = db.Column(db.Boolean, nullable=False, default=True)
    weather_alerts = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", backref=db.backref("alert_preferences", uselist=False))


class AlertHistory(db.Model):
    __tablename__ = "alert_history"
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('email', 'sms', 'in_app')",
            name="ck_alert_history_type",
        ),
        CheckConstraint(
            "status IN ('queued', 'sending', 'retrying', 'sent', 'failed')",
            name="ck_alert_history_status",
        ),
        UniqueConstraint("prediction_id", "alert_type", name="uq_alert_prediction_type"),
        UniqueConstraint(
            "mosquito_detection_id",
            "alert_type",
            name="uq_alert_mosquito_detection_type",
        ),
        Index("ix_alert_history_user_created", "user_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prediction_id = db.Column(
        db.Integer,
        db.ForeignKey("prediction_history.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    mosquito_detection_id = db.Column(
        db.Integer,
        db.ForeignKey("mosquito_detections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    dedupe_key = db.Column(db.String(100), nullable=True, unique=True)
    alert_type = db.Column(db.String(16), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="queued", index=True)
    recipient = db.Column(db.String(254), nullable=False)
    message = db.Column(db.Text, nullable=False)
    failure_reason = db.Column(db.String(1000), nullable=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", backref=db.backref("alerts", lazy="dynamic"))
    prediction = db.relationship("PredictionHistory", backref=db.backref("alerts", lazy="dynamic"))
    mosquito_detection = db.relationship(
        "MosquitoDetection", backref=db.backref("alerts", lazy="dynamic")
    )
