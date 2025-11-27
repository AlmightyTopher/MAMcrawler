"""
Narrator Detection using Speech-to-Text (Section 11).
Detects narrator from audiobook files using Whisper or similar.
"""

import logging
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict
import re

logger = logging.getLogger(__name__)

class NarratorDetector:
    """
    Detects narrator from audiobook files using speech-to-text.
    """
    
    def __init__(self):
        self.cache = {}  # Cache results to avoid re-processing
    
    def detect_from_audio(self, audio_path: str, duration_limit: int = 60) -> Optional[str]:
        """
        Detect narrator from audio file using speech-to-text on the first minute.
        
        Args:
            audio_path: Path to audio file
            duration_limit: Seconds of audio to analyze (default 60)
            
        Returns:
            Detected narrator name or None
        """
        try:
            path = Path(audio_path)
            
            if not path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            # Check cache
            cache_key = str(path)
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            logger.info(f"🎤 Detecting narrator from: {path.name}")
            
            # Extract first minute of audio for analysis
            temp_audio = path.parent / f"temp_narrator_sample_{path.stem}.wav"
            
            try:
                # Use ffmpeg to extract first minute as WAV
                subprocess.run(
                    [
                        'ffmpeg',
                        '-i', str(path),
                        '-t', str(duration_limit),
                        '-vn',  # No video
                        '-acodec', 'pcm_s16le',
                        '-ar', '16000',  # 16kHz sample rate (good for speech)
                        '-ac', '1',  # Mono
                        '-y',  # Overwrite
                        str(temp_audio)
                    ],
                    capture_output=True,
                    check=True,
                    timeout=120
                )
                
                # Use Whisper for speech-to-text
                # Note: Requires whisper to be installed: pip install openai-whisper
                narrator = self._transcribe_and_extract_narrator(temp_audio)
                
                # Cache result
                self.cache[cache_key] = narrator
                
                return narrator
                
            finally:
                # Clean up temp file
                if temp_audio.exists():
                    temp_audio.unlink()
                    
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e.stderr}")
            return None
        except FileNotFoundError:
            logger.error("ffmpeg not found. Please install ffmpeg.")
            return None
        except Exception as e:
            logger.error(f"Narrator detection failed: {e}")
            return None
    
    def _transcribe_and_extract_narrator(self, audio_file: Path) -> Optional[str]:
        """
        Transcribe audio and extract narrator name from introduction.
        
        Common patterns:
        - "Narrated by [Name]"
        - "Read by [Name]"
        - "[Book Title] by [Author], narrated by [Name]"
        """
        try:
            import whisper
            
            # Load smallest model for speed (base or tiny)
            model = whisper.load_model("tiny")
            
            # Transcribe
            result = model.transcribe(str(audio_file), language="en")
            text = result["text"].strip()
            
            logger.debug(f"Transcription: {text[:200]}...")
            
            # Extract narrator using patterns
            narrator = self._extract_narrator_from_text(text)
            
            if narrator:
                logger.info(f"✓ Detected narrator: {narrator}")
            else:
                logger.warning("✗ Could not detect narrator from audio")
            
            return narrator
            
        except ImportError:
            logger.error("Whisper not installed. Install with: pip install openai-whisper")
            return None
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    def _extract_narrator_from_text(self, text: str) -> Optional[str]:
        """
        Extract narrator name from transcribed text using patterns.
        """
        # Common patterns
        patterns = [
            r'narrated by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'read by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'performed by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'narrator[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                narrator = match.group(1).strip()
                # Validate it looks like a name (2-4 words, capitalized)
                words = narrator.split()
                if 1 <= len(words) <= 4 and all(w[0].isupper() for w in words):
                    return narrator
        
        return None
    
    def detect_from_metadata(self, torrent_metadata: Dict, mam_metadata: Dict = None) -> Optional[str]:
        """
        Extract narrator from torrent or MAM metadata.
        
        Args:
            torrent_metadata: Torrent file metadata
            mam_metadata: MAM page metadata (if available)
            
        Returns:
            Narrator name or None
        """
        # Check torrent metadata
        if torrent_metadata:
            narrator = torrent_metadata.get('narrator')
            if narrator and narrator != "Unknown":
                logger.info(f"✓ Narrator from torrent metadata: {narrator}")
                return narrator
        
        # Check MAM metadata
        if mam_metadata:
            narrator = mam_metadata.get('narrator')
            if narrator and narrator != "Unknown":
                logger.info(f"✓ Narrator from MAM metadata: {narrator}")
                return narrator
        
        return None
    
    def fuzzy_match_narrator(self, detected: str, known_narrators: list) -> Optional[str]:
        """
        Fuzzy match detected narrator against known narrators.
        
        Args:
            detected: Detected narrator name
            known_narrators: List of known narrator names
            
        Returns:
            Best match or original if no good match
        """
        if not detected or not known_narrators:
            return detected
        
        try:
            from fuzzywuzzy import fuzz
            
            best_match = None
            best_score = 0
            
            for known in known_narrators:
                score = fuzz.ratio(detected.lower(), known.lower())
                if score > best_score:
                    best_score = score
                    best_match = known
            
            # Use match if score > 80
            if best_score > 80:
                logger.info(f"✓ Fuzzy matched '{detected}' -> '{best_match}' (score: {best_score})")
                return best_match
            
            return detected
            
        except ImportError:
            logger.warning("fuzzywuzzy not installed. Install with: pip install fuzzywuzzy python-Levenshtein")
            return detected
