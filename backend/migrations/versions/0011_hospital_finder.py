"""Add hospital finder records.

Revision ID: 0011_hospital_finder
Revises: 0010_mosquito_detection
"""
from alembic import op
import sqlalchemy as sa


revision = "0011_hospital_finder"
down_revision = "0010_mosquito_detection"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "hospitals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("pincode", sa.String(length=12), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("ambulance_phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("hospital_type", sa.String(length=40), nullable=False),
        sa.Column("emergency", sa.Boolean(), nullable=False),
        sa.Column("icu", sa.Boolean(), nullable=False),
        sa.Column("blood_bank", sa.Boolean(), nullable=False),
        sa.Column("ambulance", sa.Boolean(), nullable=False),
        sa.Column("opening_hours", sa.String(length=500), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_hospitals_name", "hospitals", ["name"])
    op.create_index("ix_hospitals_district", "hospitals", ["district"])
    op.create_index("ix_hospitals_city", "hospitals", ["city"])
    op.create_index("ix_hospitals_pincode", "hospitals", ["pincode"])
    op.create_index("ix_hospitals_location", "hospitals", ["latitude", "longitude"])


def downgrade():
    op.drop_index("ix_hospitals_location", table_name="hospitals")
    op.drop_index("ix_hospitals_pincode", table_name="hospitals")
    op.drop_index("ix_hospitals_city", table_name="hospitals")
    op.drop_index("ix_hospitals_district", table_name="hospitals")
    op.drop_index("ix_hospitals_name", table_name="hospitals")
    op.drop_table("hospitals")
