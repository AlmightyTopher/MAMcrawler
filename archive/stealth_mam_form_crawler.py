"""
Stealth MAM Audiobookshelf Search Crawler
- Searches for Audiobookshelf-related content on MyAnonamouse
- Handles pagination automatically
- Extracts metadata: title, author, size, download links
- Human-like behavior with realistic timing
"""

import asyncio
import os
import re
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, parse_qs

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stealth_audiobookshelf_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StealthMAMAudiobookshelfCrawler:
    """Stealth crawler for Audiobookshelf content on MAM."""

    def __init__(self):
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env file")

        self.base_url = "https://www.myanonamouse.net"
        self.session_id = "mam_audiobookshelf_session"
        self.is_authenticated = False

        self.output_dir = Path("audiobookshelf_output")
        self.output_dir.mkdir(exist_ok=True)

        self.state_file = Path("audiobookshelf_crawler_state.json")
        self.state = self.load_state()

        # Search terms and URLs - forum search for Audiobookshelf discussions
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

    def load_state(self) -> Dict:
        """Load crawler state for resume capability."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
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
            headless=True,
            viewport_width=width,
            viewport_height=height,
            verbose=False,
            user_agent=self.get_random_user_agent(),
            ignore_https_errors=False,
            java_script_enabled=True
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

    async def authenticate(self, crawler: AsyncWebCrawler) -> bool:
        """Authenticate with human-like behavior."""
        if self.is_authenticated:
            logger.info("Already authenticated")
            return True

        logger.info("🔐 Authenticating with MyAnonamouse (stealth mode)...")

        # Initial delay before login
        await self.human_delay(3, 7)

        try:
            login_url = f"{self.base_url}/login.php"

            # JavaScript for realistic login
            js_login = f"""
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

                emailInput.value = '{self.username}';
                await new Promise(resolve => setTimeout(resolve, {random.randint(800, 1500)}));

                passwordInput.focus();
                await new Promise(resolve => setTimeout(resolve, {random.randint(500, 1000)}));

                passwordInput.value = '{self.password}';
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
                response_text = result.markdown.lower()

                if "logout" in response_text or "my account" in response_text or "tophertek" in response_text:
                    logger.info("✅ Authentication successful")
                    self.is_authenticated = True

                    if result.screenshot:
                        import base64
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        with open('stealth_audiobookshelf_login_success.png', 'wb') as f:
                            f.write(screenshot_data)

                    return True
                else:
                    logger.error("❌ Authentication failed")
                    if result.screenshot:
                        import base64
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        with open('stealth_audiobookshelf_login_failed.png', 'wb') as f:
                            f.write(screenshot_data)
                    return False
            else:
                logger.error(f"❌ Browser automation failed: {result.error_message}")
                return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def extract_forum_metadata(self, html: str) -> List[Dict[str, Any]]:
        """Extract forum post metadata from search results page."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        posts = []

        # Debug: Save HTML for inspection
        debug_file = self.output_dir / f"debug_{self.current_search_term.replace(' ', '_').lower()}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"🔍 Debug HTML saved to: {debug_file}")

        # Find forum post containers - MAM forum search results use divs with classes row1, row2
        post_containers = soup.find_all('div', class_=lambda x: bool(x and isinstance(x, str) and ('row1' in x or 'row2' in x)))

        logger.info(f"🔍 Found {len(post_containers)} potential forum post containers")

        for container in post_containers:
            try:
                post_data = {}

                # Skip containers that don't have forum links (pagination, etc.)
                if not container.find('a'):
                    continue

                # Extract forum title and link (first link)
                forum_link = container.find('a')
                if forum_link:
                    post_data['forum_title'] = forum_link.get_text(strip=True)
                    href = forum_link.get('href')
                    if href and isinstance(href, str):
                        if href.startswith('/'):
                            post_data['forum_url'] = f"{self.base_url}{href}"
                        else:
                            post_data['forum_url'] = href

                # Extract post title and link (second link)
                all_links = container.find_all('a')
                if len(all_links) >= 2:
                    post_link = all_links[1]  # Second link is the post title
                    post_data['post_title'] = post_link.get_text(strip=True)
                    href = post_link.get('href')
                    if href and isinstance(href, str):
                        if href.startswith('/'):
                            post_data['post_url'] = f"{self.base_url}{href}"
                        else:
                            post_data['post_url'] = href

                # Extract author (span with color style)
                author_span = container.find('span', style=lambda s: bool(s and 'color:' in str(s)))
                if author_span:
                    post_data['author'] = author_span.get_text(strip=True)

                # Extract post date (look for date pattern in text)
                date_text = None
                for text in container.stripped_strings:
                    # Look for date pattern like "2023-11-26 06:24:38"
                    if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', text):
                        date_text = text
                        break
                if date_text:
                    post_data['post_date'] = date_text

                # Extract post snippet/content (div with forumSearchReduce class)
                content_div = container.find('div', class_='forumSearchReduce')
                if content_div:
                    # Remove any links from content for cleaner text
                    for link in content_div.find_all('a'):
                        link.decompose()
                    post_data['content_snippet'] = content_div.get_text(strip=True)[:500]  # Limit to 500 chars

                # Extract additional metadata
                post_data['category'] = 'Audiobookshelf Forum'
                post_data['search_term'] = self.current_search_term
                post_data['crawled_at'] = datetime.now().isoformat()

                # Only add if we have essential data
                if post_data.get('post_title') and post_data.get('post_url'):
                    posts.append(post_data)
                    logger.debug(f"✅ Extracted post: {post_data['post_title'][:50]}...")

            except Exception as e:
                logger.warning(f"Error extracting forum post data: {e}")
                continue

        logger.info(f"✅ Successfully extracted {len(posts)} forum posts")
        return posts

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
                # Extract forum post metadata
                torrents = self.extract_forum_metadata(result.html)

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

            logger.info(f"💾 Saved {len(new_torrents)} new torrents to {filename} (total: {len(combined_data)})")
        else:
            logger.info(f"ℹ️  No new torrents to save for {search_term}")

    async def crawl_individual_post(self, crawler: AsyncWebCrawler, post_url: str, search_term: str) -> Dict[str, Any]:
        """Visit individual post URL and extract full content by clicking 'Show more'."""
        logger.info(f"📖 Visiting individual post: {post_url}")

        await self.human_delay(5, 15)  # Longer delay for individual posts

        # JavaScript to click "Show more" buttons and extract full content
        js_expand_content = """
        async function expandAndExtractContent() {
            // Wait for page to load
            await new Promise(resolve => setTimeout(resolve, 2000));

            // Click all "Show more" or "Show More" buttons
            const showMoreButtons = document.querySelectorAll('div.forSTswap.fse, a[href*="showmore"], button[onclick*="showmore"]');
            for (const button of showMoreButtons) {
                try {
                    button.click();
                    await new Promise(resolve => setTimeout(resolve, 1000));
                } catch (e) {
                    console.log('Could not click button:', e);
                }
            }

            // Wait for content to expand
            await new Promise(resolve => setTimeout(resolve, 3000));

            // Extract the main post content
            const postContent = {};

            // Try to find the main post content area
            const contentSelectors = [
                '.post-content',
                '.post-body',
                '.message-content',
                '.forum-post-content',
                '[class*="post"][class*="content"]',
                '.post'
            ];

            let mainContent = '';
            for (const selector of contentSelectors) {
                const elements = document.querySelectorAll(selector);
                if (elements.length > 0) {
                    // Get the first substantial content
                    for (const el of elements) {
                        const text = el.textContent?.trim();
                        if (text && text.length > 100) {  // Substantial content
                            mainContent = text;
                            break;
                        }
                    }
                    if (mainContent) break;
                }
            }

            // If no specific selector worked, get all paragraph text
            if (!mainContent) {
                const paragraphs = document.querySelectorAll('p');
                const paraTexts = [];
                for (const p of paragraphs) {
                    const text = p.textContent?.trim();
                    if (text && text.length > 20) {
                        paraTexts.push(text);
                    }
                }
                mainContent = paraTexts.join('\\n\\n');
            }

            // Get post metadata
            const title = document.querySelector('h1, .thread-title, .post-title')?.textContent?.trim() || '';
            const author = document.querySelector('.post-author, .username, [class*="author"]')?.textContent?.trim() || '';
            const date = document.querySelector('.post-date, .timestamp, time')?.textContent?.trim() || '';

            // Get quoted content separately
            const quotes = [];
            const quoteElements = document.querySelectorAll('.quote, blockquote, [class*="quote"]');
            for (const quote of quoteElements) {
                const quoteText = quote.textContent?.trim();
                if (quoteText && quoteText.length > 10) {
                    quotes.push(quoteText);
                }
            }

            return {
                title: title,
                author: author,
                date: date,
                full_content: mainContent,
                quotes: quotes,
                url: window.location.href
            };
        }

        return await expandAndExtractContent();
        """

        config = CrawlerRunConfig(
            session_id=self.session_id,
            cache_mode=CacheMode.BYPASS,
            js_code=js_expand_content,
            wait_for="css:body",
            page_timeout=60000
        )

        try:
            result = await crawler.arun(url=post_url, config=config)

            if result.success and result.markdown:
                try:
                    # Parse the returned JSON
                    import json
                    content_data = json.loads(result.markdown)

                    post_data = {
                        'post_url': post_url,
                        'search_term': search_term,
                        'full_title': content_data.get('title', ''),
                        'full_author': content_data.get('author', ''),
                        'full_date': content_data.get('date', ''),
                        'full_content': content_data.get('full_content', ''),
                        'quotes': content_data.get('quotes', []),
                        'crawled_at': datetime.now().isoformat(),
                        'content_length': len(content_data.get('full_content', ''))
                    }

                    logger.info(f"✅ Extracted full content: {len(post_data['full_content'])} chars")
                    return post_data

                except json.JSONDecodeError as e:
                    logger.warning(f"Could not parse content JSON: {e}")
                    return {
                        'post_url': post_url,
                        'search_term': search_term,
                        'error': f'JSON parse error: {e}',
                        'crawled_at': datetime.now().isoformat()
                    }
            else:
                logger.warning(f"Failed to crawl individual post: {result.error_message}")
                return {
                    'post_url': post_url,
                    'search_term': search_term,
                    'error': result.error_message,
                    'crawled_at': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error crawling individual post {post_url}: {e}")
            return {
                'post_url': post_url,
                'search_term': search_term,
                'error': str(e),
                'crawled_at': datetime.now().isoformat()
            }

    def save_full_content_to_file(self, full_posts: List[Dict[str, Any]], search_term: str):
        """Save full post content to JSON file."""
        if not full_posts:
            return

        filename = f"audiobookshelf_{search_term.replace(' ', '_').lower()}_full_content.json"
        filepath = self.output_dir / filename

        # Load existing data if file exists
        existing_data = []
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load existing full content data: {e}")

        # Merge new data (avoid duplicates by URL)
        existing_urls = {p.get('post_url') for p in existing_data}
        new_posts = [p for p in full_posts if p.get('post_url') not in existing_urls]

        if new_posts:
            combined_data = existing_data + new_posts

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Saved {len(new_posts)} full posts to {filename} (total: {len(combined_data)})")
        else:
            logger.info(f"ℹ️  No new full posts to save for {search_term}")

    async def crawl_full_content(self, crawler: AsyncWebCrawler, search_term: str):
        """Crawl full content for all posts found in search results."""
        logger.info(f"📖 Starting full content crawl for: {search_term}")

        # Load the search results
        results_file = self.output_dir / f"audiobookshelf_{search_term.replace(' ', '_').lower()}_results.json"
        if not results_file.exists():
            logger.warning(f"No search results file found for {search_term}")
            return

        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)
        except Exception as e:
            logger.error(f"Could not load search results: {e}")
            return

        # Filter posts to only MAM forum posts (not external links)
        mam_posts = [p for p in posts if p.get('post_url', '').startswith('https://www.myanonamouse.net/')]

        logger.info(f"📖 Found {len(mam_posts)} MAM posts to crawl for full content")

        full_posts = []
        processed_count = 0

        for post in mam_posts:
            post_url = post.get('post_url')
            if not post_url:
                continue

            # Check if we've already crawled this post
            content_key = f"full_{post_url}"
            if content_key in self.state.get('completed', []):
                logger.debug(f"⏭️  Already crawled full content: {post_url}")
                continue

            processed_count += 1
            logger.info(f"📖 Processing post {processed_count}/{len(mam_posts)}: {post_url}")

            full_post_data = await self.crawl_individual_post(crawler, post_url, search_term)

            if full_post_data and 'error' not in full_post_data:
                full_posts.append(full_post_data)
                self.state['completed'].append(content_key)

                # Save periodically (every 5 posts)
                if len(full_posts) >= 5:
                    self.save_full_content_to_file(full_posts, search_term)
                    full_posts = []
                    self.save_state()
            else:
                logger.warning(f"Failed to get full content for: {post_url}")
                self.state['failed'].append({
                    'url': post_url,
                    'type': 'full_content',
                    'search_term': search_term,
                    'error': full_post_data.get('error', 'Unknown error'),
                    'timestamp': datetime.now().isoformat()
                })

            # Limit to avoid overwhelming the server (max 20 posts per search term)
            if processed_count >= 20:
                logger.warning(f"⚠️  Reached post limit (20) for {search_term}")
                break

        # Save any remaining posts
        if full_posts:
            self.save_full_content_to_file(full_posts, search_term)

        self.save_state()
        logger.info(f"🏁 Completed full content crawl for {search_term}: {processed_count} posts processed")

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
        logger.info("🕵️  Starting STEALTH MAM Audiobookshelf Search Crawler")
        logger.info("="*70)

        # Create browser with randomized config
        browser_config = self.create_browser_config()
        logger.info(f"🖥️  Viewport: {browser_config.viewport_width}x{browser_config.viewport_height}")

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

            # Step 3: Crawl full content for each search term
            logger.info(f"\n{'='*70}")
            logger.info("📖 PHASE 2: EXTRACTING FULL CONTENT")
            logger.info(f"{'='*70}\n")

            for search_term in self.search_terms:
                logger.info(f"\n{'='*70}")
                logger.info(f"📖 Full Content {self.search_terms.index(search_term) + 1}/{len(self.search_terms)}: {search_term}")
                logger.info(f"{'='*70}\n")

                await self.crawl_full_content(crawler, search_term)

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

    def create_summary_report(self):
        """Create a summary report of all crawled data."""
        summary_file = self.output_dir / "AUDIOBOOKSHELF_CRAWL_SUMMARY.md"

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
        content = "# Audiobookshelf Search Results Summary\n\n"
        content += f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**Total Torrents Found:** {total_torrents}\n\n"
        content += "## Search Results by Term\n\n"

        for term, count in search_stats.items():
            content += f"- **{term}:** {count} torrents\n"

        content += "\n## Output Files\n\n"
        for json_file in sorted(self.output_dir.glob("audiobookshelf_*.json")):
            content += f"- {json_file.name}\n"

        content += "\n## Metadata Extracted\n\n"
        content += "- Title\n"
        content += "- Author/Uploader\n"
        content += "- Size\n"
        content += "- Download Links\n"
        content += "- Category (Audiobookshelf)\n"
        content += "- Search Term\n"
        content += "- Crawl Timestamp\n"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"📊 Summary report created: {summary_file}")


async def main():
    """Entry point."""
    try:
        crawler = StealthMAMAudiobookshelfCrawler()
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
