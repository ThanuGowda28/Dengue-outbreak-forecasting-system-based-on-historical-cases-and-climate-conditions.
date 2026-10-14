"""Add per-user workspace preferences.

Revision ID: 0006_user_preferences
Revises: 0005_admin_patient_records
"""
from alembic import op
import sqlalchemy as sa


revision = "0006_user_preferences"
down_revision = "0005_admin_patient_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("alerts", sa.Boolean(), nullable=False),
        sa.Column("weekly_summary", sa.Boolean(), nullable=False),
        sa.Column("dark_mode", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade():
    op.drop_table("user_preferences")
