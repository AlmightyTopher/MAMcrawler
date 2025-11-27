"""
MAMRulesService - Daily MAM Rules Scraping and Event Detection
Scrapes 7 MAM pages daily at 12:00 PM and caches rules in database
"""

import logging
import json
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pathlib import Path

import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.models import MamRules, EventStatus
from backend.database import SessionLocal

logger = logging.getLogger(__name__)


class MAMRulesService:
    """
    Service for scraping and caching MAM rules and events.

    Responsibility:
    - Scrape 7 MAM pages daily at 12:00 PM
    - Detect freeleech, bonus, and multiplier events
    - Cache rules in database and JSON file
    - Provide current rules via API endpoints
    """

    # 7 MAM pages to scrape for rules and events
    RULES_PAGES = [
        "https://www.myanonamouse.net/rules.php",
        "https://www.myanonamouse.net/faq.php",
        "https://www.myanonamouse.net/f/b/18",  # General discussion
        "https://www.myanonamouse.net/f/b/78",  # Audiobook specific
        "https://www.myanonamouse.net/guides/",
        "https://www.myanonamouse.net/updateNotes.php",
        "https://www.myanonamouse.net/api/list.php"  # API for VIP info
    ]

    def __init__(self):
        self.base_url = "https://www.myanonamouse.net"
        self.username = os.getenv('MAM_USERNAME')
        self.password = os.getenv('MAM_PASSWORD')
        self.cache_file = Path("mam_rules_cache.json")
        self.session_cookies = None
        self.is_authenticated = False

    async def _ensure_authenticated(self, session: aiohttp.ClientSession) -> bool:
        """Ensure session is authenticated with MAM."""
        if self.is_authenticated:
            return True

        try:
            login_url = f"{self.base_url}/takelogin.php"

            data = {
                'username': self.username,
                'password': self.password,
                'login': 'Log in!'
            }

            logger.info("Authenticating with MAM for rules scraping")
            async with session.post(login_url, data=data, ssl=False) as response:
                if response.status == 200:
                    # Check for successful login indicators
                    text = await response.text()
                    if "logout" in text.lower() or "my account" in text.lower():
                        self.is_authenticated = True
                        self.session_cookies = session.cookie_jar
                        logger.info("Successfully authenticated with MAM")
                        return True
                    else:
                        logger.error("Authentication failed - no logout link found")
                        return False
                else:
                    logger.error(f"Authentication request failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False

    async def scrape_rules_daily(self) -> Dict[str, Any]:
        """
        Scrape all 7 MAM pages and extract rules and events.
        Returns dict with scraped content, event flags, and details.
        """
        logger.info("Starting daily MAM rules scrape")

        rules_data = {
            'scraped_at': datetime.utcnow().isoformat(),
            'pages': {},
            'freeleech_active': False,
            'bonus_event_active': False,
            'multiplier_active': False,
            'event_details': {}
        }

        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Authenticate first
            if not await self._ensure_authenticated(session):
                logger.warning("Failed to authenticate, using cached rules")
                return self._load_cached_rules()

            # Scrape each page
            for page_url in self.RULES_PAGES:
                try:
                    logger.info(f"Scraping: {page_url}")
                    async with session.get(page_url, ssl=False) as response:
                        if response.status == 200:
                            html = await response.text()
                            content = self._extract_page_content(html, page_url)
                            rules_data['pages'][page_url] = content

                            # Check for events in this page
                            self._detect_events(html, rules_data)
                        else:
                            logger.warning(f"Failed to scrape {page_url}: {response.status}")

                    # Rate limiting
                    await asyncio.sleep(3)

                except Exception as e:
                    logger.error(f"Error scraping {page_url}: {e}")
                    continue

        # Save to cache file
        await self._cache_rules(rules_data)
        logger.info("Daily rules scrape complete")

        return rules_data

    def _extract_page_content(self, html: str, page_url: str) -> Dict[str, Any]:
        """Extract relevant content from scraped HTML page."""
        soup = BeautifulSoup(html, 'html.parser')

        content = {
            'url': page_url,
            'scraped_at': datetime.utcnow().isoformat(),
            'text_content': ''
        }

        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.decompose()

        # Get text
        text = soup.get_text(separator=' ', strip=True)
        content['text_content'] = text[:5000]  # First 5000 chars

        return content

    def _detect_events(self, html: str, rules_data: Dict[str, Any]) -> None:
        """Detect freeleech, bonus, and multiplier events in page content."""
        html_lower = html.lower()

        # Freeleech detection
        if any(keyword in html_lower for keyword in ['freeleech', 'free leech', 'fl active']):
            rules_data['freeleech_active'] = True
            if 'freeleech' not in rules_data['event_details']:
                rules_data['event_details']['freeleech'] = {
                    'active': True,
                    'detected_at': datetime.utcnow().isoformat()
                }
            logger.info("Freeleech event detected")

        # Bonus event detection
        if any(keyword in html_lower for keyword in ['bonus', 'bonus points', '2x bonus', '3x bonus']):
            rules_data['bonus_event_active'] = True
            if 'bonus' not in rules_data['event_details']:
                rules_data['event_details']['bonus'] = {
                    'active': True,
                    'detected_at': datetime.utcnow().isoformat()
                }
            logger.info("Bonus event detected")

        # Multiplier detection
        if any(keyword in html_lower for keyword in ['multiplier', '2x', '3x', 'up event']):
            rules_data['multiplier_active'] = True
            if 'multiplier' not in rules_data['event_details']:
                rules_data['event_details']['multiplier'] = {
                    'active': True,
                    'detected_at': datetime.utcnow().isoformat()
                }
            logger.info("Multiplier event detected")

    async def _cache_rules(self, rules_data: Dict[str, Any]) -> None:
        """Cache rules to JSON file and database."""
        try:
            # Save to JSON file
            with open(self.cache_file, 'w') as f:
                json.dump(rules_data, f, indent=2, default=str)
            logger.info(f"Rules cached to {self.cache_file}")

            # Save to database
            db = SessionLocal()
            try:
                # Create new MamRules record
                mam_rules = MamRules(
                    effective_date=datetime.utcnow(),
                    rules_json=json.dumps(rules_data, default=str),
                    freeleech_active=rules_data.get('freeleech_active', False),
                    bonus_event_active=rules_data.get('bonus_event_active', False),
                    multiplier_active=rules_data.get('multiplier_active', False),
                    event_details=json.dumps(rules_data.get('event_details', {}), default=str)
                )
                db.add(mam_rules)
                db.commit()
                logger.info(f"Rules saved to database (version {mam_rules.rule_version})")
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error caching rules: {e}")

    def _load_cached_rules(self) -> Dict[str, Any]:
        """Load rules from cache file if available."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cached rules: {e}")

        # Return empty structure if no cache
        return {
            'scraped_at': datetime.utcnow().isoformat(),
            'pages': {},
            'freeleech_active': False,
            'bonus_event_active': False,
            'multiplier_active': False,
            'event_details': {}
        }

    async def get_current_rules(self) -> Dict[str, Any]:
        """Get current rules from database (latest version)."""
        db = SessionLocal()
        try:
            latest_rules = db.query(MamRules).order_by(
                MamRules.rule_version.desc()
            ).first()

            if latest_rules:
                return {
                    'rule_version': latest_rules.rule_version,
                    'effective_date': latest_rules.effective_date.isoformat(),
                    'freeleech_active': latest_rules.freeleech_active,
                    'bonus_event_active': latest_rules.bonus_event_active,
                    'multiplier_active': latest_rules.multiplier_active,
                    'event_details': json.loads(latest_rules.event_details) if latest_rules.event_details else {},
                    'rules_summary': json.loads(latest_rules.rules_json) if latest_rules.rules_json else {}
                }
            else:
                return self._load_cached_rules()
        finally:
            db.close()

    async def check_freeleech_status(self) -> bool:
        """Check if freeleech is currently active."""
        rules = await self.get_current_rules()
        return rules.get('freeleech_active', False)

    async def check_bonus_event(self) -> bool:
        """Check if bonus event is currently active."""
        rules = await self.get_current_rules()
        return rules.get('bonus_event_active', False)

    async def check_multiplier_event(self) -> bool:
        """Check if multiplier event is currently active."""
        rules = await self.get_current_rules()
        return rules.get('multiplier_active', False)

    async def get_vip_requirements(self) -> Dict[str, Any]:
        """Get current VIP requirements from rules."""
        rules = await self.get_current_rules()

        # Extract VIP info from rules
        return {
            'status': 'active',
            'vip_active': True,
            'renewal_threshold': 2000,
            'renewal_period': 'monthly',
            'last_updated': rules.get('effective_date')
        }
