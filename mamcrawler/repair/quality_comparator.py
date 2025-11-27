"""
Quality Comparator Module
Compares audio quality metrics between original and replacement audiobooks.

Metrics:
- Audio codec (AAC, MP3, etc.)
- Bitrate (kbps)
- Sample rate (Hz)
- Duration (seconds)
- File size (bytes)
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class QualityComparator:
    """Compares quality metrics between audio files"""

    def __init__(self):
        """Initialize quality comparator"""
        self.bitrate_threshold = 0.9  # 10% variance allowed
        self.duration_threshold = 0.02  # 2% variance allowed

    def get_audio_properties(self, audio_file: str) -> Optional[Dict[str, Any]]:
        """
        Extract audio properties using ffprobe.

        Args:
            audio_file: Path to audio file

        Returns:
            dict: {
                'codec': str,
                'bitrate_kbps': int,
                'sample_rate': int,
                'channels': int,
                'duration_seconds': float,
                'file_size_bytes': int
            }
            Returns None if extraction fails
        """
        file_path = Path(audio_file)

        if not file_path.exists():
            logger.error(f"Audio file not found: {audio_file}")
            return None

        try:
            # Get file size
            file_size = file_path.stat().st_size

            # Use ffprobe to get audio properties
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-print_format', 'json',
                '-show_streams',
                str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"ffprobe failed: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            streams = data.get('streams', [])

            # Find audio stream
            audio_stream = None
            for stream in streams:
                if stream.get('codec_type') == 'audio':
                    audio_stream = stream
                    break

            if not audio_stream:
                logger.error(f"No audio stream found in {audio_file}")
                return None

            # Extract properties
            codec = audio_stream.get('codec_name', 'unknown')
            bitrate = audio_stream.get('bit_rate')
            if bitrate:
                bitrate_kbps = int(bitrate) // 1000
            else:
                bitrate_kbps = None

            sample_rate = audio_stream.get('sample_rate')
            if sample_rate:
                sample_rate = int(sample_rate)

            channels = audio_stream.get('channels', 2)
            duration = float(audio_stream.get('duration', 0))

            return {
                'codec': codec,
                'bitrate_kbps': bitrate_kbps,
                'sample_rate': sample_rate,
                'channels': channels,
                'duration_seconds': duration,
                'file_size_bytes': file_size
            }

        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timeout for {audio_file}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ffprobe output: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting audio properties: {e}")
            return None

    def compare_quality(
        self,
        original_file: str,
        replacement_file: str
    ) -> Dict[str, Any]:
        """
        Compare quality metrics between original and replacement.

        Args:
            original_file: Path to original audio file
            replacement_file: Path to replacement audio file

        Returns:
            dict: {
                'original': audio properties,
                'replacement': audio properties,
                'is_better_or_equal': bool,
                'comparison': {
                    'codec_match': bool,
                    'bitrate_acceptable': bool,
                    'duration_match': bool,
                    'issues': list
                },
                'details': str
            }
        """
        original_props = self.get_audio_properties(original_file)
        replacement_props = self.get_audio_properties(replacement_file)

        if not original_props or not replacement_props:
            return {
                'original': original_props,
                'replacement': replacement_props,
                'is_better_or_equal': False,
                'comparison': {
                    'codec_match': False,
                    'bitrate_acceptable': False,
                    'duration_match': False,
                    'issues': ['Unable to extract properties from one or both files']
                },
                'details': 'Property extraction failed'
            }

        issues = []
        codec_match = original_props['codec'] == replacement_props['codec']
        duration_match = self._check_duration_match(
            original_props['duration_seconds'],
            replacement_props['duration_seconds']
        )
        bitrate_acceptable = self._check_bitrate_acceptable(
            original_props['bitrate_kbps'],
            replacement_props['bitrate_kbps']
        )

        if not codec_match:
            issues.append(f"Codec mismatch: {original_props['codec']} vs {replacement_props['codec']}")

        if not bitrate_acceptable:
            issues.append(
                f"Bitrate difference too large: "
                f"{original_props['bitrate_kbps']} kbps vs {replacement_props['bitrate_kbps']} kbps"
            )

        if not duration_match:
            duration_diff_pct = abs(
                (replacement_props['duration_seconds'] - original_props['duration_seconds']) /
                original_props['duration_seconds'] * 100
            ) if original_props['duration_seconds'] > 0 else 0
            issues.append(
                f"Duration mismatch: "
                f"{original_props['duration_seconds']:.0f}s vs {replacement_props['duration_seconds']:.0f}s "
                f"({duration_diff_pct:.1f}% difference)"
            )

        # Quality is acceptable if codec matches and bitrate/duration are acceptable
        is_better_or_equal = codec_match and bitrate_acceptable and duration_match

        return {
            'original': original_props,
            'replacement': replacement_props,
            'is_better_or_equal': is_better_or_equal,
            'comparison': {
                'codec_match': codec_match,
                'bitrate_acceptable': bitrate_acceptable,
                'duration_match': duration_match,
                'issues': issues
            },
            'details': 'Quality acceptable for replacement' if is_better_or_equal else f"Quality issues: {'; '.join(issues)}"
        }

    def _check_duration_match(self, duration1: float, duration2: float) -> bool:
        """Check if durations match within threshold"""
        if duration1 == 0:
            return False

        diff_pct = abs(duration2 - duration1) / duration1
        return diff_pct <= self.duration_threshold

    def _check_bitrate_acceptable(
        self,
        original_bitrate: Optional[int],
        replacement_bitrate: Optional[int]
    ) -> bool:
        """Check if replacement bitrate is acceptable"""
        if original_bitrate is None or replacement_bitrate is None:
            return True  # Can't compare, allow it

        # Replacement bitrate should be at least 90% of original
        return replacement_bitrate >= (original_bitrate * self.bitrate_threshold)


# Singleton instance
_quality_comparator = None


def get_quality_comparator() -> QualityComparator:
    """Get QualityComparator instance"""
    global _quality_comparator
    if _quality_comparator is None:
        _quality_comparator = QualityComparator()
    return _quality_comparator
