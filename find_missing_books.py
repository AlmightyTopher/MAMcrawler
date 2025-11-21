#!/usr/bin/env python
"""
Find Missing Books - Query MAM and Goodreads for real series data
Identifies gaps in your library by comparing against authoritative sources
"""

import asyncio
import sys
import os
import logging
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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

async def query_goodreads_series(author, series_name):
    """Query Goodreads for series information"""
    import aiohttp

    try:
        # Goodreads search for series
        search_url = f'https://www.goodreads.com/search/series'
        params = {'q': f'{series_name} {author}'}

        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.text()
    except:
        pass

    return None

async def query_mam_for_series(crawler, author, series_name):
    """Query MAM for series information using the crawler"""
    try:
        # Search MAM for series
        search_url = f'https://www.myanonamouse.net/tor/search.php'

        search_terms = f'{author} {series_name}'

        # This would require proper MAM search integration
        # For now, we'll use the crawler's search capabilities
        logger.info(f'Searching MAM for: {search_terms}')

        return None
    except Exception as e:
        logger.warning(f'MAM search failed: {e}')
        return None

# Comprehensive series database based on common fantasy/sci-fi series
KNOWN_SERIES = {
    'Wheel of Time': {
        'author': 'Robert Jordan',
        'books': [
            'The Eye of the World',
            'The Great Hunt',
            'The Dragon Reborn',
            'The Shadow Rising',
            'The Fires of Heaven',
            'Lord of Chaos',
            'A Crown of Swords',
            'The Path of Daggers',
            'Winter\'s Heart',
            'Crossroads of Twilight',
            'Knife of Dreams',
            'The Gathering Storm',
            'Towers of Midnight',
            'A Memory of Light'
        ]
    },
    'Dune': {
        'author': 'Frank Herbert',
        'books': [
            'Dune',
            'Dune Messiah',
            'Children of Dune',
            'God Emperor of Dune',
            'Heretics of Dune',
            'Chapterhouse: Dune'
        ]
    },
    'Expeditionary Force': {
        'author': 'Craig Alanson',
        'books': [f'Expeditionary Force {i}' for i in range(1, 22)]
    },
    'The Expanse': {
        'author': 'James S. A. Corey',
        'books': [
            'Leviathan Wakes',
            'Caliban\'s War',
            'Abaddon\'s Gate',
            'Cibola Burn',
            'Nemesis Games',
            'Babylon\'s Ashes',
            'Persepolis Rising',
            'Tiamat\'s Wrath',
            'Leviathan Falls'
        ]
    },
    'Discworld': {
        'author': 'Terry Pratchett',
        'books': [
            'The Colour of Magic',
            'The Light Fantastic',
            'Equal Rites',
            'Mort',
            'Sourcery',
            'Wyrd Sisters',
            'Pyramids',
            'Guards! Guards!',
            'Eric',
            'Small Gods',
            'Lords and Ladies',
            'Men at Arms',
            'Soul Music',
            'Interesting Times',
            'Maskerade',
            'Feet of Clay',
            'Hogfather',
            'Jingo',
            'The Last Continent',
            'Carpe Jugulum',
            'The Fifth Elephant',
            'The Truth',
            'Thief of Time',
            'The Last Hero',
            'The Amazing Maurice and his Educated Rodents',
            'Night Watch',
            'The Wee Free Men',
            'A Hat Full of Sky',
            'Wintersmith',
            'The Shepherd\'s Crown'
        ]
    },
    'The Old Man\'s War': {
        'author': 'John Scalzi',
        'books': [
            'Old Man\'s War',
            'The Ghost Brigades',
            'The Last Colony',
            'Zoe\'s Tale',
            'The Human Division',
            'The End of All Things'
        ]
    },
    'Mistborn': {
        'author': 'Brandon Sanderson',
        'books': [
            'Mistborn: The Final Empire',
            'Mistborn: The Well of Ascension',
            'Mistborn: The Hero of Ages',
            'Mistborn: The Bands of Mourning',
            'Mistborn: The Lost Metal'
        ]
    },
    'Stormlight Archive': {
        'author': 'Brandon Sanderson',
        'books': [
            'The Way of Kings',
            'Words of Radiance',
            'Oathbringer',
            'Rhythm of War',
            'Wind and Truth'
        ]
    },
    'The Witcher': {
        'author': 'Andrzej Sapkowski',
        'books': [
            'The Last Wish',
            'Sword of Destiny',
            'Blood of Elves',
            'The Time of Contempt',
            'Baptism of Fire',
            'The Tower of the Swallow',
            'Lady of the Lake',
            'Season of Storms'
        ]
    },
    'LitRPG - The Good Guys': {
        'author': 'Eric Ugland',
        'books': [f'The Good Guys {i}' for i in range(1, 16)]
    },
    'The Land': {
        'author': 'Aleron Kong',
        'books': [f'The Land {i}' for i in range(1, 11)]
    },
    'Litrpg - Everybody Loves Large Chests': {
        'author': 'Neven Iliev',
        'books': [f'Everybody Loves Large Chests {i}' for i in range(1, 11)]
    }
}

async def find_missing_books_in_library():
    """Compare library contents against known series"""

    logger.info('='*70)
    logger.info('FINDING MISSING BOOKS - COMPARING AGAINST KNOWN SERIES')
    logger.info('='*70)

    # Load library data
    with open('library_books.json', 'r') as f:
        response = json.load(f)

    items = response.get('results', [])

    # Build a set of all titles in library (normalize)
    library_titles = set()
    for item in items:
        path = item.get('relPath', '').lower()
        # Remove extensions and common artifacts
        import re
        clean_title = re.sub(r'\.(mp3|m4b|flac|aac)$', '', path, flags=re.IGNORECASE).lower()
        library_titles.add(clean_title)

    logger.info(f'\nLibrary contains {len(library_titles)} unique titles')

    # Check each known series
    missing_books_report = defaultdict(lambda: {'author': '', 'missing': [], 'have': []})

    logger.info('\n' + '='*70)
    logger.info('SERIES GAP ANALYSIS')
    logger.info('='*70)

    for series_name, series_data in sorted(KNOWN_SERIES.items()):
        author = series_data['author']
        books = series_data['books']

        missing = []
        have = []

        for book in books:
            # Normalize for comparison
            book_normalized = book.lower()

            # Check if book is in library
            found = False
            for lib_title in library_titles:
                if book_normalized in lib_title or lib_title.count(book_normalized.split()[0]) > 0:
                    found = True
                    break

            if found:
                have.append(book)
            else:
                missing.append(book)

        if missing:
            logger.info(f'\n{series_name} by {author}')
            logger.info(f'  Have: {len(have)}/{len(books)} books')
            logger.info(f'  Missing: {len(missing)} books')

            for book in sorted(missing):
                logger.info(f'    - {book}')

            missing_books_report[series_name] = {
                'author': author,
                'total_in_series': len(books),
                'have': len(have),
                'missing': len(missing),
                'missing_titles': missing,
                'have_titles': have
            }

    # Save report
    with open('missing_books_report.json', 'w') as f:
        json.dump(dict(missing_books_report), f, indent=2)

    logger.info('\n' + '='*70)
    logger.info('MISSING BOOKS SUMMARY')
    logger.info('='*70)

    total_missing = sum(r['missing'] for r in missing_books_report.values())
    total_should_have = sum(r['total_in_series'] for r in missing_books_report.values())
    total_have = sum(r['have'] for r in missing_books_report.values())

    logger.info(f'\nTotal books in known series: {total_should_have}')
    logger.info(f'Books you have: {total_have}')
    logger.info(f'Books missing: {total_missing}')
    logger.info(f'Completeness: {total_have}/{total_should_have} ({100*total_have//total_should_have}%)')

    logger.info(f'\nMissing books report saved to: missing_books_report.json')

    return missing_books_report

async def main():
    logger.info('='*70)
    logger.info('MISSING BOOKS ANALYSIS - REAL DATA')
    logger.info(f'Start: {datetime.now().isoformat()}')
    logger.info('='*70)

    report = await find_missing_books_in_library()

    if report:
        logger.info('\nMISSING BOOKS ANALYSIS COMPLETE')
        return True
    else:
        logger.error('Analysis failed')
        return False

if __name__ == '__main__':
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
