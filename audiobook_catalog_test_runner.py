"""
Comprehensive Test Runner for Audiobook Catalog Crawler
Runs full system test with whitelisted genres and generates detailed reports.
"""

import asyncio
import json
import csv
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import traceback

from audiobook_catalog_crawler import AudiobookCatalogCrawler
from crawl4ai import AsyncWebCrawler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audiobook_catalog_test.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AudiobookCatalogTestRunner:
    """Comprehensive test runner for audiobook catalog crawler."""

    def __init__(self, config_path: str = "audiobook_catalog_config.json"):
        """Initialize test runner with configuration."""
        self.config_path = Path(config_path)
        self.config = self._load_config()

        self.crawler = AudiobookCatalogCrawler()
        self.test_results = {
            'start_time': None,
            'end_time': None,
            'duration_seconds': 0,
            'total_genres_tested': 0,
            'successful_genres': 0,
            'failed_genres': 0,
            'total_audiobooks_found': 0,
            'genre_results': [],
            'errors': [],
            'validation_passed': False
        }

        # Setup output directory
        self.output_dir = Path(self.config['output_settings']['output_dir'])
        self.output_dir.mkdir(exist_ok=True)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"✅ Loaded configuration from {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            raise

    def _get_enabled_genres(self) -> List[Dict[str, Any]]:
        """Get list of enabled genres from whitelist."""
        enabled = [
            genre for genre in self.config['whitelisted_genres']
            if genre.get('enabled', True)
        ]
        logger.info(f"📋 Found {len(enabled)} enabled genres in whitelist")
        return enabled

    async def test_discovery(self) -> bool:
        """Test site discovery and filter extraction."""
        logger.info("\n" + "=" * 70)
        logger.info("🔍 PHASE 1: SITE DISCOVERY")
        logger.info("=" * 70)

        try:
            result = await self.crawler.discover_site_structure()

            if result.get('success'):
                filters = result.get('filters', {})
                genres = filters.get('genres', [])
                timespans = filters.get('timespans', [])

                logger.info(f"✅ Discovery successful")
                logger.info(f"   Genres found: {len(genres)}")
                logger.info(f"   Timespans found: {len(timespans)}")

                return True
            else:
                error = result.get('error', 'Unknown error')
                logger.error(f"❌ Discovery failed: {error}")
                self.test_results['errors'].append({
                    'phase': 'discovery',
                    'error': error
                })
                return False

        except Exception as e:
            logger.error(f"❌ Discovery exception: {e}")
            traceback.print_exc()
            self.test_results['errors'].append({
                'phase': 'discovery',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            return False

    async def test_genre_query(self, genre: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test querying a specific genre.

        Args:
            genre: Genre configuration dict

        Returns:
            Test result dictionary
        """
        genre_name = genre['name']
        genre_value = genre['value']
        timespan = self.config['timespan_preference']
        max_results = self.config['extraction_settings']['max_results_per_genre']

        logger.info(f"\n📚 Testing Genre: {genre_name}")
        logger.info(f"   Genre Value: {genre_value}")
        logger.info(f"   Timespan: {timespan['label']}")
        logger.info(f"   Max Results: {max_results}")

        result = {
            'genre_name': genre_name,
            'genre_value': genre_value,
            'timespan': timespan['label'],
            'success': False,
            'audiobooks': [],
            'audiobook_count': 0,
            'error': None,
            'screenshot_path': None
        }

        try:
            browser_config = self.crawler.create_browser_config()

            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Navigate to audiobooks
                nav_result = await self.crawler.navigate_to_audiobooks(crawler)

                if not nav_result.get('success'):
                    error = nav_result.get('error', 'Navigation failed')
                    logger.error(f"   ❌ Navigation failed: {error}")
                    result['error'] = error
                    return result

                logger.info(f"   ✅ Navigation successful")

                # Query with genre and timespan
                audiobooks = await self.crawler.query_audiobooks(
                    crawler,
                    genre_value,
                    timespan['value']
                )

                # Limit to top N results
                audiobooks = audiobooks[:max_results]

                result['success'] = True
                result['audiobooks'] = audiobooks
                result['audiobook_count'] = len(audiobooks)

                logger.info(f"   ✅ Query successful")
                logger.info(f"   📖 Found {len(audiobooks)} audiobooks (top {max_results})")

                # Display results
                for i, book in enumerate(audiobooks, 1):
                    title = book.get('title', 'Unknown')
                    author = book.get('author', '')
                    link = book.get('link', '')

                    logger.info(f"      {i}. {title}")
                    if author:
                        logger.info(f"         Author: {author}")
                    if link:
                        logger.info(f"         Link: {link[:50]}...")

                # Check for screenshot
                screenshot_filename = f"results_{genre_value}_{timespan['value']}.png"
                screenshot_path = self.crawler.cache_dir / screenshot_filename
                if screenshot_path.exists():
                    result['screenshot_path'] = str(screenshot_path)
                    logger.info(f"   📸 Screenshot saved: {screenshot_path}")

        except Exception as e:
            logger.error(f"   ❌ Query exception: {e}")
            traceback.print_exc()
            result['error'] = str(e)
            result['success'] = False

        return result

    async def run_all_tests(self):
        """Run complete test suite for all whitelisted genres."""
        logger.info("\n" + "=" * 70)
        logger.info("🚀 AUDIOBOOK CATALOG COMPREHENSIVE TEST SUITE")
        logger.info("=" * 70)
        logger.info(f"Configuration: {self.config_path}")
        logger.info(f"Output Directory: {self.output_dir}")
        logger.info("=" * 70)

        self.test_results['start_time'] = datetime.now().isoformat()

        # Phase 1: Discovery
        discovery_success = await self.test_discovery()

        if not discovery_success:
            logger.error("\n❌ Discovery phase failed. Aborting tests.")
            self.test_results['end_time'] = datetime.now().isoformat()
            self._calculate_duration()
            return False

        # Phase 2: Genre Testing
        logger.info("\n" + "=" * 70)
        logger.info("📚 PHASE 2: GENRE TESTING")
        logger.info("=" * 70)

        enabled_genres = self._get_enabled_genres()
        self.test_results['total_genres_tested'] = len(enabled_genres)

        for i, genre in enumerate(enabled_genres, 1):
            logger.info(f"\n[{i}/{len(enabled_genres)}] Testing genre: {genre['name']}")

            genre_result = await self.test_genre_query(genre)
            self.test_results['genre_results'].append(genre_result)

            if genre_result['success']:
                self.test_results['successful_genres'] += 1
                self.test_results['total_audiobooks_found'] += genre_result['audiobook_count']
            else:
                self.test_results['failed_genres'] += 1
                self.test_results['errors'].append({
                    'phase': 'genre_query',
                    'genre': genre['name'],
                    'error': genre_result['error']
                })

            # Wait between requests
            if i < len(enabled_genres):
                wait_time = self.config['crawler_settings']['wait_between_requests']
                logger.info(f"   ⏳ Waiting {wait_time} seconds before next genre...")
                await asyncio.sleep(wait_time)

        # Phase 3: Validation
        logger.info("\n" + "=" * 70)
        logger.info("✅ PHASE 3: VALIDATION")
        logger.info("=" * 70)

        self.test_results['validation_passed'] = self._validate_results()

        # Finalize
        self.test_results['end_time'] = datetime.now().isoformat()
        self._calculate_duration()

        # Generate reports
        await self._generate_reports()

        return self.test_results['validation_passed']

    def _calculate_duration(self):
        """Calculate test duration."""
        if self.test_results['start_time'] and self.test_results['end_time']:
            start = datetime.fromisoformat(self.test_results['start_time'])
            end = datetime.fromisoformat(self.test_results['end_time'])
            duration = (end - start).total_seconds()
            self.test_results['duration_seconds'] = duration
            logger.info(f"⏱️  Test Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")

    def _validate_results(self) -> bool:
        """Validate test results against requirements."""
        requirements = self.config['validation_requirements']

        passed = True
        issues = []

        # Check minimum results per genre
        min_results = requirements['min_results_per_genre']
        for genre_result in self.test_results['genre_results']:
            if genre_result['success'] and genre_result['audiobook_count'] < min_results:
                issues.append(
                    f"Genre '{genre_result['genre_name']}' returned only "
                    f"{genre_result['audiobook_count']} results (minimum: {min_results})"
                )
                passed = False

        # Check max failures allowed
        max_failures = requirements['max_failures_allowed']
        if self.test_results['failed_genres'] > max_failures:
            issues.append(
                f"Too many failed genres: {self.test_results['failed_genres']} "
                f"(max allowed: {max_failures})"
            )
            passed = False

        # Check if titles are present
        if requirements['require_titles']:
            for genre_result in self.test_results['genre_results']:
                for book in genre_result['audiobooks']:
                    if not book.get('title'):
                        issues.append(
                            f"Missing title in genre '{genre_result['genre_name']}'"
                        )
                        passed = False
                        break

        # Log validation results
        if passed:
            logger.info("✅ All validation checks passed!")
        else:
            logger.error("❌ Validation failed!")
            for issue in issues:
                logger.error(f"   - {issue}")

        return passed

    async def _generate_reports(self):
        """Generate comprehensive test reports."""
        logger.info("\n" + "=" * 70)
        logger.info("📊 GENERATING REPORTS")
        logger.info("=" * 70)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON Report
        if self.config['output_settings']['json_output']:
            json_path = self.output_dir / f"test_results_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ JSON report: {json_path}")

        # CSV Report
        if self.config['output_settings']['csv_output']:
            csv_path = self.output_dir / f"audiobooks_{timestamp}.csv"
            self._generate_csv_report(csv_path)
            logger.info(f"✅ CSV report: {csv_path}")

        # Markdown Report
        if self.config['output_settings']['markdown_report']:
            md_path = self.output_dir / f"test_report_{timestamp}.md"
            self._generate_markdown_report(md_path)
            logger.info(f"✅ Markdown report: {md_path}")

        logger.info("\n📁 All reports saved to: " + str(self.output_dir))

    def _generate_csv_report(self, csv_path: Path):
        """Generate CSV report of all audiobooks found."""
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Genre',
                'Rank',
                'Title',
                'Author',
                'Link',
                'Timespan'
            ])

            # Data
            for genre_result in self.test_results['genre_results']:
                genre_name = genre_result['genre_name']
                timespan = genre_result['timespan']

                for i, book in enumerate(genre_result['audiobooks'], 1):
                    writer.writerow([
                        genre_name,
                        i,
                        book.get('title', ''),
                        book.get('author', ''),
                        book.get('link', ''),
                        timespan
                    ])

    def _generate_markdown_report(self, md_path: Path):
        """Generate comprehensive markdown report."""
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("# Audiobook Catalog Test Report\n\n")

            # Summary
            f.write("## Executive Summary\n\n")
            f.write(f"- **Test Date**: {self.test_results['start_time']}\n")
            f.write(f"- **Duration**: {self.test_results['duration_seconds']:.2f} seconds\n")
            f.write(f"- **Validation Status**: {'✅ PASSED' if self.test_results['validation_passed'] else '❌ FAILED'}\n\n")

            # Statistics
            f.write("## Statistics\n\n")
            f.write(f"- **Total Genres Tested**: {self.test_results['total_genres_tested']}\n")
            f.write(f"- **Successful Queries**: {self.test_results['successful_genres']}\n")
            f.write(f"- **Failed Queries**: {self.test_results['failed_genres']}\n")
            f.write(f"- **Total Audiobooks Found**: {self.test_results['total_audiobooks_found']}\n\n")

            # Genre Results
            f.write("## Genre Results\n\n")
            for genre_result in self.test_results['genre_results']:
                status = "✅" if genre_result['success'] else "❌"
                f.write(f"### {status} {genre_result['genre_name']}\n\n")
                f.write(f"- **Timespan**: {genre_result['timespan']}\n")
                f.write(f"- **Audiobooks Found**: {genre_result['audiobook_count']}\n")

                if genre_result['error']:
                    f.write(f"- **Error**: {genre_result['error']}\n")

                if genre_result['screenshot_path']:
                    f.write(f"- **Screenshot**: [{genre_result['screenshot_path']}]({genre_result['screenshot_path']})\n")

                f.write("\n")

                # List audiobooks
                if genre_result['audiobooks']:
                    f.write("#### Top Audiobooks\n\n")
                    for i, book in enumerate(genre_result['audiobooks'], 1):
                        title = book.get('title', 'Unknown')
                        author = book.get('author', '')
                        link = book.get('link', '')

                        f.write(f"{i}. **{title}**\n")
                        if author:
                            f.write(f"   - Author: {author}\n")
                        if link:
                            f.write(f"   - [Download Link]({link})\n")
                        f.write("\n")

            # Errors
            if self.test_results['errors']:
                f.write("## Errors\n\n")
                for error in self.test_results['errors']:
                    f.write(f"- **Phase**: {error.get('phase', 'Unknown')}\n")
                    if 'genre' in error:
                        f.write(f"- **Genre**: {error['genre']}\n")
                    f.write(f"- **Error**: {error.get('error', 'Unknown')}\n")
                    f.write("\n")

    def print_summary(self):
        """Print test summary to console."""
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Validation Status: {'✅ PASSED' if self.test_results['validation_passed'] else '❌ FAILED'}")
        print(f"Duration: {self.test_results['duration_seconds']:.2f} seconds")
        print(f"Genres Tested: {self.test_results['total_genres_tested']}")
        print(f"Successful: {self.test_results['successful_genres']}")
        print(f"Failed: {self.test_results['failed_genres']}")
        print(f"Total Audiobooks: {self.test_results['total_audiobooks_found']}")
        print("=" * 70)


async def main():
    """Main entry point."""
    runner = AudiobookCatalogTestRunner()

    try:
        success = await runner.run_all_tests()
        runner.print_summary()

        if success:
            logger.info("\n🎉 All tests passed! Ready for Docker containerization.")
            return 0
        else:
            logger.error("\n❌ Some tests failed. Review the reports before containerization.")
            return 1

    except Exception as e:
        logger.error(f"\n💥 Critical error: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
