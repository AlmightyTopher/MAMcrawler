"""
API Endpoints Configuration Schema
Validation schema for external API service configurations
"""

from pydantic import BaseModel, Field, validator, SecretStr
from typing import Optional, Dict, Any, List
import re


class APIEndpointsConfig(BaseModel):
    """API endpoints configuration schema."""

    # Audiobookshelf API
    audiobookshelf: Dict[str, Any] = Field(default_factory=dict, description="Audiobookshelf API settings")

    # MyAnonamouse API
    myanonamouse: Dict[str, Any] = Field(default_factory=dict, description="MyAnonamouse API settings")

    # qBittorrent API
    qbittorrent: Dict[str, Any] = Field(default_factory=dict, description="qBittorrent API settings")

    # Goodreads API
    goodreads: Dict[str, Any] = Field(default_factory=dict, description="Goodreads API settings")

    # Google Books API
    google_books: Dict[str, Any] = Field(default_factory=dict, description="Google Books API settings")

    # Prowlarr API
    prowlarr: Dict[str, Any] = Field(default_factory=dict, description="Prowlarr API settings")

    # Hardcover API
    hardcover: Dict[str, Any] = Field(default_factory=dict, description="Hardcover API settings")

    # External services
    external: Dict[str, Any] = Field(default_factory=dict, description="External service settings")

    @validator('audiobookshelf')
    def validate_audiobookshelf_config(cls, v):
        """Validate Audiobookshelf configuration."""
        if v:
            if 'url' in v and not v['url'].startswith(('http://', 'https://')):
                raise ValueError("Audiobookshelf URL must start with http:// or https://")
        return v

    @validator('myanonamouse')
    def validate_myanonamouse_config(cls, v):
        """Validate MyAnonamouse configuration."""
        if v:
            if 'base_url' in v and not v['base_url'].startswith(('http://', 'https://')):
                raise ValueError("MyAnonamouse base URL must start with http:// or https://")
        return v

    class Config:
        extra = "allow"