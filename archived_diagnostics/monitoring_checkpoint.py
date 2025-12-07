#!/usr/bin/env python3
"""
REAL WORKFLOW MONITORING - 15-MINUTE CHECKPOINTS
Tracks progress with status updates every 15 minutes
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
import aiohttp
from dotenv import load_dotenv

load_dotenv()

class WorkflowMonitor:
    def __init__(self):
        self.log_file = Path("workflow_monitor.log")
        self.checkpoint_file = Path("workflow_checkpoint.json")
        self.start_time = datetime.now()
        self.checkpoint_interval = 900  # 15 minutes in seconds
        self.last_checkpoint = datetime.now()

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"
        print(formatted)
        with open(self.log_file, 'a') as f:
            f.write(formatted + "\n")

    async def check_abs_status(self) -> dict:
        """Check AudiobookShelf status"""
        try:
            abs_url = os.getenv('ABS_URL', 'http://localhost:13378')
            abs_token = os.getenv('ABS_TOKEN')

            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Bearer {abs_token}'}

                # Get library info
                async with session.get(f'{abs_url}/api/libraries', headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        libs = await resp.json()
                        lib = libs.get('libraries', [{}])[0]

                        # Get item count
                        async with session.get(
                            f'{abs_url}/api/libraries/{lib.get("id")}/items?limit=1',
                            headers=headers
                        ) as items_resp:
                            items_data = await items_resp.json()
                            total_items = items_data.get('total', 0)

                        return {
                            'status': 'OK',
                            'library': lib.get('name'),
                            'total_items': total_items
                        }
                    else:
                        return {'status': 'FAIL', 'error': f'HTTP {resp.status}'}
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    async def check_qb_status(self) -> dict:
        """Check qBittorrent status"""
        try:
            qb_url = os.getenv('QBITTORRENT_URL', 'http://192.168.0.48:52095/')
            qb_user = os.getenv('QBITTORRENT_USERNAME')
            qb_pass = os.getenv('QBITTORRENT_PASSWORD')

            async with aiohttp.ClientSession() as session:
                # Get torrents
                async with session.post(
                    f'{qb_url}api/v2/auth/login',
                    data={'username': qb_user, 'password': qb_pass},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as auth_resp:
                    if auth_resp.status != 200:
                        return {'status': 'AUTH_FAIL'}

                # Get torrent list
                async with session.get(f'{qb_url}api/v2/torrents/info') as torrents_resp:
                    if torrents_resp.status == 200:
                        torrents = await torrents_resp.json()

                        downloading = [t for t in torrents if t.get('state') in ['downloading', 'allocating']]
                        completed = [t for t in torrents if t.get('state') in ['uploading', 'forcedUP']]

                        return {
                            'status': 'OK',
                            'total_torrents': len(torrents),
                            'downloading': len(downloading),
                            'completed': len(completed)
                        }
                    else:
                        return {'status': 'FAIL', 'error': f'HTTP {torrents_resp.status}'}
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    async def get_execution_log_status(self) -> dict:
        """Parse execution log to get workflow status"""
        log_file = Path("real_workflow_execution.log")

        if not log_file.exists():
            return {'status': 'NO_LOG'}

        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()

            if not lines:
                return {'status': 'EMPTY_LOG'}

            # Get last line
            last_line = lines[-1].strip()

            # Count items loaded
            loaded_count = 0
            for line in reversed(lines[-100:]):
                if '[SCAN ]' in line and 'Loaded' in line:
                    try:
                        parts = line.split('Loaded ')
                        if len(parts) > 1:
                            count_str = parts[1].split(' items')[0]
                            loaded_count = int(count_str)
                            break
                    except:
                        pass

            # Check for errors
            errors = [l for l in lines[-50:] if '[ERROR]' in l or '[FAIL]' in l]

            return {
                'status': 'RUNNING',
                'last_update': last_line[-50:] if len(last_line) > 50 else last_line,
                'items_loaded': loaded_count,
                'recent_errors': len(errors)
            }
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

    async def checkpoint(self):
        """Create a checkpoint snapshot"""
        checkpoint_data = {
            'timestamp': datetime.now().isoformat(),
            'elapsed_seconds': (datetime.now() - self.start_time).total_seconds(),
            'abs': await self.check_abs_status(),
            'qbittorrent': await self.check_qb_status(),
            'workflow': await self.get_execution_log_status()
        }

        # Save checkpoint
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)

        # Log status
        self.log("=" * 80, "CHECKPOINT")
        self.log(f"Elapsed: {checkpoint_data['elapsed_seconds']:.0f}s", "CHECKPOINT")
        self.log(f"ABS: {checkpoint_data['abs'].get('status')}", "CHECKPOINT")

        if checkpoint_data['abs'].get('status') == 'OK':
            self.log(f"  Library: {checkpoint_data['abs'].get('library')}", "CHECKPOINT")
            self.log(f"  Items: {checkpoint_data['abs'].get('total_items')}", "CHECKPOINT")

        self.log(f"qBittorrent: {checkpoint_data['qbittorrent'].get('status')}", "CHECKPOINT")

        if checkpoint_data['qbittorrent'].get('status') == 'OK':
            self.log(f"  Downloading: {checkpoint_data['qbittorrent'].get('downloading')}", "CHECKPOINT")
            self.log(f"  Completed: {checkpoint_data['qbittorrent'].get('completed')}", "CHECKPOINT")

        self.log(f"Workflow: {checkpoint_data['workflow'].get('status')}", "CHECKPOINT")

        if checkpoint_data['workflow'].get('status') == 'RUNNING':
            self.log(f"  Items loaded: {checkpoint_data['workflow'].get('items_loaded')}", "CHECKPOINT")
            self.log(f"  Recent errors: {checkpoint_data['workflow'].get('recent_errors')}", "CHECKPOINT")

        self.log("=" * 80, "CHECKPOINT")

        return checkpoint_data

    async def run(self, duration_minutes: int = 120):
        """Run monitoring for specified duration"""
        self.log(f"Starting monitoring for {duration_minutes} minutes", "INIT")
        self.log(f"Checkpoints every 15 minutes", "INIT")

        end_time = datetime.now().timestamp() + (duration_minutes * 60)
        checkpoint_count = 0

        while datetime.now().timestamp() < end_time:
            # Do checkpoint
            checkpoint_count += 1
            self.log(f"Checkpoint #{checkpoint_count}", "INFO")

            try:
                await self.checkpoint()
            except Exception as e:
                self.log(f"Checkpoint error: {e}", "ERROR")

            # Wait for next checkpoint (15 minutes)
            self.log(f"Next checkpoint in 15 minutes...", "INFO")
            await asyncio.sleep(self.checkpoint_interval)

        self.log(f"Monitoring complete after {checkpoint_count} checkpoints", "COMPLETE")


async def main():
    monitor = WorkflowMonitor()
    await monitor.run(duration_minutes=120)  # Monitor for 2 hours


if __name__ == '__main__':
    asyncio.run(main())
