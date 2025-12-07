"""
Application Configuration Schema
Validation schema for core application settings
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
import re


class AppConfig(BaseModel):
    """Application configuration schema."""

    # Basic app info
    name: str = Field(..., min_length=1, max_length=100, description="Application name")
    version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$', description="Application version (semantic versioning)")
    description: str = Field("", max_length=500, description="Application description")
    author: str = Field("", max_length=100, description="Application author")

    # Environment settings
    environment: str = Field("development", pattern=r'^(development|staging|production)$', description="Runtime environment")
    debug: bool = Field(False, description="Debug mode enabled")
    log_level: str = Field("INFO", pattern=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$', description="Logging level")

    # Feature flags
    features: dict = Field(default_factory=dict, description="Feature flags")

    # Performance settings
    performance: dict = Field(default_factory=dict, description="Performance configuration")

    # File paths
    paths: dict = Field(default_factory=dict, description="File system paths")

    # System settings
    system: dict = Field(default_factory=dict, description="System-wide settings")

    @validator('version')
    def validate_version(cls, v):
        """Validate semantic version format."""
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError('Version must follow semantic versioning (x.y.z)')
        return v

    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment value."""
        valid_envs = ['development', 'staging', 'production']
        if v not in valid_envs:
            raise ValueError(f'Environment must be one of: {valid_envs}')
        return v

    class Config:
        extra = "allow"  # Allow extra fields for flexibility