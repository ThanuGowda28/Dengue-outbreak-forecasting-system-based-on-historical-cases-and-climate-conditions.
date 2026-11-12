"""Add isolated forecasting history.

Revision ID: 0012_forecast_history
Revises: 0011_hospital_finder
"""
from alembic import op
import sqlalchemy as sa


revision = "0012_forecast_history"
down_revision = "0011_hospital_finder"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "forecast_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("forecast_year", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("expected_trend", sa.String(length=20), nullable=False),
        sa.Column("projected_cases", sa.Float(), nullable=False),
        sa.Column("climate_summary", sa.JSON(), nullable=False),
        sa.Column("timeline", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forecast_history_user_id", "forecast_history", ["user_id"])
    op.create_index("ix_forecast_history_forecast_year", "forecast_history", ["forecast_year"])
    op.create_index("ix_forecast_history_state", "forecast_history", ["state"])
    op.create_index("ix_forecast_history_generated_at", "forecast_history", ["generated_at"])


def downgrade():
    op.drop_index("ix_forecast_history_generated_at", table_name="forecast_history")
    op.drop_index("ix_forecast_history_state", table_name="forecast_history")
    op.drop_index("ix_forecast_history_forecast_year", table_name="forecast_history")
    op.drop_index("ix_forecast_history_user_id", table_name="forecast_history")
    op.drop_table("forecast_history")
