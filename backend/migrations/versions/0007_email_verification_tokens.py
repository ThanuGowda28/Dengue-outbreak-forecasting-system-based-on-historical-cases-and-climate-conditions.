"""Add expiring email verification tokens.

Revision ID: 0007_email_verification_tokens
Revises: 0006_user_preferences
"""
from alembic import op
import sqlalchemy as sa


revision = "0007_email_verification_tokens"
down_revision = "0006_user_preferences"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("token_hash"),
    )


def downgrade():
    op.drop_table("email_verification_tokens")
