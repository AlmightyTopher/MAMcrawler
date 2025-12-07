# MAMcrawler Unified Configuration System

## Overview

The MAMcrawler project has been consolidated into a single, unified configuration management system that provides:

- **Hierarchical configuration** with environment overrides
- **Type-safe configuration** with Pydantic validation
- **Secure secret handling** with AES-256-GCM encryption
- **Configuration hot-reloading** for runtime updates
- **Multi-environment support** (dev, staging, prod)
- **Comprehensive error handling** and validation

## Architecture

### Core Components

1. **`config_system.py`** - Main configuration manager
2. **`config/`** - YAML/JSON configuration files
3. **`config_schemas/`** - Pydantic validation schemas
4. **`config_secrets/`** - Encrypted secrets storage

### Configuration Hierarchy

```
Environment Variables (highest priority)
    ↓
Runtime Overrides
    ↓
Environment-specific config files
    ↓
Default config files (lowest priority)
```

## Quick Start

### Basic Usage

```python
from config_system import get_config_value, get_secret

# Get configuration values
app_name = get_config_value('app.name', 'MAMcrawler')
debug_mode = get_config_value('app.debug', False)

# Get secrets
api_key = get_secret('anthropic_api_key')
password = get_secret('mam_password')
```

### Advanced Usage

```python
from config_system import ConfigSystem

config_system = ConfigSystem()

# Get entire configuration sections
crawler_config = config_system.get_config('crawler')
api_endpoints = config_system.get_config('api_endpoints')

# Set runtime overrides
config_system.set_config_value('app.debug', True)

# Start hot-reloading
config_system.start_hot_reload()
```

## Configuration Files

### Directory Structure

```
config/
├── app.yaml              # Application settings
├── database.yaml         # Database configuration
├── api_endpoints.yaml    # API endpoints and credentials
├── crawler.yaml          # Crawler settings
├── logging.yaml          # Logging configuration
├── security.yaml         # Security settings
├── system.yaml           # System-wide settings
├── mam_crawler.yaml      # MAM-specific crawler config
└── audiobook_automation.yaml  # Automation settings

config_schemas/
├── app.py
├── database.py
├── api_endpoints.py
├── crawler.py
├── logging.py
├── security.py
├── system.py
├── mam_crawler.py
└── audiobook_automation.py

config_secrets/
├── .master.key          # Encryption key (auto-generated)
├── default/
│   ├── anthropic_api_key.enc
│   ├── abs_token.enc
│   └── ...
└── README.md
```

### Environment Support

Create environment-specific files:

```
config/app.production.yaml
config/database.staging.yaml
config/api_endpoints.development.yaml
```

Set the environment:

```bash
export APP_ENV=production
# or
export ENV=staging
```

## Migration Guide

### From Old Config System

The old configuration files have been updated to use the new system while maintaining backward compatibility:

#### config.py → Backward Compatible
```python
# Old usage still works
from config import config
abs_url = config.api_endpoints.abs_url
api_key = config.security.anthropic_api_key.get_secret_value()
```

#### config_simple.py → Backward Compatible
```python
# Old usage still works
from config_simple import config
qb_host = config.qb_host
mam_password = config.mam_password
```

#### mam_crawler_config.py → Updated
```python
# Now uses unified config
from mam_crawler_config import mam_procedures
# Configuration loaded from config/mam_crawler.yaml
```

### Updating Your Code

#### Replace Direct Environment Access
```python
# Old
import os
api_key = os.getenv('ANTHROPIC_API_KEY')

# New
from config_system import get_secret
api_key = get_secret('anthropic_api_key')
```

#### Replace Config Imports
```python
# Old
from config import config
from config_simple import config as simple_config

# New
from config_system import get_config_value, get_secret
```

#### Configuration Access Patterns
```python
# Old patterns
abs_url = config.api_endpoints.abs_url
debug = config.system.debug_mode
api_key = config.security.anthropic_api_key.get_secret_value()

# New patterns
abs_url = get_config_value('api_endpoints.abs_url')
debug = get_config_value('app.debug')
api_key = get_secret('anthropic_api_key')
```

## Secret Management

### Setting Secrets

```python
from config_system import set_secret

# Store API keys
set_secret('anthropic_api_key', 'your-api-key-here')
set_secret('abs_token', 'your-token-here')

# Store credentials
set_secret('mam_username', 'your-username')
set_secret('mam_password', 'your-password')
```

### Retrieving Secrets

```python
from config_system import get_secret

# Get secrets
api_key = get_secret('anthropic_api_key')
password = get_secret('mam_password')
```

### Secret Namespaces

```python
# Default namespace
set_secret('api_key', 'value')

# Custom namespace
set_secret('api_key', 'value', namespace='production')
api_key = get_secret('api_key', namespace='production')
```

## Validation

### Schema Validation

Configuration files are validated against Pydantic schemas:

```python
# config_schemas/app.py
from pydantic import BaseModel, Field

class AppConfig(BaseModel):
    name: str = Field(default="MAMcrawler")
    version: str = Field(default="2.0.0")
    debug: bool = Field(default=False)
```

### Runtime Validation

```python
from config_system import ConfigSystem

config_system = ConfigSystem()
errors = config_system.validate_configuration()

if errors:
    for error in errors:
        print(f"Configuration error: {error}")
```

## Hot Reloading

### Enable Hot Reloading

```python
from config_system import ConfigSystem

config_system = ConfigSystem()
config_system.start_hot_reload()

# Configuration changes will be automatically reloaded
```

### Reload Callbacks

```python
def on_config_reload():
    print("Configuration reloaded!")

config_system.add_reload_callback(on_config_reload)
```

## Environment Variables

### Supported Environment Variables

| Environment Variable | Config Path | Description |
|---------------------|-------------|-------------|
| `APP_ENV` | - | Environment (development/production/staging) |
| `APP_NAME` | `app.name` | Application name |
| `APP_VERSION` | `app.version` | Application version |
| `DEBUG_MODE` | `app.debug` | Debug mode |
| `ABS_URL` | `api_endpoints.abs_url` | Audiobookshelf URL |
| `ABS_TOKEN` | `api_endpoints.abs_token` | Audiobookshelf token |
| `MAM_USERNAME` | `api_endpoints.mam_username` | MAM username |
| `MAM_PASSWORD` | `api_endpoints.mam_password` | MAM password |
| `QB_HOST` | `api_endpoints.qbittorrent.host` | qBittorrent host |
| `QB_PORT` | `api_endpoints.qbittorrent.port` | qBittorrent port |
| `QB_USERNAME` | `api_endpoints.qbittorrent.username` | qBittorrent username |
| `QB_PASSWORD` | `api_endpoints.qbittorrent.password` | qBittorrent password |
| `BROWSER_HEADLESS` | `crawler.browser.headless` | Browser headless mode |
| `LOG_LEVEL` | `logging.console.level` | Log level |

## Security Features

### Secret Encryption
- AES-256-GCM encryption for all secrets
- Master key auto-generated and stored securely
- Secrets never stored in plain text

### Access Control
- Secrets are decrypted only when accessed
- Master key protected with restrictive permissions
- Environment-specific secret isolation

### Validation
- All configuration validated against schemas
- Type checking prevents invalid values
- Required fields enforced

## Troubleshooting

### Common Issues

#### Configuration Not Found
```
Error: Configuration 'missing_config' not found
```
**Solution**: Create the missing configuration file in `config/missing_config.yaml`

#### Secret Not Found
```
Error: Secret 'missing_secret' not found
```
**Solution**: Set the secret using `set_secret('missing_secret', 'value')`

#### Validation Errors
```
Error: Configuration validation failed for 'app'
```
**Solution**: Check the configuration file against the schema in `config_schemas/app.py`

#### Master Key Issues
```
Error: Failed to decrypt secret
```
**Solution**: The master key may be corrupted. Delete `.master.key` and re-enter secrets.

### Debugging

Enable debug logging:
```python
import logging
logging.getLogger('config_system').setLevel(logging.DEBUG)
```

Check configuration status:
```python
from config_system import ConfigSystem
config_system = ConfigSystem()
info = config_system.get_environment_info()
print(info)
```

## Migration Status

### ✅ Completed
- [x] Unified configuration system implementation
- [x] Hierarchical configuration with environment overrides
- [x] Type-safe configuration with Pydantic validation
- [x] Secure secret handling with encryption
- [x] Configuration hot-reloading
- [x] Multi-environment support
- [x] Backward compatibility layers
- [x] Configuration schemas and validation
- [x] Documentation and examples

### 🔄 In Progress
- [ ] Full codebase migration (ongoing)
- [ ] Old configuration file archival

### 📋 Remaining Tasks

1. **Update remaining Python files** to use new configuration system
2. **Migrate hardcoded values** to configuration files
3. **Update documentation** to reflect new system
4. **Archive old configuration files** after full migration
5. **Add integration tests** for configuration system

### Migration Priority

1. **High Priority**: Core application files, API clients, database connections
2. **Medium Priority**: Utility scripts, background workers
3. **Low Priority**: Legacy scripts, deprecated features

## Support

For issues with the configuration system:

1. Check this documentation
2. Review error messages and logs
3. Validate configuration files against schemas
4. Test with minimal configuration
5. Check environment variables and secrets

## Agent 8 - Configuration Consolidation Specialist

This unified configuration system was designed and implemented by Agent 8 to provide a robust, secure, and maintainable configuration management solution for the MAMcrawler project.