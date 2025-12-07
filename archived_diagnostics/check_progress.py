"""
Quick progress checker for the stealth crawler
"""

import json
from pathlib import Path
from datetime import datetime

def check_progress():
    """Check and display current progress."""
    state_file = Path("crawler_state.json")

    if not state_file.exists():
        print("❌ No crawler state file found. Crawler may not have started yet.")
        return

    try:
        with open(state_file, 'r') as f:
            state = json.load(f)

        completed = state.get('completed', [])
        failed = state.get('failed', [])
        last_run = state.get('last_run')

        print("="*70)
        print("📊 STEALTH CRAWLER PROGRESS")
        print("="*70)
        print(f"✅ Completed: {len(completed)} guides")
        print(f"❌ Failed: {len(failed)} guides")
        print(f"🕐 Last updated: {last_run if last_run else 'Never'}")
        print("="*70)

        if failed:
            print("\n⚠️  Failed guides:")
            for fail in failed[-5:]:  # Show last 5 failures
                print(f"   - {fail.get('title', 'Unknown')}: {fail.get('error', 'No error info')}")

        # Check log file for latest activity
        log_file = Path("stealth_crawler.log")
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_10 = lines[-10:] if len(lines) >= 10 else lines

                print("\n📝 Latest activity (last 10 lines):")
                print("-"*70)
                for line in last_10:
                    print(line.strip())

        print("\n" + "="*70)

    except Exception as e:
        print(f"❌ Error reading state: {e}")

if __name__ == "__main__":
    check_progress()
