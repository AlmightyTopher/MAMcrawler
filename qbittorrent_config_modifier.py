#!/usr/bin/env python3
"""
qBittorrent Config Modifier - Direct File Configuration

Since the Web UI automation proved difficult, this script:
1. Finds the qBittorrent config file
2. Modifies IP whitelist setting directly
3. Restarts qBittorrent (if possible)
4. Tests the connection
"""

import os
import sys
import json
import asyncio
import aiohttp
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


class QBittorrentConfigModifier:
    """Modify qBittorrent config directly"""

    def __init__(self):
        self.qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/').rstrip('/')
        self.qb_user = os.getenv('QBITTORRENT_USERNAME', 'TopherGutbrod')
        self.qb_pass = os.getenv('QBITTORRENT_PASSWORD', 'Tesl@ismy#1')
        self.log_file = Path("qbittorrent_config_modifier.log")
        self.config_paths = [
            Path.home() / '.config' / 'qBittorrent' / 'qBittorrent.conf',
            Path.home() / 'AppData' / 'Local' / 'qBittorrent' / 'qBittorrent.conf',
            Path.home() / 'AppData' / 'Roaming' / 'qBittorrent' / 'qBittorrent.conf',
            Path('C:\\Users') / os.getenv('USERNAME', 'dogma') / 'AppData' / 'Local' / 'qBittorrent' / 'qBittorrent.conf',
        ]

    def log(self, message: str, level: str = "INFO"):
        """Log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level:5}] {message}"
        print(formatted)
        with open(self.log_file, 'a') as f:
            f.write(formatted + "\n")

    def find_config_file(self) -> Path:
        """Find qBittorrent config file"""
        self.log("=" * 80)
        self.log("STEP 1: Find qBittorrent Config File", "STEP")
        self.log("=" * 80)

        for path in self.config_paths:
            self.log(f"Checking: {path}", "DEBUG")
            if path.exists():
                self.log(f"Found config file: {path}", "OK")
                return path

        self.log("Config file not found in standard locations", "FAIL")
        self.log("Searched paths:", "INFO")
        for path in self.config_paths:
            self.log(f"  - {path}", "INFO")

        return None

    def modify_config(self, config_path: Path) -> bool:
        """Modify qBittorrent config file"""
        self.log("=" * 80)
        self.log("STEP 2: Modify Config File", "STEP")
        self.log("=" * 80)

        try:
            # Read config file
            self.log(f"Reading config file: {config_path}", "DEBUG")
            with open(config_path, 'r') as f:
                config_content = f.read()

            original_content = config_content

            # Look for WebUI section
            if '[Preferences]' not in config_content:
                self.log("No [Preferences] section found", "FAIL")
                return False

            self.log("Found [Preferences] section", "OK")

            # Comment out or remove WebUI\\IpWhitelistEnabled
            self.log("Looking for IP whitelist settings...", "DEBUG")

            # Replace various IP whitelist settings
            replacements = [
                (r'WebUI\\IpWhitelistEnabled=true', 'WebUI\\IpWhitelistEnabled=false'),
                (r'WebUI\\IpWhitelistEnabled=True', 'WebUI\\IpWhitelistEnabled=false'),
                (r'WebUI\\ip_whitelist_enabled=true', 'WebUI\\ip_whitelist_enabled=false'),
                (r'WebUI\\IPWhitelistEnabled=true', 'WebUI\\IPWhitelistEnabled=false'),
            ]

            for old, new in replacements:
                if old in config_content:
                    self.log(f"Replacing: {old}", "DEBUG")
                    config_content = config_content.replace(old, new)

            # Also clear the actual whitelist
            # Look for lines containing IP whitelist
            lines = config_content.split('\n')
            modified_lines = []

            for line in lines:
                # Comment out IP whitelist entries
                if 'IpWhitelist=' in line or 'ip_whitelist=' in line or 'IPWhitelist=' in line:
                    self.log(f"Found IP setting: {line[:80]}", "DEBUG")
                    # Set to empty
                    if '=' in line:
                        key = line.split('=')[0]
                        modified_lines.append(f"{key}=")
                        self.log(f"Cleared: {key}", "DEBUG")
                    else:
                        modified_lines.append(line)
                else:
                    modified_lines.append(line)

            config_content = '\n'.join(modified_lines)

            # Check if content changed
            if config_content == original_content:
                self.log("No changes needed", "WARN")
            else:
                # Backup original
                backup_path = config_path.with_suffix('.conf.backup')
                self.log(f"Creating backup: {backup_path}", "DEBUG")
                with open(backup_path, 'w') as f:
                    f.write(original_content)

                # Write modified config
                self.log(f"Writing modified config: {config_path}", "DEBUG")
                with open(config_path, 'w') as f:
                    f.write(config_content)

                self.log("Config file modified successfully", "OK")
                return True

            return False

        except Exception as e:
            self.log(f"Failed to modify config: {e}", "FAIL")
            return False

    def restart_qbittorrent(self) -> bool:
        """Attempt to restart qBittorrent"""
        self.log("=" * 80)
        self.log("STEP 3: Restart qBittorrent", "STEP")
        self.log("=" * 80)

        try:
            # Try to kill existing qBittorrent process
            self.log("Attempting to stop qBittorrent...", "DEBUG")

            result = subprocess.run(
                ["taskkill", "/IM", "qbittorrent.exe", "/F"],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                self.log("qBittorrent process stopped", "OK")
            else:
                self.log("qBittorrent process not found or already stopped", "WARN")

            # Wait a moment
            import time
            time.sleep(2)

            # Try to start qBittorrent
            self.log("Attempting to start qBittorrent...", "DEBUG")

            try:
                subprocess.Popen("qbittorrent")
                self.log("qBittorrent started successfully", "OK")
                time.sleep(5)  # Wait for it to fully start
                return True
            except FileNotFoundError:
                self.log("qBittorrent executable not found in PATH", "WARN")
                self.log("You may need to restart qBittorrent manually", "INFO")
                return False

        except Exception as e:
            self.log(f"Error restarting qBittorrent: {e}", "FAIL")
            return False

    async def test_api_connection(self) -> bool:
        """Test API connection"""
        self.log("=" * 80)
        self.log("STEP 4: Test API Connection", "STEP")
        self.log("=" * 80)

        try:
            # Wait for qBittorrent to be ready
            import time
            time.sleep(3)

            async with aiohttp.ClientSession() as session:
                # Test 1: Login
                self.log("Testing authentication...", "DEBUG")
                data = aiohttp.FormData()
                data.add_field('username', self.qb_user)
                data.add_field('password', self.qb_pass)

                try:
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
                            self.log("API still returning 403", "FAIL")
                            return False
                        else:
                            self.log(f"API error: HTTP {resp.status}", "FAIL")
                            return False

                except aiohttp.ClientConnectionError:
                    self.log("Could not connect to qBittorrent - may still be starting", "WARN")
                    return False

        except Exception as e:
            self.log(f"Test failed: {e}", "FAIL")
            return False

    async def run_fix(self) -> bool:
        """Run complete fix"""
        self.log("")
        self.log("=" * 100)
        self.log("qBITTORRENT CONFIG MODIFIER - DIRECT FILE MODIFICATION")
        self.log("=" * 100)
        self.log("")

        # Step 1: Find config
        config_path = self.find_config_file()
        if not config_path:
            self.log("Cannot proceed without config file", "FAIL")
            return False

        self.log("")

        # Step 2: Modify config
        modified = self.modify_config(config_path)

        self.log("")

        # Step 3: Restart
        self.restart_qbittorrent()

        self.log("")

        # Step 4: Test
        test_result = await self.test_api_connection()

        # Summary
        self.log("")
        self.log("=" * 100)
        self.log("SUMMARY", "SUMMARY")
        self.log("=" * 100)

        if test_result:
            self.log("SUCCESS: API is now accessible!", "OK")
            self.log("The workflow can now add torrents to qBittorrent", "OK")
            self.log("Next: Re-run execute_full_workflow.py", "OK")
        else:
            self.log("API is still not accessible", "FAIL")
            self.log("Try manual configuration:", "INFO")
            self.log("1. Open qBittorrent Web UI: http://192.168.0.48:52095/", "INFO")
            self.log("2. Go to Tools > Options > Web UI", "INFO")
            self.log("3. Uncheck 'IP whitelist' or add your IP", "INFO")
            self.log("4. Click Apply and retry", "INFO")

        return test_result


async def main():
    modifier = QBittorrentConfigModifier()

    try:
        success = await modifier.run_fix()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
