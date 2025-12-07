import socket
import requests
import time

tracker_host = "t.myanonamouse.net"
tracker_url = "https://t.myanonamouse.net/announce"

print(f"--- Diagnosing connection to {tracker_host} ---")

# 1. DNS Resolution
try:
    ip = socket.gethostbyname(tracker_host)
    print(f"✓ DNS Resolution: {ip}")
except Exception as e:
    print(f"❌ DNS Resolution Failed: {e}")

# 2. TCP Connect (HTTPS port 443)
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5)
        result = s.connect_ex((tracker_host, 443))
        if result == 0:
            print("✓ TCP Connect (443): Success")
        else:
            print(f"❌ TCP Connect (443): Failed (Error {result})")
except Exception as e:
    print(f"❌ TCP Connect Error: {e}")

# 3. HTTP Request (Simulate Announce)
try:
    # MAM returns 400 or 403 for GET on announce without params, but it proves connectivity
    resp = requests.get(tracker_url, timeout=10)
    print(f"✓ HTTP Request: Status {resp.status_code} (This is good, it means we reached the server)")
except Exception as e:
    print(f"❌ HTTP Request Failed: {e}")
