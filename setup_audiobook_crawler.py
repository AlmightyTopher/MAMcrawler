"""
Quick setup and first-run script for audiobook catalog crawler.
Guides user through initial setup and configuration.
"""

import asyncio
import os
import sys
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed."""
    required = [
        'crawl4ai',
        'beautifulsoup4',
        'lxml',
        'qbittorrent-api'
    ]

    missing = []

    for package in required:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - NOT INSTALLED")
            missing.append(package)

    return missing


def check_env_file():
    """Check if .env file exists and has qBittorrent settings."""
    env_path = Path('.env')

    if not env_path.exists():
        print("\n⚠️  .env file not found")
        print("Creating from .env.example...")

        example_path = Path('.env.example')
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
            print("✅ Created .env file")
            print("💡 Edit .env to add your qBittorrent credentials")
        else:
            print("❌ .env.example not found")
            print("💡 Create .env manually with QB_HOST, QB_PORT, QB_USERNAME, QB_PASSWORD")
        return False

    # Check for qBittorrent settings
    with open(env_path, 'r') as f:
        content = f.read()

    has_qb_settings = all(key in content for key in ['QB_HOST', 'QB_PORT', 'QB_USERNAME', 'QB_PASSWORD'])

    if has_qb_settings:
        print("✅ .env file exists with qBittorrent settings")
        return True
    else:
        print("⚠️  .env file missing qBittorrent settings")
        print("💡 Add QB_HOST, QB_PORT, QB_USERNAME, QB_PASSWORD to .env")
        return False


def check_qbittorrent():
    """Check if qBittorrent is running and Web UI is accessible."""
    try:
        import qbittorrentapi
        from dotenv import load_dotenv

        load_dotenv()

        qb_host = os.getenv('QB_HOST', 'localhost')
        qb_port = os.getenv('QB_PORT', '8080')
        qb_username = os.getenv('QB_USERNAME', 'admin')
        qb_password = os.getenv('QB_PASSWORD', 'adminadmin')

        qbt_client = qbittorrentapi.Client(
            host=qb_host,
            port=qb_port,
            username=qb_username,
            password=qb_password
        )

        qbt_client.auth_log_in()
        print(f"✅ qBittorrent connected at {qb_host}:{qb_port}")
        return True

    except ImportError:
        print("⚠️  qbittorrent-api not installed (optional)")
        return None
    except Exception as e:
        print(f"⚠️  qBittorrent not accessible: {e}")
        print("💡 Enable Web UI in qBittorrent: Tools → Options → Web UI")
        return False


async def run_discovery():
    """Run initial discovery of audiobook catalog."""
    print("\n" + "="*70)
    print("🔍 RUNNING INITIAL DISCOVERY")
    print("="*70)
    print("This will:")
    print("  - Navigate to the audiobook catalog website")
    print("  - Extract available genres and timespans")
    print("  - Save screenshots for verification")
    print("  - Cache filters for fast queries")
    print()

    proceed = input("Run discovery now? (y/n): ").strip().lower()

    if proceed == 'y':
        try:
            from audiobook_catalog_crawler import AudiobookCatalogCrawler

            crawler = AudiobookCatalogCrawler()
            result = await crawler.discover_site_structure()

            if result.get('success'):
                print("\n✅ DISCOVERY COMPLETE!")
                print("\nNext steps:")
                print("1. Review catalog_cache/audiobooks_page.png")
                print("2. Check catalog_cache/genres.json and timespans.json")
                print("3. Run: python audiobook_query.py")
                return True
            else:
                print("\n❌ Discovery failed")
                print(f"Error: {result.get('error')}")
                return False

        except Exception as e:
            print(f"\n❌ Error during discovery: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("\nSkipping discovery. You can run it later with:")
        print("  python audiobook_catalog_crawler.py")
        return None


async def main():
    """Main setup flow."""
    print("="*70)
    print("📚 AUDIOBOOK CATALOG CRAWLER - SETUP")
    print("="*70)
    print()

    # Step 1: Check dependencies
    print("1️⃣  Checking dependencies...")
    print("-" * 70)
    missing = check_dependencies()

    if missing:
        print(f"\n❌ Missing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)

    print("\n✅ All dependencies installed")

    # Step 2: Check .env
    print("\n2️⃣  Checking .env configuration...")
    print("-" * 70)
    check_env_file()

    # Step 3: Check qBittorrent (optional)
    print("\n3️⃣  Checking qBittorrent connection (optional)...")
    print("-" * 70)
    qb_status = check_qbittorrent()

    if qb_status is None:
        print("\n💡 qBittorrent integration is optional")
        print("   You can still use the crawler to discover and query audiobooks")

    # Step 4: Run discovery
    print("\n4️⃣  Initial discovery...")
    print("-" * 70)

    discovery_result = await run_discovery()

    # Summary
    print("\n" + "="*70)
    print("📋 SETUP SUMMARY")
    print("="*70)

    print("\n✅ Setup complete!")
    print("\nWhat to do next:")
    print("\n1. Interactive mode:")
    print("   python audiobook_query.py")
    print("\n2. Command-line mode:")
    print("   python audiobook_query.py refresh       # Refresh filters")
    print("   python audiobook_query.py genres        # Show genres")
    print("   python audiobook_query.py timespans     # Show timespans")
    print("   python audiobook_query.py query 1 2     # Query genre #1, timespan #2")

    print("\n3. Read the documentation:")
    print("   AUDIOBOOK_CATALOG_README.md")

    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(main())
