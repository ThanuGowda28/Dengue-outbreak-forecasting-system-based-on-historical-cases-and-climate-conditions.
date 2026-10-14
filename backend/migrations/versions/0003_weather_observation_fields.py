"""Add queryable climate observation fields to weather history.

Revision ID: 0003_weather_observation_fields
Revises: 0002_weather_history
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_weather_observation_fields"
down_revision = "0002_weather_history"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("weather_history", sa.Column("district", sa.String(length=100), nullable=True))
    op.add_column("weather_history", sa.Column("temperature", sa.Float(), nullable=True))
    op.add_column("weather_history", sa.Column("humidity", sa.Float(), nullable=True))
    op.add_column("weather_history", sa.Column("rainfall", sa.Float(), nullable=True))
    op.add_column("weather_history", sa.Column("pressure", sa.Float(), nullable=True))
    op.add_column("weather_history", sa.Column("wind_speed", sa.Float(), nullable=True))
    op.add_column("weather_history", sa.Column("cloud_cover", sa.Float(), nullable=True))
    op.add_column("weather_history", sa.Column("weather_date", sa.Date(), nullable=True))
    op.create_index("ix_weather_history_district", "weather_history", ["district"])
    op.create_index("ix_weather_history_weather_date", "weather_history", ["weather_date"])


def downgrade():
    op.drop_index("ix_weather_history_weather_date", table_name="weather_history")
    op.drop_index("ix_weather_history_district", table_name="weather_history")
    op.drop_column("weather_history", "weather_date")
    op.drop_column("weather_history", "cloud_cover")
    op.drop_column("weather_history", "wind_speed")
    op.drop_column("weather_history", "pressure")
    op.drop_column("weather_history", "rainfall")
    op.drop_column("weather_history", "humidity")
    op.drop_column("weather_history", "temperature")
    op.drop_column("weather_history", "district")
