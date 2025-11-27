#!/usr/bin/env python
"""
Validate Audiobookshelf Metadata Against Goodreads
Cross-references books in library with Goodreads to verify series and metadata accuracy
"""

import asyncio
import aiohttp
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

load_dotenv()

class GoodreadsValidator:
    def __init__(self):
        self.goodreads_email = os.getenv('GOODREADS_EMAIL')
        self.goodreads_password = os.getenv('GOODREADS_PASSWORD')
        self.driver = None
        self.cache = {}

    def setup_driver(self):
        """Initialize Selenium WebDriver for Goodreads"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.driver = webdriver.Chrome(options=chrome_options)

    def login_to_goodreads(self):
        """Login to Goodreads"""
        try:
            self.driver.get('https://www.goodreads.com/user/sign_in')
            time.sleep(2)

            # Find and fill email field
            email_field = self.driver.find_element(By.ID, 'user_email')
            email_field.send_keys(self.goodreads_email)

            # Find and fill password field
            password_field = self.driver.find_element(By.ID, 'user_password')
            password_field.send_keys(self.goodreads_password)

            # Click sign in button
            sign_in_button = self.driver.find_element(By.NAME, 'commit')
            sign_in_button.click()

            # Wait for login to complete
            time.sleep(3)
            print("[OK] Logged into Goodreads")
            return True
        except Exception as e:
            print(f"[ERROR] Goodreads login failed: {e}")
            return False

    def search_book_on_goodreads(self, title, author):
        """Search for book on Goodreads and extract series info"""
        if (title, author) in self.cache:
            return self.cache[(title, author)]

        try:
            # URL-encode the search query
            search_query = f'{title} {author}'.strip()
            search_url = f'https://www.goodreads.com/search?q={search_query}'

            self.driver.get(search_url)
            time.sleep(1)

            # Wait for search results
            try:
                first_result = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'bookTitle'))
                )

                # Extract book info
                try:
                    series_element = self.driver.find_element(By.CLASS_NAME, 'greyText')
                    series_text = series_element.text if series_element else ''
                except:
                    series_text = ''

                result = {'found': True, 'series': series_text}
                self.cache[(title, author)] = result
                return result
            except:
                result = {'found': False, 'series': ''}
                self.cache[(title, author)] = result
                return result
        except Exception as e:
            print(f"[ERROR] Goodreads search error for '{title}': {e}")
            return {'found': False, 'series': '', 'error': str(e)}

    def cleanup(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()


async def main():
    abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
    abs_token = os.getenv('ABS_TOKEN')
    headers = {'Authorization': f'Bearer {abs_token}'}
    books_dir = Path('F:/Audiobookshelf/Books')

    print("GOODREADS METADATA VALIDATION")
    print("=" * 80)
    print()

    # Initialize Goodreads validator
    validator = GoodreadsValidator()
    validator.setup_driver()
    if not validator.login_to_goodreads():
        print("WARNING: Could not login to Goodreads. Skipping Goodreads validation.")
        validator.cleanup()
        return

    try:
        async with aiohttp.ClientSession() as session:
            # Get library ID
            async with session.get(f'{abs_url}/api/libraries', headers=headers) as resp:
                libs = await resp.json()
                lib_id = libs['libraries'][0]['id']

            print(f"Library ID: {lib_id}")
            print()

            # Load all library items
            print("Loading library items from API...")
            all_items = []
            offset = 0
            page = 0

            while offset < 10000:  # Limit to first 10K items for validation sample
                async with session.get(
                    f'{abs_url}/api/libraries/{lib_id}/items?limit=500&offset={offset}',
                    headers=headers
                ) as resp:
                    result = await resp.json()
                    items = result.get('results', [])
                    if not items:
                        break
                    all_items.extend(items)
                    page += 1
                    offset += 500
                    print(f"  Page {page}: loaded {len(items)} items (total: {len(all_items)})", end='\r')

            print(f"\nTotal items loaded: {len(all_items)}")
            print()

            # Validate sample of books
            print("VALIDATING BOOKS AGAINST GOODREADS")
            print("-" * 80)

            validated = 0
            matches = 0
            mismatches = 0
            not_found = 0

            # Sample every 100th book for validation (to save time)
            for idx, item in enumerate(all_items[::100]):
                if validated >= 50:  # Validate first 50 sampled books
                    break

                media_metadata = item.get('media', {}).get('metadata', {})
                title = media_metadata.get('title', '')
                author = media_metadata.get('authorName', '')
                series_in_abs = media_metadata.get('seriesName', '')

                if not title or not author:
                    continue

                # Search on Goodreads
                gr_result = validator.search_book_on_goodreads(title, author)

                if gr_result['found']:
                    gr_series = gr_result.get('series', '')

                    print(f"\n[BOOK {validated + 1}] {title}")
                    print(f"  Author: {author}")
                    print(f"  ABS Series: {series_in_abs or '(none)'}")
                    print(f"  GR Series: {gr_series or '(none)'}")

                    if series_in_abs and gr_series:
                        if series_in_abs.lower() == gr_series.lower():
                            print(f"  Status: [MATCH]")
                            matches += 1
                        else:
                            print(f"  Status: [MISMATCH]")
                            mismatches += 1
                    else:
                        print(f"  Status: [OK - One or both empty]")

                else:
                    print(f"\n[BOOK {validated + 1}] {title}")
                    print(f"  Status: [NOT FOUND ON GOODREADS]")
                    not_found += 1

                validated += 1
                time.sleep(0.5)  # Rate limiting

        print()
        print("=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Books validated: {validated}")
        print(f"  - Matches: {matches}")
        print(f"  - Mismatches: {mismatches}")
        print(f"  - Not found on Goodreads: {not_found}")
        print()
        print("Validation complete.")

    finally:
        validator.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
