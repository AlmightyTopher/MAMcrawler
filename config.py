#!/usr/bin/env python3
"""
Unified Configuration System - Backward Compatibility Layer

This module provides backward compatibility with the old config.py interface
while using the new unified configuration system.
"""

import warnings
from typing import Optional, Dict, Any, List
from pydantic import SecretStr

# Import from the new unified configuration system
from config_system import ConfigSystem

# Initialize the unified configuration system
_config_system = ConfigSystem()


class SecuritySettings:
    """Security and API key management settings - backward compatibility."""

    def __init__(self):
        self._config = _config_system

    @property
    def anthropic_api_key(self) -> Optional[SecretStr]:
        """Get Anthropic API key."""
        value = self._config.get_secret('anthropic_api_key')
        return SecretStr(value) if value else None

    @property
    def google_books_api_key(self) -> Optional[SecretStr]:
        """Get Google Books API key."""
        value = self._config.get_secret('google_books_api_key')
        return SecretStr(value) if value else None

    @property
    def postgres_host(self) -> str:
        """Get PostgreSQL host."""
        return self._config.get('database.postgresql.host', 'localhost')

    @property
    def postgres_port(self) -> int:
        """Get PostgreSQL port."""
        return self._config.get('database.postgresql.port', 5432)

    @property
    def postgres_db(self) -> str:
        """Get PostgreSQL database name."""
        return self._config.get('database.postgresql.database', 'audiobooks')

    @property
    def postgres_user(self) -> str:
        """Get PostgreSQL username."""
        return self._config.get('database.postgresql.user', 'postgres')

    @property
    def postgres_password(self) -> Optional[SecretStr]:
        """Get PostgreSQL password."""
        value = self._config.get_secret('postgres_password')
        return SecretStr(value) if value else None


class APIEndpoints:
    """API endpoint configurations - backward compatibility."""

    def __init__(self):
        self._config = _config_system

    @property
    def abs_url(self) -> str:
        """Get Audiobookshelf URL."""
        return self._config.get('api_endpoints.audiobookshelf.url', 'http://localhost:13378')

    @property
    def abs_token(self) -> Optional[SecretStr]:
        """Get Audiobookshelf token."""
        value = self._config.get_secret('abs_token')
        return SecretStr(value) if value else None

    @property
    def mam_username(self) -> Optional[str]:
        """Get MyAnonamouse username."""
        return self._config.get_secret('mam_username')

    @property
    def mam_password(self) -> Optional[SecretStr]:
        """Get MyAnonamouse password."""
        value = self._config.get_secret('mam_password')
        return SecretStr(value) if value else None

    @property
    def qb_host(self) -> str:
        """Get qBittorrent host."""
        return self._config.get('api_endpoints.qbittorrent.host', 'localhost')

    @property
    def qb_port(self) -> int:
        """Get qBittorrent port."""
        return self._config.get('api_endpoints.qbittorrent.port', 8080)

    @property
    def qb_username(self) -> str:
        """Get qBittorrent username."""
        return self._config.get('api_endpoints.qbittorrent.username', 'admin')

    @property
    def qb_password(self) -> Optional[SecretStr]:
        """Get qBittorrent password."""
        value = self._config.get_secret('qbittorrent_password')
        return SecretStr(value) if value else None


class CrawlerSettings:
    """Crawler and stealth operation settings - backward compatibility."""

    def __init__(self):
        self._config = _config_system

    @property
    def browser_headless(self) -> bool:
        """Get browser headless mode."""
        return self._config.get('crawler.browser.headless', True)

    @property
    def browser_user_agent(self) -> str:
        """Get browser user agent."""
        return self._config.get('crawler.browser.user_agent',
                               'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    @property
    def request_delay_min(self) -> float:
        """Get minimum request delay."""
        return self._config.get('crawler.rate_limiting.min_delay', 1.0)

    @property
    def request_delay_max(self) -> float:
        """Get maximum request delay."""
        return self._config.get('crawler.rate_limiting.max_delay', 3.0)

    @property
    def http_proxy(self) -> Optional[str]:
        """Get HTTP proxy."""
        return self._config.get('crawler.proxy.http_proxy')

    @property
    def https_proxy(self) -> Optional[str]:
        """Get HTTPS proxy."""
        return self._config.get('crawler.proxy.https_proxy')

    @property
    def wireguard_config(self) -> Optional[str]:
        """Get WireGuard config path."""
        return self._config.get('crawler.vpn.wireguard_config')


class DatabaseSettings:
    """Database connection and performance settings - backward compatibility."""

    def __init__(self):
        self._config = _config_system

    @property
    def db_pool_size(self) -> int:
        """Get database pool size."""
        return self._config.get('database.pool.min_connections', 1)

    @property
    def db_max_overflow(self) -> int:
        """Get database max overflow."""
        return self._config.get('database.pool.max_connections', 20)

    @property
    def db_pool_timeout(self) -> int:
        """Get database pool timeout."""
        return self._config.get('database.pool.max_idle_time', 300)

    @property
    def rag_db_path(self) -> str:
        """Get RAG database path."""
        return self._config.get('database.sqlite.path', 'data/mamcrawler.db')

    @property
    def enable_query_logging(self) -> bool:
        """Get query logging enabled flag."""
        return self._config.get('database.monitoring.enable_query_logging', False)


class LoggingSettings:
    """Logging configuration settings - backward compatibility."""

    def __init__(self):
        self._config = _config_system

    @property
    def log_level(self) -> str:
        """Get log level."""
        return self._config.get('logging.console.level', 'INFO')

    @property
    def log_format(self) -> str:
        """Get log format."""
        return self._config.get('logging.console.format',
                               '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    @property
    def log_file_path(self) -> str:
        """Get log file path."""
        return self._config.get('logging.file.path', 'logs/mamcrawler.log')

    @property
    def max_log_size_mb(self) -> int:
        """Get max log size in MB."""
        return self._config.get('logging.file.max_size_mb', 100)

    @property
    def backup_count(self) -> int:
        """Get backup count."""
        return self._config.get('logging.file.backup_count', 5)


class SystemSettings:
    """System-wide operational settings - backward compatibility."""

    def __init__(self):
        self._config = _config_system

    @property
    def app_name(self) -> str:
        """Get application name."""
        return self._config.get('app.name', 'MAMcrawler')

    @property
    def app_version(self) -> str:
        """Get application version."""
        return self._config.get('app.version', '2.0.0')

    @property
    def debug_mode(self) -> bool:
        """Get debug mode flag."""
        return self._config.get('app.debug', False)

    @property
    def output_dir(self) -> str:
        """Get output directory."""
        return self._config.get('paths.output_dir', 'output')

    @property
    def temp_dir(self) -> str:
        """Get temp directory."""
        return self._config.get('paths.temp_dir', 'temp')

    @property
    def max_concurrent_requests(self) -> int:
        """Get max concurrent requests."""
        return self._config.get('performance.max_concurrent_requests', 10)

    @property
    def request_timeout(self) -> int:
        """Get request timeout."""
        return self._config.get('performance.request_timeout', 30)


class ConfigManager:
    """Centralized configuration manager with validation and security checks - backward compatibility."""

    def __init__(self):
        self._config_system = _config_system
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
        return self._logging

    @property
    def system(self) -> SystemSettings:
        """Get system settings with validation."""
        if self._system is None:
            self._system = SystemSettings()
        return self._system

    def _validate_security_settings(self):
        """Validate critical security settings."""
        if not self._security.anthropic_api_key or not self._security.anthropic_api_key.get_secret_value():
            self._validation_errors.append("ANTHROPIC_API_KEY is required but not set")

        if not self._security.google_books_api_key or not self._security.google_books_api_key.get_secret_value():
            self._validation_errors.append("GOOGLE_BOOKS_API_KEY is required but not set")

        if not self._security.postgres_password or not self._security.postgres_password.get_secret_value():
            self._validation_errors.append("POSTGRES_PASSWORD is required but not set")

    def _validate_api_endpoints(self):
        """Validate API endpoint configurations."""
        if not self._api_endpoints.abs_token or not self._api_endpoints.abs_token.get_secret_value():
            self._validation_errors.append("ABS_TOKEN is required for Audiobookshelf integration")

        if not self._api_endpoints.mam_username:
            self._validation_errors.append("MAM_USERNAME is required for MAM crawler")

        if not self._api_endpoints.mam_password or not self._api_endpoints.mam_password.get_secret_value():
            self._validation_errors.append("MAM_PASSWORD is required for MAM crawler")

    def validate_all(self) -> List[str]:
        """Validate all configuration settings."""
        # Reset validation errors
        self._validation_errors = []

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
        # Use the new config system's masking functionality
        return self._config_system.get_masked_env_vars()

    def _mask_secret(self, secret: str) -> str:
        """Mask secret string for safe display."""
        if len(secret) <= 8:
            return "*" * len(secret)
        return secret[:4] + "*" * (len(secret) - 8) + secret[-4:]

    def check_environment(self) -> Dict[str, Any]:
        """Check current environment setup status."""
        validation_errors = self.validate_all()

        return {
            "virtual_environment": self._config_system.check_virtual_environment(),
            "validation_errors": validation_errors,
            "configuration_complete": len(validation_errors) == 0,
            "masked_env_vars": self.get_masked_env_vars()
        }


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