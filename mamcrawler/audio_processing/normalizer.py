"""
Audio Normalization Module
Standardizes loudness levels across diverse audio sources using ffmpeg's loudnorm filter.

Features:
- LUFS analysis (Loudness Units relative to Full Scale)
- Loudness normalization to target level (-16 LUFS default for audiobooks)
- Dynamic range preservation
- Support for m4b and mp3 output formats
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class AudioNormalizer:
    """Handles audio loudness normalization with LUFS analysis and adjustment"""

    def __init__(self, target_lufs: float = -16.0, output_format: str = "m4b"):
        """
        Initialize audio normalizer.

        Args:
            target_lufs: Target loudness in LUFS (default: -16 for audiobooks)
            output_format: Output format ('m4b' or 'mp3')
        """
        self.target_lufs = target_lufs
        self.output_format = output_format
        self.supported_formats = ["m4b", "mp3"]

        if output_format not in self.supported_formats:
            raise ValueError(f"Output format must be one of {self.supported_formats}")

    def analyze_loudness(self, audio_file: str) -> Optional[Dict[str, Any]]:
        """
        Analyze loudness of audio file using ffprobe and loudnorm filter.

        Args:
            audio_file: Path to audio file

        Returns:
            dict: {
                'integrated_loudness': float (LUFS),
                'loudness_range': float (LU),
                'true_peak': float (dBFS),
                'duration': float (seconds),
                'valid': bool
            }
            Returns None if analysis fails
        """
        audio_path = Path(audio_file)

        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_file}")
            return None

        try:
            # Use ffmpeg loudnorm filter to analyze loudness
            cmd = [
                'ffmpeg',
                '-i', str(audio_path),
                '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json',
                '-f', 'null',
                '-'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            # Extract loudnorm output from stderr
            output = result.stderr

            # Parse loudnorm JSON output if present
            loudness_stats = {
                'integrated_loudness': None,
                'loudness_range': None,
                'true_peak': None,
                'duration': None,
                'valid': False
            }

            # Extract individual values from loudnorm output
            for line in output.split('\n'):
                if 'Parsed_loudnorm' in line:
                    if 'Integrated loudness' in line:
                        try:
                            parts = line.split(':')
                            if len(parts) > 1:
                                value_str = parts[-1].strip().split()[0]
                                loudness_stats['integrated_loudness'] = float(value_str)
                        except (ValueError, IndexError):
                            pass
                    elif 'Loudness range' in line:
                        try:
                            parts = line.split(':')
                            if len(parts) > 1:
                                value_str = parts[-1].strip().split()[0]
                                loudness_stats['loudness_range'] = float(value_str)
                        except (ValueError, IndexError):
                            pass
                    elif 'True peak' in line:
                        try:
                            parts = line.split(':')
                            if len(parts) > 1:
                                value_str = parts[-1].strip().split()[0]
                                loudness_stats['true_peak'] = float(value_str)
                        except (ValueError, IndexError):
                            pass

            # Also get duration from ffprobe
            duration_cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1:noescapestrings=1',
                str(audio_path)
            ]

            duration_result = subprocess.run(
                duration_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            try:
                loudness_stats['duration'] = float(duration_result.stdout.strip())
            except ValueError:
                loudness_stats['duration'] = None

            # Mark as valid if we got at least integrated loudness
            loudness_stats['valid'] = loudness_stats['integrated_loudness'] is not None

            logger.info(
                f"Loudness analysis for {audio_path.name}: "
                f"{loudness_stats['integrated_loudness']} LUFS"
            )

            return loudness_stats

        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg loudness analysis timeout for {audio_file}")
            return None
        except Exception as e:
            logger.error(f"Error analyzing loudness for {audio_file}: {e}")
            return None

    def normalize_to_target(
        self,
        input_path: str,
        output_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Normalize audio to target loudness level.

        Args:
            input_path: Path to input audio file
            output_path: Path to output audio file

        Returns:
            dict: {
                'success': bool,
                'input_file': str,
                'output_file': str,
                'original_loudness': float (LUFS),
                'target_loudness': float (LUFS),
                'applied': bool,
                'details': str
            }
        """
        input_file = Path(input_path)
        output_file = Path(output_path)

        if not input_file.exists():
            logger.error(f"Input file not found: {input_path}")
            return {
                'success': False,
                'input_file': str(input_path),
                'output_file': str(output_path),
                'original_loudness': None,
                'target_loudness': self.target_lufs,
                'applied': False,
                'details': 'Input file not found'
            }

        try:
            # Analyze original loudness
            analysis = self.analyze_loudness(input_path)

            if not analysis or not analysis['valid']:
                logger.warning(f"Unable to analyze loudness for {input_path}, skipping normalization")
                return {
                    'success': False,
                    'input_file': str(input_path),
                    'output_file': str(output_path),
                    'original_loudness': None,
                    'target_loudness': self.target_lufs,
                    'applied': False,
                    'details': 'Loudness analysis failed'
                }

            original_loudness = analysis['integrated_loudness']

            # If already at target, just copy file
            if abs(original_loudness - self.target_lufs) < 0.5:
                logger.info(
                    f"{input_file.name} already at target loudness "
                    f"({original_loudness} LUFS), skipping normalization"
                )
                return {
                    'success': True,
                    'input_file': str(input_path),
                    'output_file': str(output_path),
                    'original_loudness': original_loudness,
                    'target_loudness': self.target_lufs,
                    'applied': False,
                    'details': 'Already at target loudness, no adjustment needed'
                }

            # Build ffmpeg command with loudnorm filter
            loudnorm_filter = (
                f"loudnorm=I={self.target_lufs}:TP=-1.5:LRA=11:measured_I={original_loudness}:"
                f"measured_LRA={analysis['loudness_range'] or 0}:"
                f"measured_TP={analysis['true_peak'] or 0}"
            )

            cmd = [
                'ffmpeg',
                '-i', str(input_file),
                '-af', loudnorm_filter,
                '-c:a', 'aac' if self.output_format == 'm4b' else 'libmp3lame',
                '-b:a', '128k',
                '-y',
                str(output_file)
            ]

            logger.info(f"Normalizing {input_file.name} to {self.target_lufs} LUFS...")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode != 0:
                logger.error(f"ffmpeg normalization failed: {result.stderr}")
                return {
                    'success': False,
                    'input_file': str(input_path),
                    'output_file': str(output_path),
                    'original_loudness': original_loudness,
                    'target_loudness': self.target_lufs,
                    'applied': False,
                    'details': f'ffmpeg error: {result.stderr[:200]}'
                }

            logger.info(f"Successfully normalized {input_file.name}")

            return {
                'success': True,
                'input_file': str(input_path),
                'output_file': str(output_path),
                'original_loudness': original_loudness,
                'target_loudness': self.target_lufs,
                'applied': True,
                'details': f'Normalized from {original_loudness:.1f} LUFS to {self.target_lufs} LUFS'
            }

        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg normalization timeout for {input_path}")
            return {
                'success': False,
                'input_file': str(input_path),
                'output_file': str(output_path),
                'original_loudness': None,
                'target_loudness': self.target_lufs,
                'applied': False,
                'details': 'Normalization process timeout'
            }
        except Exception as e:
            logger.error(f"Error normalizing {input_path}: {e}")
            return {
                'success': False,
                'input_file': str(input_path),
                'output_file': str(output_path),
                'original_loudness': None,
                'target_loudness': self.target_lufs,
                'applied': False,
                'details': f'Exception: {str(e)}'
            }

    def preserve_dynamic_range(self) -> Dict[str, str]:
        """
        Get ffmpeg filter string for dynamic range preservation.

        Returns:
            dict: Filter configuration for maintaining dynamic range
        """
        return {
            'filter': 'loudnorm=print_format=json',
            'description': 'Preserves dynamic range by using loudnorm with TP (True Peak) limiting',
            'true_peak_limit': '-1.5 dBFS',
            'integrated_loudness_target': f'{self.target_lufs} LUFS'
        }


# Singleton instance
_audio_normalizer = None


def get_audio_normalizer(
    target_lufs: float = -16.0,
    output_format: str = "m4b"
) -> AudioNormalizer:
    """Get AudioNormalizer instance"""
    global _audio_normalizer
    if _audio_normalizer is None:
        _audio_normalizer = AudioNormalizer(target_lufs, output_format)
    return _audio_normalizer
