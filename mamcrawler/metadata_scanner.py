"""
Full Metadata Scanner (Section 14).
Combines speech-to-text, torrent metadata, Goodreads, and Audiobookshelf.
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, Optional
from mamcrawler.narrator_detector import NarratorDetector
from mamcrawler.goodreads import GoodreadsMetadata

logger = logging.getLogger(__name__)

class MetadataScanner:
    """
    Performs full metadata scan combining multiple sources.
    """
    
    def __init__(self):
        self.narrator_detector = NarratorDetector()
        self.goodreads = GoodreadsMetadata()
    
    async def scan_audiobook(self, 
                            audiobook_path: str,
                            torrent_metadata: Dict = None,
                            mam_metadata: Dict = None) -> Dict:
        """
        Perform full metadata scan (Section 14).
        
        Args:
            audiobook_path: Path to audiobook files
            torrent_metadata: Metadata from torrent file
            mam_metadata: Metadata from MAM page
            
        Returns:
            Canonical metadata dict
        """
        logger.info(f"📚 Starting full metadata scan: {audiobook_path}")
        
        canonical = {
            'title': None,
            'author': None,
            'series': None,
            'series_number': None,
            'narrator': None,
            'description': None,
            'cover_url': None,
            'isbn': None,
            'publication_date': None,
            'genres': [],
            'rating': None,
            'goodreads_url': None,
            'sources': []
        }
        
        # Step 1: Extract from torrent metadata
        if torrent_metadata:
            canonical.update(self._extract_from_torrent(torrent_metadata))
            canonical['sources'].append('torrent')
        
        # Step 2: Extract from MAM metadata
        if mam_metadata:
            canonical.update(self._extract_from_mam(mam_metadata))
            canonical['sources'].append('mam')
        
        # Step 3: Extract from filenames
        filename_data = self._extract_from_filename(audiobook_path)
        if filename_data:
            canonical.update(filename_data)
            canonical['sources'].append('filename')
        
        # Step 4: Detect narrator from audio (Section 11)
        narrator = await self._detect_narrator(audiobook_path, torrent_metadata, mam_metadata)
        if narrator:
            canonical['narrator'] = narrator
            canonical['sources'].append('audio_detection')
        
        # Step 5: Query Goodreads for canonical data (Section 14)
        if canonical.get('title') and canonical.get('author'):
            goodreads_data = await self.goodreads.search_book(
                canonical['title'],
                canonical['author']
            )
            if goodreads_data:
                canonical.update(self._merge_goodreads(canonical, goodreads_data))
                canonical['sources'].append('goodreads')
        
        # Step 6: Resolve conflicts using priority order (Section 15)
        canonical = self._resolve_conflicts(canonical)
        
        logger.info(f"✓ Metadata scan complete: {canonical.get('title')} by {canonical.get('author')}")
        logger.info(f"  Series: {canonical.get('series')} #{canonical.get('series_number')}")
        logger.info(f"  Narrator: {canonical.get('narrator')}")
        logger.info(f"  Sources: {', '.join(canonical['sources'])}")
        
        return canonical
    
    def _extract_from_torrent(self, torrent_metadata: Dict) -> Dict:
        """Extract metadata from torrent file."""
        return {
            'title': torrent_metadata.get('title'),
            'author': torrent_metadata.get('author'),
            'narrator': torrent_metadata.get('narrator'),
        }
    
    def _extract_from_mam(self, mam_metadata: Dict) -> Dict:
        """Extract metadata from MAM page."""
        return {
            'title': mam_metadata.get('title'),
            'author': mam_metadata.get('author'),
            'narrator': mam_metadata.get('narrator'),
            'series': mam_metadata.get('series'),
            'series_number': mam_metadata.get('series_number'),
        }
    
    def _extract_from_filename(self, audiobook_path: str) -> Dict:
        """
        Extract metadata from filename patterns.
        
        Common patterns:
        - "Title - Author - Narrator"
        - "Author - Title (Series #1)"
        - "Title (Unabridged) by Author"
        """
        import re
        
        path = Path(audiobook_path)
        if path.is_file():
            filename = path.stem
        else:
            # Use directory name
            filename = path.name
        
        metadata = {}
        
        # Pattern: "Title by Author"
        match = re.search(r'(.+?)\s+by\s+(.+?)(?:\s*\(|$)', filename, re.IGNORECASE)
        if match:
            metadata['title'] = match.group(1).strip()
            metadata['author'] = match.group(2).strip()
        
        # Pattern: "Series Name #1 - Title"
        match = re.search(r'(.+?)\s*#(\d+(?:\.\d+)?)\s*[-–]\s*(.+)', filename)
        if match:
            metadata['series'] = match.group(1).strip()
            metadata['series_number'] = match.group(2)
            if not metadata.get('title'):
                metadata['title'] = match.group(3).strip()
        
        return metadata
    
    async def _detect_narrator(self, 
                               audiobook_path: str,
                               torrent_metadata: Dict = None,
                               mam_metadata: Dict = None) -> Optional[str]:
        """
        Detect narrator using multiple methods (Section 11).
        
        Priority:
        1. Metadata (torrent/MAM)
        2. Speech-to-text detection
        """
        # Try metadata first (faster)
        narrator = self.narrator_detector.detect_from_metadata(torrent_metadata, mam_metadata)
        if narrator:
            return narrator
        
        # Fallback to speech-to-text
        path = Path(audiobook_path)
        audio_files = []
        
        if path.is_file():
            audio_files = [path]
        else:
            # Find first audio file
            for ext in ['.mp3', '.m4a', '.m4b', '.ogg', '.flac']:
                audio_files = list(path.rglob(f'*{ext}'))
                if audio_files:
                    break
        
        if audio_files:
            # Use first file for detection
            narrator = self.narrator_detector.detect_from_audio(str(audio_files[0]))
            return narrator
        
        return None
    
    def _merge_goodreads(self, canonical: Dict, goodreads: Dict) -> Dict:
        """
        Merge Goodreads data with canonical metadata.
        
        Goodreads takes priority for:
        - Series name and ordering
        - Description
        - Cover art
        - Publication info
        - Genres
        
        Does NOT overwrite:
        - Title (use speech-to-text if available)
        - Narrator
        """
        merged = canonical.copy()
        
        # Always use Goodreads for these
        merged['series'] = goodreads.get('series') or canonical.get('series')
        merged['series_number'] = goodreads.get('series_number') or canonical.get('series_number')
        merged['description'] = goodreads.get('description') or canonical.get('description')
        merged['cover_url'] = goodreads.get('cover_url') or canonical.get('cover_url')
        merged['isbn'] = goodreads.get('isbn') or goodreads.get('isbn13') or canonical.get('isbn')
        merged['publication_date'] = goodreads.get('publication_date') or canonical.get('publication_date')
        merged['genres'] = goodreads.get('genres') or canonical.get('genres')
        merged['rating'] = goodreads.get('rating') or canonical.get('rating')
        merged['goodreads_url'] = goodreads.get('goodreads_url')
        
        # Use Goodreads title/author if canonical doesn't have them
        if not merged.get('title'):
            merged['title'] = goodreads.get('title')
        if not merged.get('author'):
            merged['author'] = goodreads.get('author')
        
        return merged
    
    def _resolve_conflicts(self, canonical: Dict) -> Dict:
        """
        Resolve metadata conflicts using priority order (Section 15).
        
        Priority:
        1. Speech-to-text (title/series/sequence)
        2. Goodreads (canonical data)
        3. Narrator from torrent/audio
        4. Torrent technical metadata
        5. Audiobookshelf existing
        """
        # Already handled in merge logic
        # This is a placeholder for future conflict resolution
        return canonical
    
    async def update_audiobookshelf(self, 
                                    abs_item_id: str,
                                    metadata: Dict,
                                    abs_client) -> bool:
        """
        Update Audiobookshelf with scanned metadata.
        
        Args:
            abs_item_id: Audiobookshelf library item ID
            metadata: Canonical metadata from scan
            abs_client: Audiobookshelf API client
            
        Returns:
            True if update successful
        """
        try:
            logger.info(f"📝 Updating Audiobookshelf item: {abs_item_id}")
            
            update_payload = {
                'metadata': {
                    'title': metadata.get('title'),
                    'author': metadata.get('author'),
                    'narrator': metadata.get('narrator'),
                    'series': metadata.get('series'),
                    'sequence': metadata.get('series_number'),
                    'description': metadata.get('description'),
                    'isbn': metadata.get('isbn'),
                    'publishedYear': self._extract_year(metadata.get('publication_date')),
                    'genres': metadata.get('genres', []),
                }
            }
            
            # Update cover if available
            if metadata.get('cover_url'):
                update_payload['coverPath'] = metadata['cover_url']
            
            # Call ABS API
            success = await abs_client.update_library_item(abs_item_id, update_payload)
            
            if success:
                logger.info(f"✓ Audiobookshelf updated successfully")
            else:
                logger.error(f"✗ Failed to update Audiobookshelf")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update Audiobookshelf: {e}")
            return False
    
    def _extract_year(self, publication_date: Optional[str]) -> Optional[str]:
        """Extract year from publication date string."""
        if not publication_date:
            return None
        
        import re
        match = re.search(r'\b(19|20)\d{2}\b', publication_date)
        if match:
            return match.group(0)
        
        return None
