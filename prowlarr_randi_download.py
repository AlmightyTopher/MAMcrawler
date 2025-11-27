#!/usr/bin/env python3
"""
Use Prowlarr to search and download all Randi Darren audiobooks
Queue directly to qBittorrent with audiobook category
"""
import os
import time
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
import requests

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

class ProwlarrRandiDownloader:
    def __init__(self):
        self.found_results = []
        self.queued_torrents = []
        self.session = requests.Session()

    def search_prowlarr(self, author_name):
        """Search Prowlarr for all titles by author"""
        logger.info(f"\n{'='*80}")
        logger.info(f"SEARCHING PROWLARR FOR: {author_name}")
        logger.info(f"{'='*80}")

        search_url = f"{PROWLARR_URL}api/v1/search"
        headers = {'X-Api-Key': PROWLARR_API_KEY}

        # Search for author name
        params = {
            'query': author_name,
            'type': 'search',
            'categories': [3000]  # Categories for books/audiobooks
        }

        try:
            logger.info(f"Querying Prowlarr API: {search_url}")
            response = self.session.get(search_url, headers=headers, params=params, timeout=30)
            logger.info(f"Response status: {response.status_code}")

            if response.status_code == 200:
                results = response.json()
                logger.info(f"Found {len(results)} results")

                for result in results:
                    torrent_info = {
                        'title': result.get('title', 'Unknown'),
                        'indexer': result.get('indexerName', 'Unknown'),
                        'guid': result.get('guid', ''),
                        'magnetUrl': result.get('magnetUrl', ''),
                        'torrentUrl': result.get('torrentUrl', ''),
                        'size': result.get('size', 0)
                    }

                    # Prefer magnet links
                    if torrent_info['magnetUrl']:
                        self.found_results.append(torrent_info)
                        logger.info(f"  Found: {torrent_info['title'][:70]}")
                    elif torrent_info['torrentUrl']:
                        self.found_results.append(torrent_info)
                        logger.info(f"  Found: {torrent_info['title'][:70]} (torrent file)")

                logger.info(f"Total usable results: {len(self.found_results)}")
            else:
                logger.error(f"Search failed: {response.status_code}")
                logger.error(f"Response: {response.text[:500]}")

        except Exception as e:
            logger.error(f"Search error: {e}")

        return self.found_results

    def queue_to_qbittorrent(self):
        """Queue all results to qBittorrent with audiobook category"""
        logger.info(f"\n{'='*80}")
        logger.info(f"QUEUEING TO QBITTORRENT WITH AUDIOBOOK CATEGORY")
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

        # Queue each result
        add_url = f"{QBITTORRENT_URL}api/v2/torrents/add"

        for result in self.found_results:
            try:
                # Use magnet link if available, otherwise torrent URL
                url = result['magnetUrl'] if result['magnetUrl'] else result['torrentUrl']

                if not url:
                    logger.warning(f"No valid URL for: {result['title']}")
                    continue

                add_data = {
                    'urls': url,
                    'category': 'audiobooks',
                    'paused': False
                }

                add_response = self.session.post(add_url, data=add_data, timeout=10)

                if add_response.status_code == 200 or add_response.text == 'Ok.':
                    logger.info(f"✓ QUEUED: {result['title'][:60]}")
                    logger.info(f"  Indexer: {result['indexer']}")
                    logger.info(f"  Size: {result['size'] / (1024**3):.2f} GB")
                    self.queued_torrents.append(result)
                else:
                    logger.warning(f"✗ Queue failed: {result['title'][:60]} (HTTP {add_response.status_code})")
                    logger.warning(f"  Response: {add_response.text[:100]}")

                time.sleep(0.5)  # Rate limit

            except Exception as e:
                logger.error(f"Error queuing {result['title']}: {e}")

        logger.info(f"\nTotal queued: {len(self.queued_torrents)}/{len(self.found_results)}")

    def verify_queue(self):
        """Verify audiobooks category in queue"""
        logger.info(f"\n{'='*80}")
        logger.info("VERIFYING QUEUE STATUS")
        logger.info(f"{'='*80}")

        try:
            torrents_url = f"{QBITTORRENT_URL}api/v2/torrents/info?category=audiobooks"
            response = self.session.get(torrents_url, timeout=10)

            if response.status_code == 200:
                audiobooks = response.json()
                logger.info(f"Total audiobooks in queue: {len(audiobooks)}")

                if audiobooks:
                    logger.info("\nAudiobook torrents in queue:")
                    for book in audiobooks[:10]:  # Show first 10
                        logger.info(f"  - {book.get('name')[:70]}")
                        logger.info(f"    State: {book.get('state')}")
                    if len(audiobooks) > 10:
                        logger.info(f"  ... and {len(audiobooks) - 10} more")
            else:
                logger.error(f"Queue query failed: {response.status_code}")

        except Exception as e:
            logger.error(f"Verification error: {e}")

    def save_results(self):
        """Save results to JSON"""
        results = {
            'search_query': 'Randi Darren',
            'timestamp': datetime.now().isoformat(),
            'prowlarr_results': len(self.found_results),
            'queued_torrents': len(self.queued_torrents),
            'found': self.found_results,
            'queued': self.queued_torrents
        }

        filename = f'prowlarr_randi_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"\nResults saved to {filename}")

    def run(self):
        """Execute full workflow"""
        try:
            logger.info("\n")
            logger.info("╔" + "="*78 + "╗")
            logger.info("║" + " "*78 + "║")
            logger.info("║" + "RANDI DARREN AUDIOBOOK DOWNLOAD VIA PROWLARR".center(78) + "║")
            logger.info("║" + " "*78 + "║")
            logger.info("╚" + "="*78 + "╝")

            # Search Prowlarr
            self.search_prowlarr('Randi Darren')

            if self.found_results:
                # Queue to qBittorrent
                self.queue_to_qbittorrent()

                # Verify
                self.verify_queue()
            else:
                logger.warning("No results found for Randi Darren")

            # Save results
            self.save_results()

            logger.info("\n" + "="*80)
            logger.info("COMPLETE")
            logger.info("="*80 + "\n")

        except Exception as e:
            logger.error(f"Workflow error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    downloader = ProwlarrRandiDownloader()
    downloader.run()
