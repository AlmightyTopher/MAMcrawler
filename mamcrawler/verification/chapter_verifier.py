"""
Chapter Verification Module
Validates audiobook chapter structure and count.
Minimum viable structure: 3 chapters (unless known single-track)
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ChapterVerifier:
    """Verifies audiobook chapter structure and count"""

    def __init__(self, min_chapters: int = 3):
        """
        Initialize chapter verifier.

        Args:
            min_chapters: Minimum expected chapters (default: 3)
        """
        self.min_chapters = min_chapters

    def extract_chapters(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract chapter metadata from audio file using ffprobe.

        Args:
            file_path: Path to audio file

        Returns:
            list: List of dicts with chapter info, or None if unable to extract
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"Audio file not found: {file_path}")
            return None

        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-print_format', 'json',
                '-show_chapters',
                str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.debug(f"ffprobe failed or no chapters found: {result.stderr}")
                return []

            data = json.loads(result.stdout)
            chapters = data.get('chapters', [])

            if not chapters:
                logger.debug(f"No chapters found in {file_path}")
                return []

            # Extract relevant chapter info
            chapter_list = []
            for ch in chapters:
                chapter_list.append({
                    'index': ch.get('id', len(chapter_list)),
                    'start_time': float(ch.get('start_time', 0)),
                    'end_time': float(ch.get('end_time', 0)),
                    'title': ch.get('tags', {}).get('title', f'Chapter {len(chapter_list) + 1}'),
                })

            logger.info(f"Extracted {len(chapter_list)} chapters from {file_path}")
            return chapter_list

        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timeout for {file_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe output: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting chapters from {file_path}: {e}")
            return None

    def validate_chapter_structure(self, chapters: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Validate chapter structure and timing.

        Args:
            chapters: List of chapter dicts from extract_chapters()

        Returns:
            dict: {
                'valid': bool,
                'count': int,
                'chapters': list,
                'issues': list
            }
        """
        if chapters is None:
            return {
                'valid': False,
                'count': 0,
                'chapters': [],
                'issues': ['Failed to extract chapters']
            }

        if not chapters:
            return {
                'valid': False,
                'count': 0,
                'chapters': [],
                'issues': ['No chapters found']
            }

        issues = []

        # Check for timing issues
        for i, chapter in enumerate(chapters):
            if chapter['end_time'] <= chapter['start_time']:
                issues.append(f"Chapter {i+1}: End time <= start time")

            # Check for gaps between chapters (warn but don't fail)
            if i < len(chapters) - 1:
                next_chapter = chapters[i + 1]
                if next_chapter['start_time'] > chapter['end_time'] + 1:  # Allow 1 sec gap
                    logger.warning(
                        f"Gap between Chapter {i+1} and {i+2}: "
                        f"{chapter['end_time']:.2f}s to {next_chapter['start_time']:.2f}s"
                    )

        is_valid = len(issues) == 0

        return {
            'valid': is_valid,
            'count': len(chapters),
            'chapters': chapters,
            'issues': issues
        }

    def verify_minimum_chapters(self, chapter_count: int, title: str = "", is_single_track: bool = False) -> Dict[str, Any]:
        """
        Verify audiobook meets minimum chapter requirement.

        Args:
            chapter_count: Number of chapters
            title: Audiobook title (for logging)
            is_single_track: True if known single-track (e.g., collection, single short story)

        Returns:
            dict: {
                'valid': bool,
                'count': int,
                'minimum_required': int,
                'details': str
            }
        """
        # Single-track audiobooks don't need minimum chapters
        if is_single_track:
            return {
                'valid': True,
                'count': chapter_count,
                'minimum_required': 1,
                'details': f'{chapter_count} chapter(s) - Single track (no minimum required)'
            }

        # Multi-track must have minimum chapters
        is_valid = chapter_count >= self.min_chapters

        return {
            'valid': is_valid,
            'count': chapter_count,
            'minimum_required': self.min_chapters,
            'details': (
                f'{chapter_count} chapter(s) - '
                f'{"PASS" if is_valid else "FAIL"} (minimum: {self.min_chapters})'
            )
        }

    def verify_audiobook(self, audio_path: str, title: str = "", is_single_track: bool = False) -> Dict[str, Any]:
        """
        Complete chapter verification for audiobook.

        Args:
            audio_path: Path to audio file
            title: Audiobook title (for logging)
            is_single_track: True if known single-track audiobook

        Returns:
            dict: Complete verification result
        """
        chapters = self.extract_chapters(audio_path)

        # Validate structure
        structure_result = self.validate_chapter_structure(chapters)

        if not structure_result['valid']:
            return {
                'passed': False,
                'structure_valid': False,
                'count': structure_result['count'],
                'minimum_met': False,
                'details': f"Invalid structure: {', '.join(structure_result['issues'])}"
            }

        chapter_count = len(chapters) if chapters else 0

        # Check minimum chapters
        minimum_result = self.verify_minimum_chapters(chapter_count, title, is_single_track)

        passed = structure_result['valid'] and minimum_result['valid']

        return {
            'passed': passed,
            'structure_valid': structure_result['valid'],
            'count': chapter_count,
            'minimum_met': minimum_result['valid'],
            'minimum_required': minimum_result['minimum_required'],
            'chapters': chapters or [],
            'details': minimum_result['details']
        }


# Singleton instance
_chapter_verifier = None


def get_chapter_verifier(min_chapters: int = 3) -> ChapterVerifier:
    """Get ChapterVerifier instance"""
    global _chapter_verifier
    if _chapter_verifier is None:
        _chapter_verifier = ChapterVerifier(min_chapters)
    return _chapter_verifier
