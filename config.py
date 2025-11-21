#!/usr/bin/env python3
"""
Secure Configuration Management System for MAMcrawler
====================================================

This module provides centralized, secure configuration management
with proper environment variable handling and validation.
"""

import os
import warnings
from pathlib import Path
from typing import Optional, Dict, Any, List
from pydantic import BaseSettings, Field, validator, SecretStr
from pydantic_settings import BaseSettings as BaseSettingsV2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class SecuritySettings(BaseSettings):
    """Security and API key management settings."""
    
    # API Keys - CRITICAL: These should NOT be hardcoded
    anthropic_api_key: SecretStr = Field(default=None, env="ANTHROPIC_API_KEY")
    google_books_api_key: SecretStr = Field(default=None, env="GOOGLE_BOOKS_API_KEY")
    
    # Database Configuration
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT") 
    postgres_db: str = Field(default="audiobooks", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: SecretStr = Field(default=None, env="POSTGRES_PASSWORD")
    
    class Config:
        env_file_encoding = 'utf-8'
        case_sensitive = True
        # Prevent secrets from being logged
        fields = {
            'anthropic_api_key': {'sensitive': True},
            'google_books_api_key': {'sensitive': True},
            'postgres_password': {'sensitive': True},
        }


class APIEndpoints(BaseSettings):
    """API endpoint configurations."""
    
    # Audiobookshelf API
    abs_url: str = Field(default="http://localhost:13378", env="ABS_URL")
    abs_token: SecretStr = Field(default=None, env="ABS_TOKEN")
    
    # MyAnonamouse credentials (for crawler)
    mam_username: str = Field(default=None, env="MAM_USERNAME")
    mam_password: SecretStr = Field(default=None, env="MAM_PASSWORD")
    
    # qBittorrent API
    qb_host: str = Field(default="localhost", env="QB_HOST")
    qb_port: int = Field(default=8080, env="QB_PORT")
    qb_username: str = Field(default="admin", env="QB_USERNAME")
    qb_password: SecretStr = Field(default=None, env="QB_PASSWORD")
    
    class Config:
        env_file_encoding = 'utf-8'
        case_sensitive = True
        fields = {
            'abs_token': {'sensitive': True},
            'mam_password': {'sensitive': True},
            'qb_password': {'sensitive': True},
        }


class CrawlerSettings(BaseSettings):
    """Crawler and stealth operation settings."""
    
    # Browser settings for stealth crawling
    browser_headless: bool = Field(default=True, env="BROWSER_HEADLESS")
    browser_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        env="BROWSER_USER_AGENT"
    )
    
    # Request throttling
    request_delay_min: float = Field(default=1.0, env="REQUEST_DELAY_MIN")
    request_delay_max: float = Field(default=3.0, env="REQUEST_DELAY_MAX")
    
    # Proxy settings (optional)
    http_proxy: Optional[str] = Field(default=None, env="HTTP_PROXY")
    https_proxy: Optional[str] = Field(default=None, env="HTTPS_PROXY")
    
    # VPN settings (optional)
    wireguard_config: Optional[str] = Field(default=None, env="WIREGUARD_CONFIG")


class DatabaseSettings(BaseSettings):
    """Database connection and performance settings."""
    
    # Connection pool settings
    db_pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    
    # SQLite settings for RAG system
    rag_db_path: str = Field(default="rag_metadata.db", env="RAG_DB_PATH")
    
    # Logging settings
    enable_query_logging: bool = Field(default=False, env="ENABLE_QUERY_LOGGING")


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_file_path: str = Field(default="logs/mamcrawler.log", env="LOG_FILE_PATH")
    max_log_size_mb: int = Field(default=100, env="MAX_LOG_SIZE_MB")
    backup_count: int = Field(default=5, env="BACKUP_COUNT")


class SystemSettings(BaseSettings):
    """System-wide operational settings."""
    
    # Application settings
    app_name: str = Field(default="MAMcrawler", env="APP_NAME")
    app_version: str = Field(default="2.0.0", env="APP_VERSION")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    
    # File paths
    output_dir: str = Field(default="output", env="OUTPUT_DIR")
    temp_dir: str = Field(default="temp", env="TEMP_DIR")
    
    # Performance settings
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, env="REQUEST_TIMEOUT")


class ConfigManager:
    """Centralized configuration manager with validation and security checks."""
    
    def __init__(self):
        self._security = None
        self._api_endpoints = None
        self._crawler = None
        self._database = None
        self._logging = None
        self._system = None
        self._validation_errors = []
    
    @property
    def security(self) -> SecuritySettings:
        """Get security settings with validation."""
        if self._security is None:
            self._security = SecuritySettings()
            self._validate_security_settings()
        return self._security
    
    @property
    def api_endpoints(self) -> APIEndpoints:
        """Get API endpoint settings with validation."""
        if self._api_endpoints is None:
            self._api_endpoints = APIEndpoints()
            self._validate_api_endpoints()
        return self._api_endpoints
    
    @property
    def crawler(self) -> CrawlerSettings:
        """Get crawler settings with validation."""
        if self._crawler is None:
            self._crawler = CrawlerSettings()
        return self._crawler
    
    @property
    def database(self) -> DatabaseSettings:
        """Get database settings with validation."""
        if self._database is None:
            self._database = DatabaseSettings()
        return self._database
    
    @property
    def logging(self) -> LoggingSettings:
        """Get logging settings with validation."""
        if self._logging is None:
            self._logging = LoggingSettings()
            self._create_log_directories()
        return self._logging
    
    @property
    def system(self) -> SystemSettings:
        """Get system settings with validation."""
        if self._system is None:
            self._system = SystemSettings()
            self._create_output_directories()
        return self._system
    
    def _validate_security_settings(self):
        """Validate critical security settings."""
        # Check for required API keys
        if not self._security.anthropic_api_key.get_secret_value():
            self._validation_errors.append("ANTHROPIC_API_KEY is required but not set")
        
        if not self._security.google_books_api_key.get_secret_value():
            self._validation_errors.append("GOOGLE_BOOKS_API_KEY is required but not set")
        
        if not self._security.postgres_password.get_secret_value():
            self._validation_errors.append("POSTGRES_PASSWORD is required but not set")
    
    def _validate_api_endpoints(self):
        """Validate API endpoint configurations."""
        if not self._api_endpoints.abs_token.get_secret_value():
            self._validation_errors.append("ABS_TOKEN is required for Audiobookshelf integration")
        
        if not self._api_endpoints.mam_username:
            self._validation_errors.append("MAM_USERNAME is required for MAM crawler")
        
        if not self._api_endpoints.mam_password.get_secret_value():
            self._validation_errors.append("MAM_PASSWORD is required for MAM crawler")
    
    def _create_log_directories(self):
        """Create log directories if they don't exist."""
        log_path = Path(self._logging.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _create_output_directories(self):
        """Create necessary output directories."""
        output_path = Path(self._system.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        temp_path = Path(self._system.temp_dir)
        temp_path.mkdir(parents=True, exist_ok=True)
    
    def validate_all(self) -> List[str]:
        """Validate all configuration settings."""
        # Force property access to trigger validation
        _ = self.security
        _ = self.api_endpoints
        _ = self.crawler
        _ = self.database
        _ = self.logging
        _ = self.system
        
        return self._validation_errors
    
    def get_masked_env_vars(self) -> Dict[str, str]:
        """Get environment variables with sensitive values masked."""
        masked_vars = {}
        
        # Security settings
        for field_name in ["ANTHROPIC_API_KEY", "GOOGLE_BOOKS_API_KEY", "POSTGRES_PASSWORD"]:
            value = os.getenv(field_name)
            if value:
                masked_vars[field_name] = self._mask_secret(value)
            else:
                masked_vars[field_name] = "NOT_SET"
        
        # API endpoint settings
        for field_name in ["ABS_TOKEN", "MAM_PASSWORD", "QB_PASSWORD"]:
            value = os.getenv(field_name)
            if value:
                masked_vars[field_name] = self._mask_secret(value)
            else:
                masked_vars[field_name] = "NOT_SET"
        
        # Non-sensitive settings
        non_sensitive_vars = [
            "ABS_URL", "MAM_USERNAME", "QB_HOST", "QB_PORT", "QB_USERNAME",
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", "POSTGRES_USER",
            "LOG_LEVEL", "DEBUG_MODE"
        ]
        
        for var in non_sensitive_vars:
            value = os.getenv(var)
            if value:
                masked_vars[var] = value
            else:
                masked_vars[var] = "NOT_SET"
        
        return masked_vars
    
    def _mask_secret(self, secret: str) -> str:
        """Mask secret string for safe display."""
        if len(secret) <= 8:
            return "*" * len(secret)
        return secret[:4] + "*" * (len(secret) - 8) + secret[-4:]
    
    def check_environment(self) -> Dict[str, Any]:
        """Check current environment setup status."""
        validation_errors = self.validate_all()
        
        return {
            "virtual_environment": self._check_virtual_environment(),
            "validation_errors": validation_errors,
            "configuration_complete": len(validation_errors) == 0,
            "masked_env_vars": self.get_masked_env_vars()
        }
    
    def _check_virtual_environment(self) -> bool:
        """Check if running in a virtual environment."""
        return (
            hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
            os.environ.get('VIRTUAL_ENV') is not None
        )


# Global configuration manager instance
config = ConfigManager()


def validate_environment() -> bool:
    """Validate the complete environment setup."""
    config_status = config.check_environment()
    
    if not config_status["virtual_environment"]:
        warnings.warn(
            "NOT running in a virtual environment! "
            "This is a critical security requirement. "
            "Please create and activate a virtual environment.",
            UserWarning
        )
        return False
    
    if not config_status["configuration_complete"]:
        error_msg = "Configuration validation failed:\n" + "\n".join(
            f"- {error}" for error in config_status["validation_errors"]
        )
        raise ValueError(error_msg)
    
    return True


# Security validation on import
try:
    validate_environment()
except Exception as e:
    warnings.warn(f"Configuration validation failed: {e}", UserWarning)


if __name__ == "__main__":
    # Quick configuration test
    import sys
    
    print("MAMcrawler Configuration Check")
    print("=" * 50)
    
    try:
        config_status = config.check_environment()
        
        print(f"Virtual Environment: {'✓' if config_status['virtual_environment'] else '✗'}")
        print(f"Configuration Complete: {'✓' if config_status['configuration_complete'] else '✗'}")
        
        if config_status["validation_errors"]:
            print("\nConfiguration Errors:")
            for error in config_status["validation_errors"]:
                print(f"- {error}")
        
        print("\nEnvironment Variables (Masked):")
        for key, value in config_status["masked_env_vars"].items():
            print(f"  {key}: {value}")
            
    except Exception as e:
        print(f"Configuration check failed: {e}")
        sys.exit(1)