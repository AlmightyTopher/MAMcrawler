"""Add genre_settings and api_logs tables

Revision ID: 20241118_001
Revises:
Create Date: 2024-11-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20241118_001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create genre_settings and api_logs tables."""

    # Create genre_settings table
    op.create_table(
        'genre_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('genre_name', sa.String(length=255), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, default=True),
        sa.Column('priority', sa.Integer(), nullable=False, default=0),
        sa.Column('date_created', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('date_updated', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for genre_settings
    op.create_index(op.f('ix_genre_settings_id'), 'genre_settings', ['id'], unique=False)
    op.create_index(op.f('ix_genre_settings_genre_name'), 'genre_settings', ['genre_name'], unique=True)

    # Create api_logs table
    op.create_table(
        'api_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('method', sa.String(length=10), nullable=False),
        sa.Column('path', sa.String(length=500), nullable=False),
        sa.Column('query_params', sa.Text(), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Float(), nullable=False),
        sa.Column('response_size', sa.Integer(), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('request_body', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for api_logs
    op.create_index(op.f('ix_api_logs_id'), 'api_logs', ['id'], unique=False)
    op.create_index(op.f('ix_api_logs_method'), 'api_logs', ['method'], unique=False)
    op.create_index(op.f('ix_api_logs_path'), 'api_logs', ['path'], unique=False)
    op.create_index(op.f('ix_api_logs_status_code'), 'api_logs', ['status_code'], unique=False)
    op.create_index(op.f('ix_api_logs_timestamp'), 'api_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    """Drop genre_settings and api_logs tables."""

    # Drop api_logs indexes and table
    op.drop_index(op.f('ix_api_logs_timestamp'), table_name='api_logs')
    op.drop_index(op.f('ix_api_logs_status_code'), table_name='api_logs')
    op.drop_index(op.f('ix_api_logs_path'), table_name='api_logs')
    op.drop_index(op.f('ix_api_logs_method'), table_name='api_logs')
    op.drop_index(op.f('ix_api_logs_id'), table_name='api_logs')
    op.drop_table('api_logs')

    # Drop genre_settings indexes and table
    op.drop_index(op.f('ix_genre_settings_genre_name'), table_name='genre_settings')
    op.drop_index(op.f('ix_genre_settings_id'), table_name='genre_settings')
    op.drop_table('genre_settings')
