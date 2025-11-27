#!/usr/bin/env python3
"""
Queue all newly found Randi Darren titles to qBittorrent from Prowlarr
Uses the variation search results
"""
import os
import sys
import json
import time
import requests
from typing import List, Dict
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

PROWLARR_URL = os.getenv('PROWLARR_URL', 'http://localhost:9696').rstrip('/')
PROWLARR_API_KEY = os.getenv('PROWLARR_API_KEY')
QBITTORRENT_URL = os.getenv('QBITTORRENT_URL', 'http://localhost:52095').rstrip('/')
QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME')
QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD')

# Titles we want to queue (not already queued in first search)
TITLES_TO_QUEUE = [
    "Fostering Faust",  # #1 - was missing
    "Incubus Inc",  # #1 - was missing
    "Incubus Inc II",  # #2 - was missing
    "Incubus Inc III",  # #3 - was missing (but found)
    "Remnant",  # #1 - was missing
    "Remnant II",  # #2 - was missing
    "Remnant III",  # #3 - was missing
    "Eastern Expansion",  # Wild Wastes #2 - was missing
    "Southern Storm",  # Wild Wastes #3 - was missing
    "Wild Wastes",  # #1 - was missing
]

def search_prowlarr(query: str) -> List[Dict]:
    """Search Prowlarr for a query"""
    try:
        params = {'query': query, 'type': 'search'}
        headers = {'X-Api-Key': PROWLARR_API_KEY}

        response = requests.get(
            f"{PROWLARR_URL}/api/v1/search",
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        print(f"Error searching Prowlarr: {e}", file=sys.stderr)
        return []

def get_best_audiobook_result(results: List[Dict]) -> Dict:
    """Get the best audiobook result from search results"""
    audiobook_results = []

    for result in results:
        title = result.get('title', '').lower()
        # Prefer M4B format, then MP3, ignore VIP editions
        if any(fmt in title for fmt in ['m4b', 'mp3']):
            # Avoid VIP if possible (look for non-VIP first)
            if '[vip]' not in title.lower():
                audiobook_results.append((result, 1))  # Priority 1: non-VIP
            else:
                audiobook_results.append((result, 2))  # Priority 2: VIP

    # Sort by priority (lower is better), then by seeders (higher is better)
    audiobook_results.sort(key=lambda x: (x[1], -x[0].get('seeders', 0)))

    if audiobook_results:
        return audiobook_results[0][0]
    return None

def get_qbittorrent_session() -> requests.Session:
    """Get authenticated qBittorrent session"""
    session = requests.Session()

    try:
        response = session.post(
            f"{QBITTORRENT_URL}/api/v2/auth/login",
            data={
                'username': QBITTORRENT_USERNAME,
                'password': QBITTORRENT_PASSWORD
            },
            timeout=10
        )

        if response.status_code == 200:
            return session
        else:
            print(f"qBittorrent login failed: {response.status_code}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"Error connecting to qBittorrent: {e}", file=sys.stderr)
        return None

def queue_torrent(session: requests.Session, magnet_uri: str, title: str) -> bool:
    """Add torrent to qBittorrent"""
    try:
        data = {
            'urls': magnet_uri,
            'category': 'audiobooks'
        }

        response = session.post(
            f"{QBITTORRENT_URL}/api/v2/torrents/add",
            data=data,
            timeout=10
        )

        if response.status_code == 200:
            return True
        else:
            print(f"  Failed to queue (HTTP {response.status_code})", file=sys.stderr)
            return False
    except Exception as e:
        print(f"  Error queuing: {e}", file=sys.stderr)
        return False

def main():
    print("\n" + "="*80)
    print("QUEUE NEWLY FOUND RANDI DARREN TITLES")
    print("="*80)

    if not PROWLARR_API_KEY or not QBITTORRENT_USERNAME:
        print("ERROR: Missing Prowlarr or qBittorrent credentials")
        sys.exit(1)

    # Get qBittorrent session
    print("\nConnecting to qBittorrent...")
    qb_session = get_qbittorrent_session()
    if not qb_session:
        print("ERROR: Could not connect to qBittorrent")
        sys.exit(1)

    print("[OK] Connected to qBittorrent")

    queued_count = 0
    failed_count = 0
    already_queued = []

    for title in TITLES_TO_QUEUE:
        print(f"\n{'-'*80}")
        print(f"SEARCHING: {title}")
        print(f"{'-'*80}")

        results = search_prowlarr(title)

        if not results:
            print(f"  No results found")
            failed_count += 1
            continue

        best_result = get_best_audiobook_result(results)

        if not best_result:
            print(f"  No audiobook results found")
            failed_count += 1
            continue

        result_title = best_result.get('title', 'Unknown')
        magnet_uri = best_result.get('magnetUrl', best_result.get('downloadUrl'))

        if not magnet_uri:
            print(f"  No magnet/download URL found")
            failed_count += 1
            continue

        print(f"  Selected: {result_title}")
        print(f"  Size: {best_result.get('size', 'N/A')}")
        print(f"  Seeders: {best_result.get('seeders', 0)}")
        print(f"  Queueing...")

        if queue_torrent(qb_session, magnet_uri, title):
            print(f"  [QUEUED]")
            queued_count += 1
        else:
            failed_count += 1

        time.sleep(1)  # Rate limiting

    # Summary
    print("\n" + "="*80)
    print("QUEUEING SUMMARY")
    print("="*80)
    print(f"Titles Queued: {queued_count}")
    print(f"Failed: {failed_count}")
    print(f"Total: {len(TITLES_TO_QUEUE)}")
    print("="*80)

    if queued_count > 0:
        print(f"\nSuccessfully queued {queued_count} new titles to qBittorrent!")

if __name__ == '__main__':
    main()
