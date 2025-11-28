# Secondary qBittorrent - Quick Reference Guide

**Quick access guide for common tasks with the secondary qBittorrent instance.**

---

## Quick Start

### Start Secondary Instance

**Option 1: Desktop Shortcut**
- Double-click "qBittorrent Secondary" on Desktop

**Option 2: Batch File**
```powershell
C:\qbittorrent_secondary\start_secondary.bat
```

**Option 3: Command Line**
```powershell
set APPDATA=C:\qbittorrent_secondary\profile
"C:\Program Files (x86)\qBittorrent\qbittorrent.exe" --webui-port=52095 --profile=C:\qbittorrent_secondary\profile
```

### Access WebUI

**URL:** http://localhost:52095

**Credentials:** (same as primary)
- Username: `TopherGutbrod`
- Password: (from `.env` file)

---

## Common Commands

### Check Health Status

```powershell
cd C:\Users\dogma\Projects\MAMcrawler
python monitor_qbittorrent_health.py
```

### Stop Secondary Instance

**Method 1:** Close console window (X button)

**Method 2:** Task Manager → End qbittorrent.exe (secondary process)

**Method 3:** PowerShell
```powershell
Get-NetTCPConnection -LocalPort 52095 -LocalAddress 127.0.0.1 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

### Check Port Status

```powershell
netstat -ano | findstr 52095
```

**Expected output (both instances running):**
```
TCP    192.168.0.48:52095    ... (primary via VPN)
TCP    127.0.0.1:52095       ... (secondary local)
```

### Verify Downloads Directory

```powershell
Get-ChildItem C:\qbittorrent_secondary\downloads
```

---

## Key File Locations

| Item | Path |
|------|------|
| **Secondary Root** | `C:\qbittorrent_secondary\` |
| **Profile** | `C:\qbittorrent_secondary\profile\` |
| **Downloads** | `C:\qbittorrent_secondary\downloads\` |
| **Config File** | `C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf` |
| **Startup Script** | `C:\qbittorrent_secondary\start_secondary.bat` |
| **Desktop Shortcut** | `%USERPROFILE%\Desktop\qBittorrent Secondary.lnk` |

---

## Configuration Summary

| Setting | Primary | Secondary |
|---------|---------|-----------|
| **IP Address** | 192.168.0.48 | localhost (127.0.0.1) |
| **WebUI Port** | 52095 | 52095 (SAME) |
| **BitTorrent Ports** | 6881-6900 | 6881-6920 |
| **Downloads** | F:\Audiobookshelf\Books\ | C:\qbittorrent_secondary\downloads\ |
| **Profile** | Default AppData | C:\qbittorrent_secondary\profile\ |

---

## Troubleshooting Quick Fixes

### Secondary Won't Start - "Port Already in Use"

**Fix:** Kill process using port 52095
```powershell
$pid = (Get-NetTCPConnection -LocalPort 52095 -LocalAddress 127.0.0.1).OwningProcess
Stop-Process -Id $pid -Force
```

### Can't Login - "Invalid Credentials"

**Fix 1:** Verify credentials from .env
```powershell
Get-Content C:\Users\dogma\Projects\MAMcrawler\.env | Select-String "QBITTORRENT"
```

**Fix 2:** Reset to default (admin/adminadmin)
```powershell
Remove-Item C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf
# Restart secondary
```

### Health Check Shows "TIMEOUT"

**Fix:** Verify secondary is running
```powershell
Test-NetConnection -ComputerName localhost -Port 52095
```

**If fails:** Restart secondary instance

### Downloads Not Starting

**Fix:** Check VPN status (might be routing issue)
```powershell
# Test VPN gateway
Test-NetConnection -ComputerName 192.168.0.1
```

---

## Environment Variables

**Required in `.env` file:**

```ini
# Primary instance (via VPN)
QBITTORRENT_URL=http://192.168.0.48:52095/

# Secondary instance (local)
QBITTORRENT_SECONDARY_URL=http://localhost:52095/

# Authentication (same for both)
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=your_password_here
```

---

## Workflow Integration

### How Failover Works

1. **VPN Connected → Uses Primary**
   - All magnets go to 192.168.0.48:52095
   - Secondary idle (ready for failover)

2. **VPN Disconnected → Uses Secondary**
   - Primary unreachable (VPN_DOWN)
   - All magnets go to localhost:52095
   - Downloads to `C:\qbittorrent_secondary\downloads\`

3. **Both Down → Queue to File**
   - Magnets saved to `qbittorrent_queue.json`
   - Manually add later or auto-process when services restore

### Check Failover Status

```powershell
python monitor_qbittorrent_health.py
```

**Look for:**
- VPN Status (Connected/Disconnected)
- Primary Instance (OK/VPN_DOWN/TIMEOUT)
- Secondary Instance (OK/TIMEOUT/NOT_CONFIGURED)

---

## Daily Operations

### Before Running Workflow

```powershell
# Quick health check
python monitor_qbittorrent_health.py
```

**Expected:** Both instances OK

### During VPN Outage

1. Secondary automatically takes over
2. Downloads proceed without interruption
3. Check logs to confirm: "Attempting secondary instance"

### After VPN Restores

1. Primary auto-resumes on next workflow run
2. Magnets added during outage stay on secondary
3. Optional: Manually migrate torrents to primary

### Check Queue File

```powershell
Get-Item C:\Users\dogma\Projects\MAMcrawler\qbittorrent_queue.json
```

**If exists:** Process queued magnets
```powershell
cd C:\Users\dogma\Projects\MAMcrawler
python -c "import asyncio; from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient; import os; from dotenv import load_dotenv; load_dotenv(); asyncio.run(ResilientQBittorrentClient(os.getenv('QBITTORRENT_URL'), os.getenv('QBITTORRENT_USERNAME'), os.getenv('QBITTORRENT_PASSWORD'), os.getenv('QBITTORRENT_SECONDARY_URL')).process_queue_file())"
```

---

## One-Liners

### Complete Setup (Automated)

```powershell
cd C:\Users\dogma\Projects\MAMcrawler
powershell -ExecutionPolicy Bypass -File setup_secondary_qbittorrent.ps1
```

### Start + Open Browser

```powershell
Start-Process C:\qbittorrent_secondary\start_secondary.bat; Start-Sleep 5; Start-Process http://localhost:52095
```

### Health Check + View Logs

```powershell
python monitor_qbittorrent_health.py; Get-Content C:\qbittorrent_secondary\profile\qBittorrent\logs\*.log -Tail 20
```

### Restart Secondary

```powershell
Get-Process qbittorrent | Where-Object {$_.CommandLine -match "52095"} | Stop-Process -Force; Start-Sleep 2; C:\qbittorrent_secondary\start_secondary.bat
```

---

## Testing Scenarios

### Test Failover (VPN Disconnect)

```powershell
# 1. Disconnect VPN (manually)
# 2. Check health
python monitor_qbittorrent_health.py
# Expected: Primary VPN_DOWN, Secondary OK

# 3. Run workflow
python execute_full_workflow.py
# Expected: Uses secondary, downloads succeed

# 4. Reconnect VPN
# 5. Check health again
python monitor_qbittorrent_health.py
# Expected: Both OK, primary restored
```

### Test Manual Magnet Add

```powershell
# 1. Open secondary WebUI
Start-Process http://localhost:52095

# 2. Add test magnet (Ubuntu ISO)
# magnet:?xt=urn:btih:e83a2b5c1c5b6b3a8c4c9b1c5b5c6b3a8c4c9b1c&dn=ubuntu-20.04.1-desktop-amd64.iso

# 3. Verify download starts
Get-ChildItem C:\qbittorrent_secondary\downloads

# 4. Verify NOT in primary
# Open http://192.168.0.48:52095 (if VPN connected)
# Torrent should NOT appear

# 5. Clean up
# WebUI: Right-click torrent → Delete → Delete files from disk
```

---

## Maintenance

### Weekly

- [ ] Run health check
- [ ] Verify both instances accessible
- [ ] Check download folder disk space

### Monthly

- [ ] Review logs for errors
- [ ] Test failover (disconnect VPN temporarily)
- [ ] Verify .env credentials still valid

### Quarterly

- [ ] Update qBittorrent (if new version available)
- [ ] Review download folder size
- [ ] Clean up old/completed torrents

---

## Emergency Procedures

### Both Instances Down

**Symptoms:** Workflow shows "All instances failed, queuing magnet"

**Fix:**
1. Check VPN connection: `Test-NetConnection 192.168.0.1`
2. Start secondary: `C:\qbittorrent_secondary\start_secondary.bat`
3. Check health: `python monitor_qbittorrent_health.py`
4. Process queue: (see "Check Queue File" above)

### Secondary Corrupted/Won't Start

**Quick reinstall:**
```powershell
# Remove secondary
Remove-Item C:\qbittorrent_secondary -Recurse -Force

# Re-run setup
cd C:\Users\dogma\Projects\MAMcrawler
powershell -ExecutionPolicy Bypass -File setup_secondary_qbittorrent.ps1
```

### Lost Password

**Reset to defaults:**
```powershell
Remove-Item C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf
# Restart secondary
# Login: admin / adminadmin
# Change password via WebUI
```

---

## Documentation Links

- **Full Setup Guide:** `SECONDARY_QBITTORRENT_SETUP.md`
- **Deployment Checklist:** `SECONDARY_DEPLOYMENT_CHECKLIST.md`
- **Phase 5 Integration:** `PHASE_5_VPN_RESILIENT_INTEGRATION.md`
- **Redundancy Overview:** `QBITTORRENT_REDUNDANCY_SETUP.md`

---

**Last Updated:** 2025-11-28
**Quick Reference Version:** 1.0
