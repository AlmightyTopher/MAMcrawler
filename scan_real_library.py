#!/usr/bin/env python
"""
Real Library Scanning - Actually query Audiobookshelf for real data
"""

import asyncio
import sys
import os
import logging
import json
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('execution.log', encoding='utf-8')
    ]
)
logger = logging.getLogger()

# Load env
for line in Path('.env').read_text().split('\n'):
    if line.strip() and not line.startswith('#') and '=' in line:
        k, v = line.split('=', 1)
        k = k.strip().strip('\'"')
        v = v.strip().strip('\'"')
        if k and v and 'your_' not in v.lower():
            os.environ[k] = v

async def scan_audiobookshelf_library():
    """Actually connect to Audiobookshelf and scan the real library"""

    logger.info('='*70)
    logger.info('REAL LIBRARY SCAN - QUERYING AUDIOBOOKSHELF')
    logger.info('='*70)

    import aiohttp

    abs_url = os.getenv('ABS_URL')
    abs_token = os.getenv('ABS_TOKEN')

    if not abs_url or not abs_token:
        logger.error('Missing ABS_URL or ABS_TOKEN')
        return None

    headers = {
        'Authorization': f'Bearer {abs_token}',
        'Content-Type': 'application/json'
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            # Get libraries
            logger.info('Fetching libraries from Audiobookshelf...')
            async with session.get(f'{abs_url}/api/v1/libraries', timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.error(f'Failed to get libraries: {resp.status}')
                    return None

                libraries = await resp.json()
                logger.info(f'Found {len(libraries)} libraries')

                all_books = []

                # For each library, get all items
                for lib in libraries:
                    lib_id = lib.get('id')
                    lib_name = lib.get('name', 'Unknown')
                    logger.info(f'\nScanning library: {lib_name}')

                    # Get items in library
                    async with session.get(
                        f'{abs_url}/api/v1/libraries/{lib_id}/items',
                        params={'limit': 10000},
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as items_resp:
                        if items_resp.status == 200:
                            items_data = await items_resp.json()
                            items = items_data.get('results', []) if isinstance(items_data, dict) else items_data

                            logger.info(f'  Found {len(items)} items')

                            for item in items:
                                book_data = {
                                    'title': item.get('media', {}).get('metadata', {}).get('title', 'Unknown'),
                                    'author': item.get('media', {}).get('metadata', {}).get('authors', [{}])[0].get('name', 'Unknown') if item.get('media', {}).get('metadata', {}).get('authors') else 'Unknown',
                                    'series': item.get('media', {}).get('metadata', {}).get('series', 'No Series'),
                                    'id': item.get('id'),
                                    'addedAt': item.get('addedAt')
                                }
                                all_books.append(book_data)

                # Save results
                with open('library_scan_results.json', 'w', encoding='utf-8') as f:
                    json.dump(all_books, f, indent=2)

                logger.info(f'\nTotal books in library: {len(all_books)}')
                logger.info('Results saved to library_scan_results.json')

                return all_books

    except asyncio.TimeoutError:
        logger.error('Timeout connecting to Audiobookshelf')
        return None
    except Exception as e:
        logger.error(f'Error querying Audiobookshelf: {type(e).__name__}: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return None

async def analyze_gaps(books):
    """Analyze library for series gaps and missing author books"""

    if not books:
        logger.error('No books to analyze')
        return

    logger.info('\n' + '='*70)
    logger.info('ANALYZING LIBRARY FOR GAPS')
    logger.info('='*70)

    # Group by author
    authors = {}
    series_list = {}

    for book in books:
        author = book.get('author', 'Unknown')
        series = book.get('series', 'No Series')
        title = book.get('title', 'Unknown')

        if author not in authors:
            authors[author] = {'books': [], 'series': {}}

        authors[author]['books'].append(title)

        if series != 'No Series':
            if series not in authors[author]['series']:
                authors[author]['series'][series] = []
            authors[author]['series'][series].append(title)

            if series not in series_list:
                series_list[series] = []
            series_list[series].append({'author': author, 'title': title})

    # Report findings
    logger.info(f'\nTotal unique authors: {len(authors)}')
    logger.info(f'Total unique series: {len(series_list)}')

    # Find series with gaps
    logger.info('\nANALYZING SERIES FOR GAPS:')
    for series in sorted(series_list.keys()):
        books_in_series = series_list[series]
        logger.info(f'\n  Series: {series}')
        logger.info(f'    Books: {len(books_in_series)}')
        for book in books_in_series:
            logger.info(f'      - {book["title"]} by {book["author"]}')

    # Report authors with multiple books
    logger.info('\n\nAUTHORS WITH MULTIPLE BOOKS:')
    multi_book_authors = {a: authors[a] for a in authors if len(authors[a]['books']) > 1}
    for author in sorted(multi_book_authors.keys()):
        books_list = multi_book_authors[author]['books']
        series_count = len(multi_book_authors[author]['series'])
        logger.info(f'\n  {author}')
        logger.info(f'    Total books: {len(books_list)}')
        logger.info(f'    Series: {series_count}')
        for series, titles in multi_book_authors[author]['series'].items():
            logger.info(f'      {series}: {len(titles)} books')

    # Save detailed analysis
    analysis = {
        'total_books': len(books),
        'total_authors': len(authors),
        'total_series': len(series_list),
        'authors': authors,
        'series': series_list
    }

    with open('library_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2)

    logger.info('\n\nDetailed analysis saved to library_analysis.json')
    logger.info('='*70)

async def main():
    logger.info('='*70)
    logger.info('REAL LIBRARY ANALYSIS')
    logger.info(f'Start: {datetime.now().isoformat()}')
    logger.info('='*70)

    # Get real data from Audiobookshelf
    books = await scan_audiobookshelf_library()

    if books:
        # Analyze the real data
        await analyze_gaps(books)
        logger.info('\nLIBRARY SCAN COMPLETE - Real data analyzed')
        return True
    else:
        logger.error('Failed to retrieve library data')
        return False

if __name__ == '__main__':
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
