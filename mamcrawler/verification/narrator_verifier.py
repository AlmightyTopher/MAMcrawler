"""
Narrator Verification Module
Validates that narrator metadata matches across audio files and metadata sources.
Uses fuzzy matching to handle typos and variations in narrator names.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class NarratorVerifier:
    """Verifies narrator consistency across audio and metadata"""

    def __init__(self, confidence_threshold: float = 0.85):
        """
        Initialize narrator verifier.

        Args:
            confidence_threshold: Minimum fuzzy match score (0.0-1.0)
        """
        self.confidence_threshold = confidence_threshold

    def extract_narrator_from_audio(self, file_path: str) -> Optional[str]:
        """
        Extract narrator from audio file metadata using ffprobe.

        Args:
            file_path: Path to audio file (.m4b, .mp3, .aac)

        Returns:
            str: Narrator name from audio metadata, or None if not found
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"Audio file not found: {file_path}")
            return None

        try:
            # Use ffprobe to extract metadata
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-print_format', 'json',
                '-show_format',
                str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.warning(f"ffprobe failed for {file_path}: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            tags = data.get('format', {}).get('tags', {})

            # Try various possible narrator tag names
            narrator_fields = ['narrator', 'artist', 'album_artist', 'NARRATOR', 'ARTIST']
            for field in narrator_fields:
                if field in tags:
                    narrator = tags[field]
                    if narrator and narrator.strip():
                        logger.info(f"Extracted narrator from audio: {narrator}")
                        return narrator.strip()

            logger.debug(f"No narrator metadata found in audio: {file_path}")
            return None

        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timeout for {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe output for {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting narrator from audio {file_path}: {e}")
            return None

    def extract_narrator_from_metadata(self, metadata: Dict[str, Any]) -> Optional[str]:
        """
        Extract narrator from metadata.json object.

        Args:
            metadata: Dictionary from metadata.json (usually from Audiobookshelf)

        Returns:
            str: Narrator name, or None if not available
        """
        # Check common narrator field names
        narrator_fields = ['narrator', 'narrators', 'Narrator', 'Narrators']

        for field in narrator_fields:
            if field in metadata:
                narrator = metadata[field]
                if isinstance(narrator, str) and narrator.strip():
                    return narrator.strip()
                elif isinstance(narrator, list) and len(narrator) > 0:
                    # Return first narrator if it's a list
                    return str(narrator[0]).strip()

        # Try to extract from description if available
        if 'description' in metadata:
            desc = str(metadata.get('description', '')).lower()
            if 'narrated by' in desc:
                # Simple extraction of text after "narrated by"
                try:
                    idx = desc.find('narrated by') + len('narrated by')
                    narrator_part = desc[idx:].strip()
                    # Get up to first period or comma
                    end_idx = min(
                        len(narrator_part),
                        narrator_part.find('.') if '.' in narrator_part else len(narrator_part),
                        narrator_part.find(',') if ',' in narrator_part else len(narrator_part)
                    )
                    narrator = narrator_part[:end_idx].strip()
                    if narrator and len(narrator) > 2:  # Filter out trivial matches
                        return narrator
                except Exception as e:
                    logger.debug(f"Failed to extract narrator from description: {e}")

        logger.debug("No narrator found in metadata")
        return None

    def fuzzy_match_narrators(self, narrator1: str, narrator2: str) -> float:
        """
        Calculate fuzzy match score between two narrator names.
        Handles typos, spacing, and minor formatting differences.

        Args:
            narrator1: First narrator name
            narrator2: Second narrator name

        Returns:
            float: Match score 0.0-1.0 (1.0 = perfect match)
        """
        # Normalize names
        n1 = str(narrator1).lower().strip()
        n2 = str(narrator2).lower().strip()

        # Direct match
        if n1 == n2:
            return 1.0

        # Remove common variations
        n1_clean = self._clean_narrator_name(n1)
        n2_clean = self._clean_narrator_name(n2)

        if n1_clean == n2_clean:
            return 0.98  # Nearly perfect match after normalization

        # Sequence matcher for fuzzy comparison
        matcher = SequenceMatcher(None, n1_clean, n2_clean)
        return matcher.ratio()

    def _clean_narrator_name(self, name: str) -> str:
        """Normalize narrator name for comparison"""
        # Remove common affixes and normalize spacing
        replacements = {
            'jr.': 'jr',
            'sr.': 'sr',
            '  ': ' ',  # double spaces
            ' the ': ' ',  # remove articles
        }

        cleaned = name
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)

        return cleaned.strip()

    def get_primary_narrator(self, narrators: list) -> Optional[str]:
        """
        Extract primary narrator from list of narrators.
        Assumes first narrator is primary.

        Args:
            narrators: List of narrator names

        Returns:
            str: Primary narrator name
        """
        if not narrators or len(narrators) == 0:
            return None

        primary = str(narrators[0]).strip()
        return primary if primary else None

    def verify_narrator_match(self, audio_narrator: Optional[str], metadata_narrator: Optional[str]) -> Dict[str, Any]:
        """
        Verify narrator matches between audio and metadata sources.

        Args:
            audio_narrator: Narrator from audio file metadata
            metadata_narrator: Narrator from metadata.json

        Returns:
            dict: {
                'match': bool,
                'confidence': 0.0-1.0,
                'narrator_primary': str (the primary narrator),
                'sources': list of sources found,
                'details': str
            }
        """
        # Count available sources
        sources = []
        if audio_narrator:
            sources.append('audio')
        if metadata_narrator:
            sources.append('metadata')

        # If only one source, consider it valid (can't verify match)
        if len(sources) <= 1:
            primary = audio_narrator or metadata_narrator
            return {
                'match': True,  # No conflict with single source
                'confidence': 1.0 if primary else 0.0,
                'narrator_primary': primary,
                'sources': sources,
                'details': f"Single source available: {', '.join(sources)}"
            }

        # Both sources available - compare
        match_score = self.fuzzy_match_narrators(audio_narrator, metadata_narrator)
        is_match = match_score >= self.confidence_threshold

        # Use metadata as primary if available, otherwise audio
        primary = metadata_narrator or audio_narrator

        return {
            'match': is_match,
            'confidence': match_score,
            'narrator_primary': primary,
            'sources': sources,
            'details': (
                f"Match score: {match_score:.2f} "
                f"(threshold: {self.confidence_threshold:.2f}) | "
                f"Audio: {audio_narrator or 'N/A'} | "
                f"Metadata: {metadata_narrator or 'N/A'}"
            )
        }

    def verify_audiobook(self, audio_path: Optional[str], metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Complete narrator verification for audiobook.

        Args:
            audio_path: Path to audio file (or None if not available)
            metadata: metadata.json dict (or None if not available)

        Returns:
            dict: Verification result with match status and details
        """
        audio_narrator = None
        metadata_narrator = None

        if audio_path:
            audio_narrator = self.extract_narrator_from_audio(audio_path)

        if metadata:
            metadata_narrator = self.extract_narrator_from_metadata(metadata)

        return self.verify_narrator_match(audio_narrator, metadata_narrator)


# Singleton instance
_narrator_verifier = None


def get_narrator_verifier(confidence_threshold: float = 0.85) -> NarratorVerifier:
    """Get NarratorVerifier instance (lazy initialization)"""
    global _narrator_verifier
    if _narrator_verifier is None:
        _narrator_verifier = NarratorVerifier(confidence_threshold)
    return _narrator_verifier
