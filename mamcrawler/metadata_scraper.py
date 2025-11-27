"""
Metadata Scraper (Scraper B)
Enforces strict identity rules for metadata scraping (Goodreads, Audible, etc.).
Rules (Section 21):
- Normal WAN IP (No Proxy)
- Local DNS
- Random User Agent
- Human-like Timing (Random delays, scroll pauses)
"""

import logging
from mamcrawler.stealth import StealthCrawler

logger = logging.getLogger(__name__)

class MetadataScraper(StealthCrawler):
    """
    Scraper B Identity: Metadata Scraping.
    Strictly enforces NO PROXY and HUMAN-LIKE behavior.
    """

    def __init__(self):
        # Initialize with METADATA Identity (Scraper B)
        super().__init__(state_file="metadata_scraper_state.json", identity_type='METADATA')
        
        # Verify NO PROXY is set
        if self.proxy:
            logger.critical("🚨 CRITICAL SECURITY VIOLATION: Proxy detected in Metadata Scraper!")
            raise RuntimeError("Metadata Scraper MUST NOT use a proxy (Section 21).")

    async def human_like_delay(self):
        """Execute human-like delay (1.5s - 9s)."""
        await self.human_delay(min_seconds=1.5, max_seconds=9.0)
