
import sqlite3
import os

db_path = r"C:\Users\dogma\Projects\MAMcrawler\beads-ui-analysis\.beads\beads.db"

if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check current status
try:
    cursor.execute("SELECT id, title, status FROM issues WHERE id = ?", ("MAMcrawler-vu3",))
    row = cursor.fetchone()
    
    if row:
        print(f"Current state: ID={row[0]}, Title='{row[1]}', Status='{row[2]}'")
        
        if row[2] != 'closed':
            print("Updating status to 'closed'...")
            cursor.execute("UPDATE issues SET status = 'closed', closed_at = strftime('%s', 'now') * 1000 WHERE id = ?", ("MAMcrawler-vu3",))
            conn.commit()
            print("Update committed.")
            
            # Verify
            cursor.execute("SELECT status FROM issues WHERE id = ?", ("MAMcrawler-vu3",))
            new_row = cursor.fetchone()
            print(f"New Status: '{new_row[0]}'")
        else:
            print("Issue is already closed.")
    else:
        print("Issue MAMcrawler-vu3 not found in DB.")

except sqlite3.OperationalError as e:
    print(f"SQLite Error: {e}")
    # Fallback to check tables if schema is different
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print("Tables:", cursor.fetchall())

conn.close()
