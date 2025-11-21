# MAM Audiobook Downloader - Deployment Guide

## Current Status: ✅ WORKING

The MAM Audiobook Downloader is fully functional and successfully:
- Validates VPN/Proxy routing (Scraper A identity)
- Authenticates with MAM using browser cookies
- Searches Prowlarr (primary) and MAM (fallback)
- Filters for best quality audiobooks
- Checks Audiobookshelf to avoid duplicates
- Downloads torrents to qBittorrent

---

## Local Deployment (Windows)

### Prerequisites
1. **WireGuard VPN** running with config at `temp_vpn_config.conf`
2. **qBittorrent** running and accessible
3. **Audiobookshelf** running and accessible
4. **Prowlarr** (optional, for primary search)

### Setup Steps

1. **Install Dependencies**
   ```powershell
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure Environment**
   Create `.env` file with:
   ```env
   # MAM Credentials
   MAM_USERNAME=your_email@example.com
   MAM_PASSWORD=your_password
   
   # MAM Cookies (from logged-in browser session)
   uid=229756
   mam_id=your_mam_id_cookie_value
   
   # qBittorrent
   QBITTORRENT_URL=http://localhost:8080
   QBITTORRENT_USERNAME=admin
   QBITTORRENT_PASSWORD=adminpass
   
   # Audiobookshelf
   ABS_URL=http://localhost:13378
   ABS_TOKEN=your_abs_api_token
   
   # Prowlarr (optional)
   PROWLARR_URL=http://localhost:9696
   PROWLARR_API_KEY=your_prowlarr_api_key
   
   # Google Books (for metadata)
   GOOGLE_BOOKS_API_KEY=your_google_books_api_key
   ```

3. **Start VPN SOCKS Proxy**
   ```powershell
   python vpn_socks_proxy.py
   ```
   Leave this running in a separate terminal.

4. **Run Downloader**
   ```powershell
   python mam_audiobook_qbittorrent_downloader.py
   ```

### Scheduling (Windows Task Scheduler)

Create a scheduled task to run daily:
```powershell
# Create task (run as Administrator)
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\Users\dogma\Projects\MAMcrawler\mam_audiobook_qbittorrent_downloader.py" -WorkingDirectory "C:\Users\dogma\Projects\MAMcrawler"
$trigger = New-ScheduledTaskTrigger -Daily -At 3AM
Register-ScheduledTask -TaskName "MAM Audiobook Downloader" -Action $action -Trigger $trigger
```

---

## Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- WireGuard VPN running on host (or use a VPN container)

### Quick Start

1. **Build and Run**
   ```bash
   docker-compose up -d
   ```

2. **View Logs**
   ```bash
   docker-compose logs -f mam-downloader
   ```

3. **Stop**
   ```bash
   docker-compose down
   ```

### Docker Architecture

- **vpn-proxy**: Runs SOCKS5 proxy bound to VPN interface
- **mam-downloader**: Runs the audiobook downloader
- Both use `network_mode: host` for VPN/proxy access

### Persistent Data

Volumes mounted:
- `./data` - State files (resume capability)
- `./logs` - Log files

### One-Time Runs

To run once instead of continuously:
```bash
# Uncomment mam-downloader-once in docker-compose.yml
docker-compose run mam-downloader-once
```

Or use a cron job:
```bash
0 3 * * * cd /path/to/MAMcrawler && docker-compose up mam-downloader
```

---

## Troubleshooting

### Login Issues
- **Browser windows opening/closing**: Use cookie-based login (already configured)
- **Cookies expired**: Log into MAM in your browser, extract new cookies, update `.env`

### VPN/Proxy Issues
- **IP validation fails**: Ensure `vpn_socks_proxy.py` is running and VPN is connected
- **Connection refused**: Check VPN interface IP matches `10.2.0.2` in `vpn_socks_proxy.py`

### Docker Issues
- **Playwright errors**: Ensure all system dependencies are installed (see Dockerfile)
- **Network issues**: Use `network_mode: host` for VPN/proxy access
- **Permission errors**: Check volume mount permissions

### General Issues
- **No torrents found**: Check Prowlarr indexers or MAM search results
- **Downloads failing**: Verify qBittorrent is running and accessible
- **Duplicates**: Audiobookshelf integration prevents this automatically

---

## Monitoring

### Logs
- **Application log**: `mam_audiobook_qbittorrent.log`
- **Docker logs**: `docker-compose logs -f`

### Stats
Check the summary at the end of each run for:
- Genres processed
- Torrents found
- Downloads added
- Errors encountered

---

## Security Notes

1. **Never commit `.env`** - Contains sensitive credentials
2. **Cookies expire** - Update periodically from browser session
3. **VPN required** - All MAM traffic must go through VPN (Scraper A identity)
4. **Proxy binding** - SOCKS proxy binds to VPN interface only

---

## Next Steps

1. ✅ Working local deployment
2. ✅ Docker configuration created
3. ⏳ Test Docker deployment (optional)
4. ⏳ Set up scheduling (Task Scheduler or cron)
5. ⏳ Monitor first few runs for issues

---

## Support

For issues or questions:
1. Check logs first
2. Verify all services (VPN, qBittorrent, ABS, Prowlarr) are running
3. Test VPN/proxy with: `curl --socks5 127.0.0.1:8080 https://api.ipify.org`
