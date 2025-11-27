"""
Audio Processor Orchestrator Module
Coordinates the complete audio processing pipeline with progress tracking and error handling.

Pipeline:
1. Normalize loudness (optional, if already normalized detected)
2. Merge files (if split files detected)
3. Extract and embed chapters
4. Rename file according to standard convention

All steps logged to operation logger with timestamps and status.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

from mamcrawler.audio_processing.normalizer import get_audio_normalizer
from mamcrawler.audio_processing.merger import get_audio_merger
from mamcrawler.audio_processing.chapter_handler import get_chapter_handler
from mamcrawler.audio_processing.file_namer import get_file_namer
from backend.logging.operation_logger import get_operation_logger

logger = logging.getLogger(__name__)


class AudioProcessorOrchestrator:
    """Orchestrates complete audio processing pipeline"""

    def __init__(self, output_format: str = "m4b"):
        """
        Initialize audio processor orchestrator.

        Args:
            output_format: Output format ('m4b' or 'mp3')
        """
        self.output_format = output_format
        self.normalizer = get_audio_normalizer(output_format=output_format)
        self.merger = get_audio_merger()
        self.chapter_handler = get_chapter_handler()
        self.file_namer = get_file_namer()
        self.operation_logger = get_operation_logger()

    def process_audiobook(
        self,
        input_path: str,
        metadata: Dict[str, Any],
        output_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run complete audio processing pipeline for audiobook.

        Args:
            input_path: Path to input audio file or directory with split files
            metadata: Audiobook metadata dict with title, author, narrator, etc.
            output_directory: Directory for processed output (optional)

        Returns:
            dict: {
                'success': bool,
                'output_path': str,
                'steps_completed': list,
                'steps_failed': list,
                'total_duration': float (seconds),
                'timestamp': float,
                'details': str
            }
        """
        start_time = time.time()
        input_file = Path(input_path)
        title = metadata.get('title', 'Unknown')
        author = metadata.get('author', 'Unknown')

        steps_completed = []
        steps_failed = []
        current_file = None

        try:
            # Step 1: Handle multi-file merging
            self._log_step(title, author, "merge", "Starting merge detection...")
            merge_result = self._process_merge(input_path)

            if merge_result['processed']:
                steps_completed.append('merge')
                current_file = merge_result['output_file']
                self._log_step(title, author, "merge", f"Merged {merge_result['merged_count']} files")
            elif merge_result['error']:
                steps_failed.append('merge')
                self._log_step(title, author, "merge", f"Merge failed: {merge_result['error']}", False)
                return self._failed_processing(title, author, "Merge failed", steps_completed, steps_failed)
            else:
                # Single file, no merge needed
                current_file = input_path
                self._log_step(title, author, "merge", "Single file, no merge needed")

            # Step 2: Normalize loudness
            self._log_step(title, author, "normalize", "Starting loudness analysis...")
            norm_output = str(Path(current_file).parent / f".{Path(current_file).stem}_normalized.m4b")

            norm_result = self.normalizer.normalize_to_target(current_file, norm_output)

            if not norm_result['success']:
                steps_failed.append('normalize')
                self._log_step(title, author, "normalize", f"Normalization failed: {norm_result['details']}", False)
                return self._failed_processing(title, author, "Normalization failed", steps_completed, steps_failed)

            steps_completed.append('normalize')
            current_file = norm_output
            self._log_step(title, author, "normalize", f"Normalized to {self.normalizer.target_lufs} LUFS")

            # Step 3: Extract chapters
            self._log_step(title, author, "chapters", "Extracting chapter metadata...")
            chapters = self.chapter_handler.extract_chapters(current_file)

            if chapters is None:
                chapters = []

            if len(chapters) > 0:
                # Create and embed chapters
                chapters_file = str(Path(current_file).parent / f".{Path(current_file).stem}_chapters.txt")
                self.chapter_handler.create_chapters_file(chapters, chapters_file)

                # Embed chapters in output
                chapters_output = str(Path(current_file).parent / f".{Path(current_file).stem}_with_chapters.m4b")
                embed_result = self.chapter_handler.embed_chapters_in_m4b(
                    current_file,
                    chapters_file,
                    chapters_output
                )

                if embed_result['success']:
                    steps_completed.append('chapters')
                    current_file = chapters_output
                    self._log_step(title, author, "chapters", f"Embedded {embed_result['chapters_embedded']} chapters")
                else:
                    # Continue without chapters if embedding fails
                    steps_failed.append('chapters')
                    self._log_step(title, author, "chapters", f"Chapter embedding failed: {embed_result['details']}", False)
            else:
                self._log_step(title, author, "chapters", "No chapters found in source audio")

            # Step 4: Rename and organize file
            self._log_step(title, author, "rename", "Generating standardized filename...")
            naming_result = self.file_namer.generate_filename(
                author=author,
                title=title,
                narrator=metadata.get('narrator'),
                year=metadata.get('releaseYear') or metadata.get('year'),
                series=metadata.get('series') or metadata.get('seriesName'),
                file_extension=self.output_format
            )

            if not naming_result['valid']:
                steps_failed.append('rename')
                self._log_step(title, author, "rename", "Failed to generate valid filename", False)
                return self._failed_processing(title, author, "Filename generation failed", steps_completed, steps_failed)

            # Create directory structure
            dir_result = self.file_namer.create_directory_structure(naming_result['full_path'])

            if not dir_result['success']:
                steps_failed.append('rename')
                self._log_step(title, author, "rename", f"Directory creation failed: {dir_result['details']}", False)
                return self._failed_processing(title, author, "Directory creation failed", steps_completed, steps_failed)

            # Handle duplicates
            dup_result = self.file_namer.handle_duplicates(naming_result['full_path'])
            final_path = dup_result['final_path']

            if not final_path:
                steps_failed.append('rename')
                self._log_step(title, author, "rename", "Could not resolve duplicate filename", False)
                return self._failed_processing(title, author, "Duplicate resolution failed", steps_completed, steps_failed)

            # Move/rename file to final location
            import shutil
            try:
                shutil.move(current_file, final_path)
                steps_completed.append('rename')
                self._log_step(title, author, "rename", f"Renamed to: {Path(final_path).name}")
            except Exception as e:
                steps_failed.append('rename')
                self._log_step(title, author, "rename", f"File move failed: {str(e)}", False)
                return self._failed_processing(title, author, "File move failed", steps_completed, steps_failed)

            # Calculate processing time
            duration = time.time() - start_time

            # Log success
            self.operation_logger.log_processing(
                title=title,
                author=author,
                step="complete",
                completed=True,
                details={
                    'output_file': final_path,
                    'steps': steps_completed,
                    'duration_seconds': duration,
                    'format': self.output_format
                }
            )

            return {
                'success': True,
                'output_path': final_path,
                'steps_completed': steps_completed,
                'steps_failed': [],
                'total_duration': duration,
                'timestamp': time.time(),
                'details': f'Processing complete in {duration:.1f} seconds'
            }

        except Exception as e:
            logger.error(f"Unexpected error during processing: {e}")
            return self._failed_processing(
                title,
                author,
                f"Unexpected error: {str(e)}",
                steps_completed,
                steps_failed
            )

    def _process_merge(self, input_path: str) -> Dict[str, Any]:
        """Check for split files and merge if needed"""
        input_file = Path(input_path)

        # If input is a directory, check for split files
        if input_file.is_dir():
            split_files = self.merger.detect_split_files(str(input_file))

            if split_files and len(split_files) > 1:
                output_path = input_file / "merged.m4b"
                merge_result = self.merger.merge_files(split_files, str(output_path), self.output_format)

                if merge_result['success']:
                    return {
                        'processed': True,
                        'output_file': merge_result['output_file'],
                        'merged_count': merge_result['merged_count'],
                        'error': None
                    }
                else:
                    return {
                        'processed': False,
                        'output_file': None,
                        'merged_count': 0,
                        'error': merge_result['details']
                    }
            else:
                # No split files found, look for single audio file
                audio_files = list(input_file.glob('*.m4b')) + list(input_file.glob('*.mp3'))
                if audio_files:
                    return {
                        'processed': False,
                        'output_file': None,
                        'merged_count': 0,
                        'error': None
                    }
                else:
                    return {
                        'processed': False,
                        'output_file': None,
                        'merged_count': 0,
                        'error': 'No audio files found in directory'
                    }
        else:
            # Single file
            return {
                'processed': False,
                'output_file': None,
                'merged_count': 0,
                'error': None
            }

    def _log_step(
        self,
        title: str,
        author: str,
        step: str,
        message: str,
        success: bool = True
    ) -> None:
        """Log processing step"""
        log_level = logging.INFO if success else logging.WARNING
        logger.log(log_level, f"[{step.upper()}] {message}")

        self.operation_logger.log_processing(
            title=title,
            author=author,
            step=step,
            completed=success,
            details={'message': message}
        )

    def _failed_processing(
        self,
        title: str,
        author: str,
        error: str,
        steps_completed: list,
        steps_failed: list
    ) -> Dict[str, Any]:
        """Create failed processing result"""
        self.operation_logger.log_failure(
            title=title,
            author=author,
            reason=f"Processing failed: {error}",
            retry_count=0,
            details={
                'steps_completed': steps_completed,
                'steps_failed': steps_failed
            }
        )

        return {
            'success': False,
            'output_path': None,
            'steps_completed': steps_completed,
            'steps_failed': steps_failed,
            'total_duration': 0,
            'timestamp': time.time(),
            'details': error
        }


# Singleton instance
_audio_processor_orchestrator = None


def get_audio_processor_orchestrator(output_format: str = "m4b") -> AudioProcessorOrchestrator:
    """Get AudioProcessorOrchestrator instance"""
    global _audio_processor_orchestrator
    if _audio_processor_orchestrator is None:
        _audio_processor_orchestrator = AudioProcessorOrchestrator(output_format)
    return _audio_processor_orchestrator
