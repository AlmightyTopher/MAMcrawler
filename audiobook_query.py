"""
Interactive Audiobook Query CLI
Allows querying the audiobook catalog by genre and timespan,
and adding results to qBittorrent.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

from audiobook_catalog_crawler import AudiobookCatalogCrawler
from crawl4ai import AsyncWebCrawler

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AudiobookQueryInterface:
    """Interactive interface for querying audiobook catalog."""

    def __init__(self):
        self.crawler = AudiobookCatalogCrawler()
        self.genres = []
        self.timespans = []

        # Load cached filters if available
        self.load_filters()

    def load_filters(self):
        """Load genres and timespans from cache."""
        try:
            if self.crawler.genres_file.exists():
                with open(self.crawler.genres_file, 'r') as f:
                    self.genres = json.load(f)
                logger.info(f"✅ Loaded {len(self.genres)} genres from cache")

            if self.crawler.timespans_file.exists():
                with open(self.crawler.timespans_file, 'r') as f:
                    self.timespans = json.load(f)
                logger.info(f"✅ Loaded {len(self.timespans)} timespans from cache")

        except Exception as e:
            logger.warning(f"⚠️  Could not load filters from cache: {e}")

    async def refresh_filters(self):
        """Refresh genre and timespan filters from the website."""
        print("\n🔄 Refreshing filters from website...")

        result = await self.crawler.discover_site_structure()

        if result.get('success'):
            filters = result['filters']
            self.genres = filters.get('genres', [])
            self.timespans = filters.get('timespans', [])

            print(f"✅ Loaded {len(self.genres)} genres and {len(self.timespans)} timespans")
        else:
            print(f"❌ Failed to refresh filters: {result.get('error')}")

    def display_genres(self):
        """Display available genres."""
        print("\n📚 AVAILABLE GENRES:")
        print("=" * 50)

        if not self.genres:
            print("⚠️  No genres available. Run 'refresh' first.")
            return

        for i, genre in enumerate(self.genres, 1):
            label = genre.get('label', 'Unknown')
            value = genre.get('value', '')
            print(f"  {i}. {label}")

    def display_timespans(self):
        """Display available timespans."""
        print("\n📅 AVAILABLE TIMESPANS:")
        print("=" * 50)

        if not self.timespans:
            print("⚠️  No timespans available. Run 'refresh' first.")
            return

        for i, timespan in enumerate(self.timespans, 1):
            label = timespan.get('label', 'Unknown')
            value = timespan.get('value', '')
            print(f"  {i}. {label}")

    async def query_audiobooks(self, genre_idx: int, timespan_idx: int) -> List[Dict[str, Any]]:
        """
        Query audiobooks by genre and timespan indices.

        Args:
            genre_idx: Genre index (1-based)
            timespan_idx: Timespan index (1-based)

        Returns:
            List of audiobook results
        """
        if genre_idx < 1 or genre_idx > len(self.genres):
            print(f"❌ Invalid genre index: {genre_idx}")
            return []

        if timespan_idx < 1 or timespan_idx > len(self.timespans):
            print(f"❌ Invalid timespan index: {timespan_idx}")
            return []

        genre = self.genres[genre_idx - 1]
        timespan = self.timespans[timespan_idx - 1]

        print(f"\n🔍 Querying: {genre['label']} | {timespan['label']}")
        print("=" * 50)

        browser_config = self.crawler.create_browser_config()

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Navigate to audiobooks first
            nav_result = await self.crawler.navigate_to_audiobooks(crawler)

            if not nav_result.get('success'):
                print(f"❌ Failed to navigate: {nav_result.get('error')}")
                return []

            # Query with selected filters
            results = await self.crawler.query_audiobooks(
                crawler,
                genre['value'],
                timespan['value']
            )

            return results

    def display_results(self, audiobooks: List[Dict[str, Any]]):
        """Display audiobook search results."""
        print(f"\n📖 RESULTS ({len(audiobooks)} audiobooks found):")
        print("=" * 70)

        if not audiobooks:
            print("⚠️  No results found for this query.")
            return

        for i, book in enumerate(audiobooks, 1):
            title = book.get('title', 'Unknown')
            author = book.get('author', '')
            link = book.get('link', '')

            print(f"\n{i}. {title}")
            if author:
                print(f"   Author: {author}")
            if link:
                print(f"   Link: {link}")

            # Show additional info
            for key, value in book.items():
                if key not in ['title', 'author', 'link', 'html_content']:
                    print(f"   {key}: {value}")

    async def add_to_qbittorrent(self, audiobook: Dict[str, Any]) -> bool:
        """
        Add audiobook to qBittorrent download queue.

        Args:
            audiobook: Audiobook dictionary with 'link' key

        Returns:
            True if added successfully
        """
        link = audiobook.get('link')

        if not link:
            print("❌ No download link found for this audiobook")
            return False

        try:
            import qbittorrentapi

            # Load qBittorrent settings from environment or config
            import os
            qb_host = os.getenv('QB_HOST', 'localhost')
            qb_port = os.getenv('QB_PORT', '8080')
            qb_username = os.getenv('QB_USERNAME', 'admin')
            qb_password = os.getenv('QB_PASSWORD', 'adminadmin')

            # Connect to qBittorrent
            qbt_client = qbittorrentapi.Client(
                host=qb_host,
                port=qb_port,
                username=qb_username,
                password=qb_password
            )

            # Check connection
            try:
                qbt_client.auth_log_in()
                logger.info("✅ Connected to qBittorrent")
            except Exception as e:
                print(f"❌ Failed to connect to qBittorrent: {e}")
                print("💡 Make sure qBittorrent Web UI is enabled")
                print("💡 Set QB_HOST, QB_PORT, QB_USERNAME, QB_PASSWORD in .env")
                return False

            # Add torrent
            if link.startswith('magnet:'):
                # Magnet link
                qbt_client.torrents_add(urls=link)
                print(f"✅ Added magnet link to qBittorrent")
                return True
            elif link.startswith('http'):
                # Torrent file URL
                qbt_client.torrents_add(urls=link)
                print(f"✅ Added torrent URL to qBittorrent")
                return True
            else:
                print(f"❌ Unknown link type: {link}")
                return False

        except ImportError:
            print("❌ qbittorrent-api not installed")
            print("💡 Install with: pip install qbittorrent-api")
            return False
        except Exception as e:
            print(f"❌ Error adding to qBittorrent: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def interactive_query(self):
        """Run interactive query session."""
        print("\n" + "=" * 70)
        print("📚 AUDIOBOOK CATALOG QUERY INTERFACE")
        print("=" * 70)

        # Check if filters are loaded
        if not self.genres or not self.timespans:
            print("\n⚠️  No filters loaded. Running discovery...")
            await self.refresh_filters()

        while True:
            print("\n" + "=" * 70)
            print("MAIN MENU")
            print("=" * 70)
            print("1. Show genres")
            print("2. Show timespans")
            print("3. Query audiobooks")
            print("4. Refresh filters")
            print("5. Exit")
            print()

            choice = input("Select option: ").strip()

            if choice == '1':
                self.display_genres()

            elif choice == '2':
                self.display_timespans()

            elif choice == '3':
                # Query audiobooks
                self.display_genres()
                genre_input = input("\nEnter genre number: ").strip()

                try:
                    genre_idx = int(genre_input)
                except ValueError:
                    print("❌ Invalid number")
                    continue

                self.display_timespans()
                timespan_input = input("\nEnter timespan number: ").strip()

                try:
                    timespan_idx = int(timespan_input)
                except ValueError:
                    print("❌ Invalid number")
                    continue

                # Run query
                results = await self.query_audiobooks(genre_idx, timespan_idx)
                self.display_results(results)

                # Ask if user wants to download
                if results:
                    download_choice = input("\nAdd audiobook to qBittorrent? (enter number or 'n' to skip): ").strip()

                    if download_choice.lower() != 'n':
                        try:
                            download_idx = int(download_choice)
                            if 1 <= download_idx <= len(results):
                                audiobook = results[download_idx - 1]
                                await self.add_to_qbittorrent(audiobook)
                            else:
                                print("❌ Invalid audiobook number")
                        except ValueError:
                            print("❌ Invalid input")

            elif choice == '4':
                await self.refresh_filters()

            elif choice == '5':
                print("\n👋 Goodbye!")
                break

            else:
                print("❌ Invalid option")


async def main():
    """Entry point."""
    interface = AudiobookQueryInterface()

    if len(sys.argv) > 1:
        # Command-line mode
        command = sys.argv[1].lower()

        if command == 'refresh':
            await interface.refresh_filters()
        elif command == 'genres':
            interface.display_genres()
        elif command == 'timespans':
            interface.display_timespans()
        elif command == 'query' and len(sys.argv) >= 4:
            genre_idx = int(sys.argv[2])
            timespan_idx = int(sys.argv[3])
            results = await interface.query_audiobooks(genre_idx, timespan_idx)
            interface.display_results(results)
        else:
            print("Usage:")
            print("  python audiobook_query.py                  # Interactive mode")
            print("  python audiobook_query.py refresh           # Refresh filters")
            print("  python audiobook_query.py genres            # Show genres")
            print("  python audiobook_query.py timespans         # Show timespans")
            print("  python audiobook_query.py query <genre#> <timespan#>  # Query")
    else:
        # Interactive mode
        await interface.interactive_query()


if __name__ == "__main__":
    asyncio.run(main())
