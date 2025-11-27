#!/usr/bin/env python3
"""
Prowlarr-Based Title Search for William D. Arand
===============================================

Search for specific titles using Prowlarr and queue to qBittorrent if missing.
- Privateer's Commission series
- Incubus Inc Book 3

Uses the successful workflow from AUTHOR_SEARCH_WORKFLOW_TEMPLATE.md
"""

import sys
import os
import time
import json
import logging
import re
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
        logging.FileHandler('prowlarr_title_search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import requests
    from backend.integrations.abs_client import AudiobookshelfClient
    from backend.integrations.qbittorrent_client import QBittorrentClient
except ImportError as e:
    logger.error(f"Missing required library: {e}")
    sys.exit(1)


class ProwlarrTitleSearch:
    """
    Search for specific titles using Prowlarr and queue to qBittorrent if missing
    """

    TARGET_TITLES = [
        # Privateer's Commission series
        "Privateer's Commission",
        "Privateer's Bounty",
        "Privateer's Empire",
        "Privateer's Legacy",

        # Incubus Inc series
        "Incubus Inc Book 3",
        "Incubus Inc 3",
        "Incubus Inc: Book 3"
    ]

    def __init__(self):
        self.prowlarr_url = os.getenv('PROWLARR_URL', 'http://localhost:9696')
        self.prowlarr_api_key = os.getenv('PROWLARR_API_KEY')

        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN')

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
            "searched_titles": {},
            "prowlarr_results": {},
            "abs_library": {},
            "missing_titles": [],
            "queued": []
        }

    def search_prowlarr_for_title(self, title: str) -> List[Dict[str, Any]]:
        """
        Search Prowlarr for a specific title
        Returns list of {title, downloadUrl, seeders, size, indexer}
        """
        print(f"Searching Prowlarr for: {title}")

        search_url = f"{self.prowlarr_url}/api/v1/search?query={quote(title)}&type=search"

        results = []

        try:
            time.sleep(1)  # Rate limiting
            response = self.session.get(search_url, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Prowlarr search failed for {title}: {response.status_code}")
                return results

            data = response.json()

            for item in data:
                if not item.get('downloadUrl'):
                    continue

                found_title = item.get('title', '')
                if not found_title:
                    continue

                # Check if this is a close match to our target title
                if self._is_title_match(title, found_title):
                    result = {
                        'search_title': title,
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
            logger.error(f"Error searching Prowlarr for {title}: {e}")

        return results

    def _is_title_match(self, search_title: str, found_title: str) -> bool:
        """Check if found title matches our search criteria"""
        search_lower = search_title.lower().strip()
        found_lower = found_title.lower().strip()

        # Exact match
        if search_lower in found_lower:
            return True

        # Handle series book numbering
        if "privateer's commission" in search_lower and "privateer" in found_lower:
            return True

        if "incubus inc" in search_lower and "incubus" in found_lower:
            # Check for book 3 specifically
            if "book 3" in search_lower and ("book 3" in found_lower or "3" in found_lower.split()[-2:]):
                return True

        return False

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison"""
        normalized = title.lower().strip()
        # Remove series/book info
        normalized = re.sub(r'\s*\(.*?(?:book|series|part|vol).*?\)\s*', '', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'[\[\]]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    async def get_abs_library_books(self) -> Dict[str, List[str]]:
        """Get all books from Audiobookshelf"""
        print("Querying Audiobookshelf library...")

        try:
            async with AudiobookshelfClient(self.abs_url, self.abs_token) as client:
                library_items = await client.get_library_items(limit=500)

                books_by_author = {}
                for item in library_items:
                    metadata = item.get('media', {}).get('metadata', {})
                    title = metadata.get('title', '')

                    # Get authors
                    authors = metadata.get('authors', [])
                    if not authors:
                        author_name = metadata.get('authorName', '')
                        if author_name:
                            authors = [author_name]

                    for author in authors:
                        author_name = author if isinstance(author, str) else author.get('name', '')
                        if author_name == 'William D. Arand':
                            if author_name not in books_by_author:
                                books_by_author[author_name] = []
                            books_by_author[author_name].append(title)

                return books_by_author

        except Exception as e:
            logger.error(f"Audiobookshelf error: {e}")
            return {}

    def identify_missing_titles(self) -> List[Dict[str, Any]]:
        """Compare Prowlarr results with Audiobookshelf library"""
        print("Identifying missing titles...")

        missing = []
        abs_books = self.results["abs_library"].get('William D. Arand', [])

        # Normalize ABS book titles
        abs_normalized = {self._normalize_title(b) for b in abs_books}

        for title, prowlarr_results in self.results["prowlarr_results"].items():
            for prowlarr_book in prowlarr_results:
                prowlarr_normalized = self._normalize_title(prowlarr_book['found_title'])

                if prowlarr_normalized not in abs_normalized:
                    missing.append(prowlarr_book)
                    print(f"  Missing: {prowlarr_book['found_title']}")

        self.results["missing_titles"] = missing
        return missing

    async def queue_missing_to_qbittorrent(self) -> int:
        """Queue missing titles to qBittorrent"""
        print("Queuing missing titles to qBittorrent...")

        queued_count = 0

        try:
            async with QBittorrentClient(self.qb_url, self.qb_user, self.qb_pass) as qb:
                for book in self.results["missing_titles"]:
                    try:
                        # Download torrent file from Prowlarr
                        download_url = book['downloadUrl']
                        torrent_response = requests.get(download_url, timeout=30)

                        if torrent_response.status_code != 200:
                            logger.warning(f"Failed to download torrent for {book['found_title']}: {torrent_response.status_code}")
                            print(f"  - {book['found_title']}: Failed to download torrent")
                            continue

                        torrent_data = torrent_response.content

                        # Add to qBittorrent
                        result = await qb.add_torrent(
                            torrent_data,
                            category="audiobooks",
                            paused=False
                        )

                        if result.get('success'):
                            queued_count += 1
                            print(f"  [OK] {book['found_title']}")
                            self.results["queued"].append({
                                'title': book['found_title'],
                                'search_title': book['search_title'],
                                'seeders': book['seeders'],
                                'indexer': book['indexer']
                            })
                        else:
                            logger.error(f"Failed to queue {book['found_title']}: {result.get('error')}")
                            print(f"  [ERROR] {book['found_title']}: {result.get('error')}")

                    except Exception as e:
                        logger.error(f"Error queuing {book['found_title']}: {e}")
                        print(f"  [ERROR] {book['found_title']}: {str(e)}")

                    time.sleep(0.5)  # Rate limiting

        except Exception as e:
            logger.error(f"qBittorrent connection error: {e}")
            print(f"WARNING: Could not connect to qBittorrent: {e}")

        print(f"Total queued: {queued_count} audiobooks")
        return queued_count

    def save_report(self):
        """Save results to JSON"""
        report_file = f"prowlarr_title_search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, indent=2, ensure_ascii=False)
            logger.info(f"Report saved to {report_file}")
            print(f"Report saved: {report_file}")
        except Exception as e:
            logger.error(f"Could not save report: {e}")

    async def run(self):
        """Execute complete workflow"""
        print("=" * 80)
        print("PROWLARR TITLE SEARCH - WILLIAM D. ARAND")
        print("=" * 80)
        print(f"Start: {datetime.now().isoformat()}")
        print(f"Target titles: {len(self.TARGET_TITLES)}")

        try:
            # Step 1: Search Prowlarr for each title
            print("\n" + "=" * 80)
            print("SEARCHING PROWLARR")
            print("=" * 80)

            for title in self.TARGET_TITLES:
                results = self.search_prowlarr_for_title(title)
                self.results["prowlarr_results"][title] = results
                self.results["searched_titles"][title] = len(results)

            # Step 2: Get Audiobookshelf library
            print("\n" + "=" * 80)
            print("QUERYING AUDIOBOOKSHELF")
            print("=" * 80)

            abs_books = await self.get_abs_library_books()
            self.results["abs_library"] = abs_books

            arand_books = abs_books.get('William D. Arand', [])
            print(f"William D. Arand books in library: {len(arand_books)}")

            # Step 3: Identify missing
            self.identify_missing_titles()

            # Step 4: Queue missing
            await self.queue_missing_to_qbittorrent()

            # Step 5: Save report
            self.save_report()

            print("\n" + "=" * 80)
            print("WORKFLOW COMPLETE")
            print("=" * 80)
            print(f"End: {datetime.now().isoformat()}\n")

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            print(f"\nError: {e}")


async def main():
    search = ProwlarrTitleSearch()
    await search.run()


if __name__ == '__main__':
    asyncio.run(main())