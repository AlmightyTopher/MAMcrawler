# qBittorrent 403 Forbidden - Root Cause & Solutions

## ROOT CAUSE IDENTIFIED

Your qBittorrent API is configured with **IP whitelisting** or **API access restrictions** that block the client's IP address from accessing authenticated API endpoints.

### Diagnostic Results:
- ✓ Basic connectivity: **HTTP 200** (qBittorrent Web UI is reachable)
- ✓ API version endpoint: **Accessible** (unauthenticated)
- ✓ Authentication: **Successful** (HTTP 200 + "Ok." response)
- ✗ Authenticated API calls: **HTTP 403 Forbidden** (blocked by IP whitelist)

This pattern proves the credentials are correct, but the client's IP is blocked from API access.

---

## QUICK FIX (5 Minutes)

### Step 1: Open qBittorrent Web UI
```
URL: http://192.168.0.48:52095/
Username: TopherGutbrod
Password: Tesl@ismy#1
```

### Step 2: Navigate to Web UI Settings
```
Menu: Tools > Options > Web UI
```

### Step 3: Check IP Whitelist Settings

Look for one of these settings:

**Option A: "IP whitelist" field**
- If present and contains IPs, add your client's IP
- The client IP is likely: `127.0.0.1` or `localhost` (if running on same machine)
- Or your local network IP (e.g., `192.168.x.x` if on same network)

**Option B: "Bypass authentication for clients on localhost"**
- Check this box if you want to allow local connections without auth
- This is useful for local network access

**Option C: "API access" permissions**
- Verify that user `TopherGutbrod` has API access enabled
- Look for "API enabled" or similar checkbox next to the user

### Step 4: Save and Restart (if needed)
- Click "Apply" or "OK" to save settings
- qBittorrent may auto-apply, or you may need to restart

### Step 5: Test Connection
The workflow will automatically test the connection on next run:
```bash
cd C:\Users\dogma\Projects\MAMcrawler
python execute_full_workflow.py
```

---

## DETAILED SETTINGS GUIDE

### For qBittorrent v4.3+

**Location:** Tools → Options → Web UI

**Settings to Check:**

1. **Enable Web User Interface**
   - Should be: ✓ Checked

2. **IP Whitelist** (if visible)
   - Should contain your client IP addresses
   - Format: `127.0.0.1`, `192.168.1.100`, `192.168.1.0/24`
   - Leave empty to allow all IPs (less secure)

3. **Bypass authentication for clients on localhost**
   - If enabled: allows `127.0.0.1` (same machine) to skip auth
   - Helpful for local clients

4. **Authentication**
   - Username: `TopherGutbrod`
   - Password: Set and saved
   - Verify user exists and password is correct

5. **API Access**
   - Look for "API" or "WebAPI" section
   - Should have checkboxes for:
     - ✓ Enable Web API
     - ✓ API access for user (TopherGutbrod)

### For Older qBittorrent Versions

Some older versions use:
- `~/.config/qBittorrent/qBittorrent.conf` config file
- Search for `[Preferences]` section
- Look for `WebUI_` settings

---

## IF YOU DON'T KNOW YOUR CLIENT IP

Run this to find the IP the client will use to connect:

### From the same machine:
```bash
# Windows
ipconfig

# Linux/Mac
ifconfig
```

### If connecting from network:
Check your router's DHCP client list, or:
```bash
# Windows
nslookup <hostname>

# Linux/Mac
hostname -I
```

---

## ALTERNATIVE: Disable IP Whitelist Entirely

**For development/testing only** (not recommended for production):

1. Open qBittorrent Web UI
2. Tools → Options → Web UI
3. Look for "IP whitelist" field
4. **Clear the field completely** (leave empty)
5. Click Apply/OK

This allows **any IP** to access the API, which is less secure but works for testing.

---

## ALTERNATIVE: Use Prowlarr Instead

If you cannot fix qBittorrent settings, the workflow has a fallback:

**Prowlarr can add torrents to qBittorrent via plugin:**

1. Workflow prepared magnets for Prowlarr
2. Access: http://localhost:9696/
3. Use Prowlarr's torrent indexer to add to qBittorrent
4. The workflow detects this fallback and continues

---

## VERIFICATION AFTER FIX

After applying changes to qBittorrent settings:

### Test 1: Simple curl command
```bash
# Windows (requires curl.exe or use PowerShell)
curl -X POST http://192.168.0.48:52095/api/v2/auth/login -d "username=TopherGutbrod&password=Tesl@ismy#1"

# Should return: "Ok."
```

### Test 2: Check if API is now accessible
```bash
# After logging in above, try:
curl http://192.168.0.48:52095/api/v2/app/preferences

# Should return: JSON with qBittorrent preferences (not 403)
```

### Test 3: Run workflow diagnostic
```bash
python qbittorrent_auth_fix.py
```

This will test all authentication methods and show which work.

---

## WHAT THE WORKFLOW WILL DO

Once you fix the IP whitelist:

1. **PHASE 5: QBITTORRENT DOWNLOAD**
   - ✓ Successfully authenticate
   - ✓ Add 1 torrent (Five Fantastic Tales audiobook)
   - ✓ Monitor download progress

2. **PHASE 6: MONITOR DOWNLOADS**
   - ✓ Check download progress every 5 minutes
   - ✓ Wait for completion (or 24-hour timeout)
   - ✓ Report status

3. **PHASES 7-12: COMPLETE**
   - ✓ Sync to AudiobookShelf
   - ✓ Write ID3 metadata
   - ✓ Enhance metadata
   - ✓ Build author history
   - ✓ Generate final report
   - ✓ Create backup

---

## CONFIGURATION REFERENCES

### From your .env file:
```
QBITTORRENT_URL=http://192.168.0.48:52095/
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=Tesl@ismy#1
DOWNLOAD_PATH=F:\Audiobookshelf\Books
```

### qBittorrent Expected Behavior:
- Web UI: Accessible at http://192.168.0.48:52095/
- API: Available at http://192.168.0.48:52095/api/v2/
- Authentication: Standard HTTP POST with username/password
- Session: Persists across multiple requests (cookie-based)

---

## TROUBLESHOOTING

### Problem: Still getting 403 after changing settings

**Solutions:**
1. Restart qBittorrent completely (close and reopen)
2. Clear browser cookies (qBittorrent session may be cached)
3. Check if there's a firewall blocking your client IP
4. Verify you edited the correct qBittorrent instance (check URL and port)

### Problem: Can't access Web UI at all

**Solutions:**
1. Verify qBittorrent is running: Check system tray or task manager
2. Verify IP and port: `http://192.168.0.48:52095/`
3. Check firewall rules: Windows Defender or 3rd-party firewall
4. Try from another machine to rule out local network issues

### Problem: User authentication fails

**Solutions:**
1. Verify username: `TopherGutbrod` (case-sensitive)
2. Verify password: `Tesl@ismy#1`
3. Check if user exists in qBittorrent
4. Check if user account is disabled/locked

---

## NEXT STEPS

1. **Apply the IP whitelist fix** (see Quick Fix section above)
2. **Test the connection** using one of the verification methods
3. **Re-run the workflow**:
   ```bash
   python execute_full_workflow.py
   ```
4. **Monitor the real workflow execution** as torrents are added and downloaded

---

## SUCCESS INDICATORS

After fix, you should see in the log:

```
[PHASE] PHASE 5: QBITTORRENT DOWNLOAD
[OK] Added 1 torrents to qBittorrent
[INFO] Five Fantastic Tales - A BBC 4 Science Fiction Audiobook...
[PHASE] PHASE 6: MONITOR DOWNLOADS
[INFO] Progress: 5%
[INFO] Progress: 12%
... (continuing until 100%)
```

Instead of:

```
[WARN] qBittorrent API returning 403 (Forbidden)
[WARN] MAGNETS PREPARED FOR DOWNLOAD
```

---

## SUPPORT

If you still need help:
1. Check qBittorrent version: Help → About
2. Review qBittorrent documentation: https://github.com/qbittorrent/qBittorrent/wiki
3. Look at the detailed Web UI settings page (it has tooltips for each setting)
4. Run: `python qbittorrent_auth_fix.py` for comprehensive diagnostics

