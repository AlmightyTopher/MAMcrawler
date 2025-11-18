#!/usr/bin/env python3
"""
Main runner script for the MAM Passive Crawling Service.
This script sets up environment variables and runs the crawler.
"""

import os
import sys
import argparse
import logging
import asyncio
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Set up environment variables for MAM credentials."""
    # Check if credentials are already set
    username = os.getenv('MAM_USERNAME')
    password = os.getenv('MAM_PASSWORD')

    # Only prompt if credentials are not set and we're in interactive mode
    if not username:
        # Check if we're running in a non-interactive environment
        import sys
        if not sys.stdin.isatty():
            logger.warning("MAM_USERNAME not set and running in non-interactive mode. Set environment variable or use --setup-env interactively.")
            return False

        username = input("Enter MAM username (dogmansemail1@gmail.com): ").strip()
        if not username:
            username = "dogmansemail1@gmail.com"
        os.environ['MAM_USERNAME'] = username

    if not password:
        # Check if we're running in a non-interactive environment
        import sys
        if not sys.stdin.isatty():
            logger.warning("MAM_PASSWORD not set and running in non-interactive mode. Set environment variable or use --setup-env interactively.")
            return False

        password = input("Enter MAM password (Tesl@ismy#1): ").strip()
        if not password:
            password = "Tesl@ismy#1"
        os.environ['MAM_PASSWORD'] = password

    logger.info("Environment variables set up successfully")
    return True

def check_venv():
    """Check if we're running in a virtual environment."""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        logger.warning("Not running in a virtual environment. Please activate venv first.")
        logger.warning("Run: venv\\Scripts\\activate (Windows) or source venv/bin/activate (Linux/Mac)")
        return False
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='MAM Passive Crawling Service')
    parser.add_argument('--output', '-o', default='mam_crawl_output.md',
                       help='Output file for crawled data (default: mam_crawl_output.md)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Set logging level')
    parser.add_argument('--setup-env', action='store_true',
                       help='Prompt for environment setup')

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Check virtual environment
    if not check_venv():
        sys.exit(1)

    # Setup environment if requested
    if args.setup_env:
        if not setup_environment():
            logger.error("Failed to set up environment variables. Run interactively or set MAM_USERNAME and MAM_PASSWORD environment variables.")
            sys.exit(1)

    # Import and run the crawler
    try:
        from mam_crawler import main as crawler_main
        logger.info("Starting MAM Passive Crawling Service...")
        asyncio.run(crawler_main())
        logger.info(f"Crawling completed. Check {args.output} for results.")

    except ImportError as e:
        logger.error(f"Failed to import crawler: {e}")
        logger.error("Make sure all dependencies are installed: pip install crawl4ai tenacity ratelimit")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()