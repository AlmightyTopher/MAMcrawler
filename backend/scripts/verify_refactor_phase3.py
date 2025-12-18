
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Load Env
from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env")))

from backend.services.discovery_service import DiscoveryService
from backend.services.mam_selenium_service import MAMSeleniumService

async def verify():
    # 1. Check Discovery Service
    ds = DiscoveryService()
    print("Loading download list from DB...")
    items = ds.load_download_list()
    print(f"Found {len(items)} items.")
    if items:
        print(f"Sample item: {items[0]}")
    
    # 2. Check Selenium Service setup (dry run)
    ms = MAMSeleniumService()
    print(f"MAM Service init. URL: {ms.mam_url}")

if __name__ == "__main__":
    asyncio.run(verify())
