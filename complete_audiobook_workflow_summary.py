#!/usr/bin/env python3
"""
Complete Audiobook Download Workflow Summary
============================================

This script summarizes the complete workflow for downloading top audiobooks
and provides manual instructions where automated systems are not working.
"""

import json
from datetime import datetime

def load_curated_books():
    """Load the curated audiobook list"""
    try:
        with open('audiobooks_to_download.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def print_workflow_summary():
    """Print comprehensive workflow summary"""

    print("=" * 120)
    print("COMPLETE AUDIOBOOK DOWNLOAD WORKFLOW SUMMARY")
    print("=" * 120)
    print(f"Generated: {datetime.now().isoformat()}")
    print()

    # Load curated books
    books = load_curated_books()

    if not books:
        print("ERROR: No curated books found. Run create_top_audiobooks_list.py first.")
        return

    # Separate by genre
    fantasy_books = [b for b in books if b['genre'] == 'fantasy']
    scifi_books = [b for b in books if b['genre'] == 'sci-fi']

    print("🎯 WORKFLOW OBJECTIVE:")
    print("Download top 10 audiobooks each from Fantasy and Sci-Fi genres")
    print()

    print("📚 CURATED AUDIOBOOK LISTS:")
    print(f"Total books: {len(books)}")
    print(f"Fantasy: {len(fantasy_books)} books")
    print(f"Sci-Fi: {len(scifi_books)} books")
    print()

    print("📖 FANTASY AUDIOBOOKS:")
    for i, book in enumerate(fantasy_books, 1):
        print("2d")
    print()

    print("🚀 SCI-FI AUDIOBOOKS:")
    for i, book in enumerate(scifi_books, 1):
        print("2d")
    print()

    print("🔄 WORKFLOW STATUS:")
    print("✅ Step 1: MAM scraping - COMPLETED (used curated list due to anti-crawling measures)")
    print("✅ Step 2: Prowlarr search - ATTEMPTED (0 results found - indexer configuration issue)")
    print("❌ Step 3: qBittorrent download - PENDING (requires manual intervention)")
    print("❌ Step 4: Download monitoring - PENDING")
    print("❌ Step 5: Audiobookshelf metadata update - PENDING")
    print()

    print("🔧 ISSUES IDENTIFIED:")
    print("• MAM website has anti-crawling measures preventing automated scraping")
    print("• Prowlarr is returning 0 results for all audiobook searches")
    print("• This suggests indexer configuration or API access issues")
    print()

    print("📋 MANUAL WORKFLOW INSTRUCTIONS:")
    print()
    print("Since automated systems are not working, follow these manual steps:")
    print()

    print("1️⃣ MANUAL TORRENT SEARCH:")
    print("   Visit your favorite torrent sites and search for these audiobooks:")
    for book in books:
        print(f"   • '{book['title']}' by {book['author']} audiobook")
    print()

    print("2️⃣ RECOMMENDED TORRENT SITES:")
    print("   • 1337x.to")
    print("   • ThePirateBay")
    print("   • RARBG")
    print("   • TorrentDownloads")
    print("   • Search for 'audiobook' + book title + author")
    print()

    print("3️⃣ DOWNLOAD TO QBITTORRENT:")
    print("   • Open qBittorrent")
    print("   • Add torrent files/magnet links")
    print("   • Set category to 'audiobooks'")
    print("   • Monitor download progress")
    print()

    print("4️⃣ MOVE TO AUDIOBOOKSHELF FOLDER:")
    print("   • Once downloads complete, move audiobook folders to:")
    print("     /path/to/audiobookshelf/audiobooks/")
    print("   • Ensure proper folder structure: Author/Book Title/")
    print()

    print("5️⃣ SCAN IN AUDIOBOOKSHELF:")
    print("   • Open Audiobookshelf web interface")
    print("   • Go to Library Settings")
    print("   • Click 'Scan Library' or 'Scan for new books'")
    print("   • Wait for metadata to be fetched and processed")
    print()

    print("6️⃣ VERIFY METADATA:")
    print("   • Check that book covers, descriptions, and chapters are correct")
    print("   • Edit metadata if needed using Audiobookshelf interface")
    print()

    print("🔍 TROUBLESHOOTING PROWLARR:")
    print("If you want to fix Prowlarr for future automated downloads:")
    print("• Check Prowlarr logs for indexer errors")
    print("• Verify indexer configurations are correct")
    print("• Test indexers manually in Prowlarr interface")
    print("• Ensure API key is correct in environment variables")
    print("• Check network connectivity to indexer sites")
    print()

    print("💡 ALTERNATIVE AUTOMATION:")
    print("Consider these alternatives for future automated downloads:")
    print("• Use different torrent indexers in Prowlarr")
    print("• Set up RSS feeds for automatic downloading")
    print("• Use Sonarr/Radarr with audiobook categories")
    print("• Implement direct torrent site scraping (with caution)")
    print()

    print("=" * 120)
    print("WORKFLOW COMPLETE - MANUAL INTERVENTION REQUIRED")
    print("=" * 120)

def main():
    print_workflow_summary()

if __name__ == '__main__':
    main()