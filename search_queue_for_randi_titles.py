#!/usr/bin/env python3
"""
Search the qBittorrent queue for Randi Darren titles that were supposedly added
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

# The 8 titles that were supposedly added
RANDI_TITLES_TO_FIND = [
    'Fic: Why Fanfiction is Taking Over the World',
    'Fostering Faust 2',
    'Fostering Faust 3',
    'System Overclocked 2',
    'System Overclocked 3',
    'Wild Wastes 4',
    'Wild Wastes 5',
    'Wild Wastes 6'
]

session = requests.Session()
login_url = f"{QBITTORRENT_URL}api/v2/auth/login"
login_data = {'username': QBITTORRENT_USERNAME, 'password': QBITTORRENT_PASSWORD}

login_response = session.post(login_url, data=login_data, timeout=10)
logger.info(f"Login status: {login_response.status_code}")

if login_response.status_code != 200:
    logger.error("Login failed")
    exit(1)

# Get all torrents
torrents_url = f"{QBITTORRENT_URL}api/v2/torrents/info"
torrents_response = session.get(torrents_url, timeout=10)

if torrents_response.status_code != 200:
    logger.error(f"Failed to get torrents: {torrents_response.status_code}")
    exit(1)

torrents = torrents_response.json()
logger.info(f"Total torrents in queue: {len(torrents)}\n")

logger.info("="*80)
logger.info("SEARCHING FOR RANDI DARREN TITLES IN QUEUE")
logger.info("="*80)

found_titles = []
not_found_titles = []

for target_title in RANDI_TITLES_TO_FIND:
    found = False
    for torrent in torrents:
        torrent_name = torrent.get('name', '').lower()
        target_lower = target_title.lower()

        # Check if title is in torrent name
        if target_lower in torrent_name or any(word in torrent_name for word in target_lower.split()):
            found_titles.append({
                'searched_for': target_title,
                'found_as': torrent.get('name'),
                'state': torrent.get('state'),
                'category': torrent.get('category') or '[uncategorized]'
            })
            logger.info(f"✓ FOUND: {target_title}")
            logger.info(f"  Queue as: {torrent.get('name')}")
            logger.info(f"  State: {torrent.get('state')}")
            logger.info(f"  Category: {torrent.get('category') or '[uncategorized]'}")
            found = True
            break

    if not found:
        not_found_titles.append(target_title)
        logger.info(f"✗ NOT FOUND: {target_title}")

logger.info("\n" + "="*80)
logger.info("SUMMARY")
logger.info("="*80)
logger.info(f"Titles found in queue: {len(found_titles)}/{len(RANDI_TITLES_TO_FIND)}")
logger.info(f"Titles NOT found in queue: {len(not_found_titles)}/{len(RANDI_TITLES_TO_FIND)}")

if found_titles:
    logger.info("\nFound titles:")
    for item in found_titles:
        logger.info(f"  - {item['searched_for']}")
        logger.info(f"    (queued as: {item['found_as'][:60]}...)")

if not_found_titles:
    logger.info("\nMissing titles:")
    for title in not_found_titles:
        logger.info(f"  - {title}")
