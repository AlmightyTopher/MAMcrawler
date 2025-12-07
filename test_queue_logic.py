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
            
            # Check Queue
            queue = data.get('queue', [])
            print(f"\n[Panel 2] Active Downloads (Queue):")
            print(f"  Count: {len(queue)}")
            
            for i, item in enumerate(queue[:5]):
                print(f"  [{i}] {item['name'][:40]}... | {item['state']} | {item['size']} | {item['dlspeed']} | {item['upspeed']}")
                
        else:
            print(f"API Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    time.sleep(2)
    test_api_status()
