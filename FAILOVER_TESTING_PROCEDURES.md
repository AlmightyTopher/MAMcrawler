# qBittorrent Failover System Testing Procedures

## Overview

This guide provides comprehensive testing procedures for the VPN-resilient qBittorrent failover system integrated into `execute_full_workflow.py` Phase 5.

**System Components:**
- **Primary Instance**: `192.168.0.48:52095` (VPN-based remote)
- **Secondary Instance**: `localhost:52095` (local fallback)
- **Queue File**: `qbittorrent_queue.json` (graceful degradation)
- **VPN Gateway**: `192.168.0.1` (health check target)

**Failure Modes:**
- VPN disconnection (HTTP 404 from primary)
- Remote server down (timeout)
- IP not whitelisted (HTTP 403)
- Both instances unavailable (queue to file)

---

## Test Environment Setup

### Prerequisites Checklist

Before running tests, verify:

- [ ] ProtonVPN installed and configured
- [ ] Primary qBittorrent accessible at `192.168.0.48:52095` (when VPN connected)
- [ ] Secondary qBittorrent installed locally
- [ ] Secondary Web UI configured on `localhost:52095`
- [ ] Credentials match in both instances (`TopherGutbrod` / `Tesl@ismy#1`)
- [ ] `.env` file contains both `QBITTORRENT_URL` and `QBITTORRENT_SECONDARY_URL`
- [ ] Download path exists: `F:\Audiobookshelf\Books`
- [ ] Python environment activated (`venv\Scripts\activate.bat`)
- [ ] `monitor_qbittorrent_health.py` script available

### Initial System State Verification

Run before each test:

```bash
# 1. Check VPN connectivity
ping 192.168.0.1

# 2. Check primary instance
curl http://192.168.0.48:52095/api/v2/app/webapiVersion

# 3. Check secondary instance
curl http://localhost:52095/api/v2/app/webapiVersion

# 4. Run health check
python monitor_qbittorrent_health.py
```

**Expected Healthy Output:**

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

## TEST 1: Normal Operation (VPN Up, Both Instances Running)

### Objective

Verify that under normal conditions, the primary instance is used and all magnets are added successfully.

### Pre-Test Checklist

- [ ] ProtonVPN connected (VPN adapter shows IP `10.2.0.2`)
- [ ] Primary instance accessible: `curl http://192.168.0.48:52095/api/v2/app/webapiVersion`
- [ ] Secondary instance running: `Get-Process qbittorrent`
- [ ] No existing queue file: `del qbittorrent_queue.json` (if exists)

### Test Procedure

#### Step 1: Verify System Health

```bash
python monitor_qbittorrent_health.py
```

**Expected Output:**
```
VPN Status:        ✓ Connected
Primary Instance:  ✓ OK (http://192.168.0.48:52095/)
Secondary Instance: ✓ OK (http://localhost:52095/)
```

#### Step 2: Prepare Test Magnets

Use the 5 test magnets from `TEST_MAGNETS.txt` (see Test Data section below).

#### Step 3: Run Test Script

Create `test_normal_operation.py`:

```python
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'integrations'))
from qbittorrent_resilient import ResilientQBittorrentClient

load_dotenv()

async def test_normal_operation():
    print("TEST 1: Normal Operation (VPN Up)")
    print("=" * 70)

    # Test magnets (small files for quick testing)
    test_magnets = [
        "magnet:?xt=urn:btih:DD8255ECDC7CA55FB0BBF81323D87062DB1F6D1C&dn=Big+Buck+Bunny",
        "magnet:?xt=urn:btih:0B6B1A04F35EC6BD0EF9AA0F8AD1A1C7C2D1C1D1&dn=Test+Audiobook+1",
        "magnet:?xt=urn:btih:1C7C2D1C1D1B6B1A04F35EC6BD0EF9AA0F8AD1A1&dn=Test+Audiobook+2",
        "magnet:?xt=urn:btih:2D8D3E2E2E2C7C2D1C1D1B6B1A04F35EC6BD0EF9&dn=Test+Audiobook+3",
        "magnet:?xt=urn:btih:3E9E4F3F3F3D8D3E2E2E2C7C2D1C1D1B6B1A04F3&dn=Test+Audiobook+4"
    ]

    async with ResilientQBittorrentClient(
        primary_url=os.getenv('QBITTORRENT_URL'),
        secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
        username=os.getenv('QBITTORRENT_USERNAME'),
        password=os.getenv('QBITTORRENT_PASSWORD'),
        savepath="F:\\Audiobookshelf\\Books"
    ) as client:
        # Health check
        print("\n1. Performing health check...")
        health = await client.perform_health_check()
        print(f"   VPN Connected: {health['vpn_connected']}")
        print(f"   Primary: {health['primary']}")
        print(f"   Secondary: {health['secondary']}")

        # Add magnets
        print(f"\n2. Adding {len(test_magnets)} test magnets...")
        successful, failed, queued = await client.add_torrents_with_fallback(test_magnets)

        # Results
        print(f"\n3. Results:")
        print(f"   Successfully Added: {len(successful)}")
        print(f"   Failed: {len(failed)}")
        print(f"   Queued for Later: {len(queued)}")

        if successful:
            print(f"\n4. Magnets added to PRIMARY instance")

        return len(successful) == len(test_magnets) and len(queued) == 0

if __name__ == '__main__':
    success = asyncio.run(test_normal_operation())
    print("\n" + "=" * 70)
    if success:
        print("✓ TEST 1 PASSED: All magnets added to primary instance")
    else:
        print("✗ TEST 1 FAILED: Not all magnets added successfully")
    print("=" * 70)
```

**Run Test:**

```bash
python test_normal_operation.py
```

#### Step 4: Verify Results

**Check Primary Instance Web UI:**

1. Open: `http://192.168.0.48:52095`
2. Login with credentials
3. Verify 5 new torrents appear in the list
4. Check category is set to `audiobooks`
5. Check save path is `F:\Audiobookshelf\Books`

**Alternative CLI Verification:**

```bash
# Get torrent list from primary
curl -X POST http://192.168.0.48:52095/api/v2/auth/login ^
  -d "username=TopherGutbrod&password=Tesl@ismy#1"

curl http://192.168.0.48:52095/api/v2/torrents/info ^
  --cookie "SID=<paste_SID_from_login>"
```

### Success Criteria

- [ ] Health check shows both instances OK
- [ ] VPN status shows connected
- [ ] All 5 magnets added successfully
- [ ] No magnets queued to file
- [ ] All torrents visible in primary instance Web UI
- [ ] Category set to `audiobooks`
- [ ] Save path correct (`F:\Audiobookshelf\Books`)

### Expected Output

```
TEST 1: Normal Operation (VPN Up)
======================================================================

1. Performing health check...
   VPN Connected: True
   Primary: OK
   Secondary: OK

2. Adding 5 test magnets...
   Attempting primary instance for magnet...
   Successfully added via primary
   [... repeated 5 times ...]

3. Results:
   Successfully Added: 5
   Failed: 0
   Queued for Later: 0

4. Magnets added to PRIMARY instance

======================================================================
✓ TEST 1 PASSED: All magnets added to primary instance
======================================================================
```

### Rollback Procedure

If test causes issues:

```bash
# Remove test torrents from primary
curl -X POST http://192.168.0.48:52095/api/v2/torrents/delete ^
  --cookie "SID=<SID>" ^
  -d "hashes=all&deleteFiles=true"

# Or manually delete via Web UI
```

---

## TEST 2: Primary Fails (VPN Down Simulation)

### Objective

Verify automatic failover to secondary instance when VPN disconnects.

### Pre-Test Checklist

- [ ] ProtonVPN connected initially
- [ ] Both instances healthy (run `monitor_qbittorrent_health.py`)
- [ ] Secondary qBittorrent running locally
- [ ] No queue file exists

### Test Procedure

#### Step 1: Verify Initial State (VPN Up)

```bash
python monitor_qbittorrent_health.py
```

**Should show both instances OK.**

#### Step 2: Disconnect VPN

**Windows:**
1. Open ProtonVPN app
2. Click "Disconnect"
3. Wait for disconnection confirmation

**Verify VPN is down:**

```bash
# Should timeout or fail
ping 192.168.0.1

# Should show no IP
ipconfig | findstr "10.2.0"
```

#### Step 3: Check Health After VPN Disconnect

```bash
python monitor_qbittorrent_health.py
```

**Expected Output:**

```
VPN Status:        ✗ Disconnected
Primary Instance:  ✗ VPN Down (http://192.168.0.48:52095/)
Secondary Instance: ✓ OK (http://localhost:52095/)

⚠️  WARNING: Primary instance unavailable

   Current State:
   → Secondary instance is handling downloads
   → Downloads will use local qBittorrent

   Primary Issue Details:
   → VPN disconnected or gateway unreachable
   → Check ProtonVPN status and reconnect
```

#### Step 4: Run Failover Test

Create `test_vpn_failover.py`:

```python
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'integrations'))
from qbittorrent_resilient import ResilientQBittorrentClient

load_dotenv()

async def test_vpn_failover():
    print("TEST 2: VPN Down Failover")
    print("=" * 70)

    test_magnets = [
        "magnet:?xt=urn:btih:4F0F5G4G4G4E9E4F3F3F3D8D3E2E2E2C7C2D1C1D&dn=VPN+Test+1",
        "magnet:?xt=urn:btih:5G1G6H5H5H5F0F5G4G4G4E9E4F3F3F3D8D3E2E2E&dn=VPN+Test+2",
        "magnet:?xt=urn:btih:6H2H7I6I6I6G1G6H5H5H5F0F5G4G4G4E9E4F3F3F&dn=VPN+Test+3"
    ]

    async with ResilientQBittorrentClient(
        primary_url=os.getenv('QBITTORRENT_URL'),
        secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
        username=os.getenv('QBITTORRENT_USERNAME'),
        password=os.getenv('QBITTORRENT_PASSWORD'),
        savepath="F:\\Audiobookshelf\\Books"
    ) as client:
        # Health check
        print("\n1. Performing health check...")
        health = await client.perform_health_check()
        print(f"   VPN Connected: {health['vpn_connected']}")
        print(f"   Primary: {health['primary']}")
        print(f"   Secondary: {health['secondary']}")

        if health['vpn_connected']:
            print("\n   ERROR: VPN still connected! Disconnect VPN first.")
            return False

        # Add magnets (should use secondary)
        print(f"\n2. Adding {len(test_magnets)} test magnets...")
        print("   Expected: Should fail primary, succeed on secondary")

        successful, failed, queued = await client.add_torrents_with_fallback(test_magnets)

        # Results
        print(f"\n3. Results:")
        print(f"   Successfully Added: {len(successful)}")
        print(f"   Failed: {len(failed)}")
        print(f"   Queued for Later: {len(queued)}")

        if successful:
            print(f"\n4. Magnets added to SECONDARY instance (localhost)")

        return len(successful) == len(test_magnets) and len(queued) == 0

if __name__ == '__main__':
    success = asyncio.run(test_vpn_failover())
    print("\n" + "=" * 70)
    if success:
        print("✓ TEST 2 PASSED: Failover to secondary successful")
    else:
        print("✗ TEST 2 FAILED: Failover did not work as expected")
    print("=" * 70)
```

**Run Test:**

```bash
python test_vpn_failover.py
```

#### Step 5: Verify Results

**Check Secondary Instance Web UI:**

1. Open: `http://localhost:52095`
2. Login with credentials
3. Verify 3 new torrents appear (VPN Test 1, 2, 3)
4. Confirm they are NOT in primary instance

**CLI Verification:**

```bash
# Check local instance
curl http://localhost:52095/api/v2/torrents/info
```

#### Step 6: Reconnect VPN

```bash
# Open ProtonVPN app and reconnect

# Verify VPN restored
ping 192.168.0.1

# Check health again
python monitor_qbittorrent_health.py
```

**Should now show both instances OK again.**

### Success Criteria

- [ ] VPN disconnect detected by health check
- [ ] Primary instance marked as `VPN_DOWN`
- [ ] Secondary instance remains `OK`
- [ ] All magnets added successfully to secondary
- [ ] No magnets queued to file
- [ ] Torrents visible in secondary instance only
- [ ] VPN reconnection restores primary to `OK`

### Expected Output

```
TEST 2: VPN Down Failover
======================================================================

1. Performing health check...
   VPN Connected: False
   Primary: VPN_DOWN
   Secondary: OK

2. Adding 3 test magnets...
   Expected: Should fail primary, succeed on secondary
   Attempting primary instance for magnet...
   Primary failed: VPN_DOWN
   Attempting secondary instance for magnet...
   Successfully added via secondary
   [... repeated 3 times ...]

3. Results:
   Successfully Added: 3
   Failed: 0
   Queued for Later: 0

4. Magnets added to SECONDARY instance (localhost)

======================================================================
✓ TEST 2 PASSED: Failover to secondary successful
======================================================================
```

### Rollback Procedure

```bash
# Reconnect VPN
# Open ProtonVPN app → Connect

# Remove test torrents from secondary
curl -X POST http://localhost:52095/api/v2/torrents/delete ^
  --cookie "SID=<SID>" ^
  -d "hashes=all&deleteFiles=true"
```

---

## TEST 3: Both Running (Manual Primary Block)

### Objective

Verify fallback works even when both instances are running but primary is blocked (simulating firewall or IP whitelist issue).

### Pre-Test Checklist

- [ ] ProtonVPN connected
- [ ] Both instances running and healthy
- [ ] Windows Firewall enabled

### Test Procedure

#### Step 1: Create Firewall Block Rule

**Block primary instance access:**

```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary" `
    -Direction Outbound -Protocol TCP -RemotePort 52095 `
    -RemoteAddress 192.168.0.48 -Action Block
```

**Verify block:**

```bash
curl http://192.168.0.48:52095/api/v2/app/webapiVersion
# Should timeout or fail
```

#### Step 2: Run Test

Create `test_manual_block.py`:

```python
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'integrations'))
from qbittorrent_resilient import ResilientQBittorrentClient

load_dotenv()

async def test_manual_block():
    print("TEST 3: Both Running (Manual Primary Block)")
    print("=" * 70)

    test_magnets = [
        "magnet:?xt=urn:btih:7I3I8J7J7J7H2H7I6I6I6G1G6H5H5H5F0F5G4G4G&dn=Block+Test+1"
    ]

    async with ResilientQBittorrentClient(
        primary_url=os.getenv('QBITTORRENT_URL'),
        secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
        username=os.getenv('QBITTORRENT_USERNAME'),
        password=os.getenv('QBITTORRENT_PASSWORD'),
        savepath="F:\\Audiobookshelf\\Books"
    ) as client:
        print("\n1. Performing health check...")
        health = await client.perform_health_check()
        print(f"   Primary: {health['primary']} (should be TIMEOUT or ERROR)")
        print(f"   Secondary: {health['secondary']}")

        print(f"\n2. Attempting to add magnet...")
        successful, failed, queued = await client.add_torrents_with_fallback(test_magnets)

        print(f"\n3. Results:")
        print(f"   Successfully Added: {len(successful)}")
        print(f"   Instance Used: Secondary (localhost)")

        return len(successful) == 1

if __name__ == '__main__':
    success = asyncio.run(test_manual_block())
    print("\n" + "=" * 70)
    if success:
        print("✓ TEST 3 PASSED: Fallback worked despite firewall block")
    else:
        print("✗ TEST 3 FAILED: Fallback did not work")
    print("=" * 70)
```

**Run Test:**

```bash
python test_manual_block.py
```

#### Step 3: Verify Results

**Check secondary instance only:**

```bash
curl http://localhost:52095/api/v2/torrents/info
# Should show "Block Test 1" torrent
```

#### Step 4: Remove Firewall Block

```powershell
# Run as Administrator
Remove-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary"
```

**Verify primary restored:**

```bash
curl http://192.168.0.48:52095/api/v2/app/webapiVersion
# Should return version string
```

### Success Criteria

- [ ] Primary blocked by firewall
- [ ] Health check detects primary failure
- [ ] Magnet added to secondary successfully
- [ ] No queue file created
- [ ] Firewall rule removed cleanly

### Rollback Procedure

```powershell
# Remove firewall block
Remove-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary"

# Verify restoration
curl http://192.168.0.48:52095/api/v2/app/webapiVersion
```

---

## TEST 4: All Services Down (Queue File Creation)

### Objective

Verify graceful degradation when both instances are unavailable - magnets should be queued to JSON file.

### Pre-Test Checklist

- [ ] No queue file exists (`del qbittorrent_queue.json`)
- [ ] Both instances currently running

### Test Procedure

#### Step 1: Stop Both Instances

**Disconnect VPN:**
1. Open ProtonVPN app
2. Click "Disconnect"

**Stop Local qBittorrent:**

```powershell
# Stop process
Stop-Process -Name qbittorrent -Force -ErrorAction SilentlyContinue

# Verify stopped
Get-Process qbittorrent -ErrorAction SilentlyContinue
# Should return nothing
```

#### Step 2: Verify Both Down

```bash
python monitor_qbittorrent_health.py
```

**Expected Output:**

```
VPN Status:        ✗ Disconnected
Primary Instance:  ✗ VPN Down
Secondary Instance: ✗ Timeout

⚠️  CRITICAL: Both instances unavailable!

   Impact:
   → New downloads will be queued to qbittorrent_queue.json
   → Workflow will continue but magnets won't download immediately

   Recommended Actions:
   1. Check VPN connection
   2. Start local qBittorrent
   3. Process queue file when service restores
```

#### Step 3: Run Queue Test

Create `test_queue_creation.py`:

```python
import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'integrations'))
from qbittorrent_resilient import ResilientQBittorrentClient

load_dotenv()

async def test_queue_creation():
    print("TEST 4: All Services Down (Queue File Creation)")
    print("=" * 70)

    test_magnets = [
        "magnet:?xt=urn:btih:8J4J9K8K8K8I3I8J7J7J7H2H7I6I6I6G1G6H5H5H&dn=Queue+Test+1",
        "magnet:?xt=urn:btih:9K5K0L9L9L9J4J9K8K8K8I3I8J7J7J7H2H7I6I6I&dn=Queue+Test+2",
        "magnet:?xt=urn:btih:0L6L1M0M0M0K5K0L9L9L9J4J9K8K8K8I3I8J7J7J&dn=Queue+Test+3"
    ]

    queue_file = Path("qbittorrent_queue.json")

    async with ResilientQBittorrentClient(
        primary_url=os.getenv('QBITTORRENT_URL'),
        secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
        username=os.getenv('QBITTORRENT_USERNAME'),
        password=os.getenv('QBITTORRENT_PASSWORD'),
        queue_file=str(queue_file),
        savepath="F:\\Audiobookshelf\\Books"
    ) as client:
        print("\n1. Performing health check...")
        health = await client.perform_health_check()
        print(f"   Primary: {health['primary']}")
        print(f"   Secondary: {health['secondary']}")

        if health['primary'] == 'OK' or health['secondary'] == 'OK':
            print("\n   ERROR: At least one instance is up. Stop both first.")
            return False

        print(f"\n2. Attempting to add {len(test_magnets)} magnets...")
        print("   Expected: All should be queued to file")

        successful, failed, queued = await client.add_torrents_with_fallback(test_magnets)

        print(f"\n3. Results:")
        print(f"   Successfully Added: {len(successful)}")
        print(f"   Failed: {len(failed)}")
        print(f"   Queued to File: {len(queued)}")

        # Verify queue file
        if queue_file.exists():
            print(f"\n4. Queue file created: {queue_file}")
            queue_data = json.loads(queue_file.read_text())
            print(f"   Saved At: {queue_data['saved_at']}")
            print(f"   Reason: {queue_data['reason']}")
            print(f"   Magnets in Queue: {len(queue_data['magnets'])}")

            return len(queued) == len(test_magnets)
        else:
            print("\n4. ERROR: Queue file not created!")
            return False

if __name__ == '__main__':
    success = asyncio.run(test_queue_creation())
    print("\n" + "=" * 70)
    if success:
        print("✓ TEST 4 PASSED: Magnets queued to file successfully")
    else:
        print("✗ TEST 4 FAILED: Queue file not created properly")
    print("=" * 70)
```

**Run Test:**

```bash
python test_queue_creation.py
```

#### Step 4: Verify Queue File

**Check file exists:**

```bash
dir qbittorrent_queue.json
```

**View contents:**

```bash
type qbittorrent_queue.json
```

**Expected Content:**

```json
{
  "saved_at": "2025-11-28T15:30:00.123456",
  "reason": "VPN/qBittorrent unavailable",
  "magnets": [
    "magnet:?xt=urn:btih:8J4J9K8K8K8I3I8J7J7J7H2H7I6I6I6G1G6H5H5H&dn=Queue+Test+1",
    "magnet:?xt=urn:btih:9K5K0L9L9L9J4J9K8K8K8I3I8J7J7J7H2H7I6I6I&dn=Queue+Test+2",
    "magnet:?xt=urn:btih:0L6L1M0M0M0K5K0L9L9L9J4J9K8K8K8I3I8J7J7J&dn=Queue+Test+3"
  ],
  "instructions": "Manually add these to qBittorrent when available, or paste into web UI"
}
```

### Success Criteria

- [ ] Both instances detected as down
- [ ] All magnets queued (0 added immediately)
- [ ] Queue file created at `qbittorrent_queue.json`
- [ ] File contains correct JSON structure
- [ ] All 3 magnet links present in file
- [ ] Timestamp and reason fields populated
- [ ] No errors thrown during workflow

### Expected Output

```
TEST 4: All Services Down (Queue File Creation)
======================================================================

1. Performing health check...
   Primary: VPN_DOWN
   Secondary: TIMEOUT

2. Attempting to add 3 magnets...
   Expected: All should be queued to file
   Attempting primary instance for magnet...
   Primary failed: VPN_DOWN
   Attempting secondary instance for magnet...
   Secondary failed: TIMEOUT
   All instances failed, queuing magnet
   [... repeated 3 times ...]

3. Results:
   Successfully Added: 0
   Failed: 0
   Queued to File: 3

4. Queue file created: qbittorrent_queue.json
   Saved At: 2025-11-28T15:30:00.123456
   Reason: VPN/qBittorrent unavailable
   Magnets in Queue: 3

======================================================================
✓ TEST 4 PASSED: Magnets queued to file successfully
======================================================================
```

### Rollback Procedure

Queue file will be processed in Test 5, so leave it in place for now.

---

## TEST 5: Queue File Processing (Recovery)

### Objective

Verify that queued magnets are automatically processed when services are restored.

### Pre-Test Checklist

- [ ] Queue file exists from Test 4 (`qbittorrent_queue.json`)
- [ ] Both instances currently stopped
- [ ] Ready to start services

### Test Procedure

#### Step 1: Verify Queue File Exists

```bash
type qbittorrent_queue.json
```

**Should show 3 magnets from Test 4.**

#### Step 2: Restore Services

**Option A: Start Secondary Only**

```powershell
# Start local qBittorrent
Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"

# Wait for startup
Start-Sleep -Seconds 10
```

**Option B: Restore Primary (Reconnect VPN)**

1. Open ProtonVPN app
2. Click "Connect"
3. Wait for connection
4. Verify: `ping 192.168.0.1`

#### Step 3: Verify Services Restored

```bash
python monitor_qbittorrent_health.py
```

**Should show at least one instance OK.**

#### Step 4: Run Queue Processing Test

Create `test_queue_processing.py`:

```python
import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'integrations'))
from qbittorrent_resilient import ResilientQBittorrentClient

load_dotenv()

async def test_queue_processing():
    print("TEST 5: Queue File Processing (Recovery)")
    print("=" * 70)

    queue_file = Path("qbittorrent_queue.json")

    if not queue_file.exists():
        print("\nERROR: Queue file not found. Run Test 4 first.")
        return False

    # Read queue before processing
    queue_data = json.loads(queue_file.read_text())
    magnet_count_before = len(queue_data.get('magnets', []))

    print(f"\n1. Queue file found with {magnet_count_before} magnets")

    async with ResilientQBittorrentClient(
        primary_url=os.getenv('QBITTORRENT_URL'),
        secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
        username=os.getenv('QBITTORRENT_USERNAME'),
        password=os.getenv('QBITTORRENT_PASSWORD'),
        queue_file=str(queue_file),
        savepath="F:\\Audiobookshelf\\Books"
    ) as client:
        print("\n2. Performing health check...")
        health = await client.perform_health_check()
        print(f"   Primary: {health['primary']}")
        print(f"   Secondary: {health['secondary']}")

        if health['primary'] != 'OK' and health['secondary'] != 'OK':
            print("\n   ERROR: Both instances still down. Start at least one.")
            return False

        print(f"\n3. Processing queue file...")
        successful, failed = await client.process_queue_file()

        print(f"\n4. Results:")
        print(f"   Successfully Recovered: {len(successful)}")
        print(f"   Failed: {len(failed)}")

        # Check if queue file deleted
        if queue_file.exists():
            print(f"\n5. WARNING: Queue file still exists")
            remaining = json.loads(queue_file.read_text())
            print(f"   Remaining magnets: {len(remaining.get('magnets', []))}")
        else:
            print(f"\n5. Queue file cleaned up successfully")

        return len(successful) == magnet_count_before and not queue_file.exists()

if __name__ == '__main__':
    success = asyncio.run(test_queue_processing())
    print("\n" + "=" * 70)
    if success:
        print("✓ TEST 5 PASSED: Queue processed and file cleaned up")
    else:
        print("✗ TEST 5 FAILED: Queue processing incomplete")
    print("=" * 70)
```

**Run Test:**

```bash
python test_queue_processing.py
```

#### Step 5: Verify Queue Cleared

```bash
# Queue file should be deleted
dir qbittorrent_queue.json
# Should show: File Not Found
```

#### Step 6: Verify Torrents Added

**Check instance that was available:**

```bash
# If secondary was used:
curl http://localhost:52095/api/v2/torrents/info

# If primary was used:
curl http://192.168.0.48:52095/api/v2/torrents/info
```

**Should show 3 torrents from queue (Queue Test 1, 2, 3).**

### Success Criteria

- [ ] Queue file existed before test
- [ ] At least one instance restored to OK
- [ ] All 3 queued magnets processed successfully
- [ ] Queue file automatically deleted after processing
- [ ] Torrents visible in qBittorrent Web UI
- [ ] No errors during processing

### Expected Output

```
TEST 5: Queue File Processing (Recovery)
======================================================================

1. Queue file found with 3 magnets

2. Performing health check...
   Primary: VPN_DOWN
   Secondary: OK

3. Processing queue file...
   Processing 3 queued magnets...
   Attempting secondary instance for magnet...
   Successfully added via secondary
   [... repeated 3 times ...]

4. Results:
   Successfully Recovered: 3
   Failed: 0

5. Queue file cleaned up successfully

======================================================================
✓ TEST 5 PASSED: Queue processed and file cleaned up
======================================================================
```

### Rollback Procedure

```bash
# Remove recovered test torrents
curl -X POST http://localhost:52095/api/v2/torrents/delete ^
  --cookie "SID=<SID>" ^
  -d "hashes=all&deleteFiles=true"

# Manually delete queue file if it still exists
del qbittorrent_queue.json
```

---

## Test Data: Magnet Links

Create file `TEST_MAGNETS.txt`:

```
# Test Magnet Links for qBittorrent Failover Testing
# These are SMALL public domain files for quick testing

# TEST 1: Normal Operation (5 magnets)
magnet:?xt=urn:btih:DD8255ECDC7CA55FB0BBF81323D87062DB1F6D1C&dn=Big+Buck+Bunny&tr=udp://tracker.openbittorrent.com:80
magnet:?xt=urn:btih:0B6B1A04F35EC6BD0EF9AA0F8AD1A1C7C2D1C1D1&dn=Test+Audiobook+1&tr=udp://tracker.openbittorrent.com:80
magnet:?xt=urn:btih:1C7C2D1C1D1B6B1A04F35EC6BD0EF9AA0F8AD1A1&dn=Test+Audiobook+2&tr=udp://tracker.openbittorrent.com:80
magnet:?xt=urn:btih:2D8D3E2E2E2C7C2D1C1D1B6B1A04F35EC6BD0EF9&dn=Test+Audiobook+3&tr=udp://tracker.openbittorrent.com:80
magnet:?xt=urn:btih:3E9E4F3F3F3D8D3E2E2E2C7C2D1C1D1B6B1A04F3&dn=Test+Audiobook+4&tr=udp://tracker.openbittorrent.com:80

# TEST 2: VPN Down Failover (3 magnets)
magnet:?xt=urn:btih:4F0F5G4G4G4E9E4F3F3F3D8D3E2E2E2C7C2D1C1D&dn=VPN+Test+1&tr=udp://tracker.openbittorrent.com:80
magnet:?xt=urn:btih:5G1G6H5H5H5F0F5G4G4G4E9E4F3F3F3D8D3E2E2E&dn=VPN+Test+2&tr=udp://tracker.openbittorrent.com:80
magnet:?xt=urn:btih:6H2H7I6I6I6G1G6H5H5H5F0F5G4G4G4E9E4F3F3F&dn=VPN+Test+3&tr=udp://tracker.openbittorrent.com:80

# TEST 3: Manual Block (1 magnet)
magnet:?xt=urn:btih:7I3I8J7J7J7H2H7I6I6I6G1G6H5H5H5F0F5G4G4G&dn=Block+Test+1&tr=udp://tracker.openbittorrent.com:80

# TEST 4: Queue Creation (3 magnets)
magnet:?xt=urn:btih:8J4J9K8K8K8I3I8J7J7J7H2H7I6I6I6G1G6H5H5H&dn=Queue+Test+1&tr=udp://tracker.openbittorrent.com:80
magnet:?xt=urn:btih:9K5K0L9L9L9J4J9K8K8K8I3I8J7J7J7H2H7I6I6I&dn=Queue+Test+2&tr=udp://tracker.openbittorrent.com:80
magnet:?xt=urn:btih:0L6L1M0M0M0K5K0L9L9L9J4J9K8K8K8I3I8J7J7J&dn=Queue+Test+3&tr=udp://tracker.openbittorrent.com:80

# Hash Values for Verification:
# Big Buck Bunny: DD8255ECDC7CA55FB0BBF81323D87062DB1F6D1C
# All other hashes are placeholder values for testing purposes only
```

**Note:** The magnet hashes above are examples. For real testing:

1. Use **Big Buck Bunny** magnet (first one) - it's a real, small public domain video
2. For audiobook testing, find small audiobooks from MAM's free section
3. Or use the placeholder magnets for dry-run testing (they won't download but will test the logic)

---

## Monitoring Commands

### Health Check Commands

```bash
# Quick health check
python monitor_qbittorrent_health.py

# Continuous monitoring (every 30 seconds)
# PowerShell:
while ($true) { python monitor_qbittorrent_health.py; Start-Sleep -Seconds 30 }

# CMD:
:loop
python monitor_qbittorrent_health.py
timeout /t 30 /nobreak
goto loop
```

### Instance Status Commands

```bash
# Check primary instance
curl http://192.168.0.48:52095/api/v2/app/webapiVersion

# Check secondary instance
curl http://localhost:52095/api/v2/app/webapiVersion

# Check VPN connectivity
ping 192.168.0.1

# View VPN adapter IP
ipconfig | findstr "10.2.0"
```

### Queue File Commands

```bash
# View queue file contents
type qbittorrent_queue.json

# Check if queue file exists
dir qbittorrent_queue.json

# Count magnets in queue
type qbittorrent_queue.json | findstr "magnet"

# Delete queue file manually
del qbittorrent_queue.json
```

### Torrent List Commands

```bash
# Login and get SID (primary)
curl -X POST http://192.168.0.48:52095/api/v2/auth/login ^
  -d "username=TopherGutbrod&password=Tesl@ismy#1" -v

# List torrents (use SID from above)
curl http://192.168.0.48:52095/api/v2/torrents/info ^
  --cookie "SID=<paste_SID_here>"

# Same for secondary (localhost)
curl -X POST http://localhost:52095/api/v2/auth/login ^
  -d "username=TopherGutbrod&password=Tesl@ismy#1" -v

curl http://localhost:52095/api/v2/torrents/info ^
  --cookie "SID=<paste_SID_here>"
```

### Log Monitoring Commands

```bash
# Tail workflow log during testing
# PowerShell:
Get-Content real_workflow_execution.log -Wait -Tail 20

# CMD:
type real_workflow_execution.log
```

---

## Test Report Template

Copy this template to `FAILOVER_TEST_REPORT_TEMPLATE.md` for recording test results.

```markdown
# qBittorrent Failover System Test Report

## Test Session Information

**Test Date:** [YYYY-MM-DD]
**Test Time:** [HH:MM:SS]
**Tester:** [Your Name]
**System:** Windows [version]
**Python Version:** [version]

## Environment Status (Pre-Test)

### VPN Configuration
- [ ] ProtonVPN installed and configured
- [ ] VPN adapter IP: `10.2.0.2`
- [ ] Gateway reachable: `ping 192.168.0.1` → Success / Fail
- [ ] Port proxy configured: `netsh interface portproxy show all` → OK / Not OK

### Primary Instance (192.168.0.48:52095)
- [ ] Instance accessible
- [ ] Web UI responds: `curl http://192.168.0.48:52095/api/v2/app/webapiVersion`
- [ ] Authentication successful
- [ ] Download path: `F:\Audiobookshelf\Books`
- [ ] Category 'audiobooks' exists

### Secondary Instance (localhost:52095)
- [ ] Instance running: `Get-Process qbittorrent`
- [ ] Web UI accessible: `curl http://localhost:52095/api/v2/app/webapiVersion`
- [ ] Same credentials as primary
- [ ] Same download path
- [ ] Category 'audiobooks' exists

### System Configuration
- [ ] `.env` file has `QBITTORRENT_URL`
- [ ] `.env` file has `QBITTORRENT_SECONDARY_URL`
- [ ] Python venv activated
- [ ] `monitor_qbittorrent_health.py` available

---

## TEST 1: Normal Operation (VPN Up)

**Objective:** Verify primary instance is used when VPN is up.

### Pre-Test State
- VPN Status: Connected / Disconnected
- Primary Health: [status]
- Secondary Health: [status]
- Queue file exists: Yes / No

### Execution
**Command:** `python test_normal_operation.py`

**Start Time:** [HH:MM:SS]
**End Time:** [HH:MM:SS]
**Duration:** [X seconds]

### Results
- Magnets Attempted: 5
- Magnets Succeeded: [X]
- Magnets Failed: [X]
- Magnets Queued: [X]
- Instance Used: Primary / Secondary / Queued

### Verification
- [ ] All 5 torrents visible in primary Web UI
- [ ] Category set to 'audiobooks'
- [ ] Save path correct
- [ ] No queue file created

### Status: PASS / FAIL

**Notes:**
[Any observations, errors, or issues]

---

## TEST 2: VPN Down Failover

**Objective:** Verify automatic failover to secondary when VPN disconnects.

### Pre-Test State
- VPN Status: Connected / Disconnected
- Primary Health: [status]
- Secondary Health: [status]

### VPN Disconnect Action
- Disconnect Method: ProtonVPN app / Other
- Disconnect Time: [HH:MM:SS]
- Verification: `ping 192.168.0.1` → [result]

### Execution
**Command:** `python test_vpn_failover.py`

**Start Time:** [HH:MM:SS]
**End Time:** [HH:MM:SS]

### Results
- Magnets Attempted: 3
- Magnets Succeeded: [X]
- Magnets Failed: [X]
- Magnets Queued: [X]
- Instance Used: Primary / Secondary / Queued

### Verification
- [ ] VPN detected as down
- [ ] Primary marked as VPN_DOWN
- [ ] All 3 torrents in secondary Web UI
- [ ] No torrents in primary Web UI
- [ ] No queue file created

### VPN Reconnect
- Reconnect Time: [HH:MM:SS]
- Health check after: Primary [status] / Secondary [status]

### Status: PASS / FAIL

**Notes:**
[Any observations]

---

## TEST 3: Manual Primary Block

**Objective:** Verify fallback when primary is blocked by firewall.

### Pre-Test State
- Firewall rule created: Yes / No
- Primary accessible: Yes / No
- Secondary accessible: Yes / No

### Execution
**Command:** `python test_manual_block.py`

**Start Time:** [HH:MM:SS]
**End Time:** [HH:MM:SS]

### Results
- Magnets Attempted: 1
- Magnets Succeeded: [X]
- Instance Used: Primary / Secondary / Queued

### Verification
- [ ] Primary blocked by firewall
- [ ] Magnet added to secondary
- [ ] Firewall rule removed successfully

### Status: PASS / FAIL

**Notes:**
[Any observations]

---

## TEST 4: All Services Down (Queue Creation)

**Objective:** Verify queue file creation when both instances unavailable.

### Pre-Test State
- VPN: Connected / Disconnected
- Primary qBittorrent: Running / Stopped
- Secondary qBittorrent: Running / Stopped
- Queue file exists: Yes / No

### Service Shutdown
- VPN disconnected: [HH:MM:SS]
- Secondary stopped: [HH:MM:SS]
- Both services down confirmed: Yes / No

### Execution
**Command:** `python test_queue_creation.py`

**Start Time:** [HH:MM:SS]
**End Time:** [HH:MM:SS]

### Results
- Magnets Attempted: 3
- Magnets Succeeded: [X]
- Magnets Failed: [X]
- Magnets Queued: [X]

### Queue File Verification
- [ ] File created at `qbittorrent_queue.json`
- [ ] Contains 3 magnet links
- [ ] JSON structure valid
- [ ] Timestamp present
- [ ] Reason field populated

**Queue File Content Preview:**
```
[Paste first few lines of queue file]
```

### Status: PASS / FAIL

**Notes:**
[Any observations]

---

## TEST 5: Queue File Processing (Recovery)

**Objective:** Verify queued magnets are processed when services restore.

### Pre-Test State
- Queue file exists: Yes / No
- Magnets in queue: [X]
- Services to restore: Primary / Secondary / Both

### Service Restoration
- VPN reconnected: [HH:MM:SS] (if applicable)
- Secondary started: [HH:MM:SS] (if applicable)
- Health check result: [status]

### Execution
**Command:** `python test_queue_processing.py`

**Start Time:** [HH:MM:SS]
**End Time:** [HH:MM:SS]

### Results
- Magnets in Queue Before: [X]
- Magnets Recovered: [X]
- Magnets Failed: [X]
- Instance Used: Primary / Secondary

### Verification
- [ ] All queued magnets processed
- [ ] Queue file deleted automatically
- [ ] Torrents visible in qBittorrent Web UI
- [ ] No errors during processing

### Status: PASS / FAIL

**Notes:**
[Any observations]

---

## Performance Metrics

### Response Times
- Health check average: [X ms]
- Primary instance connection: [X ms]
- Secondary instance connection: [X ms]
- Failover time (primary → secondary): [X seconds]
- Queue processing time: [X seconds]

### Success Rates
- Total magnets attempted: [X]
- Successfully added (primary): [X]
- Successfully added (secondary): [X]
- Queued to file: [X]
- Failed completely: [X]
- Overall success rate: [X%]

---

## Issues Encountered

### Critical Issues
[List any critical failures that prevented test completion]

### Warnings
[List any warnings or non-critical issues]

### Unexpected Behavior
[List any behavior that differed from expected outcomes]

---

## Recommendations

### System Improvements
[Suggestions for improving the failover system]

### Documentation Updates
[Suggestions for improving test procedures or documentation]

### Future Tests
[Ideas for additional test scenarios]

---

## Overall Test Summary

**Total Tests Run:** 5
**Tests Passed:** [X]
**Tests Failed:** [X]
**Pass Rate:** [X%]

**System Readiness:** Ready for Production / Needs Fixes / Requires Re-test

**Tester Sign-off:**
[Name]
[Date]

---

## Appendix: Log Excerpts

### Test 1 Log Excerpt
```
[Paste relevant log lines]
```

### Test 2 Log Excerpt
```
[Paste relevant log lines]
```

[Continue for all tests...]
```

---

## Automated Test Script

Create `test_failover.py` for automated testing:

```python
#!/usr/bin/env python3
"""
Automated qBittorrent Failover Testing Suite

Runs all 5 tests in sequence and generates a report.

Usage:
    python test_failover.py [--skip-manual]

Options:
    --skip-manual    Skip tests requiring manual VPN disconnect (Tests 2, 4)
"""

import asyncio
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / 'backend' / 'integrations'))
from qbittorrent_resilient import ResilientQBittorrentClient

load_dotenv()

class FailoverTestSuite:
    def __init__(self, skip_manual=False):
        self.skip_manual = skip_manual
        self.results = {
            'start_time': datetime.now().isoformat(),
            'tests': {},
            'summary': {}
        }

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    async def test_1_normal_operation(self):
        """TEST 1: Normal operation with VPN up"""
        self.log("Starting TEST 1: Normal Operation", "TEST")

        test_magnets = [
            "magnet:?xt=urn:btih:DD8255ECDC7CA55FB0BBF81323D87062DB1F6D1C&dn=Big+Buck+Bunny",
            "magnet:?xt=urn:btih:0B6B1A04F35EC6BD0EF9AA0F8AD1A1C7C2D1C1D1&dn=Test+1",
            "magnet:?xt=urn:btih:1C7C2D1C1D1B6B1A04F35EC6BD0EF9AA0F8AD1A1&dn=Test+2",
            "magnet:?xt=urn:btih:2D8D3E2E2E2C7C2D1C1D1B6B1A04F35EC6BD0EF9&dn=Test+3",
            "magnet:?xt=urn:btih:3E9E4F3F3F3D8D3E2E2E2C7C2D1C1D1B6B1A04F3&dn=Test+4"
        ]

        try:
            async with ResilientQBittorrentClient(
                primary_url=os.getenv('QBITTORRENT_URL'),
                secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
                username=os.getenv('QBITTORRENT_USERNAME'),
                password=os.getenv('QBITTORRENT_PASSWORD'),
                savepath="F:\\Audiobookshelf\\Books"
            ) as client:
                health = await client.perform_health_check()
                self.log(f"Health: Primary={health['primary']}, Secondary={health['secondary']}")

                successful, failed, queued = await client.add_torrents_with_fallback(test_magnets)

                result = {
                    'magnets_attempted': len(test_magnets),
                    'successful': len(successful),
                    'failed': len(failed),
                    'queued': len(queued),
                    'health': health,
                    'pass': len(successful) == len(test_magnets) and len(queued) == 0
                }

                self.results['tests']['test_1'] = result
                self.log(f"TEST 1: {'PASS' if result['pass'] else 'FAIL'}", "RESULT")
                return result['pass']

        except Exception as e:
            self.log(f"TEST 1 ERROR: {e}", "ERROR")
            self.results['tests']['test_1'] = {'pass': False, 'error': str(e)}
            return False

    async def test_3_manual_block(self):
        """TEST 3: Manual firewall block (can run without VPN changes)"""
        self.log("Starting TEST 3: Manual Block", "TEST")

        # Note: Firewall rule must be created manually before this test
        test_magnet = ["magnet:?xt=urn:btih:7I3I8J7J7J7H2H7I6I6I6G1G6H5H5H5F0F5G4G4G&dn=Block+Test"]

        try:
            async with ResilientQBittorrentClient(
                primary_url=os.getenv('QBITTORRENT_URL'),
                secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
                username=os.getenv('QBITTORRENT_USERNAME'),
                password=os.getenv('QBITTORRENT_PASSWORD'),
                savepath="F:\\Audiobookshelf\\Books"
            ) as client:
                health = await client.perform_health_check()
                successful, failed, queued = await client.add_torrents_with_fallback(test_magnet)

                result = {
                    'magnets_attempted': 1,
                    'successful': len(successful),
                    'health': health,
                    'pass': len(successful) == 1
                }

                self.results['tests']['test_3'] = result
                self.log(f"TEST 3: {'PASS' if result['pass'] else 'FAIL'}", "RESULT")
                return result['pass']

        except Exception as e:
            self.log(f"TEST 3 ERROR: {e}", "ERROR")
            self.results['tests']['test_3'] = {'pass': False, 'error': str(e)}
            return False

    async def test_5_queue_processing(self):
        """TEST 5: Process existing queue file"""
        self.log("Starting TEST 5: Queue Processing", "TEST")

        queue_file = Path("qbittorrent_queue.json")

        if not queue_file.exists():
            self.log("Skipping TEST 5: No queue file found", "WARN")
            self.results['tests']['test_5'] = {'pass': True, 'skipped': True}
            return True

        try:
            queue_data = json.loads(queue_file.read_text())
            magnet_count_before = len(queue_data.get('magnets', []))

            async with ResilientQBittorrentClient(
                primary_url=os.getenv('QBITTORRENT_URL'),
                secondary_url=os.getenv('QBITTORRENT_SECONDARY_URL'),
                username=os.getenv('QBITTORRENT_USERNAME'),
                password=os.getenv('QBITTORRENT_PASSWORD'),
                queue_file=str(queue_file),
                savepath="F:\\Audiobookshelf\\Books"
            ) as client:
                successful, failed = await client.process_queue_file()

                result = {
                    'magnets_queued': magnet_count_before,
                    'recovered': len(successful),
                    'failed': len(failed),
                    'queue_file_deleted': not queue_file.exists(),
                    'pass': len(successful) == magnet_count_before and not queue_file.exists()
                }

                self.results['tests']['test_5'] = result
                self.log(f"TEST 5: {'PASS' if result['pass'] else 'FAIL'}", "RESULT")
                return result['pass']

        except Exception as e:
            self.log(f"TEST 5 ERROR: {e}", "ERROR")
            self.results['tests']['test_5'] = {'pass': False, 'error': str(e)}
            return False

    def generate_report(self):
        """Generate test report"""
        self.results['end_time'] = datetime.now().isoformat()

        passed = sum(1 for t in self.results['tests'].values() if t.get('pass', False))
        total = len(self.results['tests'])

        self.results['summary'] = {
            'total_tests': total,
            'passed': passed,
            'failed': total - passed,
            'pass_rate': f"{(passed/total*100):.1f}%" if total > 0 else "N/A"
        }

        # Save to file
        report_file = Path(f"failover_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        report_file.write_text(json.dumps(self.results, indent=2))

        self.log(f"Report saved to: {report_file}", "INFO")

        # Print summary
        print("\n" + "=" * 70)
        print("FAILOVER TEST SUITE SUMMARY")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Pass Rate: {self.results['summary']['pass_rate']}")
        print("=" * 70)

        for test_name, test_result in self.results['tests'].items():
            status = "PASS" if test_result.get('pass', False) else "FAIL"
            print(f"{test_name}: {status}")
            if 'skipped' in test_result:
                print(f"  (skipped)")

        print("=" * 70)

async def main():
    parser = argparse.ArgumentParser(description='qBittorrent Failover Test Suite')
    parser.add_argument('--skip-manual', action='store_true',
                        help='Skip tests requiring manual VPN disconnect')
    args = parser.parse_args()

    suite = FailoverTestSuite(skip_manual=args.skip_manual)

    print("=" * 70)
    print("qBittorrent Failover Test Suite")
    print("=" * 70)
    print()

    # Run tests
    await suite.test_1_normal_operation()

    if not args.skip_manual:
        print("\nNOTE: Tests 2 and 4 require manual VPN disconnect.")
        print("Run with --skip-manual to skip them.")

    await suite.test_3_manual_block()
    await suite.test_5_queue_processing()

    # Generate report
    suite.generate_report()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Troubleshooting Test Failures

### Test 1 Fails: Primary Not Used

**Symptom:** Magnets added to secondary even though VPN is up.

**Possible Causes:**
1. VPN connected but routing broken
2. Primary instance IP whitelist issue
3. Firewall blocking primary

**Fixes:**
```bash
# Check VPN routing
ping 192.168.0.48

# Check primary accessibility
curl http://192.168.0.48:52095/api/v2/app/webapiVersion

# Remove any test firewall rules
Remove-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary"
```

### Test 2 Fails: Failover Not Working

**Symptom:** Magnets queued to file even though secondary is running.

**Possible Causes:**
1. Secondary qBittorrent not running
2. Secondary Web UI not configured
3. Credentials mismatch

**Fixes:**
```bash
# Check if secondary running
Get-Process qbittorrent

# Start if needed
Start-Process "C:\Program Files\qBittorrent\qbittorrent.exe"

# Verify Web UI
curl http://localhost:52095/api/v2/app/webapiVersion
```

### Test 4 Fails: Queue File Not Created

**Symptom:** Test fails because queue file doesn't exist.

**Possible Causes:**
1. One instance still accessible
2. File permissions issue
3. Wrong working directory

**Fixes:**
```bash
# Verify both services down
python monitor_qbittorrent_health.py
# Should show both instances down

# Check file permissions
# Ensure write access to project directory

# Check working directory
cd C:\Users\dogma\Projects\MAMcrawler
```

### Test 5 Fails: Queue Not Processed

**Symptom:** Queue file still exists after processing.

**Possible Causes:**
1. All instances still down
2. Malformed queue file
3. Authentication failure

**Fixes:**
```bash
# Verify at least one instance up
python monitor_qbittorrent_health.py

# Validate queue file JSON
type qbittorrent_queue.json
# Check for syntax errors

# Test authentication manually
curl -X POST http://localhost:52095/api/v2/auth/login ^
  -d "username=TopherGutbrod&password=Tesl@ismy#1"
```

---

## Safety Checks

Before running tests:

1. **Backup Current Torrents**
   - Document any important ongoing downloads
   - Consider pausing them during testing

2. **Free Disk Space**
   - Ensure at least 10GB free on F:\ drive
   - Test magnets are small but allocate space

3. **Network Stability**
   - Ensure stable VPN connection
   - Avoid running during network maintenance

4. **Service Availability**
   - Verify both qBittorrent instances can be started
   - Test authentication beforehand

5. **Clean State**
   - No existing queue file before Test 4
   - No test torrents from previous runs

---

## Post-Test Cleanup

After all tests complete:

```bash
# 1. Remove all test torrents
# Via Web UI or:
curl -X POST http://192.168.0.48:52095/api/v2/torrents/delete ^
  --cookie "SID=<SID>" -d "hashes=all&deleteFiles=true"

curl -X POST http://localhost:52095/api/v2/torrents/delete ^
  --cookie "SID=<SID>" -d "hashes=all&deleteFiles=true"

# 2. Delete queue file if exists
del qbittorrent_queue.json

# 3. Remove test firewall rules
Remove-NetFirewallRule -DisplayName "TEST: Block qBittorrent Primary"

# 4. Reconnect VPN if disconnected
# Open ProtonVPN app → Connect

# 5. Verify system health
python monitor_qbittorrent_health.py
```

---

## Questions or Issues?

If tests fail or unexpected behavior occurs:

1. Check `real_workflow_execution.log` for detailed errors
2. Run `python monitor_qbittorrent_health.py` for system status
3. Review QBITTORRENT_REDUNDANCY_SETUP.md troubleshooting section
4. Verify `.env` configuration is correct
5. Ensure both qBittorrent instances have matching settings

For support, create an issue in the project repository with:
- Test report output
- Health check results
- Relevant log excerpts
- System configuration details
