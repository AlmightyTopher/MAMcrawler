import asyncio
import logging
import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestStats")

async def test_stats():
    print("Importing selenium_integration...")
    try:
        from selenium_integration import get_mam_user_stats
    except ImportError as e:
        print(f"Failed to import: {e}")
        return

    print("Calling get_mam_user_stats()...")
    try:
        stats = await get_mam_user_stats()
        if stats:
            print("\nSUCCESS! Stats received:")
            print(f"Ratio: {stats.get('ratio')}")
            print(f"Shorthand: {stats.get('shorthand')}")
            print(f"Raw Data Keys: {list(stats.get('raw_data', {}).keys())}")
        else:
            print("\nFAILURE: No stats returned (None)")
    except Exception as e:
        print(f"\nEXCEPTION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_stats())
