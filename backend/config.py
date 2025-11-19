"""
Configuration management for Audiobook Automation System
Loads environment variables and provides centralized config access
"""

import os
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


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

    # Admin Panel JWT Authentication
    JWT_SECRET_KEY: Optional[str] = None  # Will be auto-generated if not set
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Password Security
    PASSWORD_SALT: str = "mamcrawler_salt_change_in_production"

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
