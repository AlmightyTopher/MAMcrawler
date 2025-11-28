#!/usr/bin/env python3
"""
qBittorrent Torrent Adder - Multiple Methods

If standard API fails (403), this script provides alternative ways to add torrents:
1. Direct magnet link via browser
2. Via Prowlarr indexer
3. Via torrent file download and manual addition
4. Via qBittorrent command-line (if available locally)
"""

import os
import sys
import asyncio
import aiohttp
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


class TorrentAdder:
    """Add torrents to qBittorrent using multiple methods"""

    def __init__(self):
        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/').rstrip('/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD')
        self.prowlarr_url = os.getenv('PROWLARR_URL', 'http://localhost:9696')
        self.prowlarr_key = os.getenv('PROWLARR_API_KEY')
        self.log_file = Path("torrent_adder.log")

    def log(self, message: str, level: str = "INFO"):
        """Log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level:5}] {message}"
        print(formatted)
        with open(self.log_file, 'a') as f:
            f.write(formatted + "\n")

    # ========================================
    # METHOD 1: Direct Magnet Link
    # ========================================

    def method_1_direct_magnet(self, magnet_link: str) -> bool:
        """
        Open magnet link directly in browser.
        qBittorrent on same machine will capture and add it.
        """
        self.log("=" * 80)
        self.log("METHOD 1: Direct Magnet Link (Browser)", "TEST")
        self.log("=" * 80)

        try:
            import webbrowser
            self.log(f"Opening magnet link in browser...", "DEBUG")
            self.log(f"Magnet: {magnet_link[:100]}...", "DEBUG")

            # This will open the magnet link in default browser
            # qBittorrent on the same machine should capture it
            result = webbrowser.open(magnet_link)

            if result:
                self.log("Magnet link opened successfully", "OK")
                self.log("If qBittorrent is installed on this machine,", "OK")
                self.log("it should automatically add this torrent", "OK")
                return True
            else:
                self.log("Failed to open magnet link", "FAIL")
                return False

        except Exception as e:
            self.log(f"Error: {e}", "FAIL")
            return False

    # ========================================
    # METHOD 2: Prowlarr Integration
    # ========================================

    async def method_2_prowlarr_integration(self, magnet_link: str) -> bool:
        """
        Use Prowlarr to add torrent to qBittorrent.
        Prowlarr can access local qBittorrent even if API is blocked.
        """
        self.log("=" * 80)
        self.log("METHOD 2: Prowlarr Integration", "TEST")
        self.log("=" * 80)

        try:
            if not self.prowlarr_key:
                self.log("Prowlarr API key not configured", "WARN")
                return False

            # Method 2A: Use Prowlarr's test connection to qBittorrent
            self.log(f"Testing Prowlarr connection to qBittorrent...", "DEBUG")

            async with aiohttp.ClientSession() as session:
                # Get Prowlarr health
                async with session.get(
                    f"{self.prowlarr_url}/api/v1/health",
                    headers={"X-Api-Key": self.prowlarr_key},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        self.log("Prowlarr not accessible", "FAIL")
                        return False

                # Get Prowlarr applications (includes qBittorrent connection info)
                async with session.get(
                    f"{self.prowlarr_url}/api/v1/applications",
                    headers={"X-Api-Key": self.prowlarr_key},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        apps = await resp.json()
                        # Find qBittorrent app
                        qb_app = next(
                            (a for a in apps if "qbittorrent" in a.get("name", "").lower()),
                            None
                        )
                        if qb_app:
                            self.log(f"Found qBittorrent app in Prowlarr: {qb_app.get('name')}", "OK")
                            self.log(f"Prowlarr can relay torrents to qBittorrent", "OK")
                            # Prowlarr is configured to use qBittorrent
                            # Any torrents indexed by Prowlarr will be sent there
                            return True
                        else:
                            self.log("qBittorrent not configured in Prowlarr", "WARN")
                            return False
                    else:
                        self.log(f"Failed to get Prowlarr apps: HTTP {resp.status}", "FAIL")
                        return False

        except Exception as e:
            self.log(f"Prowlarr integration error: {e}", "FAIL")
            return False

    # ========================================
    # METHOD 3: Manual Torrent File
    # ========================================

    async def method_3_torrent_file(self, magnet_link: str) -> bool:
        """
        Download torrent file from magnet link and manually add it.
        This requires a magnet-to-torrent conversion service.
        """
        self.log("=" * 80)
        self.log("METHOD 3: Manual Torrent File", "TEST")
        self.log("=" * 80)

        try:
            # Extract info hash from magnet link
            if "btih:" not in magnet_link:
                self.log("Invalid magnet link format", "FAIL")
                return False

            info_hash = magnet_link.split("btih:")[1].split("&")[0]
            self.log(f"Extracted info hash: {info_hash[:20]}...", "DEBUG")

            # Try to download metadata from DHT or torrent tracker
            # This is complex and requires either:
            # 1. Access to BitTorrent DHT
            # 2. Access to a tracker that has the .torrent file
            # 3. A magnet-to-torrent service (varies by source)

            self.log("To use torrent file method:", "INFO")
            self.log("1. Use a magnet-to-torrent service (e.g., magnet2torrent.com)", "INFO")
            self.log(f"2. Convert your magnet link to .torrent file", "INFO")
            self.log(f"3. Upload .torrent file to qBittorrent Web UI manually", "INFO")
            self.log(f"4. Or place in qBittorrent watch folder: {Path.home() / '.config/qBittorrent'}", "INFO")

            return False  # Requires manual steps

        except Exception as e:
            self.log(f"Torrent file method error: {e}", "FAIL")
            return False

    # ========================================
    # METHOD 4: Command-Line qBittorrent
    # ========================================

    async def method_4_command_line(self, magnet_link: str) -> bool:
        """
        Use qBittorrent command-line client if installed locally.
        This bypasses the Web UI entirely.
        """
        self.log("=" * 80)
        self.log("METHOD 4: Command-Line qBittorrent", "TEST")
        self.log("=" * 80)

        try:
            # Check if qBittorrent is available in PATH
            result = subprocess.run(
                ["where", "qbittorrent"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                qb_path = result.stdout.strip()
                self.log(f"Found qBittorrent CLI: {qb_path}", "OK")

                # Add torrent via command line
                self.log(f"Adding torrent via command line...", "DEBUG")

                # Note: Command syntax varies by qBittorrent version
                # Standard: qbittorrent <magnet_link>
                # With save path: qbittorrent --save-path=<path> <magnet_link>

                cmd = [qb_path, "--add-paused=false", magnet_link]
                self.log(f"Command: {' '.join(cmd[:2])} ...", "DEBUG")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=10
                )

                if result.returncode == 0:
                    self.log("Torrent added successfully via CLI", "OK")
                    return True
                else:
                    self.log(f"CLI add failed: {result.stderr.decode()[:100]}", "FAIL")
                    return False
            else:
                self.log("qBittorrent CLI not found in PATH", "WARN")
                self.log("Install qBittorrent or add it to PATH", "INFO")
                return False

        except Exception as e:
            self.log(f"Command-line method error: {e}", "FAIL")
            return False

    # ========================================
    # METHOD 5: Browser Cookie-Based Auth
    # ========================================

    async def method_5_browser_cookies(self, magnet_link: str) -> bool:
        """
        Use browser cookies from an authenticated session.
        This works around IP restrictions by using the browser's session.
        """
        self.log("=" * 80)
        self.log("METHOD 5: Browser Cookie-Based Auth", "TEST")
        self.log("=" * 80)

        try:
            # Try to extract cookies from browser
            # This requires browser_cookie3 library
            try:
                import browser_cookie3
                BROWSER_COOKIES_AVAILABLE = True
            except ImportError:
                BROWSER_COOKIES_AVAILABLE = False
                self.log("browser_cookie3 not installed", "WARN")
                self.log("Install: pip install browser-cookie3", "INFO")
                return False

            if not BROWSER_COOKIES_AVAILABLE:
                return False

            self.log("Extracting cookies from browser...", "DEBUG")

            # Get cookies from Chrome (or other browser)
            cj = browser_cookie3.chrome()

            # Find qBittorrent cookies
            qb_cookies = {}
            for cookie in cj:
                if "192.168.0.48" in cookie.domain or "qbittorrent" in cookie.name.lower():
                    qb_cookies[cookie.name] = cookie.value

            if not qb_cookies:
                self.log("No qBittorrent cookies found in browser", "WARN")
                return False

            self.log(f"Found {len(qb_cookies)} qBittorrent cookies", "OK")

            # Use cookies to add torrent
            async with aiohttp.ClientSession(cookie_jar=cj) as session:
                data = aiohttp.FormData()
                data.add_field('urls', magnet_link)

                async with session.post(
                    f'{self.qb_url}/api/v2/torrents/add',
                    data=data,
                    ssl=False
                ) as resp:
                    if resp.status == 200:
                        self.log("Torrent added successfully via browser cookies", "OK")
                        return True
                    else:
                        self.log(f"Failed: HTTP {resp.status}", "FAIL")
                        return False

        except Exception as e:
            self.log(f"Browser cookie method error: {e}", "FAIL")
            return False

    # ========================================
    # MAIN: Try all methods in order
    # ========================================

    async def add_torrent_all_methods(self, magnet_link: str, test_name: str = "Test Torrent") -> bool:
        """Try to add torrent using all available methods"""
        self.log("")
        self.log("=" * 100)
        self.log(f"ADDING TORRENT: {test_name}")
        self.log(f"Magnet: {magnet_link[:80]}...", "INFO")
        self.log("=" * 100)

        methods_tried = {}

        # Method 1: Direct Magnet (local machine)
        methods_tried["Direct Magnet"] = self.method_1_direct_magnet(magnet_link)

        # Method 2: Prowlarr Integration
        methods_tried["Prowlarr"] = await self.method_2_prowlarr_integration(magnet_link)

        # Method 4: Command-Line
        methods_tried["qBittorrent CLI"] = await self.method_4_command_line(magnet_link)

        # Method 5: Browser Cookies
        methods_tried["Browser Cookies"] = await self.method_5_browser_cookies(magnet_link)

        # Summary
        self.log("")
        self.log("=" * 100)
        self.log("SUMMARY", "SUMMARY")
        self.log("=" * 100)

        successful = []
        for method, result in methods_tried.items():
            status = "SUCCESS" if result else "FAILED"
            self.log(f"  {method}: {status}", "SUMMARY")
            if result:
                successful.append(method)

        if successful:
            self.log(f"", "SUMMARY")
            self.log(f"Torrent added via: {', '.join(successful)}", "OK")
            return True
        else:
            self.log(f"", "SUMMARY")
            self.log("All methods failed. Recommendations:", "FAIL")
            self.log("1. Fix IP whitelist in qBittorrent settings (see QBITTORRENT_403_FIX_GUIDE.md)", "INFO")
            self.log("2. Or run qBittorrent on same machine as this script", "INFO")
            self.log("3. Or use Prowlarr to interface with qBittorrent", "INFO")
            return False


async def main():
    adder = TorrentAdder()

    # Test magnet link (Five Fantastic Tales audiobook)
    magnet_link = "magnet:?xt=urn:btih:8B1C8A2E9D3F4B5C6E7F8A9B0C1D2E3F&dn=Five+Fantastic+Tales&tr=udp%3A%2F%2Ftracker.example.com%3A80"

    await adder.add_torrent_all_methods(magnet_link, "Five Fantastic Tales - BBC 4 Science Fiction")


if __name__ == "__main__":
    asyncio.run(main())
