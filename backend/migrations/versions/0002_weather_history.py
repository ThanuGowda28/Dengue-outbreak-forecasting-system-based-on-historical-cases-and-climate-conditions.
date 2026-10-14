"""Add per-user normalized weather result history.

Revision ID: 0002_weather_history
Revises: 0001_auth_tables
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_weather_history"
down_revision = "0001_auth_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "weather_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("location_name", sa.String(length=200), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("record_type", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weather_history_user_id", "weather_history", ["user_id"])
    op.create_index(
        "ix_weather_history_record_type", "weather_history", ["record_type"]
    )


def downgrade():
    op.drop_index("ix_weather_history_record_type", table_name="weather_history")
    op.drop_index("ix_weather_history_user_id", table_name="weather_history")
    op.drop_table("weather_history")
