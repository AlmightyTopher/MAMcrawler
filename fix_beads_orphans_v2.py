
import sqlite3
import os

db_path = r"C:\Users\dogma\Projects\MAMcrawler\beads-ui-analysis\.beads\beads.db"

if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Inspecting dependencies table schema...")
    cursor.execute("PRAGMA table_info(dependencies)")
    columns = cursor.fetchall()
    for col in columns:
        print(col)
        
    print("\nAttempting simplified cleanup based on schema inspection...")
    # Assuming 'issue_id' exists based on error "issue_id not in issues"
    # and looking for the other column which usually points to the other issue (e.g. 'blocked_by', 'blocks')
    # But for now, let's just delete rows where issue_id is invalid
    
    cursor.execute("DELETE FROM dependencies WHERE issue_id NOT IN (SELECT id FROM issues)")
    print(f"Deleted {cursor.rowcount} orphans by issue_id.")
    
    # Try to identify the other column
    col_names = [c[1] for c in columns]
    other_col = None
    if 'dependency_id' in col_names: other_col = 'dependency_id'
    elif 'blocked_by' in col_names: other_col = 'blocked_by'
    elif 'blocks' in col_names: other_col = 'blocks'
    
    if other_col:
        print(f"Checking secondary column: {other_col}")
        cursor.execute(f"DELETE FROM dependencies WHERE {other_col} NOT IN (SELECT id FROM issues)")
        print(f"Deleted {cursor.rowcount} orphans by {other_col}.")
    
    conn.commit()

    print("\nCleaning up labels...")
    cursor.execute("DELETE FROM labels WHERE issue_id NOT IN (SELECT id FROM issues)")
    print(f"Deleted {cursor.rowcount} orphaned labels.")
    
    print("\nCleaning up comments...")
    cursor.execute("DELETE FROM comments WHERE issue_id NOT IN (SELECT id FROM issues)")
    print(f"Deleted {cursor.rowcount} orphaned comments.")
    
    conn.commit()

except Exception as e:
    print(f"Error: {e}")

conn.close()
