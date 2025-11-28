# qBittorrent Client Code Changes - Reference Guide

## Overview
This document provides exact code changes made to fix the HTTP 403 authentication issue in `backend/integrations/qbittorrent_client.py`.

## File Location
```
backend/integrations/qbittorrent_client.py
```

## Change 1: Add Import for Regex

**Location**: Line 12 (imports section)

**Added**:
```python
import re
```

**Full import section after change**:
```python
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import asyncio
import re
from urllib.parse import urljoin

import aiohttp
from aiohttp import ClientTimeout, ClientError, FormData
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
```

## Change 2: Add SID Storage to __init__

**Location**: Line 68 (in `__init__` method)

**Added**:
```python
self._sid: Optional[str] = None  # Manual SID cookie handling
```

**Context (full __init__)**:
```python
def __init__(
    self,
    base_url: str,
    username: str,
    password: str,
    timeout: int = 30,
):
    self.base_url = base_url.rstrip("/")
    self.username = username
    self.password = password
    self.timeout = ClientTimeout(total=timeout)
    self.session: Optional[aiohttp.ClientSession] = None
    self._authenticated = False
    self._sid: Optional[str] = None  # Manual SID cookie handling  <-- NEW LINE

    logger.info(f"Initialized QBittorrentClient for {self.base_url}")
```

## Change 3: Update _login Method

**Location**: Lines 92-131

**Replaced entire method**:

### BEFORE:
```python
async def _login(self):
    """
    Authenticate with qBittorrent Web UI.

    Raises:
        QBittorrentAuthError: If authentication fails
    """
    logger.info("Authenticating with qBittorrent")
    url = urljoin(self.base_url, "/api/v2/auth/login")

    data = FormData()
    data.add_field("username", self.username)
    data.add_field("password", self.password)

    try:
        async with self.session.post(url, data=data) as response:
            response.raise_for_status()
            result = await response.text()

            if result.strip() == "Ok.":
                self._authenticated = True
                logger.info("Successfully authenticated with qBittorrent")
            else:
                raise QBittorrentAuthError(f"Authentication failed: {result}")

    except aiohttp.ClientError as e:
        logger.error(f"Authentication request failed: {str(e)}")
        raise QBittorrentAuthError(f"Login request failed: {str(e)}")
```

### AFTER:
```python
async def _login(self):
    """
    Authenticate with qBittorrent Web UI.

    Handles SameSite=Strict cookies by manually extracting and storing the SID.

    Raises:
        QBittorrentAuthError: If authentication fails
    """
    logger.info("Authenticating with qBittorrent")
    url = urljoin(self.base_url, "/api/v2/auth/login")

    data = FormData()
    data.add_field("username", self.username)
    data.add_field("password", self.password)

    try:
        async with self.session.post(url, data=data) as response:
            response.raise_for_status()
            result = await response.text()

            if result.strip() == "Ok.":
                # Extract SID from Set-Cookie header for SameSite=Strict handling
                for header_name in response.headers:
                    if header_name.lower() == 'set-cookie':
                        cookie_val = response.headers[header_name]
                        match = re.search(r'SID=([^;]+)', cookie_val)
                        if match:
                            self._sid = match.group(1)
                            logger.debug(f"Extracted SID for manual cookie handling")
                            break

                self._authenticated = True
                logger.info("Successfully authenticated with qBittorrent")
            else:
                raise QBittorrentAuthError(f"Authentication failed: {result}")

    except aiohttp.ClientError as e:
        logger.error(f"Authentication request failed: {str(e)}")
        raise QBittorrentAuthError(f"Login request failed: {str(e)}")
```

**Key changes**:
- Added docstring mention of SameSite=Strict handling
- Extract SID from Set-Cookie header using regex pattern `r'SID=([^;]+)'`
- Loop through response headers looking for 'set-cookie'
- Store extracted SID in `self._sid`

## Change 4: Update _request Method

**Location**: Lines 149-224

**Key changes to _request method**:

### Add Cookie Header (after `logger.debug(f"{method} {url}")` line):
```python
# Add manual SID cookie if available (handles SameSite=Strict)
if self._sid:
    headers = kwargs.get('headers', {})
    if not isinstance(headers, dict):
        headers = dict(headers)
    headers['Cookie'] = f'SID={self._sid}'
    kwargs['headers'] = headers
```

### Update docstring:
Change from:
```python
"""
Make HTTP request with retry logic.
...
"""
```

To:
```python
"""
Make HTTP request with retry logic.

Includes SID cookie for proper authentication with qBittorrent's
SameSite=Strict cookie policy.
...
"""
```

### Update 403 error handling:
In the exception handler for `aiohttp.ClientResponseError`:

Change from:
```python
if e.status == 403:
    logger.warning("Authentication expired, re-authenticating")
    self._authenticated = False
    await self._login()
    # Retry the request after re-authentication
    return await self._request(method, endpoint, **kwargs)
```

To:
```python
if e.status == 403:
    logger.warning("Authentication expired, re-authenticating")
    self._authenticated = False
    self._sid = None  # Clear old SID
    await self._login()
    # Retry the request after re-authentication
    return await self._request(method, endpoint, **kwargs)
```

## Configuration Changes

**File**: `C:\Users\dogma\AppData\Roaming\qBittorrent\qBittorrent.ini`

### Change 1: Disable IP Whitelist
**Line 76**:
```ini
# BEFORE:
WebUI\AuthSubnetWhitelistEnabled=true

# AFTER:
WebUI\AuthSubnetWhitelistEnabled=false
```

### Change 2: Enable Localhost Authentication
**Line 89**:
```ini
# BEFORE:
WebUI\LocalHostAuth=false

# AFTER:
WebUI\LocalHostAuth=true
```

## Summary of All Changes

### Code Changes (1 file)
- **File**: `backend/integrations/qbittorrent_client.py`
- **Lines Changed**: 5 (1 import + 1 variable + 1 method + 1 docstring + 1 error handler)
- **Total Code Added**: ~30 lines (including comments)
- **Dependencies Added**: None (using standard `re` module)

### Configuration Changes (1 file)
- **File**: `C:\Users\dogma\AppData\Roaming\qBittorrent\qBittorrent.ini`
- **Settings Changed**: 2
- **Lines Modified**: 2

## Testing Verification

### Test 1: Authentication
```
Expected: HTTP 200, response "Ok."
Actual: HTTP 200, response "Ok." ✓
SID Extracted: Yes ✓
```

### Test 2: API Access
```
Expected: HTTP 200, JSON response
Actual: HTTP 200, preferences retrieved ✓
```

### Test 3: Torrent Addition
```
Expected: Torrent added to queue
Actual: Torrent count 854 → 855 ✓
```

## Integration Notes

- Changes are backward compatible
- No changes to method signatures
- No changes to public API
- Existing code using QBittorrentClient needs no modifications
- Error handling maintains existing retry logic

## Rollback Instructions

If needed to revert:

1. **Code Changes**: Remove the 4 code changes from `qbittorrent_client.py` (undo each step above)
2. **Config Changes**: Revert INI file settings to original values
3. **No data loss**: No data files are created or modified

## Performance Impact

- **Minimal**: Single regex operation per login
- **Negligible**: Additional header assignment per request (< 1ms)
- **No additional API calls**: Only manual header injection

## Security Considerations

- SID is extracted from the server's own Set-Cookie header (no external dependency)
- SID is handled only in memory (not persisted)
- SID is cleared on authentication failure
- No additional credentials exposed
- Maintains existing security practices
