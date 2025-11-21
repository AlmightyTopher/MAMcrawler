# MAMcrawler - To-Do List

## 🔴 Critical - VPN Setup (In Progress)

### WireGuard Tunnel Configuration
- [ ] **Troubleshoot WireGuard service startup issue**
  - Service is installed but fails to start
  - Error: "Cannot open 'WireGuardTunnel$TopherTek-Python-Tunnel' service"
  - Config file is correctly placed at `C:\ProgramData\WireGuard\TopherTek-Python-Tunnel.conf`
  - May need to check for conflicts with ProtonVPN WireGuard service

- [ ] **Complete VPN routing setup**
  - Once service starts, verify interface appears
  - Set interface metric to 500
  - Create firewall rule binding Python to VPN interface
  - Add default route for VPN interface
  - Test that Python traffic uses VPN while other Windows traffic uses normal connection

### Manual Steps to Try
```powershell
# 1. Stop conflicting services
Stop-Service "ProtonVPN WireGuard" -Force

# 2. Reinstall tunnel service
cd "C:\Program Files\WireGuard"
.\wireguard.exe /uninstalltunnelservice TopherTek-Python-Tunnel
.\wireguard.exe /installtunnelservice "C:\ProgramData\WireGuard\TopherTek-Python-Tunnel.conf"

# 3. Start via wireguard.exe
.\wireguard.exe /tunnelservice TopherTek-Python-Tunnel

# 4. Verify interface appears
Get-NetIPInterface | Where-Object {$_.InterfaceAlias -like "*TopherTek*"}
```

## 🟡 High Priority - Testing & Verification

### Dual VPN Scraper
- [ ] **Test Goodreads dual scraper** (after VPN is working)
  - Run: `python dual_goodreads_scraper.py`
  - Verify two workers start (VPN + Direct)
  - Check that different IPs are used
  - Validate merged results in `final_goodreads_results.json`

### MENGO Audiobook Downloader
- [ ] **Test MENGO integration**
  - Run: `python mam_audiobook_qbittorrent_downloader.py`
  - Verify it fetches Top 10 from `https://mango-mushroom-0d3dde80f.azurestaticapps.net/`
  - Check MAM search for each title
  - Confirm torrents are added to qBittorrent

### MAM Crawler
- [ ] **Test passive crawler**
  - Run: `python run_mam_crawler.py`
  - Verify guides section crawling
  - Check qBittorrent settings extraction
  - Confirm RAG ingestion triggers automatically

### RAG System
- [ ] **Verify RAG functionality**
  - Check that `ingest.py` processes new markdown files
  - Test query functionality (if implemented)
  - Verify FAISS index updates correctly

## 🟢 Medium Priority - Enhancements

### Code Quality
- [ ] **Add comprehensive error handling**
  - Better VPN connection failure handling
  - Graceful degradation if MENGO is unavailable
  - Retry logic for network failures

- [ ] **Add logging improvements**
  - Structured logging with levels
  - Separate log files per component
  - Log rotation

### Documentation
- [ ] **Create user guide**
  - Installation instructions
  - Configuration guide
  - Troubleshooting section

- [ ] **Document VPN setup process**
  - Step-by-step WireGuard configuration
  - Windows firewall rule creation
  - Verification steps

### Features
- [ ] **Add IP verification**
  - Check actual IP being used by each worker
  - Log IP addresses for verification
  - Alert if both workers use same IP

- [ ] **Implement rate limiting dashboard**
  - Show current rate limit status
  - Display queue sizes
  - Estimate completion times

## 🔵 Low Priority - Future Improvements

### Performance
- [ ] **Optimize crawling speed**
  - Adjust delay ranges based on site response
  - Implement adaptive rate limiting
  - Consider connection pooling

### Monitoring
- [ ] **Add metrics collection**
  - Track success/failure rates
  - Monitor response times
  - Log bandwidth usage

### Testing
- [ ] **Create unit tests**
  - Test StealthCrawler methods
  - Mock network requests
  - Validate data extraction

- [ ] **Add integration tests**
  - End-to-end workflow tests
  - VPN routing verification
  - Multi-worker coordination

## 📋 Completed Tasks ✅

- [x] Create Shared Stealth Library (`mamcrawler/stealth.py`)
- [x] Refactor `mam_crawler.py` to use StealthCrawler
- [x] Refactor `mam_audiobook_qbittorrent_downloader.py` to use StealthCrawler
- [x] Add MENGO URL targeting for Top 10 list
- [x] Create `dual_goodreads_scraper.py` orchestrator
- [x] Create `goodreads_worker.py` with stealth features
- [x] Create `vpn_manager.py` for WireGuard management
- [x] Archive old crawler scripts
- [x] Integrate RAG ingestion into `mam_crawler.py`
- [x] Verify `ingest.py` functionality
- [x] Create WireGuard config file
- [x] Install WireGuard tunnel service

## 🚨 Blockers

1. **WireGuard Service Won't Start**
   - Prevents VPN routing setup
   - Blocks dual scraper testing
   - May be related to ProtonVPN conflict

## 📝 Notes

- All core refactoring is complete
- Scripts are ready to test once VPN is working
- Consider running MENGO downloader and MAM crawler independently of VPN setup
- VPN is only required for Goodreads dual scraper

---

**Last Updated:** 2025-11-20 21:12 PST
