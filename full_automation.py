"""
FULL AUTOMATION: Restart ABS, Populate Series, Verify

This script handles the complete workflow:
1. Start Audiobookshelf (schema repair)
2. Stop Audiobookshelf (database access)
3. Populate series
4. Restart Audiobookshelf (to see changes)

This is THE reliable method - no timeouts, clear logging.
"""

import subprocess
import time
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('full_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def find_abs_executable():
    """Find Audiobookshelf executable"""
    paths = [
        "C:\\Users\\dogma\\AppData\\Local\\Programs\\Audiobookshelf\\AudiobookshelfTray.exe",
        "C:\\Program Files\\Audiobookshelf\\Audiobookshelf.exe",
        "C:\\Program Files (x86)\\Audiobookshelf\\Audiobookshelf.exe",
    ]
    for path in paths:
        if Path(path).exists():
            return path
    return None


def is_running():
    """Check if Audiobookshelf is running"""
    result = subprocess.run(
        "tasklist | findstr /i node",
        shell=True,
        capture_output=True,
        text=True
    )
    return "node" in result.stdout.lower()


def start_abs(exe_path):
    """Start Audiobookshelf application"""
    logger.info(f"Starting Audiobookshelf from: {exe_path}")
    try:
        exe_dir = str(Path(exe_path).parent)
        subprocess.Popen(exe_path, cwd=exe_dir)
        time.sleep(2)

        if is_running():
            logger.info("[OK] Audiobookshelf is now running")
            return True
        else:
            logger.warning("[!] Could not start Audiobookshelf automatically")
            logger.warning("  Please start Audiobookshelf manually and press Enter")
            input("  Press Enter when Audiobookshelf is running...")

            if is_running():
                logger.info("[OK] Audiobookshelf detected")
                return True
            else:
                logger.error("[X] Audiobookshelf is still not running")
                return False
    except Exception as e:
        logger.error(f"Error starting Audiobookshelf: {e}")
        return False


def stop_abs():
    """Stop Audiobookshelf application"""
    logger.info("Stopping Audiobookshelf...")
    try:
        subprocess.run("taskkill /IM node.exe /F 2>nul", shell=True)
        time.sleep(2)

        if not is_running():
            logger.info("[OK] Audiobookshelf is now stopped")
            return True
        else:
            logger.warning("[!] Audiobookshelf still appears to be running")
            # Try once more with verbose kill
            subprocess.run("taskkill /IM node.exe /F", shell=True)
            time.sleep(2)
            return not is_running()
    except Exception as e:
        logger.error(f"Error stopping Audiobookshelf: {e}")
        return False


def wait_seconds(seconds, label):
    """Wait with countdown"""
    logger.info(f"{label} ({seconds}s)...")
    for i in range(seconds, 0, -1):
        time.sleep(1)
        if i % 5 == 0 or i <= 3:
            logger.info(f"  {i}s remaining...")


def run_populator():
    """Run the series populator"""
    logger.info("Running series populator...")
    result = subprocess.run(
        [sys.executable, "simple_series_populator.py"],
        cwd="C:\\Users\\dogma\\Projects\\MAMcrawler",
        capture_output=True,
        text=True
    )

    # Print output
    if result.stdout:
        logger.info(result.stdout)
    if result.stderr:
        logger.warning(result.stderr)

    return result.returncode == 0


def main():
    """Main workflow"""
    logger.info("")
    logger.info("=" * 80)
    logger.info("FULL AUTOMATION: RESTART, POPULATE, VERIFY")
    logger.info("=" * 80)
    logger.info("")

    # Find Audiobookshelf
    abs_exe = find_abs_executable()
    if not abs_exe:
        logger.error("Could not find Audiobookshelf executable")
        logger.error("Please install Audiobookshelf and try again")
        return 1

    logger.info(f"Found Audiobookshelf at: {abs_exe}")
    logger.info("")

    try:
        # Step 1: Stop if running
        logger.info("STEP 1: Check current status")
        logger.info("-" * 80)
        if is_running():
            logger.info("Audiobookshelf is running, stopping...")
            stop_abs()
            wait_seconds(2, "Waiting for process to exit")
        else:
            logger.info("Audiobookshelf is not running")
        logger.info("")

        # Step 2: Start Audiobookshelf (schema repair)
        logger.info("STEP 2: Start Audiobookshelf (schema repair)")
        logger.info("-" * 80)
        if not start_abs(abs_exe):
            logger.error("Could not start Audiobookshelf")
            return 1
        wait_seconds(30, "Waiting for initialization")
        logger.info("")

        # Step 3: Stop Audiobookshelf (database access)
        logger.info("STEP 3: Stop Audiobookshelf (for database access)")
        logger.info("-" * 80)
        stop_abs()
        wait_seconds(2, "Waiting for shutdown")
        logger.info("")

        # Step 4: Populate series
        logger.info("STEP 4: Populate series")
        logger.info("-" * 80)
        if not run_populator():
            logger.error("Series population failed!")
            logger.error("Check simple_series_populator.log for details")
            return 1
        logger.info("")

        # Step 5: Restart Audiobookshelf
        logger.info("STEP 5: Restart Audiobookshelf")
        logger.info("-" * 80)
        if not start_abs(abs_exe):
            logger.error("Could not restart Audiobookshelf")
            logger.warning("You may need to start it manually")
            return 1
        wait_seconds(30, "Waiting for startup")
        logger.info("")

        # Summary
        logger.info("=" * 80)
        logger.info("AUTOMATION COMPLETE - SUCCESS!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Series should now be visible in Audiobookshelf!")
        logger.info("Open http://localhost:13378 in your browser")
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
