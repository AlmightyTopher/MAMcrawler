import time
import requests
import subprocess
import sys
from mamcrawler.status_reporter import StatusReporter

def run_mock_task():
    print("Starting mock task...")
    with StatusReporter("Test Task", total=5) as status:
        for i in range(5):
            print(f"Update {i}")
            status.update(i, f"Processing item {i}", "Testing")
            time.sleep(2)
        status.complete("Done")

def check_api():
    try:
        url = "http://localhost:8081/api/status"
        res = requests.get(url)
        data = res.json()
        task = data.get('active_task')
        print(f"API Task Status: {task}")
    except Exception as e:
        print(f"API Check Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run_mock_task()
    else:
        # Start mock task in background
        proc = subprocess.Popen([sys.executable, "test_dashboard_live.py", "run"])
        time.sleep(2)
        # Check API
        for _ in range(5):
            check_api()
            time.sleep(2)
        proc.wait()
