#!/usr/bin/env python3
"""
Secure Configuration Management System for MAMcrawler
====================================================

This module provides centralized, secure configuration management
with proper environment variable handling and validation.
"""

import os
import warnings
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv


class ConfigManager:
    """Simple configuration manager with security validation."""
    
    def __init__(self):
        self.validation_errors = []
        self._check_virtual_environment()
        self._validate_security_settings()
    
    def _check_virtual_environment(self) -> bool:
        """Check if running in a virtual environment."""
        in_venv = (
            hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
            os.environ.get('VIRTUAL_ENV') is not None
        )
        
        if not in_venv:
            warnings.warn(
                "NOT running in a virtual environment! "
                "This is a critical security requirement. "
                "Please create and activate a virtual environment.",
                UserWarning
            )
            return False
        
        return True
    
    def _validate_security_settings(self):
        """Validate critical security settings."""
        # Check for required API keys
        if not os.getenv('ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_API_KEY') == 'your_anthropic_api_key_here':
            self.validation_errors.append("ANTHROPIC_API_KEY is required but not set")
        
        if not os.getenv('GOOGLE_BOOKS_API_KEY') or os.getenv('GOOGLE_BOOKS_API_KEY') == 'your_google_books_api_key_here':
            self.validation_errors.append("GOOGLE_BOOKS_API_KEY is required but not set")
        
        # Check for required credentials
        if not os.getenv('ABS_TOKEN') or os.getenv('ABS_TOKEN') == 'your_abs_token_here':
            self.validation_errors.append("ABS_TOKEN is required for Audiobookshelf integration")
        
        if not os.getenv('MAM_USERNAME') or os.getenv('MAM_USERNAME') == 'your_mam_username':
            self.validation_errors.append("MAM_USERNAME is required for MAM crawler")
        
        if not os.getenv('MAM_PASSWORD') or os.getenv('MAM_PASSWORD') == 'your_mam_password':
            self.validation_errors.append("MAM_PASSWORD is required for MAM crawler")
    
    def get_masked_env_vars(self) -> Dict[str, str]:
        """Get environment variables with sensitive values masked."""
        masked_vars = {}
        
        # Security settings
        sensitive_vars = [
            'ANTHROPIC_API_KEY', 'GOOGLE_BOOKS_API_KEY', 'POSTGRES_PASSWORD',
            'ABS_TOKEN', 'MAM_PASSWORD', 'QB_PASSWORD'
        ]
        
        for var in sensitive_vars:
            value = os.getenv(var)
            if value:
                masked_vars[var] = self._mask_secret(value)
            else:
                masked_vars[var] = "NOT_SET"
        
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
    
    def validate_all(self) -> List[str]:
        """Validate all configuration settings."""
        self._validate_security_settings()
        return self.validation_errors
    
    def check_environment(self) -> Dict[str, Any]:
        """Check current environment setup status."""
        validation_errors = self.validate_all()
        
        return {
            "virtual_environment": self._check_virtual_environment(),
            "validation_errors": validation_errors,
            "configuration_complete": len(validation_errors) == 0,
            "masked_env_vars": self.get_masked_env_vars()
        }
    
    # Configuration properties
    @property
    def abs_url(self) -> str:
        """Get Audiobookshelf URL."""
        return os.getenv('ABS_URL', 'http://localhost:13378')
    
    @property
    def abs_token(self) -> str:
        """Get Audiobookshelf token."""
        return os.getenv('ABS_TOKEN', '')
    
    @property
    def mam_username(self) -> str:
        """Get MyAnonamouse username."""
        return os.getenv('MAM_USERNAME', '')
    
    @property
    def mam_password(self) -> str:
        """Get MyAnonamouse password."""
        return os.getenv('MAM_PASSWORD', '')
    
    @property
    def qb_host(self) -> str:
        """Get qBittorrent host."""
        return os.getenv('QB_HOST', 'localhost')
    
    @property
    def qb_port(self) -> int:
        """Get qBittorrent port."""
        return int(os.getenv('QB_PORT', '8080'))
    
    @property
    def qb_username(self) -> str:
        """Get qBittorrent username."""
        return os.getenv('QB_USERNAME', 'admin')
    
    @property
    def qb_password(self) -> str:
        """Get qBittorrent password."""
        return os.getenv('QB_PASSWORD', '')
    
    @property
    def log_level(self) -> str:
        """Get logging level."""
        return os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def debug_mode(self) -> bool:
        """Get debug mode setting."""
        return os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    
    @property
    def browser_headless(self) -> bool:
        """Get browser headless setting."""
        return os.getenv('BROWSER_HEADLESS', 'true').lower() == 'true'
    
    @property
    def request_delay_min(self) -> float:
        """Get minimum request delay."""
        return float(os.getenv('REQUEST_DELAY_MIN', '1.0'))
    
    @property
    def request_delay_max(self) -> float:
        """Get maximum request delay."""
        return float(os.getenv('REQUEST_DELAY_MAX', '3.0'))
    
    @property
    def output_dir(self) -> str:
        """Get output directory."""
        output_dir = os.getenv('OUTPUT_DIR', 'output')
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return output_dir
    
    @property
    def temp_dir(self) -> str:
        """Get temp directory."""
        temp_dir = os.getenv('TEMP_DIR', 'temp')
        Path(temp_dir).mkdir(parents=True, exist_ok=True)
        return temp_dir
    
    @property
    def log_file_path(self) -> str:
        """Get log file path."""
        log_path = os.getenv('LOG_FILE_PATH', 'logs/mamcrawler.log')
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        return log_path


def validate_environment() -> bool:
    """Validate the complete environment setup."""
    config = ConfigManager()
    config_status = config.check_environment()
    
    if not config_status["virtual_environment"]:
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