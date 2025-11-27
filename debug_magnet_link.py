#!/usr/bin/env python3
"""
Debug torrent page to find magnet link location
"""

import logging
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize driver
chrome_options = ChromeOptions()
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
chrome_options.add_argument('--disable-images')

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    # Navigate to a torrent page
    torrent_url = "https://www.myanonamouse.net/t/1198735"
    logger.info(f"Navigating to {torrent_url}")
    driver.get(torrent_url)
    time.sleep(4)

    # Save page source
    page_source = driver.page_source
    with open("torrent_page_debug.html", "w", encoding="utf-8") as f:
        f.write(page_source)

    logger.info("Saved torrent page to torrent_page_debug.html")

    # Search for magnet links
    logger.info("\nSearching for magnet links...")

    # Try 1: Direct magnet link
    try:
        magnet_elems = driver.find_elements(By.XPATH, "//a[contains(@href, 'magnet:')]")
        logger.info(f"Found {len(magnet_elems)} magnet links with XPath 1")
        for elem in magnet_elems[:3]:
            logger.info(f"  {elem.get_attribute('href')[:100]}...")
    except:
        logger.info("XPath 1 failed")

    # Try 2: Download buttons
    try:
        download_btns = driver.find_elements(By.XPATH, "//a[contains(@class, 'download')]")
        logger.info(f"Found {len(download_btns)} download buttons")
        for btn in download_btns[:3]:
            logger.info(f"  {btn.get_attribute('href')[:100]}...")
            logger.info(f"  Text: {btn.text}")
    except:
        logger.info("XPath 2 failed")

    # Try 3: Look for magnet in all links
    try:
        all_links = driver.find_elements(By.TAG_NAME, "a")
        magnet_links = [link for link in all_links if "magnet" in link.get_attribute('href').lower()]
        logger.info(f"Found {len(magnet_links)} links with 'magnet' in href")
        for link in magnet_links[:3]:
            logger.info(f"  {link.get_attribute('href')[:100]}...")
    except:
        logger.info("XPath 3 failed")

    # Try 4: Look for download link
    try:
        dl_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Download')]")
        logger.info(f"Found 'Download' text link: {dl_link.get_attribute('href')}")
    except:
        logger.info("Download link not found")

finally:
    driver.quit()
