"""Add mosquito detection history and alert associations.

Revision ID: 0010_mosquito_detection
Revises: 0009_alert_history_preferences
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_mosquito_detection"
down_revision = "0009_alert_history_preferences"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "mosquito_detections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.String(length=255), nullable=False),
        sa.Column("annotated_image_path", sa.String(length=255), nullable=True),
        sa.Column("prediction", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("objects_detected", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.JSON(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mosquito_detections_user_id", "mosquito_detections", ["user_id"]
    )
    op.create_index(
        "ix_mosquito_detections_prediction", "mosquito_detections", ["prediction"]
    )
    op.create_index(
        "ix_mosquito_detections_created_at", "mosquito_detections", ["created_at"]
    )
    op.create_index(
        "ix_mosquito_detection_user_created",
        "mosquito_detections",
        ["user_id", "created_at"],
    )

    with op.batch_alter_table("alert_history") as batch_op:
        batch_op.drop_constraint("ck_alert_history_type", type_="check")
        batch_op.create_check_constraint(
            "ck_alert_history_type", "alert_type IN ('email', 'sms', 'in_app')"
        )
        batch_op.add_column(
            sa.Column("mosquito_detection_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_alert_history_mosquito_detection_id_mosquito_detections",
            "mosquito_detections",
            ["mosquito_detection_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_alert_history_mosquito_detection_id",
            ["mosquito_detection_id"],
        )
        batch_op.create_unique_constraint(
            "uq_alert_mosquito_detection_type",
            ["mosquito_detection_id", "alert_type"],
        )


def downgrade():
    with op.batch_alter_table("alert_history") as batch_op:
        batch_op.drop_constraint(
            "uq_alert_mosquito_detection_type", type_="unique"
        )
        batch_op.drop_index("ix_alert_history_mosquito_detection_id")
        batch_op.drop_constraint(
            "fk_alert_history_mosquito_detection_id_mosquito_detections",
            type_="foreignkey",
        )
        batch_op.drop_column("mosquito_detection_id")
        batch_op.drop_constraint("ck_alert_history_type", type_="check")
        batch_op.create_check_constraint(
            "ck_alert_history_type", "alert_type IN ('email', 'sms')"
        )
    op.drop_index("ix_mosquito_detection_user_created", table_name="mosquito_detections")
    op.drop_index("ix_mosquito_detections_created_at", table_name="mosquito_detections")
    op.drop_index("ix_mosquito_detections_prediction", table_name="mosquito_detections")
    op.drop_index("ix_mosquito_detections_user_id", table_name="mosquito_detections")
    op.drop_table("mosquito_detections")
