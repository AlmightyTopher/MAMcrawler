"""
Automated Weekly Audiobook Batch Downloader
Queries all genres, grabs top N results, adds to qBittorrent automatically.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from audiobook_catalog_crawler import AudiobookCatalogCrawler
from crawl4ai import AsyncWebCrawler
from vip_status_manager import VIPStatusManager

import logging

# Load environment
load_dotenv()


class AutomatedAudiobookBatch:
    """Automated batch processor for weekly audiobook downloads."""

    def __init__(self, config_path: str = "audiobook_auto_config.json"):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        self.crawler = AudiobookCatalogCrawler()

        # Setup logging
        log_file = self.config['notifications']['log_file']
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

        # Track downloads
        self.session_stats = {
            'started_at': datetime.now().isoformat(),
            'genres_processed': 0,
            'audiobooks_found': 0,
            'audiobooks_added': 0,
            'errors': [],
            'skipped': [],
            'downloads': []
        }

    def load_config(self) -> Dict:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            return json.load(f)

    def load_genres_and_timespans(self) -> tuple:
        """Load cached genres and timespans."""
        genres = []
        timespans = []

        if self.crawler.genres_file.exists():
            with open(self.crawler.genres_file, 'r') as f:
                genres = json.load(f)

        if self.crawler.timespans_file.exists():
            with open(self.crawler.timespans_file, 'r') as f:
                timespans = json.load(f)

        return genres, timespans

    def filter_genres(self, genres: List[Dict]) -> List[Dict]:
        """Filter genres based on whitelist or blacklist mode."""
        use_whitelist = self.config['query_settings'].get('use_whitelist', False)

        if use_whitelist:
            # WHITELIST MODE: Only include specified genres
            included = self.config.get('included_genres', [])
            included_lower = [g.lower() for g in included]

            filtered = []
            for genre in genres:
                label = genre.get('label', '').lower()
                if any(incl.lower() in label for incl in included):
                    filtered.append(genre)
                    self.logger.info(f"[INCLUDE] Whitelisted genre: {genre.get('label')}")
                else:
                    self.logger.debug(f"[SKIP] Not in whitelist: {genre.get('label')}")
                    self.session_stats['skipped'].append({
                        'genre': genre.get('label'),
                        'reason': 'not_in_whitelist'
                    })

            return filtered
        else:
            # BLACKLIST MODE: Exclude specified genres
            excluded = self.config.get('excluded_genres', [])
            excluded_lower = [g.lower() for g in excluded]

            filtered = []
            for genre in genres:
                label = genre.get('label', '').lower()
                if not any(excl in label for excl in excluded_lower):
                    filtered.append(genre)
                else:
                    self.logger.info(f"[SKIP] Excluding genre: {genre.get('label')}")
                    self.session_stats['skipped'].append({
                        'genre': genre.get('label'),
                        'reason': 'excluded_in_config'
                    })

            return filtered

    def get_preferred_timespan(self, timespans: List[Dict]) -> Optional[Dict]:
        """Get the preferred timespan from config."""
        preference = self.config['query_settings']['timespan_preference']

        # Try to match preference (e.g., 'recent', 'new', 'latest')
        for timespan in timespans:
            label = timespan.get('label', '').lower()
            if preference in label or 'recent' in label or 'new' in label:
                return timespan

        # Fallback to first timespan
        return timespans[0] if timespans else None

    async def query_genre(self, crawler: AsyncWebCrawler, genre: Dict, timespan: Dict) -> List[Dict]:
        """Query a single genre with the preferred timespan."""
        genre_label = genre.get('label', 'Unknown')
        timespan_label = timespan.get('label', 'Unknown')

        self.logger.info(f"\n[QUERY] {genre_label} | {timespan_label}")

        try:
            # Navigate to audiobooks
            nav_result = await self.crawler.navigate_to_audiobooks(crawler)
            if not nav_result.get('success'):
                self.logger.error(f"[ERROR] Failed to navigate for {genre_label}")
                return []

            # Query with filters
            results = await self.crawler.query_audiobooks(
                crawler,
                genre['value'],
                timespan['value']
            )

            self.logger.info(f"[FOUND] {len(results)} audiobooks in {genre_label}")
            return results

        except Exception as e:
            self.logger.error(f"[ERROR] Query failed for {genre_label}: {e}")
            self.session_stats['errors'].append({
                'genre': genre_label,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return []

    def get_audiobookshelf_library(self):
        """Get all audiobooks from Audiobookshelf library."""
        try:
            import requests

            abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
            abs_token = os.getenv('ABS_TOKEN', '')

            if not abs_token:
                self.logger.warning("[WARNING] ABS_TOKEN not set - duplicate detection disabled")
                return None

            # Get all library items from Audiobookshelf
            headers = {
                'Authorization': f'Bearer {abs_token}'
            }

            # Get libraries
            response = requests.get(f'{abs_url}/api/libraries', headers=headers)
            if response.status_code != 200:
                self.logger.warning(f"[WARNING] Failed to get ABS libraries: {response.status_code}")
                return None

            libraries = response.json().get('libraries', [])

            # Get all items from all libraries
            all_books = []
            for library in libraries:
                library_id = library.get('id')
                lib_response = requests.get(
                    f'{abs_url}/api/libraries/{library_id}/items',
                    headers=headers,
                    params={'limit': 10000}  # Get lots of items
                )

                if lib_response.status_code == 200:
                    items = lib_response.json().get('results', [])
                    all_books.extend(items)

            self.logger.info(f"[INFO] Loaded {len(all_books)} audiobooks from Audiobookshelf")

            return all_books

        except ImportError:
            self.logger.warning("[WARNING] requests library not installed - duplicate detection disabled")
            return None
        except Exception as e:
            self.logger.warning(f"[WARNING] Failed to connect to Audiobookshelf: {e}")
            import traceback
            traceback.print_exc()
            return None

    def is_duplicate(self, audiobook: Dict, abs_library) -> bool:
        """Check if audiobook already exists in Audiobookshelf library."""
        if not abs_library:
            return False  # Can't check, assume not duplicate

        try:
            incoming_title = audiobook.get('title', '').lower()
            if not incoming_title:
                return False

            # Check against all books in Audiobookshelf library
            for book_item in abs_library:
                # Get book metadata
                media = book_item.get('media', {})
                metadata = media.get('metadata', {})

                # Get title from ABS
                abs_title = metadata.get('title', '').lower()
                if not abs_title:
                    continue

                # Clean both titles for comparison
                clean_incoming = self._clean_title_for_comparison(incoming_title)
                clean_abs = self._clean_title_for_comparison(abs_title)

                # Check for substantial overlap
                if clean_incoming in clean_abs or clean_abs in clean_incoming:
                    # Additional check: similar length (prevent false matches)
                    len_ratio = min(len(clean_incoming), len(clean_abs)) / max(len(clean_incoming), len(clean_abs))
                    if len_ratio > 0.6:  # 60% length similarity
                        # Found duplicate!
                        author = metadata.get('authorName', 'Unknown Author')
                        self.logger.debug(f"    Match found: '{abs_title}' by {author}")
                        return True

            return False

        except Exception as e:
            self.logger.warning(f"[WARNING] Duplicate check failed: {e}")
            return False  # Assume not duplicate on error

    def _clean_title_for_comparison(self, title: str) -> str:
        """Clean title for duplicate comparison."""
        import re

        # Remove common audiobook suffixes
        title = re.sub(r'\s*\(unabridged\)\s*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*\(audiobook\)\s*', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*audiobook\s*', '', title, flags=re.IGNORECASE)

        # Remove file extensions
        title = re.sub(r'\.(mp3|m4b|m4a|flac)$', '', title, flags=re.IGNORECASE)

        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title)

        return title.strip()

    def select_top_n(self, audiobooks: List[Dict], n: int, genre: str, abs_library=None) -> List[Dict]:
        """
        Select top N NEW audiobooks from results (skips duplicates).

        Checks up to max_check_limit (default 100) to find N unique books.
        Skips audiobooks already in Audiobookshelf library.

        Args:
            audiobooks: List of audiobook results
            n: Number of NEW books to select
            genre: Genre name (for logging)
            abs_library: Audiobookshelf library data

        Returns:
            List of up to N non-duplicate audiobooks
        """
        if not self.config['query_settings'].get('skip_duplicates', False):
            # Duplicate checking disabled
            return audiobooks[:n]

        max_check = self.config['query_settings'].get('max_check_limit', 100)
        selected = []
        checked = 0
        skipped = 0

        self.logger.info(f"[FILTER] Finding {n} new books (checking up to top {max_check})")

        for audiobook in audiobooks[:max_check]:
            checked += 1

            # Check if duplicate
            if abs_library and self.is_duplicate(audiobook, abs_library):
                title = audiobook.get('title', 'Unknown')
                self.logger.info(f"  [{checked}] SKIP (duplicate): {title}")
                skipped += 1
                self.session_stats['skipped'].append({
                    'title': title,
                    'genre': genre,
                    'reason': 'duplicate_in_audiobookshelf'
                })
                continue

            # Not a duplicate, add to selected
            title = audiobook.get('title', 'Unknown')
            self.logger.info(f"  [{checked}] SELECT (new): {title}")
            selected.append(audiobook)

            # Stop if we have enough
            if len(selected) >= n:
                break

        self.logger.info(f"[RESULT] Selected {len(selected)} new books (skipped {skipped} duplicates, checked {checked} total)")

        return selected

    async def add_to_qbittorrent(self, audiobook: Dict, genre: str) -> bool:
        """Add audiobook to qBittorrent."""
        link = audiobook.get('link')

        if not link:
            self.logger.warning(f"[SKIP] No download link for: {audiobook.get('title')}")
            return False

        # Check dry-run mode
        if self.config['download_settings']['dry_run']:
            self.logger.info(f"[DRY-RUN] Would add: {audiobook.get('title')}")
            self.session_stats['audiobooks_added'] += 1
            self.session_stats['downloads'].append({
                'title': audiobook.get('title'),
                'genre': genre,
                'link': link,
                'dry_run': True,
                'timestamp': datetime.now().isoformat()
            })
            return True

        try:
            import qbittorrentapi

            qb_host = os.getenv('QB_HOST', 'localhost')
            qb_port = os.getenv('QB_PORT', '8080')
            qb_username = os.getenv('QB_USERNAME', 'admin')
            qb_password = os.getenv('QB_PASSWORD', 'adminadmin')

            qbt_client = qbittorrentapi.Client(
                host=qb_host,
                port=qb_port,
                username=qb_username,
                password=qb_password
            )

            qbt_client.auth_log_in()

            # Add with category
            category = self.config['download_settings']['category']
            save_path = self.config['download_settings']['save_path']

            add_params = {'urls': link}
            if category:
                add_params['category'] = category
            if save_path:
                add_params['save_path'] = save_path

            qbt_client.torrents_add(**add_params)

            self.logger.info(f"[ADDED] {audiobook.get('title')} -> qBittorrent")
            self.session_stats['audiobooks_added'] += 1
            self.session_stats['downloads'].append({
                'title': audiobook.get('title'),
                'genre': genre,
                'link': link,
                'category': category,
                'timestamp': datetime.now().isoformat()
            })
            return True

        except ImportError:
            self.logger.error("[ERROR] qbittorrent-api not installed")
            return False
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to add to qBittorrent: {e}")
            self.session_stats['errors'].append({
                'audiobook': audiobook.get('title'),
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return False

    async def process_all_genres(self):
        """Main processing loop - query all genres and download top N."""
        self.logger.info("="*70)
        self.logger.info("AUTOMATED AUDIOBOOK BATCH DOWNLOAD")
        self.logger.info("="*70)

        # Load genres and timespans
        genres, timespans = self.load_genres_and_timespans()

        if not genres or not timespans:
            self.logger.error("[ERROR] No genres/timespans found. Run discovery first:")
            self.logger.error("  python audiobook_catalog_crawler.py")
            return

        # Filter genres
        use_whitelist = self.config['query_settings'].get('use_whitelist', False)
        active_genres = self.filter_genres(genres)

        if use_whitelist:
            included = self.config.get('included_genres', [])
            self.logger.info(f"\n[INFO] WHITELIST MODE: Only downloading {', '.join(included)}")
            self.logger.info(f"[INFO] Processing {len(active_genres)} matching genres (skipped {len(genres) - len(active_genres)})")
        else:
            excluded = self.config.get('excluded_genres', [])
            self.logger.info(f"\n[INFO] BLACKLIST MODE: Excluding {', '.join(excluded)}")
            self.logger.info(f"[INFO] Processing {len(active_genres)} genres (excluded {len(genres) - len(active_genres)})")

        # Get preferred timespan
        preferred_timespan = self.get_preferred_timespan(timespans)
        if not preferred_timespan:
            self.logger.error("[ERROR] No timespan available")
            return

        self.logger.info(f"[INFO] Using timespan: {preferred_timespan.get('label')}")

        # Get settings
        top_n = self.config['query_settings']['top_n_per_genre']
        self.logger.info(f"[INFO] Top {top_n} audiobooks per genre")

        if self.config['download_settings']['dry_run']:
            self.logger.info("[INFO] DRY-RUN MODE - No actual downloads")

        # Connect to Audiobookshelf for duplicate checking
        abs_library = None
        if self.config['query_settings'].get('skip_duplicates', False):
            self.logger.info("[INFO] Duplicate detection enabled - connecting to Audiobookshelf...")
            abs_library = self.get_audiobookshelf_library()
            if abs_library:
                self.logger.info(f"[INFO] Found {len(abs_library)} audiobooks in Audiobookshelf library")
            else:
                self.logger.warning("[WARNING] Could not connect to Audiobookshelf - duplicate detection disabled")

        # Create browser
        browser_config = self.crawler.create_browser_config()

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Process each genre
            for i, genre in enumerate(active_genres, 1):
                genre_label = genre.get('label', 'Unknown')

                self.logger.info(f"\n{'='*70}")
                self.logger.info(f"GENRE {i}/{len(active_genres)}: {genre_label}")
                self.logger.info(f"{'='*70}")

                # Query this genre
                audiobooks = await self.query_genre(crawler, genre, preferred_timespan)

                if not audiobooks:
                    self.logger.warning(f"[SKIP] No results for {genre_label}")
                    continue

                # Select top N (with duplicate checking)
                top_audiobooks = self.select_top_n(audiobooks, top_n, genre_label, abs_library)
                self.logger.info(f"[SELECT] Selected {len(top_audiobooks)} NEW books from {len(audiobooks)} results")

                self.session_stats['genres_processed'] += 1
                self.session_stats['audiobooks_found'] += len(audiobooks)

                # Add each to qBittorrent
                for j, audiobook in enumerate(top_audiobooks, 1):
                    title = audiobook.get('title', 'Unknown')
                    self.logger.info(f"\n  [{j}/{len(top_audiobooks)}] {title}")

                    if self.config['download_settings']['auto_add_to_qbittorrent']:
                        await self.add_to_qbittorrent(audiobook, genre_label)
                    else:
                        self.logger.info(f"  [SKIP] Auto-add disabled in config")

                    # Small delay between downloads
                    await asyncio.sleep(1)

                # Delay between genres to be polite
                if i < len(active_genres):
                    self.logger.info(f"\n[WAIT] Pausing before next genre...")
                    await asyncio.sleep(5)

        # Generate final report
        self.generate_report()

        # Maintain VIP status and spend remaining points
        self.maintain_vip_status()

    def generate_report(self):
        """Generate and save summary report."""
        self.session_stats['completed_at'] = datetime.now().isoformat()

        # Count duplicates separately
        duplicates = [s for s in self.session_stats['skipped'] if s.get('reason') == 'duplicate_in_audiobookshelf']
        other_skipped = [s for s in self.session_stats['skipped'] if s.get('reason') != 'duplicate_in_audiobookshelf']

        report = "\n" + "="*70 + "\n"
        report += "BATCH DOWNLOAD SUMMARY\n"
        report += "="*70 + "\n\n"
        report += f"Started:  {self.session_stats['started_at']}\n"
        report += f"Finished: {self.session_stats['completed_at']}\n\n"
        report += f"Genres Processed:    {self.session_stats['genres_processed']}\n"
        report += f"Audiobooks Found:    {self.session_stats['audiobooks_found']}\n"
        report += f"Audiobooks Added:    {self.session_stats['audiobooks_added']}\n"
        report += f"Duplicates Skipped:  {len(duplicates)}\n"
        report += f"Other Skipped:       {len(other_skipped)}\n"
        report += f"Errors:              {len(self.session_stats['errors'])}\n"

        if self.config['download_settings']['dry_run']:
            report += "\n[DRY-RUN MODE] No actual downloads performed\n"

        # Show duplicate detection stats
        if duplicates:
            report += "\n" + "-"*70 + "\n"
            report += f"DUPLICATES SKIPPED ({len(duplicates)} already in Audiobookshelf):\n"
            report += "-"*70 + "\n"
            for dup in duplicates[:20]:  # First 20 duplicates
                genre = dup.get('genre', 'Unknown')
                title = dup.get('title', 'Unknown')
                report += f"  - [{genre}] {title}\n"

            if len(duplicates) > 20:
                report += f"  ... and {len(duplicates) - 20} more duplicates\n"

        if self.session_stats['downloads']:
            report += "\n" + "-"*70 + "\n"
            report += "DOWNLOADS:\n"
            report += "-"*70 + "\n"
            for dl in self.session_stats['downloads'][:20]:  # First 20
                report += f"  - [{dl['genre']}] {dl['title']}\n"

            if len(self.session_stats['downloads']) > 20:
                report += f"  ... and {len(self.session_stats['downloads']) - 20} more\n"

        if self.session_stats['errors']:
            report += "\n" + "-"*70 + "\n"
            report += "ERRORS:\n"
            report += "-"*70 + "\n"
            for err in self.session_stats['errors'][:10]:
                report += f"  - {err.get('genre', err.get('audiobook', 'Unknown'))}: {err['error']}\n"

        report += "\n" + "="*70 + "\n"

        # Print report
        self.logger.info(report)

        # Save report to file
        if self.config['notifications']['summary_report']:
            report_file = Path(f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            self.logger.info(f"[SAVED] Report saved to {report_file}")

        # Save JSON stats
        stats_file = Path(f"batch_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_stats, f, indent=2)
        self.logger.info(f"[SAVED] Stats saved to {stats_file}")

    def maintain_vip_status(self):
        """
        Maintain VIP status and spend remaining bonus points.

        Priority:
        1. Renew VIP if below 7 days remaining (never let VIP drop below 1 week)
        2. Reserve 1,250 points for 7-day VIP buffer
        3. Spend remaining points on upload credit (ratio improvement)
        """
        self.logger.info("\n" + "="*70)
        self.logger.info("VIP STATUS MAINTENANCE")
        self.logger.info("="*70)

        try:
            # Initialize VIP manager
            vip_manager = VIPStatusManager(logger=self.logger)

            # Check if dry-run mode
            dry_run = self.config['download_settings'].get('dry_run', False)

            # Maintain VIP status and spend remaining points
            result = vip_manager.check_and_maintain_vip(dry_run=dry_run)

            # Add VIP maintenance results to session stats
            self.session_stats['vip_maintenance'] = result

            # Log summary
            if 'error' not in result:
                self.logger.info("\n" + "-"*70)
                self.logger.info("VIP MAINTENANCE COMPLETE")
                self.logger.info("-"*70)
                self.logger.info(f"VIP Days Added:       {result.get('vip_days_added', 0)} days")
                self.logger.info(f"Upload Credit Added:  {result.get('upload_gb_added', 0)} GB")
                self.logger.info(f"Points Remaining:     {result.get('remaining_points', 0):,}")
                self.logger.info(f"VIP Buffer Reserved:  {result.get('vip_buffer_reserved', 0):,.0f} points")
                self.logger.info("-"*70)
            else:
                self.logger.warning(f"[VIP] Maintenance error: {result.get('error')}")

        except Exception as e:
            self.logger.error(f"[VIP] VIP maintenance failed: {e}")
            import traceback
            traceback.print_exc()

        self.logger.info("="*70)


async def main():
    """Entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Automated audiobook batch downloader")
    parser.add_argument('--config', default='audiobook_auto_config.json', help='Config file path')
    parser.add_argument('--dry-run', action='store_true', help='Run without actually downloading')
    args = parser.parse_args()

    try:
        batch = AutomatedAudiobookBatch(config_path=args.config)

        # Override dry-run if specified
        if args.dry_run:
            batch.config['download_settings']['dry_run'] = True

        await batch.process_all_genres()

    except KeyboardInterrupt:
        print("\n[CANCELLED] Batch process interrupted by user")
    except Exception as e:
        print(f"[ERROR] Batch process failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
