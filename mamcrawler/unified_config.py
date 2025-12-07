#!/usr/bin/env python3
"""
Unified Configuration Management System for MAMcrawler
======================================================

This module provides centralized, secure configuration management
with proper environment variable handling and validation.
Combines advanced security features with RAG and crawler settings.
"""

import os
import sys
import warnings
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from pydantic import Field, validator, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


# ============================================================================
# SECURITY AND API CONFIGURATION
# ============================================================================

class SecuritySettings(BaseSettings):
    """Security and API key management settings."""
    
    # API Keys - CRITICAL: These should NOT be hardcoded
    anthropic_api_key: SecretStr = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    google_books_api_key: SecretStr = Field(default=None, validation_alias="GOOGLE_BOOKS_API_KEY")
    
    # Database Configuration
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT") 
    postgres_db: str = Field(default="audiobooks", validation_alias="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", validation_alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(default=None, validation_alias="POSTGRES_PASSWORD")
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=True
    )


class APIEndpoints(BaseSettings):
    """API endpoint configurations."""
    
    # Audiobookshelf API
    abs_url: str = Field(default="http://localhost:13378", validation_alias="ABS_URL")
    abs_token: SecretStr = Field(default=None, validation_alias="ABS_TOKEN")
    
    # MyAnonamouse credentials (for crawler)
    mam_username: str = Field(default=None, validation_alias="MAM_USERNAME")
    mam_password: SecretStr = Field(default=None, validation_alias="MAM_PASSWORD")
    
    # qBittorrent API
    qb_host: str = Field(default="localhost", validation_alias="QB_HOST")
    qb_port: int = Field(default=8080, validation_alias="QB_PORT")
    qb_username: str = Field(default="admin", validation_alias="QB_USERNAME")
    qb_password: SecretStr = Field(default=None, validation_alias="QB_PASSWORD")
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=True
    )


# ============================================================================
# CRAWLER CONFIGURATION
# ============================================================================

class CrawlerSettings(BaseSettings):
    """Crawler and stealth operation settings."""
    
    # Browser settings for stealth crawling
    browser_headless: bool = Field(default=True, validation_alias="BROWSER_HEADLESS")
    browser_user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        validation_alias="BROWSER_USER_AGENT"
    )
    
    # Request throttling
    request_delay_min: float = Field(default=1.0, validation_alias="REQUEST_DELAY_MIN")
    request_delay_max: float = Field(default=3.0, validation_alias="REQUEST_DELAY_MAX")
    
    # Proxy settings (optional)
    http_proxy: Optional[str] = Field(default=None, validation_alias="HTTP_PROXY")
    https_proxy: Optional[str] = Field(default=None, validation_alias="HTTPS_PROXY")
    
    # VPN settings (optional)
    wireguard_config: Optional[str] = Field(default=None, validation_alias="WIREGUARD_CONFIG")


# ============================================================================
# RAG CONFIGURATION
# ============================================================================

class RAGSettings(BaseSettings):
    """RAG (Retrieval-Augmented Generation) system configuration."""
    
    # Model configuration
    model_name: str = Field(default="all-MiniLM-L6-v2", validation_alias="RAG_MODEL_NAME")
    dimension: int = Field(default=384, validation_alias="RAG_DIMENSION")
    top_k: int = Field(default=5, validation_alias="RAG_TOP_K")
    llm_model: str = Field(default="claude-haiku-4-5", validation_alias="RAG_LLM_MODEL")
    max_tokens: int = Field(default=1500, validation_alias="RAG_MAX_TOKENS")
    
    # File paths
    index_path: str = Field(default="index.faiss", validation_alias="RAG_INDEX_PATH")
    db_path: str = Field(default="metadata.sqlite", validation_alias="RAG_DB_PATH")
    
    # Header splitting configuration
    headers_to_split: List[Tuple[str, str]] = Field(
        default_factory=lambda: [("#", "H1"), ("##", "H2"), ("###", "H3")],
        validation_alias="RAG_HEADERS_TO_SPLIT"
    )
    
    # Remote API usage mode
    remote_mode: str = Field(
        default="ask",
        validation_alias="REMOTE_MODE",
        description="Remote API usage mode: 'ask', 'off', or 'on'"
    )
    
    model_config = SettingsConfigDict(
        protected_namespaces=('settings_',),
        env_file_encoding='utf-8'
    )
    
    @validator('remote_mode')
    def validate_remote_mode(cls, v):
        if v not in ['ask', 'off', 'on']:
            raise ValueError("remote_mode must be 'ask', 'off', or 'on'")
        return v


# ============================================================================
# OUTPUT AND SYSTEM CONFIGURATION
# ============================================================================

class OutputSettings(BaseSettings):
    """Configuration for output directories and files."""
    
    guides_dir: str = Field(default="guides_output", validation_alias="GUIDES_DIR")
    forum_dir: str = Field(default="forum_qbittorrent_output", validation_alias="FORUM_DIR")
    state_file: str = Field(default="crawler_state.json", validation_alias="STATE_FILE")
    log_file: str = Field(default="stealth_crawler.log", validation_alias="LOG_FILE")


class SystemSettings(BaseSettings):
    """System-wide operational settings."""
    
    # Application settings
    app_name: str = Field(default="MAMcrawler", validation_alias="APP_NAME")
    app_version: str = Field(default="2.0.0", validation_alias="APP_VERSION")
    debug_mode: bool = Field(default=False, validation_alias="DEBUG_MODE")
    
    # File paths
    output_dir: str = Field(default="output", validation_alias="OUTPUT_DIR")
    temp_dir: str = Field(default="temp", validation_alias="TEMP_DIR")
    
    # Performance settings
    max_concurrent_requests: int = Field(default=10, validation_alias="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, validation_alias="REQUEST_TIMEOUT")
    
    # Database settings
    db_pool_size: int = Field(default=10, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, validation_alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, validation_alias="DB_POOL_TIMEOUT")
    
    # Logging settings
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        validation_alias="LOG_FORMAT"
    )
    log_file_path: str = Field(default="logs/mamcrawler.log", validation_alias="LOG_FILE_PATH")
    max_log_size_mb: int = Field(default=100, validation_alias="MAX_LOG_SIZE_MB")
    backup_count: int = Field(default=5, validation_alias="BACKUP_COUNT")


# ============================================================================
# LEGACY COMPATIBILITY CONSTANTS
# ============================================================================

# Shared user agents (kept up-to-date)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Allowed paths (single source of truth)
ALLOWED_PATHS = [
    "/",  # homepage
    "/t/",  # torrent pages (public)
    "/tor/browse.php",  # browse page
    "/tor/search.php",  # search results
    "/guides/",  # guides section
    "/f/",  # forum sections (public)
]

# Forbidden patterns
FORBIDDEN_PATTERNS = [
    "/user/",
    "/account/",
    "/admin/",
    "/mod/",
    "/login",
    "/register",
    "/upload",
    "/download",
    "/api/",
]


# ============================================================================
# UNIFIED CONFIGURATION MANAGER
# ============================================================================

class ConfigManager:
    """Centralized configuration manager with validation and security checks."""
    
    def __init__(self):
        self._security = None
        self._api_endpoints = None
        self._crawler = None
        self._rag = None
        self._output = None
        self._system = None
    
    @property
    def security(self) -> SecuritySettings:
        """Get security settings (lazy loaded)."""
        if self._security is None:
            self._security = SecuritySettings()
        return self._security
    
    @property
    def api_endpoints(self) -> APIEndpoints:
        """Get API endpoint settings (lazy loaded)."""
        if self._api_endpoints is None:
            self._api_endpoints = APIEndpoints()
        return self._api_endpoints
    
    @property
    def crawler(self) -> CrawlerSettings:
        """Get crawler settings (lazy loaded)."""
        if self._crawler is None:
            self._crawler = CrawlerSettings()
        return self._crawler
    
    @property
    def rag(self) -> RAGSettings:
        """Get RAG settings (lazy loaded)."""
        if self._rag is None:
            self._rag = RAGSettings()
        return self._rag
    
    @property
    def output(self) -> OutputSettings:
        """Get output settings (lazy loaded)."""
        if self._output is None:
            self._output = OutputSettings()
        return self._output
    
    @property
    def system(self) -> SystemSettings:
        """Get system settings (lazy loaded)."""
        if self._system is None:
            self._system = SystemSettings()
        return self._system
    
    def get_masked_env_vars(self) -> Dict[str, str]:
        """Get environment variables with secrets masked for logging."""
        masked_vars = {}
        for key, value in os.environ.items():
            if any(secret_key in key.upper() for secret_key in ['KEY', 'PASSWORD', 'TOKEN', 'SECRET']):
                if value:
                    masked_vars[key] = '*' * 8  # Mask the value
                else:
                    masked_vars[key] = ''
            else:
                masked_vars[key] = value
        return masked_vars
    
    def _check_virtual_environment(self) -> bool:
        """Check if running in a virtual environment."""
        return (
            hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        )
    
    def validate_environment(self) -> Dict[str, Any]:
        """Validate environment and return status."""
        status = {
            'virtual_env': self._check_virtual_environment(),
            'missing_required': [],
            'warnings': [],
            'config_valid': True
        }
        
        # Check for virtual environment
        if not status['virtual_env']:
            status['warnings'].append("Not running in virtual environment")
        
        return status


# ============================================================================
# LEGACY COMPATIBILITY INSTANCES
# ============================================================================

# Create global instance for backward compatibility
config_manager = ConfigManager()

# Default instances for easy import (legacy compatibility)
DEFAULT_CRAWLER_CONFIG = config_manager.crawler
DEFAULT_RAG_CONFIG = config_manager.rag
DEFAULT_OUTPUT_CONFIG = config_manager.output

# Remote API usage mode (legacy compatibility)
REMOTE_MODE = config_manager.rag.remote_mode

# Export as 'config' for new modules
config = config_manager

# ============================================================================
# VALIDATION AND UTILITY FUNCTIONS
# ============================================================================

def validate_environment():
    """Validate the current environment configuration."""
    return config_manager.validate_environment()


def get_config() -> ConfigManager:
    """Get the global configuration manager instance."""
    return config_manager