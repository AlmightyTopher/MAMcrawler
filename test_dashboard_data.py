import requests
import json
import time

def test_api_status():
    print("Testing /api/status endpoint...")
    try:
        response = requests.get("http://localhost:8081/api/status")
        if response.status_code == 200:
            data = response.json()
            print("\nAPI Status: OK")
            
            # 1. Check Stats
            stats = data.get('stats', {})
            print(f"\n[Panel 1] MAM Stats:")
            print(f"  Ratio: {stats.get('ratio')}")
            print(f"  Buffer: {stats.get('buffer')}")
            print(f"  Shorthand: {stats.get('shorthand')}")
            
            # 2. Check Queue
            queue = data.get('queue', [])
            print(f"\n[Panel 2] Active Downloads (Queue):")
            print(f"  Count: {len(queue)}")
            if queue:
                print(f"  First Item: {queue[0]}")
            else:
                print("  (Queue is empty, which might be normal)")
                
            # 3. Check Services
            services = data.get('services', [])
            print(f"\n[Panel 3] System Health:")
            for s in services:
                print(f"  {s['name']}: {s['status']}")
                
            # 4. Check Logs
            logs = data.get('recent_logs', [])
            print(f"\n[Panel 4] System Logs:")
            print(f"  Count: {len(logs)}")
            if logs:
                print(f"  Latest: {logs[-1]}")
                
        else:
            print(f"API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    # Wait a moment for server to fully start
    time.sleep(2)
    test_api_status()
