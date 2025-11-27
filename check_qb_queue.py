#!/usr/bin/env python3
"""
Check actual qBittorrent queue status and verify the items that were supposedly added
"""
import requests
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
QBITTORRENT_URL = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD', 'Tesl@ismy#1')

# Normalize URL
if not QBITTORRENT_URL.endswith('/'):
    QBITTORRENT_URL += '/'

logger.info(f"qBittorrent URL: {QBITTORRENT_URL}")
logger.info(f"Username: {QBITTORRENT_USERNAME}")

def check_qb_status():
    """Check qBittorrent queue status"""
    session = requests.Session()

    try:
        # Step 1: Login to qBittorrent
        logger.info("Attempting qBittorrent login...")
        login_url = f"{QBITTORRENT_URL}api/v2/auth/login"
        login_data = {
            'username': QBITTORRENT_USERNAME,
            'password': QBITTORRENT_PASSWORD
        }

        login_response = session.post(login_url, data=login_data, timeout=10)
        logger.info(f"Login response status: {login_response.status_code}")
        logger.info(f"Login response text: {login_response.text[:200]}")

        if login_response.status_code != 200:
            logger.error(f"Login failed: {login_response.status_code}")
            return

        # Step 2: Get all torrents
        logger.info("\n" + "="*80)
        logger.info("QUERYING ALL TORRENTS")
        logger.info("="*80)

        torrents_url = f"{QBITTORRENT_URL}api/v2/torrents/info"
        torrents_response = session.get(torrents_url, timeout=10)

        if torrents_response.status_code == 200:
            torrents = torrents_response.json()
            logger.info(f"Total torrents in qBittorrent: {len(torrents)}")

            if torrents:
                logger.info("\nTorrents by category:")
                categories = {}
                for torrent in torrents:
                    category = torrent.get('category', 'uncategorized')
                    if category not in categories:
                        categories[category] = []
                    categories[category].append({
                        'name': torrent.get('name'),
                        'state': torrent.get('state'),
                        'size': torrent.get('size')
                    })

                for cat, items in categories.items():
                    logger.info(f"\n  {cat.upper()}: {len(items)} items")
                    for item in items[:5]:  # Show first 5
                        logger.info(f"    - {item['name'][:80]} ({item['state']})")
                    if len(items) > 5:
                        logger.info(f"    ... and {len(items) - 5} more")
            else:
                logger.warning("No torrents found in qBittorrent")
        else:
            logger.error(f"Failed to get torrents: {torrents_response.status_code}")
            logger.error(f"Response: {torrents_response.text[:300]}")

        # Step 3: Check for audiobooks category specifically
        logger.info("\n" + "="*80)
        logger.info("QUERYING AUDIOBOOKS CATEGORY")
        logger.info("="*80)

        audiobooks_url = f"{QBITTORRENT_URL}api/v2/torrents/info?category=audiobooks"
        audiobooks_response = session.get(audiobooks_url, timeout=10)

        if audiobooks_response.status_code == 200:
            audiobooks = audiobooks_response.json()
            logger.info(f"Total audiobooks in queue: {len(audiobooks)}")

            if audiobooks:
                logger.info("\nAudiobook torrents:")
                for book in audiobooks:
                    logger.info(f"  - {book.get('name')[:80]}")
                    logger.info(f"    State: {book.get('state')}")
                    logger.info(f"    Progress: {book.get('progress')*100:.1f}%")
                    logger.info(f"    Category: {book.get('category')}")
            else:
                logger.warning("No audiobooks in queue")
        else:
            logger.error(f"Failed to query audiobooks: {audiobooks_response.status_code}")

        # Step 4: Check server state
        logger.info("\n" + "="*80)
        logger.info("SERVER STATE")
        logger.info("="*80)

        server_url = f"{QBITTORRENT_URL}api/v2/app/webuiApi"
        server_response = session.get(server_url, timeout=10)

        if server_response.status_code == 200:
            logger.info("qBittorrent API is responding")
        else:
            logger.warning(f"API check returned: {server_response.status_code}")

        logger.info("\n" + "="*80)
        logger.info("QUEUE CHECK COMPLETE")
        logger.info("="*80)

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {e}")
        logger.error("Is qBittorrent running?")
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_qb_status()
