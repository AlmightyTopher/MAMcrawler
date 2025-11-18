#!/usr/bin/env python3
"""
Audiobook Audio Verifier

Complete audio-based metadata verification system that:
1. Extracts opening audio segments (30-60 seconds)
2. Transcribes using speech-to-text
3. Parses metadata from transcription
4. Verifies against external sources (Goodreads)
5. Updates Audiobookshelf when confidence >= 95%
"""

import asyncio
import aiohttp
import logging
import os
import re
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Speech recognition
import speech_recognition as sr

# Import our Goodreads client
from goodreads_api_client import GoodreadsClient, BookMetadata

logger = logging.getLogger(__name__)


@dataclass
class AudioExtraction:
    """Result of audio extraction"""
    success: bool
    audio_file: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription"""
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ParsedMetadata:
    """Metadata parsed from audio transcription"""
    title: Optional[str] = None
    author: Optional[str] = None
    series_name: Optional[str] = None
    sequence: Optional[str] = None
    raw_transcript: Optional[str] = None


@dataclass
class VerificationResult:
    """Complete verification result for a book"""
    book_id: str
    current_title: str
    audio_extraction: AudioExtraction
    transcription: TranscriptionResult
    parsed_metadata: ParsedMetadata
    external_verification: Optional[BookMetadata] = None
    final_confidence: float = 0.0
    updated: bool = False
    update_error: Optional[str] = None
    timestamp: str = ""


class AudioExtractor:
    """Extracts audio segments from audiobook files using FFmpeg"""

    @staticmethod
    def extract_opening_segment(audio_file: str, output_file: str, duration: int = 45) -> AudioExtraction:
        """
        Extract the first N seconds of an audio file

        Args:
            audio_file: Path to source audio file
            output_file: Path for extracted segment (WAV format)
            duration: Seconds to extract (default 45)

        Returns:
            AudioExtraction result
        """
        try:
            # FFmpeg command to extract first N seconds as WAV (for speech recognition)
            cmd = [
                'ffmpeg',
                '-i', audio_file,
                '-t', str(duration),  # Duration
                '-ar', '16000',       # Sample rate 16kHz (good for speech)
                '-ac', '1',           # Mono
                '-y',                 # Overwrite output
                output_file
            ]

            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode == 0:
                # Verify file was created
                if Path(output_file).exists():
                    file_size = Path(output_file).stat().st_size
                    logger.info(f"Extracted {duration}s audio segment ({file_size} bytes)")
                    return AudioExtraction(
                        success=True,
                        audio_file=output_file,
                        duration=duration
                    )
                else:
                    return AudioExtraction(
                        success=False,
                        error="Output file not created"
                    )
            else:
                error_msg = result.stderr.decode('utf-8', errors='ignore')
                logger.warning(f"FFmpeg failed: {error_msg[:200]}")
                return AudioExtraction(
                    success=False,
                    error=f"FFmpeg error: {error_msg[:200]}"
                )

        except subprocess.TimeoutExpired:
            return AudioExtraction(success=False, error="FFmpeg timeout")
        except FileNotFoundError:
            return AudioExtraction(success=False, error="FFmpeg not found - install FFmpeg")
        except Exception as e:
            logger.error(f"Audio extraction error: {e}")
            return AudioExtraction(success=False, error=str(e))


class SpeechTranscriber:
    """Transcribes audio using Google Speech Recognition (free tier)"""

    def __init__(self):
        self.recognizer = sr.Recognizer()

    def transcribe_audio_file(self, audio_file: str) -> TranscriptionResult:
        """
        Transcribe audio file to text using Google Speech Recognition

        Args:
            audio_file: Path to WAV file

        Returns:
            TranscriptionResult with text
        """
        try:
            # Load audio file
            with sr.AudioFile(audio_file) as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

                # Record audio
                audio_data = self.recognizer.record(source)

            logger.info("Transcribing audio...")

            # Use Google Speech Recognition (free)
            text = self.recognizer.recognize_google(audio_data)

            logger.info(f"Transcription successful: {len(text)} characters")
            logger.debug(f"Transcript: {text[:200]}...")

            return TranscriptionResult(
                success=True,
                text=text,
                confidence=0.8  # Google doesn't provide confidence scores
            )

        except sr.UnknownValueError:
            logger.warning("Speech not understood")
            return TranscriptionResult(
                success=False,
                error="Speech not understood"
            )
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return TranscriptionResult(
                success=False,
                error=f"Service error: {e}"
            )
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return TranscriptionResult(
                success=False,
                error=str(e)
            )


class MetadataParser:
    """Parses audiobook metadata from transcribed text"""

    # Publishers to strip from beginning of transcript
    PUBLISHERS = [
        r'unabridged recording of\s+',
        r'this is\s+',
        r'presenting\s+',
        r'audible\s+',
        r'podium audio presents\s+',
        r'tantor audio presents\s+',
        r'recorded books presents\s+',
        r'sound booth theater presents\s+',
        r'pandora radio\s+a division of recorded books presents\s+',
        r'brilliance audio presents\s+',
        r'harper audio presents\s+',
        r'macmillan audio presents\s+',
    ]

    PATTERNS = {
        # Common audiobook opening patterns
        # Pattern: "X written by Y and read by Z" -> extract before "written by"
        'title_author_1': re.compile(r'^(.+?)\s+written by\s+(.*?)(?:\s+(?:and read by|narrated by|performed by|featuring)|,|\.|$)', re.IGNORECASE),
        # Pattern: "X by Y narrated by Z"
        'title_author_2': re.compile(r'^(.+?)\s+by\s+(.*?)(?:\s+(?:narrated by|performed by)|,|\.|$)', re.IGNORECASE),
        # Pattern: "X author Y"
        'title_author_3': re.compile(r'^(.+?)\s+author\s+(.*?)(?:\.|,|$)', re.IGNORECASE),

        # Series patterns (applied to title)
        'series_1': re.compile(r'(.+?)\s+(?:book|volume|vol)\s+(\d+)', re.IGNORECASE),
        'series_2': re.compile(r'(.+?)\s+number\s+(\d+)', re.IGNORECASE),
        'series_3': re.compile(r'(.+?)\s+(?:trilogy|series)\s+book\s+(\d+)', re.IGNORECASE),
    }

    def _clean_transcript(self, transcript: str) -> str:
        """Remove publisher names and common prefixes from transcript"""
        clean = transcript.strip()

        # Remove publisher names from beginning
        for publisher_pattern in self.PUBLISHERS:
            clean = re.sub(f'^{publisher_pattern}', '', clean, flags=re.IGNORECASE)

        return clean.strip()

    def parse_transcript(self, transcript: str) -> ParsedMetadata:
        """
        Parse audiobook metadata from transcript

        Looks for patterns like:
        - "This is [Title] by [Author]"
        - "[Title] written by [Author]"
        - "[Series Name] Book [Number]"

        Returns:
            ParsedMetadata with extracted fields
        """
        if not transcript:
            return ParsedMetadata(raw_transcript=transcript)

        # Clean transcript - remove publisher names
        clean_text = self._clean_transcript(transcript)

        # Extract title and author
        title = None
        author = None

        for pattern_name, pattern in self.PATTERNS.items():
            if 'title_author' in pattern_name:
                match = pattern.search(clean_text)
                if match:
                    title = match.group(1).strip()
                    author = match.group(2).strip()
                    logger.info(f"Extracted (pattern {pattern_name}): '{title}' by {author}")
                    break

        if not title or not author:
            return ParsedMetadata(raw_transcript=transcript)

        # Clean up author name - remove narrator info if present
        author = re.sub(r'\s+(?:narrated|performed|featuring|read)\s+by.*$', '', author, flags=re.IGNORECASE).strip()

        # Extract series information from the title
        series_name = None
        sequence = None

        for pattern_name, pattern in self.PATTERNS.items():
            if 'series' in pattern_name:
                match = pattern.search(title)
                if match:
                    series_name = match.group(1).strip()
                    sequence = match.group(2).strip()
                    # Update title to be just the series name (without "Book N")
                    title = series_name
                    logger.info(f"Extracted series from title: {series_name} #{sequence}")
                    break

        return ParsedMetadata(
            title=title,
            author=author,
            series_name=series_name,
            sequence=sequence,
            raw_transcript=transcript
        )


class MetadataUpdater:
    """Updates Audiobookshelf metadata via REST API"""

    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.session = None

    async def __aenter__(self):
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def update_book_metadata(self, book_id: str, metadata: ParsedMetadata,
                                   verified_metadata: Optional[BookMetadata] = None) -> Tuple[bool, Optional[str]]:
        """
        Update book metadata in Audiobookshelf

        Uses verified_metadata if available, otherwise uses parsed metadata

        Returns:
            (success, error_message)
        """
        try:
            # Prefer verified metadata from external source
            if verified_metadata:
                update_data = {
                    "metadata": {
                        "title": verified_metadata.title,
                        "author": verified_metadata.author
                    }
                }

                # Add series if present
                if verified_metadata.series_name:
                    update_data["metadata"]["series"] = [{
                        "name": verified_metadata.series_name,
                        "sequence": verified_metadata.series_position or "1"
                    }]

            else:
                # Fall back to parsed metadata
                update_data = {
                    "metadata": {
                        "title": metadata.title or "Unknown",
                        "author": metadata.author or "Unknown"
                    }
                }

                if metadata.series_name:
                    update_data["metadata"]["series"] = [{
                        "name": metadata.series_name,
                        "sequence": metadata.sequence or "1"
                    }]

            # PATCH request to update metadata
            url = f"{self.api_url}/api/items/{book_id}/media"
            async with self.session.patch(url, json=update_data) as resp:
                if resp.status in (200, 204):
                    logger.info(f"Successfully updated book {book_id}")
                    return True, None
                else:
                    error = await resp.text()
                    logger.error(f"Update failed with status {resp.status}: {error}")
                    return False, f"API error {resp.status}: {error[:100]}"

        except Exception as e:
            logger.error(f"Error updating metadata: {e}")
            return False, str(e)


class VerificationController:
    """Main orchestration class for audio-based verification"""

    def __init__(self, abs_url: str, abs_token: str, temp_dir: Optional[str] = None):
        self.abs_url = abs_url.rstrip('/')
        self.abs_token = abs_token
        self.temp_dir = Path(temp_dir or tempfile.gettempdir()) / "audiobook_verification"
        self.temp_dir.mkdir(exist_ok=True)

        self.audio_extractor = AudioExtractor()
        self.speech_transcriber = SpeechTranscriber()
        self.metadata_parser = MetadataParser()

        self.session = None
        self.goodreads_client = None
        self.metadata_updater = None

    async def __aenter__(self):
        headers = {
            "Authorization": f"Bearer {self.abs_token}",
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(headers=headers)
        self.goodreads_client = await GoodreadsClient().__aenter__()
        self.metadata_updater = await MetadataUpdater(self.abs_url, self.abs_token).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        if self.goodreads_client:
            await self.goodreads_client.__aexit__(exc_type, exc_val, exc_tb)
        if self.metadata_updater:
            await self.metadata_updater.__aexit__(exc_type, exc_val, exc_tb)

    async def get_book_audio_file(self, book_id: str) -> Optional[str]:
        """Get the first audio file path for a book"""
        try:
            url = f"{self.abs_url}/api/items/{book_id}"
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    logger.warning(f"Failed to get book {book_id}: status {resp.status}")
                    return None

                data = await resp.json()

                # Get audio files
                media = data.get('media', {})
                audio_files = media.get('audioFiles', [])

                if not audio_files:
                    logger.warning(f"No audio files found for book {book_id}")
                    return None

                # Return path to first audio file
                first_file = audio_files[0]
                file_path = first_file.get('metadata', {}).get('path')

                if not file_path:
                    logger.warning(f"No file path in audio file metadata")
                    return None

                logger.info(f"Found audio file: {file_path}")
                return file_path

        except Exception as e:
            logger.error(f"Error getting book audio file: {e}")
            return None

    async def verify_book(self, book_id: str, current_title: str) -> VerificationResult:
        """
        Complete verification workflow for a single book

        Steps:
        1. Get audio file from Audiobookshelf
        2. Extract opening segment
        3. Transcribe with speech-to-text
        4. Parse metadata from transcript
        5. Verify with Goodreads
        6. Update if confidence >= 95%

        Returns:
            VerificationResult with all details
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Verifying: {current_title}")
        logger.info(f"Book ID: {book_id}")
        logger.info(f"{'='*80}")

        result = VerificationResult(
            book_id=book_id,
            current_title=current_title,
            audio_extraction=AudioExtraction(success=False),
            transcription=TranscriptionResult(success=False),
            parsed_metadata=ParsedMetadata(),
            timestamp=datetime.now().isoformat()
        )

        # Step 1: Get audio file
        logger.info("Step 1: Getting audio file...")
        audio_file = await self.get_book_audio_file(book_id)
        if not audio_file:
            result.audio_extraction = AudioExtraction(success=False, error="No audio file found")
            return result

        # Step 2: Extract opening segment
        logger.info("Step 2: Extracting opening audio segment...")
        output_wav = str(self.temp_dir / f"{book_id}.wav")

        extraction = self.audio_extractor.extract_opening_segment(audio_file, output_wav, duration=45)
        result.audio_extraction = extraction

        if not extraction.success:
            logger.error(f"Audio extraction failed: {extraction.error}")
            return result

        # Step 3: Transcribe
        logger.info("Step 3: Transcribing audio...")
        transcription = self.speech_transcriber.transcribe_audio_file(extraction.audio_file)
        result.transcription = transcription

        if not transcription.success:
            logger.error(f"Transcription failed: {transcription.error}")
            # Clean up temp file
            try:
                Path(extraction.audio_file).unlink()
            except:
                pass
            return result

        logger.info(f"Transcript: {transcription.text}")

        # Step 4: Parse metadata
        logger.info("Step 4: Parsing metadata from transcript...")
        parsed = self.metadata_parser.parse_transcript(transcription.text)
        result.parsed_metadata = parsed

        if not parsed.title or not parsed.author:
            logger.warning("Could not extract title/author from transcript")
            result.final_confidence = 0.3
            # Clean up
            try:
                Path(extraction.audio_file).unlink()
            except:
                pass
            return result

        # Step 5: Verify with Goodreads
        logger.info("Step 5: Verifying with Goodreads...")
        is_valid, confidence, goodreads_data = await self.goodreads_client.verify_metadata(
            parsed.title,
            parsed.author,
            parsed.series_name,
            parsed.sequence
        )

        result.external_verification = goodreads_data
        result.final_confidence = confidence

        logger.info(f"External verification confidence: {confidence*100:.1f}%")

        # Step 6: Update if confidence >= 95%
        if result.final_confidence >= 0.95:
            logger.info("Step 6: Confidence >= 95%, updating metadata...")
            success, error = await self.metadata_updater.update_book_metadata(
                book_id,
                parsed,
                goodreads_data
            )
            result.updated = success
            result.update_error = error

            if success:
                logger.info("Metadata updated successfully!")
            else:
                logger.error(f"Update failed: {error}")
        else:
            logger.info(f"Step 6: Confidence {confidence*100:.1f}% < 95%, skipping update")
            result.updated = False

        # Clean up temp file
        try:
            Path(extraction.audio_file).unlink()
        except:
            pass

        return result


# Utility function to convert dataclass to JSON-serializable dict
def to_dict(obj):
    """Convert dataclass to dict recursively"""
    if hasattr(obj, '__dict__'):
        return {k: to_dict(v) for k, v in obj.__dict__.items()}
    elif isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [to_dict(item) for item in obj]
    else:
        return obj


if __name__ == "__main__":
    # Test with a single book
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s'
    )

    print("Audio verification system ready")
    print("Use verify_all_uncertain_books.py to process all books")
