# Production Deployment Checklist - VPN-Resilient qBittorrent System

**Date**: 2025-11-28
**Status**: Ready for Immediate Deployment
**Project Size**: 2.2 GB (complete with all documentation)

---

## Pre-Deployment Verification

### System Requirements ✅

- [ ] **Windows 10/11** - Current OS
- [ ] **Administrator Access** - For setup script and service management
- [ ] **PowerShell 5.0+** - For automated setup (built-in on Windows 10+)
- [ ] **Python 3.8+** - For health check and testing scripts
- [ ] **500 MB Free Disk Space** - For secondary instance config
- [ ] **qBittorrent Installed** - At C:\Program Files (x86)\qBittorrent\
- [ ] **Internet Connectivity** - For downloading torrents

### Project Integrity ✅

- [ ] **Project Location**: C:\Users\dogma\Projects\MAMcrawler
- [ ] **Project Size**: 2.2 GB (reasonable for full documentation + code)
- [ ] **Git Status**: On main branch, 31 commits ahead of origin
- [ ] **All Files Present**: execute_full_workflow.py, .env, etc.

### Primary qBittorrent Status ✅

- [ ] **Service Running**: Check https://192.168.0.48:52095/
- [ ] **VPN Connected**: Can reach 192.168.0.48
- [ ] **Credentials Working**: QBITTORRENT_USERNAME + QBITTORRENT_PASSWORD set in .env
- [ ] **WebUI Responsive**: Login page loads without timeout
- [ ] **Download Path Valid**: F:\Audiobookshelf\Books\ exists and has write permissions

### Environment Variables ✅

```
QBITTORRENT_URL=http://192.168.0.48:52095/
QBITTORRENT_USERNAME=TopherGutbrod
QBITTORRENT_PASSWORD=<your_password>
PYTHONIOENCODING=utf-8
```

Check with:
```powershell
Get-Content .env | findstr QBITTORRENT
```

---

## Deployment Phase 1: Automated Setup

### Step 1.1: Pre-Flight Check

```powershell
# Verify PowerShell execution policy can be bypassed
powershell -ExecutionPolicy Bypass -Command "Write-Host 'OK'"

# Expected: OK appears, no error
```

**If failed**:
- Right-click PowerShell → Run as Administrator
- Try again

### Step 1.2: Run Automated Setup Script

```powershell
# Navigate to project
cd C:\Users\dogma\Projects\MAMcrawler

# Run setup with elevated privileges
powershell -ExecutionPolicy Bypass -File setup_secondary_qbittorrent.ps1
```

**Expected behavior**:
- Script starts
- Lists pre-flight checks (should all show ✓)
- Creates directories: C:\qbittorrent_secondary\
- Copies configuration file
- Creates start_secondary.bat
- Updates .env file
- Shows success message

**Duration**: ~5 minutes

**If failed**:
- Check error message for specific issue
- Refer to `SECONDARY_DEPLOYMENT_CHECKLIST.md` → Troubleshooting
- Or use manual setup: `SECONDARY_QBITTORRENT_SETUP.md`

### Step 1.3: Verify Setup Completed

```powershell
# Check directory structure
Test-Path "C:\qbittorrent_secondary"
Test-Path "C:\qbittorrent_secondary\profile\qBittorrent\qBittorrent.conf"
Test-Path "C:\qbittorrent_secondary\start_secondary.bat"

# Expected: All should return True
```

### Step 1.4: Verify .env Updated

```powershell
# Check for secondary URL
Get-Content .env | findstr QBITTORRENT_SECONDARY_URL

# Expected: QBITTORRENT_SECONDARY_URL=http://localhost:52095/
```

**If missing**, manually add:
```ini
QBITTORRENT_SECONDARY_URL=http://localhost:52095/
```

---

## Deployment Phase 2: Start Secondary Instance

### Step 2.1: Start Secondary qBittorrent

```batch
# Method 1: Run batch file
C:\qbittorrent_secondary\start_secondary.bat

# Or Method 2: Double-click in Windows Explorer
# Navigate to: C:\qbittorrent_secondary\
# Double-click: start_secondary.bat
```

**Expected behavior**:
- New command window opens
- Shows qBittorrent startup messages
- After ~5 seconds: "Listening on IP 127.0.0.1:52095" appears
- Window stays open (don't close)

**Duration**: ~5 seconds to startup

**If fails**:
- Check error message
- Verify C:\qbittorrent_secondary\ permissions
- See Troubleshooting section

### Step 2.2: Wait for Full Startup

- Wait 5 seconds after window opens
- Look for: "Listening on IP" message
- Verify: Command window is active and window shows status messages

### Step 2.3: Set WebUI Password (First Time Only)

1. Open browser: `http://localhost:52095`
2. Default login:
   - Username: `TopherGutbrod`
   - Password: `admin`
3. Navigate: Settings → WebUI
4. Change password to match primary (from .env)
5. Click Save

**Note**: Password must match primary for automatic failover to work

---

## Deployment Phase 3: Verification

### Step 3.1: Verify Both Instances Running

```powershell
# Check processes
Get-Process qbittorrent

# Expected output: Should show at least 1 qbittorrent process
# Note: May not show separate process for secondary (uses same exe)
```

### Step 3.2: Verify Network Ports

```powershell
# Check port 52095 is listening
netstat -ano | findstr 52095

# Expected: Should show entries for 52095
# Note: Both primary and secondary may show (primary via VPN, secondary local)
```

### Step 3.3: Test WebUI Access

Primary instance:
```powershell
curl -k https://192.168.0.48:52095/

# Expected: HTTP 200 + login page
```

Secondary instance:
```powershell
curl http://localhost:52095/

# Expected: HTTP 200 + login page
```

### Step 3.4: Run Health Check Script

```powershell
# Run health check
python monitor_qbittorrent_health.py

# Expected output:
# ============ qBittorrent Health Check ============
# VPN Status: CONNECTED (192.168.0.1 ping successful)
# Primary Instance (192.168.0.48:52095): OK
# Secondary Instance (localhost:52095): OK
# Fallback Configuration: ENABLED
# Queue File: NOT FOUND
# ===== All systems operational - ready for production =====
```

**If health check fails**:
- Primary down → Fix VPN or restart primary
- Secondary down → Check batch file output for errors
- See Troubleshooting section

### Step 3.5: Create Integration Test Magnet

Add a test magnet to both instances to verify they're independent:

**Primary (https://192.168.0.48:52095/)**:
- Add test magnet link
- Verify it appears in primary list
- Should NOT appear in secondary

**Secondary (http://localhost:52095/)**:
- Add different test magnet
- Verify it appears in secondary list
- Should NOT appear in primary

**Purpose**: Ensures instances are truly separate (no sync between them)

---

## Deployment Phase 4: Testing

### Step 4.1: Run Quick Failover Test (Recommended First)

```powershell
# Run safe test suite (no VPN manipulation)
python test_failover.py --quick

# Expected: All tests pass
# Duration: ~10 minutes
# Tests: Normal operation, fallback, queue processing
```

**What tests verify**:
- Test 1: Primary accepts magnets (normal operation)
- Test 3: Fallback to secondary works
- Test 5: Queue file processing works

### Step 4.2: Run Full Failover Test (Optional but Recommended)

```powershell
# Run comprehensive test suite
python test_failover.py

# Expected: All 5 tests pass
# Duration: ~20 minutes
# Tests: All scenarios including VPN disconnect
```

**What tests verify**:
- Test 1: Primary normal (5 magnets)
- Test 2: Primary fails → Secondary (3 magnets, requires VPN disconnect)
- Test 3: Manual failover (1 magnet via firewall)
- Test 4: Both down → Queue (3 magnets)
- Test 5: Queue recovery (3 magnets from queue)

### Step 4.3: Document Test Results

```powershell
# Fill out test report
# Edit: FAILOVER_TEST_REPORT_TEMPLATE.md

# Record:
# - Date and time of test
# - All test results (pass/fail)
# - Any observations or warnings
# - Performance metrics if available
# - Recommended next steps
```

---

## Deployment Phase 5: Integration with Workflow

### Step 5.1: Verify Phase 5 Integration

```powershell
# Run workflow with verbose logging
python execute_full_workflow.py

# Watch for Phase 5 output:
# "Checking qBittorrent connectivity..."
# "Primary instance health check: OK"
# "Using primary instance"
# "Successfully added X magnets to qBittorrent"
```

**Expected**: Phase 5 completes without errors

### Step 5.2: Simulate VPN Disconnect (Optional Test)

1. **Disconnect VPN** (or block primary IP with firewall)
2. **Run Phase 5 again**:
   ```powershell
   # Run workflow
   python execute_full_workflow.py

   # Watch for Phase 5 output:
   # "Primary instance health check: FAIL"
   # "Secondary instance health check: OK"
   # "Using secondary instance"
   # "Successfully added X magnets to secondary"
   ```
3. **Reconnect VPN**
4. **Verify**: Magnets appear in secondary instance list

**Purpose**: Proves automatic failover works in real workflow

### Step 5.3: Verify Separate Download Folders

After test runs:
- **Primary downloads** (F:\Audiobookshelf\Books\) - Contains primary's downloads
- **Secondary downloads** (C:\qbittorrent_secondary\downloads\) - Contains secondary's downloads
- **No overlap** - Each instance's downloads in separate folder

---

## Deployment Phase 6: Production Readiness

### Step 6.1: Final System Verification

```powershell
# Check all critical systems
Write-Host "=== FINAL PRODUCTION READINESS CHECK ===" -ForegroundColor Green
Write-Host ""

# 1. Primary instance
Write-Host "1. Primary Instance:" -ForegroundColor Cyan
curl -s -k https://192.168.0.48:52095/ | Select-String -Pattern "<!DOCTYPE" | Out-Null
if ($?) { Write-Host "   ✓ Responding" } else { Write-Host "   ✗ Not responding" }

# 2. Secondary instance
Write-Host "2. Secondary Instance:" -ForegroundColor Cyan
curl -s http://localhost:52095/ | Select-String -Pattern "<!DOCTYPE" | Out-Null
if ($?) { Write-Host "   ✓ Responding" } else { Write-Host "   ✗ Not responding" }

# 3. VPN connectivity
Write-Host "3. VPN Connectivity:" -ForegroundColor Cyan
ping -n 1 192.168.0.1 | Select-String -Pattern "Reply" | Out-Null
if ($?) { Write-Host "   ✓ VPN Connected" } else { Write-Host "   ✗ VPN Not Connected" }

# 4. Health check
Write-Host "4. Health Check:" -ForegroundColor Cyan
python monitor_qbittorrent_health.py | Select-String -Pattern "operational"
```

### Step 6.2: Backup Current Configuration

```powershell
# Backup .env file
Copy-Item ".env" ".env.backup.2025-11-28"

# Backup secondary config
Copy-Item "qbittorrent_secondary_config.ini" "qbittorrent_secondary_config.ini.backup.2025-11-28"

Write-Host "Backups created - can restore if needed"
```

### Step 6.3: Stop Secondary Instance (Ready State)

```powershell
# Stop secondary instance
Get-Process qbittorrent | Where-Object {$_.CommandLine -match "profile"} | Stop-Process -Force

# Or manually: Close the command window running secondary

Write-Host "Secondary instance stopped - ready for daily startup"
```

---

## Daily Operations Procedure

### Morning Checklist (Daily - 5 seconds)

```powershell
# Every morning before running workflow
python monitor_qbittorrent_health.py
```

**Expected**:
```
✓ VPN Status: CONNECTED
✓ Primary Instance: OK
✓ Secondary Instance: OK (if running)
```

If any fail:
1. Check VPN connection
2. Verify primary is running (should always be)
3. Start secondary if needed: `C:\qbittorrent_secondary\start_secondary.bat`

### Before Running Workflow

```powershell
# 1. Verify health (5 sec)
python monitor_qbittorrent_health.py

# 2. Start secondary if needed
C:\qbittorrent_secondary\start_secondary.bat

# 3. Run workflow
python execute_full_workflow.py
```

### After Workflow Completes

```powershell
# 1. Stop secondary instance
Get-Process qbittorrent | Where-Object {$_.CommandLine -match "profile"} | Stop-Process -Force

# 2. Verify downloads
dir C:\qbittorrent_secondary\downloads

# 3. Check logs if needed
Get-Content "C:\qbittorrent_secondary\profile\qBittorrent\logs\*" -Tail 20
```

---

## Troubleshooting Quick Reference

### Secondary won't start
- Check C:\qbittorrent_secondary\ exists
- Run batch file as Administrator
- Check port 52095 not in use: `netstat -ano | findstr 52095`

### Health check fails
- Verify VPN is connected: `ping 192.168.0.1`
- Check primary: `curl https://192.168.0.48:52095/`
- Check secondary: `curl http://localhost:52095/`

### Failover not working
- Verify QBITTORRENT_SECONDARY_URL in .env
- Check secondary instance is running
- Verify credentials match between instances

### Downloads go to wrong folder
- Primary: F:\Audiobookshelf\Books\
- Secondary: C:\qbittorrent_secondary\downloads\
- Check qBittorrent.conf download_path setting

---

## Sign-Off & Approval

**Deployment Verification**:
- [ ] All pre-deployment requirements met
- [ ] Setup script completed successfully
- [ ] Secondary instance starts correctly
- [ ] Health check shows all systems operational
- [ ] Quick test passed (or full test passed)
- [ ] Integration test completed successfully
- [ ] Backup of configuration created
- [ ] Daily operations procedure understood

**System Ready for Production**:
- [ ] Primary instance operational
- [ ] Secondary instance operational
- [ ] Failover logic verified
- [ ] Queue processing verified
- [ ] Documentation reviewed
- [ ] Troubleshooting guides available
- [ ] Rollback procedure understood

**Approval**:
- **Deployed By**: _________________ (Name)
- **Date**: _________________ (Date)
- **System Status**: [ ] Ready for Production [ ] Needs More Testing [ ] Requires Fixes

---

## What Happens Now

### Automated
- VPN monitoring runs continuously (every qBittorrent request)
- Health checks happen automatically before each download attempt
- Failover is transparent (no manual intervention)
- Queue processing happens automatically on recovery

### Manual (Required)
- Start secondary before each workflow run: `C:\qbittorrent_secondary\start_secondary.bat`
- Daily health check: `python monitor_qbittorrent_health.py`
- Stop secondary after workflow completes
- Monthly full test: `python test_failover.py --quick`

---

## Documentation Index

| Document | Purpose | When to Read |
|----------|---------|--------------|
| `VPN_RESILIENT_DEPLOYMENT_GUIDE.md` | Master guide | Before deployment |
| `SECONDARY_QBITTORRENT_SETUP.md` | Manual setup | If automated fails |
| `FAILOVER_TESTING_PROCEDURES.md` | Test procedures | Before testing |
| `SECONDARY_QUICK_REFERENCE.md` | Daily operations | Every day before workflow |
| `SECONDARY_DEPLOYMENT_CHECKLIST.md` | Verification | During deployment |
| `FRANK_SERVICES_DIAGNOSIS.md` | Frank service issue | Optional, for Frank restart |

---

## Success Indicators

**If everything is working correctly, you will see**:

1. ✅ Health check shows both instances OK
2. ✅ Workflow Phase 5 completes without errors
3. ✅ Magnets appear in qBittorrent WebUI
4. ✅ Downloads continue even if VPN drops
5. ✅ Queue file auto-processes on recovery
6. ✅ No manual failover intervention needed
7. ✅ Daily operations take only 5-10 minutes

---

**Deployment Complete! System is production-ready.** 🚀

For questions, refer to appropriate document or see Troubleshooting section.
