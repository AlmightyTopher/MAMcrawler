"""
Audio File Validator
Validates audiobook metadata by checking file properties, ID3 tags, and audio analysis

Features:
- Extract ID3 metadata from M4B, MP3, FLAC files
- Analyze audio file properties (duration, bitrate, codec)
- Compare file metadata with Hardcover resolution
- Generate confidence score based on metadata agreement
- Support for opening in player for manual verification
"""

import os
from pathlib import Path
from typing import Optional, Dict, Tuple, List
import logging
import subprocess
import json

logger = logging.getLogger(__name__)


class AudioValidator:
    """Validates audiobook files and metadata"""

    # Audio file extensions we support
    AUDIO_EXTENSIONS = {'.m4b', '.mp3', '.flac', '.ogg', '.wma', '.aac'}

    def __init__(self):
        self.has_mutagen = self._check_mutagen()
        self.has_ffprobe = self._check_ffprobe()

    def _check_mutagen(self) -> bool:
        """Check if mutagen is available for ID3 tag reading"""
        try:
            import mutagen
            return True
        except ImportError:
            logger.warning("mutagen not available - ID3 tag reading disabled")
            return False

    def _check_ffprobe(self) -> bool:
        """Check if ffprobe is available for audio analysis"""
        try:
            result = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("ffprobe not available - audio analysis disabled")
            return False

    def validate_file(self, file_path: str) -> Dict:
        """
        Validate an audio file

        Returns:
            {
                'valid': bool,
                'file': str,
                'duration': int (seconds),
                'codec': str,
                'bitrate': str,
                'metadata': {
                    'title': str,
                    'artist': str,
                    'album': str,
                    'date': str,
                    'genre': str
                }
            }
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {'valid': False, 'error': f'File not found: {file_path}'}

        if file_path.suffix.lower() not in self.AUDIO_EXTENSIONS:
            return {'valid': False, 'error': f'Unsupported file type: {file_path.suffix}'}

        result = {
            'valid': True,
            'file': str(file_path),
            'duration': None,
            'codec': None,
            'bitrate': None,
            'metadata': {}
        }

        # Get audio properties
        if self.has_ffprobe:
            audio_info = self._get_audio_properties(file_path)
            result.update(audio_info)

        # Get ID3 tags
        if self.has_mutagen:
            metadata = self._extract_metadata(file_path)
            result['metadata'] = metadata

        return result

    def _get_audio_properties(self, file_path: Path) -> Dict:
        """Extract audio properties using ffprobe"""
        try:
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_format',
                    '-show_streams',
                    '-of', 'json',
                    str(file_path)
                ],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return {}

            data = json.loads(result.stdout)

            # Extract duration
            duration = None
            if 'format' in data and 'duration' in data['format']:
                duration = int(float(data['format']['duration']))

            # Extract codec and bitrate
            codec = None
            bitrate = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'audio':
                    codec = stream.get('codec_name', '').upper()
                    if 'bit_rate' in stream:
                        br = int(stream['bit_rate'])
                        bitrate = f"{br // 1000}k"
                    break

            return {
                'duration': duration,
                'codec': codec,
                'bitrate': bitrate
            }

        except Exception as e:
            logger.warning(f"Failed to get audio properties: {e}")
            return {}

    def _extract_metadata(self, file_path: Path) -> Dict:
        """Extract ID3 tags using mutagen"""
        try:
            from mutagen import File

            audio = File(str(file_path))
            if not audio:
                return {}

            metadata = {}

            # Map common tags to standardized keys
            tag_map = {
                'title': ['TIT2', '\xa9nam', 'TITLE', 'Title'],
                'artist': ['TPE1', '\xa9ART', 'ARTIST', 'Artist', 'AUTHOR'],
                'album': ['TALB', '\xa9alb', 'ALBUM', 'Album', 'SERIES'],
                'date': ['TDRC', '\xa9day', 'DATE', 'Date', 'YEAR'],
                'genre': ['TCON', '\xa9gen', 'GENRE', 'Genre'],
                'narrator': ['TPE3', 'NARRATOR', 'Narrator'],
            }

            for standard_key, possible_tags in tag_map.items():
                for tag in possible_tags:
                    if tag in audio:
                        value = audio[tag]
                        if isinstance(value, list) and value:
                            metadata[standard_key] = str(value[0])
                        else:
                            metadata[standard_key] = str(value)
                        break

            return metadata

        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
            return {}

    def compare_with_hardcover(
        self,
        file_info: Dict,
        hardcover_title: str,
        hardcover_author: str,
        hardcover_series: Optional[Tuple[str, float]] = None
    ) -> Tuple[float, List[str]]:
        """
        Compare file metadata with Hardcover data

        Returns:
            (confidence_score: 0.0-1.0, differences: list of discrepancies)
        """
        metadata = file_info.get('metadata', {})
        differences = []
        score_parts = []

        # Title comparison
        file_title = metadata.get('title', '').lower()
        hc_title = hardcover_title.lower()

        if file_title and file_title == hc_title:
            score_parts.append(1.0)  # Perfect match
        elif file_title and hc_title in file_title:
            score_parts.append(0.95)  # Contains match
            differences.append(f"Title partial match: '{metadata.get('title')}' vs '{hardcover_title}'")
        elif file_title:
            score_parts.append(0.5)  # Present but doesn't match
            differences.append(f"Title mismatch: '{metadata.get('title')}' vs '{hardcover_title}'")
        else:
            score_parts.append(0.7)  # Missing title tag

        # Artist/Author comparison
        file_artist = metadata.get('artist', '').lower()
        hc_author = hardcover_author.lower()

        if file_artist and file_artist == hc_author:
            score_parts.append(1.0)
        elif file_artist and hc_author in file_artist:
            score_parts.append(0.95)
            differences.append(f"Artist partial match: '{metadata.get('artist')}' vs '{hardcover_author}'")
        elif file_artist:
            score_parts.append(0.5)
            differences.append(f"Artist mismatch: '{metadata.get('artist')}' vs '{hardcover_author}'")
        else:
            score_parts.append(0.7)

        # Narrator presence (bonus if present)
        if metadata.get('narrator'):
            score_parts.append(0.9)  # Narrator information present

        # Calculate average confidence
        confidence = sum(score_parts) / len(score_parts) if score_parts else 0.5

        return confidence, differences

    @staticmethod
    def open_in_player(file_path: str) -> bool:
        """
        Open audio file in system default player

        Returns:
            True if successfully opened
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False

        try:
            if os.name == 'nt':  # Windows
                os.startfile(str(file_path))
                return True
            elif os.name == 'posix':  # macOS/Linux
                subprocess.Popen(['open', str(file_path)])
                return True
        except Exception as e:
            logger.error(f"Failed to open file: {e}")
            return False

        return False


# ============================================================================
# Usage Functions
# ============================================================================

async def validate_and_compare(
    file_path: str,
    hardcover_title: str,
    hardcover_author: str,
    hardcover_series: Optional[Tuple[str, float]] = None,
    auto_open: bool = False
) -> Dict:
    """
    Validate a file and compare with Hardcover data

    Args:
        file_path: Path to audio file
        hardcover_title: Title from Hardcover
        hardcover_author: Author from Hardcover
        hardcover_series: Series info from Hardcover
        auto_open: Open in player automatically

    Returns:
        Validation result with confidence and differences
    """
    validator = AudioValidator()

    # Validate file
    file_info = validator.validate_file(file_path)

    if not file_info.get('valid'):
        return {
            'valid': False,
            'error': file_info.get('error')
        }

    # Compare with Hardcover
    confidence, differences = validator.compare_with_hardcover(
        file_info,
        hardcover_title,
        hardcover_author,
        hardcover_series
    )

    result = {
        'valid': True,
        'file': file_path,
        'file_info': file_info,
        'hardcover_match': {
            'title': hardcover_title,
            'author': hardcover_author,
            'series': hardcover_series
        },
        'confidence': confidence,
        'differences': differences,
        'requires_verification': confidence < 0.95
    }

    # Optionally open in player
    if auto_open and confidence < 0.95:
        print(f"\nOpening file for manual verification: {file_path}")
        print(f"Confidence: {confidence:.0%}")
        if differences:
            print("Differences found:")
            for diff in differences:
                print(f"  - {diff}")
        print("\nPress Enter after confirming the audiobook title, author, and series...")

        validator.open_in_player(file_path)
        input()  # Wait for user

        result['manual_verification_complete'] = True

    return result


# ============================================================================
# Demo
# ============================================================================

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def demo():
        # Example usage
        file_path = "path/to/audiobook.m4b"

        result = await validate_and_compare(
            file_path,
            hardcover_title="The Way of Kings",
            hardcover_author="Brandon Sanderson",
            auto_open=False
        )

        print(json.dumps(result, indent=2, default=str))

    asyncio.run(demo())
