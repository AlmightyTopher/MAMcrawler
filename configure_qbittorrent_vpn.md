# Configure qBittorrent for VPN Proxy

## Status: ✅ Port Proxy is Active and Working!

Your port proxy is now configured and listening on port 1080:
```
127.0.0.1:1080 ← qBittorrent
    ↓ (SOCKS5)
10.2.0.1:8080 ← ProtonVPN WireGuard Interface
    ↓
VPN Network ← MAM
```

## Now Configure qBittorrent

### Step 1: Open qBittorrent
- Launch qBittorrent application

### Step 2: Access Network Settings
1. Click **Tools** in the menu bar
2. Select **Options** (or press **Ctrl+,**)
3. In the left sidebar, click **Network**

### Step 3: Configure Proxy

Under the **Proxy server** section, configure these settings:

#### Proxy Type
- Change from "None" to **SOCKS5**

#### IP Address
- Enter: **127.0.0.1**

#### Port
- Enter: **1080**

#### Authentication (if needed)
- Username: (leave blank)
- Password: (leave blank)

#### Proxy Options (Check these boxes)
- ☑ **Use proxy for peer connections** (IMPORTANT!)
- ☑ **Use proxy for tracker connections** (IMPORTANT!)

### Step 4: Save Configuration
1. Scroll to the bottom of the Options window
2. Click **OK** to save

qBittorrent will restart/reconnect with the new proxy settings.

---

## Verify Configuration

### Method 1: Check qBittorrent Network Status
1. In qBittorrent, go to **Tools > Options > Network**
2. Verify your settings are saved:
   - Proxy Type: SOCKS5
   - IP: 127.0.0.1
   - Port: 1080

### Method 2: Test with a Torrent
1. Add a test torrent to qBittorrent
2. Look for these indicators:
   - Status changes from "Connecting" to "Downloading/Uploading"
   - Peers are found and listed
   - Upload/Download speeds show activity

### Method 3: Monitor Network Connection
Open Command Prompt and run:
```bash
netstat -an | find "1080"
```

If the proxy is in use, you'll see established connections on port 1080.

---

## Troubleshooting

### Issue: qBittorrent still can't connect to peers
1. **Restart qBittorrent** - Make sure settings are applied
2. **Verify proxy is active** - Run: `netsh interface portproxy show all`
3. **Check ProtonVPN** - Make sure it's still connected
4. **Try disabling then re-enabling proxy** in qBittorrent settings

### Issue: "Connection refused" errors in qBittorrent
This means qBittorrent can't reach port 1080. Try:
```bash
# In Command Prompt (Admin)
netsh interface portproxy delete v4tov4 listenport=1080 listenaddress=127.0.0.1
netsh interface portproxy add v4tov4 listenport=1080 listenaddress=127.0.0.1 connectport=8080 connectaddress=10.2.0.1
```

### Issue: All settings correct but no downloads
1. Restart ProtonVPN
2. Restart qBittorrent
3. Verify port 1080 is still listening: `netsh interface portproxy show all`

---

## What Each Setting Does

| Setting | Purpose |
|---------|---------|
| **Proxy Type: SOCKS5** | Protocol that qBittorrent uses to send traffic through proxy |
| **IP: 127.0.0.1** | Localhost (your computer) |
| **Port: 1080** | Where the proxy tunnel is listening |
| **Peer connections** | Ensures torrent peer traffic goes through VPN |
| **Tracker connections** | Ensures tracker communication goes through VPN |

---

## Once Configured

Once qBittorrent is configured with the VPN proxy, you can run your Phase 1 downloader:

```bash
python PHASE1_WORKING.py
```

This will search for audiobooks on MAM through the VPN proxy, keeping your traffic anonymous and encrypted.

---

## Important Notes

- **Do NOT close the port proxy** - It will remain active until you restart Windows or manually delete it
- **qBittorrent must be restarted** after changing proxy settings
- **ProtonVPN must stay connected** for the proxy to work
- **If you restart Windows**, the port proxy will be deleted and you'll need to run the netsh command again

---

## Need Help?

Run the diagnostic again to verify everything:
```bash
python check_vpn_connection.py
```

Should show:
- ✅ ProtonVPN running
- ✅ VPN adapter connected
- ✅ Port 1080 open
