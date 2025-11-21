"""
Dual Goodreads Scraper Orchestrator.
Manages VPN connection and spawns two worker processes (VPN + Direct).
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

from vpn_manager import VPNManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DualScraper")

class DualScraperOrchestrator:
    def __init__(self, config_path: str = "vpn_config.conf"):
        self.vpn_manager = VPNManager()
        self.config_path = Path(config_path).absolute()
        self.vpn_python = Path("python_vpn.exe")
        self.direct_python = Path(sys.executable)

    def setup_environment(self):
        """
        Prepare the environment:
        1. Create python_vpn.exe copy if needed.
        2. Ensure VPN is running (if config exists).
        """
        # 1. Create Executable Copy for VPN routing
        if not self.vpn_python.exists():
            logger.info(f"Creating {self.vpn_python} for VPN routing...")
            try:
                shutil.copy(sys.executable, self.vpn_python)
            except Exception as e:
                logger.error(f"Failed to copy Python executable: {e}")
                return False
        
        # 2. Setup VPN
        if self.config_path.exists():
            logger.info("Config file found. Ensuring VPN is active...")
            # Note: We assume the firewall rules for python_vpn.exe are set up manually 
            # or via the setup_wireguard_python_tunnel.ps1 script.
            # We just ensure the tunnel is up.
            tunnel_name = self.config_path.stem
            if self.vpn_manager.get_tunnel_status(tunnel_name) != "RUNNING":
                self.vpn_manager.install_tunnel(str(self.config_path))
        else:
            logger.warning(f"VPN Config {self.config_path} not found. Running in fallback mode (Direct only or Manual VPN).")

        return True

    async def run_dual_scrape(self, queries: List[str]):
        """
        Split queries and run two workers.
        """
        mid = len(queries) // 2
        vpn_queries = queries[:mid]
        direct_queries = queries[mid:]

        # Write input files
        with open("queue_vpn.json", "w") as f:
            json.dump(vpn_queries, f)
        with open("queue_direct.json", "w") as f:
            json.dump(direct_queries, f)

        # Start Workers
        procs = []
        
        # Worker 1: VPN (uses python_vpn.exe)
        logger.info("🚀 Starting VPN Worker...")
        cmd_vpn = [
            str(self.vpn_python.absolute()),
            "goodreads_worker.py",
            "--id", "vpn",
            "--input", "queue_vpn.json",
            "--output", "results_vpn.json"
        ]
        procs.append(subprocess.Popen(cmd_vpn))

        # Worker 2: Direct (uses standard python)
        logger.info("🚀 Starting Direct Worker...")
        cmd_direct = [
            str(self.direct_python),
            "goodreads_worker.py",
            "--id", "direct",
            "--input", "queue_direct.json",
            "--output", "results_direct.json"
        ]
        procs.append(subprocess.Popen(cmd_direct))

        # Wait for completion
        for p in procs:
            p.wait()

        logger.info("✅ Both workers completed.")
        self.merge_results()

    def merge_results(self):
        """Merge output files."""
        final_results = []
        
        for mode in ["vpn", "direct"]:
            try:
                with open(f"results_{mode}.json", "r") as f:
                    data = json.load(f)
                    final_results.extend(data)
            except FileNotFoundError:
                logger.warning(f"Results file for {mode} not found.")

        with open("final_goodreads_results.json", "w") as f:
            json.dump(final_results, f, indent=2)
        
        logger.info(f"🎉 Merged {len(final_results)} results to final_goodreads_results.json")

def main():
    # Example queries
    queries = [
        "Project Hail Mary",
        "The Martian",
        "Artemis",
        "Bobiverse",
        "Dungeon Crawler Carl",
        "He Who Fights With Monsters",
        "Red Rising",
        "Golden Son",
        "Morning Star",
        "Iron Gold"
    ]

    orchestrator = DualScraperOrchestrator()
    if orchestrator.setup_environment():
        asyncio.run(orchestrator.run_dual_scrape(queries))

if __name__ == "__main__":
    main()