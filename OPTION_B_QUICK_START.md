# Option B - Quick Start Guide

## What You Need To Do (3 Steps)

### Step 1: Change ProtonVPN Split Tunneling Mode

**Current:** "Include only selected apps" ❌
**Change to:** "Exclude selected apps from VPN tunnel" ✅

1. ProtonVPN → Settings → Advanced → Split Tunneling
2. Change radio button to: **"Exclude selected apps from VPN tunnel"**
3. Click **"Add Application"**
4. Browse to: `C:\Users\dogma\Projects\MAMcrawler\venv\Scripts\python.exe`
5. Add it to the excluded apps list
6. Save settings

### Step 2: Restart ProtonVPN

1. Disconnect from server
2. Right-click tray icon → **Exit**
3. Wait 10 seconds
4. Start ProtonVPN
5. **Connect to a server**

### Step 3: Verify Setup

```cmd
python verify_option_b.py
```

**Expected:**
```
✅ SUCCESS - Two different routes detected!
  System Python IP: [VPN IP] (via VPN)
  venv Python IP:   [Your ISP IP] (direct WAN)
```

---

## What This Does

```
System Python (C:\Program Files\Python311\python.exe)
  ↓
  NOT excluded from VPN
  ↓
  All traffic → ProtonVPN → Goodreads
  ↓
  Appears as: VPN IP (Germany/US/etc)

venv Python (.\venv\Scripts\python.exe)
  ↓
  Excluded from VPN
  ↓
  All traffic → Direct WAN → Goodreads
  ↓
  Appears as: Your ISP IP
```

**Result:** Goodreads sees two completely different users!

---

## Run Dual Scraper

After verification passes:

```cmd
python run_dual_scraper.py
```

This will:
1. Launch VPN scraper with system Python
2. Launch direct scraper with venv Python
3. Both run simultaneously
4. Merge and deduplicate results
5. Save to `merged_results_[timestamp].json`

---

## Files Created

- `scraper_vpn.py` - VPN route scraper
- `scraper_direct.py` - Direct route scraper
- `run_dual_scraper.py` - Orchestrator
- `verify_option_b.py` - Setup verification
- `OPTION_B_SETUP.md` - Detailed guide
- `OPTION_B_QUICK_START.md` - This file

---

## Current Status

**You are here:** Need to change Split Tunneling mode to "Exclude"

**Next:** Follow Step 1 above
