import os
import logging
from dotenv import load_dotenv
import qbittorrentapi

load_dotenv()

def check_qbit_logs():
    host = os.getenv('QB_HOST', 'http://localhost')
    port = os.getenv('QB_PORT', '8080')
    username = os.getenv('QB_USERNAME', 'admin')
    password = os.getenv('QB_PASSWORD', '')
    
    if not host.startswith('http'):
        host = f'http://{host}'
    if str(port) not in host:
        host = f"{host}:{port}"
        
    try:
        qbt = qbittorrentapi.Client(host=host, username=username, password=password)
        qbt.auth_log_in()
        
        print("--- Recent qBittorrent Logs ---")
        logs = qbt.log.main(last_known_id=-1)
        for log in logs[-20:]: # Last 20 logs
            print(f"[{log.timestamp}] {log.message}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_qbit_logs()
