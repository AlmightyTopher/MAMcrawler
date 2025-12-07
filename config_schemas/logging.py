"""
Logging Configuration Schema
Validation schema for centralized logging settings
"""

from pydantic import BaseModel, Field
from typing import Dict, Any


class LoggingConfig(BaseModel):
    """Logging configuration schema."""

    # Console logging
    console: Dict[str, Any] = Field(default_factory=dict, description="Console logging settings")

    # File logging
    file: Dict[str, Any] = Field(default_factory=dict, description="File logging settings")

    # Error logging
    error_file: Dict[str, Any] = Field(default_factory=dict, description="Error logging settings")

    # Component-specific logging levels
    components: Dict[str, Any] = Field(default_factory=dict, description="Component logging levels")

    # External service logging
    external: Dict[str, Any] = Field(default_factory=dict, description="External service logging")

    # Performance logging
    performance: Dict[str, Any] = Field(default_factory=dict, description="Performance logging")

    # Security logging
    security: Dict[str, Any] = Field(default_factory=dict, description="Security logging")

    class Config:
        extra = "allow"