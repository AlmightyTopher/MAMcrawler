#!/usr/bin/env python3
"""
Safe Audiobookshelf Series Population Automation

This script safely manages Audiobookshelf lifecycle for series population.
Every step is explicit, logged, and verified.

Usage:
    python safe_automation.py
"""

import subprocess
import time
import sys
import os
from pathlib import Path
from datetime import datetime


def log(message):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    sys.stdout.flush()


def countdown(seconds, message):
    """Display countdown timer"""
    log(f"{message} - waiting {seconds} seconds...")
    for i in range(seconds, 0, -1):
        print(f"  {i}...", end="\r")
        sys.stdout.flush()
        time.sleep(1)
    print("  Done!     ")
    sys.stdout.flush()


def check_if_running():
    """Check if Audiobookshelf (node.exe) is currently running"""
    log("Checking if Audiobookshelf is running...")
    try:
        result = subprocess.run(
            'tasklist | findstr /i "node.exe"',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.stdout.strip():
            log(f"  FOUND: Audiobookshelf is running")
            log(f"  Process info: {result.stdout.strip()}")
            return True
        else:
            log("  NOT RUNNING: Audiobookshelf is not running")
            return False

    except subprocess.TimeoutExpired:
        log("  WARNING: Timeout checking process status")
        return False
    except Exception as e:
        log(f"  ERROR: Failed to check if running: {e}")
        return False


def stop_audiobookshelf():
    """Stop Audiobookshelf using taskkill"""
    log("Attempting to stop Audiobookshelf...")

    try:
        # Use taskkill to stop node.exe (Audiobookshelf)
        result = subprocess.run(
            'taskkill /F /IM node.exe',
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            log("  SUCCESS: Stop command executed successfully")
            log(f"  Output: {result.stdout.strip()}")
        else:
            log(f"  WARNING: Stop command returned code {result.returncode}")
            log(f"  Output: {result.stdout.strip()}")
            log(f"  Error: {result.stderr.strip()}")

        # Wait 2 seconds and verify it stopped
        time.sleep(2)

        if not check_if_running():
            log("  VERIFIED: Audiobookshelf has stopped")
            return True
        else:
            log("  WARNING: Audiobookshelf may still be running")
            return False

    except subprocess.TimeoutExpired:
        log("  ERROR: Timeout while trying to stop")
        return False
    except Exception as e:
        log(f"  ERROR: Failed to stop: {e}")
        return False


def start_audiobookshelf(abs_path):
    """Start Audiobookshelf"""
    log("Attempting to start Audiobookshelf...")

    try:
        # Start Audiobookshelf using subprocess.Popen
        process = subprocess.Popen(
            [str(abs_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=abs_path.parent
        )

        log(f"  STARTED: Process launched with PID {process.pid}")

        # Wait 3 seconds and verify it's running
        time.sleep(3)

        if check_if_running():
            log("  VERIFIED: Audiobookshelf is now running")
            return True
        else:
            log("  WARNING: Audiobookshelf may not have started properly")
            return False

    except FileNotFoundError:
        log(f"  ERROR: Executable not found at {abs_path}")
        return False
    except Exception as e:
        log(f"  ERROR: Failed to start: {e}")
        return False


def run_series_populator():
    """Run the series populator script"""
    log("Running series populator...")

    # Determine the Python executable path
    venv_python = Path(__file__).parent / "venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        python_exe = str(venv_python)
        log(f"  Using venv Python: {python_exe}")
    else:
        python_exe = sys.executable
        log(f"  Using system Python: {python_exe}")

    # Path to series populator script
    populator_script = Path(__file__).parent.parent / "allgendownload" / "abs_authmatch_service.py"

    if not populator_script.exists():
        log(f"  ERROR: Series populator script not found at {populator_script}")
        return False

    log(f"  Script path: {populator_script}")

    try:
        log("  Executing series populator (this may take several minutes)...")
        result = subprocess.run(
            [python_exe, str(populator_script)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            log("  SUCCESS: Series populator completed successfully")
            if result.stdout.strip():
                log("  Output:")
                for line in result.stdout.strip().split('\n')[:20]:  # Show first 20 lines
                    log(f"    {line}")
            return True
        else:
            log(f"  ERROR: Series populator failed with code {result.returncode}")
            if result.stderr.strip():
                log("  Error output:")
                for line in result.stderr.strip().split('\n')[:20]:
                    log(f"    {line}")
            return False

    except subprocess.TimeoutExpired:
        log("  ERROR: Series populator timed out (exceeded 10 minutes)")
        return False
    except Exception as e:
        log(f"  ERROR: Failed to run series populator: {e}")
        return False


def main():
    """Main automation workflow"""
    log("=" * 70)
    log("AUDIOBOOKSHELF SERIES POPULATION AUTOMATION")
    log("=" * 70)
    log("")

    # STEP 1: Verify Audiobookshelf installation path
    log("STEP 1: Verifying Audiobookshelf installation path")
    log("-" * 70)

    abs_path = Path(r"C:\Users\dogma\AppData\Local\Programs\Audiobookshelf\Audiobookshelf.exe")
    log(f"  Checking path: {abs_path}")

    if not abs_path.exists():
        log(f"  ERROR: Audiobookshelf not found at {abs_path}")
        log("  Please update the abs_path in this script with the correct path")
        log("  AUTOMATION FAILED")
        return 1

    log(f"  SUCCESS: Found Audiobookshelf at {abs_path}")
    log("")

    # STEP 2: Check if currently running and stop if needed
    log("STEP 2: Checking if Audiobookshelf is running")
    log("-" * 70)

    if check_if_running():
        log("  Audiobookshelf is running, need to stop it")
        if not stop_audiobookshelf():
            log("  WARNING: Failed to stop Audiobookshelf cleanly")
            log("  Continuing anyway...")
    else:
        log("  Audiobookshelf is not running, nothing to stop")
    log("")

    # STEP 3: Wait to ensure fully stopped
    log("STEP 3: Ensuring Audiobookshelf is fully stopped")
    log("-" * 70)
    countdown(5, "Waiting for clean shutdown")
    log("")

    # STEP 4: Start Audiobookshelf fresh
    log("STEP 4: Starting Audiobookshelf for database repair")
    log("-" * 70)

    if not start_audiobookshelf(abs_path):
        log("  ERROR: Failed to start Audiobookshelf")
        log("  AUTOMATION FAILED")
        return 1

    countdown(35, "Waiting for database repair and full startup")
    log("")

    # STEP 5: Stop Audiobookshelf again
    log("STEP 5: Stopping Audiobookshelf before series population")
    log("-" * 70)

    if not stop_audiobookshelf():
        log("  WARNING: Failed to stop Audiobookshelf cleanly")
        log("  Continuing anyway...")

    countdown(3, "Waiting for clean shutdown")
    log("")

    # STEP 6: Run series populator
    log("STEP 6: Running series populator")
    log("-" * 70)

    if not run_series_populator():
        log("  ERROR: Series populator failed")
        log("  AUTOMATION FAILED (but will try to restart Audiobookshelf)")
        # Continue to restart anyway
    else:
        log("  SUCCESS: Series population completed")
    log("")

    # STEP 7: Restart Audiobookshelf
    log("STEP 7: Restarting Audiobookshelf")
    log("-" * 70)

    if not start_audiobookshelf(abs_path):
        log("  ERROR: Failed to restart Audiobookshelf")
        log("  You may need to start it manually")
        log("  AUTOMATION COMPLETED WITH ERRORS")
        return 1

    countdown(10, "Waiting for Audiobookshelf to fully start")
    log("")

    # Final verification
    log("=" * 70)
    log("FINAL VERIFICATION")
    log("-" * 70)

    if check_if_running():
        log("  SUCCESS: Audiobookshelf is running")
        log("")
        log("=" * 70)
        log("AUTOMATION COMPLETED SUCCESSFULLY")
        log("=" * 70)
        return 0
    else:
        log("  WARNING: Audiobookshelf may not be running")
        log("  You may need to start it manually")
        log("")
        log("=" * 70)
        log("AUTOMATION COMPLETED WITH WARNINGS")
        log("=" * 70)
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("")
        log("=" * 70)
        log("INTERRUPTED BY USER")
        log("=" * 70)
        sys.exit(130)
    except Exception as e:
        log("")
        log("=" * 70)
        log(f"FATAL ERROR: {e}")
        log("=" * 70)
        import traceback
        log("Traceback:")
        traceback.print_exc()
        sys.exit(1)
