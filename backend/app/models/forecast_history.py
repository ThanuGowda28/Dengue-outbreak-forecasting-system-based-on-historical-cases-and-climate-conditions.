from datetime import datetime, timezone

from ..extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class ForecastHistory(db.Model):
    __tablename__ = "forecast_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    forecast_year = db.Column(db.Integer, nullable=False, index=True)
    state = db.Column(db.String(100), nullable=False, index=True)
    district = db.Column(db.String(100), nullable=True)
    risk = db.Column(db.String(20), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    expected_trend = db.Column(db.String(20), nullable=False)
    projected_cases = db.Column(db.Float, nullable=False)
    climate_summary = db.Column(db.JSON, nullable=False)
    timeline = db.Column(db.JSON, nullable=False)
    recommendations = db.Column(db.JSON, nullable=False)
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = db.relationship("User", backref=db.backref("forecast_history", lazy="dynamic"))
