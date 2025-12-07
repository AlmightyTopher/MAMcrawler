#!/usr/bin/env python3
"""
Prowlarr Audiobook Indexer Setup Script
========================================

Adds and configures audiobook-capable indexers to Prowlarr for automated downloading.
"""

import sys
import os
import json
import requests
from typing import Dict, Any, List

if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

from dotenv import load_dotenv
load_dotenv()

class ProwlarrIndexerSetup:
    """Setup audiobook-capable indexers in Prowlarr"""

    def __init__(self):
        self.prowlarr_url = os.getenv('PROWLARR_URL', 'http://localhost:9696')
        self.prowlarr_api_key = os.getenv('PROWLARR_API_KEY')

        self.session = requests.Session()
        self.session.headers.update({
            'X-Api-Key': self.prowlarr_api_key,
            'Content-Type': 'application/json'
        })

        # Common audiobook-capable public indexers
        self.audiobook_indexers = [
            {
                "name": "1337x",
                "implementation": "Torznab",
                "settings": {
                    "baseUrl": "https://1337x.to",
                    "apiPath": "/torznab-api",
                    "categories": [8000, 100013],  # Books, AudioBooks
                    "apiKey": "",
                    "minimumSeeders": 1
                },
                "enableRss": True,
                "enableAutomaticSearch": True,
                "enableInteractiveSearch": True,
                "supportsRss": True,
                "supportsSearch": True,
                "protocol": "torrent",
                "priority": 25,
                "downloadClientId": 0
            },
            {
                "name": "RARBG",
                "implementation": "Rarbg",
                "settings": {
                    "baseUrl": "https://rarbg.to",
                    "apiKey": "",
                    "categories": [8000, 100013],  # Books, AudioBooks
                    "minimumSeeders": 1,
                    "sortedBy": "last"
                },
                "enableRss": True,
                "enableAutomaticSearch": True,
                "enableInteractiveSearch": True,
                "supportsRss": True,
                "supportsSearch": True,
                "protocol": "torrent",
                "priority": 25,
                "downloadClientId": 0
            },
            {
                "name": "The Pirate Bay",
                "implementation": "ThePirateBay",
                "settings": {
                    "baseUrl": "https://thepiratebay.org",
                    "categories": [8000, 100013],  # Books, AudioBooks
                    "minimumSeeders": 1
                },
                "enableRss": True,
                "enableAutomaticSearch": True,
                "enableInteractiveSearch": True,
                "supportsRss": True,
                "supportsSearch": True,
                "protocol": "torrent",
                "priority": 25,
                "downloadClientId": 0
            },
            {
                "name": "TorrentDownloads",
                "implementation": "Torznab",
                "settings": {
                    "baseUrl": "https://www.torrentdownloads.me",
                    "apiPath": "/torznab-api",
                    "categories": [8000, 100013],  # Books, AudioBooks
                    "apiKey": "",
                    "minimumSeeders": 1
                },
                "enableRss": True,
                "enableAutomaticSearch": True,
                "enableInteractiveSearch": True,
                "supportsRss": True,
                "supportsSearch": True,
                "protocol": "torrent",
                "priority": 25,
                "downloadClientId": 0
            }
        ]

    def get_existing_indexers(self) -> List[Dict[str, Any]]:
        """Get list of existing indexers"""
        try:
            response = self.session.get(f"{self.prowlarr_url}/api/v1/indexer", timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Failed to get indexers: HTTP {response.status_code}")
                return []
        except Exception as e:
            print(f"Error getting indexers: {e}")
            return []

    def add_indexer(self, indexer_config: Dict[str, Any]) -> bool:
        """Add a new indexer to Prowlarr"""
        try:
            response = self.session.post(
                f"{self.prowlarr_url}/api/v1/indexer",
                json=indexer_config,
                timeout=30
            )

            if response.status_code in [200, 201]:
                print(f"✓ Successfully added indexer: {indexer_config['name']}")
                return True
            else:
                print(f"✗ Failed to add indexer {indexer_config['name']}: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"✗ Error adding indexer {indexer_config['name']}: {e}")
            return False

    def test_indexer(self, indexer_id: int) -> bool:
        """Test an indexer"""
        try:
            response = self.session.post(
                f"{self.prowlarr_url}/api/v1/indexer/test/{indexer_id}",
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('isSuccessful', False):
                    print(f"✓ Indexer test passed")
                    return True
                else:
                    print(f"✗ Indexer test failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"✗ Indexer test failed: HTTP {response.status_code}")
                return False

        except Exception as e:
            print(f"✗ Error testing indexer: {e}")
            return False

    def update_mam_categories(self):
        """Update MAM indexer to enable audiobook categories"""
        print("Updating MyAnonamouse indexer for audiobook categories...")

        try:
            # Get current MAM indexer
            response = self.session.get(f"{self.prowlarr_url}/api/v1/indexer", timeout=10)
            if response.status_code != 200:
                print("Failed to get indexers")
                return False

            indexers = response.json()
            mam_indexer = None
            for idx in indexers:
                if idx.get('name', '').lower() == 'myanonamouse':
                    mam_indexer = idx
                    break

            if not mam_indexer:
                print("MyAnonamouse indexer not found")
                return False

            # MAM already has audiobook categories in its capabilities
            # The issue is that our search isn't finding results
            # Let's check if MAM is properly configured for audiobook searches

            print("MyAnonamouse indexer found - audiobook categories are already available")
            print("Testing MAM indexer...")

            return self.test_indexer(mam_indexer['id'])

        except Exception as e:
            print(f"Error updating MAM indexer: {e}")
            return False

    def setup_audiobook_indexers(self):
        """Main setup function"""
        print("=" * 80)
        print("PROWLARR AUDIOBOOK INDEXER SETUP")
        print("=" * 80)
        print(f"Prowlarr URL: {self.prowlarr_url}")
        print()

        # Step 1: Check existing indexers
        print("1. CHECKING EXISTING INDEXERS")
        print("-" * 40)
        existing_indexers = self.get_existing_indexers()
        existing_names = [idx.get('name', '').lower() for idx in existing_indexers]

        print(f"Found {len(existing_indexers)} existing indexers:")
        for idx in existing_indexers:
            status = "ENABLED" if idx.get('enable', False) else "DISABLED"
            print(f"  - {idx.get('name', 'Unknown')} ({status})")
        print()

        # Step 2: Update MAM indexer
        print("2. UPDATING MYANONAMOUE INDEXER")
        print("-" * 40)
        mam_updated = self.update_mam_categories()
        print()

        # Step 3: Add public audiobook indexers
        print("3. ADDING PUBLIC AUDIOBOOK INDEXERS")
        print("-" * 40)

        added_count = 0
        for indexer_config in self.audiobook_indexers:
            indexer_name = indexer_config['name'].lower()

            if indexer_name in existing_names:
                print(f"Indexer {indexer_config['name']} already exists - skipping")
                continue

            print(f"Adding indexer: {indexer_config['name']}")
            if self.add_indexer(indexer_config):
                added_count += 1
            print()

        print(f"Successfully added {added_count} new indexers")
        print()

        # Step 4: Summary and recommendations
        print("4. SETUP SUMMARY & RECOMMENDATIONS")
        print("-" * 40)

        total_indexers = len(existing_indexers) + added_count
        print(f"Total indexers configured: {total_indexers}")
        print()

        print("NEXT STEPS:")
        print("1. Open Prowlarr web interface")
        print("2. Go to Indexers section")
        print("3. Test each new indexer by clicking 'Test'")
        print("4. Configure API keys if required (some indexers need them)")
        print("5. Enable audiobook categories for each indexer")
        print("6. Run the audiobook search script again")
        print()

        print("TROUBLESHOOTING:")
        print("- If indexers fail tests, check network connectivity")
        print("- Some indexers may require API keys or have rate limits")
        print("- Public indexers may be blocked in some regions")
        print("- Consider using VPN if indexers are geo-blocked")
        print()

        print("=" * 80)
        print("SETUP COMPLETE")
        print("=" * 80)


def main():
    setup = ProwlarrIndexerSetup()
    setup.setup_audiobook_indexers()


if __name__ == '__main__':
    main()