# Logging Configuration

This directory contains configuration files for the unified logging system.

## Configuration Files

### `default.json`
Default configuration used when no environment-specific config is found.

### `development.json`
Configuration for development environment:
- DEBUG level logging
- Console and file output
- Tracing enabled
- Smaller log files for development

### `production.json`
Configuration for production environment:
- INFO level logging
- File and database output (no console spam)
- Optimized for performance
- Larger log files with longer retention

### `testing.json`
Configuration for testing environment:
- DEBUG level logging
- Console only (no persistent files)
- Minimal configuration for fast tests

## Configuration Options

| Option | Type | Description |
|--------|------|-------------|
| `level` | string | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `destinations` | array | Output destinations (console, file, database, remote) |
| `format` | string | Log format (structured, simple, json) |
| `enable_json` | boolean | Enable JSON structured logging |
| `enable_tracing` | boolean | Enable distributed tracing |
| `enable_metrics` | boolean | Enable performance metrics collection |
| `max_file_size_mb` | number | Maximum log file size in MB |
| `backup_count` | number | Number of backup log files to keep |
| `log_directory` | string | Directory for log files |
| `app_name` | string | Application name for log identification |
| `environment` | string | Environment name |

## Usage

The logging system automatically loads the appropriate configuration based on:

1. `LOG_CONFIG` environment variable (path to config file)
2. `ENVIRONMENT` environment variable (development/production/testing)
3. Falls back to `default.json`

Example:
```bash
# Use specific config file
export LOG_CONFIG=/path/to/custom_config.json

# Use environment-based config
export ENVIRONMENT=production

# Use default config (no environment variables)