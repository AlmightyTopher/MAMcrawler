#!/usr/bin/env python3
"""
REAL-TIME STATUS DASHBOARD
Shows live progress of workflow execution with all metrics
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import time
import sys

def get_workflow_status():
    """Get workflow execution status"""
    log_file = Path("real_workflow_execution.log")

    if not log_file.exists():
        return {
            'phase': 'NOT_STARTED',
            'items_loaded': 0,
            'errors': 0
        }

    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()

        phase = "SCANNING"
        items_loaded = 0
        errors = 0

        # Get latest status
        for line in reversed(lines[-50:]):
            if '[PHASE]' in line and 'PHASE' in line:
                phase = line.split('[PHASE]')[1].strip()
                break

        # Count items loaded
        for line in lines[-20:]:
            if '[SCAN ]' in line and 'Loaded' in line:
                try:
                    parts = line.split('Loaded ')
                    if len(parts) > 1:
                        count_str = parts[1].split(' items')[0]
                        items_loaded = int(count_str)
                except:
                    pass

        # Count errors
        for line in lines[-100:]:
            if '[ERROR]' in line or '[FAIL]' in line:
                errors += 1

        return {
            'phase': phase,
            'items_loaded': items_loaded,
            'errors': errors,
            'last_line': lines[-1].strip()[-60:] if lines else ''
        }
    except:
        return {'phase': 'ERROR', 'items_loaded': 0, 'errors': 0}

def get_monitor_checkpoint():
    """Get latest monitor checkpoint"""
    checkpoint_file = Path("monitor_status.json")

    if not checkpoint_file.exists():
        return None

    try:
        with open(checkpoint_file, 'r') as f:
            return json.load(f)
    except:
        return None

def get_book_stats():
    """Get book statistics from database"""
    db_file = Path("downloaded_books.db")

    if not db_file.exists():
        return {
            'queued': 0,
            'downloading': 0,
            'downloaded': 0,
            'added_to_abs': 0,
            'total_size': 0,
            'total_value': 0
        }

    try:
        conn = sqlite3.connect(db_file)
        c = conn.cursor()

        c.execute("SELECT COUNT(*) FROM books WHERE status = 'queued'")
        queued = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM books WHERE status = 'downloading'")
        downloading = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM books WHERE status = 'downloaded'")
        downloaded = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM books WHERE status = 'added_to_abs'")
        added_to_abs = c.fetchone()[0]

        c.execute("SELECT SUM(file_size) FROM books WHERE status IN ('downloaded', 'added_to_abs')")
        total_size = c.fetchone()[0] or 0

        c.execute("SELECT SUM(estimated_value) FROM books WHERE status IN ('downloaded', 'added_to_abs')")
        total_value = c.fetchone()[0] or 0

        conn.close()

        return {
            'queued': queued,
            'downloading': downloading,
            'downloaded': downloaded,
            'added_to_abs': added_to_abs,
            'total_size_gb': round(total_size / (1024**3), 2) if total_size else 0,
            'total_value': round(total_value, 2) if total_value else 0
        }
    except:
        return {
            'queued': 0,
            'downloading': 0,
            'downloaded': 0,
            'added_to_abs': 0,
            'total_size': 0,
            'total_value': 0
        }

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def print_dashboard():
    """Print the dashboard"""
    clear_screen()

    workflow = get_workflow_status()
    checkpoint = get_monitor_checkpoint()
    books = get_book_stats()

    print("=" * 100)
    print("AUDIOBOOK ACQUISITION WORKFLOW - REAL-TIME DASHBOARD")
    print("=" * 100)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("")

    # Workflow Status
    print("WORKFLOW STATUS")
    print("-" * 100)
    print(f"Current Phase:          {workflow['phase']}")
    print(f"Items Scanned:          {workflow['items_loaded']:,}")
    print(f"Workflow Errors:        {workflow['errors']}")
    print(f"Last Activity:          {workflow['last_line']}")
    print("")

    # Books Status
    print("BOOK QUEUE & DOWNLOAD STATUS")
    print("-" * 100)
    print(f"Queued:                 {books['queued']} books")
    print(f"Downloading:            {books['downloading']} books")
    print(f"Downloaded:             {books['downloaded']} books")
    print(f"Added to ABS:           {books['added_to_abs']} books")
    print(f"Total Size:             {books['total_size_gb']} GB")
    print(f"Estimated Total Value:  ${books['total_value']:.2f}")
    print("")

    # System Status
    if checkpoint:
        print("SYSTEM STATUS (Latest Checkpoint)")
        print("-" * 100)
        checkpoint_num = checkpoint.get('checkpoint_number', 0)
        elapsed = checkpoint.get('elapsed_minutes', 0)

        print(f"Checkpoint #:           {checkpoint_num}")
        print(f"Elapsed Time:           {elapsed:.1f} minutes")

        systems = checkpoint.get('systems', {})
        print(f"AudiobookShelf:         {systems.get('abs', {}).get('status', 'UNKNOWN')}")
        print(f"qBittorrent:            {systems.get('qbittorrent', {}).get('status', 'UNKNOWN')}")
        print(f"Prowlarr:               {systems.get('prowlarr', {}).get('status', 'UNKNOWN')}")

        # Issues
        issues = checkpoint.get('issues_and_repairs', [])
        if issues:
            print(f"\nISSUES DETECTED:        {len(issues)}")
            for issue in issues[:3]:  # Show first 3
                print(f"  - {issue['issue']} [{issue['status']}]")
        else:
            print("ISSUES:                 None")

        print("")

    # Summary
    total_books = books['queued'] + books['downloading'] + books['downloaded'] + books['added_to_abs']
    print("SUMMARY")
    print("-" * 100)
    print(f"Total Books in Pipeline: {total_books}")
    print(f"Science Fiction Target:  10 books")
    print(f"Fantasy Target:          10 books")
    print(f"Combined Target:         20 books")
    print("")

    print("=" * 100)
    print("Refreshing automatically. Press Ctrl+C to exit.")
    print("=" * 100)

def run_dashboard(refresh_interval: int = 10):
    """Run the dashboard with auto-refresh"""
    try:
        while True:
            print_dashboard()
            time.sleep(refresh_interval)
    except KeyboardInterrupt:
        print("\n\nDashboard stopped.")
        sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Print once and exit
        print_dashboard()
    else:
        # Run continuous dashboard
        run_dashboard(refresh_interval=10)
