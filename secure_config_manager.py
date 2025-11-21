"""
Secure Configuration Management System
Handles API keys, credentials, and sensitive configuration data securely.
Implements proper environment variable management and credential sanitization.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, Union
from pathlib import Path
from dataclasses import dataclass, field
from cryptography.fernet import Fernet
import base64
import secrets

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """Custom exception for security-related configuration errors."""
    pass

class CredentialSanitizer:
    """Utility class for sanitizing sensitive data in logs and outputs."""
    
    @staticmethod
    def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
        """Mask sensitive data for safe logging/display."""
        if not data or len(data) <= visible_chars * 2:
            return "*" * len(data) if data else ""
        return data[:visible_chars] + "*" * (len(data) - visible_chars * 2) + data[-visible_chars:]
    
    @staticmethod
    def sanitize_for_logging(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary for safe logging."""
        sensitive_keys = {
            'password', 'token', 'secret', 'key', 'api_key', 'auth', 
            'credential', 'username', 'email', 'private', 'secret_key'
        }
        
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str):
                    sanitized[key] = CredentialSanitizer.mask_sensitive_data(value)
                else:
                    sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = CredentialSanitizer.sanitize_for_logging(value)
            else:
                sanitized[key] = value
        return sanitized

@dataclass
class SecureConfig:
    """Secure configuration manager with encryption and validation."""
    
    # API Keys - CRITICAL: These should NEVER be hardcoded
    anthropic_api_key: Optional[str] = field(default=None, metadata={"sensitive": True})
    google_books_api_key: Optional[str] = field(default=None, metadata={"sensitive": True})
    
    # Database credentials
    postgres_user: str = "postgres"
    postgres_password: Optional[str] = field(default=None, metadata={"sensitive": True})
    
    # Audiobookshelf integration
    abs_url: str = "http://localhost:13378"
    abs_token: Optional[str] = field(default=None, metadata={"sensitive": True})
    
    # MyAnonamouse credentials (for crawler)
    mam_username: Optional[str] = field(default=None, metadata={"sensitive": True})
    mam_password: Optional[str] = field(default=None, metadata={"sensitive": True})
    
    # qBittorrent credentials
    qb_username: str = "admin"
    qb_password: Optional[str] = field(default=None, metadata={"sensitive": True})
    
    # Other API keys
    nyt_api_key: Optional[str] = field(default=None, metadata={"sensitive": True})
    
    # Security settings
    encryption_enabled: bool = True
    session_timeout: int = 3600  # 1 hour
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_required_fields()
        self._load_from_environment()
        self._validate_configuration()
    
    def _validate_required_fields(self):
        """Validate that required fields are properly configured."""
        required_fields = [
            ('anthropic_api_key', 'ANTHROPIC_API_KEY'),
            ('google_books_api_key', 'GOOGLE_BOOKS_API_KEY'),
            ('abs_token', 'ABS_TOKEN'),
            ('mam_username', 'MAM_USERNAME'),
            ('mam_password', 'MAM_PASSWORD'),
        ]
        
        missing_fields = []
        for field_name, env_var in required_fields:
            if not getattr(self, field_name):
                missing_fields.append(f"{field_name} (env: {env_var})")
        
        if missing_fields:
            logger.warning(f"Missing optional configuration: {', '.join(missing_fields)}")
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        env_mappings = {
            'anthropic_api_key': 'ANTHROPIC_API_KEY',
            'google_books_api_key': 'GOOGLE_BOOKS_API_KEY',
            'postgres_password': 'POSTGRES_PASSWORD',
            'abs_token': 'ABS_TOKEN',
            'abs_url': 'ABS_URL',
            'mam_username': 'MAM_USERNAME',
            'mam_password': 'MAM_PASSWORD',
            'qb_username': 'QB_USERNAME',
            'qb_password': 'QB_PASSWORD',
            'nyt_api_key': 'NYT_API_KEY',
        }
        
        for field_name, env_var in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                setattr(self, field_name, env_value)
    
    def _validate_configuration(self):
        """Validate configuration values for security and correctness."""
        validation_errors = []
        
        # Check for obvious hardcoded values
        hardcoded_patterns = {
            'your_anthropic_api_key_here': 'ANTHROPIC_API_KEY appears to be a placeholder',
            'your_google_books_api_key_here': 'GOOGLE_BOOKS_API_KEY appears to be a placeholder',
            'your_abs_token_here': 'ABS_TOKEN appears to be a placeholder',
            'your_mam_password': 'MAM_PASSWORD appears to be a placeholder',
        }
        
        for field_name, env_var in [
            ('anthropic_api_key', 'ANTHROPIC_API_KEY'),
            ('google_books_api_key', 'GOOGLE_BOOKS_API_KEY'),
            ('abs_token', 'ABS_TOKEN'),
            ('mam_password', 'MAM_PASSWORD'),
        ]:
            value = getattr(self, field_name)
            if value:
                for pattern, message in hardcoded_patterns.items():
                    if pattern in value:
                        validation_errors.append(f"{env_var}: {message}")
        
        if validation_errors:
            raise SecurityError(f"Configuration validation failed: {'; '.join(validation_errors)}")
    
    def get_safe_dict(self) -> Dict[str, Any]:
        """Get configuration dictionary with sensitive data masked."""
        config_dict = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if key.endswith('_key') or key.endswith('_password') or key.endswith('_token'):
                    config_dict[key] = CredentialSanitizer.mask_sensitive_data(str(value))
                else:
                    config_dict[key] = value
        return config_dict
    
    def validate_api_connectivity(self) -> Dict[str, bool]:
        """Validate API connectivity for configured services."""
        import aiohttp
        import asyncio
        
        results = {}
        
        # Test Audiobookshelf connectivity
        if self.abs_token and self.abs_url:
            async def test_abs():
                try:
                    headers = {'Authorization': f'Bearer {self.abs_token}'}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.abs_url}/api/libraries", headers=headers) as resp:
                            return resp.status == 200
                except Exception:
                    return False
            results['abs'] = asyncio.run(test_abs())
        
        return results

class SecureFileManager:
    """Secure file management for configuration and credentials."""
    
    def __init__(self, config_dir: str = ".secure_config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self._generate_encryption_key()
    
    def _generate_encryption_key(self):
        """Generate and store encryption key securely."""
        key_file = self.config_dir / ".encryption.key"
        
        if not key_file.exists():
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            # Set restrictive permissions (Unix-like systems)
            try:
                os.chmod(key_file, 0o600)
            except (OSError, AttributeError):
                pass  # Windows doesn't support chmod
    
    def store_secure_config(self, config: SecureConfig, filename: str = "config.enc"):
        """Store configuration securely with encryption."""
        key_file = self.config_dir / ".encryption.key"
        key = key_file.read_bytes()
        fernet = Fernet(key)
        
        config_data = json.dumps(config.__dict__, default=str)
        encrypted_data = fernet.encrypt(config_data.encode())
        
        config_file = self.config_dir / filename
        config_file.write_bytes(encrypted_data)
        
        logger.info(f"Secure configuration stored: {config_file}")
    
    def load_secure_config(self, filename: str = "config.enc") -> Optional[SecureConfig]:
        """Load configuration securely with decryption."""
        key_file = self.config_dir / ".encryption.key"
        if not key_file.exists():
            logger.warning("Encryption key not found")
            return None
        
        key = key_file.read_bytes()
        fernet = Fernet(key)
        
        config_file = self.config_dir / filename
        if not config_file.exists():
            logger.warning(f"Configuration file not found: {config_file}")
            return None
        
        try:
            encrypted_data = config_file.read_bytes()
            decrypted_data = fernet.decrypt(encrypted_data)
            config_dict = json.loads(decrypted_data.decode())
            
            return SecureConfig(**config_dict)
        except Exception as e:
            logger.error(f"Failed to load secure configuration: {e}")
            return None

# Global secure configuration instance
_secure_config = None

def get_secure_config() -> SecureConfig:
    """Get the global secure configuration instance."""
    global _secure_config
    if _secure_config is None:
        _secure_config = SecureConfig()
    return _secure_config

def create_secure_config_template():
    """Create a template .env file with proper structure."""
    template_content = """# MAM Crawler Secure Configuration Template
# Copy this file to .env and fill in your actual values

# ==============================================
# REQUIRED API KEYS (Never commit real values)
# ==============================================
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_BOOKS_API_KEY=your_google_books_api_key_here

# ==============================================
# DATABASE CONFIGURATION
# ==============================================
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_postgres_password

# ==============================================
# AUDIOBOOKSHELF INTEGRATION
# ==============================================
ABS_URL=http://localhost:13378
ABS_TOKEN=your_abs_api_token_here

# ==============================================
# MYANONAMOUSE CREDENTIALS
# ==============================================
MAM_USERNAME=your_mam_username
MAM_PASSWORD=your_secure_mam_password

# ==============================================
# QBITTORRENT CONFIGURATION
# ==============================================
QB_USERNAME=admin
QB_PASSWORD=your_qbittorrent_password

# ==============================================
# OPTIONAL API KEYS
# ==============================================
NYT_API_KEY=your_nyt_api_key

# ==============================================
# SECURITY SETTINGS
# ==============================================
SECURITY_LEVEL=high
ENCRYPTION_ENABLED=true
SESSION_TIMEOUT=3600

# ==============================================
# DEVELOPMENT SETTINGS
# ==============================================
DEMO_MODE=false
DEBUG_LEVEL=INFO
LOG_RETENTION_DAYS=30
"""
    
    template_file = Path(".env.template")
    template_file.write_text(template_content)
    logger.info(f"Configuration template created: {template_file}")
    
    # Also create .gitignore for sensitive files
    gitignore_content = """# Security and Configuration
.env
.env.local
.env.production
.secure_config/
.secrets/
config.enc
*.key
*.pem
*.p12

# Logs with potential sensitive data
*.log
logs/
debug_*.html
*_response.html

# Database files with potential cached credentials
*.db
*.sqlite
*.sqlite3
cache/
"""
    
    gitignore_file = Path(".gitignore")
    gitignore_file.write_text(gitignore_content)
    logger.info(f"Security .gitignore created: {gitignore_file}")

if __name__ == "__main__":
    # Create configuration template
    create_secure_config_template()
    
    # Initialize secure config
    try:
        config = get_secure_config()
        print("Secure configuration initialized successfully")
        print("Safe configuration preview:")
        print(json.dumps(config.get_safe_dict(), indent=2))
    except SecurityError as e:
        print(f"Configuration error: {e}")
        print("Please check your .env file and ensure all required variables are set")