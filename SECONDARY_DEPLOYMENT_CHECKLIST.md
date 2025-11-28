# Secondary qBittorrent Deployment Checklist

**Version:** 1.0
**Last Updated:** 2025-11-28
**Purpose:** Ensure safe and complete deployment of secondary qBittorrent instance

---

## Pre-Deployment Checklist

### System Requirements

- [ ] **Operating System:** Windows 10 or Windows 11
- [ ] **Administrator Access:** Can run PowerShell as Administrator
- [ ] **Disk Space:** At least 10 GB free on C:\ drive
- [ ] **RAM:** At least 4 GB system memory
- [ ] **Network:** Localhost connectivity enabled (default on Windows)

### Software Prerequisites

- [ ] **qBittorrent Installed:** Version 4.3+ at one of:
  - `C:\Program Files (x86)\qBittorrent\qbittorrent.exe`
  - `C:\Program Files\qBittorrent\qbittorrent.exe`
- [ ] **Python Installed:** Python 3.8+ for workflow scripts
- [ ] **MAMcrawler Project:** Cloned to `C:\Users\dogma\Projects\MAMcrawler`
- [ ] **Primary qBittorrent:** Already configured and working

### Configuration Prerequisites

- [ ] **Primary Credentials Known:** Username and password from `.env` file
- [ ] **Primary URL Known:** Usually `http://192.168.0.48:52095/`
- [ ] **VPN Configuration:** ProtonVPN or equivalent configured (for testing failover)
- [ ] **Environment File:** `.env` file exists in project root

### Documentation Review

- [ ] Read `SECONDARY_QBITTORRENT_SETUP.md` (at least Overview section)
- [ ] Reviewed `PHASE_5_VPN_RESILIENT_INTEGRATION.md` (understand failover logic)
- [ ] Bookmarked troubleshooting section in setup guide
- [ ] Identified support contact (if deployment for someone else)

---

## Deployment Checklist

### Option A: Automated Deployment (Recommended)

- [ ] **Open PowerShell as Administrator**
  - Right-click Start → Windows PowerShell (Admin)
- [ ] **Navigate to project directory**
  ```powershell
  cd C:\Users\dogma\Projects\MAMcrawler
  ```
- [ ] **Run automated setup script**
  ```powershell
  powershell -ExecutionPolicy Bypass -File setup_secondary_qbittorrent.ps1
  ```
- [ ] **Confirm setup when prompted** (press Y)
- [ ] **Review setup output** (verify no errors)
- [ ] **Script completed successfully** (no red error messages)

**If automated deployment fails, use Option B (Manual Deployment)**

---

### Option B: Manual Deployment

#### 1. Create Directory Structure

- [ ] **Create root directory**
  ```powershell
  New-Item -Path "C:\qbittorrent_secondary" -ItemType Directory -Force
  ```
- [ ] **Create profile directory**
  ```powershell
  New-Item -Path "C:\qbittorrent_secondary\profile" -ItemType Directory -Force
  ```
- [ ] **Create downloads directory**
  ```powershell
  New-Item -Path "C:\qbittorrent_secondary\downloads" -ItemType Directory -Force
  ```
- [ ] **Create incomplete directory**
  ```powershell
  New-Item -Path "C:\qbittorrent_secondary\downloads\.incomplete" -ItemType Directory -Force
  ```
- [ ] **Create config directory**
  ```powershell
  New-Item -Path "C:\qbittorrent_secondary\profile\qBittorrent" -ItemType Directory -Force
  ```

#### 2. Configure qBittorrent

- [ ] **Copy template configuration**
  ```powershell
  Copy-Item "C:\Users\dogma\Projects\MAMcrawler\qbittorrent_secondary_config.ini" -Destination "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf"
  ```
- [ ] **Open qBittorrent.conf in Notepad**
  ```powershell
  notepad "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf"
  ```
- [ ] **Replace `{YourUsername}`** with actual Windows username (e.g., `dogma`)
- [ ] **Verify WebUI port:** `WebUI\Port=52095`
- [ ] **Verify download path:** `Downloads\SavePath=C:\\qbittorrent_secondary\\downloads`
- [ ] **Save and close** Notepad

#### 3. Create Startup Batch File

- [ ] **Create batch file**
  ```powershell
  notepad "C:\qbittorrent_secondary\start_secondary.bat"
  ```
- [ ] **Paste this content** (verify paths match your system):
  ```batch
  @echo off
  echo Starting qBittorrent Secondary Instance
  echo WebUI: http://localhost:52095
  echo.
  set APPDATA=C:\qbittorrent_secondary\profile
  "C:\Program Files (x86)\qBittorrent\qbittorrent.exe" --webui-port=52095 --profile=C:\qbittorrent_secondary\profile
  pause
  ```
- [ ] **Save and close** Notepad

#### 4. Create Desktop Shortcut

- [ ] **Right-click Desktop** → New → Shortcut
- [ ] **Target:** `C:\qbittorrent_secondary\start_secondary.bat`
- [ ] **Name:** `qBittorrent Secondary`
- [ ] **Change icon** (optional):
  - Right-click shortcut → Properties → Change Icon
  - Browse: `C:\Program Files (x86)\qBittorrent\qbittorrent.exe`

#### 5. Update Environment File

- [ ] **Open .env file**
  ```powershell
  notepad "C:\Users\dogma\Projects\MAMcrawler\.env"
  ```
- [ ] **Add secondary URL** (if not already present):
  ```ini
  QBITTORRENT_SECONDARY_URL=http://localhost:52095/
  ```
- [ ] **Verify primary URL** is set:
  ```ini
  QBITTORRENT_URL=http://192.168.0.48:52095/
  ```
- [ ] **Verify credentials** are set:
  ```ini
  QBITTORRENT_USERNAME=TopherGutbrod
  QBITTORRENT_PASSWORD=your_password_here
  ```
- [ ] **Save and close**

---

## Post-Deployment Verification

### Phase 1: Basic Verification

- [ ] **Verify directory structure**
  ```powershell
  Get-ChildItem "C:\qbittorrent_secondary" -Recurse -Directory
  ```
  **Expected:** profile, downloads, .incomplete, qBittorrent directories exist

- [ ] **Verify configuration file**
  ```powershell
  Get-Item "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf"
  ```
  **Expected:** File exists, size > 0 bytes

- [ ] **Verify batch file**
  ```powershell
  Get-Item "C:\qbittorrent_secondary\start_secondary.bat"
  ```
  **Expected:** File exists

- [ ] **Verify Desktop shortcut**
  ```powershell
  Get-Item "$env:USERPROFILE\Desktop\qBittorrent Secondary.lnk"
  ```
  **Expected:** Shortcut exists

---

### Phase 2: First Launch Verification

- [ ] **Start secondary instance**
  - Double-click Desktop shortcut OR
  - Run: `C:\qbittorrent_secondary\start_secondary.bat`

- [ ] **Console window appears**
  - Shows "Starting qBittorrent Secondary Instance"
  - No error messages

- [ ] **qBittorrent tray icon appears**
  - Look in system tray (bottom-right)
  - Icon shows qBittorrent logo

- [ ] **Wait 5 seconds for startup**

- [ ] **Open browser to http://localhost:52095**

- [ ] **WebUI login page appears**
  - Shows qBittorrent login form
  - No "connection refused" or "404" errors

---

### Phase 3: Password Configuration

- [ ] **Login with default credentials**
  - Username: `admin`
  - Password: `adminadmin`

- [ ] **Login successful**
  - qBittorrent Web UI dashboard loads
  - Shows torrent list (empty)

- [ ] **Open Web UI settings**
  - Click Tools → Options → Web UI

- [ ] **Change username**
  - Change from `admin` to: `TopherGutbrod` (match primary)

- [ ] **Change password**
  - Set to match primary (from `.env` file)
  - **DO NOT use default password in production!**

- [ ] **Save settings**
  - Click "Save" button
  - Settings saved confirmation appears

- [ ] **Logout and login again**
  - Click logout icon
  - Login with NEW credentials (TopherGutbrod / your-password)

- [ ] **Login successful with new credentials**

---

### Phase 4: Test Magnet Addition

**Test magnet link (Ubuntu ISO - legal, safe, fast):**
```
magnet:?xt=urn:btih:e83a2b5c1c5b6b3a8c4c9b1c5b5c6b3a8c4c9b1c&dn=ubuntu-20.04.1-desktop-amd64.iso
```

- [ ] **Add test magnet**
  - Click "Add Torrent" button (+ icon)
  - Paste magnet link
  - Verify save path: `C:\qbittorrent_secondary\downloads\`
  - Click "Download"

- [ ] **Torrent appears in list**
  - Shows in torrent list
  - Status: "Downloading" or "Metadata downloading"

- [ ] **Download starts**
  - Shows download speed > 0 KB/s (may take 30-60 seconds)

- [ ] **Verify file appears in downloads folder**
  ```powershell
  Get-ChildItem "C:\qbittorrent_secondary\downloads"
  ```
  **Expected:** Folder or files for Ubuntu ISO appear

- [ ] **Verify primary NOT affected**
  - Open primary WebUI: http://192.168.0.48:52095 (if VPN connected)
  - Test torrent does NOT appear in primary's list

- [ ] **Remove test torrent**
  - Right-click test torrent → Delete
  - Select "Delete files from disk"
  - Confirm deletion

- [ ] **Verify test files removed**
  ```powershell
  Get-ChildItem "C:\qbittorrent_secondary\downloads"
  ```
  **Expected:** Test files gone

---

### Phase 5: Health Check Integration

- [ ] **Run health check script**
  ```powershell
  cd C:\Users\dogma\Projects\MAMcrawler
  python monitor_qbittorrent_health.py
  ```

- [ ] **Health check completes successfully**

- [ ] **VPN status shows Connected** (if VPN running)

- [ ] **Primary instance shows OK**
  - Status: `✓ OK`
  - URL: `http://192.168.0.48:52095/`

- [ ] **Secondary instance shows OK**
  - Status: `✓ OK`
  - URL: `http://localhost:52095/`

- [ ] **No queue file present**
  - Verify: `qbittorrent_queue.json` does NOT exist

---

### Phase 6: Failover Testing

**IMPORTANT:** This test temporarily disconnects VPN. Ensure no critical downloads in progress.

- [ ] **Disconnect VPN**
  - Close ProtonVPN or disable VPN connection
  - Wait 10 seconds for disconnection

- [ ] **Run health check again**
  ```powershell
  python monitor_qbittorrent_health.py
  ```

- [ ] **Verify failover state**
  - VPN status: `✗ Disconnected`
  - Primary status: `✗ VPN Down`
  - Secondary status: `✓ OK`

- [ ] **Run full workflow (optional)**
  ```powershell
  python execute_full_workflow.py
  ```

- [ ] **Verify workflow uses secondary**
  - Check logs for "Attempting secondary instance"
  - Verify magnets added successfully (if any found)

- [ ] **Reconnect VPN**
  - Reconnect ProtonVPN
  - Wait 10 seconds for connection

- [ ] **Run health check again**
  ```powershell
  python monitor_qbittorrent_health.py
  ```

- [ ] **Verify primary restored**
  - VPN status: `✓ Connected`
  - Primary status: `✓ OK`
  - Secondary status: `✓ OK`

---

### Phase 7: Final Verification

- [ ] **Both instances accessible simultaneously**
  - Primary: http://192.168.0.48:52095 (via VPN)
  - Secondary: http://localhost:52095 (local)
  - Both login successfully with same credentials

- [ ] **Environment file updated**
  ```powershell
  Get-Content "C:\Users\dogma\Projects\MAMcrawler\.env" | Select-String "QBITTORRENT"
  ```
  **Expected output includes:**
  ```
  QBITTORRENT_URL=http://192.168.0.48:52095/
  QBITTORRENT_SECONDARY_URL=http://localhost:52095/
  QBITTORRENT_USERNAME=TopherGutbrod
  QBITTORRENT_PASSWORD=...
  ```

- [ ] **Separate download directories confirmed**
  - Primary: `F:\Audiobookshelf\Books\` (or configured location)
  - Secondary: `C:\qbittorrent_secondary\downloads\`
  - No overlap between the two

- [ ] **Documentation accessible**
  - Can open `SECONDARY_QBITTORRENT_SETUP.md`
  - Troubleshooting section bookmarked

- [ ] **Support contact known** (if applicable)

---

## Troubleshooting Checklist

**Use this if any verification steps fail.**

### Issue: Secondary won't start

- [ ] **Check qBittorrent installation path**
  ```powershell
  Get-Item "C:\Program Files (x86)\qBittorrent\qbittorrent.exe"
  ```
  If not found, update batch file with correct path

- [ ] **Check for port conflicts**
  ```powershell
  netstat -ano | findstr 52095
  ```
  If port already in use, kill process or use different port

- [ ] **Verify permissions**
  ```powershell
  # Test write access
  New-Item -Path "C:\qbittorrent_secondary\profile\test.txt" -Force
  Remove-Item "C:\qbittorrent_secondary\profile\test.txt"
  ```
  If fails, run batch file as Administrator

- [ ] **Check Task Manager**
  - Open Task Manager
  - Look for `qbittorrent.exe` processes
  - End any conflicting instances

---

### Issue: Can't login to WebUI

- [ ] **Verify correct credentials**
  - Check `.env` file for username/password
  - Try default credentials: admin / adminadmin (first launch only)

- [ ] **Reset password (if forgotten)**
  ```powershell
  # Delete config to reset
  Remove-Item "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf"
  ```
  Restart secondary, reconfigure password

- [ ] **Check browser cache**
  - Clear browser cache
  - Try incognito/private window
  - Try different browser

---

### Issue: Health check shows secondary as "TIMEOUT"

- [ ] **Verify secondary is running**
  ```powershell
  netstat -ano | findstr 52095
  ```
  Should show 127.0.0.1:52095 LISTENING

- [ ] **Verify firewall not blocking**
  ```powershell
  Test-NetConnection -ComputerName localhost -Port 52095
  ```
  Should return TcpTestSucceeded: True

- [ ] **Check WebUI enabled in config**
  ```powershell
  Get-Content "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf" | Select-String "WebUI"
  ```
  Should show: WebUI\Enabled=true

---

### Issue: Magnets go to wrong instance

- [ ] **Verify .env configuration**
  - QBITTORRENT_URL should point to primary
  - QBITTORRENT_SECONDARY_URL should point to secondary

- [ ] **Check VPN status**
  - If VPN down, secondary is correct (expected behavior)
  - If VPN up but using secondary, check primary health

- [ ] **Review workflow logs**
  ```powershell
  python execute_full_workflow.py 2>&1 | Select-String "qBittorrent"
  ```
  Look for which instance was attempted

---

### Issue: Downloads in wrong location

- [ ] **Verify qBittorrent.conf paths**
  ```powershell
  Get-Content "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf" | Select-String "SavePath"
  ```
  Should show: Downloads\SavePath=C:\\qbittorrent_secondary\\downloads

- [ ] **Check category settings**
  - Open secondary WebUI
  - Categories panel (left sidebar)
  - Verify "audiobooks" category points to correct location

- [ ] **Verify which instance added the torrent**
  - Check torrent list in both instances
  - Verify download location in torrent properties

---

## Rollback Procedure

**If deployment fails and you need to revert:**

### Quick Rollback (Remove Secondary)

- [ ] **Stop secondary instance**
  - Close console window
  - OR Task Manager → End qbittorrent.exe (secondary)

- [ ] **Remove directory**
  ```powershell
  Remove-Item -Path "C:\qbittorrent_secondary" -Recurse -Force
  ```

- [ ] **Remove Desktop shortcut**
  ```powershell
  Remove-Item "$env:USERPROFILE\Desktop\qBittorrent Secondary.lnk"
  ```

- [ ] **Remove .env entry**
  - Edit `.env` file
  - Remove line: `QBITTORRENT_SECONDARY_URL=http://localhost:52095/`

- [ ] **Remove firewall rules (optional)**
  ```powershell
  Remove-NetFirewallRule -DisplayName "qBittorrent Secondary WebUI"
  Remove-NetFirewallRule -DisplayName "qBittorrent Secondary BitTorrent"
  ```

- [ ] **Verify primary still works**
  ```powershell
  python monitor_qbittorrent_health.py
  ```
  Should show primary OK, secondary NOT_CONFIGURED

---

### Full System Restore (Nuclear Option)

**Only use if secondary instance corrupted primary or caused major issues.**

- [ ] **Stop all qBittorrent instances**
  ```powershell
  Get-Process qbittorrent | Stop-Process -Force
  ```

- [ ] **Backup primary configuration**
  ```powershell
  Copy-Item "$env:APPDATA\qBittorrent" -Destination "$env:USERPROFILE\qBittorrent_backup" -Recurse
  ```

- [ ] **Remove secondary completely** (see Quick Rollback above)

- [ ] **Restart primary qBittorrent**
  - Launch from Start Menu
  - Verify WebUI accessible
  - Verify torrents still present

- [ ] **Restore primary config if needed**
  ```powershell
  Copy-Item "$env:USERPROFILE\qBittorrent_backup\*" -Destination "$env:APPDATA\qBittorrent" -Recurse -Force
  ```

- [ ] **Verify primary health**
  ```powershell
  python monitor_qbittorrent_health.py
  ```

---

## Production Readiness Sign-Off

**All sections above must be checked before signing off.**

### Deployment Team Sign-Off

- [ ] **All Pre-Deployment checks passed**
- [ ] **All Deployment steps completed**
- [ ] **All Post-Deployment verification passed**
- [ ] **Failover tested successfully**
- [ ] **Rollback procedure reviewed and understood**
- [ ] **Documentation accessible to end users**
- [ ] **Support contact identified**

### Deployment Details

- **Deployment Date:** ____________________
- **Deployed By:** ____________________
- **System Hostname:** ____________________
- **Primary URL:** ____________________
- **Secondary URL:** ____________________
- **Environment File Location:** ____________________
- **Verified By:** ____________________
- **Approval:** ____________________

---

## Post-Deployment Monitoring

**First 7 days after deployment:**

- [ ] **Day 1:** Run health check, verify both instances accessible
- [ ] **Day 3:** Run health check, verify no errors in logs
- [ ] **Day 7:** Test failover again (disconnect VPN temporarily)

**Ongoing:**

- [ ] **Weekly:** Run `python monitor_qbittorrent_health.py`
- [ ] **Monthly:** Verify downloads directory has adequate space
- [ ] **Quarterly:** Review logs for errors or warnings

---

## Support Resources

- **Setup Guide:** `SECONDARY_QBITTORRENT_SETUP.md`
- **Phase 5 Documentation:** `PHASE_5_VPN_RESILIENT_INTEGRATION.md`
- **Health Monitor:** `python monitor_qbittorrent_health.py`
- **Troubleshooting:** See "Common Issues & Solutions" in setup guide

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-28 | MAMcrawler Project | Initial deployment checklist |

---

**End of Checklist**
