# Configuration Secrets Management

This directory contains encrypted secrets for the MAMcrawler configuration system.

## Overview

The secrets management system provides secure storage and retrieval of sensitive configuration data such as API keys, passwords, and tokens. All secrets are encrypted using AES-256-GCM encryption with a master key.

## Files

- `.master.key` - Master encryption key (auto-generated, do not modify)
- `{namespace}/{secret_name}.enc` - Encrypted secret files organized by namespace

## Usage

### Setting Secrets

```python
from config_system import set_secret

# Store an API key
set_secret('anthropic_api_key', 'your-api-key-here')

# Store credentials in a specific namespace
set_secret('mam_password', 'your-password', namespace='mam')
```

### Retrieving Secrets

```python
from config_system import get_secret

# Retrieve a secret
api_key = get_secret('anthropic_api_key')

# Retrieve from a specific namespace
password = get_secret('mam_password', namespace='mam')
```

### Available Secrets

The following secrets are expected by the configuration system:

#### API Keys
- `anthropic_api_key` - Anthropic/Claude API key
- `abs_token` - Audiobookshelf API token
- `google_books_api_key` - Google Books API key
- `prowlarr_api_key` - Prowlarr API key
- `hardcover_api_key` - Hardcover API key

#### Credentials
- `mam_username` - MyAnonamouse username
- `mam_password` - MyAnonamouse password
- `qbittorrent_password` - qBittorrent web UI password

#### Database
- `postgres_password` - PostgreSQL database password

## Security Notes

- The master key is automatically generated and stored locally
- Secrets are encrypted at rest using industry-standard encryption
- Never commit secret files to version control
- The `.master.key` file should be backed up securely
- If the master key is lost, all secrets become inaccessible

## Migration from .env

To migrate existing secrets from `.env` files:

1. The configuration system will automatically detect and migrate secrets during initialization
2. Old `.env` files should be removed after successful migration
3. Verify that all secrets are accessible through the new system

## Backup and Recovery

- Regularly backup the `.master.key` file to a secure location
- Keep encrypted secret files in version control (they are encrypted)
- In case of master key loss, secrets must be re-entered manually

## Troubleshooting

### Cannot decrypt secret
- Verify the master key file exists and is readable
- Check file permissions on the secrets directory
- Ensure the secret was stored with the correct namespace

### Master key not found
- The system will automatically generate a new master key
- Existing encrypted secrets will become inaccessible
- Re-enter secrets using the new master key