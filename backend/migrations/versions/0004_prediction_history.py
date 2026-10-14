"""Create per-user prediction history.

Revision ID: 0004_prediction_history
Revises: 0003_weather_observation_fields
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_prediction_history"
down_revision = "0003_weather_observation_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "prediction_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("humidity", sa.Float(), nullable=False),
        sa.Column("rainfall", sa.Float(), nullable=False),
        sa.Column("wind_speed", sa.Float(), nullable=False),
        sa.Column("pressure", sa.Float(), nullable=False),
        sa.Column("solar_radiation", sa.Float(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("prediction", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("class_probabilities", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("prediction_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_history_user_id", "prediction_history", ["user_id"])
    op.create_index("ix_prediction_history_state", "prediction_history", ["state"])
    op.create_index("ix_prediction_history_prediction", "prediction_history", ["prediction"])
    op.create_index("ix_prediction_history_prediction_time", "prediction_history", ["prediction_time"])
    op.create_index("ix_prediction_history_user_time", "prediction_history", ["user_id", "prediction_time"])


def downgrade():
    op.drop_index("ix_prediction_history_user_time", table_name="prediction_history")
    op.drop_index("ix_prediction_history_prediction_time", table_name="prediction_history")
    op.drop_index("ix_prediction_history_prediction", table_name="prediction_history")
    op.drop_index("ix_prediction_history_state", table_name="prediction_history")
    op.drop_index("ix_prediction_history_user_id", table_name="prediction_history")
    op.drop_table("prediction_history")
