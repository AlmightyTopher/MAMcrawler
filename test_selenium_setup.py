#!/usr/bin/env python3
"""Test if Selenium/ChromeDriver is properly set up"""

import sys
import os

print("=" * 120)
print("SELENIUM/CHROMEDRIVER SETUP TEST")
print("=" * 120)
print()

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    print("✓ Selenium module imported successfully")
    print()

    # Test ChromeDriver
    print("Attempting to start ChromeDriver...")
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)

    try:
        driver = webdriver.Chrome(options=opts)
        print("✓ ChromeDriver started successfully")

        # Test basic navigation
        driver.get("https://www.google.com")
        print("✓ Successfully navigated to google.com")

        # Check page title
        title = driver.title
        print(f"✓ Page title: {title}")

        driver.quit()
        print("✓ ChromeDriver closed")
        print()
        print("=" * 120)
        print("SELENIUM SETUP: OK")
        print("=" * 120)
        print()
        print("You can now run: python mam_selenium_crawler.py")
        print()

    except Exception as e:
        print(f"✗ ChromeDriver error: {e}")
        print()
        print("INSTALLATION INSTRUCTIONS:")
        print("-" * 120)
        print()
        print("Option 1: Use webdriver-manager (automatic)")
        print("  pip install webdriver-manager")
        print("  Then modify mam_selenium_crawler.py to use:")
        print("    from webdriver_manager.chrome import ChromeDriverManager")
        print("    service = Service(ChromeDriverManager().install())")
        print("    driver = webdriver.Chrome(service=service, options=chrome_options)")
        print()
        print("Option 2: Download ChromeDriver manually")
        print("  1. Get your Chrome version: chrome://version/")
        print("  2. Download matching ChromeDriver from: https://chromedriver.chromium.org/")
        print("  3. Add to PATH or specify in code")
        print()
        sys.exit(1)

except ImportError as e:
    print(f"✗ Import error: {e}")
    print()
    print("Please install Selenium:")
    print("  pip install selenium")
    sys.exit(1)
