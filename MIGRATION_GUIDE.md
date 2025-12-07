# Unified Logging System Migration Guide

## Overview

The MAMcrawler project now has a comprehensive unified logging system that consolidates all logging approaches across the codebase. This guide explains how to migrate existing code to use the new system.

## Key Benefits

- **Structured Logging**: JSON format with consistent metadata
- **Multiple Destinations**: Console, file, database, remote logging
- **Performance Monitoring**: Built-in timing and metrics collection
- **Security Events**: Dedicated security logging
- **Distributed Tracing**: Request correlation and tracing
- **Centralized Configuration**: Environment-based config management

## Migration Steps

### 1. Replace Import Statements

**Before:**
```python
import logging
logger = logging.getLogger(__name__)
```

**After:**
```python
from logging_system import get_logger
logger = get_logger(__name__)
```

### 2. Update Log Calls

**Basic logging remains the same:**
```python
logger.info("Processing started")
logger.error("An error occurred", structured_data={"error_code": 500})
```

**Enhanced structured logging:**
```python
# Add structured data
logger.info("User login", structured_data={
    "user_id": "user123",
    "ip_address": "192.168.1.100",
    "method": "password"
})

# Performance logging
from logging_system import log_performance
log_performance("database_query", 150.5, {"query_type": "SELECT"})

# Security events
from logging_system import log_security_event
log_security_event("Failed login attempt", "WARNING", {
    "user_id": "user123",
    "ip_address": "192.168.1.100"
})

# Audit trails
from logging_system import log_audit
log_audit("USER_LOGIN", user="user123", resource="auth_system")
```

### 3. Performance Monitoring

**Before:**
```python
import time
start = time.time()
# ... do work ...
duration = time.time() - start
print(f"Operation took {duration:.2f}s")
```

**After:**
```python
from logging_system import performance_timer

with performance_timer("my_operation"):
    # ... do work ...
    pass
```

### 4. Configuration

The system automatically loads configuration based on:

1. `LOG_CONFIG` environment variable (path to config file)
2. `ENVIRONMENT` environment variable (development/production/testing)
3. Falls back to `logging_config/default.json`

**Example:**
```bash
# Use specific config
export LOG_CONFIG=/path/to/custom_config.json

# Use environment config
export ENVIRONMENT=production
```

## Configuration Files

Located in `logging_config/` directory:

- `development.json`: Debug logging, console + file output
- `production.json`: Info level, file + database output
- `testing.json`: Debug level, console only
- `default.json`: Fallback configuration

## New Features Available

### Structured Data
```python
logger.info("API request", structured_data={
    "endpoint": "/api/users",
    "method": "GET",
    "response_time_ms": 150,
    "status_code": 200
})
```

### Tracing Context
```python
from logging_system import trace_context

with trace_context("user_registration", "validate_input"):
    # All logs in this context will include trace/span IDs
    logger.info("Validating user input")
    # ... more operations ...
```

### Custom Log Levels
```python
from logging_system import LogLevel

logger.log(LogLevel.SECURITY.value, "Security event")
logger.log(LogLevel.PERFORMANCE.value, "Performance metric")
logger.log(LogLevel.AUDIT.value, "Audit event")
```

## Migration Priority

1. **High Priority**: Core modules (database, authentication, API endpoints)
2. **Medium Priority**: Business logic modules
3. **Low Priority**: Utility scripts and one-off tools

## Testing Migration

After migrating a module, test that:

1. Logs still appear in expected locations
2. Structured data is properly formatted
3. Performance monitoring works
4. No exceptions are raised

## Rollback Plan

If issues arise, you can temporarily revert by:

1. Keep old logging imports commented out
2. Switch back to standard logging calls
3. Revert configuration to use basic logging

## Support

The new logging system includes comprehensive error handling and will fallback gracefully if configuration issues occur. Check the logs directory for any system errors.

## Files Created

- `logging_system.py`: Main logging framework
- `logging_config/`: Configuration files
- `logging_utils/`: Analysis and utility tools
- `test_unified_logging.py`: Comprehensive test suite

## Next Steps

1. Start migrating high-priority modules
2. Update documentation to reference new logging patterns
3. Monitor system performance and adjust configurations as needed
4. Consider integrating with external monitoring systems (ELK stack, etc.)