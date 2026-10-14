from ..extensions import db
from . import utcnow


class WeatherHistory(db.Model):
    __tablename__ = "weather_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_name = db.Column(db.String(200), nullable=False)
    district = db.Column(db.String(100), nullable=True, index=True)
    temperature = db.Column(db.Float, nullable=True)
    humidity = db.Column(db.Float, nullable=True)
    rainfall = db.Column(db.Float, nullable=True)
    pressure = db.Column(db.Float, nullable=True)
    wind_speed = db.Column(db.Float, nullable=True)
    cloud_cover = db.Column(db.Float, nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    weather_date = db.Column(db.Date, nullable=True, index=True)
    record_type = db.Column(db.String(16), nullable=False, index=True)
    provider = db.Column(db.String(32), nullable=False)
    observed_at = db.Column(db.DateTime(timezone=True), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", backref=db.backref("weather_history", lazy="dynamic"))
