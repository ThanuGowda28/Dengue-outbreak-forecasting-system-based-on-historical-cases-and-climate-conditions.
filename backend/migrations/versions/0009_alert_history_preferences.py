"""Add asynchronous alert history and preferences.

Revision ID: 0009_alert_history_preferences
Revises: 0008_password_reset_tokens
"""
from alembic import op
import sqlalchemy as sa


revision = "0009_alert_history_preferences"
down_revision = "0008_password_reset_tokens"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alert_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sms_alerts", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("daily_notifications", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("high_risk_notifications", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("weather_alerts", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "alert_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=100), nullable=True),
        sa.Column("alert_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("recipient", sa.String(length=254), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("failure_reason", sa.String(length=1000), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("alert_type IN ('email', 'sms')", name="ck_alert_history_type"),
        sa.CheckConstraint(
            "status IN ('queued', 'sending', 'retrying', 'sent', 'failed')",
            name="ck_alert_history_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prediction_id"], ["prediction_history.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("prediction_id", "alert_type", name="uq_alert_prediction_type"),
        sa.UniqueConstraint("dedupe_key", name="uq_alert_history_dedupe_key"),
    )
    op.create_index("ix_alert_history_user_id", "alert_history", ["user_id"])
    op.create_index("ix_alert_history_prediction_id", "alert_history", ["prediction_id"])
    op.create_index("ix_alert_history_status", "alert_history", ["status"])
    op.create_index("ix_alert_history_created_at", "alert_history", ["created_at"])
    op.create_index("ix_alert_history_user_created", "alert_history", ["user_id", "created_at"])


def downgrade():
    op.drop_index("ix_alert_history_user_created", table_name="alert_history")
    op.drop_index("ix_alert_history_created_at", table_name="alert_history")
    op.drop_index("ix_alert_history_status", table_name="alert_history")
    op.drop_index("ix_alert_history_prediction_id", table_name="alert_history")
    op.drop_index("ix_alert_history_user_id", table_name="alert_history")
    op.drop_table("alert_history")
    op.drop_table("alert_preferences")
