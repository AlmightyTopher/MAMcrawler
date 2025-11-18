"""
Stealth MAM Guides Crawler - Human-like behavior with realistic timing
- Random delays (10-30 seconds between pages)
- Mouse movement and scrolling simulation
- Viewport randomization
- Sequential processing (no batch)
- State persistence for resume capability
- Retry logic with exponential backoff
"""

import asyncio
import os
import re
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

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
        logging.FileHandler('stealth_crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class StealthMAMCrawler:
    """Stealth crawler with human-like behavior."""

    def __init__(self):
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')

        if not self.username or not self.password:
            raise ValueError("MAM_USERNAME and MAM_PASSWORD must be set in .env file")

        self.base_url = "https://www.myanonamouse.net"
        self.session_id = "mam_stealth_session"
        self.is_authenticated = False

        self.output_dir = Path("guides_output")
        self.output_dir.mkdir(exist_ok=True)

        self.state_file = Path("crawler_state.json")
        self.state = self.load_state()

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
                logger.info(f"Loaded state: {len(state.get('completed', []))} guides already crawled")
                return state
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

        return {
            'completed': [],
            'failed': [],
            'pending': [],
            'last_run': None
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
            # Additional stealth settings
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
                        with open('stealth_login_success.png', 'wb') as f:
                            f.write(screenshot_data)

                    return True
                else:
                    logger.error("❌ Authentication failed")
                    if result.screenshot:
                        import base64
                        screenshot_data = base64.b64decode(result.screenshot) if isinstance(result.screenshot, str) else result.screenshot
                        with open('stealth_login_failed.png', 'wb') as f:
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

    async def extract_guide_links(self, crawler: AsyncWebCrawler) -> List[Dict[str, str]]:
        """Extract all guide links from main page."""
        guides_url = f"{self.base_url}/guides/"
        logger.info(f"📋 Extracting guide links from: {guides_url}")

        await self.human_delay(5, 10)

        config = CrawlerRunConfig(
            session_id=self.session_id,
            cache_mode=CacheMode.BYPASS,
            js_code=self.create_stealth_js(),
            wait_for="css:body",
            page_timeout=30000
        )

        try:
            result = await crawler.arun(url=guides_url, config=config)

            if result.success and result.html:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html, 'lxml')

                guide_links = []
                seen_urls = set()

                for link in soup.find_all('a', href=lambda h: h and '/guides/' in h):
                    url = link.get('href', '')
                    title = link.get_text(strip=True) or 'Untitled'

                    if url.startswith('/'):
                        url = f"{self.base_url}{url}"

                    if url in seen_urls or url == guides_url or not '/guides/' in url:
                        continue

                    seen_urls.add(url)

                    guide_links.append({
                        'url': url,
                        'title': title,
                        'category': self.extract_category_from_url(url)
                    })

                logger.info(f"✅ Found {len(guide_links)} unique guide links")
                return guide_links

        except Exception as e:
            logger.error(f"Error extracting links: {e}")
            import traceback
            traceback.print_exc()

        return []

    def extract_category_from_url(self, url: str) -> str:
        """Extract category from URL."""
        if '?gid=' in url:
            return "Guide"
        path_parts = url.rstrip('/').split('/')
        if len(path_parts) >= 2:
            category = path_parts[-2] if path_parts[-1] else path_parts[-2]
            if category != 'guides':
                return category.replace('-', ' ').replace('_', ' ').title()
        return "General"

    async def crawl_guide_with_retry(self, crawler: AsyncWebCrawler, guide_info: Dict[str, str], max_retries: int = 3) -> Dict[str, Any]:
        """Crawl individual guide with retry logic and exponential backoff."""
        url = guide_info['url']
        title = guide_info['title']

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"📖 Crawling guide ({attempt}/{max_retries}): {title}")

                # Human-like delay before crawling
                await self.human_delay()

                config = CrawlerRunConfig(
                    session_id=self.session_id,
                    cache_mode=CacheMode.BYPASS,
                    js_code=self.create_stealth_js(),
                    wait_for="css:body",
                    page_timeout=45000,
                    screenshot=False  # Save bandwidth
                )

                result = await crawler.arun(url=url, config=config)

                if result.success:
                    guide_data = {
                        'success': True,
                        'url': url,
                        'title': title,
                        'category': guide_info['category'],
                        'content': result.markdown,
                        'metadata': result.metadata,
                        'links': result.links,
                        'crawled_at': datetime.now().isoformat(),
                        'attempt': attempt
                    }

                    logger.info(f"✅ Successfully crawled: {title}")
                    return guide_data
                else:
                    logger.warning(f"⚠️  Attempt {attempt} failed: {result.error_message}")

                    # Exponential backoff
                    if attempt < max_retries:
                        backoff = (2 ** attempt) * 5  # 10s, 20s, 40s
                        logger.info(f"⏱️  Backing off for {backoff} seconds before retry...")
                        await asyncio.sleep(backoff)

            except Exception as e:
                logger.error(f"❌ Error on attempt {attempt}: {e}")
                if attempt < max_retries:
                    backoff = (2 ** attempt) * 5
                    await asyncio.sleep(backoff)

        # All retries failed
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
        return filename[:100]

    def save_guide_to_file(self, guide_data: Dict[str, Any]):
        """Save guide to individual markdown file."""
        if not guide_data.get('success'):
            return

        filename = self.sanitize_filename(guide_data['title']) + ".md"
        filepath = self.output_dir / filename

        content = f"# {guide_data['title']}\n\n"
        content += f"**URL:** {guide_data['url']}\n\n"
        content += f"**Category:** {guide_data.get('category', 'General')}\n\n"

        if guide_data.get('metadata'):
            meta = guide_data['metadata']
            if meta.get('title'):
                content += f"**Page Title:** {meta['title']}\n\n"
            if meta.get('description'):
                content += f"**Description:** {meta['description']}\n\n"

        content += f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"**Attempts:** {guide_data.get('attempt', 1)}\n\n"
        content += "---\n\n"

        # Add related links
        if guide_data.get('links'):
            internal_links = guide_data['links'].get('internal', [])
            if internal_links:
                guide_links = [link for link in internal_links if '/guides/' in link]
                if guide_links:
                    content += "## Related Guides\n\n"
                    for link in guide_links[:20]:
                        content += f"- {link}\n"
                    content += "\n---\n\n"

        content += "## Content\n\n"
        content += guide_data.get('content', 'No content extracted')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"💾 Saved: {filename}")

    async def run(self):
        """Main execution with stealth and state management."""
        logger.info("="*70)
        logger.info("🕵️  Starting STEALTH MAM Guides Crawler")
        logger.info("="*70)

        # Create browser with randomized config
        browser_config = self.create_browser_config()
        logger.info(f"🖥️  Viewport: {browser_config.viewport_width}x{browser_config.viewport_height}")

        async with AsyncWebCrawler(config=browser_config) as crawler:
            # Step 1: Authenticate
            if not await self.authenticate(crawler):
                logger.error("❌ Authentication failed. Exiting.")
                return

            # Step 2: Extract guide links
            all_guides = await self.extract_guide_links(crawler)

            if not all_guides:
                logger.error("❌ No guide links found. Exiting.")
                return

            # Step 3: Filter out already completed guides
            completed_urls = set(self.state.get('completed', []))
            pending_guides = [g for g in all_guides if g['url'] not in completed_urls]

            logger.info(f"📊 Total guides: {len(all_guides)}")
            logger.info(f"✅ Already completed: {len(completed_urls)}")
            logger.info(f"⏳ Pending: {len(pending_guides)}")

            if not pending_guides:
                logger.info("🎉 All guides already crawled!")
                return

            # Step 4: Crawl guides sequentially with human timing
            for i, guide_info in enumerate(pending_guides, 1):
                logger.info(f"\n{'='*70}")
                logger.info(f"Progress: {i}/{len(pending_guides)} (Total: {len(completed_urls) + i}/{len(all_guides)})")
                logger.info(f"{'='*70}\n")

                guide_data = await self.crawl_guide_with_retry(crawler, guide_info)

                if guide_data.get('success'):
                    self.save_guide_to_file(guide_data)
                    self.state['completed'].append(guide_data['url'])
                else:
                    self.state['failed'].append({
                        'url': guide_data['url'],
                        'title': guide_data['title'],
                        'error': guide_data.get('error'),
                        'timestamp': datetime.now().isoformat()
                    })

                # Save state after each guide
                self.save_state()

                # Show progress
                success_count = len(self.state['completed'])
                fail_count = len(self.state['failed'])
                logger.info(f"📈 Session stats: ✅ {success_count} | ❌ {fail_count}")

            # Final summary
            logger.info("\n" + "="*70)
            logger.info("🎯 CRAWL COMPLETE")
            logger.info("="*70)
            logger.info(f"✅ Successfully crawled: {len(self.state['completed'])} guides")
            logger.info(f"❌ Failed: {len(self.state['failed'])} guides")
            logger.info(f"📁 Output directory: {self.output_dir.absolute()}")
            logger.info("="*70)


async def main():
    """Entry point."""
    try:
        crawler = StealthMAMCrawler()
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
