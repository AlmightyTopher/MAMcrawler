#!/usr/bin/env python3
"""
Search Prowlarr for Randi Darren titles using variations of names
Tests different title formats to find more matches
"""
import os
import sys
import json
import time
import requests
from typing import List, Dict, Tuple
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

PROWLARR_URL = os.getenv('PROWLARR_URL', 'http://localhost:9696')
PROWLARR_API_KEY = os.getenv('PROWLARR_API_KEY')

# Missing titles from Goodreads (18 titles not found in initial Prowlarr search)
MISSING_TITLES = [
    # Fostering Faust Series
    "Fostering Faust",  # #1
    "Fostering Faust Compilation Rebirth",

    # Incubus Inc. Series
    "Incubus Inc",  # #1
    "Incubus Inc II",  # #2
    "Incubus Inc III",  # #3
    "Incubus Inc Book 2",
    "Incubus Inc Compilation Running the Precipice",

    # Privateer's Commission Series
    "Privateer's Commission",
    "Privateer's Commission 2",

    # Remnant Series
    "Remnant",  # #1
    "Remnant II",  # #2
    "Remnant III",  # #3
    "Remnant Compilation The Road To Hell",

    # Wild Wastes Series
    "Eastern Expansion",  # Wild Wastes #2
    "Southern Storm",  # Wild Wastes #3
    "Wild Wastes",  # #1
    "Wild Wastes Omnibus",
]

def generate_variations(title: str) -> List[str]:
    """Generate multiple search variations for a title"""
    variations = [title]

    # Remove subtitles/series markers
    if " - " in title:
        variations.append(title.split(" - ")[0])

    # Try with Randi Darren prefix
    variations.append(f"Randi Darren {title}")

    # Remove commas and quotes
    clean_title = title.replace("'", "").replace('"', '')
    if clean_title != title:
        variations.append(clean_title)

    # Try without series numbers
    for pattern in ["#1", "#2", "#3", "II", "III", "IV", "V", "VI"]:
        if pattern in title:
            clean = title.replace(pattern, "").strip()
            if clean:
                variations.append(clean)

    # Try compact series names
    variations.append(title.replace(" ", ""))
    variations.append(title.replace(" Inc", " Inc."))

    # Remove duplicates while preserving order
    seen = set()
    unique_variations = []
    for v in variations:
        v_clean = v.lower().strip()
        if v_clean not in seen:
            seen.add(v_clean)
            unique_variations.append(v)

    return unique_variations

def search_prowlarr(query: str) -> List[Dict]:
    """Search Prowlarr for a query"""
    try:
        params = {
            'query': query,
            'type': 'search'
        }

        headers = {
            'X-Api-Key': PROWLARR_API_KEY
        }

        response = requests.get(
            f"{PROWLARR_URL}/api/v1/search",
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        print(f"Error searching Prowlarr: {e}", file=sys.stderr)
        return []

def find_audiobook_results(results: List[Dict], query: str) -> List[Dict]:
    """Filter results for audiobook-related items"""
    audiobook_results = []

    for result in results:
        title = result.get('title', '').lower()
        # Look for audiobook indicators
        if any(indicator in title for indicator in ['audiobook', 'm4b', 'mp3', 'aac', 'narrator', 'narrated']):
            audiobook_results.append(result)

    return audiobook_results

def main():
    print("\n" + "="*80)
    print("PROWLARR TITLE VARIATIONS SEARCH - Randi Darren")
    print("="*80)

    if not PROWLARR_API_KEY:
        print("ERROR: PROWLARR_API_KEY not set in environment")
        sys.exit(1)

    print(f"Searching Prowlarr: {PROWLARR_URL}")
    print(f"Testing {len(MISSING_TITLES)} missing titles with variations...\n")

    found_titles = {}
    total_results = 0

    for title in MISSING_TITLES:
        print(f"\n{'='*80}")
        print(f"TITLE: {title}")
        print(f"{'='*80}")

        variations = generate_variations(title)
        print(f"Trying {len(variations)} variations:")

        title_found = False

        for i, variation in enumerate(variations, 1):
            print(f"  [{i}] {variation:<50}", end=" ", flush=True)

            results = search_prowlarr(variation)

            if results:
                # Filter for audiobook results
                audiobook_results = find_audiobook_results(results, variation)

                if audiobook_results:
                    print(f"[FOUND] {len(audiobook_results)} results")
                    title_found = True

                    for result in audiobook_results[:3]:  # Show top 3
                        print(f"      - {result.get('title', 'N/A')[:70]}")
                        print(f"        Size: {result.get('size', 'N/A')} | Seeders: {result.get('seeders', 0)}")

                    if title not in found_titles:
                        found_titles[title] = audiobook_results

                    total_results += len(audiobook_results)
                else:
                    print(f"  (found {len(results)} results but non-audiobook)")
            else:
                print("  -")

            time.sleep(0.5)  # Rate limiting

        if not title_found:
            print(f"  [NO RESULTS]")

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total Missing Titles: {len(MISSING_TITLES)}")
    print(f"Titles Found: {len(found_titles)}")
    print(f"Total Results: {total_results}")

    if found_titles:
        print(f"\nSuccessfully found matches for:")
        for title in found_titles.keys():
            count = len(found_titles[title])
            print(f"  - {title} ({count} results)")
    else:
        print(f"\nNo audiobook matches found in Prowlarr for any title variations")

    print("\n" + "="*80)

if __name__ == '__main__':
    main()
