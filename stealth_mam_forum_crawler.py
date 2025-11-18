"""
Stealth MAM Forum Crawler - Extract qbittorrent-related posts from MAM forum (forums-only, last 1.5 years)
- Human-like behavior with realistic timing
- Search for qbittorrent mentions in forum topic titles and posts
- Extract full post content and metadata
- State persistence for resume capability
- Retry logic with exponential backoff (capped)
- No emojis in logging or output
"""

import asyncio
import os
import re
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv
import logging

# optional dependency
try:
    from dateutil import parser as date_parser
    from dateutil import relativedelta
except Exception:
    date_parser = None
    relativedelta = None

# Load environment variables
load_dotenv()

# Configure logging (no emojis)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stealth_forum_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StealthMAMForumCrawler:
    """Stealth crawler for MAM forum posts related to qbittorrent."""

    def __init__(self):
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env file")

        self.base_url = "https://www.myanonamouse.net"
        self.forum_url = f"{self.base_url}/f"
        self.session_id = "mam_forum_stealth_session"
        self.is_authenticated = False

        self.output_dir = Path("forum_qbittorrent_output")
        self.output_dir.mkdir(exist_ok=True)

        self.state_file = Path("forum_crawler_state.json")
        self.state = self.load_state()

        # Search parameters - focused on torrent automation, maintenance, and improvement
        self.search_term = "torrent automation"
        self.search_variations = [
            # qBittorrent specific
            "qbittorrent", "qbit", "q-bit", "q-bittorrent",
            "qbittorrent client", "qbittorrent settings", "qbittorrent config",
            "qbittorrent automation", "qbittorrent script", "qbittorrent tool",

            # General torrent automation
            "torrent automation", "automated torrent", "torrent script",
            "torrent maintenance", "torrent improvement", "torrent tool",
            "batch torrent", "torrent batch", "torrent queue",

            # Download automation
            "automated download", "download automation", "auto download",
            "download script", "download tool", "download manager",

            # Maintenance and improvement
            "torrent maintenance", "improve torrent", "torrent optimization",
            "speed improvement", "faster torrent", "torrent speed",
            "communication improvement", "better torrent",

            # Tools and projects
            "torrent project", "torrent code", "torrent api",
            "qbittorrent api", "qbittorrent webui", "qbittorrent integration",

            # Audiobook specific automation
            "audiobook automation", "auto audiobook", "audiobook batch",
            "audiobook script", "audiobook tool", "audiobook download automation"
        ]

        # Human-like timing parameters (can be overridden for testing)
        self.min_delay = 15
        self.max_delay = 45
        self.scroll_delay = 3
        self.read_delay = 8

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

        # Time cutoff: 1.5 years (18 months) ago
        now = datetime.now(timezone.utc)
        if relativedelta:
            self.cutoff_date = now - relativedelta.relativedelta(months=18)
        else:
            from datetime import timedelta
            self.cutoff_date = now - timedelta(days=18 * 30)

        logger.info(f"Cutoff date for posts: {self.cutoff_date.isoformat()}")

    def load_state(self) -> Dict:
        """Load crawler state for resume capability."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.info(f"Loaded state: {len(state.get('completed', []))} posts already crawled")
                state.setdefault('completed', [])
                state.setdefault('failed', [])
                state.setdefault('pending', [])
                state.setdefault('skipped_old', [])
                state.setdefault('last_run', None)
                return state
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

        return {
            'completed': [],
            'failed': [],
            'pending': [],
            'skipped_old': [],
            'last_run': None
        }

    def save_state(self):
        """Save current crawler state."""
        self.state['last_run'] = datetime.now(timezone.utc).isoformat()
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"State saved: {len(self.state['completed'])} completed")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    async def human_delay(self, min_seconds: Optional[int] = None, max_seconds: Optional[int] = None):
        """Simulate human-like random delay."""
        min_s = min_seconds or self.min_delay
        max_s = max_seconds or self.max_delay
        delay = random.uniform(min_s, max_s)
        logger.info(f"Waiting {delay:.1f} seconds (human-like delay)...")
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

        # Force UTF-8 output to avoid Windows encoding issues
        import sys
        if sys.platform == 'win32':
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

        return BrowserConfig(
            headless=False,
            viewport_width=width,
            viewport_height=height,
            verbose=False,
            user_agent=self.get_random_user_agent(),
            ignore_https_errors=False,
            java_script_enabled=True,

            light_mode=False
        )

    def create_stealth_js(self) -> str:
        """Create JavaScript for human-like behavior simulation."""
        return """
        async function simulateHumanBehavior() {
            for (let i = 0; i < 4; i++) {
                const x = Math.floor(Math.random() * window.innerWidth);
                const y = Math.floor(Math.random() * window.innerHeight);

                const event = new MouseEvent('mousemove', {
                    clientX: x,
                    clientY: y,
                    bubbles: true
                });
                document.dispatchEvent(event);

                await new Promise(resolve => setTimeout(resolve, 300 + Math.random() * 500));
            }

            const scrollHeight = document.documentElement.scrollHeight;
            const scrollSteps = 4 + Math.floor(Math.random() * 4);

            for (let i = 0; i < scrollSteps; i++) {
                const scrollTo = (scrollHeight / scrollSteps) * (i + 1);
                window.scrollTo({
                    top: scrollTo,
                    behavior: 'smooth'
                });

                await new Promise(resolve => setTimeout(resolve, 1500 + Math.random() * 3000));
            }

            window.scrollTo({ top: 0, behavior: 'smooth' });
            await new Promise(resolve => setTimeout(resolve, 800));
        }

        await simulateHumanBehavior();
        """

    async def authenticate(self, crawler: AsyncWebCrawler) -> bool:
        """Authenticate with human-like behavior."""
        if self.is_authenticated:
            logger.info("Already authenticated")
            return True

        logger.info("Authenticating with MyAnonamouse (forum stealth mode)")

        await self.human_delay(5, 10)

        try:
            login_url = f"{self.base_url}/login.php"

            js_login = f"""
            await new Promise(resolve => setTimeout(resolve, {random.randint(2000, 4000)}));

            for (let i = 0; i < 3; i++) {{
                const event = new MouseEvent('mousemove', {{
                    clientX: 300 + Math.random() * 300,
                    clientY: 200 + Math.random() * 150,
                    bubbles: true
                }});
                document.dispatchEvent(event);
                await new Promise(resolve => setTimeout(resolve, {random.randint(400, 800)}));
            }}

            const emailInput = document.querySelector('input[name="email"]');
            const passwordInput = document.querySelector('input[name="password"]');

            if (emailInput && passwordInput) {{
                emailInput.focus();
                await new Promise(resolve => setTimeout(resolve, {random.randint(600, 1200)}));

                emailInput.value = '{self.username}';
                await new Promise(resolve => setTimeout(resolve, {random.randint(1000, 2000)}));

                passwordInput.focus();
                await new Promise(resolve => setTimeout(resolve, {random.randint(600, 1200)}));

                passwordInput.value = '{self.password}';
                await new Promise(resolve => setTimeout(resolve, {random.randint(1200, 2500)}));

                const submitBtn = document.querySelector('input[type="submit"]');
                if (submitBtn) {{
                    submitBtn.click();
                }} else {{
                    const form = document.querySelector('form');
                    if (form) form.submit();
                }}

                await new Promise(resolve => setTimeout(resolve, 5000));
            }}
            """

            config = CrawlerRunConfig(
                session_id=self.session_id,
                cache_mode=CacheMode.BYPASS,
                js_code=js_login,
                wait_for="css:body",
                page_timeout=60000,
                screenshot=True
            )

            result = await crawler.arun(url=login_url, config=config)

            if result.success:
                response_text = (result.markdown or "").lower()
                if any(k in response_text for k in ["logout", "my account", "log out"]):
                    logger.info("Authentication successful")
                    self.is_authenticated = True

                    if getattr(result, 'screenshot', None):
                        import base64
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        with open('forum_login_success.png', 'wb') as f:
                            f.write(screenshot_data)

                    return True
                else:
                    logger.error("Authentication failed")
                    if getattr(result, 'screenshot', None):
                        import base64
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        with open('forum_login_failed.png', 'wb') as f:
                            f.write(screenshot_data)
                    return False
            else:
                logger.error(f"Browser automation failed: {result.error_message}")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def search_forum_posts(self, crawler: AsyncWebCrawler) -> List[Dict[str, str]]:
        """Search forum for qbittorrent-related posts using direct search URL."""
        logger.info("Searching forum for qbittorrent-related topics (direct search only)")

        # Skip browsing phase - go directly to search
        search_posts = await self.search_forum_via_search_box(crawler)

        logger.info(f"Direct search results: {len(search_posts)} topics found")
        return search_posts

    async def browse_forum_for_qbittorrent(self, crawler: AsyncWebCrawler) -> List[Dict[str, str]]:
        """Browse forum pages directly to find qbittorrent posts (titles only)."""
        logger.info("Browsing forum pages for qbittorrent mentions")

        qbittorrent_posts = []
        max_pages = 12

        for page in range(1, max_pages + 1):
            page_url = f"{self.forum_url}?page={page}" if page > 1 else self.forum_url

            await self.human_delay()

            config = CrawlerRunConfig(
                session_id=self.session_id,
                cache_mode=CacheMode.BYPASS,
                js_code=self.create_stealth_js(),
                wait_for="css:body",
                page_timeout=30000
            )

            try:
                result = await crawler.arun(url=page_url, config=config)

                if result.success and result.html:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(result.html, 'lxml')

                    for link in soup.find_all('a', href=lambda h: h and '/t/' in h):
                        title = link.get_text(strip=True) or ''
                        url = link.get('href', '')

                        if not title or not url:
                            continue

                        if url.startswith('/'):
                            url = f"{self.base_url}{url}"

                        title_lower = title.lower()
                        if any(term.lower() in title_lower for term in self.search_variations):
                            qbittorrent_posts.append({
                                'url': url,
                                'title': title,
                                'snippet': title,
                                'found_term': self.search_term
                            })

                    logger.info(f"Forum page {page}: accumulated {len(qbittorrent_posts)} qbittorrent topics")

                    if len(qbittorrent_posts) >= 200:
                        break

            except Exception as e:
                logger.error(f"Error browsing forum page {page}: {e}")
                continue

        logger.info(f"Total candidate qbittorrent topics found on forum listings: {len(qbittorrent_posts)}")
        return qbittorrent_posts

    async def search_forum_via_search_box(self, crawler: AsyncWebCrawler) -> List[Dict[str, str]]:
        """Search forum using the direct search URL."""
        logger.info("Searching forum via direct search URL")

        search_posts = []

        # Go directly to the search URL
        search_url = f"{self.base_url}/f/search.php?text=qbittorrent&searchIn=1&order=default&start=0"
        logger.info(f"Navigating to search URL: {search_url}")

        await self.human_delay()

        config = CrawlerRunConfig(
            session_id=self.session_id,
            cache_mode=CacheMode.BYPASS,
            js_code=self.create_stealth_js(),
            wait_for="css:body",
            page_timeout=45000
        )

        try:
            result = await crawler.arun(url=search_url, config=config)

            if result.success and result.html:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html, 'lxml')

                # Look for search results - topic links
                for link in soup.find_all('a', href=lambda h: h and '/t/' in h):
                    title = link.get_text(strip=True) or ''
                    url = link.get('href', '')

                    if not title or not url:
                        continue

                    if url.startswith('/'):
                        url = f"{self.base_url}{url}"

                    # Include all results from search, they should be relevant since we searched for qBittorrent
                    search_posts.append({
                        'url': url,
                        'title': title,
                        'snippet': f"Found via qBittorrent search: {title}",
                        'found_term': 'qBittorrent direct search'
                    })

                logger.info(f"Direct search results: found {len(search_posts)} topics matching 'qBittorrent'")

                # Check for pagination and get more results
                if search_posts:
                    # Look for pagination links with start parameter
                    pagination_links = soup.find_all('a', href=lambda h: h and 'start=' in h and 'search.php' in h)
                    page_urls = []

                    for pagelink in pagination_links:
                        pagelink_href = pagelink.get('href')
                        if pagelink_href and pagelink_href.startswith('/'):
                            full_url = f"{self.base_url}{pagelink_href}"
                            if full_url not in page_urls:
                                page_urls.append(full_url)

                    # Process more pages to get closer to 150 results (about 25-30 per page)
                    for page_url in page_urls[:10]:  # Check up to 10 additional pages
                        await self.human_delay()

                        page_config = CrawlerRunConfig(
                            session_id=self.session_id,
                            cache_mode=CacheMode.BYPASS,
                            js_code=self.create_stealth_js(),
                            wait_for="css:body",
                            page_timeout=30000
                        )

                        try:
                            page_result = await crawler.arun(url=page_url, config=page_config)

                            if page_result.success and page_result.html:
                                page_soup = BeautifulSoup(page_result.html, 'lxml')

                                for link in page_soup.find_all('a', href=lambda h: h and '/t/' in h):
                                    title = link.get_text(strip=True) or ''
                                    url = link.get('href', '')

                                    if not title or not url:
                                        continue

                                    if url.startswith('/'):
                                        url = f"{self.base_url}{url}"

                                    # Check if we already have this URL
                                    if not any(existing['url'] == url for existing in search_posts):
                                        search_posts.append({
                                            'url': url,
                                            'title': title,
                                            'snippet': f"Found via qBittorrent search page: {title}",
                                            'found_term': 'qBittorrent direct search'
                                        })

                        except Exception as e:
                            logger.error(f"Error browsing search result page: {e}")
                            continue

            else:
                logger.error("Direct search failed or returned no results")

        except Exception as e:
            logger.error(f"Error during direct forum search: {e}")
            import traceback
            traceback.print_exc()

        logger.info(f"Total topics found via qBittorrent direct search: {len(search_posts)}")
        return search_posts

    def extract_post_date_from_html(self, html: str) -> Optional[datetime]:
        """Attempt to extract a post date (first found) from HTML. Returns UTC datetime or None."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')

            time_tag = soup.find('time')
            if time_tag:
                dt = time_tag.get('datetime') or time_tag.get_text(strip=True)
                if dt and date_parser:
                    try:
                        parsed = date_parser.parse(dt)
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        return parsed.astimezone(timezone.utc)
                    except Exception:
                        pass

            for meta_name in ['article:published_time', 'pubdate', 'date', 'dcterms.created']:
                meta = soup.find('meta', attrs={'property': meta_name}) or soup.find('meta', attrs={'name': meta_name})
                if meta and meta.get('content'):
                    if date_parser:
                        try:
                            parsed = date_parser.parse(meta['content'])
                            if parsed.tzinfo is None:
                                parsed = parsed.replace(tzinfo=timezone.utc)
                            return parsed.astimezone(timezone.utc)
                        except Exception:
                            pass

            text = soup.get_text(separator=' ', strip=True)
            patterns = [
                r'(posted(?: on|:)?\s+[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
                r'(last post(?: on|:)?\s+[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
                r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})'
            ]
            for pat in patterns:
                m = re.search(pat, text, flags=re.IGNORECASE)
                if m:
                    candidate = m.group(1)
                    if date_parser:
                        try:
                            parsed = date_parser.parse(candidate, fuzzy=True)
                            if parsed.tzinfo is None:
                                parsed = parsed.replace(tzinfo=timezone.utc)
                            return parsed.astimezone(timezone.utc)
                        except Exception:
                            continue

            month_regex = r'(?:(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\s+\d{1,2},?\s+\d{4}'
            m = re.search(month_regex, text, flags=re.IGNORECASE)
            if m and date_parser:
                try:
                    parsed = date_parser.parse(m.group(0), fuzzy=True)
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed.astimezone(timezone.utc)
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"Date extraction error: {e}")

        return None

    async def crawl_post_with_retry(self, crawler: AsyncWebCrawler, post_info: Dict[str, str], max_retries: int = 3) -> Dict[str, Any]:
        """Crawl individual forum post with retry logic and cutoff filtering."""
        url = post_info['url']
        title = post_info['title']

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Crawling post ({attempt}/{max_retries}): {title} - {url}")

                await self.human_delay()

                config = CrawlerRunConfig(
                    session_id=self.session_id,
                    cache_mode=CacheMode.BYPASS,
                    js_code=self.create_stealth_js(),
                    wait_for="css:body",
                    page_timeout=45000,
                    screenshot=False
                )

                result = await crawler.arun(url=url, config=config)

                if result.success:
                    html = result.html or ""
                    post_date = self.extract_post_date_from_html(html)

                    if post_date:
                        logger.info(f"Found post date: {post_date.isoformat()}")
                        if post_date < self.cutoff_date:
                            logger.info(f"Skipping '{title}' - post older than cutoff ({self.cutoff_date.date()})")
                            return {
                                'success': False,
                                'skipped_old': True,
                                'url': url,
                                'title': title,
                                'post_date': post_date.isoformat(),
                                'reason': 'Older than cutoff'
                            }
                    else:
                        logger.info("Could not determine post date - including by default")

                    post_data = {
                        'success': True,
                        'url': url,
                        'title': title,
                        'content': result.markdown,
                        'metadata': result.metadata,
                        'links': result.links,
                        'crawled_at': datetime.now(timezone.utc).isoformat(),
                        'attempt': attempt,
                        'search_term': post_info.get('found_term'),
                        'snippet': post_info.get('snippet'),
                        'post_date': post_date.isoformat() if post_date else None
                    }

                    logger.info(f"Successfully crawled: {title}")
                    return post_data
                else:
                    logger.warning(f"Attempt {attempt} failed: {result.error_message}")
                    if attempt < max_retries:
                        backoff = min((2 ** attempt) * 8, 60)
                        logger.info(f"Backing off for {backoff} seconds before retry")
                        await asyncio.sleep(backoff)

            except Exception as e:
                logger.error(f"Error on attempt {attempt}: {e}")
                if attempt < max_retries:
                    backoff = min((2 ** attempt) * 8, 60)
                    await asyncio.sleep(backoff)

        return {
            'success': False,
            'url': url,
            'title': title,
            'error': 'Max retries exceeded',
            'attempts': max_retries
        }

    def sanitize_filename(self, title: str) -> str:
        """Convert title to safe filename."""
        filename = re.sub(r'[<>:"/\\|?*]', '', title)
        filename = re.sub(r'\s+', '_', filename)
        return filename[:120]

    def save_post_to_file(self, post_data: Dict[str, Any]):
        """Save forum post to individual markdown file."""
        if not post_data.get('success'):
            return

        filename = self.sanitize_filename(post_data['title']) + ".md"
        filepath = self.output_dir / filename

        content = f"# {post_data['title']}\n\n"
        content += f"**URL:** {post_data['url']}\n\n"
        content += f"**Search Term:** {post_data.get('search_term', 'qbittorrent')}\n\n"

        if post_data.get('snippet'):
            content += f"**Snippet:** {post_data['snippet']}\n\n"

        if post_data.get('post_date'):
            content += f"**Post Date:** {post_data['post_date']}\n\n"

        if post_data.get('metadata'):
            meta = post_data['metadata']
            if meta.get('title'):
                content += f"**Page Title:** {meta['title']}\n\n"
            if meta.get('description'):
                content += f"**Description:** {meta['description']}\n\n"

        content += f"**Crawled:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
        content += f"**Attempts:** {post_data.get('attempt', 1)}\n\n"
        content += "---\n\n"
        content += "## Post Content\n\n"
        content += post_data.get('content', 'No content extracted')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Saved: {filename}")

    def generate_summary_report(self):
        """Generate summary report of crawled posts."""
        report_file = self.output_dir / "FORUM_QBITTORRENT_SUMMARY.md"

        successful = [p for p in self.state.get('completed', []) if isinstance(p, dict)]
        failed = self.state.get('failed', [])
        skipped = self.state.get('skipped_old', [])

        content = f"# MAM Forum qbittorrent Posts Crawl Summary\n\n"
        content += f"**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n"
        content += f"**Search Term:** {self.search_term}\n\n"
        content += f"**Total Candidates Found:** {len(successful) + len(failed) + len(skipped)}\n\n"
        content += f"**Successful:** {len(successful)}\n\n"
        content += f"**Failed:** {len(failed)}\n\n"
        content += f"**Skipped (older than 1.5 years):** {len(skipped)}\n\n"
        content += "---\n\n"

        if successful:
            content += "## Successfully Crawled Posts\n\n"
            for i, post in enumerate(successful, 1):
                if isinstance(post, dict):
                    filename = self.sanitize_filename(post.get('title', 'Untitled')) + ".md"
                    content += f"{i}. [{post.get('title', 'Untitled')}]({filename})\n"
                    content += f"   - URL: {post.get('url', '')}\n"
                    if post.get('snippet'):
                        content += f"   - Snippet: {post.get('snippet', '')[:100]}...\n"
                    if post.get('post_date'):
                        content += f"   - Post Date: {post.get('post_date')}\n"
                    content += "\n"

        if skipped:
            content += "## Skipped (Older than 1.5 years)\n\n"
            for s in skipped:
                if isinstance(s, dict):
                    content += f"- {s.get('title', 'Untitled')} ({s.get('url', '')}) — Post Date: {s.get('post_date', 'Unknown')}\n"
            content += "\n"

        if failed:
            content += "## Failed Posts\n\n"
            for post in failed:
                if isinstance(post, dict):
                    content += f"- {post.get('title', 'Untitled')} ({post.get('url', '')})\n"
                    content += f"  Error: {post.get('error', 'Unknown')}\n"
                else:
                    content += f"- {post}\n"
            content += "\n"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Summary report saved to {report_file}")

    async def run(self):
        """Main execution with stealth and state management."""
        logger.info("=" * 80)
        logger.info("Starting STEALTH MAM Forum qbittorrent Crawler (forums-only, last 1.5 years)")
        logger.info("=" * 80)

        browser_config = self.create_browser_config()
        logger.info(f"Viewport: {browser_config.viewport_width}x{browser_config.viewport_height}")

        async with AsyncWebCrawler(config=browser_config) as crawler:
            if not await self.authenticate(crawler):
                logger.error("Authentication failed. Exiting.")
                return

            qbittorrent_posts = await self.search_forum_posts(crawler)

            if not qbittorrent_posts:
                logger.warning("No qbittorrent-related topics found on forum listings.")
                return

            completed_urls = set()
            for completed in self.state.get('completed', []):
                if isinstance(completed, dict):
                    completed_urls.add(completed.get('url', ''))
                else:
                    completed_urls.add(completed)

            pending_posts = [p for p in qbittorrent_posts if p['url'] not in completed_urls]

            logger.info(f"Total qbittorrent topics found: {len(qbittorrent_posts)}")
            logger.info(f"Already completed: {len(completed_urls)}")
            logger.info(f"Pending: {len(pending_posts)}")

            if not pending_posts:
                logger.info("All qbittorrent topics already crawled!")
                return

            for i, post_info in enumerate(pending_posts, 1):
                logger.info("\n" + "=" * 80)
                logger.info(f"Progress: {i}/{len(pending_posts)} (Total: {len(completed_urls) + i}/{len(qbittorrent_posts)})")
                logger.info("=" * 80 + "\n")

                post_data = await self.crawl_post_with_retry(crawler, post_info)

                if post_data.get('skipped_old'):
                    self.state['skipped_old'].append({
                        'url': post_data['url'],
                        'title': post_data['title'],
                        'post_date': post_data.get('post_date'),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    logger.info(f"Skipped (old): {post_data['title']}")
                elif post_data.get('success'):
                    self.save_post_to_file(post_data)
                    self.state['completed'].append({
                        'url': post_data['url'],
                        'title': post_data['title'],
                        'post_date': post_data.get('post_date'),
                        'crawled_at': post_data.get('crawled_at')
                    })
                else:
                    self.state['failed'].append({
                        'url': post_data.get('url'),
                        'title': post_data.get('title'),
                        'error': post_data.get('error'),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })

                self.save_state()

                success_count = len([c for c in self.state['completed'] if isinstance(c, dict)])
                fail_count = len(self.state['failed'])
                skipped_count = len(self.state['skipped_old'])
                logger.info(f"Session stats: Successful {success_count} | Failed {fail_count} | Skipped {skipped_count}")

            self.generate_summary_report()

            logger.info("\n" + "=" * 80)
            logger.info("FORUM CRAWL COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Successfully crawled: {len([c for c in self.state['completed'] if isinstance(c, dict)])} qbittorrent posts")
            logger.info(f"Failed: {len(self.state['failed'])} posts")
            logger.info(f"Skipped (older than 1.5 years): {len(self.state.get('skipped_old', []))}")
            logger.info(f"Output directory: {self.output_dir.absolute()}")
            logger.info("=" * 80)

async def main():
    """Entry point."""
    try:
        crawler = StealthMAMForumCrawler()
        await crawler.run()
    except KeyboardInterrupt:
        logger.info("\nCrawl interrupted by user")
        logger.info("Progress has been saved - run again to resume")
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
