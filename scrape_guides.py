#!/usr/bin/env python3
"""
Script to scrape MyAnonamouse.net guides section for sub-links and metadata.
Uses MAMPassiveCrawler to perform asynchronous crawling with rate limiting.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

from mam_crawler import MAMPassiveCrawler, MAMDataProcessor

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG level as requested
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scrape_guides.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def scrape_guides_section() -> List[Dict[str, Any]]:
    """
    Scrape the guides section of MAM to collect sub-links and metadata.

    Returns:
        List of guide data dictionaries with metadata
    """
    logger.info("Starting MAM guides section scraping")

    # Initialize crawler
    crawler = MAMPassiveCrawler()

    # Scrape guides section
    logger.info("Crawling guides section...")
    guides_data = await crawler.crawl_guides_section()

    logger.info(f"Collected {len(guides_data)} guide entries")

    # Extract sub-links and metadata from successful crawls
    all_metadata = []
    for guide in guides_data:
        if guide.get("success") and guide.get("data"):
            data = guide["data"]

            # Extract metadata from the guide data
            metadata = {
                "url": guide.get("url", ""),
                "title": data.get("title", ""),
                "date": data.get("timestamp", ""),
                "tags": data.get("tags", ""),
                "sub_links": data.get("sub_links", []),
                "crawled_at": guide.get("crawled_at", ""),
                "content_length": len(data.get("content", "")),
                "description": data.get("description", ""),
                "author": data.get("author", "")
            }

            # Add sub-links as separate entries if they exist
            if metadata["sub_links"]:
                for sub_link in metadata["sub_links"]:
                    if sub_link.startswith('/'):
                        sub_link = f"https://www.myanonamouse.net{sub_link}"

                    sub_metadata = metadata.copy()
                    sub_metadata["url"] = sub_link
                    sub_metadata["is_sub_link"] = True
                    sub_metadata["parent_url"] = guide.get("url", "")
                    all_metadata.append(sub_metadata)

            # Add the main guide entry
            metadata["is_sub_link"] = False
            all_metadata.append(metadata)

    logger.info(f"Extracted metadata for {len(all_metadata)} entries")
    return all_metadata

async def main():
    """Main execution function."""
    try:
        # Scrape guides section
        metadata = await scrape_guides_section()

        # Save to JSON file
        with open('crawl_results.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(metadata)} metadata entries to crawl_results.json")

        # Process with MAMDataProcessor for additional output
        processor = MAMDataProcessor()

        # Create sample guide data for processing (since we only have metadata)
        sample_guide_data = []
        for item in metadata:
            if not item.get("is_sub_link"):  # Only process main guides
                sample_guide_data.append({
                    "success": True,
                    "url": item["url"],
                    "title": item["title"],
                    "crawled_at": item["crawled_at"],
                    "data": {
                        "title": item["title"],
                        "description": item.get("description", ""),
                        "author": item.get("author", ""),
                        "timestamp": item.get("date", ""),
                        "content": f"Content length: {item.get('content_length', 0)} characters",
                        "tags": item.get("tags", "")
                    }
                })

        # Process guides data
        guides_md = processor.process_guides_data(sample_guide_data)

        # Create qBittorrent section (empty for now)
        qb_md = "# qBittorrent Settings & Configurations\n\nCrawl Timestamp: {}\n\nNo qBittorrent configuration content was successfully extracted.\n\n".format(
            datetime.now().isoformat()
        )

        # Save to markdown output
        processor.save_markdown_output(guides_md, qb_md, "mam_crawl_output.md")

        # Log file sizes and previews
        logger.info("=== File Summary ===")
        logger.info(f"crawl_results.json size: {os.path.getsize('crawl_results.json')} bytes")
        logger.info(f"mam_crawl_output.md size: {os.path.getsize('mam_crawl_output.md')} bytes")

        # Preview large files
        if len(metadata) > 0:
            logger.info("=== Preview of crawl_results.json (first entry) ===")
            logger.info(json.dumps(metadata[0], indent=2, ensure_ascii=False)[:1000] + "...")

        logger.info("Scraping completed successfully")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())