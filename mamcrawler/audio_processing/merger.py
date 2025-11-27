"""
Audio Merging Module
Combines split audio files (part1, part2, etc.) into single audiobook file.

Features:
- Detection of split file patterns
- Multi-file merging with ffmpeg
- Chapter boundary preservation
- Merge integrity validation
"""

import logging
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import os

logger = logging.getLogger(__name__)


class AudioMerger:
    """Handles merging of split audio files into single audiobook"""

    def __init__(self):
        """Initialize audio merger"""
        self.split_patterns = [
            r'part[_\s]?(\d+)',
            r'disc[_\s]?(\d+)',
            r'cd[_\s]?(\d+)',
            r'volume[_\s]?(\d+)',
            r'(\d+)_of_\d+',
        ]

    def detect_split_files(self, directory: str) -> Optional[List[str]]:
        """
        Detect split audio files in directory.

        Args:
            directory: Path to directory containing audio files

        Returns:
            list: Sorted list of split files (e.g., ['part1.m4b', 'part2.m4b'])
            Returns None if fewer than 2 split files detected
        """
        dir_path = Path(directory)

        if not dir_path.is_dir():
            logger.error(f"Directory not found: {directory}")
            return None

        try:
            split_files = {}

            for file_path in dir_path.glob('*'):
                if not file_path.is_file():
                    continue

                # Check against split patterns
                for pattern in self.split_patterns:
                    match = re.search(pattern, file_path.stem, re.IGNORECASE)
                    if match:
                        part_num = int(match.group(1))
                        split_files[part_num] = str(file_path)
                        logger.debug(f"Found split file: {file_path.name} (part {part_num})")
                        break

            if len(split_files) < 2:
                logger.info(f"Only {len(split_files)} split file(s) found in {directory}")
                return None

            # Sort by part number and return file paths
            sorted_files = [split_files[i] for i in sorted(split_files.keys())]

            logger.info(f"Detected {len(sorted_files)} split files for merging")
            return sorted_files

        except Exception as e:
            logger.error(f"Error detecting split files in {directory}: {e}")
            return None

    def merge_files(
        self,
        file_list: List[str],
        output_path: str,
        output_format: str = "m4b"
    ) -> Dict[str, Any]:
        """
        Merge multiple audio files into single file.

        Args:
            file_list: List of audio file paths in order
            output_path: Path to output merged file
            output_format: Output format ('m4b' or 'mp3')

        Returns:
            dict: {
                'success': bool,
                'output_file': str,
                'merged_count': int,
                'total_duration': float (seconds),
                'details': str
            }
        """
        if not file_list or len(file_list) < 2:
            logger.error("At least 2 files required for merging")
            return {
                'success': False,
                'output_file': output_path,
                'merged_count': 0,
                'total_duration': 0,
                'details': 'Insufficient files to merge (need at least 2)'
            }

        # Verify all input files exist
        for file_path in file_list:
            if not Path(file_path).exists():
                logger.error(f"Input file not found: {file_path}")
                return {
                    'success': False,
                    'output_file': output_path,
                    'merged_count': 0,
                    'total_duration': 0,
                    'details': f'Input file not found: {file_path}'
                }

        output_file = Path(output_path)

        try:
            # Create ffmpeg concat demuxer file
            concat_file = output_file.parent / f".{output_file.stem}_concat.txt"

            try:
                with open(concat_file, 'w') as f:
                    for file_path in file_list:
                        # Escape single quotes in path
                        escaped_path = str(file_path).replace("'", "\\'")
                        f.write(f"file '{escaped_path}'\n")

                logger.info(f"Created concat file: {concat_file}")

                # Build ffmpeg command
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_file),
                    '-c', 'copy',
                    '-y',
                    str(output_file)
                ]

                logger.info(f"Merging {len(file_list)} files into {output_file.name}...")

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

                if result.returncode != 0:
                    logger.error(f"ffmpeg merge failed: {result.stderr}")
                    return {
                        'success': False,
                        'output_file': str(output_file),
                        'merged_count': 0,
                        'total_duration': 0,
                        'details': f'ffmpeg error: {result.stderr[:200]}'
                    }

                # Calculate total duration
                total_duration = self._calculate_total_duration(file_list)

                logger.info(f"Successfully merged {len(file_list)} files")

                return {
                    'success': True,
                    'output_file': str(output_file),
                    'merged_count': len(file_list),
                    'total_duration': total_duration,
                    'details': f'Merged {len(file_list)} files, total duration: {total_duration/3600:.1f} hours'
                }

            finally:
                # Clean up concat file
                if concat_file.exists():
                    concat_file.unlink()
                    logger.debug(f"Cleaned up concat file: {concat_file}")

        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg merge timeout for {output_path}")
            return {
                'success': False,
                'output_file': str(output_file),
                'merged_count': 0,
                'total_duration': 0,
                'details': 'Merge process timeout'
            }
        except Exception as e:
            logger.error(f"Error merging files: {e}")
            return {
                'success': False,
                'output_file': str(output_file),
                'merged_count': 0,
                'total_duration': 0,
                'details': f'Exception: {str(e)}'
            }

    def _calculate_total_duration(self, file_list: List[str]) -> float:
        """
        Calculate total duration of all files.

        Args:
            file_list: List of audio file paths

        Returns:
            float: Total duration in seconds
        """
        total_duration = 0

        for file_path in file_list:
            try:
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1:noescapestrings=1',
                    str(file_path)
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                try:
                    duration = float(result.stdout.strip())
                    total_duration += duration
                except ValueError:
                    logger.warning(f"Could not parse duration for {file_path}")

            except Exception as e:
                logger.warning(f"Error getting duration for {file_path}: {e}")

        return total_duration

    def preserve_chapter_boundaries(self, file_list: List[str]) -> Dict[str, Any]:
        """
        Preserve chapter boundaries when merging files.

        Args:
            file_list: List of audio files being merged

        Returns:
            dict: {
                'chapters': list of chapter dicts with timing info,
                'preserved': bool,
                'details': str
            }
        """
        chapters = []
        cumulative_time = 0

        try:
            for file_num, file_path in enumerate(file_list):
                # Get file duration
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1:noescapestrings=1',
                    str(file_path)
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                try:
                    duration = float(result.stdout.strip())

                    # Create chapter marker at file boundary
                    chapters.append({
                        'index': file_num + 1,
                        'title': f'Part {file_num + 1}',
                        'start_time': cumulative_time,
                        'end_time': cumulative_time + duration,
                        'duration': duration
                    })

                    cumulative_time += duration

                except ValueError:
                    logger.warning(f"Could not parse duration for {file_path}")

            logger.info(f"Preserved {len(chapters)} chapter boundaries from split files")

            return {
                'chapters': chapters,
                'preserved': True,
                'details': f'{len(chapters)} chapter markers at split boundaries'
            }

        except Exception as e:
            logger.error(f"Error preserving chapter boundaries: {e}")
            return {
                'chapters': [],
                'preserved': False,
                'details': f'Exception: {str(e)}'
            }

    def validate_merge_integrity(self, input_files: List[str], output_file: str) -> Dict[str, Any]:
        """
        Validate that merge completed without data loss.

        Args:
            input_files: List of input files
            output_file: Path to merged output file

        Returns:
            dict: {
                'valid': bool,
                'input_total_duration': float,
                'output_duration': float,
                'duration_match': bool,
                'file_size': int,
                'details': str
            }
        """
        try:
            # Calculate input total duration
            input_total = sum(self._get_file_duration(f) for f in input_files)

            # Get output duration
            output_duration = self._get_file_duration(output_file)

            # Get output file size
            output_path = Path(output_file)
            file_size = output_path.stat().st_size if output_path.exists() else 0

            # Check if durations match (within 1 second tolerance)
            duration_match = abs(input_total - output_duration) < 1.0

            is_valid = duration_match and file_size > 0

            logger.info(
                f"Merge validation: input={input_total:.1f}s, output={output_duration:.1f}s, "
                f"match={duration_match}, size={file_size} bytes"
            )

            return {
                'valid': is_valid,
                'input_total_duration': input_total,
                'output_duration': output_duration,
                'duration_match': duration_match,
                'file_size': file_size,
                'details': 'Merge integrity verified' if is_valid else 'Duration mismatch detected'
            }

        except Exception as e:
            logger.error(f"Error validating merge integrity: {e}")
            return {
                'valid': False,
                'input_total_duration': 0,
                'output_duration': 0,
                'duration_match': False,
                'file_size': 0,
                'details': f'Exception: {str(e)}'
            }

    def _get_file_duration(self, file_path: str) -> float:
        """Get duration of audio file in seconds"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1:noescapestrings=1',
                str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return float(result.stdout.strip())

        except (ValueError, subprocess.TimeoutExpired):
            return 0.0


# Singleton instance
_audio_merger = None


def get_audio_merger() -> AudioMerger:
    """Get AudioMerger instance"""
    global _audio_merger
    if _audio_merger is None:
        _audio_merger = AudioMerger()
    return _audio_merger
