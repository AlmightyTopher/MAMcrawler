"""
Chapter Handler Module
Manages chapter metadata extraction and embedding in audiobook files.

Features:
- Chapter extraction from audio files
- Chapter file generation (m4b-tool compatible)
- Chapter embedding in m4b files
- Chapter validation and structure verification
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ChapterHandler:
    """Handles chapter extraction and embedding in audiobook files"""

    def __init__(self):
        """Initialize chapter handler"""
        pass

    def extract_chapters(self, audio_file: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract chapter metadata from audio file.

        Args:
            audio_file: Path to audio file

        Returns:
            list: List of chapter dicts with:
                {
                    'index': int,
                    'title': str,
                    'start_time': float (seconds),
                    'end_time': float (seconds),
                    'duration': float (seconds)
                }
            Returns None if extraction fails
        """
        file_path = Path(audio_file)

        if not file_path.exists():
            logger.error(f"Audio file not found: {audio_file}")
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
                    'title': ch.get('tags', {}).get('title', f'Chapter {len(chapter_list) + 1}'),
                    'start_time': float(ch.get('start_time', 0)),
                    'end_time': float(ch.get('end_time', 0)),
                    'duration': float(ch.get('end_time', 0)) - float(ch.get('start_time', 0))
                })

            logger.info(f"Extracted {len(chapter_list)} chapters from {file_path}")
            return chapter_list

        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timeout for {audio_file}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe output: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting chapters from {audio_file}: {e}")
            return None

    def create_chapters_file(
        self,
        chapters: List[Dict[str, Any]],
        output_path: str
    ) -> Optional[str]:
        """
        Create chapters file in m4b-tool compatible format.

        Args:
            chapters: List of chapter dicts from extract_chapters()
            output_path: Path to save chapters file

        Returns:
            str: Path to created chapters file
            Returns None if creation fails
        """
        if not chapters:
            logger.error("No chapters provided")
            return None

        output_file = Path(output_path)

        try:
            # Create m4b-tool compatible format
            lines = []
            for chapter in chapters:
                # Convert to mm:ss:ms format (milliseconds)
                start_ms = int(chapter['start_time'] * 1000)
                minutes = start_ms // 60000
                seconds = (start_ms % 60000) // 1000
                milliseconds = start_ms % 1000

                title = chapter.get('title', f"Chapter {chapter.get('index', 0)}")

                # m4b-tool format: HH:MM:SS.mmm Title
                time_str = f"{minutes//60:02d}:{minutes%60:02d}:{seconds:02d}.{milliseconds:03d}"
                lines.append(f"{time_str} {title}")

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            logger.info(f"Created chapters file with {len(chapters)} entries: {output_file}")
            return str(output_file)

        except Exception as e:
            logger.error(f"Error creating chapters file: {e}")
            return None

    def embed_chapters_in_m4b(
        self,
        audio_file: str,
        chapters_file: str,
        output_file: str
    ) -> Dict[str, Any]:
        """
        Embed chapters in m4b file using m4b-tool.

        Args:
            audio_file: Path to input audio file
            chapters_file: Path to chapters text file
            output_file: Path to output m4b file with chapters

        Returns:
            dict: {
                'success': bool,
                'output_file': str,
                'chapters_embedded': int,
                'details': str
            }
        """
        audio_path = Path(audio_file)
        chapters_path = Path(chapters_file)
        output_path = Path(output_file)

        # Verify input files exist
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_file}")
            return {
                'success': False,
                'output_file': str(output_path),
                'chapters_embedded': 0,
                'details': 'Audio file not found'
            }

        if not chapters_path.exists():
            logger.error(f"Chapters file not found: {chapters_file}")
            return {
                'success': False,
                'output_file': str(output_path),
                'chapters_embedded': 0,
                'details': 'Chapters file not found'
            }

        try:
            # Check if m4b-tool is available
            result = subprocess.run(
                ['m4b-tool', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning("m4b-tool not available, attempting ffmpeg method")
                return self._embed_chapters_ffmpeg(audio_file, chapters_file, output_file)

            # Use m4b-tool to embed chapters
            cmd = [
                'm4b-tool',
                'merge',
                '--no-conversion',
                '--chapter-pattern', str(chapters_path),
                '-o', str(output_path),
                str(audio_path)
            ]

            logger.info(f"Embedding chapters using m4b-tool...")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.warning(f"m4b-tool embedding failed: {result.stderr}, trying ffmpeg")
                return self._embed_chapters_ffmpeg(audio_file, chapters_file, output_file)

            # Count chapters from file
            with open(chapters_path) as f:
                chapter_count = len([l for l in f if l.strip()])

            logger.info(f"Successfully embedded {chapter_count} chapters")

            return {
                'success': True,
                'output_file': str(output_path),
                'chapters_embedded': chapter_count,
                'details': f'Embedded {chapter_count} chapters using m4b-tool'
            }

        except subprocess.TimeoutExpired:
            logger.error("Chapter embedding timeout")
            return {
                'success': False,
                'output_file': str(output_path),
                'chapters_embedded': 0,
                'details': 'Chapter embedding process timeout'
            }
        except Exception as e:
            logger.error(f"Error embedding chapters: {e}")
            return {
                'success': False,
                'output_file': str(output_path),
                'chapters_embedded': 0,
                'details': f'Exception: {str(e)}'
            }

    def _embed_chapters_ffmpeg(
        self,
        audio_file: str,
        chapters_file: str,
        output_file: str
    ) -> Dict[str, Any]:
        """
        Fallback method to embed chapters using ffmpeg metadata.

        Args:
            audio_file: Path to input audio file
            chapters_file: Path to chapters text file
            output_file: Path to output m4b file with chapters

        Returns:
            dict: Success/failure result
        """
        try:
            # Create FFmpeg metadata format from chapters file
            metadata_path = Path(output_file).parent / f".{Path(output_file).stem}_metadata.txt"

            with open(chapters_file) as f:
                chapter_lines = f.readlines()

            # Create FFmpeg metadata format
            metadata_lines = [';FFMETADATA1']

            for chapter_line in chapter_lines:
                if chapter_line.strip():
                    # Parse time and title
                    parts = chapter_line.strip().split(None, 1)
                    if len(parts) == 2:
                        time_str, title = parts
                        # Convert mm:ss to milliseconds
                        time_parts = time_str.split(':')
                        if len(time_parts) >= 2:
                            minutes = int(time_parts[0])
                            seconds = int(time_parts[1].split('.')[0])
                            ms = int(time_str.split('.')[-1]) if '.' in time_str else 0
                            start_ms = minutes * 60000 + seconds * 1000 + ms

                            metadata_lines.append('\n[CHAPTER]')
                            metadata_lines.append(f'TIMEBASE=1/1000')
                            metadata_lines.append(f'START={start_ms}')
                            metadata_lines.append(f'TITLE={title}')

            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(metadata_lines))

            # Use ffmpeg to embed metadata
            cmd = [
                'ffmpeg',
                '-i', str(audio_file),
                '-i', str(metadata_path),
                '-map_metadata', '1',
                '-c', 'copy',
                '-y',
                str(output_file)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode != 0:
                logger.error(f"ffmpeg chapter embedding failed: {result.stderr}")
                return {
                    'success': False,
                    'output_file': str(output_file),
                    'chapters_embedded': 0,
                    'details': f'ffmpeg error: {result.stderr[:200]}'
                }

            # Count chapters
            chapter_count = len([l for l in chapter_lines if l.strip()])

            logger.info(f"Successfully embedded {chapter_count} chapters using ffmpeg")

            # Clean up metadata file
            if metadata_path.exists():
                metadata_path.unlink()

            return {
                'success': True,
                'output_file': str(output_file),
                'chapters_embedded': chapter_count,
                'details': f'Embedded {chapter_count} chapters using ffmpeg metadata'
            }

        except Exception as e:
            logger.error(f"Error in ffmpeg chapter embedding: {e}")
            return {
                'success': False,
                'output_file': str(output_file),
                'chapters_embedded': 0,
                'details': f'Exception: {str(e)}'
            }

    def validate_chapters_embedded(self, audio_file: str) -> Dict[str, Any]:
        """
        Validate that chapters are readable in audio file.

        Args:
            audio_file: Path to audio file to validate

        Returns:
            dict: {
                'valid': bool,
                'chapter_count': int,
                'readable': bool,
                'details': str
            }
        """
        try:
            chapters = self.extract_chapters(audio_file)

            if chapters is None:
                return {
                    'valid': False,
                    'chapter_count': 0,
                    'readable': False,
                    'details': 'Failed to read chapters from file'
                }

            chapter_count = len(chapters)
            is_valid = chapter_count > 0

            return {
                'valid': is_valid,
                'chapter_count': chapter_count,
                'readable': True,
                'details': f'{chapter_count} chapters readable' if is_valid else 'No chapters found'
            }

        except Exception as e:
            logger.error(f"Error validating chapters: {e}")
            return {
                'valid': False,
                'chapter_count': 0,
                'readable': False,
                'details': f'Exception: {str(e)}'
            }


# Singleton instance
_chapter_handler = None


def get_chapter_handler() -> ChapterHandler:
    """Get ChapterHandler instance"""
    global _chapter_handler
    if _chapter_handler is None:
        _chapter_handler = ChapterHandler()
    return _chapter_handler
