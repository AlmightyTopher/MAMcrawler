import os
import time
import logging
import asyncio
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import qbittorrentapi
from backend.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class MAMSeleniumService:
    """
    Service for crawling MyAnonamouse using Selenium.
    Ported from execute_real_workflow_final_real.py
    """

    def __init__(self):
        self.mam_url = settings.MAM_URL if hasattr(settings, 'MAM_URL') else 'https://www.myanonamouse.net'
        self.mam_user = settings.MAM_USERNAME
        self.mam_pass = settings.MAM_PASSWORD
        self.driver = None

    def setup_driver(self):
        """Setup Selenium WebDriver"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            self.driver = webdriver.Chrome(options=options)
            logger.info("Selenium WebDriver initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            self.driver = None
            return False

    def login_to_mam(self):
        """Login to MAM using working approach"""
        if not self.driver:
            if not self.setup_driver():
                return False

        try:
            logger.info("Navigating to MAM login page...")
            self.driver.get(f"{self.mam_url}/tor/login.php")
            time.sleep(2)

            # Find and fill login form
            username_field = self.driver.find_element(By.NAME, 'username')
            password_field = self.driver.find_element(By.NAME, 'password')
            try:
                login_button = self.driver.find_element(By.XPATH, "//input[@type='submit' or @value='Login']")
            except:
                # Fallback selector
                login_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit']")

            username_field.clear()
            username_field.send_keys(self.mam_user)
            password_field.clear()
            password_field.send_keys(self.mam_pass)

            logger.info("Submitting login form...")
            login_button.click()
            time.sleep(3)

            # Check if login was successful
            page_source = self.driver.page_source.lower()
            if 'logout' in page_source or 'my account' in page_source:
                logger.info("MAM login successful")
                return True
            else:
                logger.warning("MAM login may have failed - checking page content")
                logger.info(f"Current URL: {self.driver.current_url}")
                return False

        except Exception as e:
            logger.error(f"MAM login error: {e}")
            return False

    def search_mam(self, query: str) -> List[Dict]:
        """Search MAM for a book"""
        if not self.driver:
            self.login_to_mam()

        try:
            # Audiobooks category = 14
            search_url = f"{self.mam_url}/tor/browse.php?search={query}&cat[]=14"
            self.driver.get(search_url)

            # Wait for table
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.torrent_table"))
                )
            except:
                logger.warning(f"Timeout waiting for results for '{query}'")
                return []

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            rows = soup.find_all('tr', {'class': lambda x: x and ('table_dark' in x or 'table_light' in x)})

            results = []
            for row in rows[:5]:  # Limit to top 5 results
                cols = row.find_all('td')
                if len(cols) >= 4:
                    title_link = cols[1].find('a')
                    if title_link:
                        title = title_link.text.strip()
                        magnet_link = cols[3].find('a', href=lambda x: x and 'magnet:' in x)
                        if magnet_link:
                            magnet = magnet_link['href']
                            results.append({
                                'title': title,
                                'magnet': magnet,
                                'query': query
                            })

            logger.info(f"Found {len(results)} MAM results for '{query}'")
            return results

        except Exception as e:
            logger.error(f"MAM search failed for '{query}': {e}")
            return []

    def get_page_source(self, url: str) -> Optional[str]:
        """Navigate to a URL and return page source"""
        if not self.driver:
            if not self.login_to_mam():
                return None
        
        try:
            logger.info(f"Navigating to {url}")
            self.driver.get(url)
            # Wait for content
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "mainBody"))
            )
            return self.driver.page_source
        except Exception as e:
            logger.error(f"Failed to fetch page {url}: {e}")
            return None

    def queue_to_qbittorrent(self, magnet: str, title: str):
        """Queue torrent to qBittorrent"""
        try:
            # Use settings for QB connection
            qb = qbittorrentapi.Client(
                host=f"{settings.QB_HOST}:{settings.QB_PORT}",
                username=settings.QB_USERNAME,
                password=settings.QB_PASSWORD
            )
            qb.auth_log_in()

            qb.torrents_add(urls=[magnet], category='audiobooks', tags=['mam', 'automated'])
            logger.info(f"Queued '{title}' to qBittorrent")
            return True
        except Exception as e:
            logger.error(f"Failed to queue '{title}': {e}")
            return False

    def close(self):
        """Close Selenium driver safely"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium driver closed")
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None

    async def run_search_and_download(self, books_to_find: List[Dict]) -> List[Dict]:
        """Run MAM crawling and downloading for a list of books"""
        try:
            if not self.setup_driver():
                return []

            if not self.login_to_mam():
                return []

            downloaded = []
            for book in books_to_find:
                title = book.get('title', '')
                author = book.get('author', '')
                query = f"{title} {author}".strip()
                
                logger.info(f"Searching for: {query}")
                results = self.search_mam(query)

                if results:
                    # Take the first result
                    result = results[0]
                    if self.queue_to_qbittorrent(result['magnet'], result['title']):
                        # Update DB if ID exists
                        db_id = book.get('db_id')
                        if db_id:
                            try:
                                from backend.database import get_db_context
                                from backend.models.download import Download
                                with get_db_context() as db:
                                    dl = db.query(Download).filter(Download.id == db_id).first()
                                    if dl:
                                        dl.status = "downloading"
                                        dl.magnet_link = result['magnet']
                                        dl.qbittorrent_status = "downloading"
                                        db.commit()
                                        logger.info(f"Updated status for DB ID {db_id} to downloading")
                            except Exception as e:
                                logger.error(f"Failed to update DB status: {e}")

                        downloaded.append({
                            'book': book,
                            'mam_result': result
                        })
                
                # Respect VIP rules / Rate limits - wait between searches
                await asyncio.sleep(5)

            return downloaded

        finally:
            self.close()
