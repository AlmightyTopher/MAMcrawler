"""
Configuration management for Audiobook Automation System
Loads environment variables and provides centralized config access
"""

import os
import re
import sys
import logging
from pathlib import Path
from functools import lru_cache
from typing import Optional, List, Dict, Any

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator, model_validator

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ============================================================================
    # API Configuration
    # ============================================================================
    API_TITLE: str = "Audiobook Automation System API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "REST API for managing audiobook discovery, metadata, and downloads"
    DEBUG: bool = False

    # ============================================================================
    # Database Configuration
    # ============================================================================
    DATABASE_URL: str = "postgresql://audiobook_user:audiobook_password@localhost:5432/audiobook_automation"
    DATABASE_ECHO: bool = False

    # ============================================================================
    # Authentication
    # ============================================================================
    API_KEY: str = "your-secret-api-key-change-in-production"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ============================================================================
    # Audiobookshelf Integration
    # ============================================================================
    ABS_URL: str = "http://localhost:13378"
    ABS_TOKEN: str = ""
    ABS_TIMEOUT: int = 30

    # ============================================================================
    # qBittorrent Integration
    # ============================================================================
    QB_HOST: str = "192.168.0.48"
    QB_PORT: int = 52095
    QB_USERNAME: str = "TopherGutbrod"
    QB_PASSWORD: str = ""
    QB_TIMEOUT: int = 30
    QB_API_VERSION: str = "v2"

    # ============================================================================
    # Prowlarr Integration
    # ============================================================================
    PROWLARR_URL: str = "http://localhost:9696"
    PROWLARR_API_KEY: str = ""
    PROWLARR_TIMEOUT: int = 30

    # ============================================================================
    # Google Books API
    # ============================================================================
    GOOGLE_BOOKS_API_KEY: str = ""
    GOOGLE_BOOKS_TIMEOUT: int = 10
    GOOGLE_BOOKS_RATE_LIMIT: int = 100  # Requests per day

    # ============================================================================
    # Goodreads Scraper Configuration
    # ============================================================================
    GOODREADS_RATE_LIMIT_SECONDS: float = 3.0
    GOODREADS_TIMEOUT: int = 30
    GOODREADS_MAX_RETRIES: int = 3

    # ============================================================================
    # MAM Crawler Integration
    # ============================================================================
    MAM_USERNAME: str = ""
    MAM_PASSWORD: str = ""
    MAM_RATE_LIMIT_MIN: int = 3
    MAM_RATE_LIMIT_MAX: int = 10
    MAM_MAX_PAGES_PER_SESSION: int = 50

    # ============================================================================
    # Scheduler Configuration
    # ============================================================================
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_JOB_STORE: str = "sqlalchemy"

    # Scheduled task times (cron format)
    TASK_MAM_TIME: str = "0 2 * * *"  # Daily 2:00 AM
    TASK_TOP10_TIME: str = "0 3 * * 6"  # Sunday 3:00 AM
    TASK_METADATA_FULL_TIME: str = "0 4 1 * *"  # 1st of month 4:00 AM
    TASK_METADATA_NEW_TIME: str = "30 4 * * 6"  # Sunday 4:30 AM
    TASK_SERIES_TIME: str = "0 3 2 * *"  # 2nd of month 3:00 AM
    TASK_AUTHOR_TIME: str = "0 3 3 * *"  # 3rd of month 3:00 AM
    TASK_GAPS_TIME: str = "0 1 * * *"  # Daily 1:00 AM

    # ============================================================================
    # Gap Analysis Configuration
    # ============================================================================
    GAP_ANALYSIS_ENABLED: bool = True
    GAP_MAX_DOWNLOADS_PER_RUN: int = 10
    GAP_SERIES_PRIORITY: bool = True
    GAP_AUTHOR_PRIORITY: bool = True
    MAM_MIN_SEEDS: int = 1
    MAM_TITLE_MATCH_THRESHOLD: float = 0.7

    # ============================================================================
    # Data Retention Policy
    # ============================================================================
    HISTORY_RETENTION_DAYS: int = 30
    FAILED_ATTEMPTS_RETENTION: str = "permanent"  # Never deleted

    # ============================================================================
    # File Paths
    # ============================================================================
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    GUIDES_OUTPUT_DIR: Path = PROJECT_ROOT / "guides_output"
    LOGS_DIR: Path = PROJECT_ROOT / "logs"

    # ============================================================================
    # Features
    # ============================================================================
    ENABLE_API_LOGGING: bool = True
    ENABLE_METADATA_CORRECTION: bool = True
    ENABLE_SERIES_COMPLETION: bool = True
    ENABLE_AUTHOR_COMPLETION: bool = True
    ENABLE_TOP10_DISCOVERY: bool = True
    ENABLE_MAM_SCRAPING: bool = True
    ENABLE_GAP_ANALYSIS: bool = True

    # ============================================================================
    # Genres for Top-10 Feature
    # ============================================================================
    ENABLED_GENRES: list = [
        "Science Fiction",
        "Fantasy",
        "Mystery",
        "Thriller"
    ]

    DISABLED_GENRES: list = [
        "Romance",
        "Erotica",
        "Self-Help"
    ]

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Allow extra fields from .env without validation errors
    )

    # ============================================================================
    # Field Validators
    # ============================================================================

    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            raise ValueError("DATABASE_URL is required")

        valid_schemes = ['postgresql://', 'postgres://', 'sqlite://']
        if not any(v.startswith(scheme) for scheme in valid_schemes):
            raise ValueError(
                f"DATABASE_URL must start with one of: {', '.join(valid_schemes)}"
            )
        return v

    @field_validator('ABS_URL', 'PROWLARR_URL')
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        """Validate URL format for service endpoints."""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError(f"URL must start with http:// or https://: {v}")
        return v.rstrip('/') if v else v

    @field_validator('QB_PORT')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535: {v}")
        return v

    @field_validator('MAM_TITLE_MATCH_THRESHOLD')
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """Validate match threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Threshold must be between 0 and 1: {v}")
        return v

    @field_validator('TASK_MAM_TIME', 'TASK_TOP10_TIME', 'TASK_METADATA_FULL_TIME',
                     'TASK_METADATA_NEW_TIME', 'TASK_SERIES_TIME', 'TASK_AUTHOR_TIME',
                     'TASK_GAPS_TIME')
    @classmethod
    def validate_cron_format(cls, v: str) -> str:
        """Validate cron expression format."""
        if not v:
            return v

        parts = v.split()
        if len(parts) != 5:
            raise ValueError(
                f"Invalid cron format (need 5 parts: min hour day month weekday): {v}"
            )
        return v

    @field_validator('GAP_MAX_DOWNLOADS_PER_RUN')
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate positive integer."""
        if v < 0:
            raise ValueError(f"Value must be non-negative: {v}")
        return v

    # ============================================================================
    # Validation Methods
    # ============================================================================

    def validate_for_production(self) -> List[str]:
        """
        Validate configuration for production use.

        Returns:
            List of warning messages for non-critical issues

        Raises:
            ConfigurationError: For critical configuration issues
        """
        errors = []
        warnings = []

        # Critical: Check for default/insecure values
        if self.API_KEY == "your-secret-api-key-change-in-production":
            errors.append("API_KEY is using default value - must be changed for production")

        if self.SECRET_KEY == "your-secret-key-change-in-production":
            errors.append("SECRET_KEY is using default value - must be changed for production")

        # Critical: Database password check (for PostgreSQL)
        if 'postgresql' in self.DATABASE_URL:
            if 'audiobook_password' in self.DATABASE_URL:
                errors.append("DATABASE_URL is using default password - must be changed for production")

        # Warnings for missing optional integrations
        if not self.ABS_TOKEN:
            warnings.append("ABS_TOKEN not set - Audiobookshelf integration will not work")

        if not self.QB_PASSWORD:
            warnings.append("QB_PASSWORD not set - qBittorrent integration will not work")

        if not self.PROWLARR_API_KEY:
            warnings.append("PROWLARR_API_KEY not set - Prowlarr integration will not work")

        if not self.GOOGLE_BOOKS_API_KEY:
            warnings.append("GOOGLE_BOOKS_API_KEY not set - Google Books API will not work")

        if not self.MAM_USERNAME or not self.MAM_PASSWORD:
            warnings.append("MAM_USERNAME/MAM_PASSWORD not set - MAM crawling will not work")

        # Check directory existence
        if not self.GUIDES_OUTPUT_DIR.exists():
            warnings.append(f"GUIDES_OUTPUT_DIR does not exist: {self.GUIDES_OUTPUT_DIR}")

        if not self.LOGS_DIR.exists():
            warnings.append(f"LOGS_DIR does not exist: {self.LOGS_DIR}")

        # Raise for critical errors
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ConfigurationError(error_msg)

        return warnings

    def get_enabled_features(self) -> Dict[str, bool]:
        """Get dictionary of enabled features."""
        return {
            "api_logging": self.ENABLE_API_LOGGING,
            "metadata_correction": self.ENABLE_METADATA_CORRECTION,
            "series_completion": self.ENABLE_SERIES_COMPLETION,
            "author_completion": self.ENABLE_AUTHOR_COMPLETION,
            "top10_discovery": self.ENABLE_TOP10_DISCOVERY,
            "mam_scraping": self.ENABLE_MAM_SCRAPING,
            "gap_analysis": self.ENABLE_GAP_ANALYSIS,
        }

    def get_integration_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of external integrations."""
        return {
            "audiobookshelf": {
                "configured": bool(self.ABS_TOKEN),
                "url": self.ABS_URL,
            },
            "qbittorrent": {
                "configured": bool(self.QB_PASSWORD),
                "host": f"{self.QB_HOST}:{self.QB_PORT}",
            },
            "prowlarr": {
                "configured": bool(self.PROWLARR_API_KEY),
                "url": self.PROWLARR_URL,
            },
            "google_books": {
                "configured": bool(self.GOOGLE_BOOKS_API_KEY),
                "rate_limit": self.GOOGLE_BOOKS_RATE_LIMIT,
            },
            "mam": {
                "configured": bool(self.MAM_USERNAME and self.MAM_PASSWORD),
                "rate_limit": f"{self.MAM_RATE_LIMIT_MIN}-{self.MAM_RATE_LIMIT_MAX}s",
            },
        }

    def summary(self) -> str:
        """Get configuration summary string."""
        features = self.get_enabled_features()
        integrations = self.get_integration_status()

        lines = [
            f"Configuration Summary:",
            f"  Environment: {'DEBUG' if self.DEBUG else 'PRODUCTION'}",
            f"  API Version: {self.API_VERSION}",
            f"",
            f"  Features:",
        ]
        for name, enabled in features.items():
            status = "enabled" if enabled else "disabled"
            lines.append(f"    - {name}: {status}")

        lines.append(f"")
        lines.append(f"  Integrations:")
        for name, info in integrations.items():
            status = "configured" if info["configured"] else "NOT configured"
            lines.append(f"    - {name}: {status}")

        return "\n".join(lines)


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings (cached)
    Loads from environment variables and .env file
    """
    return Settings()


# Convenience function to access settings throughout the app
def get_config() -> Settings:
    """Get current configuration"""
    return get_settings()


def validate_config(production_mode: bool = False) -> None:
    """
    Validate configuration on application startup.

    Args:
        production_mode: If True, enforce production requirements

    Raises:
        ConfigurationError: If validation fails
    """
    settings = get_settings()

    logger.info("Validating configuration...")

    if production_mode:
        warnings = settings.validate_for_production()
        for warning in warnings:
            logger.warning(f"Config warning: {warning}")

    # Log configuration summary
    logger.info(settings.summary())

    # Create required directories
    for dir_path in [settings.GUIDES_OUTPUT_DIR, settings.LOGS_DIR]:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")

    logger.info("Configuration validation complete")


def init_config(production_mode: Optional[bool] = None) -> Settings:
    """
    Initialize and validate configuration.

    This should be called at application startup.

    Args:
        production_mode: Override for production validation.
                        If None, uses DEBUG setting to determine.

    Returns:
        Validated Settings instance

    Raises:
        ConfigurationError: If validation fails
    """
    settings = get_settings()

    # Determine production mode
    if production_mode is None:
        production_mode = not settings.DEBUG

    # Validate
    validate_config(production_mode=production_mode)

    return settings
