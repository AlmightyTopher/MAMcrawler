#!/usr/bin/env python3
"""
Search Prowlarr for Randi Darren audiobooks and queue to qBittorrent with audiobook category
Uses Prowlarr's download endpoint to fetch torrents
"""
import os
import time
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
import requests
from io import BytesIO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()
PROWLARR_URL = os.getenv('PROWLARR_URL', 'http://localhost:9696')
PROWLARR_API_KEY = os.getenv('PROWLARR_API_KEY')
QBITTORRENT_URL = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME')
QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD')

if not PROWLARR_URL.endswith('/'):
    PROWLARR_URL += '/'
if not QBITTORRENT_URL.endswith('/'):
    QBITTORRENT_URL += '/'

class RandiQueueManager:
    def __init__(self):
        self.found_results = []
        self.queued_torrents = []
        self.session = requests.Session()

    def search_prowlarr(self, author):
        """Search Prowlarr for Randi Darren audiobooks"""
        logger.info(f"\n{'='*80}")
        logger.info(f"SEARCHING PROWLARR FOR: {author}")
        logger.info(f"{'='*80}")

        url = f"{PROWLARR_URL}api/v1/search"
        headers = {'X-Api-Key': PROWLARR_API_KEY}
        params = {'query': author, 'type': 'search'}

        try:
            response = self.session.get(url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                self.found_results = response.json()
                logger.info(f"Found {len(self.found_results)} audiobooks")

                for i, result in enumerate(self.found_results, 1):
                    logger.info(f"\n{i}. {result['title']}")
                    logger.info(f"   Indexer: {result['indexer']}")
                    logger.info(f"   Size: {result['size'] / (1024**3):.2f} GB")
                    logger.info(f"   Seeders: {result['seeders']}")
            else:
                logger.error(f"Search failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Search error: {e}")

        return self.found_results

    def queue_via_prowlarr_download(self):
        """Queue torrents using Prowlarr's download endpoint"""
        logger.info(f"\n{'='*80}")
        logger.info("QUEUEING TO QBITTORRENT (via Prowlarr Download)")
        logger.info(f"{'='*80}")

        # Authenticate with qBittorrent
        login_url = f"{QBITTORRENT_URL}api/v2/auth/login"
        login_data = {
            'username': QBITTORRENT_USERNAME,
            'password': QBITTORRENT_PASSWORD
        }

        try:
            login_response = self.session.post(login_url, data=login_data, timeout=10)
            if login_response.status_code != 200:
                logger.error("qBittorrent login failed")
                return

            logger.info("qBittorrent authenticated")
        except Exception as e:
            logger.error(f"qBittorrent login error: {e}")
            return

        # Process each result
        add_url = f"{QBITTORRENT_URL}api/v2/torrents/add"

        for result in self.found_results:
            try:
                title = result['title']
                download_url = result.get('downloadUrl', '')

                if not download_url:
                    logger.warning(f"No download URL for: {title}")
                    continue

                logger.info(f"\nProcessing: {title[:70]}")
                logger.info(f"  Download URL: {download_url[:80]}...")

                # Download the torrent file from Prowlarr
                torrent_response = self.session.get(download_url, timeout=30, allow_redirects=True)

                if torrent_response.status_code == 200:
                    # Queue to qBittorrent
                    files = {
                        'torrents': (f"{title}.torrent", BytesIO(torrent_response.content), 'application/x-bittorrent')
                    }
                    data = {
                        'category': 'audiobooks',
                        'paused': False
                    }

                    add_response = self.session.post(add_url, files=files, data=data, timeout=15)

                    if add_response.status_code == 200 or add_response.text == 'Ok.':
                        logger.info(f"✓ QUEUED: {title[:60]}")
                        self.queued_torrents.append({
                            'title': title,
                            'size': result.get('size'),
                            'seeders': result.get('seeders'),
                            'status': 'queued'
                        })
                    else:
                        logger.warning(f"✗ Queue failed: {title} (HTTP {add_response.status_code})")
                        logger.warning(f"  Response: {add_response.text[:100]}")

                else:
                    logger.warning(f"✗ Download failed: {title} (HTTP {torrent_response.status_code})")

                time.sleep(0.5)  # Rate limit between queueing

            except Exception as e:
                logger.error(f"Error processing {result.get('title', 'Unknown')}: {e}")

        logger.info(f"\n{'='*80}")
        logger.info(f"QUEUE RESULTS: {len(self.queued_torrents)}/{len(self.found_results)} queued")
        logger.info(f"{'='*80}")

    def verify_audiobook_category(self):
        """Verify audiobooks are in the audiobook category"""
        logger.info(f"\n{'='*80}")
        logger.info("VERIFYING AUDIOBOOK CATEGORY IN QUEUE")
        logger.info(f"{'='*80}")

        try:
            url = f"{QBITTORRENT_URL}api/v2/torrents/info?category=audiobooks"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                audiobooks = response.json()
                logger.info(f"Total torrents in 'audiobooks' category: {len(audiobooks)}")

                if audiobooks:
                    logger.info("\nRecently queued audiobooks:")
                    # Show the ones we just added (most recent)
                    for torrent in audiobooks[-min(10, len(audiobooks)):]:
                        logger.info(f"  - {torrent['name'][:70]}")
                        logger.info(f"    State: {torrent['state']}")
                        logger.info(f"    Category: {torrent['category']}")

            else:
                logger.error(f"Category query failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Verification error: {e}")

    def save_results(self):
        """Save results to JSON"""
        results = {
            'search_query': 'Randi Darren',
            'timestamp': datetime.now().isoformat(),
            'total_found': len(self.found_results),
            'total_queued': len(self.queued_torrents),
            'found': [
                {
                    'title': r['title'],
                    'size': r.get('size'),
                    'seeders': r.get('seeders'),
                    'indexer': r.get('indexer')
                }
                for r in self.found_results
            ],
            'queued': self.queued_torrents
        }

        filename = f'randi_prowlarr_queue_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"Results saved to {filename}")

    def run(self):
        """Execute full workflow"""
        try:
            logger.info("\n")
            logger.info("╔" + "="*78 + "╗")
            logger.info("║" + " "*78 + "║")
            logger.info("║" + "RANDI DARREN AUDIOBOOK PROWLARR QUEUE".center(78) + "║")
            logger.info("║" + " "*78 + "║")
            logger.info("╚" + "="*78 + "╝\n")

            # Search
            self.search_prowlarr('Randi Darren')

            if self.found_results:
                # Queue
                self.queue_via_prowlarr_download()

                # Verify
                self.verify_audiobook_category()
            else:
                logger.warning("No results found for Randi Darren")

            # Save
            self.save_results()

            logger.info("\n" + "="*80)
            logger.info("COMPLETE")
            logger.info("="*80 + "\n")

        except Exception as e:
            logger.error(f"Workflow error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    manager = RandiQueueManager()
    manager.run()
