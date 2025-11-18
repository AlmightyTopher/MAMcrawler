# ProtonVPN SOCKS5 Proxy Setup Guide

## Current Status
✅ ProtonVPN is RUNNING (verified processes)
❌ SOCKS5 proxy is NOT listening (no proxy port detected)

## Problem
Split Tunneling is either disabled or not configured correctly.

## Step-by-Step Fix

### Step 1: Enable Split Tunneling in ProtonVPN

1. **Open ProtonVPN** (already running)
2. Click **Settings** (gear icon in top-right)
3. Navigate to **Advanced** section
4. Find **Split Tunneling** section
5. Enable **Split Tunneling**
6. Select **"Include only selected apps in VPN tunnel"** mode
7. Click **Add Application**

### Step 2: Add Python to Included Apps

You need to add your Python executable to the "Included Apps" list.

**Find your Python path:**
```cmd
where python
```

Common Python paths:
- `C:\Users\dogma\Projects\MAMcrawler\venv\Scripts\python.exe` (your virtual env)
- `C:\Python312\python.exe`
- `C:\Program Files\Python312\python.exe`
- `C:\Users\dogma\AppData\Local\Programs\Python\Python312\python.exe`

**Add BOTH of these:**
1. Your system Python (`where python`)
2. Your venv Python (`C:\Users\dogma\Projects\MAMcrawler\venv\Scripts\python.exe`)

### Step 3: Verify SOCKS5 Proxy Port

After enabling Split Tunneling, ProtonVPN creates a local SOCKS5 proxy.

**Modern ProtonVPN versions use different ports:**
- **Version 3.x**: Port `1080` (classic SOCKS5)
- **Version 4.x**: Port `8080` or dynamic port
- **Custom installations**: May use `62410`, `54674`, etc.

**To find your proxy port:**
1. In ProtonVPN Settings → Advanced → Split Tunneling
2. Look for "Local Proxy Port" or "SOCKS5 Port" setting
3. Note the port number

### Step 4: Disable Kill Switch (Optional but Recommended)

Kill Switch can interfere with Split Tunneling:

1. ProtonVPN Settings → Connection
2. Disable **Kill Switch** (or set to "Software only")
3. This prevents VPN from blocking direct connections

### Step 5: Verify Setup

Run the diagnostic script (see below) to verify:
```cmd
python protonvpn_diagnostic.py
```

## Expected Result

After proper setup, you should see:
```
✅ ProtonVPN is running
✅ SOCKS5 proxy detected: socks5://127.0.0.1:PORT
✅ Proxy is functional (can make requests)
✅ External IP via VPN: [VPN IP address]
```

## Troubleshooting

### "No proxy port detected"
- **Restart ProtonVPN** after enabling Split Tunneling
- Check that Python is in "Included Apps" list
- Verify Split Tunneling mode is "Include only selected apps"

### "Proxy test failed"
- Try installing `pysocks` library: `pip install pysocks`
- Check Windows Firewall isn't blocking localhost connections
- Verify ProtonVPN is actually connected to a server

### "Wrong external IP"
- Make sure you selected "Include only selected apps" mode (not Exclude)
- Verify Python executable path is correct
- Restart ProtonVPN and reconnect

## ProtonVPN Version Info

To check your ProtonVPN version:
1. Open ProtonVPN
2. Settings → Help → About
3. Note the version number

**Version-specific notes:**
- **v4.3.x+**: Uses port `8080` by default
- **v3.x**: Uses port `1080` by default
- **v2.x**: No Split Tunneling support (upgrade required)

## Next Steps

1. Follow Steps 1-4 above
2. Run `python protonvpn_diagnostic.py` to verify
3. If proxy detected, run `python dual_goodreads_scraper.py`
4. Check logs for "✅ Detected ProtonVPN SOCKS5 proxy"
