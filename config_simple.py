#!/usr/bin/env python3
"""
Simple Configuration Manager - Redirect to Unified System

This module now redirects to the unified configuration system
for backward compatibility.
"""

import warnings

# Import from the unified configuration system
from config_system import ConfigSystem

# Initialize the unified configuration system
_config_system = ConfigSystem()


class ConfigManager:
    """Simple configuration manager - now uses unified system."""

    def __init__(self):
        self._config_system = _config_system
        self.validation_errors = []

    def _check_virtual_environment(self) -> bool:
        """Check if running in a virtual environment."""
        return self._config_system.check_virtual_environment()

    def _validate_security_settings(self):
        """Validate critical security settings."""
        # Use the unified system's validation
        validation_result = self._config_system.validate_configuration()
        if not validation_result['valid']:
            self.validation_errors.extend(validation_result['errors'])

    def get_masked_env_vars(self) -> dict:
        """Get environment variables with sensitive values masked."""
        return self._config_system.get_masked_env_vars()

    def _mask_secret(self, secret: str) -> str:
        """Mask secret string for safe display."""
        if len(secret) <= 8:
            return "*" * len(secret)
        return secret[:4] + "*" * (len(secret) - 8) + secret[-4:]

    def validate_all(self) -> list:
        """Validate all configuration settings."""
        self.validation_errors = []
        self._validate_security_settings()
        return self.validation_errors

    def check_environment(self) -> dict:
        """Check current environment setup status."""
        validation_errors = self.validate_all()

        return {
            "virtual_environment": self._check_virtual_environment(),
            "validation_errors": validation_errors,
            "configuration_complete": len(validation_errors) == 0,
            "masked_env_vars": self.get_masked_env_vars()
        }

    # Configuration properties - redirect to unified system
    @property
    def abs_url(self) -> str:
        """Get Audiobookshelf URL."""
        return self._config_system.get('api_endpoints.audiobookshelf.url', 'http://localhost:13378')

    @property
    def abs_token(self) -> str:
        """Get Audiobookshelf token."""
        return self._config_system.get_secret('abs_token') or ''

    @property
    def mam_username(self) -> str:
        """Get MyAnonamouse username."""
        return self._config_system.get_secret('mam_username') or ''

    @property
    def mam_password(self) -> str:
        """Get MyAnonamouse password."""
        return self._config_system.get_secret('mam_password') or ''

    @property
    def qb_host(self) -> str:
        """Get qBittorrent host."""
        return self._config_system.get('api_endpoints.qbittorrent.host', 'localhost')

    @property
    def qb_port(self) -> int:
        """Get qBittorrent port."""
        return self._config_system.get('api_endpoints.qbittorrent.port', 8080)

    @property
    def qb_username(self) -> str:
        """Get qBittorrent username."""
        return self._config_system.get('api_endpoints.qbittorrent.username', 'admin')

    @property
    def qb_password(self) -> str:
        """Get qBittorrent password."""
        return self._config_system.get_secret('qbittorrent_password') or ''

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self._config_system.get('logging.console.level', 'INFO')

    @property
    def debug_mode(self) -> bool:
        """Get debug mode setting."""
        return self._config_system.get('app.debug', False)

    @property
    def browser_headless(self) -> bool:
        """Get browser headless setting."""
        return self._config_system.get('crawler.browser.headless', True)

    @property
    def request_delay_min(self) -> float:
        """Get minimum request delay."""
        return self._config_system.get('crawler.rate_limiting.min_delay', 1.0)

    @property
    def request_delay_max(self) -> float:
        """Get maximum request delay."""
        return self._config_system.get('crawler.rate_limiting.max_delay', 3.0)

    @property
    def output_dir(self) -> str:
        """Get output directory."""
        return self._config_system.get('paths.output_dir', 'output')

    @property
    def temp_dir(self) -> str:
        """Get temp directory."""
        return self._config_system.get('paths.temp_dir', 'temp')

    @property
    def log_file_path(self) -> str:
        """Get log file path."""
        return self._config_system.get('logging.file.path', 'logs/mamcrawler.log')


def validate_environment() -> bool:
    """Validate the complete environment setup."""
    config = ConfigManager()
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


# Global configuration manager instance
config = ConfigManager()


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