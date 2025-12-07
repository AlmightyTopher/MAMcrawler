#!/usr/bin/env python3
"""
Debug MAM login to identify the issue
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv

load_dotenv()

def debug_mam_login():
    """Debug MAM login step by step"""

    mam_url = os.getenv('MAM_URL', 'https://www.myanonamouse.net')
    mam_user = os.getenv('MAM_USERNAME')
    mam_pass = os.getenv('MAM_PASSWORD')

    print(f"MAM URL: {mam_url}")
    print(f"MAM User: {mam_user}")
    print(f"MAM Pass: {'*' * len(mam_pass) if mam_pass else 'None'}")

    # Setup driver with visible browser for debugging
    options = Options()
    # Remove headless for debugging
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    try:
        print("1. Navigating to login page...")
        driver.get(f"{mam_url}/login.php")
        print(f"Current URL: {driver.current_url}")
        print(f"Page title: {driver.title}")

        print("2. Waiting for username field...")
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        print("Username field found")

        print("3. Filling credentials...")
        username_field.send_keys(mam_user)

        password_field = driver.find_element(By.NAME, "password")
        password_field.send_keys(mam_pass)

        print("4. Clicking submit...")
        submit_button = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        submit_button.click()

        print("5. Waiting for redirect...")
        WebDriverWait(driver, 10).until(
            lambda d: "login" not in d.current_url.lower()
        )

        print(f"Final URL: {driver.current_url}")
        print(f"Final title: {driver.title}")

        if "login" in driver.current_url.lower():
            print("ERROR: Still on login page - authentication failed")
            print("Page source:")
            print(driver.page_source[:1000])
        else:
            print("SUCCESS: Login successful")

    except Exception as e:
        print(f"ERROR: {e}")
        print(f"Current URL: {driver.current_url}")
        print("Page source:")
        print(driver.page_source[:1000])

    finally:
        input("Press Enter to close browser...")
        driver.quit()

if __name__ == '__main__':
    debug_mam_login()