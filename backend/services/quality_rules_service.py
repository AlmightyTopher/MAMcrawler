"""
ReleaseQualityRulesService - Quality Rules Enforcement
Implements 7-step quality priority rules for release selection
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from backend.models import Book, Download
from backend.database import SessionLocal

logger = logging.getLogger(__name__)


class ReleaseQualityRulesService:
    """
    Service for quality rules enforcement and release selection.

    Quality Priority (7-step hierarchy):
    1. Free leech (zero ratio requirement)
    2. Free (ratio-counted but free to user)
    3. Bonus point eligible (high point value)
    4. Standard paid (normal pricing)
    5. Higher quality paid (higher cost, better quality)
    6. Bestseller pricing (premium titles)
    7. Regional/special editions (last resort)

    Responsibility:
    - Calculate quality scores for releases
    - Enforce free-first rule (always)
    - Prevent inferior edition downloads
    - Trigger replacement when superior found
    - Track quality metrics
    """

    # Quality score weights
    QUALITY_WEIGHTS = {
        'format_quality': 0.25,      # Audio quality (128-320 kbps)
        'narrator_rating': 0.20,     # Narrator popularity/rating
        'edition_type': 0.20,        # First edition vs. special edition
        'source_reliability': 0.20,  # Source reliability (MAM verified)
        'completeness': 0.15         # Complete vs. abridged
    }

    # Release type priorities (higher = better)
    RELEASE_PRIORITIES = {
        'free_leech': 100,           # Zero ratio requirement
        'free': 90,                  # Free to user
        'bonus_eligible': 80,        # Uses bonus points
        'standard_paid': 70,         # Normal price
        'higher_quality_paid': 60,   # Premium quality
        'bestseller_pricing': 50,    # Bestseller premium
        'regional': 40               # Regional/special
    }

    def __init__(self):
        self.quality_cache = {}
        self.downloaded_editions = {}

    def calculate_quality_score(
        self,
        format_quality: int,         # 128-320 kbps
        narrator_rating: float,      # 0-10
        edition_type: str,           # first/anniversary/special
        source_reliability: int,     # 0-100
        completeness: bool           # True if complete
    ) -> float:
        """
        Calculate overall quality score for a release.

        Score range: 0-100

        Args:
            format_quality: Audio bitrate in kbps (128-320)
            narrator_rating: Narrator rating 0-10
            edition_type: Type of edition
            source_reliability: Source reliability 0-100
            completeness: Whether book is complete

        Returns:
            Quality score 0-100
        """
        try:
            # Format quality score (normalize 128-320 to 0-100)
            format_score = min(100, (format_quality / 320) * 100)

            # Narrator rating score
            narrator_score = (narrator_rating / 10) * 100

            # Edition type score
            edition_scores = {
                'first': 100,
                'special_anniversary': 90,
                'remaster': 85,
                'special': 70,
                'abridged': 40
            }
            edition_score = edition_scores.get(edition_type, 50)

            # Source reliability is already 0-100
            reliability_score = source_reliability

            # Completeness score
            completeness_score = 100 if completeness else 60

            # Weighted calculation
            quality_score = (
                format_score * self.QUALITY_WEIGHTS['format_quality'] +
                narrator_score * self.QUALITY_WEIGHTS['narrator_rating'] +
                edition_score * self.QUALITY_WEIGHTS['edition_type'] +
                reliability_score * self.QUALITY_WEIGHTS['source_reliability'] +
                completeness_score * self.QUALITY_WEIGHTS['completeness']
            )

            return round(quality_score, 2)

        except Exception as e:
            logger.error(f"Error calculating quality score: {e}")
            return 50.0  # Default middle score

    def validate_release_selection(
        self,
        book_id: int,
        release_type: str,           # free_leech/free/bonus/paid/etc
        quality_score: float,
        edition_type: str,
        price: int = 0
    ) -> Tuple[bool, str]:
        """
        Validate if a release should be downloaded based on quality rules.

        Rules:
        1. Always prefer free/freeleech
        2. Never download inferior edition if better exists
        3. Trigger replacement if superior edition available
        4. Enforce quality minimums

        Args:
            book_id: Book ID
            release_type: Type of release
            quality_score: Quality score 0-100
            edition_type: Type of edition
            price: Bonus point cost

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        db = SessionLocal()

        try:
            # Check for existing downloads of this book
            existing = db.query(Download).filter(
                Download.book_id == book_id,
                Download.status == 'completed'
            ).first()

            # Rule 1: Always prefer free/freeleech
            if existing and release_type == 'paid':
                if existing.release_edition in ['free_leech', 'free']:
                    return False, "Already have free version"

            # Rule 2: Don't download inferior editions
            if existing:
                existing_quality = existing.quality_score or 50.0

                if quality_score < existing_quality:
                    return False, f"Quality {quality_score} < existing {existing_quality}"

                # Rule 3: Flag for replacement if superior
                if quality_score > existing_quality * 1.1:  # 10% better
                    logger.info(f"Book {book_id}: Superior edition found ({quality_score} > {existing_quality})")
                    # In Phase 3, this would trigger replacement procedure
                    return True, "Superior edition available (will be flagged for replacement)"

            # Rule 4: Enforce quality minimums
            if quality_score < 40:
                return False, f"Quality score {quality_score} below minimum threshold (40)"

            # Default: allow download
            return True, "Release approved"

        except Exception as e:
            logger.error(f"Error validating release: {e}")
            return True, f"Validation error: {str(e)}"

        finally:
            db.close()

    def get_recommended_release(
        self,
        releases: List[Dict]
    ) -> Optional[Dict]:
        """
        Get recommended release from list based on quality rules.

        Selection strategy:
        1. Free leech first
        2. Free second
        3. Highest quality score third
        4. Check against existing editions

        Args:
            releases: List of available releases with quality info

        Returns:
            Recommended release or None
        """
        if not releases:
            return None

        try:
            # Sort by priority
            sorted_releases = sorted(
                releases,
                key=lambda r: (
                    self.RELEASE_PRIORITIES.get(r.get('type', 'standard'), 0),  # Type priority
                    r.get('quality_score', 50),                                   # Quality score
                    r.get('edition_type') == 'first'                              # First edition
                ),
                reverse=True
            )

            recommended = sorted_releases[0]

            logger.info(
                f"Recommended release: {recommended.get('type')} "
                f"(quality: {recommended.get('quality_score')})"
            )

            return recommended

        except Exception as e:
            logger.error(f"Error getting recommended release: {e}")
            return releases[0] if releases else None

    def check_duplicate_prevention(
        self,
        book_id: int,
        narrator: str
    ) -> Tuple[bool, str]:
        """
        Check if download would create a duplicate based on narrator.

        Prevents:
        - Downloading same narrator twice
        - Inferior narrator version

        Args:
            book_id: Book ID
            narrator: Narrator name

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        db = SessionLocal()

        try:
            # Find existing downloads of this book
            existing = db.query(Download).filter(
                Download.book_id == book_id,
                Download.status == 'completed'
            ).all()

            for download in existing:
                # Get narrator from related Book record
                book = db.query(Book).filter(Book.id == book_id).first()

                if book and book.narrator:
                    if book.narrator.lower() == narrator.lower():
                        return False, f"Already have this narrator: {narrator}"

            return True, "No duplicate narrator found"

        except Exception as e:
            logger.error(f"Error checking duplicate prevention: {e}")
            return True, f"Validation error: {str(e)}"

        finally:
            db.close()

    async def trigger_replacement_procedure(
        self,
        book_id: int,
        current_download_id: int,
        superior_release: Dict
    ) -> bool:
        """
        Trigger replacement when superior edition is found.

        Steps:
        1. Mark current download for replacement
        2. Queue superior edition
        3. Schedule deletion after completion

        Args:
            book_id: Book ID
            current_download_id: ID of current download
            superior_release: Superior release info

        Returns:
            True if replacement triggered
        """
        db = SessionLocal()

        try:
            # Mark current as "to_be_replaced"
            current = db.query(Download).filter(
                Download.id == current_download_id
            ).first()

            if current:
                current.status = 'to_be_replaced'
                db.commit()

                logger.info(
                    f"Marked download {current_download_id} for replacement "
                    f"(quality: {superior_release.get('quality_score')})"
                )

                return True

        except Exception as e:
            logger.error(f"Error triggering replacement: {e}")
            db.rollback()

        finally:
            db.close()

        return False

    def get_quality_report(self, book_id: int) -> Dict:
        """Get quality report for a book."""
        db = SessionLocal()

        try:
            book = db.query(Book).filter(Book.id == book_id).first()
            downloads = db.query(Download).filter(
                Download.book_id == book_id
            ).all()

            if not book:
                return {'error': 'Book not found'}

            quality_history = [
                {
                    'source': d.source,
                    'quality_score': d.quality_score,
                    'edition': d.release_edition,
                    'status': d.status,
                    'date_queued': d.date_queued.isoformat() if d.date_queued else None
                }
                for d in downloads
            ]

            return {
                'book_id': book_id,
                'title': book.title,
                'current_quality': book.quality_score,
                'quality_history': quality_history,
                'best_available_quality': max([d.quality_score for d in downloads if d.quality_score], default=None)
            }

        finally:
            db.close()
