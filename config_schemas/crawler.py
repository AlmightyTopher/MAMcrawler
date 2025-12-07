"""
Crawler Configuration Schema
Validation schema for web crawling and stealth operation settings
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List


class CrawlerConfig(BaseModel):
    """Crawler configuration schema."""

    # Browser settings
    browser: Dict[str, Any] = Field(default_factory=dict, description="Browser configuration")

    # Request throttling
    rate_limiting: Dict[str, Any] = Field(default_factory=dict, description="Rate limiting settings")

    # Stealth settings
    stealth: Dict[str, Any] = Field(default_factory=dict, description="Stealth operation settings")

    # Proxy settings
    proxy: Dict[str, Any] = Field(default_factory=dict, description="Proxy configuration")

    # VPN settings
    vpn: Dict[str, Any] = Field(default_factory=dict, description="VPN configuration")

    # Session management
    session: Dict[str, Any] = Field(default_factory=dict, description="Session management")

    # Error handling
    error_handling: Dict[str, Any] = Field(default_factory=dict, description="Error handling configuration")

    # Content extraction
    extraction: Dict[str, Any] = Field(default_factory=dict, description="Content extraction settings")

    class Config:
        extra = "allow"