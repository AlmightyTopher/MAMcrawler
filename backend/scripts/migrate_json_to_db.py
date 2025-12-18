
import json
import os
import sys

from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Explicitly load .env
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
print(f"Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path)

from backend.database import get_db_context, init_db
from backend.models import Download, Book
from backend.config import get_settings

settings = get_settings()

def migrate_json_queue():
    """Migrate audiobooks_to_download.json to Postgres downloads table"""
    json_path = os.path.join(settings.PROJECT_ROOT, 'audiobooks_to_download.json')
    
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return

    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            
        print(f"Found {len(data)} books in JSON.")
        
        with get_db_context() as db:
            count = 0
            for item in data:
                title = item.get('title')
                author = item.get('author')
                
                # Check if exists
                exists = db.query(Download).filter(
                    Download.title == title, 
                    Download.author == author
                ).first()
                
                if not exists:
                    # Create new download entry
                    new_dl = Download(
                        title=title,
                        author=author,
                        source="MAM_JSON_MIGRATION",
                        status="queued",
                        date_queued=None # Use default now()
                    )
                    db.add(new_dl)
                    count += 1
            
            db.commit()
            print(f"Successfully migrated {count} new items to 'downloads' table.")
            
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    init_db() # Ensure tables exist
    migrate_json_queue()
