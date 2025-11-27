"""
Duration Verification Module
Validates audiobook duration falls within acceptable tolerance of expected duration.
Uses ffprobe to extract actual duration from audio files.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class DurationVerifier:
    """Verifies audiobook duration is within expected tolerance"""

    def __init__(self, tolerance_percent: float = 2.0):
        """
        Initialize duration verifier.

        Args:
            tolerance_percent: Accept durations within ±tolerance_percent of expected
        """
        self.tolerance_percent = tolerance_percent

    def get_actual_duration(self, file_path: str) -> Optional[float]:
        """
        Extract actual duration from audio file using ffprobe.

        Args:
            file_path: Path to audio file

        Returns:
            float: Duration in seconds, or None if unable to determine
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"Audio file not found: {file_path}")
            return None

        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1:nofile=1',
                str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.warning(f"ffprobe failed for {file_path}: {result.stderr}")
                return None

            duration_str = result.stdout.strip()
            if not duration_str:
                logger.warning(f"No duration found in {file_path}")
                return None

            duration = float(duration_str)
            logger.info(f"Extracted duration from audio: {duration:.2f}s ({duration/3600:.2f}h)")
            return duration

        except subprocess.TimeoutExpired:
            logger.error(f"ffprobe timeout for {file_path}")
            return None
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to parse duration from {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error extracting duration from {file_path}: {e}")
            return None

    def get_expected_duration(self, title: str, author: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[float]:
        """
        Get expected duration from metadata or external source.

        Args:
            title: Audiobook title
            author: Author name
            metadata: metadata.json dict with optional duration field

        Returns:
            float: Expected duration in seconds, or None if not available
        """
        # First, check if metadata has duration
        if metadata:
            if 'duration' in metadata:
                try:
                    # Could be seconds or formatted string
                    duration = metadata['duration']
                    if isinstance(duration, (int, float)):
                        return float(duration)
                    elif isinstance(duration, str):
                        # Try to parse common formats
                        try:
                            return float(duration)
                        except ValueError:
                            pass
                except Exception as e:
                    logger.debug(f"Failed to parse duration from metadata: {e}")

            # Check for durationMs (milliseconds)
            if 'durationMs' in metadata:
                try:
                    return float(metadata['durationMs']) / 1000.0
                except Exception as e:
                    logger.debug(f"Failed to parse durationMs: {e}")

        # No expected duration available
        logger.debug(f"No expected duration available for {title}")
        return None

    def calculate_variance_percent(self, actual: float, expected: float) -> float:
        """
        Calculate percentage variance between actual and expected duration.

        Args:
            actual: Actual duration in seconds
            expected: Expected duration in seconds

        Returns:
            float: Variance as percentage (negative = shorter, positive = longer)
        """
        if expected == 0:
            return 0.0

        variance = ((actual - expected) / expected) * 100
        return variance

    def verify_tolerance(self, actual: Optional[float], expected: Optional[float]) -> Dict[str, Any]:
        """
        Verify actual duration is within tolerance of expected.

        Args:
            actual: Actual duration in seconds
            expected: Expected duration in seconds

        Returns:
            dict: {
                'valid': bool,
                'actual_seconds': float,
                'actual_hours': float,
                'expected_seconds': float,
                'expected_hours': float,
                'variance_percent': float,
                'tolerance_percent': float,
                'details': str
            }
        """
        # If no expected duration, can't verify - consider valid
        if expected is None:
            return {
                'valid': True,
                'actual_seconds': actual or 0,
                'actual_hours': (actual or 0) / 3600,
                'expected_seconds': None,
                'expected_hours': None,
                'variance_percent': None,
                'tolerance_percent': self.tolerance_percent,
                'details': 'No expected duration available (cannot verify tolerance)'
            }

        # If no actual duration, verification failed
        if actual is None:
            return {
                'valid': False,
                'actual_seconds': None,
                'actual_hours': None,
                'expected_seconds': expected,
                'expected_hours': expected / 3600,
                'variance_percent': None,
                'tolerance_percent': self.tolerance_percent,
                'details': 'Unable to determine actual duration'
            }

        # Calculate variance
        variance = self.calculate_variance_percent(actual, expected)
        is_valid = abs(variance) <= self.tolerance_percent

        logger.info(
            f"Duration check: Actual={actual/3600:.2f}h, "
            f"Expected={expected/3600:.2f}h, "
            f"Variance={variance:.2f}%"
        )

        return {
            'valid': is_valid,
            'actual_seconds': actual,
            'actual_hours': actual / 3600,
            'expected_seconds': expected,
            'expected_hours': expected / 3600,
            'variance_percent': variance,
            'tolerance_percent': self.tolerance_percent,
            'details': (
                f"Actual: {actual/3600:.2f}h, Expected: {expected/3600:.2f}h, "
                f"Variance: {variance:+.2f}% (tolerance: {self.tolerance_percent}%)"
            )
        }

    def verify_audiobook(self, audio_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Complete duration verification for audiobook.

        Args:
            audio_path: Path to audio file
            metadata: metadata.json dict (optional)

        Returns:
            dict: Verification result with duration details
        """
        actual = self.get_actual_duration(audio_path)

        expected = None
        if metadata:
            title = metadata.get('title', 'Unknown')
            author = metadata.get('author', 'Unknown')
            expected = self.get_expected_duration(title, author, metadata)

        return self.verify_tolerance(actual, expected)


# Singleton instance
_duration_verifier = None


def get_duration_verifier(tolerance_percent: float = 2.0) -> DurationVerifier:
    """Get DurationVerifier instance"""
    global _duration_verifier
    if _duration_verifier is None:
        _duration_verifier = DurationVerifier(tolerance_percent)
    return _duration_verifier
