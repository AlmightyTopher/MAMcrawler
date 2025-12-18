
import sqlite3
import os

db_path = r"C:\Users\dogma\Projects\MAMcrawler\beads-ui-analysis\.beads\beads.db"

if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Identify non-MAM issues (not starting with MAMcrawler-)
    cursor.execute("SELECT id, title FROM issues WHERE id NOT LIKE 'MAMcrawler-%'")
    rows = cursor.fetchall()
    
    if rows:
        print(f"Found {len(rows)} non-MAM issues:")
        ids_to_delete = []
        for row in rows:
            print(f" - {row[0]}: {row[1]}")
            ids_to_delete.append(row[0])
            
        print(f"Deleting {len(ids_to_delete)} issues...")
        # Use executemany for safer deletion
        cursor.executemany("DELETE FROM issues WHERE id = ?", [(id,) for id in ids_to_delete])
        conn.commit()
        print(f"Successfully deleted {cursor.rowcount} issues.")
    else:
        print("No non-MAM issues found.")

except sqlite3.OperationalError as e:
    print(f"SQLite Error: {e}")

conn.close()
