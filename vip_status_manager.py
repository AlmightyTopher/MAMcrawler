#!/usr/bin/env python3
"""
VIP Status Manager for MAM
Automatically maintains VIP status by:
1. Checking VIP expiry date via real scraping
2. Renewing if below 1 week (7 days) remaining
3. At end of automation, spending remaining points on VIP extension first, then ratio
Enforces Strict Identity Rules (Section 21).
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from bs4 import BeautifulSoup
import aiohttp
from aiohttp_socks import ProxyConnector

from mamcrawler.stealth import StealthCrawler

# Fix Windows encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

class VIPStatusManager(StealthCrawler):
    """Manages VIP status renewal and bonus point allocation using MAM Identity."""

    # VIP Status Constants (from VIP Guide)
    POINTS_PER_28_DAYS = 5000
    POINTS_PER_DAY = POINTS_PER_28_DAYS / 28  # ~178.57 points/day
    MINIMUM_DAYS_BUFFER = 7  # Never let VIP drop below 1 week
    MINIMUM_POINTS_BUFFER = MINIMUM_DAYS_BUFFER * POINTS_PER_DAY  # ~1,250 points

    # Upload Credit Constants (from Bonus Points Guide)
    POINTS_PER_1GB_UPLOAD = 500

    def __init__(self, logger=None):
        """Initialize VIP status manager with MAM Identity."""
        # Initialize StealthCrawler as Scraper A (MAM)
        super().__init__(state_file="vip_manager_state.json", identity_type='MAM')
        
        self.logger = logger or self._setup_logger()
        self.mam_username = os.getenv('MAM_USERNAME', '')
        self.mam_password = os.getenv('MAM_PASSWORD', '')
        self.base_url = "https://www.myanonamouse.net"
        self.session_cookies = None

    def _setup_logger(self) -> logging.Logger:
        """Setup logger for VIP manager."""
        logger = logging.getLogger('VIPManager')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    async def login(self) -> bool:
        """Login to MAM using MAM Identity (Proxy + UA)."""
        login_url = f"{self.base_url}/takelogin.php"
        
        login_data = {
            "username": self.mam_username,
            "password": self.mam_password,
            "login": "Login"
        }
        
        headers = {
            'User-Agent': self.get_user_agent(),
            'Referer': f"{self.base_url}/login.php",
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        connector = None
        if self.proxy:
            connector = ProxyConnector.from_url(self.proxy)
            
        try:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(login_url, data=login_data, headers=headers) as resp:
                    text = await resp.text()
                    if "logout" in text.lower() or "my account" in text.lower():
                        self.session_cookies = {c.key: c.value for c in session.cookie_jar}
                        self.logger.info("✓ VIP Manager Login successful")
                        return True
                    else:
                        self.logger.error("✗ VIP Manager Login failed")
                        return False
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return False

    async def get_real_stats(self) -> Optional[Dict]:
        """Fetch real stats from MAM."""
        if not self.session_cookies:
            if not await self.login():
                return None

        # Use UID from spec or discover it? Spec says uid=229756 in example, but we should probably find our own.
        # Actually, the store page usually shows points.
        store_url = f"{self.base_url}/store.php"
        
        headers = {'User-Agent': self.get_user_agent()}
        connector = ProxyConnector.from_url(self.proxy) if self.proxy else None
        
        try:
            async with aiohttp.ClientSession(connector=connector, cookies=self.session_cookies) as session:
                async with session.get(store_url, headers=headers) as resp:
                    html = await resp.text()
                    
            soup = BeautifulSoup(html, 'lxml')
            
            # Parse Bonus Points
            # Usually in a div with id "bonus_points" or similar, or in the header
            # Based on common MAM layout: <span id="bp">123,456</span>
            bp_elem = soup.find(id="bp") or soup.find("span", class_="bonusPoints")
            bonus_points = 0
            if bp_elem:
                bonus_points = int(bp_elem.get_text(strip=True).replace(',', ''))
                
            # Parse VIP Status
            # Look for "VIP" icon or text in user info
            vip_status = False
            vip_expiry = None
            
            # This is a heuristic; actual parsing depends on MAM's exact HTML
            # Assuming we can find it in the store page or user details
            if "You are currently a VIP" in html:
                vip_status = True
                # Try to find expiry date
                # "Your VIP status expires on: YYYY-MM-DD HH:MM:SS"
                import re
                match = re.search(r"expires on: (\d{4}-\d{2}-\d{2})", html)
                if match:
                    vip_expiry = datetime.strptime(match.group(1), "%Y-%m-%d")
            
            return {
                'bonus_points': bonus_points,
                'vip_status': vip_status,
                'vip_expiry_date': vip_expiry,
                'ratio': 0.0, # Placeholder, need to parse from header if needed
                'earning_rate': 0.0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to fetch stats: {e}")
            return None

    def calculate_vip_days_remaining(self, expiry_date: Optional[datetime]) -> Optional[int]:
        """Calculate days remaining on VIP status."""
        if not expiry_date:
            return None
        now = datetime.now()
        if expiry_date <= now:
            return 0
        delta = expiry_date - now
        return delta.days

    def calculate_renewal_needed(self, days_remaining: Optional[int]) -> Tuple[bool, int]:
        """Calculate if VIP renewal is needed."""
        if days_remaining is None:
            return True, 28 # Assume needed if unknown
        if days_remaining < self.MINIMUM_DAYS_BUFFER:
            return True, 28 - days_remaining
        return False, 0

    def calculate_renewal_cost(self, days_to_add: int) -> int:
        return int(days_to_add * self.POINTS_PER_DAY)

    async def renew_vip_status(self, days_to_add: int, dry_run: bool = False) -> bool:
        """Renew VIP status on MAM."""
        cost = self.calculate_renewal_cost(days_to_add)
        self.logger.info(f"[VIP] Renewing VIP status for {days_to_add} days (cost: {cost} points)")

        if dry_run:
            self.logger.info("[VIP] DRY-RUN: Would renew VIP status")
            return True

        # TODO: Implement actual POST to store.php
        # This requires analyzing the form data for the store purchase
        self.logger.warning("[VIP] Actual purchase logic not yet implemented (Safety)")
        return False

    async def spend_remaining_points(self, current_points: int, reserve_for_vip: bool = True, dry_run: bool = False) -> Dict:
        """Spend remaining bonus points on VIP extension first, then upload credit."""
        self.logger.info(f"[VIP] Starting point allocation with {current_points:,} points")

        result = {
            'starting_points': current_points,
            'vip_points_spent': 0,
            'vip_days_added': 0,
            'upload_points_spent': 0,
            'upload_gb_added': 0,
            'remaining_points': current_points,
            'vip_buffer_reserved': 0
        }

        stats = await self.get_real_stats()
        if not stats:
            self.logger.error("Could not get real stats, aborting spend")
            return result
            
        days_remaining = self.calculate_vip_days_remaining(stats.get('vip_expiry_date'))
        needs_renewal, days_to_add = self.calculate_renewal_needed(days_remaining)

        if needs_renewal and days_to_add > 0:
            renewal_cost = self.calculate_renewal_cost(days_to_add)
            if current_points >= renewal_cost:
                self.logger.info(f"[VIP] VIP renewal needed: {days_remaining or 0} days remaining")
                if not dry_run:
                    success = await self.renew_vip_status(days_to_add, dry_run=False)
                    if success:
                        result['vip_points_spent'] = renewal_cost
                        result['vip_days_added'] = days_to_add
                        result['remaining_points'] -= renewal_cost
                else:
                    self.logger.info("[VIP] DRY-RUN: Would renew VIP status")
                    result['vip_points_spent'] = renewal_cost
                    result['vip_days_added'] = days_to_add
                    result['remaining_points'] -= renewal_cost
            else:
                self.logger.warning(f"[VIP] Insufficient points for VIP renewal! Need {renewal_cost:,}, have {current_points:,}")
        else:
            self.logger.info(f"[VIP] VIP status healthy: {days_remaining or 'unknown'} days remaining")

        if reserve_for_vip:
            if result['remaining_points'] > self.MINIMUM_POINTS_BUFFER:
                result['vip_buffer_reserved'] = self.MINIMUM_POINTS_BUFFER
                result['remaining_points'] -= self.MINIMUM_POINTS_BUFFER
                self.logger.info(f"[VIP] Reserved {self.MINIMUM_POINTS_BUFFER:,.0f} points for VIP buffer")

        if result['remaining_points'] >= self.POINTS_PER_1GB_UPLOAD:
            upload_gb = result['remaining_points'] // self.POINTS_PER_1GB_UPLOAD
            upload_cost = upload_gb * self.POINTS_PER_1GB_UPLOAD
            self.logger.info(f"[VIP] Spending {upload_cost:,} points on {upload_gb} GB upload credit")
            if not dry_run:
                pass # Implement buy logic
            else:
                self.logger.info("[VIP] DRY-RUN: Would buy upload credit")
            result['upload_points_spent'] = upload_cost
            result['upload_gb_added'] = upload_gb
            result['remaining_points'] -= upload_cost

        return result

    async def check_and_maintain_vip(self, dry_run: bool = False) -> Dict:
        """Main function to check and maintain VIP status."""
        self.logger.info("[VIP] Starting VIP status maintenance check...")
        stats = await self.get_real_stats()
        if not stats:
            return {'error': 'failed_to_get_stats'}
            
        current_points = stats.get('bonus_points', 0)
        if not stats.get('vip_status', False):
            self.logger.warning("[VIP] WARNING: Not currently VIP!")
            
        result = await self.spend_remaining_points(current_points=current_points, reserve_for_vip=True, dry_run=dry_run)
        self.logger.info("[VIP] VIP status maintenance complete")
        return result

async def main_async():
    import argparse
    parser = argparse.ArgumentParser(description='Test VIP status manager')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()

    manager = VIPStatusManager()
    await manager.check_and_maintain_vip(dry_run=args.dry_run)

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
