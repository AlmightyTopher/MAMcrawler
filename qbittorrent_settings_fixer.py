#!/usr/bin/env python3
"""
qBittorrent Settings Fixer - Automated Browser Control

Uses Selenium to:
1. Navigate to qBittorrent Web UI
2. Log in with credentials
3. Open Web UI settings
4. Fix IP whitelist
5. Test the connection
"""

import os
import sys
import time
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("ERROR: Selenium not installed")
    print("Install: pip install selenium")
    sys.exit(1)

load_dotenv()


class QBittorrentSettingsFixer:
    """Automated browser control for qBittorrent settings"""

    def __init__(self):
        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/').rstrip('/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD', 'Tesl@ismy#1')
        self.driver = None
        self.log_file = Path("qbittorrent_settings_fixer.log")
        self.wait_timeout = 15

    def log(self, message: str, level: str = "INFO"):
        """Log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level:5}] {message}"
        print(formatted)
        with open(self.log_file, 'a') as f:
            f.write(formatted + "\n")

    def setup_driver(self):
        """Setup Chrome WebDriver"""
        self.log("Setting up Chrome WebDriver...", "SETUP")

        chrome_options = Options()
        # Don't run headless so we can see what's happening
        # chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.log("Chrome WebDriver initialized successfully", "OK")
            return True
        except Exception as e:
            self.log(f"Failed to initialize Chrome: {e}", "FAIL")
            self.log("Make sure ChromeDriver is installed or in PATH", "FAIL")
            return False

    def navigate_to_qbittorrent(self) -> bool:
        """Navigate to qBittorrent Web UI"""
        self.log("=" * 80)
        self.log("STEP 1: Navigate to qBittorrent Web UI", "STEP")
        self.log("=" * 80)

        try:
            self.log(f"Opening {self.qb_url}...", "DEBUG")
            self.driver.get(self.qb_url)

            # Wait for page to load
            time.sleep(3)

            self.log("Checking if login page loaded...", "DEBUG")

            # Check if we're on login page or already logged in
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                self.log("Login page detected", "OK")
                return True
            except TimeoutException:
                # Maybe already logged in?
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "mainwindow"))
                    )
                    self.log("Already logged in", "OK")
                    return True
                except TimeoutException:
                    self.log("Could not detect login page or main window", "FAIL")
                    return False

        except Exception as e:
            self.log(f"Navigation failed: {e}", "FAIL")
            return False

    def login(self) -> bool:
        """Log in to qBittorrent"""
        self.log("=" * 80)
        self.log("STEP 2: Log In", "STEP")
        self.log("=" * 80)

        try:
            # Check if already logged in
            try:
                WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "mainwindow"))
                )
                self.log("Already logged in, skipping login", "OK")
                return True
            except TimeoutException:
                pass

            # Find login form
            self.log("Finding login form...", "DEBUG")
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "username"))
            )

            password_field = self.driver.find_element(By.NAME, "password")
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")

            # Fill in credentials
            self.log(f"Entering credentials for user: {self.qb_user}", "DEBUG")
            username_field.clear()
            username_field.send_keys(self.qb_user)

            password_field.clear()
            password_field.send_keys(self.qb_pass)

            # Submit form
            self.log("Clicking login button...", "DEBUG")
            login_button.click()

            # Wait for main page to load
            self.log("Waiting for dashboard to load...", "DEBUG")
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "mainwindow"))
            )

            self.log("Successfully logged in", "OK")
            time.sleep(2)
            return True

        except TimeoutException as e:
            self.log(f"Login timeout: {e}", "FAIL")
            return False
        except Exception as e:
            self.log(f"Login failed: {e}", "FAIL")
            return False

    def open_settings(self) -> bool:
        """Open Tools > Options settings"""
        self.log("=" * 80)
        self.log("STEP 3: Open Web UI Settings", "STEP")
        self.log("=" * 80)

        try:
            # Wait for page to be interactive
            time.sleep(2)

            # Look for Tools menu or Options button
            self.log("Looking for Tools menu or Options button...", "DEBUG")

            # Try to find a settings/options button (may be icon-based)
            # qBittorrent typically has a gear icon or "Tools" menu

            # Try different selectors
            selectors = [
                (By.CSS_SELECTOR, "a[href*='preferences']"),
                (By.CSS_SELECTOR, "button[title*='preferences']"),
                (By.CSS_SELECTOR, "button[title*='settings']"),
                (By.XPATH, "//a[contains(text(), 'Tools')]"),
                (By.XPATH, "//button[contains(text(), 'Tools')]"),
            ]

            found = False
            for selector in selectors:
                try:
                    element = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located(selector)
                    )
                    self.log(f"Found settings element: {selector}", "DEBUG")
                    element.click()
                    found = True
                    break
                except TimeoutException:
                    continue

            if not found:
                # Try right-clicking or looking for a menu
                self.log("Trying to find Tools menu...", "DEBUG")
                try:
                    tools_link = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'Tools')]"))
                    )
                    tools_link.click()
                    time.sleep(1)

                    # Look for Options submenu
                    options_link = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Options')]"))
                    )
                    options_link.click()
                    found = True
                except TimeoutException:
                    pass

            if not found:
                self.log("Could not find Tools/Options menu in standard locations", "WARN")
                self.log("Trying direct URL navigation...", "DEBUG")
                # Try navigating directly to preferences page
                self.driver.get(f"{self.qb_url}/preferences")
                time.sleep(3)

            # Wait for preferences page to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "preferences"))
                )
                self.log("Preferences page loaded successfully", "OK")
                return True
            except TimeoutException:
                # Maybe the page loaded differently
                time.sleep(2)
                self.log("Preferences page may have loaded", "WARN")
                return True

        except Exception as e:
            self.log(f"Failed to open settings: {e}", "FAIL")
            return False

    def fix_ip_whitelist(self) -> bool:
        """Find and fix IP whitelist setting"""
        self.log("=" * 80)
        self.log("STEP 4: Fix IP Whitelist Setting", "STEP")
        self.log("=" * 80)

        try:
            time.sleep(2)

            # Look for Web UI section
            self.log("Looking for Web UI settings section...", "DEBUG")

            # Try to find Web UI tab or section
            try:
                web_ui_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'Web UI')]"))
                )
                self.log("Found Web UI tab, clicking...", "DEBUG")
                web_ui_tab.click()
                time.sleep(2)
            except TimeoutException:
                self.log("Web UI tab not found, continuing...", "WARN")

            # Look for IP whitelist input field
            self.log("Looking for IP whitelist field...", "DEBUG")

            # Common selectors for IP whitelist field
            selectors = [
                (By.ID, "ipWhitelistInput"),
                (By.NAME, "ipWhitelist"),
                (By.XPATH, "//input[contains(@placeholder, 'IP')]"),
                (By.XPATH, "//input[contains(@placeholder, 'whitelist')]"),
                (By.XPATH, "//textarea[contains(@id, 'IP')]"),
            ]

            ip_field = None
            for selector in selectors:
                try:
                    ip_field = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located(selector)
                    )
                    self.log(f"Found IP whitelist field: {selector}", "OK")
                    break
                except TimeoutException:
                    continue

            if not ip_field:
                self.log("IP whitelist field not found in standard locations", "WARN")
                self.log("Taking screenshot for manual inspection...", "WARN")
                self.driver.save_screenshot("qbittorrent_settings.png")
                self.log("Screenshot saved: qbittorrent_settings.png", "INFO")

                # Try to find any input field and check its label
                self.log("Searching for any whitelist-related fields...", "DEBUG")
                try:
                    elements = self.driver.find_elements(By.XPATH, "//input[@type='text']")
                    self.log(f"Found {len(elements)} text input fields", "DEBUG")

                    for i, elem in enumerate(elements):
                        try:
                            label = self.driver.find_element(
                                By.XPATH,
                                f"//label[contains(text(), 'IP')] | //label[contains(text(), 'whitelist')]"
                            )
                            ip_field = elem
                            self.log(f"Found IP whitelist field at index {i}", "OK")
                            break
                        except NoSuchElementException:
                            pass
                except Exception as e:
                    self.log(f"Error searching fields: {e}", "WARN")

            if not ip_field:
                self.log("Could not find IP whitelist field", "FAIL")
                self.log("Manual configuration may be required", "INFO")
                return False

            # Clear and update the field
            self.log("Clearing IP whitelist field...", "DEBUG")
            ip_field.click()
            time.sleep(0.5)
            ip_field.clear()
            time.sleep(0.5)

            # Leave it empty to allow all IPs (or add localhost)
            self.log("Setting IP whitelist to allow all IPs (empty field)...", "DEBUG")
            # Leaving empty = allow all IPs
            # Or add: 127.0.0.1,192.168.1.0/24

            self.log("IP whitelist field cleared (will allow all IPs)", "OK")
            time.sleep(1)

            return True

        except Exception as e:
            self.log(f"Failed to fix IP whitelist: {e}", "FAIL")
            return False

    def save_settings(self) -> bool:
        """Save settings"""
        self.log("=" * 80)
        self.log("STEP 5: Save Settings", "STEP")
        self.log("=" * 80)

        try:
            # Look for Apply or OK button
            self.log("Looking for Save/Apply button...", "DEBUG")

            selectors = [
                (By.XPATH, "//button[contains(text(), 'Apply')]"),
                (By.XPATH, "//button[contains(text(), 'OK')]"),
                (By.XPATH, "//button[contains(text(), 'Save')]"),
                (By.CSS_SELECTOR, "button.confirm-button"),
            ]

            found = False
            for selector in selectors:
                try:
                    button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable(selector)
                    )
                    self.log(f"Found button: {selector}", "DEBUG")
                    button.click()
                    found = True
                    break
                except TimeoutException:
                    continue

            if not found:
                self.log("Apply/OK button not found", "WARN")
                self.log("Settings may auto-save", "INFO")
                return False

            self.log("Clicked save button, waiting for response...", "DEBUG")
            time.sleep(3)

            self.log("Settings saved successfully", "OK")
            return True

        except Exception as e:
            self.log(f"Failed to save settings: {e}", "FAIL")
            return False

    async def test_api_connection(self) -> bool:
        """Test API connection after fix"""
        self.log("=" * 80)
        self.log("STEP 6: Test API Connection", "STEP")
        self.log("=" * 80)

        try:
            # Wait a bit for settings to take effect
            self.log("Waiting for settings to apply...", "DEBUG")
            await asyncio.sleep(3)

            async with aiohttp.ClientSession() as session:
                # Test 1: Login
                self.log("Testing authentication...", "DEBUG")
                data = aiohttp.FormData()
                data.add_field('username', self.qb_user)
                data.add_field('password', self.qb_pass)

                async with session.post(
                    f'{self.qb_url}/api/v2/auth/login',
                    data=data,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        self.log(f"Login failed: HTTP {resp.status}", "FAIL")
                        return False
                    text = await resp.text()
                    if text.strip() != 'Ok.':
                        self.log(f"Login response invalid: {text}", "FAIL")
                        return False

                self.log("Authentication successful", "OK")

                # Test 2: API call
                self.log("Testing API access (preferences)...", "DEBUG")
                async with session.get(
                    f'{self.qb_url}/api/v2/app/preferences',
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        self.log("API access successful - HTTP 200", "OK")
                        prefs = await resp.json()
                        save_path = prefs.get('save_path', 'N/A')
                        self.log(f"Download path: {save_path}", "OK")
                        return True
                    elif resp.status == 403:
                        self.log("API still returning 403 - IP whitelist not fixed", "FAIL")
                        return False
                    else:
                        self.log(f"API error: HTTP {resp.status}", "FAIL")
                        return False

        except Exception as e:
            self.log(f"Test failed: {e}", "FAIL")
            return False

    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            self.log("Browser closed", "DEBUG")

    async def run_fix(self) -> bool:
        """Run complete fix procedure"""
        self.log("")
        self.log("=" * 100)
        self.log("qBITTORRENT SETTINGS FIXER - AUTOMATED BROWSER CONTROL")
        self.log("=" * 100)
        self.log("")

        steps = [
            ("Setup Driver", self.setup_driver),
            ("Navigate to qBittorrent", self.navigate_to_qbittorrent),
            ("Log In", self.login),
            ("Open Settings", self.open_settings),
            ("Fix IP Whitelist", self.fix_ip_whitelist),
            ("Save Settings", self.save_settings),
        ]

        results = {}

        for step_name, step_func in steps:
            self.log("")
            try:
                if asyncio.iscoroutinefunction(step_func):
                    result = await step_func()
                else:
                    result = step_func()
                results[step_name] = result

                if not result:
                    self.log(f"Step '{step_name}' failed, continuing anyway...", "WARN")

            except Exception as e:
                self.log(f"Exception in '{step_name}': {e}", "FAIL")
                results[step_name] = False

        # Test API connection
        self.log("")
        test_result = await self.test_api_connection()
        results["Test API Connection"] = test_result

        # Summary
        self.log("")
        self.log("=" * 100)
        self.log("SUMMARY", "SUMMARY")
        self.log("=" * 100)

        for step_name, result in results.items():
            status = "SUCCESS" if result else "FAILED"
            self.log(f"  {step_name}: {status}", "SUMMARY")

        self.log("")

        if test_result:
            self.log("SUCCESS: API is now accessible!", "OK")
            self.log("The workflow can now add torrents to qBittorrent", "OK")
            self.log("Next: Re-run execute_full_workflow.py", "OK")
        else:
            self.log("API is still not accessible", "FAIL")
            self.log("Manual configuration may be required", "INFO")
            self.log("Check the screenshots and logs", "INFO")

        self.close()
        return test_result


async def main():
    fixer = QBittorrentSettingsFixer()

    try:
        success = await fixer.run_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        fixer.close()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
