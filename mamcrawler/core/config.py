"""
Unified Configuration System for MAMcrawler

This module provides a centralized configuration management system for all crawler components,
ensuring consistency and eliminating hardcoded values.

Author: Audiobook Automation System
Version: 1.0.0
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import timedelta

from .utils import ConfigManager


@dataclass
class CrawlerConfig:
    """Configuration for crawler behavior."""
    
    # Rate limiting
    min_delay: float = 3.0
    max_delay: float = 10.0
    rate_limit_enabled: bool = True
    
    # Session management
    session_timeout: int = 7200  # 2 hours
    retry_attempts: int = 3
    retry_backoff_base: float = 2.0  # Exponential backoff base
    
    # Authentication
    auto_reauth: bool = True
    reauth_threshold: float = 0.9  # Reauth when 90% of session expired
    
    # User agent rotation
    rotate_user_agents: bool = True
    user_agents_file: Optional[str] = None
    
    # Browser settings
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    disable_images: bool = True
    disable_css: bool = False
    disable_javascript: bool = False
    
    # Stealth behavior
    simulate_human: bool = True
    scroll_pause_range: tuple = (1.0, 3.0)
    mouse_movement_count: int = 3
    
    # Timeout settings
    page_load_timeout: int = 30000  # 30 seconds
    element_wait_timeout: int = 10000  # 10 seconds
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.min_delay < 0:
            raise ValueError("min_delay must be non-negative")
        if self.max_delay < self.min_delay:
            raise ValueError("max_delay must be greater than or equal to min_delay")


@dataclass
class DatabaseConfig:
    """Configuration for database operations."""
    
    # Connection settings
    connection_string: Optional[str] = None
    max_connections: int = 10
    connection_timeout: int = 30
    
    # Retry settings
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Performance settings
    query_timeout: int = 30
    batch_size: int = 100
    
    # Connection pooling
    pool_pre_ping: bool = True
    pool_recycle: int = 3600  # 1 hour
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.max_connections <= 0:
            raise ValueError("max_connections must be positive")
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    
    # Log levels
    level: str = "INFO"
    console_level: Optional[str] = None
    file_level: Optional[str] = None
    
    # File settings
    log_to_file: bool = True
    log_directory: str = "logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    
    # Format settings
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Performance settings
    buffer_size: int = 1024
    flush_interval: float = 1.0  # seconds
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {self.level}")
        if self.console_level and self.console_level.upper() not in valid_levels:
            raise ValueError(f"Invalid console log level: {self.console_level}")
        if self.file_level and self.file_level.upper() not in valid_levels:
            raise ValueError(f"Invalid file log level: {self.file_level}")


@dataclass
class ProxyConfig:
    """Configuration for proxy usage."""
    
    # Proxy settings
    enabled: bool = False
    proxies: List[str] = field(default_factory=list)
    rotation_enabled: bool = True
    rotation_interval: int = 30  # minutes
    
    # Authentication
    proxy_auth: Optional[Dict[str, str]] = None
    
    # Health checks
    health_check_url: str = "https://httpbin.org/ip"
    health_check_interval: int = 300  # 5 minutes
    max_failures: int = 3
    
    # Performance
    timeout: int = 10
    connection_timeout: int = 5


@dataclass
class SecurityConfig:
    """Configuration for security settings."""
    
    # SSL/TLS
    verify_ssl: bool = True
    ssl_ca_bundle: Optional[str] = None
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    
    # Headers
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Content validation
    max_content_length: int = 50 * 1024 * 1024  # 50MB
    allowed_content_types: List[str] = field(default_factory=lambda: ["text/html", "text/plain", "application/json"])
    
    # Rate limiting per domain
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    
    # Request validation
    max_url_length: int = 2048
    blocked_domains: List[str] = field(default_factory=list)


@dataclass
class MAMConfig:
    """Configuration specific to MyAnonamouse."""
    
    # Site settings
    base_url: str = "https://www.myanonamouse.net"
    login_url: str = "https://www.myanonamouse.net/login.php"
    browse_url: str = "https://www.myanonamouse.net/tor/browse.php"
    guides_url: str = "https://www.myanonamouse.net/guides/"
    
    # Allowed paths
    allowed_paths: List[str] = field(default_factory=lambda: [
        "/", "/t/", "/tor/browse.php", "/tor/search.php", 
        "/guides/", "/f/", "/u/"
    ])
    
    # Authentication
    username_field: str = "username"
    password_field: str = "password"
    submit_button_selector: str = "input[type=submit]"
    
    # Selectors
    login_form_selector: str = "form[name=loginform]"
    logout_link_selector: str = "a[href*='logout']"
    profile_link_selector: str = "a[href*='profile']"
    
    # Forum settings
    forum_base_url: str = "https://www.myanonamouse.net/f/"
    forum_post_selector: str = ".post"
    forum_title_selector: str = ".post-title"
    forum_content_selector: str = ".post-content"
    
    # Guide settings
    guides_list_selector: str = ".guide-item"
    guide_title_selector: str = ".guide-title"
    guide_content_selector: str = ".guide-content"
    
    # Search settings
    search_selector: str = "input[name=search]"
    search_button_selector: str = "input[type=submit]"
    results_selector: str = ".search-result"
    
    # Pagination
    next_page_selector: str = ".pagination a[title='Next']"
    page_number_selector: str = ".pagination a"


@dataclass
class OutputConfig:
    """Configuration for output handling."""
    
    # Output directory
    output_dir: str = "output"
    create_subdirs: bool = True
    
    # File naming
    filename_template: str = "{title}_{timestamp}.{ext}"
    max_filename_length: int = 100
    sanitize_filenames: bool = True
    
    # File formats
    preferred_format: str = "json"
    formats: List[str] = field(default_factory=lambda: ["json", "csv", "md"])
    
    # Compression
    compress_output: bool = False
    compression_format: str = "gzip"
    
    # Backup settings
    backup_enabled: bool = True
    max_backups: int = 5
    
    # Metadata handling
    save_metadata: bool = True
    metadata_fields: List[str] = field(default_factory=lambda: [
        "title", "url", "timestamp", "category", "tags"
    ])


@dataclass
class MonitoringConfig:
    """Configuration for monitoring and metrics."""
    
    # Health checks
    health_check_enabled: bool = True
    health_check_interval: int = 60  # seconds
    
    # Performance metrics
    metrics_enabled: bool = True
    metrics_endpoint: Optional[str] = None
    
    # Alerts
    alerts_enabled: bool = True
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "error_rate": 0.05,  # 5%
        "response_time": 10.0,  # 10 seconds
        "memory_usage": 0.8,  # 80%
        "cpu_usage": 0.8  # 80%
    })
    
    # Reporting
    report_enabled: bool = True
    report_interval: int = 3600  # 1 hour
    report_formats: List[str] = field(default_factory=lambda: ["json", "html"])


class ConfigRegistry:
    """
    Central registry for all configuration objects.
    """
    
    def __init__(self):
        """Initialize the configuration registry."""
        self._config: Dict[str, Any] = {}
        self._config_managers: Dict[str, ConfigManager] = {}
        
    def register_config(self, name: str, config_obj: Any, config_path: Optional[str] = None):
        """
        Register a configuration object.
        
        Args:
            name: Name of the configuration
            config_obj: Configuration object instance
            config_path: Optional path to config file
        """
        self._config[name] = config_obj
        
        if config_path:
            self._config_managers[name] = ConfigManager()
    
    def get_config(self, name: str) -> Optional[Any]:
        """
        Get a registered configuration.
        
        Args:
            name: Name of the configuration
            
        Returns:
            Configuration object or None
        """
        return self._config.get(name)
    
    def update_config(self, name: str, config_data: Dict[str, Any]):
        """
        Update a configuration with new data.
        
        Args:
            name: Name of the configuration
            config_data: New configuration data
        """
        if name in self._config:
            config_obj = self._config[name]
            for key, value in config_data.items():
                if hasattr(config_obj, key):
                    setattr(config_obj, key, value)
    
    def save_all_configs(self, base_path: str = "config"):
        """
        Save all configurations to files.
        
        Args:
            base_path: Base directory for config files
        """
        base_path = Path(base_path)
        base_path.mkdir(exist_ok=True)
        
        for name, config_obj in self._config.items():
            config_file = base_path / f"{name}.json"
            try:
                config_dict = {
                    k: v for k, v in config_obj.__dict__.items() 
                    if not k.startswith('_')
                }
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, indent=2, default=str)
            except Exception as e:
                logging.error(f"Failed to save config {name}: {e}")
    
    def load_all_configs(self, base_path: str = "config"):
        """
        Load all configurations from files.
        
        Args:
            base_path: Base directory for config files
        """
        base_path = Path(base_path)
        if not base_path.exists():
            return
        
        for config_file in base_path.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                name = config_file.stem
                if name in self._config:
                    self.update_config(name, config_data)
            except Exception as e:
                logging.error(f"Failed to load config {name}: {e}")


class GlobalConfig:
    """
    Global configuration manager for the entire application.
    """
    
    _instance = None
    
    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize global configuration."""
        if self._initialized:
            return
            
        self._initialized = True
        
        # Initialize configuration registry
        self.registry = ConfigRegistry()
        
        # Register default configurations
        self._register_default_configs()
        
        # Load from environment
        self._load_from_environment()
        
        # Load from config files
        self.config_path = os.getenv('MAMCRAWLER_CONFIG_PATH', 'config')
        self.registry.load_all_configs(self.config_path)
    
    def _register_default_configs(self):
        """Register default configurations."""
        # Register all default configurations
        self.registry.register_config("crawler", CrawlerConfig())
        self.registry.register_config("database", DatabaseConfig())
        self.registry.register_config("logging", LoggingConfig())
        self.registry.register_config("proxy", ProxyConfig())
        self.registry.register_config("security", SecurityConfig())
        self.registry.register_config("mam", MAMConfig())
        self.registry.register_config("output", OutputConfig())
        self.registry.register_config("monitoring", MonitoringConfig())
    
    def _load_from_environment(self):
        """Load configuration values from environment variables."""
        # Load from environment variables with MAMCRAWLER_ prefix
        
        # Crawler config
        crawler_config = self.get_config("crawler")
        if crawler_config:
            if os.getenv('MAMCRAWLER_MIN_DELAY'):
                crawler_config.min_delay = float(os.getenv('MAMCRAWLER_MIN_DELAY'))
            if os.getenv('MAMCRAWLER_MAX_DELAY'):
                crawler_config.max_delay = float(os.getenv('MAMCRAWLER_MAX_DELAY'))
            if os.getenv('MAMCRAWLER_HEADLESS'):
                crawler_config.headless = os.getenv('MAMCRAWLER_HEADLESS').lower() == 'true'
        
        # Database config
        db_config = self.get_config("database")
        if db_config:
            if os.getenv('DATABASE_URL'):
                db_config.connection_string = os.getenv('DATABASE_URL')
        
        # MAM config
        mam_config = self.get_config("mam")
        if mam_config:
            if os.getenv('MAM_USERNAME'):
                # This would be loaded by individual crawlers
                pass
        
        # Proxy config
        proxy_config = self.get_config("proxy")
        if proxy_config:
            if os.getenv('MAMCRAWLER_PROXY_ENABLED'):
                proxy_config.enabled = os.getenv('MAMCRAWLER_PROXY_ENABLED').lower() == 'true'
            if os.getenv('MAMCRAWLER_PROXIES'):
                proxy_config.proxies = [
                    proxy.strip() for proxy in os.getenv('MAMCRAWLER_PROXIES').split(',')
                ]
        
        # Logging config
        logging_config = self.get_config("logging")
        if logging_config:
            if os.getenv('MAMCRAWLER_LOG_LEVEL'):
                logging_config.level = os.getenv('MAMCRAWLER_LOG_LEVEL').upper()
            if os.getenv('MAMCRAWLER_LOG_DIR'):
                logging_config.log_directory = os.getenv('MAMCRAWLER_LOG_DIR')
    
    def get_config(self, name: str) -> Optional[Any]:
        """
        Get a configuration object.
        
        Args:
            name: Name of the configuration
            
        Returns:
            Configuration object
        """
        return self.registry.get_config(name)
    
    def update_config(self, name: str, **kwargs):
        """
        Update a configuration with keyword arguments.
        
        Args:
            name: Name of the configuration
            **kwargs: Configuration values to update
        """
        self.registry.update_config(name, kwargs)
    
    def save_configs(self):
        """Save all configurations to files."""
        self.registry.save_all_configs(self.config_path)
    
    def get_crawler_config(self) -> CrawlerConfig:
        """Get crawler configuration."""
        return self.get_config("crawler")
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self.get_config("database")
    
    def get_mam_config(self) -> MAMConfig:
        """Get MAM configuration."""
        return self.get_config("mam")
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self.get_config("logging")
    
    def get_proxy_config(self) -> ProxyConfig:
        """Get proxy configuration."""
        return self.get_config("proxy")
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return self.get_config("security")
    
    def get_output_config(self) -> OutputConfig:
        """Get output configuration."""
        return self.get_config("output")
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration."""
        return self.get_config("monitoring")


# Global configuration instance
global_config = GlobalConfig()


# Convenience functions for accessing configuration
def get_global_config() -> GlobalConfig:
    """Get the global configuration instance."""
    return global_config


def get_crawler_config() -> CrawlerConfig:
    """Get crawler configuration."""
    return global_config.get_crawler_config()


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return global_config.get_database_config()


def get_mam_config() -> MAMConfig:
    """Get MAM configuration."""
    return global_config.get_mam_config()


def get_logging_config() -> LoggingConfig:
    """Get logging configuration."""
    return global_config.get_logging_config()


def get_proxy_config() -> ProxyConfig:
    """Get proxy configuration."""
    return global_config.get_proxy_config()


def get_security_config() -> SecurityConfig:
    """Get security configuration."""
    return global_config.get_security_config()


def get_output_config() -> OutputConfig:
    """Get output configuration."""
    return global_config.get_output_config()


def get_monitoring_config() -> MonitoringConfig:
    """Get monitoring configuration."""
    return global_config.get_monitoring_config()


# Export main classes and functions
__all__ = [
    'CrawlerConfig',
    'DatabaseConfig', 
    'LoggingConfig',
    'ProxyConfig',
    'SecurityConfig',
    'MAMConfig',
    'OutputConfig',
    'MonitoringConfig',
    'ConfigRegistry',
    'GlobalConfig',
    'get_global_config',
    'get_crawler_config',
    'get_database_config',
    'get_mam_config',
    'get_logging_config',
    'get_proxy_config',
    'get_security_config',
    'get_output_config',
    'get_monitoring_config'
]