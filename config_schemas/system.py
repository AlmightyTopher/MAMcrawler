"""
System Configuration Schema
Validation schema for general system-wide settings
"""

from pydantic import BaseModel, Field
from typing import Dict, Any


class SystemConfig(BaseModel):
    """System configuration schema."""

    # Application settings
    app: Dict[str, Any] = Field(default_factory=dict, description="Application settings")

    # Environment settings
    environment: Dict[str, Any] = Field(default_factory=dict, description="Environment configuration")

    # File system paths
    paths: Dict[str, Any] = Field(default_factory=dict, description="File system paths")

    # Performance settings
    performance: Dict[str, Any] = Field(default_factory=dict, description="Performance configuration")

    # Resource management
    resources: Dict[str, Any] = Field(default_factory=dict, description="Resource management")

    # Monitoring and health checks
    monitoring: Dict[str, Any] = Field(default_factory=dict, description="Monitoring settings")

    # Backup settings
    backup: Dict[str, Any] = Field(default_factory=dict, description="Backup configuration")

    # Update settings
    updates: Dict[str, Any] = Field(default_factory=dict, description="Update settings")

    class Config:
        extra = "allow"