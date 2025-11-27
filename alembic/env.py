"""
Alembic environment configuration for async SQLAlchemy

This file handles:
- Database connection configuration
- Target metadata for schema comparison
- Migration execution (online/offline modes)
"""

import os
import asyncio
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from alembic import context

# Import settings and models
from backend.config import get_settings
from backend.database import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from settings
settings = get_settings()


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode

    This configures the context with just a URL without the
    Engine, though an Engine is acceptable here as well. By
    skipping the Engine creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """
    Execute migrations given a database connection

    Args:
        connection: Active database connection
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode

    In this scenario we need to create an Engine and associate
    a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    # Create async engine
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    # Run offline migrations
    run_migrations_offline()
else:
    # Run online migrations
    asyncio.run(run_migrations_online())
