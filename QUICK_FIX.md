# QUICK FIX - Enable ProtonVPN Split Tunneling

## Diagnosis Complete ✅

**Status:**
- ✅ ProtonVPN is RUNNING (2 processes detected)
- ✅ Found 4 Python installations
- ❌ Split Tunneling is NOT enabled (no SOCKS5 proxy detected)

**Root Cause:** Split Tunneling is disabled, so ProtonVPN is not exposing a local SOCKS5 proxy.

---

## 5-Minute Fix

### Step 1: Open ProtonVPN Settings
1. Look for ProtonVPN in your system tray (bottom-right)
2. Right-click the ProtonVPN icon
3. Click **Settings** or open the main window and click the gear icon (⚙️)

### Step 2: Navigate to Split Tunneling
1. In Settings, go to **Advanced** tab
2. Scroll down to **Split Tunneling** section
3. Click to **ENABLE** Split Tunneling

### Step 3: Configure Split Tunneling Mode
1. Select the mode: **"Include only selected apps in VPN tunnel"**
   - ⚠️ Important: NOT "Exclude" mode, but "Include" mode
2. This will create a local SOCKS5 proxy for selected apps

### Step 4: Add Python Executables
Click **"Add Application"** or **"+"** button and add these paths:

**Your Python installations (add ALL of these):**
```
C:\Users\dogma\Projects\MAMcrawler\venv\Scripts\python.exe
C:\Program Files\Python311\python.exe
C:\Users\dogma\AppData\Local\Programs\Python\Python312\python.exe
```

**How to add:**
- Method 1: Click "Browse" and navigate to each path
- Method 2: Paste the path directly if there's a text field
- Method 3: Look for "Add by path" option

### Step 5: Optional - Disable Kill Switch
1. Go to **Connection** tab in Settings
2. Find **Kill Switch** option
3. Either:
   - Disable it completely, OR
   - Set to "Software only" mode
4. This prevents VPN from blocking your direct WAN scraper

### Step 6: Restart ProtonVPN
1. Disconnect from VPN server
2. Close ProtonVPN completely (right-click system tray → Exit)
3. Wait 10 seconds
4. Start ProtonVPN again
5. Connect to a VPN server

### Step 7: Verify Setup
Run the diagnostic again:
```cmd
python protonvpn_diagnostic.py
```

**Expected output:**
```
✅ ProtonVPN is RUNNING
✅ Found proxy port: 8080 (or 1080)
✅ WORKING! External IP: [VPN IP address]
🎉 SUCCESS - ProtonVPN SOCKS5 Proxy is Working!
```

---

## Still Not Working?

### Check ProtonVPN Version
1. Settings → Help → About
2. Note the version number

**If version < 3.0:**
- Split Tunneling may not be supported
- Update ProtonVPN to latest version

### Alternative: Check ProtonVPN Documentation
1. Open ProtonVPN
2. Help → Support → Search "Split Tunneling"
3. Follow their official guide for your version

### Manual Port Check
Run this in Command Prompt:
```cmd
netstat -ano | findstr "LISTENING" | findstr "127.0.0.1"
```

Look for ports like: 1080, 8080, 54674, 62410

If you see a port, note the number and update `dual_goodreads_scraper.py`:
```python
# Line 267, change ports_to_check
ports_to_check = [YOUR_PORT_HERE, 8080, 1080]
```

---

## After Fix - Run Your Scraper

Once the diagnostic shows "SUCCESS", run your dual scraper:

```cmd
python dual_goodreads_scraper.py
```

**Expected behavior:**
- VPN scraper will use ProtonVPN SOCKS5 proxy (appears as VPN IP)
- Direct scraper will use your normal internet (appears as your ISP IP)
- Both scrapers run simultaneously with different fingerprints
- Results are merged and deduplicated

---

## Why This Matters

**Without Split Tunneling:**
- Both scrapers use your direct IP
- Goodreads sees two sessions from same IP = suspicious
- Higher chance of rate limiting or blocking

**With Split Tunneling:**
- VPN scraper → VPN IP (appears as different location/ISP)
- Direct scraper → Your real IP
- Goodreads sees two completely different users
- Lower detection risk, better scraping success

---

## Summary Checklist

- [ ] Open ProtonVPN Settings → Advanced
- [ ] Enable Split Tunneling
- [ ] Select "Include only selected apps" mode
- [ ] Add all 3 Python paths to Included Apps
- [ ] (Optional) Disable Kill Switch
- [ ] Restart ProtonVPN and reconnect
- [ ] Run `python protonvpn_diagnostic.py`
- [ ] Verify "SUCCESS" message
- [ ] Run `python dual_goodreads_scraper.py`

**Time estimate: 5-10 minutes**
