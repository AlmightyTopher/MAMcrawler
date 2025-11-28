# VPN-Resilient qBittorrent Integration - Quick Reference

## Quick Start

### 1. Basic Usage (Current Setup)
```bash
# Primary instance only (no fallback)
python execute_full_workflow.py
```

### 2. With Secondary Fallback
```bash
# Set secondary instance URL in .env
export QBITTORRENT_SECONDARY_URL=http://localhost:52095

python execute_full_workflow.py
```

### 3. Check Queue File
```bash
# If VPN was down, check for queued magnets
cat qbittorrent_queue.json
```

## Environment Variables

### Required
```bash
QBITTORRENT_URL=http://192.168.0.48:52095/
QBITTORRENT_USERNAME=your_username
QBITTORRENT_PASSWORD=your_password
DOWNLOAD_PATH=F:/Audiobookshelf/Books
```

### Optional
```bash
QBITTORRENT_SECONDARY_URL=http://localhost:52095
```

## Health Check Output

### VPN Connected
```
[HEALTH]   VPN Status: CONNECTED
[HEALTH]   Primary Instance: OK
```

### VPN Down
```
[HEALTH]   VPN Status: DOWN
[HEALTH]   Primary Instance: HTTP_404
[WARN ]   Magnets queued to qbittorrent_queue.json
```

## Troubleshooting

### Issue: HTTP 404 Errors
**Cause**: VPN disconnected, qBittorrent not accessible
**Solution**: 
1. Check VPN connection
2. Restart VPN
3. Check `qbittorrent_queue.json` for queued magnets
4. Re-run workflow when VPN reconnects

### Issue: All Instances Unavailable
**Cause**: Both primary and secondary down
**Solution**:
1. Check `qbittorrent_queue.json`
2. Manually add magnets to qBittorrent Web UI
3. Or wait for services to recover and re-run

### Issue: Secondary Instance Not Working
**Cause**: Not configured or wrong URL
**Solution**:
1. Set `QBITTORRENT_SECONDARY_URL` in .env
2. Verify secondary instance is running
3. Test: `curl http://localhost:52095/api/v2/app/webapiVersion`

## Queue File Recovery

### Manual Addition
1. Open qBittorrent Web UI
2. Go to Add Torrent
3. Paste magnet links from `qbittorrent_queue.json`

### Automatic Processing
```python
# In Python script
from backend.integrations.qbittorrent_resilient import ResilientQBittorrentClient

async with ResilientQBittorrentClient(...) as client:
    successful, failed = await client.process_queue_file()
```

## Testing Checklist

- [ ] VPN connected, primary works
- [ ] VPN down, secondary works (if configured)
- [ ] All instances down, queue file created
- [ ] Queue file contains valid magnet links
- [ ] Manual addition from queue file works

## Common Commands

```bash
# Check VPN connectivity
ping 192.168.0.1

# Check primary qBittorrent
curl http://192.168.0.48:52095/api/v2/app/webapiVersion

# Check secondary qBittorrent
curl http://localhost:52095/api/v2/app/webapiVersion

# View queue file
cat qbittorrent_queue.json | jq

# Run workflow
python execute_full_workflow.py
```

## Integration Points

### In execute_full_workflow.py

**Line 37-38**: Import statements
```python
from qbittorrent_resilient import ResilientQBittorrentClient
```

**Line 370-469**: Phase 5 implementation
```python
async def add_to_qbittorrent(self, magnet_links, max_downloads=10):
    async with ResilientQBittorrentClient(...) as client:
        # Health check
        health = await client.perform_health_check()
        
        # Add with fallback
        successful, failed, queued = await client.add_torrents_with_fallback(...)
```

**Line 54**: Secondary URL configuration
```python
self.qb_secondary_url = os.getenv('QBITTORRENT_SECONDARY_URL', None)
```

## Status Codes

- `OK`: Instance is healthy
- `HTTP_404`: VPN down or instance not accessible
- `TIMEOUT`: Connection timeout
- `VPN_DOWN`: VPN gateway not reachable
- `NOT_CONFIGURED`: Secondary instance not set

## Quick Fixes

### VPN Not Detected
```python
# In backend/integrations/qbittorrent_resilient.py line 27
# Change gateway IP if needed
self.gateway_ip = "YOUR_VPN_GATEWAY_IP"
```

### Change Timeout
```python
# In backend/integrations/qbittorrent_resilient.py line 28
self.timeout = 10  # Increase to 10 seconds
```

### Different Queue File
```python
# In execute_full_workflow.py line 390
queue_file="my_custom_queue.json"
```

---

**Quick Reference Version**: 1.0
**Last Updated**: 2025-11-28
