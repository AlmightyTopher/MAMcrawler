"""
Quality Filter for MAMcrawler.
Enforces Release Quality Rules (Section 5) and Integrity Checks (Section 13).
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class QualityFilter:
    """
    Enforces strict quality rules for audiobook selection.
    """

    def __init__(self):
        pass

    def _parse_bitrate(self, title: str, description: str = "") -> int:
        """Extract bitrate from title or description."""
        # Look for patterns like "128kbps", "64 kbps", "192k"
        text = (title + " " + description).lower()
        match = re.search(r'(\d+)\s*kbps', text)
        if match:
            return int(match.group(1))
        match = re.search(r'(\d+)\s*k\b', text) # e.g. 128k
        if match:
            return int(match.group(1))
        return 0

    def _is_abridged(self, title: str) -> bool:
        """Check if abridged."""
        return "abridged" in title.lower() and "unabridged" not in title.lower()

    def _is_single_file(self, title: str, description: str = "") -> bool:
        """Check if single file (heuristic)."""
        text = (title + " " + description).lower()
        if "single file" in text or "one file" in text:
            return True
        if "chaptered" in text: # Often implies single file with chapters or m4b
            return True
        return False

    def _score_release(self, torrent: Dict) -> int:
        """
        Score a release based on quality rules.
        Higher score is better.
        """
        score = 0
        title = torrent.get('title', '')
        description = torrent.get('description', '') # Might not be available in list view
        seeders = int(torrent.get('seeders', 0))

        # 1. Unabridged > Abridged (Huge penalty for abridged)
        if self._is_abridged(title):
            score -= 1000
        else:
            score += 100

        # 2. Bitrate
        bitrate = self._parse_bitrate(title, description)
        if bitrate >= 128 and bitrate <= 192:
            score += 50 # Ideal
        elif bitrate >= 96:
            score += 40 # Preferred
        elif bitrate >= 64:
            score += 20 # Acceptable
        elif bitrate > 0:
            score -= 10 # Too low
        
        # 3. Single File vs Split
        if self._is_single_file(title, description):
            score += 10
        
        # 4. Verified Narrator (Heuristic: if narrator field is populated and not "Unknown")
        narrator = torrent.get('narrator', 'Unknown')
        if narrator and narrator != "Unknown":
            score += 5

        # 5. Seeder Count (Tie-breaker, small weight)
        score += min(seeders, 10) * 0.1

        return score

    def select_best_release(self, torrents: List[Dict]) -> Optional[Dict]:
        """
        Select the single best release from a list of candidates.
        Returns None if no release meets minimum standards.
        """
        if not torrents:
            return None

        scored_torrents = []
        for t in torrents:
            score = self._score_release(t)
            scored_torrents.append((score, t))
            logger.debug(f"Scored '{t['title']}': {score}")

        # Sort by score descending
        scored_torrents.sort(key=lambda x: x[0], reverse=True)

        best_score, best_torrent = scored_torrents[0]

        # Minimum acceptable score check?
        # If best is abridged (score < 0), maybe reject?
        if best_score < 0:
            logger.warning(f"Best release '{best_torrent['title']}' has negative score ({best_score}). Rejecting.")
            return None

        logger.info(f"Selected best release: '{best_torrent['title']}' (Score: {best_score})")
        return best_torrent

    def check_integrity(self, torrent_path: str, torrent_info: Dict) -> bool:
        """
        Perform post-download integrity check (Section 13).
        
        Args:
            torrent_path: Path to downloaded torrent directory/file
            torrent_info: Torrent metadata from qBittorrent
            
        Returns:
            True if all checks pass, False otherwise
        """
        import os
        import subprocess
        import json
        from pathlib import Path
        
        logger.info(f"🔍 Starting integrity check for: {torrent_path}")
        
        try:
            path = Path(torrent_path)
            
            # 1. Verify path exists
            if not path.exists():
                logger.error(f"✗ Path does not exist: {torrent_path}")
                return False
            
            # 2. Collect all audio files
            audio_extensions = {'.mp3', '.m4a', '.m4b', '.ogg', '.flac', '.aac', '.opus'}
            audio_files = []
            
            if path.is_file():
                if path.suffix.lower() in audio_extensions:
                    audio_files = [path]
            else:
                for ext in audio_extensions:
                    audio_files.extend(path.rglob(f'*{ext}'))
            
            if not audio_files:
                logger.error(f"✗ No audio files found in: {torrent_path}")
                return False
            
            logger.info(f"Found {len(audio_files)} audio file(s)")
            
            # 3. Verify total size matches torrent (within 1% tolerance)
            expected_size = torrent_info.get('total_size', 0)
            if expected_size > 0:
                actual_size = sum(f.stat().st_size for f in audio_files)
                size_diff_pct = abs(actual_size - expected_size) / expected_size * 100
                
                if size_diff_pct > 1.0:
                    logger.error(f"✗ Size mismatch: Expected {expected_size}, got {actual_size} ({size_diff_pct:.2f}% diff)")
                    return False
                
                logger.info(f"✓ Size check passed ({actual_size} bytes, {size_diff_pct:.2f}% diff)")
            
            # 4. Verify each audio file decodes and check duration
            total_duration = 0
            expected_duration = torrent_info.get('duration', 0)  # If available
            
            for audio_file in audio_files:
                # Use ffprobe to validate audio
                try:
                    result = subprocess.run(
                        [
                            'ffprobe',
                            '-v', 'error',
                            '-show_entries', 'format=duration,size',
                            '-of', 'json',
                            str(audio_file)
                        ],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode != 0:
                        logger.error(f"✗ ffprobe failed for {audio_file.name}: {result.stderr}")
                        return False
                    
                    probe_data = json.loads(result.stdout)
                    file_duration = float(probe_data.get('format', {}).get('duration', 0))
                    total_duration += file_duration
                    
                    logger.debug(f"✓ {audio_file.name}: {file_duration:.2f}s")
                    
                except subprocess.TimeoutExpired:
                    logger.error(f"✗ ffprobe timeout for {audio_file.name}")
                    return False
                except json.JSONDecodeError:
                    logger.error(f"✗ Invalid ffprobe output for {audio_file.name}")
                    return False
                except FileNotFoundError:
                    logger.error("✗ ffprobe not found. Please install ffmpeg.")
                    return False
            
            logger.info(f"✓ All audio files decode successfully")
            logger.info(f"✓ Total duration: {total_duration/3600:.2f} hours")
            
            # 5. Check duration within 1% tolerance (if expected duration available)
            if expected_duration > 0:
                duration_diff_pct = abs(total_duration - expected_duration) / expected_duration * 100
                
                if duration_diff_pct > 1.0:
                    logger.warning(f"⚠ Duration mismatch: Expected {expected_duration}s, got {total_duration}s ({duration_diff_pct:.2f}% diff)")
                    # Don't fail on duration mismatch, just warn
                else:
                    logger.info(f"✓ Duration check passed ({duration_diff_pct:.2f}% diff)")
            
            logger.info(f"✅ Integrity check PASSED for: {torrent_path}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Integrity check failed with exception: {e}")
            return False
