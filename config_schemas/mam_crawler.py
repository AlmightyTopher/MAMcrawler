"""
MAM Crawler Configuration Schema
Validation schema for MyAnonamouse.net crawling operations
"""

from pydantic import BaseModel, Field
from typing import Dict, Any


class MamCrawlerConfig(BaseModel):
    """MAM crawler configuration schema."""

    # Site configuration
    site: Dict[str, Any] = Field(default_factory=dict, description="Site configuration")

    # Authentication
    auth: Dict[str, Any] = Field(default_factory=dict, description="Authentication settings")

    # Crawling rules
    rules: Dict[str, Any] = Field(default_factory=dict, description="Crawling rules")

    # Content extraction
    extraction: Dict[str, Any] = Field(default_factory=dict, description="Content extraction settings")

    # Search settings
    search: Dict[str, Any] = Field(default_factory=dict, description="Search configuration")

    # Download settings
    download: Dict[str, Any] = Field(default_factory=dict, description="Download settings")

    # Compliance settings
    compliance: Dict[str, Any] = Field(default_factory=dict, description="MAM compliance rules")

    class Config:
        extra = "allow"