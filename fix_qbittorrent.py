
import requests
import time

QB_URL = "http://localhost:52095"
USERNAME = "TopherGutbrod"
PASSWORD = "Tesl@ismy#1"

def main():
    session = requests.Session()
    
    # 1. Login
    try:
        resp = session.post(f"{QB_URL}/api/v2/auth/login", data={'username': USERNAME, 'password': PASSWORD})
        if resp.text == "Fails.":
            print("Login failed!")
            return
        print("Login successful.")
    except Exception as e:
        print(f"Could not connect to qBittorrent: {e}")
        return

    # 2. Get Torrents
    try:
        resp = session.get(f"{QB_URL}/api/v2/torrents/info?filter=all")
        torrents = resp.json()
    except Exception as e:
        print(f"Failed to get torrents: {e}")
        return

    force_start_hashes = []
    recheck_hashes = []
    
    print(f"Found {len(torrents)} torrents total.")
    
    for t in torrents:
        state = t.get('state', 'unknown')
        name = t.get('name', 'Unknown')
        progress = t.get('progress', 0)
        
        # States: metaDL, allocating, downloading, pausedDL, queuedDL, stalledDL, checkingDL, error, missingFiles
        if state in ['queuedDL', 'stalledDL', 'metaDL', 'downloading']:
            # Force start to bypass queue limits and kickstart stalled ones
            print(f"Force Starting: [{state}] {name}")
            force_start_hashes.append(t['hash'])
            
        if state == 'missingFiles':
            # Missing files often need a recheck to realize they can just start downloading again (if 0%)
            # or to find the files if they reappeared.
            print(f"Force Rechecking (Missing Files): {name}")
            recheck_hashes.append(t['hash'])
            # Also force start it after recheck command just in case
            force_start_hashes.append(t['hash'])

    # 3. Actions
    if force_start_hashes:
        print(f"Force Starting {len(force_start_hashes)} torrents...")
        hashes_str = "|".join(force_start_hashes)
        session.post(f"{QB_URL}/api/v2/torrents/setForceStart", data={'hashes': hashes_str, 'value': 'true'})
        # Also resume in case they were paused
        session.post(f"{QB_URL}/api/v2/torrents/resume", data={'hashes': hashes_str})
        # And reannounce
        session.post(f"{QB_URL}/api/v2/torrents/reannounce", data={'hashes': hashes_str})

    if recheck_hashes:
        print(f"Rechecking {len(recheck_hashes)} torrents...")
        hashes_str = "|".join(recheck_hashes)
        session.post(f"{QB_URL}/api/v2/torrents/recheck", data={'hashes': hashes_str})
    
    print("Done. Applied Force Start and Recheck where needed.")

if __name__ == "__main__":
    main()
