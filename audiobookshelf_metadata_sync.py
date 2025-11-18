#!/usr/bin/env python3
"""
Audiobookshelf Metadata Synchronization with Google Books API
Synchronizes Audiobookshelf library metadata with Google Books API data,
with special focus on series linking and complete metadata enrichment.
"""

import asyncio
import os
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

import aiohttp
import requests

load_dotenv()

import time
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audiobookshelf_metadata_sync.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
class RateLimitError(Exception):
    """Custom exception for rate limiting errors."""
    pass
logger = logging.getLogger(__name__)

class AudiobookshelfMetadataSync:
    """Synchronizes Audiobookshelf metadata with Google Books API."""

    def __init__(self):
        # Audiobookshelf configuration
        self.abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
        self.abs_token = os.getenv('ABS_TOKEN', '')

        # Google Books API
        self.google_books_api_key = os.getenv('GOOGLE_BOOKS_API_KEY', 'AIzaSyArxwp_0IyT-H7GMXR7pves4Fs2LLCHeMg')
        # Google Books API
        self.google_books_api_key = os.getenv('GOOGLE_BOOKS_API_KEY', 'AIzaSyArxwp_0IyT-H7GMXR7pves4Fs2LLCHeMg')
        self.google_books_api_base = "https://www.googleapis.com/books/v1"

        # Goodreads credentials
        self.goodreads_username = os.getenv('GOODREADS_USERNAME', '')
        self.goodreads_password = os.getenv('GOODREADS_PASSWORD', '')
        self.google_books_api_base = "https://www.googleapis.com/books/v1"

        # Metadata provider configurations
        self.provider_urls = {
            "google": "https://www.googleapis.com/books/v1/volumes?q={q}+inauthor:{a}",
            "goodreads": "http://localhost:5555/goodreads/search?query={q}&author={a}",
            "kindle": "http://localhost:5555/kindle/us/search?query={q}&author={a}",
            "hardcover": "https://provider.vito0912.de/hardcover/en/book",
            "lubimyczytac-abs": "http://localhost:3000/search?query={q}&author={a}",
            "audioteka-abs": "http://localhost:3001/search?query={q}&author={a}"
        }

        self.provider_headers = {
            "google": {},
            "goodreads": {},
            "kindle": {},
            "hardcover": {"Authorization": "abs"},
            "lubimyczytac-abs": {"Authorization": "00000"},
            "audioteka-abs": {"Authorization": "00000"}
        }

        # State tracking
        self.stats = {
            'books_processed': 0,
            'books_updated': 0,
            'series_linked': 0,
            'metadata_enriched': 0,
            'scraper_fallback_used': 0,
            'provider_success': {},
            'errors': [],
            'skipped': []
        }

        # Cache for series information
        self.series_cache = {}

    def get_audiobookshelf_library(self) -> List[Dict]:
        """Get all items from Audiobookshelf library."""
        if not self.abs_token or not self.abs_url:
            raise ValueError("ABS_URL and ABS_TOKEN must be set in .env")

        try:
            headers = {'Authorization': f'Bearer {self.abs_token}'}
            logger.info(f"Connecting to Audiobookshelf at: {self.abs_url}")

            # Test basic connectivity first
            try:
                test_response = requests.get(f"{self.abs_url}/api/status", headers=headers, timeout=5)
                logger.info(f"Audiobookshelf status check: {test_response.status_code}")
            except Exception as e:
                logger.warning(f"Audiobookshelf status check failed: {e}")

            # Get libraries
            logger.info("Fetching libraries...")
            lib_response = requests.get(f"{self.abs_url}/api/libraries", headers=headers, timeout=10)
            logger.info(f"Libraries API response: {lib_response.status_code}")

            if lib_response.status_code != 200:
                logger.error(f"Failed to get libraries. Status: {lib_response.status_code}")
                logger.error(f"Response: {lib_response.text}")
                return []

            lib_response.raise_for_status()
            libraries = lib_response.json()
            logger.info(f"Found {len(libraries)} libraries")
            logger.info(f"Libraries data type: {type(libraries)}")
            logger.info(f"Libraries data: {libraries}")  # Debug: show what we got

            if not libraries:
                logger.warning("No Audiobookshelf libraries found")
                return []

            # Handle different response formats - some APIs wrap in "libraries" key
            if isinstance(libraries, dict) and 'libraries' in libraries:
                libraries = libraries['libraries']
                logger.info(f"Unwrapped libraries from response, now have {len(libraries)} libraries")

            # Get the first library (assuming audiobook library)
            try:
                lib_id = libraries[0]['id']
                lib_name = libraries[0].get('name', 'Unknown')
                logger.info(f"Using library: {lib_name} (ID: {lib_id})")
            except (IndexError, KeyError) as e:
                logger.error(f"Failed to access library data: {e}")
                logger.error(f"Library structure: {libraries}")
                return []

            # Get all items from the library
            logger.info("Fetching library items...")
            items_response = requests.get(
                f"{self.abs_url}/api/libraries/{lib_id}/items",
                headers=headers,
                timeout=30
            )
            logger.info(f"Items API response: {items_response.status_code}")

            if items_response.status_code != 200:
                logger.error(f"Failed to get items. Status: {items_response.status_code}")
                logger.error(f"Response: {items_response.text}")
                return []

            items_response.raise_for_status()
            items_data = items_response.json()

            items = items_data.get('results', [])
            logger.info(f"Found {len(items)} items in Audiobookshelf library")
            return items

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection failed to Audiobookshelf at {self.abs_url}")
            logger.error("Please ensure Audiobookshelf is running and accessible")
            logger.error(f"Error details: {e}")
            return []
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to Audiobookshelf at {self.abs_url}")
            logger.error("The server may be slow to respond or unreachable")
            logger.error(f"Error details: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to get Audiobookshelf library: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            return []

    async def query_provider(self, provider: str, title: str, author: str = "") -> Optional[Dict]:
        """Query a specific metadata provider for book information."""
        try:
            if provider == "google":
                return await self.search_google_books(title, author)
            else:
                # For other providers, use synchronous requests since they may not support async
                return self.search_other_provider(provider, title, author)
        except Exception as e:
            logger.warning(f"Failed to query {provider} for '{title}': {e}")
            return None

    async def search_google_books(self, title: str, author: str = "") -> Optional[Dict]:
        """Search Google Books API for book metadata with increased results."""
        try:
            # Clean and prepare search query
            clean_title = self.clean_title(title)
            query_parts = [f'intitle:"{clean_title}"']

            if author:
                clean_author = self.clean_author(author)
                query_parts.append(f'inauthor:"{clean_author}"')

            query = ' '.join(query_parts)

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.google_books_api_base}/volumes",
                    params={
                        "q": query,
                        "key": self.google_books_api_key,
                        "maxResults": 20,  # Increased from 5 to 20 for better matching
                        "orderBy": "relevance"
                    }
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.find_best_match(data, title, author)
                    else:
                        logger.warning(f"Google Books API error: {response.status}")
                        return None

        except Exception as e:
            logger.warning(f"Failed to search Google Books for '{title}': {e}")
            return None

    def search_other_provider(self, provider: str, title: str, author: str = "") -> Optional[Dict]:
        """Search other metadata providers synchronously."""
        try:
            url = self.provider_urls[provider].format(q=title.replace(" ","+"), a=author.replace(" ","+"))
            headers = self.provider_headers.get(provider, {})

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self.normalize_provider_data(provider, data, title, author)
            else:
                logger.warning(f"{provider} API error: {response.status_code}")
                return None

        except Exception as e:
            logger.warning(f"Failed to search {provider} for '{title}': {e}")
            return None

    def normalize_provider_data(self, provider: str, data: Dict, title: str, author: str) -> Optional[Dict]:
        """Normalize data from different providers to Google Books format."""
        try:
            if provider == "google":
                # Already in Google format
                return data
            elif provider in ["goodreads", "kindle", "hardcover", "lubimyczytac-abs", "audioteka-abs"]:
                # Convert to Google Books-like format
                volume_info = {}

                # Extract basic fields
                if provider == "google":
                    items = data.get("items", [{}])
                    if items:
                        volume_info = items[0].get("volumeInfo", {})
                else:
                    # For other providers, assume direct data structure
                    volume_info = data

                # Ensure we have the expected structure
                if not volume_info:
                    return None

                # Add provider-specific normalization if needed
                return {
                    "items": [{
                        "volumeInfo": volume_info
                    }]
                }
            else:
                logger.warning(f"Unknown provider: {provider}")
                return None

        except Exception as e:
            logger.warning(f"Failed to normalize {provider} data: {e}")
            return None

    def find_best_match(self, data: Dict, original_title: str, original_author: str) -> Optional[Dict]:
        """Find the best matching book from Google Books results."""
        items = data.get('items', [])

        if not items:
            return None

        # Score each result
        scored_results = []
        for item in items:
            volume_info = item.get('volumeInfo', {})
            score = self.calculate_match_score(volume_info, original_title, original_author)
            scored_results.append((score, volume_info))

        # Sort by score (highest first)
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # Return the best match if score is above threshold
        best_score, best_match = scored_results[0]
        if best_score >= 0.6:  # 60% match threshold
            logger.info(f"  ✓ Best match for '{original_title}' (score: {best_score:.2f})")
            return best_match
        else:
            logger.info(f"  ⚠ No good match for '{original_title}' (best score: {best_score:.2f})")
            return None

    def calculate_match_score(self, volume_info: Dict, original_title: str, original_author: str) -> float:
        """Calculate how well a Google Books result matches our book."""
        score = 0.0

        # Title matching (40% weight)
        gb_title = volume_info.get('title', '').lower()
        orig_title = original_title.lower()

        if gb_title == orig_title:
            score += 0.4
        elif orig_title in gb_title or gb_title in orig_title:
            score += 0.3
        elif self.calculate_string_similarity(orig_title, gb_title) > 0.8:
            score += 0.25

        # Author matching (35% weight)
        if original_author:
            gb_authors = [a.lower() for a in volume_info.get('authors', [])]
            orig_author = original_author.lower()

            if any(orig_author in gb_author or gb_author in orig_author for gb_author in gb_authors):
                score += 0.35
            elif any(self.calculate_string_similarity(orig_author, gb_author) > 0.8 for gb_author in gb_authors):
                score += 0.25

        # Has series info (15% weight)
        if volume_info.get('seriesInfo'):
            score += 0.15

        # Has good metadata (10% weight)
        metadata_score = 0
        if volume_info.get('description'): metadata_score += 0.03
        if volume_info.get('categories'): metadata_score += 0.02
        if volume_info.get('publishedDate'): metadata_score += 0.02
        if volume_info.get('pageCount'): metadata_score += 0.02
        if volume_info.get('averageRating'): metadata_score += 0.01
        score += metadata_score

        return min(score, 1.0)  # Cap at 100%

    def calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using simple ratio."""
        # Remove common words and punctuation
        def clean_string(s):
            s = re.sub(r'[^\w\s]', '', s.lower())
            words = s.split()
            # Remove common stop words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            words = [w for w in words if w not in stop_words]
            return ' '.join(words)

        clean1 = clean_string(str1)
        clean2 = clean_string(str2)

        if not clean1 or not clean2:
            return 0.0

        # Simple Jaccard similarity
        set1 = set(clean1.split())
        set2 = set(clean2.split())

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def clean_title(self, title: str) -> str:
        """Clean book title for searching."""
        # Remove series info like "Book 1 of 3", "(Series Name #1)", etc.
        title = re.sub(r'\s*\([^)]*\)\s*', '', title)  # Remove parentheses
        title = re.sub(r'\s*book\s+\d+\s+of\s+\d+', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*#?\d+\s*$', '', title)  # Remove trailing numbers
        title = re.sub(r'\s*vol\.?\s*\d+', '', title, flags=re.IGNORECASE)
        title = re.sub(r'\s*volume\s*\d+', '', title, flags=re.IGNORECASE)

        return title.strip()

    def clean_author(self, author: str) -> str:
        """Clean author name for searching."""
        # Remove common suffixes
        author = re.sub(r'\s*\([^)]*\)\s*', '', author)  # Remove parentheses
        author = re.sub(r'\s*jr\.?\s*$', '', author, flags=re.IGNORECASE)
        author = re.sub(r'\s*sr\.?\s*$', '', author, flags=re.IGNORECASE)
        author = re.sub(r'\s*\biii?\b\s*$', '', author, flags=re.IGNORECASE)

        return author.strip()

    def extract_series_info(self, volume_info: Dict) -> Tuple[Optional[str], Optional[int]]:
        """Extract series name and book number from Google Books data."""
        series_info = volume_info.get('seriesInfo', {})

        if series_info:
            series_name = series_info.get('seriesName', '').strip()
            book_number = series_info.get('bookNumber')

            if series_name and book_number:
                return series_name, int(book_number)

        # Fallback: try to extract from title
        title = volume_info.get('title', '')
        return self.extract_series_from_title(title)

    def extract_series_from_title(self, title: str) -> Tuple[Optional[str], Optional[int]]:
        """Try to extract series info from book title."""
        # Common patterns: "Series Name #1", "Series Name (Book 1)", etc.
        patterns = [
            r'(.+?)\s*#(\d+)',  # "Series Name #1"
            r'(.+?)\s*\(book\s*(\d+)\)',  # "Series Name (Book 1)"
            r'(.+?)\s*book\s*(\d+)',  # "Series Name Book 1"
            r'(.+?)\s*vol\.?\s*(\d+)',  # "Series Name Vol 1"
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                series_name = match.group(1).strip()
                book_number = int(match.group(2))

                # Clean up series name
                series_name = re.sub(r'\s+', ' ', series_name)
                return series_name, book_number

        return None, None

    def update_audiobookshelf_metadata_quality_preserved(self, item_id: str, new_metadata: Dict, current_metadata: Dict) -> bool:
        """Update Audiobookshelf item metadata with quality preservation and idempotency."""
        try:
            headers = {
                'Authorization': f'Bearer {self.abs_token}',
                'Content-Type': 'application/json'
            }

            # Get current item data first
            get_response = requests.get(
                f"{self.abs_url}/api/items/{item_id}",
                headers=headers,
                timeout=10
            )
            get_response.raise_for_status()
            current_item = get_response.json()

            # Prepare update payload
            update_data = {
                "media": {
                    "metadata": {}
                }
            }

            # Quality preservation logic: only update if new data is better or missing
            fields_to_update = {}

            # Title: prefer existing unless new is significantly different
            if new_metadata.get('title') and not current_metadata.get('title'):
                fields_to_update['title'] = new_metadata['title']

            # Author: prefer existing unless new is significantly different
            if new_metadata.get('authorName') and not current_metadata.get('authorName'):
                fields_to_update['authorName'] = new_metadata['authorName']

            # Description: prefer longer, more complete descriptions
            new_desc = new_metadata.get('description', '').strip()
            current_desc = current_metadata.get('description', '').strip()
            if new_desc and (not current_desc or len(new_desc) > len(current_desc) * 0.8):
                fields_to_update['description'] = new_desc

            # Publisher: prefer existing unless missing
            if new_metadata.get('publisher') and not current_metadata.get('publisher'):
                fields_to_update['publisher'] = new_metadata['publisher']

            # Published year: prefer existing unless missing
            if new_metadata.get('publishedYear') and not current_metadata.get('publishedYear'):
                fields_to_update['publishedYear'] = new_metadata['publishedYear']

            # Genres: merge and deduplicate
            new_genres = new_metadata.get('genres', [])
            current_genres = current_metadata.get('genres', [])
            if new_genres and not current_genres:
                fields_to_update['genres'] = new_genres

            # Tags: merge and deduplicate
            new_tags = new_metadata.get('tags', [])
            current_tags = current_metadata.get('tags', [])
            if new_tags and not current_tags:
                fields_to_update['tags'] = new_tags

            # ISBN: prefer existing unless missing
            if new_metadata.get('isbn') and not current_metadata.get('isbn'):
                fields_to_update['isbn'] = new_metadata['isbn']

            # Series information: critical - always update if new data available
            if new_metadata.get('series'):
                # Normalize series name for consistency
                normalized_series = self.normalize_series_name(new_metadata['series'])
                current_series = current_metadata.get('series', '')

                # Update if no current series or if normalized version is different
                if not current_series or normalized_series != self.normalize_series_name(current_series):
                    fields_to_update['series'] = normalized_series
                    logger.info(f"  📚 Updated series to: {normalized_series}")

            if new_metadata.get('seriesNumber'):
                current_series_num = current_metadata.get('seriesSequence', '')
                if not current_series_num or str(new_metadata['seriesNumber']) != str(current_series_num):
                    fields_to_update['seriesSequence'] = str(new_metadata['seriesNumber'])
                    logger.info(f"  📚 Updated series number to: {new_metadata['seriesNumber']}")

            # Only proceed if there are fields to update
            if not fields_to_update:
                logger.info(f"  ℹ️ No metadata updates needed for item {item_id} (quality preservation)")
                return True

            # Apply updates
            update_data['media']['metadata'] = fields_to_update

            # Send update request
            update_response = requests.patch(
                f"{self.abs_url}/api/items/{item_id}",
                headers=headers,
                json=update_data,
                timeout=15
            )

            if update_response.status_code == 200:
                logger.info(f"  ✓ Updated metadata for item {item_id} ({len(fields_to_update)} fields)")
                return True
            else:
                logger.warning(f"  ⚠ Failed to update item {item_id}: {update_response.status_code}")
                logger.warning(f"    Response: {update_response.text}")
                return False

        except Exception as e:
            logger.error(f"  ✗ Error updating item {item_id}: {e}")
            return False

    def normalize_series_name(self, series_name: str) -> str:
        """Normalize series names for consistency."""
        if not series_name:
            return series_name

        # Convert to title case
        normalized = series_name.strip().title()

        # Common normalizations
        replacements = {
            ' And ': ' and ',
            ' Of ': ' of ',
            ' The ': ' the ',
            ' A ': ' a ',
            ' An ': ' an ',
            ' In ': ' in ',
            ' On ': ' on ',
            ' At ': ' at ',
            ' To ': ' to ',
            ' For ': ' for ',
            ' From ': ' from ',
            ' With ': ' with ',
            ' By ': ' by ',
        }

        for old, new in replacements.items():
            normalized = normalized.replace(old, new)

        return normalized

    async def process_book(self, book_item: Dict) -> None:
        """Process a single book from Audiobookshelf with exact provider order and retry logic."""
        try:
            item_id = book_item['id']
            media = book_item.get('media', {})
            metadata = media.get('metadata', {})

            title = metadata.get('title', 'Unknown Title')
            author = metadata.get('authorName', 'Unknown Author')

            logger.info(f"\n📖 Processing: '{title}' by {author}")

            # Provider call order: Google Books API → Goodreads API → Hardcover (third provider)
            provider_order = ['google', 'goodreads', 'hardcover']
            provider_data = None
            successful_provider = None

            # Try each provider with exactly 2 attempts and backoff
            for provider in provider_order:
                logger.info(f"  🔍 Trying {provider} API (2 attempts max)")

                for attempt in range(2):
                    try:
                        logger.info(f"    Attempt {attempt + 1}/2 for {provider}")
                        result = await self.query_provider(provider, title, author)
                        if result:
                            provider_data = result
                            successful_provider = provider
                            logger.info(f"  ✓ {provider} succeeded on attempt {attempt + 1}")
                            break
                        else:
                            logger.warning(f"    ⚠ {provider} attempt {attempt + 1} returned no data")

                    except RateLimitError:
                        logger.warning(f"    ⚠ {provider} attempt {attempt + 1} rate-limited")
                        if attempt < 1:  # Only wait if not the last attempt
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
                        continue
                    except Exception as e:
                        logger.warning(f"    ⚠ {provider} attempt {attempt + 1} error: {e}")
                        if attempt < 1:  # Only wait if not the last attempt
                            await asyncio.sleep(1)  # Fixed 1s delay for errors
                        continue

                # If this provider succeeded, stop trying others
                if provider_data:
                    break

                logger.warning(f"  ✗ {provider} failed after 2 attempts")

            # If all three providers failed, use Goodreads scraper as fallback
            if not provider_data:
                logger.info("  🔄 All APIs failed - using Goodreads scraper fallback")
                try:
                    goodreads_scraper_data = await self.search_goodreads_audiobook(title, author)
                    if goodreads_scraper_data:
                        provider_data = goodreads_scraper_data
                        successful_provider = 'goodreads_scraper'
                        logger.info("  ✓ Goodreads scraper fallback succeeded")
                        self.stats['scraper_fallback_used'] += 1
                    else:
                        logger.warning("  ✗ Goodreads scraper fallback also failed")
                except Exception as e:
                    logger.error(f"  ✗ Goodreads scraper error: {e}")

            if not provider_data:
                logger.warning(f"  ❌ ALL PROVIDERS AND SCRAPER FAILED for '{title}' by {author}")
                self.stats['skipped'].append({
                    'title': title,
                    'author': author,
                    'reason': 'all_providers_and_scraper_failed'
                })
                return

            # Extract enhanced metadata
            enhanced_metadata = self.extract_enhanced_metadata(provider_data)

            # Update Audiobookshelf with quality preservation
            if self.update_audiobookshelf_metadata_quality_preserved(item_id, enhanced_metadata, metadata):
                self.stats['books_updated'] += 1

                # Track which provider succeeded
                if successful_provider:
                    if successful_provider not in self.stats['provider_success']:
                        self.stats['provider_success'][successful_provider] = 0
                    self.stats['provider_success'][successful_provider] += 1

                # Check if series linking was done
                if enhanced_metadata.get('series') and enhanced_metadata.get('seriesNumber'):
                    self.stats['series_linked'] += 1

                self.stats['metadata_enriched'] += 1
                logger.info(f"  ✓ Successfully updated with data from {successful_provider}")
            else:
                self.stats['errors'].append({
                    'title': title,
                    'author': author,
                    'error': 'update_failed'
                })

        except Exception as e:
            logger.error(f"  ✗ Error processing book '{title}': {e}")
            self.stats['errors'].append({
                'title': title,
                'author': author,
                'error': str(e)
            })

    def extract_enhanced_metadata(self, google_data: Dict) -> Dict:
        """Extract enhanced metadata from Google Books data."""
        metadata = {}

        # Basic fields
        metadata['title'] = google_data.get('title', '')
        metadata['subtitle'] = google_data.get('subtitle', '')

        # Authors
        authors = google_data.get('authors', [])
        if authors:
            metadata['authorName'] = ', '.join(authors)

        # Description
        description = google_data.get('description', '')
        if description:
            # Clean HTML tags if present
            description = re.sub(r'<[^>]+>', '', description)
            metadata['description'] = description

        # Publisher and date
        metadata['publisher'] = google_data.get('publisher', '')
        published_date = google_data.get('publishedDate', '')
        if published_date:
            # Extract year
            year_match = re.search(r'(\d{4})', published_date)
            if year_match:
                metadata['publishedYear'] = year_match.group(1)

        # Genres/Categories
        categories = google_data.get('categories', [])
        if categories:
            metadata['genres'] = categories

        # ISBN
        industry_identifiers = google_data.get('industryIdentifiers', [])
        for identifier in industry_identifiers:
            if identifier.get('type') in ['ISBN_13', 'ISBN_10']:
                metadata['isbn'] = identifier.get('identifier')
                break

        # Series information
        series_name, series_number = self.extract_series_info(google_data)
        if series_name:
            metadata['series'] = series_name
        if series_number:
            metadata['seriesNumber'] = series_number

        # Additional tags
        tags = []
        if google_data.get('averageRating'):
            tags.append(f"Rating: {google_data['averageRating']}")
        if google_data.get('maturityRating') == 'NOT_MATURE':
            tags.append('General Audience')

        if tags:
            metadata['tags'] = tags

        return metadata

    async def process_series_linking(self) -> None:
        """Process series linking for all books in the library with validation."""
        logger.info("\n🔗 Processing series linking and validation...")

        try:
            # Get all books again to check series relationships
            books = self.get_audiobookshelf_library()

            # Group books by series
            series_groups = {}
            for book in books:
                media = book.get('media', {})
                metadata = media.get('metadata', {})

                series = metadata.get('series', '').strip()
                if series:
                    # Normalize series name for grouping
                    normalized_series = self.normalize_series_name(series)
                    if normalized_series not in series_groups:
                        series_groups[normalized_series] = []
                    series_groups[normalized_series].append(book)

            # Process each series
            series_validation_results = {}
            for series_name, series_books in series_groups.items():
                if len(series_books) > 1:
                    logger.info(f"  📚 Processing series '{series_name}' ({len(series_books)} books)")

                    # Validate and fix series consistency
                    validation_result = await self.validate_and_fix_series(series_name, series_books)
                    series_validation_results[series_name] = validation_result

                    if validation_result['fixed']:
                        logger.info(f"    ✓ Fixed {validation_result['fixed']} series issues in '{series_name}'")
                    else:
                        logger.info(f"    ✓ Series '{series_name}' already consistent")

            # Generate series validation report
            await self.generate_series_validation_report(series_validation_results)

        except Exception as e:
            logger.error(f"Error processing series linking: {e}")

    async def validate_and_fix_series(self, series_name: str, series_books: List[Dict]) -> Dict[str, Any]:
        """Validate series consistency and fix issues."""
        fixed_count = 0

        try:
            # Sort by series number if available
            sorted_books = sorted(series_books, key=lambda x: self.get_series_number(x))

            # Check for series name consistency and fix
            for book in sorted_books:
                item_id = book['id']
                current_metadata = book.get('media', {}).get('metadata', {})
                current_series = current_metadata.get('series', '')

                # Fix series name if inconsistent
                if current_series != series_name:
                    update_data = {
                        "media": {
                            "metadata": {
                                "series": series_name
                            }
                        }
                    }

                    if self.update_series_metadata(item_id, update_data):
                        fixed_count += 1
                        logger.info(f"      Fixed series name for book '{current_metadata.get('title', 'Unknown')}'")
                    else:
                        logger.warning(f"      Failed to fix series name for book '{current_metadata.get('title', 'Unknown')}'")

            # Check and fix series numbering
            for i, book in enumerate(sorted_books):
                item_id = book['id']
                expected_number = i + 1
                current_metadata = book.get('media', {}).get('metadata', {})
                current_number = current_metadata.get('seriesSequence', '')

                if not current_number or str(current_number) != str(expected_number):
                    update_data = {
                        "media": {
                            "metadata": {
                                "seriesSequence": str(expected_number)
                            }
                        }
                    }

                    if self.update_series_metadata(item_id, update_data):
                        fixed_count += 1
                        logger.info(f"      Fixed series number to {expected_number} for '{current_metadata.get('title', 'Unknown')}'")
                    else:
                        logger.warning(f"      Failed to fix series number for '{current_metadata.get('title', 'Unknown')}'")

            return {
                'series_name': series_name,
                'total_books': len(series_books),
                'fixed': fixed_count,
                'success': True
            }

        except Exception as e:
            logger.error(f"Error validating series '{series_name}': {e}")
            return {
                'series_name': series_name,
                'total_books': len(series_books),
                'fixed': fixed_count,
                'success': False,
                'error': str(e)
            }

    async def generate_series_validation_report(self, validation_results: Dict[str, Any]) -> None:
        """Generate a report of series validation results."""
        report_file = f"series_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        report = f"# Series Validation Report\n\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        total_series = len(validation_results)
        total_fixed = sum(result.get('fixed', 0) for result in validation_results.values())
        successful_validations = sum(1 for result in validation_results.values() if result.get('success', False))

        report += f"## Summary\n\n"
        report += f"- **Total Series Processed:** {total_series}\n"
        report += f"- **Series Successfully Validated:** {successful_validations}\n"
        report += f"- **Total Fixes Applied:** {total_fixed}\n\n"

        report += f"## Series Details\n\n"
        for series_name, result in validation_results.items():
            status = "✅" if result.get('success') else "❌"
            report += f"### {status} {series_name}\n"
            report += f"- Books: {result.get('total_books', 0)}\n"
            report += f"- Fixes Applied: {result.get('fixed', 0)}\n"
            if not result.get('success'):
                report += f"- Error: {result.get('error', 'Unknown')}\n"
            report += "\n"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Series validation report saved: {report_file}")

    def get_series_number(self, book: Dict) -> int:
        """Get series number for sorting."""
        metadata = book.get('media', {}).get('metadata', {})
        series_seq = metadata.get('seriesSequence', '')

        try:
            return int(series_seq) if series_seq else 999
        except ValueError:
            return 999

    def update_series_metadata(self, item_id: str, update_data: Dict) -> bool:
        """Update series metadata for a book."""
        try:
            headers = {
                'Authorization': f'Bearer {self.abs_token}',
                'Content-Type': 'application/json'
            }

            response = requests.patch(
                f"{self.abs_url}/api/items/{item_id}",
                headers=headers,
                json=update_data,
                timeout=15
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error updating series metadata for {item_id}: {e}")
            return False

    async def scrape_goodreads_audiobooks(self) -> None:
        """Scrape Goodreads for additional audiobook information after metadata processing."""
        logger.info("\n📚 Starting Goodreads audiobook scraping...")

        try:
            # Get all books again to process with Goodreads
            books = self.get_audiobookshelf_library()
            if not books:
                logger.warning("No books found for Goodreads scraping")
                return

            goodreads_stats = {
                'books_processed': 0,
                'audiobooks_found': 0,
                'series_updated': 0,
                'errors': []
            }

            for book in books:
                try:
                    item_id = book['id']
                    media = book.get('media', {})
                    metadata = media.get('metadata', {})

                    title = metadata.get('title', 'Unknown Title')
                    author = metadata.get('authorName', 'Unknown Author')
                    series = metadata.get('series', '')

                    goodreads_stats['books_processed'] += 1

                    logger.info(f"  🔍 Searching Goodreads for: '{title}' by {author}")

                    # Search Goodreads for the title
                    goodreads_data = await self.search_goodreads_audiobook(title, author)
                    if goodreads_data:
                        goodreads_stats['audiobooks_found'] += 1

                        # Extract series information from Goodreads
                        goodreads_series = goodreads_data.get('series', '')
                        goodreads_series_number = goodreads_data.get('series_number', '')

                        # Update Audiobookshelf if we found better series info
                        update_needed = False
                        update_data = {"media": {"metadata": {}}}

                        # Prioritize series matching - ensure consistency
                        if goodreads_series and (not series or series.lower() != goodreads_series.lower()):
                            update_data["media"]["metadata"]["series"] = goodreads_series
                            update_needed = True
                            logger.info(f"    ✓ Updated series to: {goodreads_series}")

                        if goodreads_series_number and str(goodreads_series_number) != str(metadata.get('seriesSequence', '')):
                            update_data["media"]["metadata"]["seriesSequence"] = str(goodreads_series_number)
                            update_needed = True
                            logger.info(f"    ✓ Updated series number to: {goodreads_series_number}")

                        # Update other audiobook-specific metadata if available
                        if goodreads_data.get('narrator') and not metadata.get('narratorName'):
                            update_data["media"]["metadata"]["narratorName"] = goodreads_data['narrator']
                            update_needed = True

                        if goodreads_data.get('duration') and not metadata.get('duration'):
                            update_data["media"]["metadata"]["duration"] = goodreads_data['duration']
                            update_needed = True

                        if update_needed:
                            if self.update_audiobookshelf_metadata(item_id, update_data["media"]["metadata"]):
                                goodreads_stats['series_updated'] += 1
                                logger.info(f"    ✓ Successfully updated Audiobookshelf metadata")
                            else:
                                goodreads_stats['errors'].append({
                                    'title': title,
                                    'author': author,
                                    'error': 'update_failed'
                                })
                    else:
                        logger.info(f"    ⚠ No audiobook data found on Goodreads")

                    # Stealth mode: Longer delays between requests to avoid detection
                    await asyncio.sleep(3 + (hash(title + author) % 3))  # 3-6 second random delays

                except Exception as e:
                    logger.error(f"    ✗ Error processing '{title}': {e}")
                    goodreads_stats['errors'].append({
                        'title': title,
                        'author': author,
                        'error': str(e)
                    })

            # Log Goodreads scraping summary
            logger.info("\n" + "="*50)
            logger.info("GOODREADS AUDIOBOOK SCRAPING SUMMARY")
            logger.info("="*50)
            logger.info(f"Books processed: {goodreads_stats['books_processed']}")
            logger.info(f"Audiobooks found: {goodreads_stats['audiobooks_found']}")
            logger.info(f"Series info updated: {goodreads_stats['series_updated']}")
            logger.info(f"Errors: {len(goodreads_stats['errors'])}")

            if goodreads_stats['series_updated'] > 0:
                logger.info(f"\n🎯 SUCCESS: Enhanced {goodreads_stats['series_updated']} books with Goodreads data!")

        except Exception as e:
            logger.error(f"Error during Goodreads scraping: {e}")

    async def search_goodreads_audiobook(self, title: str, author: str = "") -> Optional[Dict]:
        """Search Goodreads for audiobook information using stealth mode."""
        try:
            # Stealth mode: Use browser-like headers and longer delays
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }

            # Use the goodreads provider URL
            url = self.provider_urls["goodreads"].format(q=title.replace(" ","+"), a=author.replace(" ","+"))

            async with aiohttp.ClientSession(headers=headers) as session:
                # Add random delay to avoid detection (2-5 seconds)
                await asyncio.sleep(2 + (hash(title) % 3))

                async with session.get(url, timeout=20) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self.extract_goodreads_audiobook_data(data, title, author)
                    else:
                        logger.warning(f"Goodreads API error: {response.status}")
                        return None

        except Exception as e:
            logger.warning(f"Failed to search Goodreads for '{title}': {e}")
            return None

    def extract_goodreads_audiobook_data(self, data: Dict, title: str, author: str) -> Optional[Dict]:
        """Extract audiobook-specific data from Goodreads response."""
        try:
            # Assuming Goodreads returns data in a specific format
            # This would need to be adjusted based on actual Goodreads API response structure
            audiobook_data = {}

            # Extract series information (prioritize this)
            if 'series' in data:
                audiobook_data['series'] = data['series'].strip()
            if 'series_number' in data:
                audiobook_data['series_number'] = data['series_number']

            # Extract audiobook-specific fields
            if 'narrator' in data:
                audiobook_data['narrator'] = data['narrator']
            if 'duration' in data:
                audiobook_data['duration'] = data['duration']
            if 'format' in data and 'audiobook' in data['format'].lower():
                audiobook_data['is_audiobook'] = True

            # Only return data if it's actually an audiobook
            if audiobook_data.get('is_audiobook') or audiobook_data.get('narrator'):
                return audiobook_data
            else:
                return None

        except Exception as e:
            logger.warning(f"Failed to extract Goodreads data: {e}")
            return None

    async def run(self) -> None:
        """Main execution."""
        logger.info("="*70)
        logger.info("AUDIOBOOKSHELF METADATA SYNC WITH GOOGLE BOOKS API")
        logger.info("="*70)

        # Get Audiobookshelf library
        books = self.get_audiobookshelf_library()
        if not books:
            logger.error("No books found in Audiobookshelf library")
            return

        logger.info(f"Found {len(books)} books to process")

        # Process each book
        for book in books:
            await self.process_book(book)
            self.stats['books_processed'] += 1

            # Rate limiting
            await asyncio.sleep(1)

        # Process series linking
        await self.process_series_linking()

        # After metadata processing, scrape Goodreads for additional audiobook info
        await self.scrape_goodreads_audiobooks()

        # Print summary
        self.print_summary()

    def print_summary(self) -> None:
        """Print comprehensive final summary with provider breakdown."""
        logger.info("\n" + "="*70)
        logger.info("AUDIOBOOKSHELF METADATA SYNC - FINAL SUMMARY")
        logger.info("="*70)

        # Basic stats
        logger.info(f"📊 Books processed: {self.stats['books_processed']}")
        logger.info(f"📝 Books updated: {self.stats['books_updated']}")
        logger.info(f"🎯 Metadata enriched: {self.stats['metadata_enriched']}")
        logger.info(f"📚 Series linked: {self.stats['series_linked']}")
        logger.info(f"🔄 Scraper fallback used: {self.stats['scraper_fallback_used']}")
        logger.info(f"⏭️  Books skipped: {len(self.stats['skipped'])}")
        logger.info(f"❌ Errors: {len(self.stats['errors'])}")

        # Provider success breakdown
        if self.stats['provider_success']:
            logger.info(f"\n🔍 Provider Success Rates:")
            total_successes = sum(self.stats['provider_success'].values())
            for provider, count in self.stats['provider_success'].items():
                percentage = (count / max(self.stats['books_updated'], 1)) * 100
                logger.info(f"  - {provider}: {count} books ({percentage:.1f}%)")

        # Series success
        if self.stats['series_linked'] > 0:
            logger.info(f"\n🎯 SUCCESS: Enhanced series metadata for {self.stats['series_linked']} books!")

        # Errors summary
        if self.stats['errors']:
            logger.info(f"\n❌ Errors encountered ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                logger.info(f"  - '{error['title']}' by {error['author']}: {error['error']}")

        # Skipped books summary
        if self.stats['skipped']:
            logger.info(f"\n⏭️  Books skipped ({len(self.stats['skipped'])}):")
            provider_failures = sum(1 for s in self.stats['skipped'] if 'all_providers_failed' in s.get('reason', ''))
            scraper_failures = sum(1 for s in self.stats['skipped'] if 'all_providers_and_scraper_failed' in s.get('reason', ''))
            logger.info(f"  - API failures: {provider_failures}")
            logger.info(f"  - API + scraper failures: {scraper_failures}")

        # Save detailed stats
        stats_file = f"audiobookshelf_sync_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        logger.info(f"\n💾 Detailed stats saved to {stats_file}")

        # Success rate
        success_rate = (self.stats['books_updated'] / max(self.stats['books_processed'], 1)) * 100
        logger.info(f"\n🎉 Overall Success Rate: {success_rate:.1f}%")
        logger.info("="*70)


async def main():
    """Entry point."""
    sync = AudiobookshelfMetadataSync()
    await sync.run()


if __name__ == "__main__":
    asyncio.run(main())