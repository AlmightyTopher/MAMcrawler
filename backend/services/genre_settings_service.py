"""
Genre Settings Service - Business logic for genre preference operations
Handles genre enable/disable for Top-10 discovery feature
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from backend.models.genre_setting import GenreSetting

logger = logging.getLogger(__name__)


class GenreSettingsService:
    """
    Service layer for genre settings operations

    Provides methods for managing genre preferences for the Top-10
    discovery feature, including enabling/disabling genres and
    retrieving active genres.
    """

    @staticmethod
    def create_genre(
        db: Session,
        genre_name: str,
        is_enabled: bool = True,
        priority: int = 0
    ) -> Dict[str, Any]:
        """
        Create a new genre setting

        Args:
            db: Database session
            genre_name: Genre name (unique)
            is_enabled: Whether genre is enabled
            priority: Priority order for processing

        Returns:
            Dict with:
                - success: bool
                - data: GenreSetting object if successful
                - error: str if failed
                - genre_id: int if successful
        """
        try:
            # Check if genre already exists
            existing = db.query(GenreSetting).filter(
                GenreSetting.genre_name == genre_name
            ).first()
            if existing:
                logger.warning(f"Genre '{genre_name}' already exists (ID: {existing.id})")
                return {
                    "success": False,
                    "error": f"Genre '{genre_name}' already exists",
                    "data": existing,
                    "genre_id": existing.id
                }

            # Create new genre setting
            genre = GenreSetting(
                genre_name=genre_name,
                is_enabled=is_enabled,
                priority=priority
            )

            db.add(genre)
            db.commit()
            db.refresh(genre)

            logger.info(f"Created genre setting: {genre.genre_name} (ID: {genre.id})")

            return {
                "success": True,
                "data": genre,
                "genre_id": genre.id,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error creating genre '{genre_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None,
                "genre_id": None
            }

    @staticmethod
    def get_genre(db: Session, genre_id: int) -> Dict[str, Any]:
        """
        Get genre setting by ID

        Args:
            db: Database session
            genre_id: Genre setting ID

        Returns:
            Dict with success, data (GenreSetting or None), error
        """
        try:
            genre = db.query(GenreSetting).filter(GenreSetting.id == genre_id).first()

            if not genre:
                return {
                    "success": False,
                    "error": f"Genre with ID {genre_id} not found",
                    "data": None
                }

            return {
                "success": True,
                "data": genre,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting genre {genre_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def get_genre_by_name(db: Session, genre_name: str) -> Dict[str, Any]:
        """
        Get genre setting by name

        Args:
            db: Database session
            genre_name: Genre name

        Returns:
            Dict with success, data (GenreSetting or None), error
        """
        try:
            genre = db.query(GenreSetting).filter(
                GenreSetting.genre_name == genre_name
            ).first()

            if not genre:
                return {
                    "success": False,
                    "error": f"Genre '{genre_name}' not found",
                    "data": None
                }

            return {
                "success": True,
                "data": genre,
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting genre by name '{genre_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def get_enabled_genres(db: Session) -> Dict[str, Any]:
        """
        Get all enabled genres, ordered by priority

        Args:
            db: Database session

        Returns:
            Dict with success, data (list of GenreSetting), count, error
        """
        try:
            genres = db.query(GenreSetting).filter(
                GenreSetting.is_enabled == True
            ).order_by(
                GenreSetting.priority.desc(),
                GenreSetting.genre_name
            ).all()

            return {
                "success": True,
                "data": genres,
                "count": len(genres),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting enabled genres: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def get_disabled_genres(db: Session) -> Dict[str, Any]:
        """
        Get all disabled genres

        Args:
            db: Database session

        Returns:
            Dict with success, data (list of GenreSetting), count, error
        """
        try:
            genres = db.query(GenreSetting).filter(
                GenreSetting.is_enabled == False
            ).order_by(GenreSetting.genre_name).all()

            return {
                "success": True,
                "data": genres,
                "count": len(genres),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting disabled genres: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def get_all_genres(db: Session) -> Dict[str, Any]:
        """
        Get all genre settings

        Args:
            db: Database session

        Returns:
            Dict with success, data (list of GenreSetting), count, error
        """
        try:
            genres = db.query(GenreSetting).order_by(
                GenreSetting.priority.desc(),
                GenreSetting.genre_name
            ).all()

            return {
                "success": True,
                "data": genres,
                "count": len(genres),
                "error": None
            }

        except Exception as e:
            logger.error(f"Error getting all genres: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }

    @staticmethod
    def enable_genre(db: Session, genre_name: str) -> Dict[str, Any]:
        """
        Enable a genre for Top-10 discovery

        Args:
            db: Database session
            genre_name: Genre name to enable

        Returns:
            Dict with success, data (GenreSetting), error
        """
        try:
            genre = db.query(GenreSetting).filter(
                GenreSetting.genre_name == genre_name
            ).first()

            if not genre:
                return {
                    "success": False,
                    "error": f"Genre '{genre_name}' not found",
                    "data": None
                }

            if genre.is_enabled:
                return {
                    "success": True,
                    "data": genre,
                    "error": None,
                    "message": f"Genre '{genre_name}' was already enabled"
                }

            genre.is_enabled = True
            genre.date_updated = datetime.now()

            db.commit()
            db.refresh(genre)

            logger.info(f"Enabled genre: {genre_name}")

            return {
                "success": True,
                "data": genre,
                "error": None,
                "message": f"Genre '{genre_name}' enabled"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error enabling genre '{genre_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def disable_genre(db: Session, genre_name: str) -> Dict[str, Any]:
        """
        Disable a genre for Top-10 discovery

        Args:
            db: Database session
            genre_name: Genre name to disable

        Returns:
            Dict with success, data (GenreSetting), error
        """
        try:
            genre = db.query(GenreSetting).filter(
                GenreSetting.genre_name == genre_name
            ).first()

            if not genre:
                return {
                    "success": False,
                    "error": f"Genre '{genre_name}' not found",
                    "data": None
                }

            if not genre.is_enabled:
                return {
                    "success": True,
                    "data": genre,
                    "error": None,
                    "message": f"Genre '{genre_name}' was already disabled"
                }

            genre.is_enabled = False
            genre.date_updated = datetime.now()

            db.commit()
            db.refresh(genre)

            logger.info(f"Disabled genre: {genre_name}")

            return {
                "success": True,
                "data": genre,
                "error": None,
                "message": f"Genre '{genre_name}' disabled"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error disabling genre '{genre_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def set_priority(db: Session, genre_name: str, priority: int) -> Dict[str, Any]:
        """
        Set priority for a genre

        Args:
            db: Database session
            genre_name: Genre name
            priority: New priority value (higher = processed first)

        Returns:
            Dict with success, data (GenreSetting), error
        """
        try:
            genre = db.query(GenreSetting).filter(
                GenreSetting.genre_name == genre_name
            ).first()

            if not genre:
                return {
                    "success": False,
                    "error": f"Genre '{genre_name}' not found",
                    "data": None
                }

            old_priority = genre.priority
            genre.priority = priority
            genre.date_updated = datetime.now()

            db.commit()
            db.refresh(genre)

            logger.info(f"Updated priority for genre '{genre_name}': {old_priority} -> {priority}")

            return {
                "success": True,
                "data": genre,
                "error": None,
                "old_priority": old_priority
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error setting priority for genre '{genre_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": None
            }

    @staticmethod
    def delete_genre(db: Session, genre_name: str) -> Dict[str, Any]:
        """
        Delete a genre setting

        Args:
            db: Database session
            genre_name: Genre name to delete

        Returns:
            Dict with success, message, error
        """
        try:
            genre = db.query(GenreSetting).filter(
                GenreSetting.genre_name == genre_name
            ).first()

            if not genre:
                return {
                    "success": False,
                    "error": f"Genre '{genre_name}' not found",
                    "message": None
                }

            db.delete(genre)
            db.commit()

            logger.info(f"Deleted genre setting: {genre_name}")

            return {
                "success": True,
                "message": f"Genre '{genre_name}' deleted",
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting genre '{genre_name}': {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "message": None
            }

    @staticmethod
    def initialize_default_genres(db: Session) -> Dict[str, Any]:
        """
        Initialize default genre settings from config

        Loads ENABLED_GENRES and DISABLED_GENRES from config and
        creates GenreSetting records for each.

        Args:
            db: Database session

        Returns:
            Dict with success, created_count, skipped_count, error
        """
        try:
            from backend.config import get_settings
            settings = get_settings()

            created_count = 0
            skipped_count = 0

            # Add enabled genres
            for i, genre in enumerate(settings.ENABLED_GENRES):
                existing = db.query(GenreSetting).filter(
                    GenreSetting.genre_name == genre
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                genre_setting = GenreSetting(
                    genre_name=genre,
                    is_enabled=True,
                    priority=len(settings.ENABLED_GENRES) - i  # Higher priority for first items
                )
                db.add(genre_setting)
                created_count += 1

            # Add disabled genres
            for genre in settings.DISABLED_GENRES:
                existing = db.query(GenreSetting).filter(
                    GenreSetting.genre_name == genre
                ).first()

                if existing:
                    skipped_count += 1
                    continue

                genre_setting = GenreSetting(
                    genre_name=genre,
                    is_enabled=False,
                    priority=0
                )
                db.add(genre_setting)
                created_count += 1

            db.commit()

            logger.info(
                f"Initialized genre settings: {created_count} created, "
                f"{skipped_count} skipped (already exist)"
            )

            return {
                "success": True,
                "created_count": created_count,
                "skipped_count": skipped_count,
                "error": None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error initializing default genres: {e}", exc_info=True)
            return {
                "success": False,
                "created_count": 0,
                "skipped_count": 0,
                "error": str(e)
            }
