"""Add emergency contacts and clinician-issued prescription records.

Revision ID: 0005_admin_patient_records
Revises: 0004_prediction_history
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_admin_patient_records"
down_revision = "0004_prediction_history"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "emergency_contacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "prescription_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("medication", sa.String(length=200), nullable=False),
        sa.Column("dose", sa.String(length=200), nullable=False),
        sa.Column("instructions", sa.String(length=2000), nullable=False),
        sa.Column("prescriber", sa.String(length=150), nullable=False),
        sa.Column("prescribed_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(medication) > 0", name="ck_prescription_medication"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prescription_records_user_id", "prescription_records", ["user_id"])


def downgrade():
    op.drop_index("ix_prescription_records_user_id", table_name="prescription_records")
    op.drop_table("prescription_records")
    op.drop_table("emergency_contacts")
