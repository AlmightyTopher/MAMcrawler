
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Load Env
from dotenv import load_dotenv
load_dotenv(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env")))

from backend.integrations.audiobookshelf_hardcover_sync import AudiobookShelfHardcoverSync, AudiobookMetadata
from dataclasses import dataclass

# Mock HardcoverBook
@dataclass
class MockAuthor:
    name: str

@dataclass
class MockHardcoverBook:
    id: int
    title: str
    description: str
    authors: list
    def get_primary_series(self):
        return ("Mock Series", 1.0)

async def test_log_creation():
    print("Initializing Sync Service...")
    # Dummy credentials
    sync = AudiobookShelfHardcoverSync("http://localhost", "api_key", "token")
    
    print("Recording mock sync...")
    abs_meta = AudiobookMetadata(
        id="test_abs_id_123",
        title="Test Book",
        author="Test Author"
    )
    
    hc_book = MockHardcoverBook(
        id=999,
        title="Test Book (Hardcover)",
        description="Desc",
        authors=[MockAuthor("Test Author")]
    )
    
    changes = {"title": "Updated from Hardcover"}
    
    sync._record_sync("test_abs_id_123", abs_meta, hc_book, changes)
    print("Sync recorded.")
    
    # Verify in DB
    from backend.database import get_db_context
    from backend.models.hardcover_sync_log import HardcoverSyncLog
    
    with get_db_context() as db:
        log = db.query(HardcoverSyncLog).filter_by(abs_item_id="test_abs_id_123").order_by(HardcoverSyncLog.id.desc()).first()
        if log:
            print(f"VERIFIED: Found log entry ID {log.id}")
            print(f"ABS ID: {log.abs_item_id}")
            print(f"Changes: {log.changes_made}")
        else:
            print("FAILED: Log entry not found in DB")

if __name__ == "__main__":
    asyncio.run(test_log_creation())
