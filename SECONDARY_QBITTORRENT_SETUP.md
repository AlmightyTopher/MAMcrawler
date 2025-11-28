# Secondary qBittorrent Instance Setup Guide

## Table of Contents
- [Overview](#overview)
- [Installation & Configuration](#installation--configuration)
- [Verification & Testing](#verification--testing)
- [Configuration Details](#configuration-details)
- [Common Issues & Solutions](#common-issues--solutions)
- [Running Both Instances Together](#running-both-instances-together)
- [Integration with Workflow](#integration-with-workflow)
- [Monitoring](#monitoring)
- [Stopping Secondary Instance](#stopping-secondary-instance)
- [Production Checklist](#production-checklist)

---

## Overview

### What is the Secondary Instance?

The secondary qBittorrent instance is a **local fallback** that runs on your Windows machine when the primary VPN-connected instance becomes unavailable. This provides zero-downtime resilience for your audiobook download workflow.

### Key Differences

| Aspect | Primary Instance | Secondary Instance |
|--------|------------------|-------------------|
| **Location** | Remote server (192.168.0.48) | Local machine (localhost) |
| **URL** | http://192.168.0.48:52095/ | http://localhost:52095/ |
| **Network** | Via VPN (ProtonVPN) | Direct local connection |
| **Port** | 52095 (WebUI) | 52095 (WebUI) - SAME PORT |
| **BitTorrent Ports** | 6881-6900 | 6881-6920 (different range) |
| **Downloads** | F:\Audiobookshelf\Books\ | C:\qbittorrent_secondary\downloads\ |
| **Profile** | Default AppData location | C:\qbittorrent_secondary\profile\ |
| **Database** | Remote server's database | Separate local database |

### When is Secondary Used?

The ResilientQBittorrentClient automatically switches to secondary when:
- **VPN disconnects** (gateway 192.168.0.1 unreachable)
- **Primary returns HTTP 404** (VPN routing issue)
- **Primary times out** (network latency > 10s)
- **Primary authentication fails** (after retries)

### How It Works

1. **Health Check**: Before adding magnets, client checks VPN connectivity
2. **Primary First**: Attempts primary instance (192.168.0.48:52095)
3. **Automatic Failover**: If primary fails, switches to secondary (localhost:52095)
4. **Queue Fallback**: If both fail, magnets saved to `qbittorrent_queue.json`
5. **Recovery**: When services restore, queued magnets auto-processed

### Port Configuration Strategy

**Why both use port 52095?**

- Primary runs on **192.168.0.48:52095** (remote machine via VPN)
- Secondary runs on **localhost:52095** (this machine)
- Same port number but **different IP addresses** = no conflict
- Fallback logic knows to switch from remote IP to localhost
- Consistent configuration simplifies environment variables

**BitTorrent ports are DIFFERENT:**
- Primary: 6881-6900 (remote server's config)
- Secondary: 6881-6920 (this guide configures different range)
- Prevents port conflicts if both running simultaneously

---

## Installation & Configuration

### Prerequisites

- Windows 10 or Windows 11
- Administrator access
- qBittorrent already installed at `C:\Program Files (x86)\qBittorrent\qbittorrent.exe`
- Primary qBittorrent credentials (username/password from `.env`)

### Step 1: Create Separate Profile Directory

**Why?** Running two qBittorrent instances from the same profile causes:
- Database lock conflicts (BEP.sqlite, torrents.db)
- Configuration overwrites
- Session file corruption
- WebUI port binding errors

**Solution:** Create a dedicated profile directory for secondary instance.

**Commands:**

```powershell
# Open PowerShell as Administrator
# Create directory structure
New-Item -Path "C:\qbittorrent_secondary" -ItemType Directory -Force
New-Item -Path "C:\qbittorrent_secondary\profile" -ItemType Directory -Force
New-Item -Path "C:\qbittorrent_secondary\downloads" -ItemType Directory -Force
New-Item -Path "C:\qbittorrent_secondary\downloads\.incomplete" -ItemType Directory -Force
```

**Verify:**

```powershell
Get-ChildItem "C:\qbittorrent_secondary" -Recurse
```

**Expected Output:**
```
    Directory: C:\qbittorrent_secondary

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        11/28/2025   2:30 PM                downloads
d-----        11/28/2025   2:30 PM                profile
```

---

### Step 2: Create Configuration File

**Location:** `C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf`

**IMPORTANT:** You must create the parent directory first!

```powershell
# Create qBittorrent config directory
New-Item -Path "C:\qbittorrent_secondary\profile\qBittorrent" -ItemType Directory -Force
```

**Copy Template Configuration:**

The project includes a template at `qbittorrent_secondary_config.ini`. Copy this to the profile directory:

```powershell
# Navigate to project directory
cd C:\Users\dogma\Projects\MAMcrawler

# Copy template to secondary profile (rename .ini to .conf)
Copy-Item "qbittorrent_secondary_config.ini" -Destination "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf"
```

**Critical Settings to Modify:**

Open `C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf` in Notepad and verify/modify:

```ini
[Preferences]
# Web UI - SAME PORT as primary (different IP)
WebUI\Port=52095
WebUI\Address=127.0.0.1
WebUI\Username=TopherGutbrod

# Downloads - DIFFERENT from primary
Downloads\SavePath=C:\\qbittorrent_secondary\\downloads
Downloads\TempPath=C:\\qbittorrent_secondary\\downloads\\.incomplete

# BitTorrent Ports - DIFFERENT range from primary
Connection\PortRangeMin=6881
# If primary uses 6881-6900, use 6901-6920 here
# Or use full range 6881-6920 (overlaps but shouldn't conflict)

# Logging
Logging\Path=C:\\qbittorrent_secondary\\profile\\qBittorrent\\logs
Logging\SavePath=C:\\qbittorrent_secondary\\profile\\qBittorrent\\logs
```

**Password Configuration:**

The password **cannot** be set via config file (security). You'll set it after first launch (Step 3).

---

### Step 3: Create Batch File for Easy Startup

**Purpose:** Makes starting secondary instance as easy as double-clicking a file.

**Location:** `C:\qbittorrent_secondary\start_secondary.bat`

**Create the file:**

```powershell
# Create batch file
@"
@echo off
echo ================================================
echo Starting qBittorrent Secondary Instance
echo ================================================
echo.
echo WebUI will be available at: http://localhost:52095
echo Profile: C:\qbittorrent_secondary\profile
echo Downloads: C:\qbittorrent_secondary\downloads
echo.
echo Press Ctrl+C to stop the secondary instance
echo ================================================
echo.

REM Set profile path via environment variable
set APPDATA=C:\qbittorrent_secondary\profile

REM Launch qBittorrent with profile override
"C:\Program Files (x86)\qBittorrent\qbittorrent.exe" --webui-port=52095 --profile=C:\qbittorrent_secondary\profile

pause
"@ | Out-File -FilePath "C:\qbittorrent_secondary\start_secondary.bat" -Encoding ASCII
```

**Test the batch file:**

```powershell
# Run batch file
C:\qbittorrent_secondary\start_secondary.bat
```

**What should happen:**
- Console window opens with status messages
- qBittorrent tray icon appears (secondary instance)
- Wait 5 seconds for startup
- Open browser: http://localhost:52095
- Login page should appear

**If it doesn't start:**
- Check Task Manager for `qbittorrent.exe` processes
- Check Windows Event Viewer for errors
- Verify installation path matches batch file

---

### Step 4: Set WebUI Password on First Launch

**Why:** Password hash can't be pre-configured (security).

**Steps:**

1. **Start secondary instance** via batch file (Step 3)
2. **Open browser** to http://localhost:52095
3. **Default credentials** (first launch only):
   - Username: `admin`
   - Password: `adminadmin`
4. **Immediately change password**:
   - Tools → Options → Web UI
   - Change "Username" to: `TopherGutbrod` (match primary)
   - Change "Password" to: **same as primary** (from `.env`)
   - Click "Save"
5. **Verify** by logging out and back in with new credentials

**CRITICAL:** Username and password **must match primary** for `ResilientQBittorrentClient` to authenticate.

**After password set:**
- Password hash is saved to `qBittorrent.conf` automatically
- File will contain line like: `WebUI\Password_PBKDF2="@ByteArray(...)"`
- Do NOT edit this line manually

---

### Step 5: Create Windows Shortcut for Quick Access

**Purpose:** One-click startup from Desktop.

**Steps:**

1. Right-click Desktop → New → Shortcut
2. **Target:** `C:\qbittorrent_secondary\start_secondary.bat`
3. **Name:** `qBittorrent Secondary`
4. Click "Finish"
5. **Optional:** Right-click shortcut → Properties → Change Icon
   - Browse to: `C:\Program Files (x86)\qBittorrent\qbittorrent.exe`
   - Select qBittorrent icon

**Advanced:** Run as Administrator (if needed)
1. Right-click shortcut → Properties
2. Advanced → Check "Run as administrator"
3. Apply

---

### Step 6: Configure Firewall (Usually Not Needed)

**Windows Firewall automatically allows localhost traffic**, so this step is typically unnecessary.

**Only if you encounter firewall blocks:**

```powershell
# Allow qBittorrent through firewall (if needed)
New-NetFirewallRule -DisplayName "qBittorrent Secondary WebUI" -Direction Inbound -Protocol TCP -LocalPort 52095 -Action Allow

# Allow BitTorrent traffic (if needed)
New-NetFirewallRule -DisplayName "qBittorrent Secondary BitTorrent" -Direction Inbound -Protocol TCP -LocalPort 6881-6920 -Action Allow
New-NetFirewallRule -DisplayName "qBittorrent Secondary BitTorrent UDP" -Direction Inbound -Protocol UDP -LocalPort 6881-6920 -Action Allow
```

**Check existing rules:**

```powershell
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*qBittorrent*"}
```

---

## Verification & Testing

### Verification 1: Configuration File Created

```powershell
Get-Item "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf"
```

**Expected:**
```
    Directory: C:\qbittorrent_secondary\profile\qBittorrent

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----        11/28/2025   3:15 PM          12345 qBittorrent.conf
```

---

### Verification 2: Directory Structure

```powershell
Get-ChildItem "C:\qbittorrent_secondary" -Recurse -Directory
```

**Expected Output:**
```
    Directory: C:\qbittorrent_secondary

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        11/28/2025   2:30 PM                downloads
d-----        11/28/2025   2:30 PM                profile

    Directory: C:\qbittorrent_secondary\downloads

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        11/28/2025   2:30 PM                .incomplete

    Directory: C:\qbittorrent_secondary\profile

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
d-----        11/28/2025   2:30 PM                qBittorrent
```

---

### Verification 3: Start Secondary Instance

```powershell
# Run batch file
C:\qbittorrent_secondary\start_secondary.bat
```

**Wait 5 seconds**, then open browser to: http://localhost:52095

**Expected:**
- qBittorrent Web UI login page
- No error messages in console window
- Tray icon shows qBittorrent running

**If you see errors:**
- "Port already in use" → Another instance already running on 52095 (see troubleshooting)
- "Permission denied" → Run batch file as Administrator
- "File not found" → Verify installation path in batch file

---

### Verification 4: Verify Port Binding

**Check which processes are using port 52095:**

```powershell
netstat -ano | findstr 52095
```

**Expected Output (if both instances running):**
```
  TCP    192.168.0.48:52095     0.0.0.0:0              LISTENING       1234
  TCP    127.0.0.1:52095        0.0.0.0:0              LISTENING       5678
```

**Interpretation:**
- First line: Primary instance (remote IP via port proxy)
- Second line: Secondary instance (localhost)
- Different PIDs (1234 vs 5678) = separate processes
- Different IPs = no conflict

**If you only see one line:**
- Only primary OR secondary running (expected if not testing simultaneously)

---

### Verification 5: Add Test Magnet

**Purpose:** Verify secondary can download independently.

**Test Magnet (Ubuntu ISO - legal and fast):**
```
magnet:?xt=urn:btih:e83a2b5c1c5b6b3a8c4c9b1c5b5c6b3a8c4c9b1c&dn=ubuntu-20.04.1-desktop-amd64.iso&tr=http://torrent.ubuntu.com:6969/announce
```

**Steps:**

1. **Open secondary WebUI:** http://localhost:52095
2. **Login** with your credentials (TopherGutbrod / your-password)
3. **Add magnet:**
   - Click "Add Torrent" button (+ icon)
   - Paste magnet link
   - **Verify category:** "audiobooks" (if available)
   - **Verify save path:** `C:\qbittorrent_secondary\downloads\`
   - Click "Download"
4. **Verify torrent appears** in torrent list
5. **Check download started** (status shows "downloading" or "metadata")

**Verify isolation:**

```powershell
# Check secondary download folder
Get-ChildItem "C:\qbittorrent_secondary\downloads"
```

**Expected:** Test torrent file or folder appears

**Verify primary NOT affected:**
- Open primary WebUI: http://192.168.0.48:52095 (if VPN connected)
- Test torrent should NOT appear in primary's list

**Clean up test:**
- Right-click test torrent → Delete → Delete files from disk

---

### Verification 6: Verify Separate Downloads

**Primary downloads location:** `F:\Audiobookshelf\Books\`

**Secondary downloads location:** `C:\qbittorrent_secondary\downloads\`

**Verify separation:**

```powershell
# Check secondary location
Get-ChildItem "C:\qbittorrent_secondary\downloads"

# Check primary location (should be empty of secondary's files)
Get-ChildItem "F:\Audiobookshelf\Books"
```

**Expected:**
- Secondary's downloads in `C:\qbittorrent_secondary\downloads\`
- Primary's downloads in `F:\Audiobookshelf\Books\`
- NO overlap between the two

**Why this matters:**
- Prevents file conflicts
- Easier to track which instance downloaded what
- Allows independent quota management

---

## Configuration Details

### Why Separate Ports for BitTorrent?

**WebUI Port (52095):**
- Same for both instances (different IPs)
- Simplifies failover logic
- No environment variable changes needed

**BitTorrent Listening Ports:**
- Primary: 6881-6900 (typical default)
- Secondary: 6881-6920 (wider range or offset)
- **Must be different** to avoid binding conflicts if both running

**What happens if BitTorrent ports conflict?**
- Second instance fails to bind
- Error: "Port already in use"
- Instance won't accept incoming connections
- Downloads still work (outgoing only) but slower

---

### Why Separate Profiles?

qBittorrent stores session data in profile directory:

**Database files:**
- `BEP.sqlite` - Peer exchange database
- `torrents.db` - Torrent metadata
- `resume/` - Resume data for active torrents

**Lock files:**
- `.lock` - Prevents multiple instances from same profile

**Configuration:**
- `qBittorrent.conf` - All settings
- `categories.json` - Category definitions

**If two instances share profile:**
- Database locks → crashes
- Configuration overwrites → lost settings
- Resume data conflicts → corrupted torrents
- Unpredictable behavior

**Separate profiles = complete isolation**

---

### Why Same WebUI Port?

**Scenario:** VPN drops, primary becomes unreachable.

**Failover logic in `ResilientQBittorrentClient`:**

```python
# Primary URL from .env
primary_url = "http://192.168.0.48:52095/"  # Remote via VPN

# Secondary URL from .env
secondary_url = "http://localhost:52095/"   # Local machine
```

**If secondary used different port (e.g., 52096):**
- Would need separate environment variable
- Failover logic would need to track different port numbers
- More configuration complexity

**Same port, different IP = simpler:**
- Only IP changes (192.168.0.48 → localhost)
- Port stays consistent (52095)
- Less configuration to maintain

---

### Why Different Download Paths?

**Primary:** `F:\Audiobookshelf\Books\` (production library)

**Secondary:** `C:\qbittorrent_secondary\downloads\` (temporary location)

**Reasons:**

1. **File Conflicts:** Same filename downloaded by both = overwrite
2. **Tracking:** Know which instance downloaded what
3. **Temporary vs Production:**
   - Secondary is emergency fallback
   - Downloads may need manual review before moving to production
4. **Disk Space:** Secondary uses system drive (usually smaller)

**Workflow when secondary used:**
1. Secondary downloads to `C:\qbittorrent_secondary\downloads\`
2. Verify download completed successfully
3. Manually move to `F:\Audiobookshelf\Books\` (if needed)
4. Or configure Audiobookshelf to scan both locations

---

### What Happens if You Misconfigure?

**Scenario 1: Both instances use same profile**

```
Error: "Application failed to start: database is locked"
```

**Cause:** Second instance can't access database (first instance holds lock)

**Fix:** Use separate profile directories (this guide's approach)

---

**Scenario 2: Both instances use same WebUI port AND same IP**

```
Error: "Failed to bind to port 52095: Address already in use"
```

**Cause:** Can't bind two processes to same IP:port combination

**Fix:** Use different IPs (localhost vs 192.168.0.48) - this guide's approach

---

**Scenario 3: Both instances use same download path**

**Symptoms:**
- Files overwrite each other
- Can't tell which instance downloaded what
- Disk quota confusion

**Fix:** Use separate download paths (this guide's approach)

---

## Common Issues & Solutions

### Issue 1: "Address already in use" error

**Error Message:**
```
Failed to bind to port 52095: Address already in use
```

**Cause:** Another process is already using port 52095 on localhost.

**Solution 1: Check if primary is already running on localhost**

```powershell
netstat -ano | findstr 52095
```

If you see:
```
TCP    127.0.0.1:52095     LISTENING     1234
```

**Kill the process:**

```powershell
# Get process details
Get-Process | Where-Object {$_.Id -eq 1234}

# Kill it
Stop-Process -Id 1234 -Force
```

**Solution 2: Check for port proxy redirect**

```powershell
netsh interface portproxy show all
```

If you see port 52095 redirecting from localhost to remote IP, this is fine (expected).

**Solution 3: Use different port temporarily**

Edit `C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf`:

```ini
WebUI\Port=52096  # Different port
```

Update batch file:

```batch
"C:\Program Files (x86)\qBittorrent\qbittorrent.exe" --webui-port=52096 --profile=C:\qbittorrent_secondary\profile
```

Update `.env`:

```ini
QBITTORRENT_SECONDARY_URL=http://localhost:52096/
```

---

### Issue 2: "Permission denied" on C:\qbittorrent_secondary

**Error Message:**
```
Access to the path 'C:\qbittorrent_secondary' is denied.
```

**Cause:** Insufficient permissions to create or write to directory.

**Solution 1: Run batch file as Administrator**

1. Right-click `start_secondary.bat`
2. Select "Run as administrator"
3. Accept UAC prompt

**Solution 2: Fix folder permissions**

```powershell
# Take ownership of folder
takeown /f "C:\qbittorrent_secondary" /r /d y

# Grant yourself full control
icacls "C:\qbittorrent_secondary" /grant "$($env:USERNAME):(OI)(CI)F" /t
```

**Solution 3: Create in user profile instead**

```powershell
# Use user profile location (no admin needed)
$ProfilePath = "$env:USERPROFILE\qbittorrent_secondary"
New-Item -Path $ProfilePath -ItemType Directory -Force
```

Update all paths in batch file and config to use `%USERPROFILE%\qbittorrent_secondary`.

---

### Issue 3: Login fails on localhost:52095

**Symptom:** "Invalid username or password" error.

**Cause 1: Credentials not synced with primary**

**Solution:** Use exact same username/password as primary (from `.env`).

```powershell
# Check .env for correct credentials
Get-Content "C:\Users\dogma\Projects\MAMcrawler\.env" | Select-String "QBITTORRENT"
```

**Cause 2: Password hash not set**

**Solution:** Set password via Web UI first time:

1. Login with default credentials (admin / adminadmin)
2. Tools → Options → Web UI
3. Set username: `TopherGutbrod`
4. Set password: (your password from `.env`)
5. Save

**Cause 3: Configuration file syntax error**

**Solution:** Validate `qBittorrent.conf`:

```powershell
# Check for syntax errors
Get-Content "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf" | Select-String "WebUI"
```

Look for:
- Missing `=` signs
- Unclosed quotes
- Invalid characters

---

### Issue 4: Secondary won't start

**Symptom:** Batch file runs but nothing happens, or immediate crash.

**Cause 1: Profile directory not writable**

**Solution:**

```powershell
# Test write access
New-Item -Path "C:\qbittorrent_secondary\profile\test.txt" -ItemType File -Force
Remove-Item "C:\qbittorrent_secondary\profile\test.txt"
```

If fails, fix permissions (see Issue 2).

**Cause 2: qBittorrent.conf has syntax errors**

**Solution:** Delete config and let qBittorrent recreate it:

```powershell
Remove-Item "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf"
```

Restart secondary, reconfigure via Web UI.

**Cause 3: Wrong installation path**

**Solution:** Verify qBittorrent is installed:

```powershell
Get-Item "C:\Program Files (x86)\qBittorrent\qbittorrent.exe"
```

If not found, check alternate location:

```powershell
Get-Item "C:\Program Files\qBittorrent\qbittorrent.exe"
```

Update batch file with correct path.

**Cause 4: Corrupted database**

**Solution:** Delete database and let it rebuild:

```powershell
Remove-Item "C:\qbittorrent_secondary\profile\qBittorrent\BEP.sqlite" -Force
Remove-Item "C:\qbittorrent_secondary\profile\qBittorrent\torrents.db" -Force
```

Restart secondary (will rebuild from scratch).

---

### Issue 5: Firewall blocking localhost:52095

**Symptom:** Connection refused or timeout when accessing http://localhost:52095.

**Cause:** Windows Firewall blocking localhost (rare).

**Solution 1: Verify localhost isn't blocked**

```powershell
Test-NetConnection -ComputerName localhost -Port 52095
```

**Expected:**
```
TcpTestSucceeded : True
```

**If False:**

```powershell
# Add explicit allow rule
New-NetFirewallRule -DisplayName "Allow localhost 52095" -Direction Inbound -LocalAddress 127.0.0.1 -LocalPort 52095 -Protocol TCP -Action Allow
```

**Solution 2: Temporarily disable firewall (testing only)**

```powershell
# Disable firewall (testing ONLY)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# Test connection

# Re-enable firewall (IMPORTANT!)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

**Solution 3: Check third-party firewall/antivirus**

- Norton, McAfee, AVG, etc. may block localhost
- Check firewall logs
- Add exception for qbittorrent.exe

---

### Issue 6: Secondary takes over all magnets

**Symptom:** All magnets going to secondary instead of primary.

**Cause:** Primary marked as unhealthy when it's actually fine.

**Solution 1: Verify primary is actually healthy**

```powershell
# Test primary connection
Test-NetConnection -ComputerName 192.168.0.48 -Port 52095
```

**Expected:** `TcpTestSucceeded : True`

**Solution 2: Check VPN connection**

```powershell
# Test VPN gateway
Test-NetConnection -ComputerName 192.168.0.1
```

**If VPN down:** Reconnect ProtonVPN first.

**Solution 3: Check ResilientQBittorrentClient logs**

```python
# Run health check manually
cd C:\Users\dogma\Projects\MAMcrawler
python monitor_qbittorrent_health.py
```

Review output to see why primary marked unhealthy.

**Solution 4: Verify port proxy (if using)**

```powershell
netsh interface portproxy show all
```

If no proxy configured but primary is remote, connection will fail.

---

## Running Both Instances Together

### Scenario 1: Both Healthy

**Primary:**
- Running on remote server (192.168.0.48:52095)
- Connected via VPN (ProtonVPN)
- Handling all downloads normally

**Secondary:**
- Running on local machine (localhost:52095)
- Idle, waiting for failover trigger
- Not used unless primary fails

**Workflow Behavior:**
```
execute_full_workflow.py
  → ResilientQBittorrentClient.perform_health_check()
  → VPN: Connected ✓
  → Primary: OK ✓
  → Secondary: OK ✓
  → Uses primary for all magnet additions
  → Secondary remains idle (ready for failover)
```

**Recommendation:** Keep secondary running during VPN downloads for instant failover.

---

### Scenario 2: Primary Down (VPN Offline)

**Primary:**
- NOT accessible (VPN disconnected)
- URL returns HTTP 404 or timeout
- Health check: `VPN_DOWN` or `HTTP_404`

**Secondary:**
- Running on local machine (localhost:52095)
- Takes over all magnet additions
- Downloads proceed without interruption

**Workflow Behavior:**
```
execute_full_workflow.py
  → ResilientQBittorrentClient.perform_health_check()
  → VPN: Disconnected ✗
  → Primary: VPN_DOWN ✗
  → Secondary: OK ✓
  → Uses secondary for all magnet additions
  → Downloads proceed to C:\qbittorrent_secondary\downloads\
```

**User Action:**
1. Workflow completes using secondary
2. Later: Reconnect VPN
3. Restart primary qBittorrent
4. Future downloads auto-switch back to primary

**Magnets added during outage:**
- Remain on secondary instance
- Continue seeding from secondary
- Can manually move to primary if desired (Tools → Copy to another client)

---

### Scenario 3: Primary Restarting

**Primary:**
- Temporarily down (Windows update, manual restart, etc.)
- Will be back online in 1-5 minutes

**Secondary:**
- Detects primary unavailable
- Takes over immediately
- Adds magnets without delay

**Once Primary Restores:**

```
execute_full_workflow.py (next run)
  → ResilientQBittorrentClient.perform_health_check()
  → VPN: Connected ✓
  → Primary: OK ✓ (restored)
  → Secondary: OK ✓
  → Switches back to primary
  → New magnets go to primary again
```

**Note:** Magnets added to secondary during outage **stay on secondary**. This is expected behavior.

**Manual migration (optional):**
1. Open secondary WebUI: http://localhost:52095
2. Select torrents added during outage
3. Right-click → Pause
4. Open primary WebUI: http://192.168.0.48:52095
5. Add same magnets to primary
6. Delete from secondary once primary starts downloading

---

## Integration with Workflow

### Environment Variable Configuration

**Required in `.env`:**

```ini
# Primary instance (via VPN)
QBITTORRENT_URL=http://192.168.0.48:52095/

# Secondary instance (local fallback)
QBITTORRENT_SECONDARY_URL=http://localhost:52095/

# Authentication (same for both)
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=your_password_here
```

**That's it!** No other changes needed to `execute_full_workflow.py`.

---

### How ResilientQBittorrentClient Uses Secondary

**Initialization:**

```python
from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient
import os

client = ResilientQBittorrentClient(
    primary_url=os.getenv('QBITTORRENT_URL'),
    secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),  # Auto-detects secondary
    username=os.getenv('QBITTORRENT_USERNAME'),
    password=os.getenv('QBITTORRENT_PASSWORD')
)
```

**Health Check (automatic):**

```python
health = await client.perform_health_check()
# Returns:
# {
#     'vpn_connected': True/False,
#     'primary': 'OK' | 'VPN_DOWN' | 'HTTP_404' | 'TIMEOUT',
#     'secondary': 'OK' | 'NOT_CONFIGURED' | 'TIMEOUT',
#     'last_check': '2025-11-28T14:30:00',
#     'active_instance': 'primary' | 'secondary' | None
# }
```

**Adding Magnets (with failover):**

```python
magnet_links = ["magnet:?xt=urn:btih:..."]

successful, failed, queued = await client.add_torrents_with_fallback(magnet_links)

# successful: Magnets added to primary or secondary
# failed: Magnets that failed even with retries
# queued: Magnets saved to qbittorrent_queue.json (both instances down)
```

**Failover Decision Tree:**

```
1. Check VPN connectivity
   ├─ VPN UP → Try primary
   │   ├─ Primary OK → Add to primary ✓
   │   └─ Primary FAIL → Try secondary
   │       ├─ Secondary OK → Add to secondary ✓
   │       └─ Secondary FAIL → Queue to JSON
   └─ VPN DOWN → Skip primary, try secondary directly
       ├─ Secondary OK → Add to secondary ✓
       └─ Secondary FAIL → Queue to JSON
```

---

### Verify Integration in Logs

**Run workflow:**

```powershell
cd C:\Users\dogma\Projects\MAMcrawler
python execute_full_workflow.py
```

**Look for Phase 5 logs:**

```
[Phase 5] qBittorrent Integration
Performing qBittorrent health check...
VPN connectivity: Connected ✓
Primary instance (http://192.168.0.48:52095): OK ✓
Secondary instance (http://localhost:52095): OK ✓
Health check results: {'vpn_connected': True, 'primary': 'OK', 'secondary': 'OK', ...}
Attempting primary instance for magnet...
Successfully added via primary
```

**If primary down:**

```
[Phase 5] qBittorrent Integration
Performing qBittorrent health check...
VPN connectivity: Disconnected ✗
Primary instance (http://192.168.0.48:52095): VPN_DOWN ✗
Secondary instance (http://localhost:52095): OK ✓
Primary qBittorrent returning 404 (VPN issue?)
Attempting secondary instance for magnet...
Successfully added via secondary
```

---

## Monitoring

### Health Check Script

**Location:** `C:\Users\dogma\Projects\MAMcrawler\monitor_qbittorrent_health.py`

**Usage:**

```powershell
cd C:\Users\dogma\Projects\MAMcrawler
python monitor_qbittorrent_health.py
```

**Sample Output:**

```
======================================================================
qBittorrent Redundancy Health Check
======================================================================

VPN Status:        ✓ Connected
Primary Instance:  ✓ OK (http://192.168.0.48:52095/)
Secondary Instance: ✓ OK (http://localhost:52095/)
Last Check:        2025-11-28T14:30:00

Status Analysis:
----------------------------------------------------------------------
✓ EXCELLENT: Full redundancy operational

   Status:
   → Both instances healthy and ready
   → Automatic failover available if VPN drops
   → Zero downtime configuration active

   System Capabilities:
   • Primary failure → Automatic failover to secondary
   • Both fail → Queue to JSON for manual recovery
   • Services restore → Auto-process queued magnets
======================================================================
```

---

### Queue File Monitoring

**What is `qbittorrent_queue.json`?**

When both primary AND secondary instances are unavailable, magnets are saved to a queue file for manual recovery.

**Location:** `C:\Users\dogma\Projects\MAMcrawler\qbittorrent_queue.json`

**Check if queue file exists:**

```powershell
Get-Item "C:\Users\dogma\Projects\MAMcrawler\qbittorrent_queue.json"
```

**View queued magnets:**

```powershell
Get-Content "C:\Users\dogma\Projects\MAMcrawler\qbittorrent_queue.json" | ConvertFrom-Json
```

**Sample queue file:**

```json
{
  "saved_at": "2025-11-28T15:00:00",
  "reason": "VPN/qBittorrent unavailable",
  "magnets": [
    "magnet:?xt=urn:btih:abc123...",
    "magnet:?xt=urn:btih:def456..."
  ],
  "instructions": "Manually add these to qBittorrent when available, or paste into web UI"
}
```

**Process queue when services restore:**

```powershell
cd C:\Users\dogma\Projects\MAMcrawler
python -c "import asyncio; from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient; import os; from dotenv import load_dotenv; load_dotenv(); asyncio.run(ResilientQBittorrentClient(os.getenv('QBITTORRENT_URL'), os.getenv('QBITTORRENT_USERNAME'), os.getenv('QBITTORRENT_PASSWORD'), os.getenv('QBITTORRENT_SECONDARY_URL')).process_queue_file())"
```

---

### Monitoring Best Practices

**Before each workflow run:**

```powershell
# Quick health check
python monitor_qbittorrent_health.py
```

**If primary down:**
- Expected if VPN disconnected
- Secondary will handle downloads
- No action needed (automatic failover)

**If both down:**
- Magnets will queue to JSON
- Resolve connection issues
- Process queue file after restoration

**Weekly health check:**
- Verify both instances accessible
- Check download directories for disk space
- Review logs for errors

---

## Stopping Secondary Instance

### Method 1: Click X on Window

If secondary started via batch file:

1. Find console window: "Starting qBittorrent Secondary Instance"
2. Click X (close button)
3. Confirm: "Terminate batch job (Y/N)?" → Y

---

### Method 2: Task Manager

1. Open Task Manager (Ctrl+Shift+Esc)
2. Find "qbittorrent.exe" process
3. **Identify secondary** (look at command line):
   ```
   "C:\Program Files (x86)\qBittorrent\qbittorrent.exe" --webui-port=52095 --profile=C:\qbittorrent_secondary\profile
   ```
4. Select process → End Task

---

### Method 3: PowerShell (Advanced)

**Stop by port:**

```powershell
# Find process using port 52095 on localhost
$ProcessId = (Get-NetTCPConnection -LocalPort 52095 -LocalAddress 127.0.0.1 -ErrorAction SilentlyContinue).OwningProcess

if ($ProcessId) {
    Stop-Process -Id $ProcessId -Force
    Write-Host "Stopped secondary instance (PID: $ProcessId)"
} else {
    Write-Host "Secondary instance not running"
}
```

**Stop by command line filter:**

```powershell
Get-Process qbittorrent | Where-Object {
    $_.CommandLine -match "qbittorrent_secondary"
} | Stop-Process -Force
```

---

### IMPORTANT: Don't Leave Secondary Running Indefinitely

**Why?**
- Uses system resources (RAM, CPU)
- Downloads to temporary location (not production library)
- May cause confusion (which instance has which torrents?)

**When to run secondary:**
- During VPN downloads (for instant failover)
- When primary known to be unstable
- During testing/verification

**When to stop secondary:**
- After workflow completes
- When VPN disconnects (if primary also stops)
- When not actively needed

**Exception:** If you want always-on redundancy, keep both running 24/7 (requires manual file management).

---

## Production Checklist

Use this checklist before deploying secondary instance:

### Pre-Deployment

- [ ] Windows 10/11 with Administrator access
- [ ] qBittorrent installed: `C:\Program Files (x86)\qBittorrent\qbittorrent.exe`
- [ ] Primary qBittorrent credentials known (from `.env`)
- [ ] Adequate disk space on C:\ drive (10+ GB recommended)
- [ ] Firewall allows localhost traffic (default: yes)

### Directory Setup

- [ ] `C:\qbittorrent_secondary\` directory created
- [ ] `C:\qbittorrent_secondary\profile\` directory created
- [ ] `C:\qbittorrent_secondary\downloads\` directory created
- [ ] `C:\qbittorrent_secondary\downloads\.incomplete\` directory created
- [ ] `C:\qbittorrent_secondary\profile\qBittorrent\` directory created

### Configuration

- [ ] `qBittorrent.conf` copied from template
- [ ] `qBittorrent.conf` WebUI port set to 52095
- [ ] `qBittorrent.conf` download paths updated
- [ ] `qBittorrent.conf` BitTorrent ports configured (6881-6920)
- [ ] `start_secondary.bat` created
- [ ] Batch file tested (launches secondary successfully)

### First Launch

- [ ] Secondary started via batch file
- [ ] WebUI accessible at http://localhost:52095
- [ ] Logged in with default credentials (admin/adminadmin)
- [ ] Password changed to match primary
- [ ] Username changed to match primary (TopherGutbrod)
- [ ] Logged out and back in with new credentials ✓

### Testing

- [ ] Test magnet added successfully
- [ ] Test magnet appears in secondary's torrent list
- [ ] Test magnet does NOT appear in primary's list
- [ ] Test download goes to `C:\qbittorrent_secondary\downloads\`
- [ ] Test torrent removed (cleanup)

### Environment Integration

- [ ] `.env` file has `QBITTORRENT_SECONDARY_URL=http://localhost:52095/`
- [ ] `.env` file has matching username/password
- [ ] `execute_full_workflow.py` Phase 5 runs without error
- [ ] Health check shows both instances: `python monitor_qbittorrent_health.py`

### Failover Testing

- [ ] Disconnect VPN
- [ ] Run `python monitor_qbittorrent_health.py`
- [ ] Verify primary shows `VPN_DOWN`
- [ ] Verify secondary shows `OK`
- [ ] Run workflow: `python execute_full_workflow.py`
- [ ] Verify workflow uses secondary (check logs)
- [ ] Reconnect VPN
- [ ] Verify primary restored

### Production Ready

- [ ] Desktop shortcut created
- [ ] Shortcut tested (one-click launch)
- [ ] Documentation reviewed
- [ ] Troubleshooting section bookmarked
- [ ] Backup of `qBittorrent.conf` created
- [ ] All tests passed ✓

---

## Summary

You've successfully set up a **zero-downtime qBittorrent failover system**!

**What you have:**
- **Primary instance** (192.168.0.48:52095 via VPN) for normal operations
- **Secondary instance** (localhost:52095) for automatic failover
- **Queue file fallback** when both instances unavailable
- **Health monitoring** to track system status

**How to use:**
1. Run primary normally (via VPN)
2. Start secondary when needed: `C:\qbittorrent_secondary\start_secondary.bat`
3. Workflow automatically fails over if primary unavailable
4. Check health: `python monitor_qbittorrent_health.py`

**Next steps:**
- Test failover by disconnecting VPN
- Monitor queue file for manual recovery scenarios
- Keep secondary running during critical download periods

**Need help?** Review the troubleshooting section or check the logs.

---

**Document Version:** 1.0
**Last Updated:** 2025-11-28
**Author:** MAMcrawler Project
**Related Docs:**
- `PHASE_5_VPN_RESILIENT_INTEGRATION.md`
- `QBITTORRENT_REDUNDANCY_SETUP.md`
- `VPN_RESILIENT_QUICK_START.md`
