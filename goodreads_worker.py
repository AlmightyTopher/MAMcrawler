"""
Goodreads Worker Script.
Executed by the Dual Scraper orchestrator.
Uses the Shared Stealth Library.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to path to import mamcrawler
sys.path.append(str(Path(__file__).parent))

from mamcrawler.stealth import StealthCrawler
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("GoodreadsWorker")

class GoodreadsWorker(StealthCrawler):
    def __init__(self, worker_id: str, output_file: str):
        super().__init__(state_file=f"goodreads_state_{worker_id}.json")
        self.worker_id = worker_id
        self.output_file = Path(output_file)
        self.results = []

    async def search_book(self, crawler: AsyncWebCrawler, query: str) -> Dict:
        """Search for a book on Goodreads."""
        encoded_query = query.replace(" ", "+")
        url = f"https://www.goodreads.com/search?q={encoded_query}"
        
        logger.info(f"[{self.worker_id}] 🔍 Searching: {query}")
        
        # Human-like delay
        await self.human_delay(5, 10)

        config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=self.create_stealth_js(),
            wait_for="css:body",
            page_timeout=60000
        )

        result = await crawler.arun(url=url, config=config)
        
        if result.success:
            logger.info(f"[{self.worker_id}] ✅ Found results for: {query}")
            return {
                "query": query,
                "success": True,
                "url": result.url,
                "html": result.html[:1000] + "..." # Truncated for now
            }
        else:
            logger.warning(f"[{self.worker_id}] ❌ Failed to search: {query}")
            return {
                "query": query,
                "success": False,
                "error": result.error_message
            }

    async def process_queue(self, queries: List[str]):
        """Process a list of search queries."""
        browser_config = self.create_browser_config(headless=True)
        
        async with AsyncWebCrawler(config=browser_config) as crawler:
            for query in queries:
                result = await self.search_book(crawler, query)
                self.results.append(result)
                
                # Save intermediate results
                self.save_results()

    def save_results(self):
        """Save results to JSON file."""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Goodreads Worker")
    parser.add_argument("--id", required=True, help="Worker ID (vpn/direct)")
    parser.add_argument("--input", required=True, help="Input JSON file with queries")
    parser.add_argument("--output", required=True, help="Output JSON file")
    
    args = parser.parse_args()
    
    # Load queries
    try:
        with open(args.input, 'r') as f:
            queries = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load input file: {e}")
        return

    worker = GoodreadsWorker(args.id, args.output)
    await worker.process_queue(queries)

if __name__ == "__main__":
    asyncio.run(main())
