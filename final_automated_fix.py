#!/usr/bin/env python3
"""
Final Automated Fix - Handles the complete series population workflow

This script:
1. Kills any running Audiobookshelf process
2. Starts Audiobookshelf (repairs database)
3. Waits 60 seconds
4. Kills Audiobookshelf
5. Waits 5 seconds
6. Runs simple_series_populator.py
7. Done - user manually restarts Audiobookshelf

No fancy code, no loops, just sequential steps.
"""

import subprocess
import time
import sys
import os
from datetime import datetime

def log(msg):
    """Print with timestamp"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def main():
    os.chdir(r"C:\Users\dogma\Projects\MAMcrawler")

    log("=" * 80)
    log("AUDIOBOOKSHELF SERIES POPULATION - AUTOMATED")
    log("=" * 80)
    log("")

    abs_exe = r"C:\Users\dogma\AppData\Local\Programs\Audiobookshelf\audiobookshelf.exe"

    # Step 1: Kill any running processes
    log("Step 1: Stopping any running Audiobookshelf processes...")
    subprocess.run("taskkill /F /IM node.exe 2>nul", shell=True)
    time.sleep(2)
    log("  Done")
    log("")

    # Step 2: Start Audiobookshelf
    log("Step 2: Starting Audiobookshelf (for database repair)...")
    try:
        subprocess.Popen(abs_exe, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log("  Process launched")
    except Exception as e:
        log(f"  ERROR: Could not start: {e}")
        return 1
    log("")

    # Step 3: Wait 60 seconds
    log("Step 3: Waiting 60 seconds for database repair...")
    for i in range(60, 0, -1):
        if i % 10 == 0:
            log(f"  {i}s remaining...")
        time.sleep(1)
    log("  Done")
    log("")

    # Step 4: Stop Audiobookshelf
    log("Step 4: Stopping Audiobookshelf (for database access)...")
    subprocess.run("taskkill /F /IM node.exe 2>nul", shell=True)
    time.sleep(5)
    log("  Done")
    log("")

    # Step 5: Run the populator
    log("Step 5: Running series populator...")
    result = subprocess.run(
        [sys.executable, "simple_series_populator.py"],
        capture_output=False
    )
    log("")

    if result.returncode == 0:
        log("Step 5: Series populator completed successfully!")
    else:
        log("Step 5: Series populator had errors (see above)")
    log("")

    # Done
    log("=" * 80)
    log("AUTOMATION COMPLETE")
    log("=" * 80)
    log("")
    log("NEXT STEPS:")
    log("1. Manually start Audiobookshelf")
    log("   Or run: START \"C:\\Users\\dogma\\AppData\\Local\\Programs\\Audiobookshelf\\audiobookshelf.exe\"")
    log("")
    log("2. Wait 60 seconds for it to fully start")
    log("")
    log("3. Open browser: http://localhost:13378")
    log("")
    log("4. Check Books section - series should now be populated!")
    log("")

    return 0

if __name__ == "__main__":
    sys.exit(main())
