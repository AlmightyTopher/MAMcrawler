"""
File Namer Module
Applies consistent naming conventions and directory structure to audiobook files.

Naming Convention:
Author/Series (if present)/Title - Narrator (Year).m4b
Example: Brandon Sanderson/Stormlight Archive/The Way of Kings - Michael Kramer (2009).m4b
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FileNamer:
    """Handles standardized naming and organization of audiobook files"""

    def __init__(self, base_directory: Optional[str] = None):
        """
        Initialize file namer.

        Args:
            base_directory: Base directory for organized audiobooks
        """
        self.base_directory = Path(base_directory) if base_directory else Path.home() / "Audiobooks"
        self.invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        self.max_filename_length = 200

    def generate_filename(
        self,
        author: str,
        title: str,
        narrator: Optional[str] = None,
        year: Optional[int] = None,
        series: Optional[str] = None,
        file_extension: str = "m4b"
    ) -> Dict[str, Any]:
        """
        Generate standardized filename and full path.

        Args:
            author: Author name
            title: Book title
            narrator: Narrator name (optional)
            year: Release year (optional)
            series: Series name (optional)
            file_extension: File extension ('m4b' or 'mp3')

        Returns:
            dict: {
                'filename': str (just the filename),
                'directory': str (author/series directory path),
                'full_path': str (complete file path),
                'valid': bool
            }
        """
        # Validate inputs
        if not author or not title:
            logger.error(f"Author and title are required (got: author='{author}', title='{title}')")
            return {
                'filename': None,
                'directory': None,
                'full_path': None,
                'valid': False
            }

        try:
            # Sanitize components
            author_clean = self._sanitize_filename(author)
            title_clean = self._sanitize_filename(title)
            narrator_clean = self._sanitize_filename(narrator) if narrator else None
            series_clean = self._sanitize_filename(series) if series else None

            # Build filename: Title - Narrator (Year).ext
            filename_parts = [title_clean]

            if narrator_clean:
                filename_parts.append(f" - {narrator_clean}")

            if year:
                filename_parts.append(f" ({year})")

            filename = ''.join(filename_parts) + f".{file_extension}"

            # Enforce max filename length
            if len(filename) > self.max_filename_length:
                # Truncate title while keeping narrator and year
                title_max = self.max_filename_length - len(f".{file_extension}") - 50
                title_clean = title_clean[:title_max].rstrip()
                filename_parts = [title_clean]

                if narrator_clean:
                    filename_parts.append(f" - {narrator_clean}")

                if year:
                    filename_parts.append(f" ({year})")

                filename = ''.join(filename_parts) + f".{file_extension}"

            # Build directory structure: Author/Series/
            dir_parts = [author_clean]

            if series_clean:
                dir_parts.append(series_clean)

            directory = self.base_directory / Path(*dir_parts)
            full_path = directory / filename

            return {
                'filename': filename,
                'directory': str(directory),
                'full_path': str(full_path),
                'valid': True
            }

        except Exception as e:
            logger.error(f"Error generating filename: {e}")
            return {
                'filename': None,
                'directory': None,
                'full_path': None,
                'valid': False
            }

    def sanitize_filename(self, name: str) -> str:
        """
        Remove or replace invalid filename characters.

        Args:
            name: Filename to sanitize

        Returns:
            str: Sanitized filename
        """
        if not name:
            return "Unknown"

        return self._sanitize_filename(name)

    def _sanitize_filename(self, name: str) -> str:
        """Internal sanitization method"""
        # Remove invalid characters
        sanitized = re.sub(self.invalid_chars, '', name)

        # Replace multiple spaces with single space
        sanitized = re.sub(r'\s+', ' ', sanitized)

        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip('. ')

        # Replace consecutive dots
        sanitized = re.sub(r'\.+', '.', sanitized)

        # Default to "Unknown" if result is empty
        if not sanitized:
            sanitized = "Unknown"

        return sanitized

    def handle_duplicates(self, target_path: str) -> Dict[str, Any]:
        """
        Handle duplicate filenames by appending counter.

        Args:
            target_path: Proposed file path

        Returns:
            dict: {
                'original_path': str,
                'final_path': str,
                'is_duplicate': bool,
                'counter': int (0 if no duplicate, 1+ if renamed)
            }
        """
        target = Path(target_path)

        if not target.exists():
            return {
                'original_path': str(target),
                'final_path': str(target),
                'is_duplicate': False,
                'counter': 0
            }

        # File exists, need to rename
        logger.warning(f"File already exists: {target_path}")

        stem = target.stem
        suffix = target.suffix
        parent = target.parent

        counter = 1
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name

            if not new_path.exists():
                logger.info(f"Renamed to: {new_path.name}")
                return {
                    'original_path': str(target),
                    'final_path': str(new_path),
                    'is_duplicate': True,
                    'counter': counter
                }

            counter += 1

            # Prevent infinite loop
            if counter > 1000:
                logger.error(f"Could not find available filename after 1000 attempts")
                return {
                    'original_path': str(target),
                    'final_path': None,
                    'is_duplicate': True,
                    'counter': counter
                }

    def validate_path_structure(self, full_path: str) -> Dict[str, Any]:
        """
        Validate that file path follows expected structure.

        Args:
            full_path: Complete file path to validate

        Returns:
            dict: {
                'valid': bool,
                'base_dir_exists': bool,
                'path_components': dict (author, series, filename),
                'issues': list
            }
        """
        try:
            path = Path(full_path)
            issues = []

            # Check if in base directory
            try:
                path.relative_to(self.base_directory)
                base_dir_valid = True
            except ValueError:
                base_dir_valid = False
                issues.append(f"Path not under base directory: {self.base_directory}")

            # Extract components
            relative_path = path.relative_to(self.base_directory)
            parts = relative_path.parts

            components = {
                'author': parts[0] if len(parts) > 0 else None,
                'series': parts[1] if len(parts) > 2 else None,
                'filename': parts[-1] if len(parts) > 0 else None
            }

            # Validate structure
            if len(parts) < 2:
                issues.append("Path must have at least author/filename structure")

            if not path.suffix in ['.m4b', '.mp3']:
                issues.append(f"Invalid file extension: {path.suffix}")

            # Check for invalid characters
            for part in parts:
                if re.search(self.invalid_chars, part):
                    issues.append(f"Invalid characters in path component: {part}")

            is_valid = len(issues) == 0 and base_dir_valid

            return {
                'valid': is_valid,
                'base_dir_exists': self.base_directory.exists(),
                'path_components': components,
                'issues': issues
            }

        except Exception as e:
            logger.error(f"Error validating path structure: {e}")
            return {
                'valid': False,
                'base_dir_exists': False,
                'path_components': {},
                'issues': [f'Exception: {str(e)}']
            }

    def create_directory_structure(self, full_path: str) -> Dict[str, Any]:
        """
        Create directory structure for file if it doesn't exist.

        Args:
            full_path: Complete file path

        Returns:
            dict: {
                'success': bool,
                'directory_created': str,
                'existed': bool,
                'details': str
            }
        """
        try:
            path = Path(full_path)
            directory = path.parent

            if directory.exists():
                return {
                    'success': True,
                    'directory_created': str(directory),
                    'existed': True,
                    'details': f'Directory already exists: {directory}'
                }

            directory.mkdir(parents=True, exist_ok=True)

            logger.info(f"Created directory structure: {directory}")

            return {
                'success': True,
                'directory_created': str(directory),
                'existed': False,
                'details': f'Created directory: {directory}'
            }

        except Exception as e:
            logger.error(f"Error creating directory structure: {e}")
            return {
                'success': False,
                'directory_created': None,
                'existed': False,
                'details': f'Exception: {str(e)}'
            }


# Singleton instance
_file_namer = None


def get_file_namer(base_directory: Optional[str] = None) -> FileNamer:
    """Get FileNamer instance"""
    global _file_namer
    if _file_namer is None:
        _file_namer = FileNamer(base_directory)
    return _file_namer
