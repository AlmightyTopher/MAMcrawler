"""
Safety Validator Module
Implements comprehensive safety checks for all operations to prevent data loss and protect configurations.

Key Principles:
- Non-destructive operations only
- Backup-first policy for metadata edits
- .env file write protection
- All operations logged in audit trail
"""

import os
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import hashlib

from backend.config import get_config

logger = logging.getLogger(__name__)


class SafetyValidator:
    """Validates operations for safety compliance and initiates necessary safeguards"""

    def __init__(self):
        self.config = get_config()
        self.protected_ops = self.config.PROTECTED_OPERATIONS
        self.backup_dir = Path(self.config.BACKUP_DIR)
        self.audit_log_dir = Path(self.config.AUDIT_LOG_DIR)

        # Initialize backup and audit directories
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_dir.mkdir(parents=True, exist_ok=True)

    def validate_operation(self, operation_type: str, flags: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that an operation has required safety flags and permissions.

        Args:
            operation_type: Type of operation (from PROTECTED_OPERATIONS)
            flags: Dictionary of flags provided by user/system

        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if operation_type not in self.protected_ops:
            return True, ""

        # Specific validations per operation
        if operation_type == "delete_audiobook":
            return self._validate_delete_audiobook(flags)
        elif operation_type == "delete_metadata":
            return self._validate_delete_metadata(flags)
        elif operation_type == "drm_removal":
            return self._validate_drm_removal(flags)
        elif operation_type == "replace_audio_file":
            return self._validate_replace_audio_file(flags)
        elif operation_type == "modify_env_file":
            return self._validate_modify_env_file(flags)

        return False, f"Unknown protected operation: {operation_type}"

    def _validate_delete_audiobook(self, flags: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate delete operation requires explicit confirmation"""
        if not flags.get("confirmed_delete"):
            return False, "DELETE operation requires confirmed_delete=True flag"
        if not flags.get("preserve_metadata"):
            return False, "DELETE operation requires preserve_metadata=True to keep metadata.json"
        return True, ""

    def _validate_delete_metadata(self, flags: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate metadata delete requires backup creation"""
        if not flags.get("backup_created"):
            return False, "METADATA DELETE operation requires backup_created=True"
        if not flags.get("confirmed_irreversible"):
            return False, "METADATA DELETE is irreversible and requires confirmed_irreversible=True"
        return True, ""

    def _validate_drm_removal(self, flags: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate DRM removal is explicitly enabled in config"""
        if not self.config.ALLOW_DRM_REMOVAL:
            return False, "DRM_REMOVAL is disabled. Set ALLOW_DRM_REMOVAL=true in .env to enable"
        if not flags.get("confirmed_drm_removal"):
            return False, "DRM_REMOVAL requires confirmed_drm_removal=True flag"
        return True, ""

    def _validate_replace_audio_file(self, flags: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate audio file replacement with backup"""
        if not flags.get("backup_created"):
            return False, "REPLACE_AUDIO_FILE requires backup_created=True (original must be backed up)"
        if not flags.get("verified_replacement"):
            return False, "REPLACE_AUDIO_FILE requires verified_replacement=True (new file verified first)"
        return True, ""

    def _validate_modify_env_file(self, flags: Dict[str, Any]) -> Tuple[bool, str]:
        """Block all .env modifications"""
        return False, "ENV_FILE modifications are blocked by safety policy. Use environment variables instead."

    def check_env_write_attempt(self, target_path: str) -> bool:
        """
        Check if operation is attempting to write to .env file.
        Returns True if write is attempted (which is blocked).
        """
        target = Path(target_path).resolve()
        env_file = Path(".env").resolve()

        if target == env_file:
            logger.error(f"BLOCKED: Attempt to write to .env file from {target}")
            return True

        return False

    def require_backup_before_edit(self, file_path: str) -> Tuple[bool, str]:
        """
        Enforce backup-first policy before editing metadata.json.
        Creates backup if it doesn't exist.

        Args:
            file_path: Path to metadata.json file

        Returns:
            Tuple[bool, str]: (success, backup_path or error_message)
        """
        file_path = Path(file_path).resolve()

        if not file_path.exists():
            return False, f"File not found: {file_path}"

        if file_path.name != "metadata.json":
            return False, "Backup required only for metadata.json files"

        # Create backup with timestamp
        backup_name = f"{file_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = self.backup_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
            return True, str(backup_path)
        except Exception as e:
            logger.error(f"Backup creation failed for {file_path}: {e}")
            return False, f"Backup failed: {str(e)}"

    def verify_backup_exists(self, backup_path: str) -> bool:
        """
        Verify that a backup file exists and is readable.

        Args:
            backup_path: Path to backup file

        Returns:
            bool: True if backup exists and is valid
        """
        backup = Path(backup_path)

        if not backup.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False

        try:
            # Verify JSON is valid
            with open(backup, 'r', encoding='utf-8') as f:
                json.load(f)
            logger.info(f"Backup verified: {backup_path}")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"Backup JSON invalid: {backup_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Backup verification failed: {backup_path}: {e}")
            return False

    def verify_non_destructive(self, file_path: str, old_data: Any, new_data: Any) -> Tuple[bool, str]:
        """
        Verify that changes are non-destructive (additive/corrective, not lossy).

        Args:
            file_path: Path to file being modified
            old_data: Original data (dict or JSON-compatible)
            new_data: New data (dict or JSON-compatible)

        Returns:
            Tuple[bool, str]: (is_non_destructive, details)
        """
        if not isinstance(old_data, dict) or not isinstance(new_data, dict):
            return False, "Non-destructive check requires dict data"

        # Check for deleted fields
        deleted_fields = set(old_data.keys()) - set(new_data.keys())
        if deleted_fields:
            return False, f"DESTRUCTIVE CHANGE DETECTED: Fields would be deleted: {deleted_fields}"

        # Check for null/empty overwrites of non-empty fields
        for key in old_data:
            if key in new_data:
                old_val = old_data[key]
                new_val = new_data[key]

                # If old has value and new is empty/null, it's destructive
                if old_val and not new_val:
                    return False, f"DESTRUCTIVE: Would overwrite non-empty '{key}' with empty value"

        logger.info(f"Non-destructive verification passed for {file_path}")
        return True, "Changes are non-destructive"

    def log_operation(self, operation_type: str, target: str, result: bool, details: str = "") -> None:
        """
        Log all operations to audit trail (append-only).

        Args:
            operation_type: Type of operation
            target: Target file/resource
            result: True if successful, False if failed
            details: Additional details
        """
        if not self.config.AUDIT_LOG_ENABLED:
            return

        audit_log = self.audit_log_dir / f"{datetime.now().strftime('%Y%m%d')}_operations.log"

        timestamp = datetime.now().isoformat()
        status = "SUCCESS" if result else "FAILED"
        log_entry = {
            "timestamp": timestamp,
            "operation": operation_type,
            "target": target,
            "status": status,
            "details": details
        }

        try:
            with open(audit_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def get_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of file for integrity verification.

        Args:
            file_path: Path to file

        Returns:
            str: SHA256 hash hex string
        """
        sha256_hash = hashlib.sha256()
        file_path = Path(file_path)

        if not file_path.exists():
            return ""

        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Hash calculation failed for {file_path}: {e}")
            return ""

    def verify_file_integrity(self, file_path: str, expected_hash: str) -> bool:
        """
        Verify file integrity by comparing hashes.

        Args:
            file_path: Path to file
            expected_hash: Expected SHA256 hash

        Returns:
            bool: True if file matches expected hash
        """
        actual_hash = self.get_file_hash(file_path)
        if actual_hash == expected_hash:
            logger.info(f"File integrity verified: {file_path}")
            return True
        else:
            logger.error(f"File integrity check FAILED: {file_path}")
            return False

    def cleanup_old_backups(self) -> int:
        """
        Remove backups older than BACKUP_RETENTION_DAYS.

        Returns:
            int: Number of backups deleted
        """
        if not self.config.BACKUP_ENABLED:
            return 0

        deleted_count = 0
        cutoff_date = datetime.now().timestamp() - (self.config.BACKUP_RETENTION_DAYS * 86400)

        for backup_file in self.backup_dir.glob("*.json"):
            if backup_file.stat().st_mtime < cutoff_date:
                try:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.info(f"Old backup deleted: {backup_file}")
                except Exception as e:
                    logger.error(f"Failed to delete backup {backup_file}: {e}")

        return deleted_count


# Convenience function for application-wide access
def get_safety_validator() -> SafetyValidator:
    """Get SafetyValidator instance"""
    return SafetyValidator()
