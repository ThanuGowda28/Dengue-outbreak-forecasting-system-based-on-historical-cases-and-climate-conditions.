from datetime import datetime, timezone

from sqlalchemy import Index

from ..extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Hospital(db.Model):
    __tablename__ = "hospitals"
    __table_args__ = (
        Index("ix_hospitals_location", "latitude", "longitude"),
    )

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(100), unique=True, nullable=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    address = db.Column(db.String(500), nullable=False, default="")
    district = db.Column(db.String(100), nullable=True, index=True)
    city = db.Column(db.String(100), nullable=True, index=True)
    state = db.Column(db.String(100), nullable=True)
    pincode = db.Column(db.String(12), nullable=True, index=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    ambulance_phone = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(254), nullable=True)
    rating = db.Column(db.Float, nullable=True)
    hospital_type = db.Column(db.String(40), nullable=False, default="Other")
    emergency = db.Column(db.Boolean, nullable=False, default=False)
    icu = db.Column(db.Boolean, nullable=False, default=False)
    blood_bank = db.Column(db.Boolean, nullable=False, default=False)
    ambulance = db.Column(db.Boolean, nullable=False, default=False)
    opening_hours = db.Column(db.String(500), nullable=True)
    website = db.Column(db.String(500), nullable=True)
    source = db.Column(db.String(30), nullable=False, default="admin")
    last_updated = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

