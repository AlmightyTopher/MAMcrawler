# Rate Limiting Implementation Guide

## Overview

This guide explains how to apply rate limiting to API endpoints in MAMcrawler.

## Installation

First, install slowapi:

```bash
pip install slowapi
```

This is already included in `backend/requirements.txt`.

## Configuration

The rate limiting is configured in `backend/rate_limit.py` with predefined limits for different endpoint types.

### Predefined Rate Limits

```python
RATE_LIMITS = {
    "public": "10/minute",           # Public endpoints
    "authenticated": "60/minute",    # Protected endpoints
    "admin": "1000/minute",          # Admin endpoints
    "download": "20/hour",           # Download operations
    "metadata": "30/minute",         # Metadata queries
    "search": "20/minute",           # Search operations
    "health": "100/minute",          # Health checks
    "upload": "5/minute",            # File uploads
}
```

## Applying Rate Limits to Routes

### Step 1: Import Rate Limiter

```python
from backend.rate_limit import limiter, RATE_LIMITS
from fastapi import Request
```

### Step 2: Add Rate Limit Decorator

Apply the limiter decorator to your endpoint:

```python
from fastapi import APIRouter

router = APIRouter()

# Public endpoint - strict limit
@router.get("/public-endpoint")
@limiter.limit(RATE_LIMITS["public"])
async def public_endpoint(request: Request):
    return {"message": "success"}

# Authenticated endpoint - generous limit
@router.get("/api/books")
@limiter.limit(RATE_LIMITS["authenticated"])
async def list_books(request: Request):
    return {"books": [...]}

# Admin endpoint - very generous limit
@router.post("/admin/settings")
@limiter.limit(RATE_LIMITS["admin"])
async def update_settings(request: Request, settings: dict):
    return {"status": "updated"}
```

### Step 3: Configure in main.py

In `backend/main.py`, configure the rate limiter:

```python
from fastapi import FastAPI
from backend.rate_limit import add_rate_limiting

app = FastAPI()

# Add rate limiting
add_rate_limiting(app)
```

## Response Format

When a rate limit is exceeded, the API returns a 429 response:

```json
{
    "error": "rate_limit_exceeded",
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "detail": "10 per 1 minute",
    "retry_after": 60,
    "timestamp": "2025-11-25T12:34:56.789012"
}
```

The response includes a `Retry-After` header indicating when to retry.

## Custom Rate Limits

For custom limits on specific endpoints:

```python
from backend.rate_limit import limiter, create_custom_limit

# Create custom limit
@router.post("/expensive-operation")
@limiter.limit("5/hour")
async def expensive_operation(request: Request):
    return {"status": "completed"}

# Or use helper function
custom_limit = create_custom_limit(3, "minute")

@router.get("/special-endpoint")
@limiter.limit(custom_limit)
async def special_endpoint(request: Request):
    return {"data": "..."}
```

## Testing Rate Limits

Test rate limiting with curl:

```bash
# Make 11 requests in quick succession (limit is 10/minute)
for i in {1..11}; do
    curl -i http://localhost:8000/public-endpoint
done

# The 11th request should return 429
```

## Bypass Rate Limiting (Development Only)

In development, you can disable rate limiting by setting an environment variable:

```bash
# In .env
RATE_LIMIT_ENABLED=false
```

Then modify the decorator:

```python
if os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false":
    @limiter.limit(RATE_LIMITS["public"])
```

## Monitoring Rate Limits

Add logging to track rate limit hits:

```python
import logging

logger = logging.getLogger(__name__)

# In your endpoint
@router.get("/api/books")
@limiter.limit(RATE_LIMITS["authenticated"])
async def list_books(request: Request):
    logger.info(f"Books accessed by {request.client.host}")
    return {"books": [...]}
```

## Common Rate Limit Values

```
Requests per second:     60/minute or 1/second
Requests per minute:     10/minute
Requests per hour:       100/hour
Requests per day:        1000/day
```

## Troubleshooting

### Issue: "limiter not found" error

**Solution:** Make sure `add_rate_limiting(app)` is called in `main.py` before defining routes.

### Issue: Rate limit not working

**Solution:** Verify:
1. `slowapi` is installed: `pip list | grep slowapi`
2. Decorator is applied: `@limiter.limit(...)`
3. Request parameter is present: `async def endpoint(request: Request)`

### Issue: Too strict limits

**Solution:** Adjust `RATE_LIMITS` dictionary in `backend/rate_limit.py`:

```python
RATE_LIMITS = {
    "public": "50/minute",  # Increased from 10/minute
    ...
}
```

## Security Considerations

1. **IP-based limiting:** Current implementation uses client IP. Behind a proxy, you may need to adjust:
   ```python
   # Modify if behind reverse proxy
   limiter = Limiter(key_func=lambda r: r.headers.get("X-Forwarded-For"))
   ```

2. **Distributed systems:** For multiple servers, consider using Redis for shared state:
   ```python
   limiter = Limiter(
       key_func=get_remote_address,
       storage_uri="redis://localhost"
   )
   ```

3. **Whitelist trusted IPs:** For internal services:
   ```python
   @limiter.limit("1000/minute", key_func=lambda r: r.headers.get("X-API-Key"))
   ```

## Next Steps

1. Apply rate limiting to all public endpoints in `backend/routes/`
2. Test with curl or Postman
3. Monitor rate limit hits in logs
4. Adjust limits based on actual usage patterns

## References

- [slowapi Documentation](https://github.com/laurentS/slowapi)
- [HTTP 429 Status Code](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429)
- [Rate Limiting Best Practices](https://cloud.google.com/architecture/rate-limiting-strategies-techniques)
