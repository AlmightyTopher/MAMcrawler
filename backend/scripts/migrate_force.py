
import json
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Explicitly load .env
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(dotenv_path)

from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, Float, func, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# Define minimal Download model matching the schema
class Download(Base):
    __tablename__ = "downloads"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, index=True) # Soft link, no FK constraint enforced here to avoid dependency
    missing_book_id = Column(Integer) # Soft link

    title = Column(String(500), nullable=False)
    author = Column(String(500), nullable=True)
    source = Column(String(100), nullable=False, index=True)
    magnet_link = Column(Text, nullable=True)
    torrent_url = Column(Text, nullable=True)
    qbittorrent_hash = Column(String(255), nullable=True, index=True)
    qbittorrent_status = Column(String(100), nullable=True)
    status = Column(String(100), nullable=False, default="queued", index=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    last_attempt = Column(TIMESTAMP, nullable=True)
    next_retry = Column(TIMESTAMP, nullable=True, index=True)
    abs_import_status = Column(String(100), nullable=True)
    abs_import_error = Column(Text, nullable=True)
    date_queued = Column(TIMESTAMP, default=func.now(), index=True)
    date_completed = Column(TIMESTAMP, nullable=True)
    metadata_json = Column(Text, nullable=True)
    metadata_applied_at = Column(TIMESTAMP, nullable=True)
    integrity_status = Column(String(50), default="pending")
    release_edition = Column(String(50), nullable=True)
    quality_score = Column(Float, nullable=True)
    is_paid = Column(Integer, default=0)
    emergency_blocked = Column(Integer, default=0)
    paid_download_allowed = Column(Integer, default=1)
    freeze_timestamp = Column(TIMESTAMP, nullable=True)
    emergency_reason = Column(String(500), nullable=True)

    # NO RELATIONSHIPS

from backend.config import get_settings
settings = get_settings()

def migrate_force():
    print(f"Connecting to {settings.DATABASE_URL}")
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        json_path = os.path.join(settings.PROJECT_ROOT, 'audiobooks_to_download.json')
        if not os.path.exists(json_path):
            print("JSON file not found.")
            return

        with open(json_path, 'r') as f:
            data = json.load(f)

        print(f"Migrating {len(data)} items...")
        count = 0
        for item in data:
            title = item.get('title')
            author = item.get('author')
            
            exists = session.query(Download).filter(
                Download.title == title, 
                Download.author == author
            ).first()
            
            if not exists:
                new_dl = Download(
                    title=title,
                    author=author,
                    source="MAM_JSON_MIGRATION",
                    status="queued"
                )
                session.add(new_dl)
                count += 1
        
        session.commit()
        print(f"Success! Added {count} items.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    migrate_force()
