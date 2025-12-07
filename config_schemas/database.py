"""
Database Configuration Schema
Validation schema for database connection and performance settings
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
import re


class DatabaseConfig(BaseModel):
    """Database configuration schema."""

    # PostgreSQL settings
    postgresql: Dict[str, Any] = Field(default_factory=dict, description="PostgreSQL connection settings")

    # SQLite settings
    sqlite: Dict[str, Any] = Field(default_factory=dict, description="SQLite connection settings")

    # Connection pool settings
    pool: Dict[str, Any] = Field(default_factory=dict, description="Connection pool configuration")

    # Performance settings
    performance: Dict[str, Any] = Field(default_factory=dict, description="Database performance settings")

    # Migration settings
    migrations: Dict[str, Any] = Field(default_factory=dict, description="Database migration settings")

    # Backup settings
    backup: Dict[str, Any] = Field(default_factory=dict, description="Database backup settings")

    # Monitoring
    monitoring: Dict[str, Any] = Field(default_factory=dict, description="Database monitoring settings")

    @validator('postgresql')
    def validate_postgresql_config(cls, v):
        """Validate PostgreSQL configuration."""
        if v:
            required_fields = ['host', 'port', 'database']
            for field in required_fields:
                if field not in v:
                    raise ValueError(f"PostgreSQL config missing required field: {field}")

            if not isinstance(v.get('port'), int) or v['port'] <= 0 or v['port'] > 65535:
                raise ValueError("PostgreSQL port must be a valid port number")

        return v

    class Config:
        extra = "allow"