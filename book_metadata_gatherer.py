"""
Book Metadata Gatherer
Implements the specified process for gathering book metadata:
1. Google search as primary method with retry logic
2. Fallback to alternative search methods with retry cycles
3. Web scraping fallback when all searches fail
4. Direct scraping for all remaining books after first failure
"""

import asyncio
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs, quote_plus

import requests
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('book_metadata_gatherer.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BookMetadataGatherer:
    """Gathers book metadata following the specified process flow."""

    def __init__(self):
        # Search methods configuration
        self.search_methods = {
            'google': {
                'name': 'Google Books API',
                'url_template': 'https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5',
                'retry_attempts': 2,
                'retry_delay': 2
            },
            'open_library': {
                'name': 'Open Library API',
                'url_template': 'https://openlibrary.org/search.json?q={query}&limit=5',
                'retry_attempts': 2,
                'retry_delay': 1
            },
            'worldcat': {
                'name': 'WorldCat Search',
                'url_template': 'https://www.worldcat.org/search?q={query}&qt=results_page',
                'retry_attempts': 1,
                'retry_delay': 1
            }
        }

        # Scraping configuration
        self.scraping_enabled = False  # Will be set to True after first book fails all searches
        self.scraping_config = {
            'max_pages_per_book': 3,
            'timeout': 30000,
            'wait_for': 'css:body'
        }

        # Output configuration
        self.output_dir = Path("book_metadata_output")
        self.output_dir.mkdir(exist_ok=True)

        # State tracking
        self.books_processed = 0
        self.search_successes = 0
        self.scraping_successes = 0
        self.failures = 0

        # Browser configuration for scraping
        self.browser_config = BrowserConfig(
            headless=True,
            viewport_width=1920,
            viewport_height=1080,
            verbose=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=False,
            java_script_enabled=True
        )

    def create_search_query(self, title: str, author: str = "") -> str:
        """Create a search query from title and author."""
        if author:
            return f"{title} {author}"
        return title

    async def search_google_books(self, title: str, author: str = "") -> Optional[Dict[str, Any]]:
        """Search Google Books API for book metadata."""
        method_config = self.search_methods['google']
        query = self.create_search_query(title, author)
        encoded_query = quote_plus(query)

        url = method_config['url_template'].format(query=encoded_query)

        for attempt in range(method_config['retry_attempts']):
            try:
                logger.info(f"Google Books search attempt {attempt + 1} for: {query}")

                response = requests.get(url, timeout=10)
                response.raise_for_status()

                data = response.json()

                if data.get('items'):
                    # Extract metadata from first result
                    book_data = data['items'][0]['volumeInfo']

                    metadata = {
                        'title': book_data.get('title', ''),
                        'subtitle': book_data.get('subtitle', ''),
                        'authors': book_data.get('authors', []),
                        'publisher': book_data.get('publisher', ''),
                        'published_date': book_data.get('publishedDate', ''),
                        'description': book_data.get('description', ''),
                        'isbn_13': None,
                        'isbn_10': None,
                        'categories': book_data.get('categories', []),
                        'language': book_data.get('language', ''),
                        'page_count': book_data.get('pageCount'),
                        'average_rating': book_data.get('averageRating'),
                        'ratings_count': book_data.get('ratingsCount'),
                        'image_links': book_data.get('imageLinks', {}),
                        'source': 'google_books_api',
                        'search_query': query,
                        'retrieved_at': datetime.now().isoformat()
                    }

                    # Extract ISBNs
                    for identifier in book_data.get('industryIdentifiers', []):
                        if identifier.get('type') == 'ISBN_13':
                            metadata['isbn_13'] = identifier.get('identifier')
                        elif identifier.get('type') == 'ISBN_10':
                            metadata['isbn_10'] = identifier.get('identifier')

                    logger.info(f"✅ Google Books found metadata for: {title}")
                    return metadata

                logger.warning(f"No results from Google Books for: {query}")

            except Exception as e:
                logger.warning(f"Google Books attempt {attempt + 1} failed: {e}")

            if attempt < method_config['retry_attempts'] - 1:
                await asyncio.sleep(method_config['retry_delay'])

        return None

    async def search_open_library(self, title: str, author: str = "") -> Optional[Dict[str, Any]]:
        """Search Open Library API for book metadata."""
        method_config = self.search_methods['open_library']
        query = self.create_search_query(title, author)
        encoded_query = quote_plus(query)

        url = method_config['url_template'].format(query=encoded_query)

        for attempt in range(method_config['retry_attempts']):
            try:
                logger.info(f"Open Library search attempt {attempt + 1} for: {query}")

                response = requests.get(url, timeout=10)
                response.raise_for_status()

                data = response.json()

                if data.get('docs') and len(data['docs']) > 0:
                    # Get first result
                    book_data = data['docs'][0]

                    metadata = {
                        'title': book_data.get('title', ''),
                        'authors': book_data.get('author_name', []),
                        'first_publish_year': book_data.get('first_publish_year'),
                        'publisher': book_data.get('publisher', []),
                        'isbn': book_data.get('isbn', []),
                        'language': book_data.get('language', []),
                        'subject': book_data.get('subject', []),
                        'description': book_data.get('description', {}).get('value') if book_data.get('description') else None,
                        'cover_i': book_data.get('cover_i'),
                        'source': 'open_library_api',
                        'search_query': query,
                        'retrieved_at': datetime.now().isoformat()
                    }

                    logger.info(f"✅ Open Library found metadata for: {title}")
                    return metadata

                logger.warning(f"No results from Open Library for: {query}")

            except Exception as e:
                logger.warning(f"Open Library attempt {attempt + 1} failed: {e}")

            if attempt < method_config['retry_attempts'] - 1:
                await asyncio.sleep(method_config['retry_delay'])

        return None

    async def search_worldcat(self, title: str, author: str = "") -> Optional[Dict[str, Any]]:
        """Search WorldCat for book metadata (web scraping approach)."""
        method_config = self.search_methods['worldcat']
        query = self.create_search_query(title, author)
        encoded_query = quote_plus(query)

        url = method_config['url_template'].format(query=encoded_query)

        for attempt in range(method_config['retry_attempts']):
            try:
                logger.info(f"WorldCat search attempt {attempt + 1} for: {query}")

                response = requests.get(url, timeout=10)
                response.raise_for_status()

                # Simple HTML parsing for basic metadata
                html_content = response.text

                # Extract basic info from HTML (simplified)
                metadata = {
                    'source': 'worldcat_search',
                    'search_query': query,
                    'url': url,
                    'raw_html_length': len(html_content),
                    'retrieved_at': datetime.now().isoformat()
                }

                # Check if we got search results
                if 'search-results' in html_content or 'results' in html_content:
                    logger.info(f"✅ WorldCat found results for: {title}")
                    return metadata
                else:
                    logger.warning(f"No clear results from WorldCat for: {query}")

            except Exception as e:
                logger.warning(f"WorldCat attempt {attempt + 1} failed: {e}")

            if attempt < method_config['retry_attempts'] - 1:
                await asyncio.sleep(method_config['retry_delay'])

        return None

    async def scrape_book_metadata(self, title: str, author: str = "") -> Optional[Dict[str, Any]]:
        """Scrape book metadata from web sources using crawl4ai."""
        logger.info(f"🔍 Starting web scraping for: {title} by {author}")

        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            # Search queries for scraping
            search_queries = [
                f'"{title}" "{author}" book site:goodreads.com',
                f'"{title}" "{author}" book site:amazon.com',
                f'"{title}" "{author}" book site:barnesandnoble.com',
                f'"{title}" "{author}" book'
            ]

            for query in search_queries[:self.scraping_config['max_pages_per_book']]:
                try:
                    # Use Google search URL
                    search_url = f"https://www.google.com/search?q={quote_plus(query)}&num=10"

                    config = CrawlerRunConfig(
                        cache_mode=CacheMode.BYPASS,
                        wait_for=self.scraping_config['wait_for'],
                        page_timeout=self.scraping_config['timeout']
                    )

                    result = await crawler.arun(url=search_url, config=config)

                    if result.success and result.html:
                        # Extract metadata from search results
                        metadata = self.extract_metadata_from_search_html(result.html, title, author)
                        if metadata:
                            metadata.update({
                                'source': 'web_scraping',
                                'search_query': query,
                                'scraped_at': datetime.now().isoformat()
                            })
                            logger.info(f"✅ Web scraping found metadata for: {title}")
                            return metadata

                    # Add delay between searches
                    await asyncio.sleep(random.uniform(2, 5))

                except Exception as e:
                    logger.warning(f"Scraping failed for query '{query}': {e}")
                    continue

        logger.warning(f"❌ Web scraping failed for: {title}")
        return None

    def extract_metadata_from_search_html(self, html: str, title: str, author: str) -> Optional[Dict[str, Any]]:
        """Extract book metadata from Google search HTML results."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')

            # Look for book-related search results
            results = soup.find_all(['div', 'h3'], class_=lambda x: x and any(term in ' '.join(x) for term in ['result', 'g', 'rc']))

            metadata = {
                'title': title,
                'author': author,
                'search_results_found': len(results),
                'potential_sources': []
            }

            # Extract URLs from results
            for result in results[:5]:  # Check first 5 results
                link = result.find('a', href=True)
                if link:
                    url = link.get('href', '')
                    if url.startswith('/url?q='):
                        # Extract actual URL from Google redirect
                        parsed = urlparse(url)
                        actual_url = parse_qs(parsed.query).get('q', [url])[0]
                        if any(domain in actual_url for domain in ['goodreads.com', 'amazon.com', 'barnesandnoble.com', 'bookdepository.com']):
                            metadata['potential_sources'].append(actual_url)

            if metadata['potential_sources']:
                return metadata

        except Exception as e:
            logger.warning(f"Failed to extract metadata from HTML: {e}")

        return None

    async def gather_book_metadata(self, title: str, author: str = "", book_index: int = 0) -> Optional[Dict[str, Any]]:
        """Gather metadata for a single book following the specified process."""
        logger.info(f"\n{'='*70}")
        logger.info(f"📖 Processing book {book_index + 1}: '{title}' by {author}")
        logger.info(f"{'='*70}")

        # If scraping mode is enabled (after first book failed), skip directly to scraping
        if self.scraping_enabled:
            logger.info("🔄 Scraping mode active - skipping searches")
            metadata = await self.scrape_book_metadata(title, author)
            if metadata:
                self.scraping_successes += 1
                return metadata
            else:
                self.failures += 1
                return None

        # Phase 1: Try search methods for first book (or until all methods exhausted)
        search_methods = [
            ('google', self.search_google_books),
            ('open_library', self.search_open_library),
            ('worldcat', self.search_worldcat)
        ]

        for method_name, search_func in search_methods:
            logger.info(f"🔍 Trying {method_name} search...")
            metadata = await search_func(title, author)
            if metadata:
                self.search_successes += 1
                return metadata

        # All search methods failed
        logger.warning(f"❌ All search methods failed for first book: {title}")

        # Phase 2: Enable scraping mode and try scraping for this book
        logger.info("🔄 Enabling scraping mode for remaining books")
        self.scraping_enabled = True

        metadata = await self.scrape_book_metadata(title, author)
        if metadata:
            self.scraping_successes += 1
            return metadata
        else:
            self.failures += 1
            return None

    async def process_books_list(self, books: List[Tuple[str, str]]) -> Dict[str, Any]:
        """Process a list of books following the specified flow."""
        logger.info(f"🚀 Starting metadata gathering for {len(books)} books")
        logger.info("Process: Google search → Fallback searches → Web scraping")

        results = []
        start_time = datetime.now()

        for i, (title, author) in enumerate(books):
            try:
                metadata = await self.gather_book_metadata(title, author, i)
                if metadata:
                    metadata['book_index'] = i + 1
                    metadata['original_title'] = title
                    metadata['original_author'] = author
                    results.append(metadata)
                    logger.info(f"✅ Book {i + 1} completed successfully")
                else:
                    logger.error(f"❌ Book {i + 1} failed: {title}")
                    results.append({
                        'book_index': i + 1,
                        'original_title': title,
                        'original_author': author,
                        'status': 'failed',
                        'error': 'All methods exhausted'
                    })

                self.books_processed += 1

                # Add delay between books to be respectful
                if i < len(books) - 1:
                    delay = random.uniform(1, 3)
                    logger.info(f"⏱️  Waiting {delay:.1f} seconds before next book...")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"❌ Unexpected error processing book {i + 1}: {e}")
                results.append({
                    'book_index': i + 1,
                    'original_title': title,
                    'original_author': author,
                    'status': 'error',
                    'error': str(e)
                })

        # Save results
        await self.save_results(results, start_time)

        # Generate summary
        summary = self.generate_summary(results, start_time)

        logger.info(f"\n{'='*70}")
        logger.info("🎯 METADATA GATHERING COMPLETE")
        logger.info(f"{'='*70}")
        logger.info(f"Books processed: {self.books_processed}")
        logger.info(f"Search successes: {self.search_successes}")
        logger.info(f"Scraping successes: {self.scraping_successes}")
        logger.info(f"Total successes: {self.search_successes + self.scraping_successes}")
        logger.info(f"Failures: {self.failures}")
        logger.info(f"Output saved to: {self.output_dir}")

        return summary

    async def save_results(self, results: List[Dict[str, Any]], start_time: datetime):
        """Save results to JSON file."""
        timestamp = start_time.strftime('%Y%m%d_%H%M%S')
        filename = f"book_metadata_results_{timestamp}.json"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Results saved to: {filepath}")

    def generate_summary(self, results: List[Dict[str, Any]], start_time: datetime) -> Dict[str, Any]:
        """Generate processing summary."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        successful_results = [r for r in results if r.get('status') != 'failed' and 'error' not in r]
        failed_results = [r for r in results if r.get('status') == 'failed' or 'error' in r]

        summary = {
            'total_books': len(results),
            'successful': len(successful_results),
            'failed': len(failed_results),
            'search_successes': self.search_successes,
            'scraping_successes': self.scraping_successes,
            'scraping_mode_activated': self.scraping_enabled,
            'duration_seconds': duration,
            'average_time_per_book': duration / len(results) if results else 0,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'sources_used': list(set(r.get('source', 'unknown') for r in successful_results))
        }

        # Save summary
        summary_file = self.output_dir / f"metadata_gathering_summary_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"📊 Summary saved to: {summary_file}")

        return summary


async def main():
    """Main entry point."""
    # Load books from Audiobookshelf library
    try:
        import requests
        import os

        # Get Audiobookshelf configuration
        abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        abs_token = os.getenv('ABS_TOKEN')

        if not abs_token:
            logger.error("AUDIOBOOKSHELF_TOKEN not found in environment variables")
            return

        # Fetch library items
        headers = {'Authorization': f'Bearer {abs_token}'}
        response = requests.get(f'{abs_url}/api/libraries', headers=headers)

        if response.status_code != 200:
            logger.error(f"Failed to fetch libraries: {response.status_code}")
            return

        libraries = response.json()
        if not libraries:
            logger.error("No libraries found")
            return

        # Get first library's items
        library_id = libraries[0]['id']
        items_response = requests.get(f'{abs_url}/api/libraries/{library_id}/items', headers=headers)

        if items_response.status_code != 200:
            logger.error(f"Failed to fetch library items: {items_response.status_code}")
            return

        items = items_response.json()['results']

        # Extract book titles and authors
        books = []
        for item in items:
            media = item.get('media', {})
            metadata = media.get('metadata', {})

            title = metadata.get('title', '').strip()
            author = metadata.get('authorName', '').strip()

            if title and author:
                books.append((title, author))

        logger.info(f"Loaded {len(books)} books from Audiobookshelf library")

        if not books:
            logger.error("No books found in library")
            return

    except Exception as e:
        logger.error(f"Failed to load books from Audiobookshelf: {e}")
        # Fallback to example books
        books = [
            ("The Name of the Wind", "Patrick Rothfuss"),
            ("The Wise Man's Fear", "Patrick Rothfuss"),
            ("The Way of Kings", "Brandon Sanderson"),
            ("Mistborn: The Final Empire", "Brandon Sanderson"),
            ("Dune", "Frank Herbert"),
            ("Neuromancer", "William Gibson"),
            ("Snow Crash", "Neal Stephenson"),
            ("The Left Hand of Darkness", "Ursula K. Le Guin"),
            ("The Dispossessed", "Ursula K. Le Guin"),
            ("Hyperion", "Dan Simmons")
        ]
        logger.info(f"Using fallback example books: {len(books)}")

    gatherer = BookMetadataGatherer()
    summary = await gatherer.process_books_list(books)

    print("\n" + "="*50)
    print("PROCESS SUMMARY")
    print("="*50)
    print(f"Total books: {summary['total_books']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Search successes: {summary['search_successes']}")
    print(f"Scraping successes: {summary['scraping_successes']}")
    print(f"Scraping mode activated: {summary['scraping_mode_activated']}")
    print(".1f")
    print(".1f")
    print(f"Sources used: {', '.join(summary['sources_used'])}")


if __name__ == "__main__":
    asyncio.run(main())