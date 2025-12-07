import logging
import sys
import os
import json
from datetime import datetime

# Add current dir to path
sys.path.append(os.getcwd())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DirectStatsTest")

def test_direct_crawler():
    print("Importing SeleniumMAMCrawler...")
    try:
        from mam_selenium_crawler import SeleniumMAMCrawler
        from selenium_integration import SeleniumIntegrationConfig
    except ImportError as e:
        print(f"Failed to import: {e}")
        return

    print("Initializing Crawler...")
    params = SeleniumIntegrationConfig.get_crawler_params()
    # Force headless for testing if not already
    params['headless'] = True
    
    crawler = SeleniumMAMCrawler(**params)
    
    try:
        print("Running get_user_stats()...")
        stats = crawler.get_user_stats()
        
        if stats:
            print("\nSUCCESS! Stats received:")
            print(json.dumps(stats, indent=2, default=str))
        else:
            print("\nFAILURE: No stats returned (None)")
            
    except Exception as e:
        print(f"\nEXCEPTION: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Cleaning up...")
        if crawler.driver:
            crawler.driver.quit()

if __name__ == "__main__":
    test_direct_crawler()
