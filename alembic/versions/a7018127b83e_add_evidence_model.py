"""add_evidence_model

Revision ID: a7018127b83e
Revises: 001
Create Date: 2025-12-13 04:48:30.737149

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a7018127b83e'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # evidence_sources
    op.create_table(
        "evidence_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True),
        sa.Column("default_modifier", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # evidence_events
    op.create_table(
        "evidence_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("evidence_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # assertions
    op.create_table(
        "assertions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("evidence_event_id", sa.Integer(), sa.ForeignKey("evidence_events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="SET NULL"), nullable=True),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("value_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("resolution_method", sa.String(length=32), nullable=False),
        sa.Column("method_weight", sa.Float(), nullable=False),
        sa.Column("source_modifier", sa.Float(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("is_human_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_assertions_book_field", "assertions", ["book_id", "field"])
    op.create_index("ix_assertions_fingerprint", "assertions", ["value_fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_assertions_fingerprint", table_name="assertions")
    op.drop_index("ix_assertions_book_field", table_name="assertions")
    op.drop_table("assertions")
    op.drop_table("evidence_events")
    op.drop_table("evidence_sources")
