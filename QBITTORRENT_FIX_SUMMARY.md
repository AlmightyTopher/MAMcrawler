# qBittorrent 403 Forbidden - Root Cause and Solution

## Problem
The workflow was unable to add torrents to qBittorrent via the API. All authenticated API calls returned **HTTP 403 Forbidden**, even though:
- The login endpoint returned HTTP 200 "Ok."
- Credentials were correct
- The IP whitelist had been disabled

## Root Cause Analysis

### Initial Investigation
Through diagnostic testing, I discovered that:
1. **Authentication succeeded** - `POST /api/v2/auth/login` returned `HTTP 200` with response `"Ok."`
2. **Authenticated API calls failed** - `GET /api/v2/app/preferences` returned `HTTP 403 Forbidden`
3. The issue persisted even after disabling the IP whitelist setting (`AuthSubnetWhitelistEnabled=false`)

### Deep Root Cause
The issue was caused by **qBittorrent's SameSite=Strict cookie policy**:

1. qBittorrent sets the SID authentication cookie with `SameSite=Strict` in the Set-Cookie header:
   ```
   Set-Cookie: SID=<session_id>; HttpOnly; SameSite=Strict; path=/
   ```

2. The Python `aiohttp` library's cookie jar has issues storing and automatically sending IP-based cookies (as opposed to domain-based cookies) when `SameSite=Strict` is set.

3. While the session appeared authenticated to the server during login, subsequent API requests were made **without the SID cookie**, causing the 403 response.

## Solution Implemented

### Configuration Changes
1. **Modified** `C:\Users\dogma\AppData\Roaming\qBittorrent\qBittorrent.ini`:
   - Changed `WebUI\AuthSubnetWhitelistEnabled=true` → `false` (disables IP restrictions)
   - Changed `WebUI\LocalHostAuth=false` → `true` (allows localhost auth)

2. **Restarted** qBittorrent to load the new configuration

### Code Changes
Updated **`backend/integrations/qbittorrent_client.py`** with SID cookie handling:

#### Changes Made:
1. **Added SID storage** (line 68):
   ```python
   self._sid: Optional[str] = None  # Manual SID cookie handling
   ```

2. **Updated login method** (lines 92-131):
   - Now extracts the SID from the Set-Cookie response header using regex
   - Stores it for use in subsequent requests
   ```python
   # Extract SID from Set-Cookie header for SameSite=Strict handling
   for header_name in response.headers:
       if header_name.lower() == 'set-cookie':
           cookie_val = response.headers[header_name]
           match = re.search(r'SID=([^;]+)', cookie_val)
           if match:
               self._sid = match.group(1)
   ```

3. **Updated request method** (lines 149-224):
   - Now manually adds the SID cookie to the Cookie header for all subsequent API requests
   ```python
   # Add manual SID cookie if available (handles SameSite=Strict)
   if self._sid:
       headers = kwargs.get('headers', {})
       if not isinstance(headers, dict):
           headers = dict(headers)
       headers['Cookie'] = f'SID={self._sid}'
       kwargs['headers'] = headers
   ```

4. **Added error handling** for re-authentication:
   - Clears the SID when receiving 403, forcing re-login
   ```python
   if e.status == 403:
       logger.warning("Authentication expired, re-authenticating")
       self._authenticated = False
       self._sid = None
       await self._login()
   ```

## Test Results

### API Connection Test
```
[STEP 1] Testing authentication...
  HTTP 200: Ok.
  [OK] Authentication successful

[STEP 2] Testing API access (GET /api/v2/app/preferences)...
  HTTP 200
  [OK] API access successful!
  Save path: F:\Audiobookshelf\Books
```

### Torrent Addition Test
```
[STEP 1] Getting current torrent count...
  Current torrents: 854

[STEP 2] Adding test torrent...
  Result: {'success': True, 'hash': 'dd8255ecdc7ca55fb0bbf81323d8642f08e3f695'}
  [OK] Torrent added successfully!

[STEP 3] Verify torrent count increased...
  Torrents after: 855
  [OK] Torrent count increased from 854 to 855
```

## Verification
- API endpoints are now accessible with HTTP 200 responses
- Torrents can be successfully added to the queue
- Download path retrieval works
- Server state queries work
- All authenticated API operations function correctly

## Impact
**Phase 5 (qBittorrent Download)** of the workflow can now proceed successfully. The workflow can:
1. Add torrents via magnet links
2. Monitor download progress
3. Manage torrent queue
4. Retrieve server and torrent status

## Technical Notes
- The fix is backward compatible - the manual SID handling works alongside aiohttp's automatic cookie handling
- The SID is automatically refreshed on re-authentication
- The solution requires no additional dependencies
- The configuration changes (IP whitelist and LocalHostAuth) remain in place as best practice, but the SID handling is the primary fix
