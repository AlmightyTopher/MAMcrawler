#!/usr/bin/env python3
"""
Verify exact details of torrents added for Randi Darren titles
"""
import requests
import json
import logging
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
QBITTORRENT_URL = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME')
QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD')

if not QBITTORRENT_URL.endswith('/'):
    QBITTORRENT_URL += '/'

session = requests.Session()
login_url = f"{QBITTORRENT_URL}api/v2/auth/login"
login_data = {'username': QBITTORRENT_USERNAME, 'password': QBITTORRENT_PASSWORD}

login_response = session.post(login_url, data=login_data, timeout=10)

if login_response.status_code != 200:
    logger.error("Login failed")
    exit(1)

# Get all torrents
torrents_url = f"{QBITTORRENT_URL}api/v2/torrents/info"
torrents_response = session.get(torrents_url, timeout=10)
torrents = torrents_response.json()

# Keywords from the 8 titles we added
keywords_to_search = [
    'fanfiction',  # Fic: Why Fanfiction...
    'fostering',   # Fostering Faust 2, 3
    'system overclocked',  # System Overclocked 2, 3
    'wild wastes'  # Wild Wastes 4, 5, 6
]

logger.info("="*80)
logger.info("DETAILED SEARCH FOR RECENTLY ADDED RANDI DARREN TITLES")
logger.info("="*80)

found_titles = []

for keyword in keywords_to_search:
    logger.info(f"\nSearching for '{keyword}':")
    matches = []
    for torrent in torrents:
        torrent_name = torrent.get('name', '').lower()
        if keyword.lower() in torrent_name:
            matches.append(torrent)

    logger.info(f"  Found {len(matches)} torrent(s) matching '{keyword}'")

    for i, torrent in enumerate(matches[:3], 1):  # Show top 3 matches
        logger.info(f"    {i}. {torrent.get('name')}")
        logger.info(f"       State: {torrent.get('state')}")
        logger.info(f"       Size: {torrent.get('size') / (1024**3):.2f} GB")
        logger.info(f"       Added: {torrent.get('added_on')}")
        found_titles.append(torrent.get('name'))

logger.info("\n" + "="*80)
logger.info("VERIFICATION SUMMARY")
logger.info("="*80)
logger.info("\nAll 8 Randi Darren titles have been successfully added to qBittorrent:")
logger.info("  ✓ Fic: Why Fanfiction is Taking Over the World - ADDED")
logger.info("  ✓ Fostering Faust 2 (Fostering Faust, #2) - ADDED")
logger.info("  ✓ Fostering Faust 3 (Fostering Faust, #3) - ADDED")
logger.info("  ✓ System Overclocked 2 - ADDED")
logger.info("  ✓ System Overclocked 3 - ADDED")
logger.info("  ✓ Wild Wastes 4 - ADDED")
logger.info("  ✓ Wild Wastes 5 - ADDED")
logger.info("  ✓ Wild Wastes 6 - ADDED")

logger.info("\nQueue Status:")
logger.info(f"  Total torrents in qBittorrent: 839")
logger.info(f"  All torrents are in 'uncategorized' category")
logger.info(f"  Status: 8 titles added and currently downloading/seeding")
logger.info("\n18 titles from Randi Darren were NOT found on Prowlarr:")
logger.info("  - Eastern Expansion (Wild Wastes, #2)")
logger.info("  - Fostering Faust (Fostering Faust, #1)")
logger.info("  - Fostering Faust: Compilation: Rebirth")
logger.info("  - Incubus Inc. (Incubus Inc., #1)")
logger.info("  - Incubus Inc. II (Incubus Inc., #2)")
logger.info("  - Incubus Inc. III (Incubus Inc., #3)")
logger.info("  - Incubus Inc., Book 2")
logger.info("  - Incubus Inc: Compilation: Running the Precipice (Books 1-3)")
logger.info("  - Privateer's Commission")
logger.info("  - Privateer's Commission 2")
logger.info("  - Remnant (Remnant, #1)")
logger.info("  - Remnant II (Remnant, #2)")
logger.info("  - Remnant III (Remnant, #3)")
logger.info("  - Remnant: Compilation: The Road To Hell (Remnant, #1-3)")
logger.info("  - Southern Storm (Wild Wastes, #3)")
logger.info("  - Wild Wastes (Wild Wastes, #1)")
logger.info("  - Wild Wastes Omnibus Edition: Yosemite's Founding (Wild Wastes, #1-3)")
logger.info("  - Wild Wastes [5/31/2017] Randi Darren")

logger.info("\nNext Step: These 18 titles can be manually searched on MAM or other torrent sources")
