from datetime import datetime, timezone

from sqlalchemy import Index

from ..extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class PredictionHistory(db.Model):
    __tablename__ = "prediction_history"
    __table_args__ = (
        Index("ix_prediction_history_user_time", "user_id", "prediction_time"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    state = db.Column(db.String(100), nullable=False, index=True)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    wind_speed = db.Column(db.Float, nullable=False)
    pressure = db.Column(db.Float, nullable=False)
    solar_radiation = db.Column(db.Float, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    prediction = db.Column(db.String(32), nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)
    class_probabilities = db.Column(db.JSON, nullable=False)
    recommendations = db.Column(db.JSON, nullable=False)
    prediction_time = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = db.relationship("User", backref=db.backref("prediction_history", lazy="dynamic"))
