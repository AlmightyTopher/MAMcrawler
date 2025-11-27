#!/usr/bin/env python3
"""
MAM Requests-Based Crawler (Alternative to Crawl4AI)
=====================================================
Uses requests library for reliable session persistence
- Email/password based authentication with persistent session
- MyAnonamouse audiobook search and extraction
- Magnet link extraction from torrent pages
- qBittorrent integration for queuing downloads
- No Crawl4AI session persistence issues
"""

import sys
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import quote, urljoin
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
print("MAM REQUESTS-BASED CRAWLER (Requests Library)")
print("=" * 120)
print(f"Start: {datetime.now().isoformat()}")
print()

try:
    import requests
    from bs4 import BeautifulSoup
    import qbittorrentapi
except ImportError as e:
    print(f"ERROR: Missing required library: {e}")
    sys.exit(1)


class MAMRequestsCrawler:
    """MAM crawler using requests library with persistent session"""

    def __init__(self, email: str, password: str, qb_url: str, qb_user: str, qb_pass: str):
        self.email = email
        self.password = password
        self.base_url = "https://www.myanonamouse.net"

        # Create persistent session with proper headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        self.qb_url = qb_url
        self.qb_user = qb_user
        self.qb_pass = qb_pass
        self.qb_client = None

        self.authenticated = False
        self.results = {"searched": 0, "found": 0, "queued": 0, "failed": 0}

    def setup(self) -> bool:
        """Initialize qBittorrent connection."""
        print("SETUP: Initializing components")
        print("-" * 120)

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

    def login(self) -> bool:
        """Login to MAM with email/password using persistent session."""
        print("STEP 1: Login to MyAnonamouse (email/password)")
        print("-" * 120)

        try:
            login_url = f"{self.base_url}/login.php"

            # First, get the login page to extract any CSRF tokens if needed
            print("  Getting login page...")
            response = self.session.get(login_url, timeout=30)

            if response.status_code != 200:
                print(f"  ✗ Could not access login page: {response.status_code}")
                return False

            # Prepare login data
            login_data = {
                'email': self.email,
                'password': self.password,
                'login': 'Login'
            }

            # Submit login form
            print("  Submitting login form...")
            response = self.session.post(
                f"{self.base_url}/takelogin.php",
                data=login_data,
                timeout=30,
                allow_redirects=True
            )

            if response.status_code != 200:
                print(f"  ✗ Login request failed: {response.status_code}")
                return False

            # Save login response for debugging
            with open('mam_login_response_requests.html', 'w', encoding='utf-8') as f:
                f.write(response.text)

            # Verify login by checking for indicators
            html_lower = response.text.lower()

            if 'not logged in' in html_lower and 'error' in html_lower:
                print(f"  ✗ Login failed - page shows 'Not logged in' error")
                return False

            # Check for positive login indicators
            if 'torrent' in html_lower or 'browse' in html_lower or 'logout' in html_lower or 'userdetails' in html_lower:
                self.authenticated = True
                print(f"  ✓ Logged in successfully (session persisted)")
                print(f"  ✓ Cookies in session: {list(self.session.cookies.keys())}")
                print()
                return True

            print(f"  ✗ Login verification inconclusive")
            print()
            return False

        except Exception as e:
            print(f"  ✗ Login error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def search_mam(self, search_term: str) -> Optional[Dict[str, Any]]:
        """Search MAM and extract first result with magnet link."""
        try:
            search_url = (
                f"{self.base_url}/tor/browse.php"
                f"?tor[searchstr]={quote(search_term)}"
                f"&tor[cat][]=13"
            )

            response = self.session.get(search_url, timeout=30)

            if response.status_code != 200:
                return None

            # Save search HTML for debugging
            with open(f'mam_search_requests_{search_term.replace(" ", "_")}.html', 'w', encoding='utf-8') as f:
                f.write(response.text)

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

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
                print(f"      No torrent links found in HTML ({len(response.text)} chars)")
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
            magnet = self._get_magnet_link(torrent_id)

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

    def _get_magnet_link(self, torrent_id: str) -> Optional[str]:
        """Extract magnet link from torrent page."""
        try:
            torrent_url = f"{self.base_url}/t/{torrent_id}"

            response = self.session.get(torrent_url, timeout=30)

            if response.status_code != 200:
                return None

            # Look for magnet link
            magnet_match = re.search(r'(magnet:\?[^"<\s]+)', response.text)
            return magnet_match.group(1) if magnet_match else None

        except:
            return None

    def search_and_queue(self, books: List[Dict[str, str]]):
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
            search_result = self.search_mam(title)

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

    def show_queue(self):
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

    def summary(self):
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

    def run(self, books: List[Dict[str, str]]):
        """Execute workflow."""
        try:
            if not self.setup():
                return False

            if not self.login():
                return False

            self.search_and_queue(books)
            self.show_queue()
            self.summary()

            return self.results['queued'] > 0

        except Exception as e:
            print(f"FATAL: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
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

    crawler = MAMRequestsCrawler(mam_email, mam_password, qb_url, qb_user, qb_pass)
    success = crawler.run(audiobooks_to_find)

    return success


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
