import os
import signal
import sys
import time

try:
    import psutil
except ImportError:
    print("psutil not found")
    sys.exit(1)

for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = proc.info['cmdline']
        if cmdline and 'api_server.py' in ' '.join(cmdline):
            print(f"Found api_server.py with PID {proc.info['pid']}")
            proc.kill()
            print("Killed.")
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
