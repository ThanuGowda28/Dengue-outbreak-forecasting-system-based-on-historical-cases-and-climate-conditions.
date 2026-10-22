from datetime import datetime, timezone

from sqlalchemy import Index

from ..extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class MosquitoDetection(db.Model):
    __tablename__ = "mosquito_detections"
    __table_args__ = (
        Index("ix_mosquito_detection_user_created", "user_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_path = db.Column(db.String(255), nullable=False)
    annotated_image_path = db.Column(db.String(255), nullable=True)
    prediction = db.Column(db.String(64), nullable=False, index=True)
    confidence = db.Column(db.Float, nullable=False)
    objects_detected = db.Column(db.JSON, nullable=False, default=list)
    recommendation = db.Column(db.JSON, nullable=False, default=list)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    district = db.Column(db.String(100), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=utcnow, index=True
    )

    user = db.relationship("User", backref=db.backref("mosquito_detections", lazy="dynamic"))
