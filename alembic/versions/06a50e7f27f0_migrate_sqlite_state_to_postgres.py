"""migrate_sqlite_state_to_postgres

Revision ID: 06a50e7f27f0
Revises: 4ca08ad584ce
Create Date: 2025-12-18 18:08:34.408173

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '06a50e7f27f0'
down_revision = '4ca08ad584ce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create downloaded_books table
    op.create_table(
        'downloaded_books',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('author', sa.Text(), nullable=True),
        sa.Column('genre', sa.Text(), nullable=True),
        sa.Column('magnet_link', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=100), nullable=True),
        sa.Column('queued_time', sa.TIMESTAMP(), nullable=True),
        sa.Column('downloaded_time', sa.TIMESTAMP(), nullable=True),
        sa.Column('added_to_abs_time', sa.TIMESTAMP(), nullable=True),
        sa.Column('estimated_value', sa.Float(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('bitrate', sa.Integer(), nullable=True),
        sa.Column('quality_check', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_downloaded_books_id'), 'downloaded_books', ['id'], unique=False)
    op.create_index(op.f('ix_downloaded_books_title'), 'downloaded_books', ['title'], unique=True)
    op.create_index(op.f('ix_downloaded_books_status'), 'downloaded_books', ['status'], unique=False)

    # Create hardcover_user_mappings table
    op.create_table(
        'hardcover_user_mappings',
        sa.Column('abs_user_id', sa.String(length=255), nullable=False),
        sa.Column('abs_username', sa.String(length=255), nullable=True),
        sa.Column('hardcover_token', sa.String(length=500), nullable=True),
        sa.Column('last_synced_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('abs_user_id')
    )
    op.create_index(op.f('ix_hardcover_user_mappings_abs_user_id'), 'hardcover_user_mappings', ['abs_user_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_hardcover_user_mappings_abs_user_id'), table_name='hardcover_user_mappings')
    op.drop_table('hardcover_user_mappings')

    op.drop_index(op.f('ix_downloaded_books_status'), table_name='downloaded_books')
    op.drop_index(op.f('ix_downloaded_books_title'), table_name='downloaded_books')
    op.drop_index(op.f('ix_downloaded_books_id'), table_name='downloaded_books')
    op.drop_table('downloaded_books')
