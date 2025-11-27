"""
Edition Replacement Logic (Section 16).
Replaces inferior editions with superior ones based on quality rules.
"""

import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class EditionReplacement:
    """
    Handles edition replacement when superior versions are found.
    """
    
    def __init__(self, quality_filter):
        """
        Args:
            quality_filter: QualityFilter instance for scoring releases
        """
        self.quality_filter = quality_filter
        self.inferior_editions = []  # Track for seeding purposes
    
    def compare_editions(self, existing: Dict, new: Dict) -> str:
        """
        Compare two editions and determine which is superior.
        
        Args:
            existing: Existing edition metadata
            new: New edition metadata
            
        Returns:
            'existing', 'new', or 'equal'
        """
        existing_score = self.quality_filter._score_release(existing)
        new_score = self.quality_filter._score_release(new)
        
        logger.info(f"📊 Edition comparison:")
        logger.info(f"  Existing: {existing.get('title')} (Score: {existing_score})")
        logger.info(f"  New: {new.get('title')} (Score: {new_score})")
        
        if new_score > existing_score:
            logger.info(f"✓ New edition is superior (+{new_score - existing_score} points)")
            return 'new'
        elif existing_score > new_score:
            logger.info(f"✓ Existing edition is superior (+{existing_score - new_score} points)")
            return 'existing'
        else:
            logger.info(f"= Editions are equal quality")
            return 'equal'
    
    async def replace_edition(self,
                             existing_item_id: str,
                             existing_path: str,
                             new_torrent: Dict,
                             download_callback,
                             abs_client,
                             qbt_client) -> bool:
        """
        Replace existing edition with superior one.
        
        Workflow (Section 16):
        1. Mark existing as "Inferior Edition"
        2. Keep inferior seeding if beneficial
        3. Download superior edition
        4. Perform integrity check
        5. Perform full scan
        6. Update metadata
        7. Replace files in Audiobookshelf
        8. Remove inferior from library (but keep seeding)
        
        Args:
            existing_item_id: Audiobookshelf item ID
            existing_path: Path to existing audiobook files
            new_torrent: New superior torrent metadata
            download_callback: Async function to download torrent
            abs_client: Audiobookshelf API client
            qbt_client: qBittorrent API client
            
        Returns:
            True if replacement successful
        """
        logger.info(f"🔄 Starting edition replacement...")
        logger.info(f"  Existing: {existing_path}")
        logger.info(f"  New: {new_torrent.get('title')}")
        
        try:
            # Step 1: Mark existing as inferior
            logger.info("1️⃣ Marking existing edition as inferior...")
            self.inferior_editions.append({
                'abs_item_id': existing_item_id,
                'path': existing_path,
                'marked_at': None  # TODO: Add timestamp
            })
            
            # Step 2: Check if existing should keep seeding
            existing_torrent_hash = await self._get_torrent_hash(existing_path, qbt_client)
            keep_seeding = False
            
            if existing_torrent_hash:
                torrent_info = await qbt_client.get_torrent_info(existing_torrent_hash)
                # Keep seeding if ratio < 2.0 or still generating points
                if torrent_info:
                    ratio = torrent_info.get('ratio', 0)
                    if ratio < 2.0:
                        keep_seeding = True
                        logger.info(f"2️⃣ Keeping inferior edition seeding (ratio: {ratio:.2f})")
            
            # Step 3: Download superior edition
            logger.info("3️⃣ Downloading superior edition...")
            download_success = await download_callback(new_torrent)
            
            if not download_success:
                logger.error("✗ Failed to download superior edition")
                return False
            
            # Step 4: Integrity check (handled by download_callback)
            logger.info("4️⃣ Integrity check (handled by download workflow)")
            
            # Step 5: Full scan (handled by download_callback)
            logger.info("5️⃣ Full metadata scan (handled by download workflow)")
            
            # Step 6: Update metadata in Audiobookshelf
            logger.info("6️⃣ Updating Audiobookshelf metadata...")
            # Metadata update handled by scan workflow
            
            # Step 7: Replace files in Audiobookshelf
            logger.info("7️⃣ Replacing files in Audiobookshelf...")
            # Get new download path
            new_path = await self._get_download_path(new_torrent, qbt_client)
            
            if new_path:
                # Update library item to point to new files
                update_success = await abs_client.update_library_item_path(
                    existing_item_id,
                    new_path
                )
                
                if not update_success:
                    logger.error("✗ Failed to update Audiobookshelf path")
                    return False
            
            # Step 8: Remove inferior from active library
            logger.info("8️⃣ Removing inferior edition from library...")
            
            if not keep_seeding:
                # Can safely delete files
                logger.info("  Deleting inferior edition files...")
                await self._delete_files(existing_path)
                
                # Stop seeding in qBittorrent
                if existing_torrent_hash:
                    await qbt_client.delete_torrent(existing_torrent_hash, delete_files=False)
            else:
                # Keep seeding but remove from Audiobookshelf
                logger.info("  Keeping inferior edition seeding for ratio/points")
                # Files stay, just not in ABS library anymore
            
            logger.info("✅ Edition replacement complete!")
            return True
            
        except Exception as e:
            logger.error(f"✗ Edition replacement failed: {e}")
            return False
    
    async def _get_torrent_hash(self, file_path: str, qbt_client) -> Optional[str]:
        """Get torrent hash for a file path."""
        try:
            torrents = await qbt_client.get_torrents()
            for torrent in torrents:
                if file_path in torrent.get('save_path', ''):
                    return torrent.get('hash')
            return None
        except Exception as e:
            logger.error(f"Failed to get torrent hash: {e}")
            return None
    
    async def _get_download_path(self, torrent: Dict, qbt_client) -> Optional[str]:
        """Get download path for a torrent."""
        try:
            torrent_hash = torrent.get('hash')
            if not torrent_hash:
                return None
            
            torrent_info = await qbt_client.get_torrent_info(torrent_hash)
            if torrent_info:
                return torrent_info.get('save_path')
            
            return None
        except Exception as e:
            logger.error(f"Failed to get download path: {e}")
            return None
    
    async def _delete_files(self, file_path: str):
        """Delete audiobook files."""
        try:
            path = Path(file_path)
            
            if path.is_file():
                path.unlink()
                logger.info(f"  Deleted file: {path}")
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
                logger.info(f"  Deleted directory: {path}")
            
        except Exception as e:
            logger.error(f"Failed to delete files: {e}")
    
    def should_replace(self, existing: Dict, new: Dict) -> bool:
        """
        Determine if existing edition should be replaced.
        
        Args:
            existing: Existing edition metadata
            new: New edition metadata
            
        Returns:
            True if replacement recommended
        """
        comparison = self.compare_editions(existing, new)
        return comparison == 'new'
    
    def get_inferior_editions(self) -> list:
        """Get list of inferior editions being kept for seeding."""
        return self.inferior_editions.copy()
