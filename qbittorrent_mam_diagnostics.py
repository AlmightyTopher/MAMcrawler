#!/usr/bin/env python3
"""
Diagnose qBittorrent connection issues with MyAnonamouse
"""
import requests
import json
import logging
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
QB_URL = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
QB_USER = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
QB_PASS = os.getenv('QBITTORRENT_PASSWORD', 'Tesl@ismy#1')

if not QB_URL.endswith('/'):
    QB_URL += '/'

logger.info(f"qBittorrent URL: {QB_URL}")
logger.info(f"Username: {QB_USER}")
logger.info("")

session = requests.Session()

# Test 1: Basic connectivity
logger.info("="*80)
logger.info("TEST 1: Basic qBittorrent Connectivity")
logger.info("="*80)

try:
    response = requests.head(QB_URL, timeout=5)
    logger.info(f"✓ qBittorrent is reachable (HTTP {response.status_code})")
except Exception as e:
    logger.error(f"✗ Cannot reach qBittorrent: {e}")
    exit(1)

# Test 2: API authentication
logger.info("\n" + "="*80)
logger.info("TEST 2: qBittorrent API Authentication")
logger.info("="*80)

try:
    login_response = session.post(
        f"{QB_URL}api/v2/auth/login",
        data={'username': QB_USER, 'password': QB_PASS},
        timeout=10
    )
    logger.info(f"Login response status: {login_response.status_code}")
    logger.info(f"Login response body: {login_response.text}")

    if login_response.status_code == 200:
        logger.info("✓ Successfully authenticated with qBittorrent")
    else:
        logger.error(f"✗ Authentication failed")
except Exception as e:
    logger.error(f"✗ Login error: {e}")
    exit(1)

# Test 3: Get qBittorrent preferences
logger.info("\n" + "="*80)
logger.info("TEST 3: qBittorrent Preferences (General Settings)")
logger.info("="*80)

try:
    prefs_response = session.get(f"{QB_URL}api/v2/app/preferences", timeout=10)

    if prefs_response.status_code == 200:
        prefs = prefs_response.json()
        logger.info("✓ Retrieved preferences")
        logger.info(f"\nKey Settings:")
        logger.info(f"  - Listen port: {prefs.get('listen_port')}")
        logger.info(f"  - UPnP/NAT-PMP enabled: {prefs.get('upnp')}")
        logger.info(f"  - Proxy type: {prefs.get('proxy_type')}")
        logger.info(f"  - Anonymous mode: {prefs.get('anonymous_mode')}")
        logger.info(f"  - Enable connections encryption: {prefs.get('enable_connections_encryption')}")

        if prefs.get('proxy_type') != 0:
            logger.warning("⚠ WARNING: Proxy is enabled!")
            logger.info(f"    Proxy type: {prefs.get('proxy_type')}")
            logger.info(f"    Proxy address: {prefs.get('proxy_ip')}")
            logger.info(f"    Proxy port: {prefs.get('proxy_port')}")

    else:
        logger.error(f"Failed to get preferences: HTTP {prefs_response.status_code}")

except Exception as e:
    logger.error(f"✗ Error getting preferences: {e}")

# Test 4: Check active torrents and their trackers
logger.info("\n" + "="*80)
logger.info("TEST 4: Active Torrents and MAM Detection")
logger.info("="*80)

try:
    torrents_response = session.get(f"{QB_URL}api/v2/torrents/info", timeout=10)

    if torrents_response.status_code == 200:
        torrents = torrents_response.json()
        logger.info(f"✓ Total torrents in queue: {len(torrents)}")

        # Look for MAM torrents
        mam_torrents = []
        for torrent in torrents:
            if 'myanonamouse' in torrent.get('name', '').lower() or 'mam' in torrent.get('name', '').lower():
                mam_torrents.append(torrent)

        if mam_torrents:
            logger.info(f"\n✓ Found {len(mam_torrents)} MAM torrents in queue:")
            for torrent in mam_torrents[:5]:
                logger.info(f"  - {torrent['name']}")
                logger.info(f"    State: {torrent['state']}")
        else:
            logger.warning("⚠ No MAM torrents found in queue")

        # Check for torrents with tracker issues
        logger.info(f"\nChecking torrent health:")
        unhealthy = 0
        for torrent in torrents[:10]:  # Check first 10
            if torrent['state'] in ['stalledDL', 'stalledUP', 'missingFiles', 'checkingResumeData']:
                unhealthy += 1
                logger.warning(f"  ✗ {torrent['name'][:50]}: {torrent['state']}")

        if unhealthy > 0:
            logger.warning(f"\n⚠ {unhealthy} torrents in stalled/unhealthy state")

    else:
        logger.error(f"Failed to get torrents: HTTP {torrents_response.status_code}")

except Exception as e:
    logger.error(f"✗ Error getting torrents: {e}")

# Test 5: Check if qBittorrent can reach trackers
logger.info("\n" + "="*80)
logger.info("TEST 5: Tracker Connectivity Test")
logger.info("="*80)

try:
    # Try to get details of a recent torrent
    torrent_peers = session.get(f"{QB_URL}api/v2/torrents/peers", timeout=10)

    if torrent_peers.status_code == 200:
        peers_data = torrent_peers.json()
        logger.info(f"✓ Peer data available: {len(peers_data)} torrents have peer info")
    else:
        logger.warning(f"⚠ Could not retrieve peer data: HTTP {torrent_peers.status_code}")

except Exception as e:
    logger.error(f"✗ Error checking peers: {e}")

# Test 6: Network/Firewall test
logger.info("\n" + "="*80)
logger.info("TEST 6: Network Diagnostics")
logger.info("="*80)

try:
    # Check if we can reach external tracker
    logger.info("Testing external connectivity (simulated tracker check)...")

    external_test = requests.get('https://www.myanonamouse.net', timeout=10, verify=False)
    logger.info(f"✓ Can reach myanonamouse.net (HTTP {external_test.status_code})")

except requests.exceptions.SSLError:
    logger.warning("⚠ SSL certificate issue reaching MAM, but connection possible")
except Exception as e:
    logger.error(f"✗ Cannot reach myanonamouse.net: {e}")
    logger.error("  This may indicate firewall/VPN issues")

# Test 7: qBittorrent logs
logger.info("\n" + "="*80)
logger.info("TEST 7: qBittorrent Application Logs")
logger.info("="*80)

try:
    logs_response = session.get(f"{QB_URL}api/v2/log/main", timeout=10, params={'last_known_id': 0, 'limit': 50})

    if logs_response.status_code == 200:
        logs = logs_response.json()
        logger.info(f"✓ Retrieved {len(logs)} recent log entries")

        logger.info("\nRecent log entries (last 10):")
        for log in logs[-10:]:
            log_type = log.get('type', 'INFO')
            message = log.get('message', '')
            logger.info(f"  [{log_type}] {message[:70]}")
    else:
        logger.error(f"Failed to get logs: HTTP {logs_response.status_code}")

except Exception as e:
    logger.error(f"✗ Error getting logs: {e}")

# Summary
logger.info("\n" + "="*80)
logger.info("DIAGNOSTIC SUMMARY")
logger.info("="*80)

logger.info("""
COMMON ISSUES AND SOLUTIONS:

1. IP Bans/Rate Limiting:
   - qBittorrent might be IP banned from MAM
   - Solution: Check qBittorrent logs for 403/429 responses

2. Tracker Connection Issues:
   - Firewall blocking tracker communication
   - Solution: Check qBittorrent listen port settings

3. Proxy Settings:
   - qBittorrent proxy misconfigured
   - Solution: Check proxy_type (should be 0 for no proxy)

4. Encryption Mismatch:
   - Tracker requires specific encryption settings
   - Solution: Check enable_connections_encryption setting

5. Anonymous Mode Issues:
   - Anonymous mode may hide peer info
   - Solution: Disable if needed for tracker communication

NEXT STEPS:
1. Review qBittorrent settings/preferences in WebUI
2. Check qBittorrent logs for error messages
3. Verify VPN is active if required for MAM
4. Check if qBittorrent listen port is properly forwarded/accessible
5. Try re-adding a small test torrent and monitoring logs
""")

logger.info("="*80)
logger.info("Diagnostic complete")
logger.info("="*80)
