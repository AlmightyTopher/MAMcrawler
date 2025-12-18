"""add_hardcover_id_columns

Revision ID: 4ca08ad584ce
Revises: f4dc3e28448d
Create Date: 2025-12-18 02:36:45.939455

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '4ca08ad584ce'
down_revision = 'f4dc3e28448d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add hardcover_id column to authors table
    op.add_column('authors', sa.Column('hardcover_id', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_authors_hardcover_id'), 'authors', ['hardcover_id'], unique=False)

    # Add hardcover_id column to series table
    op.add_column('series', sa.Column('hardcover_id', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_series_hardcover_id'), 'series', ['hardcover_id'], unique=False)

    # Add hardcover_id column to missing_books table
    op.add_column('missing_books', sa.Column('hardcover_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Remove hardcover_id columns in reverse order
    op.drop_column('missing_books', 'hardcover_id')

    op.drop_index(op.f('ix_series_hardcover_id'), table_name='series')
    op.drop_column('series', 'hardcover_id')

    op.drop_index(op.f('ix_authors_hardcover_id'), table_name='authors')
    op.drop_column('authors', 'hardcover_id')
