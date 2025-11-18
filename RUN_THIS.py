"""
RUN THIS SCRIPT - IT WILL FIX EVERYTHING

This script is designed to be foolproof:
1. It handles Audiobookshelf startup/shutdown correctly
2. It waits appropriately between steps
3. It has clear error messages if something goes wrong
4. It uses PowerShell (which works better on Windows)

Just run it and follow the prompts.
"""

import subprocess
import time
import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler('RUN_THIS.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_powershell(script):
    """Run PowerShell script safely"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip(), result.returncode == 0
    except Exception as e:
        logger.error(f"PowerShell error: {e}")
        return "", False


def is_abs_running():
    """Check if Audiobookshelf is running"""
    output, success = run_powershell(
        "Get-Process -Name node -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"
    )
    try:
        return int(output) > 0
    except:
        return False


def start_abs():
    """Start Audiobookshelf application"""
    logger.info("Starting Audiobookshelf...")
    try:
        exe_path = r"C:\Users\dogma\AppData\Local\Programs\Audiobookshelf\AudiobookshelfTray.exe"
        subprocess.Popen(exe_path, cwd=r"C:\Users\dogma\AppData\Local\Programs\Audiobookshelf")
        time.sleep(2)

        if is_abs_running():
            logger.info("[OK] Audiobookshelf is now running")
            return True
        else:
            logger.warning("[!] Could not start Audiobookshelf automatically")
            logger.warning("  Please start Audiobookshelf manually and press Enter")
            input("  Press Enter when Audiobookshelf is running...")

            if is_abs_running():
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

        if not is_abs_running():
            logger.info("[OK] Audiobookshelf is now stopped")
            return True
        else:
            logger.warning("[!] Audiobookshelf still appears to be running")
            # Try once more with verbose kill
            subprocess.run("taskkill /IM node.exe /F", shell=True)
            time.sleep(2)
            return not is_abs_running()
    except Exception as e:
        logger.error(f"Error stopping Audiobookshelf: {e}")
        return False


def run_populator():
    """Run the series populator"""
    logger.info("Running series populator...")
    logger.info("")

    result = subprocess.run(
        [sys.executable, "simple_series_populator.py"],
        cwd="C:\\Users\\dogma\\Projects\\MAMcrawler",
    )

    logger.info("")
    return result.returncode == 0


def main():
    """Main workflow"""
    os.chdir("C:\\Users\\dogma\\Projects\\MAMcrawler")

    logger.info("")
    logger.info("=" * 80)
    logger.info("AUDIOBOOKSHELF SERIES POPULATOR - AUTOMATIC")
    logger.info("=" * 80)
    logger.info("")

    try:
        # Step 1: Stop if running
        logger.info("[STEP 1/5] Checking current status...")
        if is_abs_running():
            logger.info("  Audiobookshelf is currently running")
            stop_abs()
        else:
            logger.info("  Audiobookshelf is not running")
        logger.info("")

        # Step 2: Start (schema repair)
        logger.info("[STEP 2/5] Starting Audiobookshelf (schema repair)...")
        if not start_abs():
            logger.error("Could not start Audiobookshelf")
            return 1

        logger.info("  Waiting 30 seconds for database repair...")
        for i in range(30, 0, -1):
            time.sleep(1)
            if i % 10 == 0:
                logger.info(f"  {i}s remaining...")
        logger.info("")

        # Step 3: Stop (database access)
        logger.info("[STEP 3/5] Stopping Audiobookshelf (for safe database access)...")
        stop_abs()
        logger.info("  Waiting 2 seconds...")
        time.sleep(2)
        logger.info("")

        # Step 4: Populate
        logger.info("[STEP 4/5] Populating series in database...")
        if not run_populator():
            logger.error("Series populator failed!")
            logger.error("Check simple_series_populator.log for details")
            return 1
        logger.info("")

        # Step 5: Restart
        logger.info("[STEP 5/5] Restarting Audiobookshelf...")
        if not start_abs():
            logger.error("Could not restart Audiobookshelf")
            logger.warning("You may need to start it manually")
            return 1

        logger.info("  Waiting 30 seconds for startup...")
        for i in range(30, 0, -1):
            time.sleep(1)
            if i % 10 == 0:
                logger.info(f"  {i}s remaining...")
        logger.info("")

        # Success!
        logger.info("=" * 80)
        logger.info("SUCCESS! Series have been populated!")
        logger.info("=" * 80)
        logger.info("")
        logger.info("Open your browser: http://localhost:13378")
        logger.info("Navigate to Books to see the Series column populated")
        logger.info("")

        return 0

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
