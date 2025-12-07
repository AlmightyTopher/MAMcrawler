"""
Audiobook Automation Configuration Schema
Validation schema for automated audiobook batch processing
"""

from pydantic import BaseModel, Field
from typing import Dict, Any


class AudiobookAutomationConfig(BaseModel):
    """Audiobook automation configuration schema."""

    # Scheduling
    schedule: Dict[str, Any] = Field(default_factory=dict, description="Scheduling configuration")

    # Query settings
    query: Dict[str, Any] = Field(default_factory=dict, description="Query settings")

    # Genre filtering
    genres: Dict[str, Any] = Field(default_factory=dict, description="Genre filtering")

    # Download settings
    download: Dict[str, Any] = Field(default_factory=dict, description="Download configuration")

    # Quality filters
    quality: Dict[str, Any] = Field(default_factory=dict, description="Quality filters")

    # Metadata processing
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata processing")

    # Notification settings
    notifications: Dict[str, Any] = Field(default_factory=dict, description="Notification settings")

    # Error handling
    error_handling: Dict[str, Any] = Field(default_factory=dict, description="Error handling")

    # Performance
    performance: Dict[str, Any] = Field(default_factory=dict, description="Performance settings")

    # Logging
    logging: Dict[str, Any] = Field(default_factory=dict, description="Logging configuration")

    class Config:
        extra = "allow"