#!/usr/bin/env python3
"""
Fix qBittorrent SOCKS5 proxy configuration
Disable proxy to restore direct tracker communication with MyAnonamouse
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
QB_USER = os.getenv('QBITTORRENT_USERNAME')
QB_PASS = os.getenv('QBITTORRENT_PASSWORD')

if not QB_URL.endswith('/'):
    QB_URL += '/'

logger.info("="*80)
logger.info("QBITTORRENT PROXY FIX")
logger.info("="*80)
logger.info(f"URL: {QB_URL}")

session = requests.Session()

# Authenticate
logger.info("\nAuthenticating with qBittorrent...")
login_response = session.post(
    f"{QB_URL}api/v2/auth/login",
    data={'username': QB_USER, 'password': QB_PASS},
    timeout=10
)

if login_response.status_code != 200:
    logger.error(f"Login failed: {login_response.status_code}")
    exit(1)

logger.info("✓ Authenticated")

# Get current preferences
logger.info("\nRetrieving current preferences...")
prefs_response = session.get(f"{QB_URL}api/v2/app/preferences", timeout=10)

if prefs_response.status_code != 200:
    logger.error(f"Failed to get preferences: {prefs_response.status_code}")
    exit(1)

current_prefs = prefs_response.json()

logger.info("\nCURRENT SETTINGS:")
logger.info(f"  Proxy type: {current_prefs.get('proxy_type')} (SOCKS5 = 2, NONE = 0)")
logger.info(f"  Proxy IP: {current_prefs.get('proxy_ip')}")
logger.info(f"  Proxy port: {current_prefs.get('proxy_port')}")
logger.info(f"  Listen port: {current_prefs.get('listen_port')}")
logger.info(f"  UPnP/NAT-PMP: {current_prefs.get('upnp')}")

# Build new preferences with proxy disabled
new_prefs = {
    'proxy_type': 0,  # 0 = no proxy
    # Other settings remain unchanged
}

# Apply the fix
logger.info("\nApplying fix: Disabling SOCKS5 proxy...")
set_prefs_response = session.post(
    f"{QB_URL}api/v2/app/setPreferences",
    data=json.dumps(new_prefs),
    headers={'Content-Type': 'application/json'},
    timeout=10
)

if set_prefs_response.status_code == 200:
    logger.info("✓ Preferences updated successfully")
else:
    logger.error(f"Failed to set preferences: {set_prefs_response.status_code}")
    logger.error(f"Response: {set_prefs_response.text}")
    exit(1)

# Verify the fix
logger.info("\nVerifying fix...")
verify_response = session.get(f"{QB_URL}api/v2/app/preferences", timeout=10)

if verify_response.status_code == 200:
    updated_prefs = verify_response.json()

    logger.info("\nUPDATED SETTINGS:")
    logger.info(f"  Proxy type: {updated_prefs.get('proxy_type')} (should be 0)")
    logger.info(f"  Proxy IP: {updated_prefs.get('proxy_ip')}")
    logger.info(f"  Proxy port: {updated_prefs.get('proxy_port')}")

    if updated_prefs.get('proxy_type') == 0:
        logger.info("\n" + "="*80)
        logger.info("SUCCESS! Proxy has been disabled")
        logger.info("="*80)
        logger.info("""
NEXT STEPS:
1. qBittorrent will now communicate directly with trackers
2. All stalled torrents should resume if trackers respond
3. Monitor qBittorrent logs for tracker announcements
4. Give torrents 5-10 minutes to resume

If torrents still don't resume:
- Check if MyAnonamouse IP is whitelisted
- Verify VPN is active (if required)
- Check qBittorrent logs for specific errors
- Try re-adding a single test torrent

Your qBittorrent can now connect properly to MyAnonamouse!
""")
    else:
        logger.error("✗ Proxy type is still not 0, fix may have failed")
else:
    logger.error(f"Failed to verify: {verify_response.status_code}")

