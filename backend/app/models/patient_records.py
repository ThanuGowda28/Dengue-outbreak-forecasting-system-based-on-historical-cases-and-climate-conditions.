from datetime import date

from sqlalchemy import CheckConstraint

from ..extensions import db
from . import utcnow


class EmergencyContact(db.Model):
    __tablename__ = "emergency_contacts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(32), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship("User", backref=db.backref("emergency_contact", uselist=False))


class PrescriptionRecord(db.Model):
    __tablename__ = "prescription_records"
    __table_args__ = (
        CheckConstraint("length(medication) > 0", name="ck_prescription_medication"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medication = db.Column(db.String(200), nullable=False)
    dose = db.Column(db.String(200), nullable=False, default="")
    instructions = db.Column(db.String(2000), nullable=False, default="")
    prescriber = db.Column(db.String(150), nullable=False)
    prescribed_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    user = db.relationship("User", backref=db.backref("prescriptions", lazy="dynamic"))
