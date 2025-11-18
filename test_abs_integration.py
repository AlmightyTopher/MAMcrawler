#!/usr/bin/env python3
"""Test Audiobookshelf integration for duplicate detection."""

import os
import sys

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_abs_connection():
    """Test connection to Audiobookshelf API."""
    import requests
    from dotenv import load_dotenv

    load_dotenv()

    abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
    abs_token = os.getenv('ABS_TOKEN', '')

    print(f"Testing Audiobookshelf connection...")
    print(f"URL: {abs_url}")
    print(f"Token: {abs_token[:20]}..." if abs_token else "Token: (empty)")
    print()

    headers = {
        'Authorization': f'Bearer {abs_token}'
    }

    try:
        # Test libraries endpoint
        print("1. Fetching libraries...")
        response = requests.get(f'{abs_url}/api/libraries', headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            libraries = response.json().get('libraries', [])
            print(f"   Found {len(libraries)} libraries")

            # Get all audiobooks
            print("\n2. Fetching audiobooks from all libraries...")
            all_books = []
            for library in libraries:
                library_id = library.get('id')
                library_name = library.get('name', 'Unknown')
                print(f"   - Library: {library_name} (ID: {library_id})")

                lib_response = requests.get(
                    f'{abs_url}/api/libraries/{library_id}/items',
                    headers=headers,
                    params={'limit': 10000},
                    timeout=30
                )

                if lib_response.status_code == 200:
                    items = lib_response.json().get('results', [])
                    print(f"     Books: {len(items)}")
                    all_books.extend(items)

            print(f"\n3. Total audiobooks found: {len(all_books)}")

            # Show sample titles
            if all_books:
                print("\n4. Sample titles from library:")
                for i, book in enumerate(all_books[:5], 1):
                    media = book.get('media', {})
                    metadata = media.get('metadata', {})
                    title = metadata.get('title', 'Unknown')
                    author = metadata.get('authorName', 'Unknown')
                    print(f"   {i}. {title} by {author}")

            print("\n✓ SUCCESS: Audiobookshelf integration working correctly!")
            return True
        else:
            print(f"   ERROR: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("✗ ERROR: Could not connect to Audiobookshelf")
        print("  Make sure Audiobookshelf is running at http://localhost:13378")
        return False
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
        return False

if __name__ == '__main__':
    success = test_abs_connection()
    sys.exit(0 if success else 1)
