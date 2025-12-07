#!/usr/bin/env python3
"""
Search for curated top audiobooks in Prowlarr and queue to qBittorrent
====================================================================

Uses the curated list of top 10 fantasy and sci-fi audiobooks to search Prowlarr
and automatically queue downloads to qBittorrent.
"""

import sys
import os
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import quote

if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

from dotenv import load_dotenv
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('prowlarr_curated_search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import requests
    from backend.integrations.qbittorrent_client import QBittorrentClient
except ImportError as e:
    logger.error(f"Missing required library: {e}")
    sys.exit(1)


class ProwlarrCuratedSearch:
    """
    Search for curated top audiobooks using Prowlarr and queue to qBittorrent
    """

    def __init__(self):
        self.prowlarr_url = os.getenv('PROWLARR_URL', 'http://localhost:9696')
        self.prowlarr_api_key = os.getenv('PROWLARR_API_KEY')

        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD')

        # For Prowlarr API
        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': self.prowlarr_api_key,
            'Content-Type': 'application/json'
        })

        self.results = {
            "searched_books": {},
            "prowlarr_results": {},
            "queued": [],
            "failed": []
        }

    def load_curated_books(self) -> List[Dict[str, Any]]:
        """Load the curated audiobook list"""
        try:
            with open('audiobooks_to_download.json', 'r', encoding='utf-8') as f:
                books = json.load(f)
            print(f"Loaded {len(books)} curated audiobooks")
            return books
        except FileNotFoundError:
            logger.error("audiobooks_to_download.json not found")
            return []
        except Exception as e:
            logger.error(f"Error loading curated books: {e}")
            return []

    def search_prowlarr_for_book(self, book: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search Prowlarr for a specific book
        Returns list of {title, downloadUrl, seeders, size, indexer}
        """
        search_query = book['search_query']
        print(f"Searching Prowlarr for: {search_query}")

        search_url = f"{self.prowlarr_url}/api/v1/search?query={quote(search_query)}&type=search"

        results = []

        try:
            time.sleep(1)  # Rate limiting
            response = self.session.get(search_url, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Prowlarr search failed for {search_query}: {response.status_code}")
                return results

            data = response.json()

            for item in data:
                if not item.get('downloadUrl'):
                    continue

                found_title = item.get('title', '')
                if not found_title:
                    continue

                # Check if this is a reasonable match (contains key terms)
                if self._is_book_match(book, found_title):
                    result = {
                        'search_query': search_query,
                        'book_title': book['title'],
                        'book_author': book['author'],
                        'book_genre': book['genre'],
                        'found_title': found_title,
                        'downloadUrl': item['downloadUrl'],
                        'seeders': item.get('seeders', 0),
                        'size': item.get('size', 0),
                        'indexer': item.get('indexer', ''),
                        'guid': item.get('guid', ''),
                        'categories': item.get('categories', [])
                    }

                    results.append(result)
                    print(f"  Found: {found_title} (seeders: {result['seeders']})")

        except Exception as e:
            logger.error(f"Error searching Prowlarr for {search_query}: {e}")

        return results

    def _is_book_match(self, book: Dict[str, Any], found_title: str) -> bool:
        """Check if found title matches our book criteria"""
        search_lower = found_title.lower().strip()
        title_lower = book['title'].lower().strip()
        author_lower = book['author'].lower().strip()

        # Must contain audiobook or audio indicators
        audio_indicators = ['audiobook', 'audio', 'mp3', 'm4b', 'aac']
        has_audio = any(indicator in search_lower for indicator in audio_indicators)

        # Must contain title keywords
        title_words = title_lower.split()
        title_matches = sum(1 for word in title_words if word in search_lower)

        # Must contain author keywords
        author_words = author_lower.split()
        author_matches = sum(1 for word in author_words if word in search_lower)

        # Reasonable match criteria
        return has_audio and (title_matches >= 2 or author_matches >= 1)

    async def queue_to_qbittorrent(self, prowlarr_results: List[Dict[str, Any]]) -> int:
        """Queue found results to qBittorrent"""
        print("Queuing audiobooks to qBittorrent...")

        queued_count = 0

        try:
            async with QBittorrentClient(self.qb_url, self.qb_user, self.qb_pass) as qb:
                for result in prowlarr_results:
                    try:
                        # Download torrent file from Prowlarr
                        download_url = result['downloadUrl']
                        torrent_response = requests.get(download_url, timeout=30)

                        if torrent_response.status_code != 200:
                            logger.warning(f"Failed to download torrent for {result['found_title']}: {torrent_response.status_code}")
                            print(f"  [FAIL] {result['book_title']}: Failed to download torrent")
                            self.results["failed"].append({
                                'book': result['book_title'],
                                'reason': f'HTTP {torrent_response.status_code}'
                            })
                            continue

                        torrent_data = torrent_response.content

                        # Add to qBittorrent
                        result_status = await qb.add_torrent(
                            torrent_data,
                            category="audiobooks",
                            paused=False
                        )

                        if result_status.get('success'):
                            queued_count += 1
                            print(f"  [OK] {result['book_title']} -> {result['found_title']}")
                            self.results["queued"].append({
                                'book_title': result['book_title'],
                                'book_author': result['book_author'],
                                'book_genre': result['book_genre'],
                                'found_title': result['found_title'],
                                'seeders': result['seeders'],
                                'indexer': result['indexer'],
                                'size': result['size']
                            })
                        else:
                            error_msg = result_status.get('error', 'Unknown error')
                            logger.error(f"Failed to queue {result['found_title']}: {error_msg}")
                            print(f"  [ERROR] {result['book_title']}: {error_msg}")
                            self.results["failed"].append({
                                'book': result['book_title'],
                                'reason': error_msg
                            })

                    except Exception as e:
                        logger.error(f"Error queuing {result['book_title']}: {e}")
                        print(f"  [ERROR] {result['book_title']}: {str(e)}")
                        self.results["failed"].append({
                            'book': result['book_title'],
                            'reason': str(e)
                        })

                    time.sleep(0.5)  # Rate limiting

        except Exception as e:
            logger.error(f"qBittorrent connection error: {e}")
            print(f"WARNING: Could not connect to qBittorrent: {e}")

        print(f"Total queued: {queued_count} audiobooks")
        return queued_count

    def save_report(self):
        """Save results to JSON"""
        report_file = f"prowlarr_curated_search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, indent=2, ensure_ascii=False)
            logger.info(f"Report saved to {report_file}")
            print(f"Report saved: {report_file}")
        except Exception as e:
            logger.error(f"Could not save report: {e}")

    async def run(self):
        """Execute complete workflow"""
        print("=" * 120)
        print("PROWLARR CURATED AUDIOBOOK SEARCH")
        print("=" * 120)
        print(f"Start: {datetime.now().isoformat()}")

        try:
            # Step 1: Load curated books
            print("\n" + "=" * 80)
            print("LOADING CURATED AUDIOBOOKS")
            print("=" * 80)

            curated_books = self.load_curated_books()
            if not curated_books:
                print("No curated books found!")
                return

            # Step 2: Search Prowlarr for each book
            print("\n" + "=" * 80)
            print("SEARCHING PROWLARR")
            print("=" * 80)

            all_prowlarr_results = []
            for book in curated_books:
                results = self.search_prowlarr_for_book(book)
                book_key = f"{book['title']} by {book['author']}"
                self.results["prowlarr_results"][book_key] = results
                self.results["searched_books"][book_key] = len(results)

                # Take the best result (highest seeders) for each book
                if results:
                    best_result = max(results, key=lambda x: x['seeders'])
                    all_prowlarr_results.append(best_result)

            print(f"Found {len(all_prowlarr_results)} downloadable audiobooks")

            # Step 3: Queue to qBittorrent
            print("\n" + "=" * 80)
            print("QUEUING TO QBITTORRENT")
            print("=" * 80)

            queued_count = await self.queue_to_qbittorrent(all_prowlarr_results)

            # Step 4: Save report
            self.save_report()

            print("\n" + "=" * 120)
            print("WORKFLOW COMPLETE")
            print("=" * 120)
            print(f"Books searched: {len(curated_books)}")
            print(f"Books found: {len(all_prowlarr_results)}")
            print(f"Books queued: {queued_count}")
            print(f"Books failed: {len(self.results['failed'])}")
            print(f"End: {datetime.now().isoformat()}\n")

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            print(f"\nError: {e}")


async def main():
    search = ProwlarrCuratedSearch()
    await search.run()


if __name__ == '__main__':
    asyncio.run(main())