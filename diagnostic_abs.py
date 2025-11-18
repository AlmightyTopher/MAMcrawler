"""
Diagnostic script to understand Audiobookshelf setup
"""

import subprocess
import socket
import json
from pathlib import Path

print("=" * 80)
print("AUDIOBOOKSHELF DIAGNOSTIC INFORMATION")
print("=" * 80)
print()

# 1. Check if running
print("1. PROCESS STATUS")
print("-" * 80)
result = subprocess.run("tasklist | findstr /i node", shell=True, capture_output=True, text=True)
if "node" in result.stdout:
    print("[RUNNING] Audiobookshelf is active")
    print(result.stdout.strip())
else:
    print("[STOPPED] Audiobookshelf is not running")
print()

# 2. Check port
print("2. PORT AVAILABILITY")
print("-" * 80)
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(("localhost", 13378))
    sock.close()
    if result == 0:
        print("[OPEN] Port 13378 is listening")
    else:
        print("[CLOSED] Port 13378 is not responding")
except Exception as e:
    print(f"[ERROR] Could not check port: {e}")
print()

# 3. Check database location
print("3. DATABASE LOCATION")
print("-" * 80)
db_search_paths = [
    "C:\\Users\\dogma\\Audiobookshelf",
    "C:\\Users\\dogma\\AppData\\Local\\Audiobookshelf",
    "C:\\Users\\dogma\\AppData\\Roaming\\Audiobookshelf",
    "F:/Audiobookshelf",
    Path.home() / "Audiobookshelf",
]

found = False
for path in db_search_paths:
    p = Path(path) if isinstance(path, str) else path
    if p.exists():
        print(f"[FOUND] {p}")
        # Check for database files
        db_files = list(p.glob("**/absdatabase.sqlite")) + \
                   list(p.glob("**/database.sqlite")) + \
                   list(p.glob("**/metadata.sqlite"))
        for db_file in db_files:
            size_mb = db_file.stat().st_size / (1024*1024)
            print(f"       - {db_file.name} ({size_mb:.1f} MB)")
        found = True

if not found:
    print("[NOT FOUND] Standard locations checked but no database found")
print()

# 4. Check for API key file or config
print("4. CONFIGURATION FILES")
print("-" * 80)
config_paths = [
    Path("C:\\Users\\dogma\\Audiobookshelf\\config.json"),
    Path("C:\\Users\\dogma\\Audiobookshelf\\settings.json"),
    Path("C:\\Users\\dogma\\AppData\\Local\\Audiobookshelf\\config.json"),
]

for config_file in config_paths:
    if config_file.exists():
        print(f"[FOUND] {config_file}")
        try:
            with open(config_file) as f:
                config = json.load(f)
                if "apiKey" in config or "token" in config:
                    print("       - Contains API key/token info")
        except:
            pass

print()
print("=" * 80)
print("RECOMMENDATION")
print("=" * 80)
print()
print("Based on the diagnostic info above:")
print()
print("Option 1: Use Database Directly (if found)")
print("  - Stop Audiobookshelf")
print("  - Use the database populator scripts")
print("  - Restart Audiobookshelf")
print()
print("Option 2: Use API (if you have/can generate API key)")
print("  - Get API key from Audiobookshelf admin panel")
print("  - Use api_series_populator.py with the key")
print()
print("Option 3: Manual Population via UI")
print("  - Open http://localhost:13378")
print("  - Manually add series through the web interface")
print()
