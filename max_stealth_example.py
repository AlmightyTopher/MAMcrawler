#!/usr/bin/env python3
"""
Max Stealth Crawler Example Usage
==================================

This script demonstrates how to use the MaxStealthCrawler for scraping
MyAnonamouse with maximum stealth and anti-detection capabilities.

Usage:
    python max_stealth_example.py

Requirements:
    - Python 3.8+
    - Playwright and stealth plugins
    - Valid MAM credentials in .env file
"""

import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from max_stealth_crawler import MaxStealthCrawler


async def basic_mam_crawl():
    """Basic example of crawling MAM with stealth techniques."""

    print("🚀 Starting Max Stealth MAM Crawler Example")
    print("=" * 50)

    # Configuration
    target_url = "https://www.myanonamouse.net"
    credentials = {
        'username': os.getenv('MAM_USERNAME'),
        'password': os.getenv('MAM_PASSWORD')
    }

    if not credentials['username'] or not credentials['password']:
        print("❌ Error: MAM_USERNAME and MAM_PASSWORD must be set in .env file")
        return

    # URLs to crawl
    urls_to_crawl = [
        f"{target_url}/torrents.php",  # Main torrents page
        f"{target_url}/browse.php?cat=13",  # Audiobooks category
        f"{target_url}/browse.php?cat=14",  # Music category
    ]

    # Data extraction selectors
    selectors = {
        'torrent_titles': 'a[href*="torrent"]',
        'categories': '.category, .cat',
        'file_sizes': '.size, [class*="size"]',
        'seeders': '.seeders, [class*="seed"]',
        'leechers': '.leechers, [class*="leech"]',
        'upload_dates': '.added, .date, [class*="date"]'
    }

    # Initialize crawler
    crawler = MaxStealthCrawler(target_url, credentials)

    try:
        # Run the stealth crawl
        print("🔧 Initializing stealth crawler...")
        results = await crawler.crawl_with_stealth(urls_to_crawl, selectors)

        # Process and display results
        print(f"\n✅ Crawl completed! Processed {len(results)} pages")
        print("-" * 50)

        for i, result in enumerate(results, 1):
            print(f"\n📄 Page {i}: {result['url']}")
            print(f"   Timestamp: {result['timestamp']}")
            print(f"   Data fields extracted: {len(result.get('data', {}))}")

            # Show sample data
            data = result.get('data', {})
            if data.get('torrent_titles'):
                titles = data['torrent_titles'][:3]  # Show first 3
                print(f"   Sample titles: {titles}")

        # Save results to file
        output_file = f"max_stealth_results_{int(asyncio.get_event_loop().time())}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 Results saved to: {output_file}")

    except KeyboardInterrupt:
        print("\n⚠️  Crawl interrupted by user")
    except Exception as e:
        print(f"\n❌ Crawl failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await crawler.cleanup()
        print("🧹 Cleanup completed")


async def advanced_stealth_example():
    """Advanced example with custom configuration and monitoring."""

    print("🔥 Advanced Max Stealth Crawler Example")
    print("=" * 50)

    target_url = "https://www.myanonamouse.net"
    credentials = {
        'username': os.getenv('MAM_USERNAME'),
        'password': os.getenv('MAM_PASSWORD')
    }

    # Create crawler
    crawler = MaxStealthCrawler(target_url, credentials)

    # Custom configuration for maximum stealth
    crawler.config.headless = False  # Use visible browser for better stealth
    crawler.config.browser_type = "chromium"

    # Conservative rate limiting
    crawler.config.rate_limit_config.update({
        'requests_per_minute': 5,
        'burst_limit': 2,
        'backoff_base': 10
    })

    # Enhanced behavioral simulation
    crawler.config.behavior_config.update({
        'page_read_time_min': 5000,
        'page_read_time_max': 12000,
        'scroll_pause_min': 800,
        'scroll_pause_max': 3000
    })

    # Enable detailed monitoring
    crawler.config.monitoring_config.update({
        'detailed_logging': True,
        'screenshot_on_failure': True,
        'performance_metrics': True,
        'anomaly_detection': True
    })

    # Single page crawl for demonstration
    urls = [f"{target_url}/torrents.php"]
    selectors = {
        'torrents': 'tr.torrent',
        'titles': 'a[href*="torrent"]',
        'stats': '.seeders, .leechers, .size'
    }

    try:
        print("🎯 Starting advanced stealth crawl...")
        results = await crawler.crawl_with_stealth(urls, selectors)

        if results:
            result = results[0]
            print("
📊 Advanced Crawl Results:"            print(f"   URL: {result['url']}")
            print(f"   Session ID: {result['session_id']}")
            print(f"   Data extracted: {len(result.get('data', {}))} fields")

            # Show monitoring stats
            if hasattr(crawler, 'monitoring_data'):
                monitoring = crawler.monitoring_data
                print("
📈 Session Monitoring:"                print(f"   Total requests: {monitoring.get('requests', [])}")
                print(f"   CAPTCHAs encountered: {monitoring.get('captchas_encountered', 0)}")
                print(f"   Proxies used: {list(monitoring.get('proxies_used', set()))}")

    except Exception as e:
        print(f"❌ Advanced crawl failed: {e}")
    finally:
        await crawler.cleanup()


async def api_endpoint_discovery_example():
    """Example of discovering and scraping API endpoints instead of HTML."""

    print("🔍 API Endpoint Discovery Example")
    print("=" * 50)

    target_url = "https://www.myanonamouse.net"
    credentials = {
        'username': os.getenv('MAM_USERNAME'),
        'password': os.getenv('MAM_PASSWORD')
    }

    crawler = MaxStealthCrawler(target_url, credentials)

    # Custom request interception to capture API calls
    api_calls = []

    async def capture_api_calls(route, request):
        """Capture API calls for analysis."""
        if any(endpoint in request.url for endpoint in ['api', 'graphql', 'ajax', 'json']):
            api_calls.append({
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'timestamp': asyncio.get_event_loop().time()
            })
            print(f"📡 Captured API call: {request.url}")

        await route.continue_()

    try:
        await crawler.initialize()
        await crawler.authenticate()

        # Set up API capture
        crawler.page.route("**/*", capture_api_calls)

        # Navigate and interact to trigger API calls
        await crawler.page.goto(f"{target_url}/torrents.php")
        await crawler.behavior_simulator.simulate_scrolling(crawler.page)
        await asyncio.sleep(5)  # Wait for dynamic content

        # Search to trigger more API calls
        await crawler.page.fill('input[name="search"]', 'audiobook')
        await crawler.page.press('input[name="search"]', 'Enter')
        await asyncio.sleep(3)

        print(f"\n🔍 Discovered {len(api_calls)} API endpoints:")
        for call in api_calls[:5]:  # Show first 5
            print(f"   {call['method']} {call['url']}")

        # Save API discovery results
        api_file = f"api_discovery_{int(asyncio.get_event_loop().time())}.json"
        with open(api_file, 'w') as f:
            json.dump(api_calls, f, indent=2)

        print(f"💾 API discovery saved to: {api_file}")

    except Exception as e:
        print(f"❌ API discovery failed: {e}")
    finally:
        await crawler.cleanup()


async def main():
    """Main function to run examples."""

    print("Max Stealth Crawler - Example Runner")
    print("====================================")
    print("Choose an example to run:")
    print("1. Basic MAM crawl")
    print("2. Advanced stealth configuration")
    print("3. API endpoint discovery")
    print("4. Run all examples")

    choice = input("\nEnter choice (1-4): ").strip()

    if choice == '1':
        await basic_mam_crawl()
    elif choice == '2':
        await advanced_stealth_example()
    elif choice == '3':
        await api_endpoint_discovery_example()
    elif choice == '4':
        print("Running all examples...")
        await basic_mam_crawl()
        print("\n" + "="*50)
        await advanced_stealth_example()
        print("\n" + "="*50)
        await api_endpoint_discovery_example()
    else:
        print("Invalid choice. Running basic example...")
        await basic_mam_crawl()


if __name__ == "__main__":
    asyncio.run(main())