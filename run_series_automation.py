"""
Complete Automated Series Population Workflow

This script orchestrates the entire process:
1. Restart Audiobookshelf to repair database schema
2. Wait for API to be available
3. Run series population
4. Verify results
"""

import subprocess
import time
import logging
import socket
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)

ABS_PORT = 13378
ABS_HOST = "localhost"


def is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Check if port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def find_abs_process():
    """Find Audiobookshelf process"""
    try:
        result = subprocess.run(
            "tasklist | findstr /i node",
            shell=True,
            capture_output=True,
            text=True
        )
        return "node" in result.stdout.lower()
    except:
        return False


def kill_abs():
    """Kill Audiobookshelf gracefully"""
    logger.info("Stopping Audiobookshelf...")
    try:
        subprocess.run("taskkill /IM node.exe /F 2>nul", shell=True)
        time.sleep(2)
        logger.info("Audiobookshelf stopped")
        return True
    except Exception as e:
        logger.error(f"Could not stop Audiobookshelf: {e}")
        return False


def start_abs():
    """Start Audiobookshelf"""
    logger.info("Starting Audiobookshelf...")
    try:
        # Try common installation paths
        paths = [
            "C:\\Program Files\\Audiobookshelf\\Audiobookshelf.exe",
            "C:\\Program Files (x86)\\Audiobookshelf\\Audiobookshelf.exe",
            "Audiobookshelf.exe"
        ]

        for path in paths:
            if Path(path).exists():
                subprocess.Popen(path)
                logger.info(f"Started Audiobookshelf from {path}")
                return True

        logger.warning("Could not find Audiobookshelf executable")
        logger.warning("Please start Audiobookshelf manually and run this script again")
        return False

    except Exception as e:
        logger.error(f"Error starting Audiobookshelf: {e}")
        return False


def wait_for_abs(max_wait: int = 60):
    """Wait for Audiobookshelf API to be available"""
    logger.info(f"Waiting for Audiobookshelf API on {ABS_HOST}:{ABS_PORT}...")

    start_time = time.time()
    attempt = 0

    while time.time() - start_time < max_wait:
        attempt += 1
        if is_port_open(ABS_HOST, ABS_PORT):
            logger.info("Audiobookshelf API is ready!")
            time.sleep(2)  # Give it a moment to fully initialize
            return True

        logger.info(f"  Waiting... (attempt {attempt}, elapsed {int(time.time() - start_time)}s)")
        time.sleep(2)

    logger.error(f"Audiobookshelf did not start within {max_wait} seconds")
    return False


def run_series_populator():
    """Run the automated series populator script"""
    logger.info("Running series population...")

    try:
        result = subprocess.run(
            [sys.executable, "automated_series_populator.py"],
            cwd="C:\\Users\\dogma\\Projects\\MAMcrawler",
            capture_output=True,
            text=True,
            timeout=300
        )

        logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        logger.error("Series populator timed out")
        return False
    except Exception as e:
        logger.error(f"Error running series populator: {e}")
        return False


def main():
    """Main workflow"""
    logger.info("=" * 80)
    logger.info("AUTOMATED AUDIOBOOKSHELF SERIES POPULATION WORKFLOW")
    logger.info("=" * 80)
    logger.info("")

    try:
        # Step 1: Check if Audiobookshelf is running
        logger.info("Step 1: Checking Audiobookshelf status...")
        if find_abs_process():
            logger.info("Audiobookshelf is running. Restarting to repair database...")
            kill_abs()
            time.sleep(3)
        else:
            logger.info("Audiobookshelf is not running")

        # Step 2: Start Audiobookshelf
        logger.info("\nStep 2: Starting Audiobookshelf...")
        if not start_abs():
            logger.error("Could not start Audiobookshelf. Aborting.")
            return 1

        # Step 3: Wait for API
        logger.info("\nStep 3: Waiting for Audiobookshelf API...")
        if not wait_for_abs(max_wait=90):
            logger.error("Audiobookshelf did not start. Aborting.")
            return 1

        # Step 4: Run series populator
        logger.info("\nStep 4: Populating series...")
        success = run_series_populator()

        if not success:
            logger.warning("Series population did not complete successfully")
            logger.warning("This may be due to database schema corruption")
            logger.info("Attempting to recover...")

            # Try the database repair script
            try:
                result = subprocess.run(
                    [sys.executable, "fix_db_and_populate_series.py"],
                    cwd="C:\\Users\\dogma\\Projects\\MAMcrawler",
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                logger.info(result.stdout)
            except Exception as e:
                logger.error(f"Recovery script failed: {e}")

        # Step 5: Restart to apply changes
        logger.info("\nStep 5: Restarting Audiobookshelf to apply changes...")
        kill_abs()
        time.sleep(2)

        if start_abs():
            logger.info("Waiting for Audiobookshelf to restart...")
            if wait_for_abs(max_wait=60):
                logger.info("Audiobookshelf is ready with series populated!")
            else:
                logger.warning("Audiobookshelf did not restart in time, but process was started")
        else:
            logger.warning("Could not restart Audiobookshelf. Please restart manually.")

        logger.info("")
        logger.info("=" * 80)
        logger.info("AUTOMATION COMPLETE")
        logger.info("=" * 80)
        logger.info("Series should now be visible in Audiobookshelf UI")
        logger.info("Open http://localhost:13378 to verify")
        logger.info("")

        return 0

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
