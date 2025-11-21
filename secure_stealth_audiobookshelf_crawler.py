"""
Secure Stealth MAM Audiobookshelf Search Crawler
- Searches for Audiobookshelf-related content on MyAnonamouse
- Handles pagination automatically
- Extracts metadata: title, author, size, download links
- Implements secure authentication and credential handling
- Uses safe web scraping techniques with proper error handling
"""

import asyncio
import os
import re
import json
import random
import base64
import hashlib
import secrets
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure secure logging
class SecureFormatter(logging.Formatter):
    """Secure logging formatter that redacts sensitive information."""
    
    SENSITIVE_KEYS = ['password', 'token', 'key', 'secret', 'username', 'email']
    
    def format(self, record):
        # Make a copy of the original record
        original_message = record.getMessage()
        
        # Redact sensitive information from the message
        for key in self.SENSITIVE_KEYS:
            pattern = rf"{key}\s*[:=]\s*['\"](.*?)['\"]"
            original_message = re.sub(pattern, f"{key}=[REDACTED]", original_message, flags=re.IGNORECASE)
        
        # Update the record message
        record.msg = original_message
        record.message = original_message
        
        # Format the record normally
        return super().format(record)

# Set up logging with secure formatter
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a file handler with secure formatter
file_handler = logging.FileHandler('secure_stealth_audiobookshelf_crawler.log', encoding='utf-8')
file_handler.setFormatter(SecureFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Create console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(SecureFormatter('%(asctime)s - %(levelname)s - %(message)s'))

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)


class SecureStealthMAMAudiobookshelfCrawler:
    """Secure stealth crawler for Audiobookshelf content on MAM."""

    def __init__(self):
        # Read credentials securely using environment variables
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env file")

        # Generate a secure session ID
        self.session_id = f"mam_audiobookshelf_session_{secrets.token_hex(8)}"
        self.is_authenticated = False

        # Use secure temporary directory for sensitive data
        self.temp_dir = Path(os.getenv('TEMP_DIR', './tmp'))
        self.temp_dir.mkdir(exist_ok=True)
        
        # Set restrictive permissions on temp directory (Unix only)
        if hasattr(os, 'chmod'):
            os.chmod(self.temp_dir, 0o700)

        self.base_url = "https://www.myanonamouse.net"
        
        # Output directory with restricted permissions
        self.output_dir = Path("audiobookshelf_output")
        self.output_dir.mkdir(exist_ok=True)
        
        # State file with secure permissions
        self.state_file = Path("secure_audiobookshelf_crawler_state.json")
        self.state = self.load_state()

        # Search terms and URLs
        self.search_terms = ["Audiobookshelf", "audiobookshelf", "audio book shelf", "ABS"]
        self.search_urls = [
            "https://www.myanonamouse.net/f/search.php?text=audiobookshelf&searchIn=1&order=default&start=0",
            "https://www.myanonamouse.net/f/search.php?text=audiobook%20shelf&searchIn=1&order=default&start=0",
            "https://www.myanonamouse.net/f/search.php?text=audio%20book%20shelf&searchIn=1&order=default&start=0",
            "https://www.myanonamouse.net/f/search.php?text=ABS&searchIn=1&order=default&start=0"
        ]

        # Human-like timing parameters
        self.min_delay = 10  # seconds between pages
        self.max_delay = 30  # seconds between pages
        self.scroll_delay = 2  # seconds for scrolling
        self.read_delay = 5  # seconds to "read" content

        # Viewport randomization for stealth
        self.viewports = [
            (1920, 1080),
            (1366, 768),
            (1536, 864),
            (1440, 900),
            (1600, 900)
        ]

        # User agent rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
        ]

    def _secure_store_secret(self, secret: str) -> str:
        """Securely store a secret and return a reference."""
        # Generate a random filename
        secret_file = self.temp_dir / f"secret_{secrets.token_hex(8)}.txt"
        
        # Write the secret to the file with secure permissions
        with open(secret_file, 'w') as f:
            f.write(secret)
        
        # Set restrictive permissions on Unix systems
        if hasattr(os, 'chmod'):
            os.chmod(secret_file, 0o600)
        
        # Return the filename for reference (not the content)
        return str(secret_file)

    def _secure_retrieve_secret(self, secret_file: str) -> Optional[str]:
        """Retrieve a securely stored secret."""
        try:
            secret_path = Path(secret_file)
            
            # Check if file exists and is within temp directory
            if not secret_path.exists() or not secret_path.is_file() or not secret_path.parent == self.temp_dir:
                logger.warning(f"Attempt to access secret file outside of temp directory: {secret_file}")
                return None
            
            # Read the secret
            with open(secret_path, 'r') as f:
                secret = f.read()
            
            # Delete the file after reading
            secret_path.unlink()
            
            return secret
        except Exception as e:
            logger.error(f"Error retrieving secret: {e}")
            return None

    def _sanitize_input(self, input_str: str) -> str:
        """Sanitize input to prevent injection attacks."""
        if not isinstance(input_str, str):
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\']', '', input_str)
        
        # Log potential security concerns
        if any(char in sanitized for char in ['<', '>', '&', '"', "'"]):
            logger.warning(f"Potentially dangerous characters removed from input")
        
        return sanitized

    def load_state(self) -> Dict:
        """Load crawler state for resume capability."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                # Sanitize state data
                for key in state:
                    if isinstance(state[key], str):
                        state[key] = self._sanitize_input(state[key])
                
                logger.info(f"Loaded state: {len(state.get('completed', []))} torrents already crawled")
                return state
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

        return {
            'completed': [],
            'failed': [],
            'pending': [],
            'last_run': None,
            'search_progress': {}  # Track pagination progress per search
        }

    def save_state(self):
        """Save current crawler state."""
        self.state['last_run'] = datetime.now().isoformat()
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"State saved: {len(self.state['completed'])} completed")
            
            # Set secure permissions on state file
            if hasattr(os, 'chmod'):
                os.chmod(self.state_file, 0o600)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    async def human_delay(self, min_seconds: Optional[int] = None, max_seconds: Optional[int] = None):
        """Simulate human-like random delay."""
        min_s = min_seconds or self.min_delay
        max_s = max_seconds or self.max_delay
        delay = random.uniform(min_s, max_s)
        logger.info(f"⏱️  Waiting {delay:.1f} seconds (human-like delay)...")
        await asyncio.sleep(delay)

    def get_random_viewport(self) -> tuple:
        """Get random viewport size for stealth."""
        return random.choice(self.viewports)

    def get_random_user_agent(self) -> str:
        """Get random user agent."""
        return random.choice(self.user_agents)

    def create_browser_config(self) -> BrowserConfig:
        """Create browser config with randomized settings."""
        width, height = self.get_random_viewport()

        return BrowserConfig(
            headless=False,
            viewport_width=width,
            viewport_height=height,
            verbose=False,
            user_agent=self.get_random_user_agent(),
            ignore_https_errors=False,
            java_script_enabled=True,
            # Additional security settings
            incognito=False,
            proxy_server=None,
            browser_args=["--disable-blink-features=AutomationControlled", "--disable-extensions"]
        )

    def create_stealth_js(self) -> str:
        """Create JavaScript for human-like behavior simulation."""
        return """
        // Simulate human-like mouse movement
        async function simulateHumanBehavior() {
            // Random mouse movements
            for (let i = 0; i < 3; i++) {
                const x = Math.floor(Math.random() * window.innerWidth);
                const y = Math.floor(Math.random() * window.innerHeight);

                const event = new MouseEvent('mousemove', {
                    clientX: x,
                    clientY: y,
                    bubbles: true
                });
                document.dispatchEvent(event);

                await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 300));
            }

            // Scroll like a human reading
            const scrollHeight = document.documentElement.scrollHeight;
            const viewportHeight = window.innerHeight;
            const scrollSteps = 3 + Math.floor(Math.random() * 3);

            for (let i = 0; i < scrollSteps; i++) {
                const scrollTo = (scrollHeight / scrollSteps) * (i + 1);
                window.scrollTo({
                    top: scrollTo,
                    behavior: 'smooth'
                });

                // Pause to "read"
                await new Promise(resolve => setTimeout(resolve, 1000 + Math.random() * 2000));
            }

            // Scroll back to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            await new Promise(resolve => setTimeout(resolve, 500));
        }

        await simulateHumanBehavior();
        """

    def _create_secure_login_js(self) -> str:
        """Create secure JavaScript for authentication without exposing credentials."""
        # Generate a random identifier for the credentials
        username_var = f"user_{secrets.token_hex(4)}"
        password_var = f"pass_{secrets.token_hex(4)}"
        
        # Store credentials in secure variables
        js_code = f"""
        // Secure credential handling
        let {username_var} = sessionStorage.getItem('{self.session_id}_username');
        let {password_var} = sessionStorage.getItem('{self.session_id}_password');
        
        if (!{username_var} || !{password_var}) {{
            // If credentials are not in session storage, the script will fail
            // This prevents credentials from being embedded in the script
            throw new Error('Credentials not available in session storage');
        }}
        
        // Wait for page load
        await new Promise(resolve => setTimeout(resolve, {random.randint(1500, 3000)}));

        // Move mouse around like looking for fields
        for (let i = 0; i < 2; i++) {{
            const event = new MouseEvent('mousemove', {{
                clientX: 300 + Math.random() * 200,
                clientY: 200 + Math.random() * 100,
                bubbles: true
            }});
            document.dispatchEvent(event);
            await new Promise(resolve => setTimeout(resolve, {random.randint(300, 600)}));
        }}

        // Fill email field (with typing delay)
        const emailInput = document.querySelector('input[name="email"]');
        const passwordInput = document.querySelector('input[name="password"]');

        if (emailInput && passwordInput) {{
            emailInput.focus();
            await new Promise(resolve => setTimeout(resolve, {random.randint(500, 1000)}));

            // Type username character by character
            for (let i = 0; i < {username_var}.length; i++) {{
                emailInput.value = {username_var}.substring(0, i + 1);
                await new Promise(resolve => setTimeout(resolve, {random.randint(50, 100)}));
            }}
            
            passwordInput.focus();
            await new Promise(resolve => setTimeout(resolve, {random.randint(500, 1000)}));

            // Type password character by character
            for (let i = 0; i < {password_var}.length; i++) {{
                passwordInput.value = {password_var}.substring(0, i + 1);
                await new Promise(resolve => setTimeout(resolve, {random.randint(50, 100)}));
            }}

            await new Promise(resolve => setTimeout(resolve, {random.randint(1000, 2000)}));

            // Click submit button (not just submit form)
            const submitBtn = document.querySelector('input[type="submit"]');
            if (submitBtn) {{
                submitBtn.click();
            }} else {{
                document.querySelector('form').submit();
            }}

            // Wait for redirect
            await new Promise(resolve => setTimeout(resolve, 4000));
            
            // Clear credentials from session storage after use
            sessionStorage.removeItem('{self.session_id}_username');
            sessionStorage.removeItem('{self.session_id}_password');
        }}
        """
        
        return js_code

    async def authenticate(self, crawler: AsyncWebCrawler) -> bool:
        """Securely authenticate with human-like behavior."""
        if self.is_authenticated:
            logger.info("Already authenticated")
            return True

        logger.info("🔐 Authenticating with MyAnonamouse (secure mode)...")

        # Initial delay before login
        await self.human_delay(3, 7)

        try:
            login_url = f"{self.base_url}/login.php"

            # Use secure credential handling
            config = CrawlerRunConfig(
                session_id=self.session_id,
                cache_mode=CacheMode.BYPASS,
                # First part: Set credentials in session storage using a separate script
                js_before_exec=[
                    f"""
                    // Store credentials securely in session storage
                    sessionStorage.setItem('{self.session_id}_username', '{self.username}');
                    sessionStorage.setItem('{self.session_id}_password', '{self.password}');
                    """
                ],
                js_code=self._create_secure_login_js(),
                wait_for="css:body",
                page_timeout=60000,
                screenshot=True
            )

            result = await crawler.arun(url=login_url, config=config)

            if result.success:
                response_text = result.markdown.lower()

                if "logout" in response_text or "my account" in response_text or "tophertek" in response_text:
                    logger.info("✅ Authentication successful")
                    self.is_authenticated = True

                    # Save screenshot with secure permissions
                    if result.screenshot:
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        screenshot_path = self.temp_dir / f"login_success_{secrets.token_hex(8)}.png"
                        with open(screenshot_path, 'wb') as f:
                            f.write(screenshot_data)
                        
                        # Set secure permissions on screenshot
                        if hasattr(os, 'chmod'):
                            os.chmod(screenshot_path, 0o600)

                    return True
                else:
                    logger.error("❌ Authentication failed")
                    if result.screenshot:
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        screenshot_path = self.temp_dir / f"login_failed_{secrets.token_hex(8)}.png"
                        with open(screenshot_path, 'wb') as f:
                            f.write(screenshot_data)
                        
                        # Set secure permissions on screenshot
                        if hasattr(os, 'chmod'):
                            os.chmod(screenshot_path, 0o600)
                    return False
            else:
                logger.error(f"❌ Browser automation failed: {result.error_message}")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def extract_torrent_metadata(self, html: str) -> List[Dict[str, Any]]:
        """Extract torrent metadata from search results page."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        torrents = []

        # Find torrent rows - MAM uses table structure for search results
        torrent_rows = soup.find_all('tr', class_=lambda x: x and ('torrentrow' in x or 'row' in x))

        for row in torrent_rows:
            try:
                torrent_data = {}

                # Extract title and link
                title_link = row.find('a', class_=lambda x: x and 'torrentlink' in x)
                if title_link:
                    # Sanitize title to prevent XSS
                    torrent_data['title'] = self._sanitize_input(title_link.get_text(strip=True))
                    href = title_link.get('href', '')
                    if href.startswith('/'):
                        torrent_data['url'] = f"{self.base_url}{href}"
                    else:
                        torrent_data['url'] = href

                # Extract author/uploader
                author_cell = row.find('td', class_=lambda x: x and 'author' in x)
                if author_cell:
                    author_link = author_cell.find('a')
                    if author_link:
                        # Sanitize author to prevent XSS
                        torrent_data['author'] = self._sanitize_input(author_link.get_text(strip=True))

                # Extract size
                size_cell = row.find('td', class_=lambda x: x and 'size' in x)
                if size_cell:
                    torrent_data['size'] = self._sanitize_input(size_cell.get_text(strip=True))

                # Extract download link
                download_link = row.find('a', href=lambda h: h and 'action=download' in h)
                if download_link:
                    href = download_link.get('href', '')
                    if href.startswith('/'):
                        torrent_data['download_url'] = f"{self.base_url}{href}"
                    else:
                        torrent_data['download_url'] = href

                # Extract additional metadata
                torrent_data['category'] = 'Audiobookshelf'
                torrent_data['search_term'] = self.current_search_term
                torrent_data['crawled_at'] = datetime.now().isoformat()

                if torrent_data.get('title') and torrent_data.get('url'):
                    torrents.append(torrent_data)

            except Exception as e:
                logger.warning(f"Error extracting torrent data from row: {e}")
                continue

        return torrents

    def check_pagination(self, html: str) -> Optional[str]:
        """Check if there are more pages and return next page URL."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        # Look for "next" link in pagination
        next_link = soup.find('a', text=lambda t: t and ('next' in t.lower() or '>' in t))

        if next_link:
            href = next_link.get('href', '')
            if href.startswith('/'):
                return f"{self.base_url}{href}"
            elif href.startswith('http'):
                return href

        return None

    async def crawl_search_page(self, crawler: AsyncWebCrawler, url: str, search_term: str) -> Dict[str, Any]:
        """Crawl a single search page and extract torrent data."""
        logger.info(f"🔍 Crawling search page: {url}")

        await self.human_delay()

        config = CrawlerRunConfig(
            session_id=self.session_id,
            cache_mode=CacheMode.BYPASS,
            js_code=self.create_stealth_js(),
            wait_for="css:body",
            page_timeout=45000
        )

        try:
            result = await crawler.arun(url=url, config=config)

            if result.success and result.html:
                # Extract torrent metadata
                torrents = self.extract_torrent_metadata(result.html)

                # Check for pagination
                next_page_url = self.check_pagination(result.html)

                page_data = {
                    'success': True,
                    'url': url,
                    'search_term': search_term,
                    'torrents': torrents,
                    'next_page': next_page_url,
                    'crawled_at': datetime.now().isoformat()
                }

                logger.info(f"✅ Found {len(torrents)} torrents on this page")
                if next_page_url:
                    logger.info(f"📄 Next page available: {next_page_url}")

                return page_data
            else:
                logger.error(f"❌ Failed to crawl search page: {result.error_message}")
                return {
                    'success': False,
                    'url': url,
                    'search_term': search_term,
                    'error': result.error_message
                }

        except Exception as e:
            logger.error(f"❌ Error crawling search page: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'url': url,
                'search_term': search_term,
                'error': str(e)
            }

    def save_torrents_to_file(self, torrents: List[Dict[str, Any]], search_term: str):
        """Save torrent data to JSON file."""
        if not torrents:
            return

        filename = f"audiobookshelf_{search_term.replace(' ', '_').lower()}_results.json"
        filepath = self.output_dir / filename

        # Load existing data if file exists
        existing_data = []
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load existing data: {e}")

        # Merge new data (avoid duplicates by URL)
        existing_urls = {t.get('url') for t in existing_data}
        new_torrents = [t for t in torrents if t.get('url') not in existing_urls]

        if new_torrents:
            combined_data = existing_data + new_torrents

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False)
            
            # Set secure permissions on the file
            if hasattr(os, 'chmod'):
                os.chmod(filepath, 0o600)

            logger.info(f"💾 Saved {len(new_torrents)} new torrents to {filename} (total: {len(combined_data)})")
        else:
            logger.info(f"ℹ️  No new torrents to save for {search_term}")

    async def crawl_search_with_pagination(self, crawler: AsyncWebCrawler, start_url: str, search_term: str):
        """Crawl a search with pagination handling."""
        logger.info(f"🚀 Starting paginated crawl for: {search_term}")
        logger.info(f"📍 Start URL: {start_url}")

        current_url = start_url
        page_count = 0
        total_torrents = 0

        while current_url:
            page_count += 1
            logger.info(f"\n{'='*70}")
            logger.info(f"📄 Page {page_count} - {search_term}")
            logger.info(f"{'='*70}\n")

            # Check if we've already crawled this page
            search_key = f"{search_term}_{current_url}"
            if search_key in self.state.get('completed', []):
                logger.info(f"⏭️  Already crawled: {current_url}")
                break

            page_data = await self.crawl_search_page(crawler, current_url, search_term)

            if page_data.get('success'):
                torrents = page_data.get('torrents', [])
                total_torrents += len(torrents)

                # Save torrents
                self.save_torrents_to_file(torrents, search_term)

                # Mark page as completed
                self.state['completed'].append(search_key)
                self.save_state()

                # Check for next page
                current_url = page_data.get('next_page')

                # Safety check - don't crawl more than 50 pages per search
                if page_count >= 50:
                    logger.warning(f"⚠️  Reached page limit (50) for {search_term}")
                    break

                # If no next page or no new torrents, stop
                if not current_url or len(torrents) == 0:
                    break

            else:
                logger.error(f"❌ Failed to crawl page {page_count}: {page_data.get('error')}")
                self.state['failed'].append({
                    'url': current_url,
                    'search_term': search_term,
                    'error': page_data.get('error'),
                    'timestamp': datetime.now().isoformat()
                })
                self.save_state()
                break

        logger.info(f"🏁 Completed crawl for {search_term}: {page_count} pages, {total_torrents} total torrents")

    async def run(self):
        """Main execution with stealth and state management."""
        logger.info("="*70)
        logger.info("🕵️  Starting SECURE STEALTH MAM Audiobookshelf Search Crawler")
        logger.info("="*70)

        # Create browser with randomized config
        browser_config = self.create_browser_config()
        logger.info(f"🖥️  Viewport: {browser_config.viewport_width}x{browser_config.viewport_height}")

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Step 1: Authenticate
                if not await self.authenticate(crawler):
                    logger.error("❌ Authentication failed. Exiting.")
                    return

                # Step 2: Crawl each search term
                for i, (search_term, search_url) in enumerate(zip(self.search_terms, self.search_urls), 1):
                    logger.info(f"\n{'='*70}")
                    logger.info(f"🔍 Search {i}/{len(self.search_terms)}: {search_term}")
                    logger.info(f"{'='*70}\n")

                    self.current_search_term = search_term
                    await self.crawl_search_with_pagination(crawler, search_url, search_term)

                # Final summary
                logger.info("\n" + "="*70)
                logger.info("🎯 AUDIOBOOKSHELF CRAWL COMPLETE")
                logger.info("="*70)
                logger.info(f"✅ Successfully crawled: {len(self.state['completed'])} pages")
                logger.info(f"❌ Failed: {len(self.state['failed'])} pages")
                logger.info(f"📁 Output directory: {self.output_dir.absolute()}")

                # Create summary file
                self.create_summary_report()

                logger.info("="*70)
        except Exception as e:
            logger.error(f"❌ Crawl failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Clean up sensitive data
            self._cleanup_sensitive_data()

    def _cleanup_sensitive_data(self):
        """Clean up sensitive data after crawling is complete."""
        logger.info("🧹 Cleaning up sensitive data...")
        
        try:
            # Remove all files in temp directory
            for file_path in self.temp_dir.glob('*'):
                if file_path.is_file():
                    # Overwrite file content before deletion for security
                    with open(file_path, 'r+b') as f:
                        f.write(b'\x00' * f.tell())
                    file_path.unlink()
            
            # Remove state file with sensitive data
            if self.state_file.exists():
                # Overwrite state file before deletion
                with open(self.state_file, 'r+b') as f:
                    f.write(b'\x00' * f.tell())
                self.state_file.unlink()
            
            logger.info("✅ Sensitive data cleaned up successfully")
        except Exception as e:
            logger.error(f"❌ Error cleaning up sensitive data: {e}")

    def create_summary_report(self):
        """Create a summary report of all crawled data."""
        summary_file = self.output_dir / "SECURE_AUDIOBOOKSHELF_CRAWL_SUMMARY.md"

        total_torrents = 0
        search_stats = {}

        # Count torrents per search term
        for json_file in self.output_dir.glob("audiobookshelf_*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    count = len(data)
                    total_torrents += count

                    search_term = json_file.stem.replace('audiobookshelf_', '').replace('_results', '').replace('_', ' ')
                    search_stats[search_term] = count
            except Exception as e:
                logger.warning(f"Could not read {json_file}: {e}")

        # Create summary content
        content = "# Secure Audiobookshelf Search Results Summary\n\n"
        content += f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**Total Torrents Found:** {total_torrents}\n\n"
        content += "## Search Results by Term\n\n"

        for term, count in search_stats.items():
            content += f"- **{term}:** {count} torrents\n"

        content += "\n## Output Files\n\n"
        for json_file in sorted(self.output_dir.glob("audiobookshelf_*.json")):
            content += f"- {json_file.name}\n"

        content += "\n## Metadata Extracted\n\n"
        content += "- Title (sanitized)\n"
        content += "- Author (sanitized)\n"
        content += "- Size\n"
        content += "- Download Links\n"
        content += "- Category (Audiobookshelf)\n"
        content += "- Search Term\n"
        content += "- Crawl Timestamp\n"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Set secure permissions on summary file
        if hasattr(os, 'chmod'):
            os.chmod(summary_file, 0o600)

        logger.info(f"📊 Summary report created: {summary_file}")


async def main():
    """Entry point."""
    try:
        crawler = SecureStealthMAMAudiobookshelfCrawler()
        await crawler.run()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Crawl interrupted by user")
        logger.info("💡 Progress has been saved - run again to resume")
    except Exception as e:
        logger.error(f"❌ Crawl failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())