"""
Hardcover User Synchronization Service

Manages synchronization of individual user progress from AudiobookShelf to Hardcover.app.
- Maintains a mapping of ABS Users to Hardcover API Tokens.
- Syncs "Read" status and progress.
"""

import asyncio
import logging
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.integrations.hardcover_client import HardcoverClient
from backend.integrations.abs_client import AudiobookshelfClient

logger = logging.getLogger(__name__)

class HardcoverUserService:
    def __init__(
        self,
        abs_base_url: str,
        abs_api_key: str,
        db_path: str = "hardcover_user_sync.db"
    ):
        self.abs_client = AudiobookshelfClient(abs_base_url, abs_api_key)
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize user mapping database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_mappings (
                    abs_user_id TEXT PRIMARY KEY,
                    abs_username TEXT,
                    hardcover_token TEXT,
                    last_synced_at TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()

    def register_user(self, abs_username: str, hardcover_token: str) -> bool:
        """
        Register a user for Hardcover sync.
        
        1. Verifies ABS user exists.
        2. Verifies Hardcover token is valid.
        3. Saves mapping.
        """
        # Run async verification in sync context if needed, or assume caller handles loop
        # For simplicity in this service class, we'll assume we are called from an async context
        # but since this method is synchronous for DB ops, we might need a helper.
        # Let's make this method async.
        return False # Placeholder if not async, but we will define async below

    async def register_user_async(self, abs_username: str, hardcover_token: str) -> Dict[str, Any]:
        """
        Async registration of user.
        """
        async with self.abs_client:
            # 1. Verify ABS User
            users_resp = await self.abs_client.users.get_users()
            users = users_resp.get("users", [])
            target_user = next((u for u in users if u["username"].lower() == abs_username.lower()), None)
            
            if not target_user:
                return {"success": False, "error": f"ABS User '{abs_username}' not found"}

            # 2. Verify Hardcover Token
            async with HardcoverClient(hardcover_token) as hc:
                me = await hc.get_me()
                if not me:
                    return {"success": False, "error": "Invalid Hardcover token"}
                
                hc_username = me.get("username")

            # 3. Save to DB
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO user_mappings 
                        (abs_user_id, abs_username, hardcover_token, last_synced_at, is_active)
                        VALUES (?, ?, ?, ?, 1)
                    """, (target_user["id"], target_user["username"], hardcover_token, datetime.now()))
                    conn.commit()
                
                logger.info(f"Registered {abs_username} -> Hardcover ({hc_username})")
                return {"success": True, "hardcover_user": hc_username, "abs_user": target_user["username"]}
                
            except Exception as e:
                logger.error(f"DB Error: {e}")
                return {"success": False, "error": str(e)}

    async def get_registered_users(self) -> List[Dict]:
        """Get list of all registered users"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM user_mappings WHERE is_active = 1")
            return [dict(row) for row in cursor.fetchall()]

    async def sync_all_users(self) -> List[Dict]:
        """
        Sync progress for all registered users.
        """
        results = []
        registered = await self.get_registered_users()
        
        async with self.abs_client:
            for user_map in registered:
                res = await self.sync_single_user(user_map)
                results.append(res)
                
        return results

    async def sync_single_user(self, user_map: Dict) -> Dict:
        """Sync a specific user"""
        abs_id = user_map["abs_user_id"]
        token = user_map["hardcover_token"]
        username = user_map["abs_username"]
        
        logger.info(f"Syncing user: {username}")
        stats = {"synced": 0, "failed": 0, "skipped": 0, "errors": []}
        
        try:
            # Get ABS User Progress
            # We explicitly fetch the user object to get mediaProgress
            user_data = await self.abs_client.users.get_user(abs_id)
            media_progress = user_data.get("mediaProgress", [])
            
            # Filter for finished books
            finished_items = [
                item for item in media_progress 
                if item.get("isFinished", False)
            ]
            
            if not finished_items:
                logger.info(f"No finished books for {username}")
                return {"user": username, "status": "no_data", "stats": stats}

            async with HardcoverClient(token) as hc:
                for item in finished_items:
                    # book_id = item["mediaItem"]["id"] # Unreliable
                    book_id = item["mediaItemId"]
                    
                    # Need to fetch the Book details to get Title/Author for resolution
                    try:
                        # Optimization: mediaProgress often contains a mini-mediaItem object
                        media_item = item.get("mediaItem")
                        metadata = {}
                        if media_item:
                             metadata = media_item.get("media", {}).get("metadata", {})
                        
                        title = metadata.get("title")
                        author = metadata.get("authorName")
                        
                        if not title or not author:
                            # Fetch full book details if missing
                            full_book = await self.abs_client.get_book_by_id(item["mediaItemId"])
                            metadata = full_book.get("media", {}).get("metadata", {})
                            title = metadata.get("title")
                            author = metadata.get("authorName")

                        if not title or not author:
                            logger.warning(f"Skipping {item['mediaItemId']} - missing metadata")
                            stats["skipped"] += 1
                            continue

                        # Resolve on Hardcover
                        match = await hc.resolve_book(title=title, author=author)
                        
                        if match.success and match.book:
                            # Check status
                            current_status = await hc.get_user_book_status(match.book.id)
                            
                            if current_status != "read":
                                logger.info(f"Marking '{title}' as Read for {username}")
                                success = await hc.update_book_status(match.book.id, "read")
                                if success:
                                    stats["synced"] += 1
                                else:
                                    stats["failed"] += 1
                            else:
                                stats["skipped"] += 1 # Already read
                        else:
                            stats["failed"] += 1
                            stats["errors"].append(f"Could not resolve: {title}")
                            
                    except Exception as e:
                        logger.error(f"Error syncing item {item.get('id')}: {e}")
                        stats["failed"] += 1
                        
            # Update last synced time
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE user_mappings SET last_synced_at = ? WHERE abs_user_id = ?", 
                    (datetime.now(), abs_id)
                )
                conn.commit()

            return {"user": username, "status": "success", "stats": stats}

        except Exception as e:
            logger.error(f"Sync failed for {username}: {e}")
            return {"user": username, "status": "error", "error": str(e)}

# ============================================================================
# CLI / Demo
# ============================================================================
async def demo():
    import os
    abs_url = os.getenv("ABS_URL", "http://localhost:13378")
    abs_token = os.getenv("ABS_TOKEN")
    
    if not abs_token:
        print("Set ABS_TOKEN env var")
        return

    service = HardcoverUserService(abs_url, abs_token)
    
    print("1. List Registered Users")
    print("2. Register User")
    print("3. Sync All")
    
    # In a real CLI we would take input, for now just list
    users = await service.get_registered_users()
    print(f"Registered users: {len(users)}")
    for u in users:
        print(f" - {u['abs_username']} (Last sync: {u['last_synced_at']})")

if __name__ == "__main__":
    asyncio.run(demo())
