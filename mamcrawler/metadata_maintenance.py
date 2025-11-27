"""
Weekly/Monthly Metadata Maintenance (Sections 3, 12).
Scheduled metadata updates and drift correction.
"""

import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class MetadataMaintenance:
    """
    Handles scheduled metadata maintenance and drift correction.
    """
    
    def __init__(self, metadata_scanner, abs_client, goodreads):
        """
        Args:
            metadata_scanner: MetadataScanner instance
            abs_client: Audiobookshelf API client
            goodreads: GoodreadsMetadata instance
        """
        self.scanner = metadata_scanner
        self.abs_client = abs_client
        self.goodreads = goodreads
        self.last_weekly_scan = None
        self.last_monthly_scan = None
    
    async def weekly_scan(self, abs_library: List[Dict]) -> Dict:
        """
        Weekly metadata scan (Section 3).
        
        Scans books added in the last 13 days for missing metadata.
        
        Args:
            abs_library: Current Audiobookshelf library
            
        Returns:
            Dict with scan results
        """
        logger.info("="*70)
        logger.info("📅 WEEKLY METADATA SCAN")
        logger.info("="*70)
        
        # Filter books added in last 13 days
        cutoff_date = datetime.now() - timedelta(days=13)
        recent_books = self._filter_recent_books(abs_library, cutoff_date)
        
        logger.info(f"📚 Found {len(recent_books)} books added in last 13 days")
        
        results = {
            'scanned': 0,
            'updated': 0,
            'errors': 0,
            'books': []
        }
        
        for book in recent_books:
            try:
                logger.info(f"📖 Scanning: {book.get('title')} by {book.get('author')}")
                
                # Check for missing metadata
                needs_update = self._needs_metadata_update(book)
                
                if needs_update:
                    # Perform full scan
                    updated = await self._update_book_metadata(book)
                    
                    if updated:
                        results['updated'] += 1
                        results['books'].append(book.get('title'))
                
                results['scanned'] += 1
                
                # Rate limiting
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error scanning {book.get('title')}: {e}")
                results['errors'] += 1
        
        self.last_weekly_scan = datetime.now()
        
        logger.info("="*70)
        logger.info(f"✅ WEEKLY SCAN COMPLETE")
        logger.info(f"  Scanned: {results['scanned']}")
        logger.info(f"  Updated: {results['updated']}")
        logger.info(f"  Errors: {results['errors']}")
        logger.info("="*70)
        
        return results
    
    async def monthly_scan(self, abs_library: List[Dict]) -> Dict:
        """
        Monthly metadata drift correction (Section 12).
        
        Re-queries Goodreads for all books to correct drift.
        
        Args:
            abs_library: Current Audiobookshelf library
            
        Returns:
            Dict with scan results
        """
        logger.info("="*70)
        logger.info("📅 MONTHLY METADATA DRIFT CORRECTION")
        logger.info("="*70)
        
        results = {
            'scanned': 0,
            'updated': 0,
            'errors': 0,
            'drift_detected': 0,
            'books': []
        }
        
        logger.info(f"📚 Scanning {len(abs_library)} books for metadata drift...")
        
        for book in abs_library:
            try:
                title = book.get('title')
                author = book.get('author')
                
                if not title or not author:
                    continue
                
                logger.info(f"📖 Checking: {title} by {author}")
                
                # Re-query Goodreads
                goodreads_data = await self.goodreads.search_book(title, author)
                
                if goodreads_data:
                    # Compare with existing metadata
                    drift = self._detect_drift(book, goodreads_data)
                    
                    if drift:
                        results['drift_detected'] += 1
                        logger.warning(f"⚠️  Drift detected in: {title}")
                        logger.warning(f"  Fields: {', '.join(drift)}")
                        
                        # Update metadata
                        updated = await self._update_book_metadata(book, goodreads_data)
                        
                        if updated:
                            results['updated'] += 1
                            results['books'].append(title)
                
                results['scanned'] += 1
                
                # Rate limiting (longer for monthly scan)
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error scanning {book.get('title')}: {e}")
                results['errors'] += 1
        
        self.last_monthly_scan = datetime.now()
        
        logger.info("="*70)
        logger.info(f"✅ MONTHLY SCAN COMPLETE")
        logger.info(f"  Scanned: {results['scanned']}")
        logger.info(f"  Drift detected: {results['drift_detected']}")
        logger.info(f"  Updated: {results['updated']}")
        logger.info(f"  Errors: {results['errors']}")
        logger.info("="*70)
        
        return results
    
    def _filter_recent_books(self, library: List[Dict], cutoff_date: datetime) -> List[Dict]:
        """Filter books added after cutoff date."""
        recent = []
        
        for book in library:
            added_at = book.get('addedAt')
            if added_at:
                # Parse timestamp
                try:
                    if isinstance(added_at, str):
                        added_date = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                    else:
                        added_date = datetime.fromtimestamp(added_at)
                    
                    if added_date >= cutoff_date:
                        recent.append(book)
                except Exception as e:
                    logger.debug(f"Could not parse date for {book.get('title')}: {e}")
        
        return recent
    
    def _needs_metadata_update(self, book: Dict) -> bool:
        """
        Check if book needs metadata update.
        
        Criteria:
        - Missing narrator
        - Missing series info
        - Missing description
        - Missing cover
        """
        needs_update = False
        
        if not book.get('narrator'):
            logger.info("  Missing: narrator")
            needs_update = True
        
        if not book.get('series'):
            logger.info("  Missing: series")
            needs_update = True
        
        if not book.get('description'):
            logger.info("  Missing: description")
            needs_update = True
        
        if not book.get('cover'):
            logger.info("  Missing: cover")
            needs_update = True
        
        return needs_update
    
    def _detect_drift(self, current: Dict, canonical: Dict) -> List[str]:
        """
        Detect metadata drift between current and canonical.
        
        Args:
            current: Current metadata from Audiobookshelf
            canonical: Canonical metadata from Goodreads
            
        Returns:
            List of drifted field names
        """
        drifted_fields = []
        
        # Check critical fields
        fields_to_check = ['title', 'author', 'series', 'series_number', 'description']
        
        for field in fields_to_check:
            current_value = current.get(field, '').strip().lower()
            canonical_value = canonical.get(field, '').strip().lower()
            
            if canonical_value and current_value != canonical_value:
                # Allow minor variations
                if not self._is_minor_variation(current_value, canonical_value):
                    drifted_fields.append(field)
        
        return drifted_fields
    
    def _is_minor_variation(self, val1: str, val2: str) -> bool:
        """Check if two values are minor variations."""
        # Remove punctuation and extra spaces
        import re
        val1_clean = re.sub(r'[^\w\s]', '', val1).strip()
        val2_clean = re.sub(r'[^\w\s]', '', val2).strip()
        
        return val1_clean == val2_clean
    
    async def _update_book_metadata(self, 
                                    book: Dict,
                                    goodreads_data: Optional[Dict] = None) -> bool:
        """
        Update book metadata in Audiobookshelf.
        
        Args:
            book: Book to update
            goodreads_data: Optional Goodreads data (will fetch if not provided)
            
        Returns:
            True if update successful
        """
        try:
            abs_item_id = book.get('id')
            if not abs_item_id:
                logger.error("Book missing ID")
                return False
            
            # Get Goodreads data if not provided
            if not goodreads_data:
                title = book.get('title')
                author = book.get('author')
                
                if title and author:
                    goodreads_data = await self.goodreads.search_book(title, author)
            
            if not goodreads_data:
                logger.warning("No Goodreads data available")
                return False
            
            # Build update payload
            update_payload = {
                'metadata': {}
            }
            
            # Update only missing or drifted fields
            if goodreads_data.get('narrator') and not book.get('narrator'):
                update_payload['metadata']['narrator'] = goodreads_data['narrator']
            
            if goodreads_data.get('series') and not book.get('series'):
                update_payload['metadata']['series'] = goodreads_data['series']
                update_payload['metadata']['sequence'] = goodreads_data.get('series_number')
            
            if goodreads_data.get('description') and not book.get('description'):
                update_payload['metadata']['description'] = goodreads_data['description']
            
            if goodreads_data.get('cover_url') and not book.get('cover'):
                update_payload['coverPath'] = goodreads_data['cover_url']
            
            # Update Audiobookshelf
            if update_payload['metadata']:
                success = await self.abs_client.update_library_item(abs_item_id, update_payload)
                
                if success:
                    logger.info(f"  ✓ Updated metadata for: {book.get('title')}")
                    return True
                else:
                    logger.error(f"  ✗ Failed to update: {book.get('title')}")
                    return False
            else:
                logger.info(f"  No updates needed for: {book.get('title')}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update book metadata: {e}")
            return False
    
    async def schedule_maintenance(self):
        """
        Schedule automatic maintenance scans.
        
        - Weekly scan: Every Sunday at 2 AM
        - Monthly scan: First Sunday of month at 3 AM
        """
        logger.info("📅 Scheduling metadata maintenance...")
        
        while True:
            try:
                now = datetime.now()
                
                # Check if it's Sunday
                if now.weekday() == 6:  # Sunday
                    # Check if it's time for weekly scan (2 AM)
                    if now.hour == 2 and (not self.last_weekly_scan or 
                                         (now - self.last_weekly_scan).days >= 7):
                        logger.info("🔔 Triggering weekly scan...")
                        abs_library = await self.abs_client.get_library()
                        await self.weekly_scan(abs_library)
                    
                    # Check if it's first Sunday of month (3 AM)
                    if now.day <= 7 and now.hour == 3 and (not self.last_monthly_scan or 
                                                           (now - self.last_monthly_scan).days >= 28):
                        logger.info("🔔 Triggering monthly scan...")
                        abs_library = await self.abs_client.get_library()
                        await self.monthly_scan(abs_library)
                
                # Sleep for 1 hour
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Maintenance scheduling error: {e}")
                await asyncio.sleep(3600)
