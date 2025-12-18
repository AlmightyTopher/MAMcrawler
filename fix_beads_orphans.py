
import sqlite3
import os

db_path = r"C:\Users\dogma\Projects\MAMcrawler\beads-ui-analysis\.beads\beads.db"

if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Checking for orphaned dependencies...")
    # Find orphaned dependencies (issue_id or dependency_id pointing to non-existent issues)
    cursor.execute("""
        SELECT count(*) FROM dependencies 
        WHERE issue_id NOT IN (SELECT id FROM issues)
        OR dependency_id NOT IN (SELECT id FROM issues)
    """)
    orphaned_count = cursor.fetchone()[0]
    
    if orphaned_count > 0:
        print(f"Found {orphaned_count} orphaned dependencies. Cleaning up...")
        cursor.execute("""
            DELETE FROM dependencies 
            WHERE issue_id NOT IN (SELECT id FROM issues)
            OR dependency_id NOT IN (SELECT id FROM issues)
        """)
        conn.commit()
        print(f"Deleted {cursor.rowcount} orphaned dependencies.")
    else:
        print("No orphaned dependencies found.")

    # Also check labels just in case
    print("Checking for orphaned labels...")
    cursor.execute("""
        SELECT count(*) FROM labels 
        WHERE issue_id NOT IN (SELECT id FROM issues)
    """)
    orphaned_labels = cursor.fetchone()[0]
    
    if orphaned_labels > 0:
        print(f"Found {orphaned_labels} orphaned labels. Cleaning up...")
        cursor.execute("""
            DELETE FROM labels 
            WHERE issue_id NOT IN (SELECT id FROM issues)
        """)
        conn.commit()
        print(f"Deleted {cursor.rowcount} orphaned labels.")
    else:
        print("No orphaned labels found.")

except sqlite3.OperationalError as e:
    print(f"SQLite Error: {e}")
    # List tables to help diagnose
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print("Tables:", [row[0] for row in cursor.fetchall()])

conn.close()
