"""
Configuration management for Audiobook Automation System
Loads environment variables and provides centralized config access

SECURITY NOTE:
- All sensitive credentials are loaded from .env file (never hardcoded)
- .env file is in .gitignore and never committed to version control
- Production deployment requires proper secrets management (Vault, AWS Secrets Manager, etc.)
- Use environment-specific .env files for dev/staging/production
"""

import os
import sys
from pathlib import Path
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ============================================================================
    # API Configuration
    # ============================================================================
    API_TITLE: str = "Audiobook Automation System API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "REST API for managing audiobook discovery, metadata, and downloads"
    DEBUG: bool = False
    DEV_TOOLS: bool = False  # Enable development tools (auto-reload, etc.)
    API_DOCS: bool = True  # Enable API documentation endpoints
    SECURITY_HEADERS: bool = True  # Enable security headers middleware

    # ============================================================================
    # CORS Configuration
    # ============================================================================
    # Comma-separated list of allowed origins for CORS
    # Production: Set to specific domains only
    # Development: Can include localhost
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    
    # Comma-separated list of allowed hosts
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"

    # ============================================================================
    # Server Configuration
    # ============================================================================
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # ============================================================================
    # Database Configuration
    # ============================================================================
    DATABASE_URL: str = "postgresql://audiobook_user:audiobook_password@localhost:5432/audiobook_automation"
    DATABASE_ECHO: bool = False

    # ============================================================================
    # Authentication
    # ============================================================================
    # CRITICAL: These MUST be set in environment variables (from .env file)
    # Never hardcode secrets in production code
    API_KEY: str = ""  # Load from environment, will validate on init
    SECRET_KEY: str = ""  # Load from environment, will validate on init
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Admin Panel JWT Authentication
    JWT_SECRET_KEY: Optional[str] = None  # Will be auto-generated if not set
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Password Security
    # CRITICAL: Must be set in environment for production
    PASSWORD_SALT: str = ""  # Load from environment, will validate on init

    # ============================================================================
    # Audiobookshelf Integration
    # ============================================================================
    ABS_URL: str = "http://localhost:13378"
    ABS_TOKEN: str = ""
    ABS_TIMEOUT: int = 30

    # ============================================================================
    # qBittorrent Integration
    # ============================================================================
    QB_HOST: str = "http://localhost"
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
    # Safety & Compliance Configuration
    # ============================================================================
    # Protected operations that require explicit flags
    PROTECTED_OPERATIONS: list = [
        "delete_audiobook",
        "delete_metadata",
        "drm_removal",
        "replace_audio_file",
        "modify_env_file"
    ]

    # DRM Removal Configuration (opt-in only)
    ALLOW_DRM_REMOVAL: bool = False  # Must be explicitly enabled in .env

    # Backup Configuration
    BACKUP_ENABLED: bool = True
    BACKUP_DIR: Path = PROJECT_ROOT / "backups"
    BACKUP_RETENTION_DAYS: int = 30

    # Audit Logging
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_DIR: Path = PROJECT_ROOT / "logs" / "audit"

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

    @model_validator(mode='after')
    def validate_secrets(self) -> 'Settings':
        """
        Validate that critical secrets are set
        Called after model initialization
        """
        is_production = os.getenv("ENV", "").lower() == "production"

        if is_production:
            # In production, all critical secrets MUST be set
            if not self.API_KEY or self.API_KEY == "":
                raise ValueError(
                    "CRITICAL: API_KEY not set in environment variables. "
                    "Set via .env file or environment variable."
                )
            if not self.SECRET_KEY or self.SECRET_KEY == "":
                raise ValueError(
                    "CRITICAL: SECRET_KEY not set in environment variables. "
                    "Set via .env file or environment variable."
                )
            if not self.PASSWORD_SALT or self.PASSWORD_SALT == "":
                raise ValueError(
                    "CRITICAL: PASSWORD_SALT not set in environment variables. "
                    "Set via .env file or environment variable."
                )

        return self

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
