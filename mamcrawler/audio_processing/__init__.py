"""
Audio Processing Package
Comprehensive audio processing pipeline including normalization, merging, chapter handling, and file naming.

Usage:
    from mamcrawler.audio_processing import get_audio_processor_orchestrator

    orchestrator = get_audio_processor_orchestrator()
    result = orchestrator.process_audiobook(
        input_path="/path/to/audiobook.m4b",
        metadata={"title": "Book Title", "author": "Author Name"}
    )

    if result['success']:
        print(f"Processed: {result['output_path']}")
    else:
        print(f"Failed: {result['error']}")
"""

from mamcrawler.audio_processing.normalizer import AudioNormalizer, get_audio_normalizer
from mamcrawler.audio_processing.merger import AudioMerger, get_audio_merger
from mamcrawler.audio_processing.chapter_handler import ChapterHandler, get_chapter_handler
from mamcrawler.audio_processing.file_namer import FileNamer, get_file_namer
from mamcrawler.audio_processing.processor_orchestrator import AudioProcessorOrchestrator, get_audio_processor_orchestrator

__all__ = [
    'AudioNormalizer',
    'AudioMerger',
    'ChapterHandler',
    'FileNamer',
    'AudioProcessorOrchestrator',
    'get_audio_normalizer',
    'get_audio_merger',
    'get_chapter_handler',
    'get_file_namer',
    'get_audio_processor_orchestrator',
]

__version__ = "1.0.0"
__description__ = "Complete audio processing pipeline for audiobooks"
