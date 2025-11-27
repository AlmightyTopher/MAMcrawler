#!/usr/bin/env python3
"""
Specific Title Search for William D. Arand
==========================================

Search MAM for specific titles/series and add to qBittorrent queue if missing.
- Privateer's Commission series
- Incubus Inc Book 3
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
from urllib.parse import quote, urljoin

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
        logging.FileHandler('specific_title_search.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import requests
    from bs4 import BeautifulSoup
    import qbittorrentapi
    from backend.integrations.abs_client import AudiobookshelfClient
    from backend.integrations.qbittorrent_client import QBittorrentClient
except ImportError as e:
    logger.error(f"Missing required library: {e}")
    sys.exit(1)


class SpecificTitleSearch:
    """
    Search for specific titles by William D. Arand and add to queue if missing
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
        self.mam_url = "https://www.myanonamouse.net"
        self.mam_username = os.getenv('MAM_USERNAME')
        self.mam_password = os.getenv('MAM_PASSWORD')

        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN')

        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD')

        # For MAM searches
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        self.results = {
            "searched_titles": {},
            "mam_results": {},
            "abs_library": {},
            "missing_titles": [],
            "queued": []
        }

    def search_mam_for_title(self, title: str) -> List[Dict[str, Any]]:
        """
        Search MAM for a specific title
        Returns list of {title, author, url, torrent_id}
        """
        print(f"Searching MAM for: {title}")

        search_url = (
            f"{self.mam_url}/tor/browse.php"
            f"?tor[searchstr]={quote(title)}"
            f"&tor[cat][]=13"  # Audiobooks
            f"&tor[searchType]=all"
            f"&tor[searchIn]=torrents"
        )

        results = []

        try:
            time.sleep(2)  # Rate limiting
            response = requests.get(search_url, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Search failed for {title}: {response.status_code}")
                return results

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all torrent entries
            rows = soup.find_all('tr')

            for row in rows:
                # Find torrent link in this row
                torrent_link = row.find('a', href=re.compile(r'/t/\d+'))
                if not torrent_link:
                    continue

                found_title = torrent_link.get_text(strip=True)
                torrent_id_match = re.search(r'/t/(\d+)', torrent_link.get('href', ''))

                if not found_title or not torrent_id_match:
                    continue

                # Check if this is a close match to our target title
                if self._is_title_match(title, found_title):
                    torrent_id = torrent_id_match.group(1)
                    torrent_info = {
                        'search_title': title,
                        'found_title': found_title,
                        'author': 'William D. Arand',
                        'torrent_id': torrent_id,
                        'url': urljoin(self.mam_url, f"/t/{torrent_id}/")
                    }

                    results.append(torrent_info)
                    print(f"  Found: {found_title}")

        except Exception as e:
            logger.error(f"Error searching for {title}: {e}")

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

    def extract_magnet_from_torrent_page(self, torrent_id: str) -> Optional[str]:
        """Extract magnet link from torrent details page"""
        try:
            torrent_url = f"{self.mam_url}/t/{torrent_id}/"
            time.sleep(1)

            response = requests.get(torrent_url, timeout=30)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for magnet link
            magnet_link = soup.find('a', href=re.compile(r'^magnet:\?'))
            if magnet_link:
                return magnet_link.get('href')

            return None

        except Exception as e:
            logger.error(f"Error extracting magnet for {torrent_id}: {e}")
            return None

    def identify_missing_titles(self) -> List[Dict[str, Any]]:
        """Compare MAM results with Audiobookshelf library"""
        print("Identifying missing titles...")

        missing = []
        abs_books = self.results["abs_library"].get('William D. Arand', [])

        # Normalize ABS book titles
        abs_normalized = {self._normalize_title(b) for b in abs_books}

        for title, mam_results in self.results["mam_results"].items():
            for mam_book in mam_results:
                mam_normalized = self._normalize_title(mam_book['found_title'])

                if mam_normalized not in abs_normalized:
                    missing.append(mam_book)
                    print(f"  Missing: {mam_book['found_title']}")

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
                        magnet_link = self.extract_magnet_from_torrent_page(book['torrent_id'])

                        if not magnet_link:
                            logger.warning(f"No magnet for {book['found_title']}")
                            print(f"  - {book['found_title']}: No magnet link found")
                            continue

                        # Add to qBittorrent
                        result = await qb.add_torrent(
                            magnet_link,
                            category="audiobooks",
                            paused=False
                        )

                        if result.get('success'):
                            queued_count += 1
                            print(f"  [OK] {book['found_title']}")
                            self.results["queued"].append({
                                'title': book['found_title'],
                                'search_title': book['search_title'],
                                'torrent_id': book['torrent_id']
                            })
                        else:
                            logger.error(f"Failed to queue {book['found_title']}")
                            print(f"  [ERROR] {book['found_title']}: {result.get('error')}")

                    except Exception as e:
                        logger.error(f"Error queuing {book['found_title']}: {e}")
                        print(f"  [ERROR] {book['found_title']}: {str(e)}")

        except Exception as e:
            logger.error(f"qBittorrent connection error: {e}")
            print(f"WARNING: Could not connect to qBittorrent: {e}")

        print(f"Total queued: {queued_count} audiobooks")
        return queued_count

    def save_report(self):
        """Save results to JSON"""
        report_file = f"specific_title_search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            logger.info(f"Report saved to {report_file}")
            print(f"Report saved: {report_file}")
        except Exception as e:
            logger.error(f"Could not save report: {e}")

    async def run(self):
        """Execute complete workflow"""
        print("=" * 80)
        print("SPECIFIC TITLE SEARCH - WILLIAM D. ARAND")
        print("=" * 80)
        print(f"Start: {datetime.now().isoformat()}")
        print(f"Target titles: {len(self.TARGET_TITLES)}")

        try:
            # Step 1: Search MAM for each title
            print("\n" + "=" * 80)
            print("SEARCHING MAM")
            print("=" * 80)

            for title in self.TARGET_TITLES:
                results = self.search_mam_for_title(title)
                self.results["mam_results"][title] = results
                self.results["searched_titles"][title] = len(results)
                time.sleep(2)

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
    search = SpecificTitleSearch()
    await search.run()


if __name__ == '__main__':
    asyncio.run(main())