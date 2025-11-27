#!/usr/bin/env python3
"""
MAM Email/Password Crawler with Crawl4AI 0.7.6
===============================================
Fresh implementation using reinstalled Crawl4AI
- Email/password based authentication (no cookies required)
- MyAnonamouse audiobook search and extraction
- Magnet link extraction from torrent pages
- qBittorrent integration for queuing downloads
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, quote
import time
import re

if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

from dotenv import load_dotenv
load_dotenv()

print("=" * 120)
print("MAM EMAIL/PASSWORD CRAWLER - CRAWL4AI 0.7.6")
print("=" * 120)
print(f"Start: {datetime.now().isoformat()}")
print()

try:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
    from bs4 import BeautifulSoup
    import qbittorrentapi
except ImportError as e:
    print(f"ERROR: Missing required library: {e}")
    sys.exit(1)


class MAMEmailPasswordCrawler:
    """MAM crawler using email/password authentication with Crawl4AI 0.7.6"""

    def __init__(self, email: str, password: str, qb_url: str, qb_user: str, qb_pass: str):
        self.email = email
        self.password = password
        self.base_url = "https://www.myanonamouse.net"
        self.crawler = None

        self.qb_url = qb_url
        self.qb_user = qb_user
        self.qb_pass = qb_pass
        self.qb_client = None

        self.authenticated = False
        self.results = {"searched": 0, "found": 0, "queued": 0, "failed": 0}

    async def setup(self):
        """Initialize crawler and qBittorrent connection."""
        self.crawler = AsyncWebCrawler()
        await self.crawler.start()
        print(f"✓ Crawler initialized (Crawl4AI 0.7.6)")

        try:
            self.qb_client = qbittorrentapi.Client(
                host=self.qb_url,
                username=self.qb_user,
                password=self.qb_pass,
                RAISE_NOTIMPLEMENTEDERROR_FOR_UNIMPLEMENTED_API_ENDPOINTS=False
            )
            self.qb_client.auth_log_in()
            print(f"✓ qBittorrent connected: {self.qb_url}")
            print()
            return True
        except Exception as e:
            print(f"✗ qBittorrent failed: {e}")
            return False

    async def login(self) -> bool:
        """Login to MAM with email/password using JavaScript form submission."""
        print("STEP 1: Login to MyAnonamouse (email/password)")
        print("-" * 120)

        try:
            login_url = f"{self.base_url}/login.php"

            # JavaScript to fill and submit login form
            login_js = f"""
            console.log('Starting login process...');

            const emailInput = document.querySelector('input[name="email"]');
            const passwordInput = document.querySelector('input[name="password"]');

            if (emailInput && passwordInput) {{
                console.log('Found email and password inputs');
                emailInput.value = '{self.email}';
                passwordInput.value = '{self.password}';

                const form = emailInput.closest('form');
                if (form) {{
                    console.log('Found form, submitting...');
                    form.submit();
                }} else {{
                    document.querySelector('form').submit();
                }}
            }} else {{
                console.log('Could not find form inputs');
            }}

            // Wait for page to load after submission
            await new Promise(resolve => setTimeout(resolve, 5000));
            console.log('Login complete');
            """

            config = CrawlerRunConfig(
                cache_mode='bypass',
                wait_for='body',
                page_timeout=30000,
                js_code=login_js
            )

            result = await self.crawler.arun(url=login_url, config=config)

            if not result.success:
                print(f"  ✗ Login failed: {result.error_message if hasattr(result, 'error_message') else 'Unknown error'}")
                return False

            # Save HTML for debugging
            with open('mam_login_response.html', 'w', encoding='utf-8') as f:
                f.write(result.html)

            # Verify login by checking for browse/torrent indicators
            html_lower = result.html.lower()
            if 'not logged in' in html_lower and 'error' in html_lower:
                print(f"  ✗ Login failed - page shows 'Not logged in' error")
                return False

            if 'torrent' in html_lower or 'browse' in html_lower or 'logout' in html_lower:
                self.authenticated = True
                print(f"  ✓ Logged in successfully")
                print()
                return True

            print(f"  ✗ Login verification inconclusive (check mam_login_response.html)")
            print()
            return False

        except Exception as e:
            print(f"  ✗ Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def search_mam(self, search_term: str) -> Optional[Dict[str, Any]]:
        """Search MAM and extract first result with magnet link."""
        try:
            search_url = (
                f"{self.base_url}/tor/browse.php"
                f"?tor[searchstr]={quote(search_term)}"
                f"&tor[cat][]=13"
            )

            config = CrawlerRunConfig(
                cache_mode='bypass',
                wait_for='body',
                page_timeout=30000
            )

            result = await self.crawler.arun(url=search_url, config=config)

            if not result.success:
                return None

            # Save HTML for debugging
            with open(f'mam_search_{search_term.replace(" ", "_")}.html', 'w', encoding='utf-8') as f:
                f.write(result.html)

            # Parse HTML
            soup = BeautifulSoup(result.html, 'html.parser')

            # Look for torrent links - try multiple patterns
            torrent_links = []

            # Pattern 1: Links with /t/ path
            for link in soup.find_all('a', href=re.compile(r'/t/\d+')):
                torrent_links.append(link)

            # Pattern 2: Links in table rows
            if not torrent_links:
                rows = soup.find_all('tr')
                for row in rows:
                    link = row.find('a', href=re.compile(r'/t/\d+'))
                    if link:
                        torrent_links.append(link)

            if not torrent_links:
                print(f"      No torrent links found in HTML ({len(result.html)} chars)")
                return None

            # Get first result
            first_link = torrent_links[0]
            result_title = first_link.get_text(strip=True)
            torrent_url = first_link.get('href', '')

            if torrent_url.startswith('/'):
                torrent_url = urljoin(self.base_url, torrent_url)

            # Extract torrent ID
            match = re.search(r'/t/(\d+)', torrent_url)
            if not match:
                return None

            torrent_id = match.group(1)
            print(f"      Found: {result_title[:80]}")
            print(f"      URL: {torrent_url}")

            # Get magnet link
            magnet = await self._get_magnet_link(torrent_id)

            if magnet:
                print(f"      Magnet: {magnet[:80]}...")
                return {
                    'title': result_title,
                    'url': torrent_url,
                    'magnet': magnet,
                    'torrent_id': torrent_id
                }
            else:
                print(f"      No magnet link found")
                return None

        except Exception as e:
            print(f"      Error: {str(e)[:80]}")
            return None

    async def _get_magnet_link(self, torrent_id: str) -> Optional[str]:
        """Extract magnet link from torrent page."""
        try:
            torrent_url = f"{self.base_url}/t/{torrent_id}"

            config = CrawlerRunConfig(
                cache_mode='bypass',
                wait_for='body',
                page_timeout=30000
            )

            result = await self.crawler.arun(url=torrent_url, config=config)

            if not result.success:
                return None

            # Look for magnet link
            magnet_match = re.search(r'(magnet:\?[^"<\s]+)', result.html)
            return magnet_match.group(1) if magnet_match else None

        except:
            return None

    async def search_and_queue(self, books: List[Dict[str, str]]):
        """Search for books and queue to qBittorrent."""

        print("STEP 2: Search MAM and Queue to qBittorrent")
        print("-" * 120)
        print()

        for i, book in enumerate(books, 1):
            title = book.get('title', 'Unknown')
            series = book.get('series', '')

            print(f"  [{i}/{len(books)}] Searching for: {title}")
            self.results['searched'] += 1

            # Search
            search_result = await self.search_mam(title)

            if not search_result:
                print(f"      ✗ Not found on MAM")
                self.results['failed'] += 1
                time.sleep(2)
                continue

            magnet = search_result.get('magnet')
            if not magnet:
                print(f"      ✗ No magnet link")
                self.results['failed'] += 1
                time.sleep(2)
                continue

            # Queue to qBittorrent
            try:
                self.qb_client.torrents_add(
                    urls=magnet,
                    category='audiobooks',
                    tags=['mam', 'auto', series] if series else ['mam', 'auto'],
                    is_paused=False
                )
                print(f"      ✓ QUEUED TO QBITTORRENT")
                self.results['queued'] += 1
                self.results['found'] += 1

            except Exception as e:
                print(f"      ✗ Queue failed: {str(e)[:60]}")
                self.results['failed'] += 1

            print()
            time.sleep(2)

    async def show_queue(self):
        """Display qBittorrent queue."""
        print("STEP 3: Current qBittorrent Queue")
        print("-" * 120)

        torrents = self.qb_client.torrents_info()
        if torrents:
            print(f"Total torrents in queue: {len(torrents)}")
            print("\nLast 10 torrents:")
            for t in torrents[-10:]:
                print(f"  {t.name}")
                print(f"    State: {t.state} | Progress: {t.progress * 100:.1f}% | Seeds: {t.num_seeds}")
        else:
            print("  (No torrents)")
        print()

    async def summary(self):
        """Print summary."""
        print("=" * 120)
        print("EXECUTION SUMMARY")
        print("=" * 120)
        print(f"  Searched: {self.results['searched']}")
        print(f"  Found: {self.results['found']}")
        print(f"  Queued to qBittorrent: {self.results['queued']}")
        print(f"  Failed: {self.results['failed']}")
        print()
        if self.results['queued'] > 0:
            print("✓ SUCCESS: Books queued to qBittorrent!")
        else:
            print("✗ No books successfully queued")
        print()

    async def cleanup(self):
        """Close crawler."""
        if self.crawler:
            await self.crawler.close()

    async def run(self, books: List[Dict[str, str]]):
        """Execute workflow."""
        try:
            if not await self.setup():
                return False

            if not await self.login():
                return False

            await self.search_and_queue(books)
            await self.show_queue()
            await self.summary()

            return self.results['queued'] > 0

        except Exception as e:
            print(f"FATAL: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            await self.cleanup()


async def main():
    """Main execution."""

    mam_email = os.getenv('MAM_USERNAME')
    mam_password = os.getenv('MAM_PASSWORD')
    qb_url = os.getenv('QBITTORRENT_URL')
    qb_user = os.getenv('QBITTORRENT_USERNAME')
    qb_pass = os.getenv('QBITTORRENT_PASSWORD')

    if not all([mam_email, mam_password, qb_url, qb_user, qb_pass]):
        print("ERROR: Missing required environment variables")
        print("Required: MAM_USERNAME, MAM_PASSWORD, QBITTORRENT_URL, QBITTORRENT_USERNAME, QBITTORRENT_PASSWORD")
        return False

    # Audiobooks to search
    audiobooks_to_find = [
        {'title': 'Save State Hero Book 3', 'series': 'Save State Hero'},
        {'title': 'Save State Hero Book 2', 'series': 'Save State Hero'},
        {'title': 'Save State Hero Book 1', 'series': 'Save State Hero'},
        {'title': 'Save State Hero Book 4', 'series': 'Save State Hero'},
        {'title': 'Save State Hero Book 5', 'series': 'Save State Hero'},
    ]

    downloader = MAMEmailPasswordCrawler(mam_email, mam_password, qb_url, qb_user, qb_pass)
    success = await downloader.run(audiobooks_to_find)

    return success


if __name__ == '__main__':
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
