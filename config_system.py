#!/usr/bin/env python3
"""
Unified Configuration Management System for MAMcrawler
======================================================

This module provides a comprehensive, secure, and type-safe configuration system
that consolidates all configuration approaches into a single, unified framework.

Features:
- Hierarchical configuration with environment overrides
- Type-safe configuration with Pydantic validation
- Secure secret handling with encryption
- Configuration hot-reloading
- Multi-environment support (dev, staging, prod)
- Runtime configuration updates
- Comprehensive error handling and validation

Author: Agent 8 - Configuration Consolidation Specialist
"""

import os
import json
import yaml
import logging
import asyncio
import hashlib
import secrets
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Type, TypeVar, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

import aiofiles
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from pydantic import BaseModel, ValidationError, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Type variables
T = TypeVar('T', bound=BaseModel)

class ConfigError(Exception):
    """Base exception for configuration errors."""
    pass

class ValidationError(ConfigError):
    """Configuration validation error."""
    pass

class SecurityError(ConfigError):
    """Configuration security error."""
    pass

class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""
    pass

@dataclass
class ConfigMetadata:
    """Metadata for configuration files."""
    path: Path
    last_modified: datetime
    checksum: str
    environment: str
    version: str = "1.0"

@dataclass
class ConfigEnvironment:
    """Configuration environment information."""
    name: str
    is_production: bool = False
    is_development: bool = False
    is_staging: bool = False
    config_paths: List[Path] = field(default_factory=list)

class SecretManager:
    """Secure secret management with encryption."""

    def __init__(self, secrets_dir: Path, master_key: Optional[str] = None):
        self.secrets_dir = secrets_dir
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        self.master_key = master_key or self._load_or_generate_master_key()
        self.fernet = Fernet(self.master_key)

    def _load_or_generate_master_key(self) -> bytes:
        """Load existing master key or generate a new one."""
        key_file = self.secrets_dir / ".master.key"

        if key_file.exists():
            return key_file.read_bytes()
        else:
            # Generate a new master key
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            # Set restrictive permissions
            try:
                os.chmod(key_file, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod
            return key

    def encrypt_secret(self, secret: str) -> str:
        """Encrypt a secret value."""
        if not secret:
            return ""
        encrypted = self.fernet.encrypt(secret.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a secret value."""
        if not encrypted_secret:
            return ""
        try:
            encrypted = base64.b64decode(encrypted_secret)
            decrypted = self.fernet.decrypt(encrypted)
            return decrypted.decode()
        except (InvalidToken, ValueError) as e:
            raise SecurityError(f"Failed to decrypt secret: {e}")

    def store_secret(self, key: str, value: str, namespace: str = "default"):
        """Store an encrypted secret."""
        namespace_dir = self.secrets_dir / namespace
        namespace_dir.mkdir(exist_ok=True)

        encrypted_value = self.encrypt_secret(value)
        secret_file = namespace_dir / f"{key}.enc"

        secret_data = {
            "key": key,
            "encrypted_value": encrypted_value,
            "created_at": datetime.now().isoformat(),
            "namespace": namespace
        }

        with open(secret_file, 'w') as f:
            json.dump(secret_data, f, indent=2)

    def load_secret(self, key: str, namespace: str = "default") -> str:
        """Load and decrypt a secret."""
        secret_file = self.secrets_dir / namespace / f"{key}.enc"

        if not secret_file.exists():
            raise ConfigNotFoundError(f"Secret '{key}' not found in namespace '{namespace}'")

        with open(secret_file, 'r') as f:
            secret_data = json.load(f)

        return self.decrypt_secret(secret_data["encrypted_value"])

class ConfigValidator:
    """Configuration validation with Pydantic schemas."""

    def __init__(self, schemas_dir: Path):
        self.schemas_dir = schemas_dir
        self.schemas_dir.mkdir(parents=True, exist_ok=True)
        self._schema_cache: Dict[str, Type[BaseModel]] = {}

    def validate_config(self, config_data: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        """Validate configuration data against a schema."""
        schema_class = self._load_schema(schema_name)
        try:
            validated_config = schema_class(**config_data)
            return validated_config.model_dump()
        except ValidationError as e:
            raise ValidationError(f"Configuration validation failed for '{schema_name}': {e}")

    def _load_schema(self, schema_name: str) -> Type[BaseModel]:
        """Load a Pydantic schema class."""
        if schema_name in self._schema_cache:
            return self._schema_cache[schema_name]

        schema_file = self.schemas_dir / f"{schema_name}.py"

        if not schema_file.exists():
            raise ConfigNotFoundError(f"Schema '{schema_name}' not found")

        # Import the schema module
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"config_schemas.{schema_name}", schema_file)
        if spec is None or spec.loader is None:
            raise ConfigError(f"Failed to load schema '{schema_name}'")

        schema_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(schema_module)

        # Find the main schema class (usually named after the schema)
        schema_class_name = schema_name.replace('_', ' ').title().replace(' ', '') + 'Config'
        if not hasattr(schema_module, schema_class_name):
            # Try alternative naming
            schema_class_name = schema_name.upper() + '_CONFIG'

        if not hasattr(schema_module, schema_class_name):
            raise ConfigError(f"Schema class '{schema_class_name}' not found in {schema_file}")

        schema_class = getattr(schema_module, schema_class_name)
        self._schema_cache[schema_name] = schema_class
        return schema_class

class ConfigLoader:
    """Configuration file loader supporting multiple formats."""

    SUPPORTED_FORMATS = {'.yaml', '.yml', '.json'}

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self, config_name: str, environment: str = "default") -> Dict[str, Any]:
        """Load configuration from file."""
        config_file = self._find_config_file(config_name, environment)

        if config_file.suffix.lower() in ['.yaml', '.yml']:
            return self._load_yaml(config_file)
        elif config_file.suffix.lower() == '.json':
            return self._load_json(config_file)
        else:
            raise ConfigError(f"Unsupported config format: {config_file.suffix}")

    def _find_config_file(self, config_name: str, environment: str) -> Path:
        """Find the appropriate config file for the environment."""
        # Try environment-specific first, then default
        for env in [environment, "default"]:
            for ext in self.SUPPORTED_FORMATS:
                config_file = self.config_dir / f"{config_name}.{env}{ext}"
                if config_file.exists():
                    return config_file

        raise ConfigNotFoundError(f"Configuration '{config_name}' not found for environment '{environment}'")

    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigError(f"Failed to load YAML config from {file_path}: {e}")

    def _load_json(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON configuration."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ConfigError(f"Failed to load JSON config from {file_path}: {e}")

class ConfigWatcher(FileSystemEventHandler):
    """File system watcher for configuration hot-reloading."""

    def __init__(self, config_system: 'ConfigSystem'):
        self.config_system = config_system
        self.last_reload = datetime.now()

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix in ['.yaml', '.yml', '.json'] and file_path.parent.name in ['config', 'config_schemas']:
            # Debounce rapid changes
            if (datetime.now() - self.last_reload).total_seconds() > 1:
                logger.info(f"Configuration file changed: {file_path}")
                asyncio.create_task(self.config_system.reload_config())
                self.last_reload = datetime.now()

class ConfigSystem:
    """
    Unified Configuration Management System.

    This is the main entry point for all configuration needs in MAMcrawler.
    Provides hierarchical configuration with environment overrides, validation,
    security, and hot-reloading capabilities.
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.config_dir = self.project_root / "config"
        self.schemas_dir = self.project_root / "config_schemas"
        self.secrets_dir = self.project_root / "config_secrets"

        # Initialize components
        self.secret_manager = SecretManager(self.secrets_dir)
        self.validator = ConfigValidator(self.schemas_dir)
        self.loader = ConfigLoader(self.config_dir)

        # Configuration state
        self._config_cache: Dict[str, Any] = {}
        self._metadata: Dict[str, ConfigMetadata] = {}
        self._runtime_overrides: Dict[str, Any] = {}
        self._environment = self._detect_environment()

        # Hot-reloading
        self.watcher = ConfigWatcher(self)
        self.observer: Optional[Observer] = None
        self._reload_callbacks: List[Callable] = []

        # Initialize configuration
        self._initialize_config()

    def _detect_environment(self) -> ConfigEnvironment:
        """Detect the current environment."""
        env_name = os.getenv('APP_ENV', os.getenv('ENV', 'development')).lower()

        return ConfigEnvironment(
            name=env_name,
            is_production=env_name in ['prod', 'production'],
            is_development=env_name in ['dev', 'development', 'local'],
            is_staging=env_name in ['staging', 'stage'],
            config_paths=[
                self.config_dir / f"*.{env_name}.yaml",
                self.config_dir / f"*.{env_name}.yml",
                self.config_dir / f"*.{env_name}.json",
                self.config_dir / "*.default.yaml",
                self.config_dir / "*.default.yml",
                self.config_dir / "*.default.json",
            ]
        )

    def _initialize_config(self):
        """Initialize the configuration system."""
        try:
            # Load base configurations
            self._load_base_configs()

            # Apply environment overrides
            self._apply_environment_overrides()

            # Validate configuration
            self._validate_all_configs()

            logger.info(f"Configuration system initialized for environment: {self._environment.name}")

        except Exception as e:
            logger.error(f"Failed to initialize configuration system: {e}")
            raise

    def _load_base_configs(self):
        """Load base configuration files."""
        config_files = [
            "app", "database", "api_endpoints", "crawler", "logging",
            "security", "system", "mam_crawler", "audiobook_automation"
        ]

        for config_name in config_files:
            try:
                config_data = self.loader.load_config(config_name, self._environment.name)
                self._config_cache[config_name] = config_data
                self._update_metadata(config_name, config_data)
            except ConfigNotFoundError:
                logger.warning(f"Configuration '{config_name}' not found, using defaults")
                self._config_cache[config_name] = {}

    def _apply_environment_overrides(self):
        """Apply environment variable overrides."""
        # Environment variable mapping
        env_mappings = {
            'app.name': 'APP_NAME',
            'app.version': 'APP_VERSION',
            'app.debug': 'DEBUG_MODE',
            'database.host': 'POSTGRES_HOST',
            'database.port': 'POSTGRES_PORT',
            'database.name': 'POSTGRES_DB',
            'database.user': 'POSTGRES_USER',
            'api_endpoints.abs_url': 'ABS_URL',
            'api_endpoints.abs_token': 'ABS_TOKEN',
            'api_endpoints.mam_username': 'MAM_USERNAME',
            'api_endpoints.mam_password': 'MAM_PASSWORD',
            'crawler.headless': 'BROWSER_HEADLESS',
            'logging.level': 'LOG_LEVEL',
        }

        for config_path, env_var in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                self.set_config_value(config_path, env_value)

    def _validate_all_configs(self):
        """Validate all loaded configurations."""
        for config_name, config_data in self._config_cache.items():
            try:
                validated_data = self.validator.validate_config(config_data, config_name)
                self._config_cache[config_name] = validated_data
            except ConfigNotFoundError:
                # No schema available, skip validation
                pass
            except ValidationError as e:
                logger.error(f"Configuration validation failed for '{config_name}': {e}")
                raise

    def _update_metadata(self, config_name: str, config_data: Dict[str, Any]):
        """Update metadata for a configuration."""
        config_file = self._find_config_file(config_name)
        if config_file:
            checksum = self._calculate_checksum(config_data)
            self._metadata[config_name] = ConfigMetadata(
                path=config_file,
                last_modified=datetime.fromtimestamp(config_file.stat().st_mtime),
                checksum=checksum,
                environment=self._environment.name
            )

    def _find_config_file(self, config_name: str) -> Optional[Path]:
        """Find the config file for a given name."""
        for pattern in self._environment.config_paths:
            if pattern.match(f"*{config_name}*"):
                # This is a simplified check - in practice, we'd glob the directory
                for ext in ['.yaml', '.yml', '.json']:
                    candidate = self.config_dir / f"{config_name}{ext}"
                    if candidate.exists():
                        return candidate
        return None

    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for configuration data."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    # Public API methods

    def get_config(self, config_name: str) -> Dict[str, Any]:
        """Get a configuration section."""
        return self._config_cache.get(config_name, {})

    def get_config_value(self, config_path: str, default=None):
        """Get a specific configuration value using dot notation."""
        keys = config_path.split('.')
        value = self._config_cache

        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default

        # Check runtime overrides
        if config_path in self._runtime_overrides:
            return self._runtime_overrides[config_path]

        return value if value is not None else default

    def set_config_value(self, config_path: str, value: Any):
        """Set a configuration value at runtime."""
        keys = config_path.split('.')
        config = self._config_cache

        # Navigate to the parent dict
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        # Set the value
        config[keys[-1]] = value
        self._runtime_overrides[config_path] = value

    def get_secret(self, key: str, namespace: str = "default") -> str:
        """Get a decrypted secret."""
        return self.secret_manager.load_secret(key, namespace)

    def set_secret(self, key: str, value: str, namespace: str = "default"):
        """Store an encrypted secret."""
        self.secret_manager.store_secret(key, value, namespace)

    def start_hot_reload(self):
        """Start hot-reloading of configuration files."""
        if self.observer is None:
            self.observer = Observer()
            self.observer.schedule(self.watcher, str(self.config_dir), recursive=True)
            self.observer.schedule(self.watcher, str(self.schemas_dir), recursive=True)
            self.observer.start()
            logger.info("Configuration hot-reloading enabled")

    def stop_hot_reload(self):
        """Stop hot-reloading."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Configuration hot-reloading disabled")

    async def reload_config(self):
        """Reload configuration from files."""
        try:
            # Reload base configs
            self._load_base_configs()
            self._apply_environment_overrides()
            self._validate_all_configs()

            # Notify callbacks
            for callback in self._reload_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback()
                    else:
                        callback()
                except Exception as e:
                    logger.error(f"Error in reload callback: {e}")

            logger.info("Configuration reloaded successfully")

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")

    def add_reload_callback(self, callback: Callable):
        """Add a callback to be called when configuration is reloaded."""
        self._reload_callbacks.append(callback)

    def get_environment_info(self) -> Dict[str, Any]:
        """Get information about the current environment."""
        return {
            "environment": self._environment.name,
            "is_production": self._environment.is_production,
            "is_development": self._environment.is_development,
            "is_staging": self._environment.is_staging,
            "config_dir": str(self.config_dir),
            "schemas_dir": str(self.schemas_dir),
            "secrets_dir": str(self.secrets_dir),
            "loaded_configs": list(self._config_cache.keys()),
            "metadata": {
                name: {
                    "path": str(meta.path),
                    "last_modified": meta.last_modified.isoformat(),
                    "checksum": meta.checksum[:8] + "..."
                }
                for name, meta in self._metadata.items()
            }
        }

    def validate_configuration(self) -> List[str]:
        """Validate the entire configuration system."""
        errors = []

        # Check required configurations
        required_configs = ["app", "database", "api_endpoints"]
        for config_name in required_configs:
            if config_name not in self._config_cache:
                errors.append(f"Required configuration '{config_name}' is missing")

        # Check critical secrets
        critical_secrets = ["anthropic_api_key", "abs_token", "mam_password"]
        for secret in critical_secrets:
            try:
                self.get_secret(secret)
            except ConfigNotFoundError:
                errors.append(f"Critical secret '{secret}' is not configured")

        # Validate all configs
        try:
            self._validate_all_configs()
        except ValidationError as e:
            errors.append(f"Configuration validation error: {e}")

        return errors

    # Context manager support
    async def __aenter__(self):
        self.start_hot_reload()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stop_hot_reload()

# Global configuration system instance
_config_system: Optional[ConfigSystem] = None

def get_config_system() -> ConfigSystem:
    """Get the global configuration system instance."""
    global _config_system
    if _config_system is None:
        _config_system = ConfigSystem()
    return _config_system

def get_config_value(path: str, default=None):
    """Convenience function to get a configuration value."""
    return get_config_system().get_config_value(path, default)

def set_config_value(path: str, value: Any):
    """Convenience function to set a configuration value."""
    get_config_system().set_config_value(path, value)

def get_secret(key: str, namespace: str = "default") -> str:
    """Convenience function to get a secret."""
    return get_config_system().get_secret(key, namespace)

def set_secret(key: str, value: str, namespace: str = "default"):
    """Convenience function to set a secret."""
    get_config_system().set_secret(key, value, namespace)

# Initialize on import
try:
    _config_system = ConfigSystem()
    logger.info("Configuration system initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize configuration system: {e}")
    raise

if __name__ == "__main__":
    # Configuration system test
    import sys

    print("MAMcrawler Unified Configuration System")
    print("=" * 50)

    try:
        config_system = get_config_system()

        # Show environment info
        env_info = config_system.get_environment_info()
        print(f"Environment: {env_info['environment']}")
        print(f"Production: {env_info['is_production']}")
        print(f"Config Directory: {env_info['config_dir']}")
        print(f"Loaded Configs: {', '.join(env_info['loaded_configs'])}")

        # Validate configuration
        errors = config_system.validate_configuration()
        if errors:
            print("\nConfiguration Errors:")
            for error in errors:
                print(f"- {error}")
            sys.exit(1)
        else:
            print("\n✓ Configuration validation passed")

        # Test some values
        print("\nSample Configuration Values:")
        print(f"App Name: {get_config_value('app.name', 'MAMcrawler')}")
        print(f"Debug Mode: {get_config_value('app.debug', False)}")
        print(f"ABS URL: {get_config_value('api_endpoints.abs_url', 'not set')}")

        print("\n✓ Configuration system test completed successfully")

    except Exception as e:
        print(f"✗ Configuration system test failed: {e}")
        sys.exit(1)