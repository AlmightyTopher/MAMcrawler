"""
Minimal Audiobookshelf Automation Script
No loops, no verification, no fancy stuff - just sequential commands
"""

import subprocess
import time
from datetime import datetime

def log(message):
    """Simple logging with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

def kill_node():
    """Kill node.exe processes"""
    try:
        subprocess.run(['taskkill', '/F', '/IM', 'node.exe'],
                      capture_output=True,
                      timeout=10)
        log("Killed node.exe")
    except Exception as e:
        log(f"Kill node.exe failed (may not be running): {e}")

def start_audiobookshelf():
    """Start Audiobookshelf.exe"""
    abs_path = r"C:\Users\dogma\AppData\Local\Programs\Audiobookshelf\audiobookshelf.exe"
    try:
        subprocess.Popen([abs_path],
                        shell=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        log("Started Audiobookshelf")
    except Exception as e:
        log(f"Start Audiobookshelf failed: {e}")

def run_series_populator():
    """Run the series populator script"""
    script_path = r"C:\Users\dogma\Projects\MAMcrawler\simple_series_populator.py"
    try:
        result = subprocess.run(['python', script_path],
                               capture_output=True,
                               text=True,
                               timeout=300)  # 5 minute timeout
        log("Series populator completed")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except subprocess.TimeoutExpired:
        log("Series populator timed out after 5 minutes")
    except Exception as e:
        log(f"Series populator failed: {e}")

def main():
    log("=== Starting Minimal Automation ===")

    # Step 1: Kill node.exe
    log("Step 1: Killing node.exe...")
    kill_node()

    # Step 2: Wait 5 seconds
    log("Step 2: Waiting 5 seconds...")
    time.sleep(5)

    # Step 3: Start Audiobookshelf
    log("Step 3: Starting Audiobookshelf...")
    start_audiobookshelf()

    # Step 4: Wait 35 seconds for startup
    log("Step 4: Waiting 35 seconds for Audiobookshelf to start...")
    time.sleep(35)

    # Step 5: Kill node.exe again
    log("Step 5: Killing node.exe before series population...")
    kill_node()

    # Step 6: Wait 3 seconds
    log("Step 6: Waiting 3 seconds...")
    time.sleep(3)

    # Step 7: Run series populator
    log("Step 7: Running series populator...")
    run_series_populator()

    # Step 8: Start Audiobookshelf again
    log("Step 8: Starting Audiobookshelf final time...")
    start_audiobookshelf()

    # Step 9: Done
    log("=== Automation Complete ===")

if __name__ == "__main__":
    main()
