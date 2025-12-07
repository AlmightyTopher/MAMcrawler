"""
Security Configuration Schema
Validation schema for security settings and encryption configuration
"""

from pydantic import BaseModel, Field
from typing import Dict, Any


class SecurityConfig(BaseModel):
    """Security configuration schema."""

    # Encryption settings
    encryption: Dict[str, Any] = Field(default_factory=dict, description="Encryption configuration")

    # Secret management
    secrets: Dict[str, Any] = Field(default_factory=dict, description="Secret management settings")

    # API key validation
    api_keys: Dict[str, Any] = Field(default_factory=dict, description="API key validation")

    # Authentication
    auth: Dict[str, Any] = Field(default_factory=dict, description="Authentication settings")

    # Network security
    network: Dict[str, Any] = Field(default_factory=dict, description="Network security")

    # Data protection
    data_protection: Dict[str, Any] = Field(default_factory=dict, description="Data protection")

    # Compliance
    compliance: Dict[str, Any] = Field(default_factory=dict, description="Compliance settings")

    # Virtual environment
    virtual_environment: Dict[str, Any] = Field(default_factory=dict, description="Virtual environment settings")

    class Config:
        extra = "allow"