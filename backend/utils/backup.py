"""
Database Backup and Recovery Utilities

Provides automated backup and restore functionality for the PostgreSQL database.
Supports scheduled backups, retention policies, and disaster recovery.
"""

import os
import gzip
import shutil
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from backend.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseBackup:
    """
    Database backup and recovery manager.

    Supports:
    - Full database dumps using pg_dump
    - Compressed backup storage
    - Configurable retention policies
    - Point-in-time recovery

    Example:
        >>> backup = DatabaseBackup()
        >>> backup_file = backup.create_backup()
        >>> print(f"Backup created: {backup_file}")

        >>> # List available backups
        >>> backups = backup.list_backups()

        >>> # Restore from backup
        >>> backup.restore_backup("backup_20250118_120000.sql.gz")
    """

    def __init__(
        self,
        backup_dir: Optional[str] = None,
        retention_days: int = 30,
        max_backups: int = 100,
    ):
        """
        Initialize backup manager.

        Args:
            backup_dir: Directory for storing backups (default: PROJECT_ROOT/backups)
            retention_days: Number of days to keep backups
            max_backups: Maximum number of backups to retain
        """
        self.settings = get_settings()
        self.backup_dir = Path(backup_dir) if backup_dir else self.settings.PROJECT_ROOT / "backups"
        self.retention_days = retention_days
        self.max_backups = max_backups

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Parse database URL for connection details
        self._parse_database_url()

        logger.info(f"DatabaseBackup initialized - dir: {self.backup_dir}, retention: {retention_days} days")

    def _parse_database_url(self):
        """Parse PostgreSQL connection details from DATABASE_URL."""
        url = self.settings.DATABASE_URL

        # Handle both postgresql:// and postgres:// schemes
        if url.startswith("postgresql://") or url.startswith("postgres://"):
            # Remove scheme
            url = url.split("://", 1)[1]

            # Extract user:password@host:port/database
            if "@" in url:
                auth, rest = url.split("@", 1)
                if ":" in auth:
                    self.db_user, self.db_password = auth.split(":", 1)
                else:
                    self.db_user = auth
                    self.db_password = ""
            else:
                rest = url
                self.db_user = "postgres"
                self.db_password = ""

            if "/" in rest:
                host_port, self.db_name = rest.split("/", 1)
            else:
                host_port = rest
                self.db_name = "postgres"

            if ":" in host_port:
                self.db_host, port_str = host_port.split(":", 1)
                self.db_port = port_str.split("?")[0]  # Remove query params
            else:
                self.db_host = host_port.split("?")[0]
                self.db_port = "5432"
        else:
            # SQLite or other database
            self.db_type = "sqlite"
            self.db_path = url.replace("sqlite:///", "")
            logger.info(f"SQLite database detected: {self.db_path}")

    def create_backup(self, compress: bool = True) -> str:
        """
        Create a database backup.

        Args:
            compress: Whether to gzip compress the backup

        Returns:
            Path to the created backup file

        Raises:
            RuntimeError: If backup fails
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if hasattr(self, 'db_type') and self.db_type == "sqlite":
            return self._backup_sqlite(timestamp, compress)
        else:
            return self._backup_postgresql(timestamp, compress)

    def _backup_sqlite(self, timestamp: str, compress: bool) -> str:
        """Create SQLite backup by copying database file."""
        backup_name = f"backup_{timestamp}.db"
        if compress:
            backup_name += ".gz"

        backup_path = self.backup_dir / backup_name
        source_path = Path(self.db_path)

        if not source_path.exists():
            raise RuntimeError(f"Source database not found: {source_path}")

        try:
            if compress:
                with open(source_path, 'rb') as f_in:
                    with gzip.open(backup_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(source_path, backup_path)

            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"SQLite backup created: {backup_path} ({size_mb:.2f} MB)")

            # Apply retention policy
            self._apply_retention_policy()

            return str(backup_path)

        except Exception as e:
            logger.error(f"SQLite backup failed: {e}")
            raise RuntimeError(f"Backup failed: {e}")

    def _backup_postgresql(self, timestamp: str, compress: bool) -> str:
        """Create PostgreSQL backup using pg_dump."""
        backup_name = f"backup_{timestamp}.sql"
        if compress:
            backup_name += ".gz"

        backup_path = self.backup_dir / backup_name

        # Set password in environment
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_password

        # Build pg_dump command
        cmd = [
            "pg_dump",
            "-h", self.db_host,
            "-p", self.db_port,
            "-U", self.db_user,
            "-d", self.db_name,
            "--format=plain",
            "--no-owner",
            "--no-acl",
        ]

        try:
            logger.info(f"Creating PostgreSQL backup: {backup_name}")

            if compress:
                # Pipe through gzip
                with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
                    result = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        env=env,
                        text=True,
                        check=True,
                    )
            else:
                with open(backup_path, 'w') as f:
                    result = subprocess.run(
                        cmd,
                        stdout=f,
                        stderr=subprocess.PIPE,
                        env=env,
                        text=True,
                        check=True,
                    )

            size_mb = backup_path.stat().st_size / (1024 * 1024)
            logger.info(f"PostgreSQL backup created: {backup_path} ({size_mb:.2f} MB)")

            # Apply retention policy
            self._apply_retention_policy()

            return str(backup_path)

        except subprocess.CalledProcessError as e:
            logger.error(f"pg_dump failed: {e.stderr}")
            raise RuntimeError(f"Backup failed: {e.stderr}")
        except FileNotFoundError:
            logger.error("pg_dump not found. Ensure PostgreSQL client tools are installed.")
            raise RuntimeError("pg_dump not found")

    def restore_backup(self, backup_name: str, confirm: bool = False) -> bool:
        """
        Restore database from backup.

        Args:
            backup_name: Name of backup file to restore
            confirm: Must be True to proceed with restore

        Returns:
            True if restore succeeded

        Raises:
            RuntimeError: If restore fails
            ValueError: If confirm is False
        """
        if not confirm:
            raise ValueError("Must set confirm=True to restore. This will overwrite existing data!")

        backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            raise RuntimeError(f"Backup not found: {backup_path}")

        if hasattr(self, 'db_type') and self.db_type == "sqlite":
            return self._restore_sqlite(backup_path)
        else:
            return self._restore_postgresql(backup_path)

    def _restore_sqlite(self, backup_path: Path) -> bool:
        """Restore SQLite database from backup."""
        target_path = Path(self.db_path)

        try:
            # Create backup of current database before restore
            if target_path.exists():
                pre_restore_backup = target_path.with_suffix('.db.pre_restore')
                shutil.copy2(target_path, pre_restore_backup)
                logger.info(f"Created pre-restore backup: {pre_restore_backup}")

            # Restore from backup
            if str(backup_path).endswith('.gz'):
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(target_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_path, target_path)

            logger.info(f"SQLite database restored from: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"SQLite restore failed: {e}")
            raise RuntimeError(f"Restore failed: {e}")

    def _restore_postgresql(self, backup_path: Path) -> bool:
        """Restore PostgreSQL database from backup."""
        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_password

        # Build psql command
        cmd = [
            "psql",
            "-h", self.db_host,
            "-p", self.db_port,
            "-U", self.db_user,
            "-d", self.db_name,
        ]

        try:
            logger.info(f"Restoring PostgreSQL from: {backup_path}")

            if str(backup_path).endswith('.gz'):
                # Decompress and pipe to psql
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    result = subprocess.run(
                        cmd,
                        stdin=f,
                        stderr=subprocess.PIPE,
                        env=env,
                        text=True,
                        check=True,
                    )
            else:
                with open(backup_path, 'r') as f:
                    result = subprocess.run(
                        cmd,
                        stdin=f,
                        stderr=subprocess.PIPE,
                        env=env,
                        text=True,
                        check=True,
                    )

            logger.info(f"PostgreSQL database restored successfully")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"psql restore failed: {e.stderr}")
            raise RuntimeError(f"Restore failed: {e.stderr}")

    def list_backups(self) -> List[dict]:
        """
        List all available backups.

        Returns:
            List of backup info dictionaries with keys:
            - name: Backup filename
            - path: Full path
            - size_mb: Size in megabytes
            - created: Creation timestamp
        """
        backups = []

        for f in sorted(self.backup_dir.glob("backup_*"), reverse=True):
            stat = f.stat()
            backups.append({
                "name": f.name,
                "path": str(f),
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })

        return backups

    def _apply_retention_policy(self):
        """Remove old backups based on retention policy."""
        backups = self.list_backups()
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)

        removed_count = 0

        for backup in backups:
            backup_date = datetime.fromisoformat(backup["created"])
            backup_path = Path(backup["path"])

            # Remove if older than retention period
            if backup_date < cutoff_date:
                backup_path.unlink()
                logger.info(f"Removed old backup: {backup['name']} (age: {self.retention_days}+ days)")
                removed_count += 1

        # Also enforce max backup count
        current_backups = self.list_backups()
        if len(current_backups) > self.max_backups:
            for backup in current_backups[self.max_backups:]:
                Path(backup["path"]).unlink()
                logger.info(f"Removed excess backup: {backup['name']} (max: {self.max_backups})")
                removed_count += 1

        if removed_count > 0:
            logger.info(f"Retention policy applied: removed {removed_count} backups")

    def get_backup_stats(self) -> dict:
        """
        Get backup statistics.

        Returns:
            Dictionary with backup statistics
        """
        backups = self.list_backups()

        if not backups:
            return {
                "count": 0,
                "total_size_mb": 0,
                "oldest": None,
                "newest": None,
            }

        total_size = sum(b["size_mb"] for b in backups)

        return {
            "count": len(backups),
            "total_size_mb": round(total_size, 2),
            "oldest": backups[-1]["created"] if backups else None,
            "newest": backups[0]["created"] if backups else None,
            "backup_dir": str(self.backup_dir),
            "retention_days": self.retention_days,
        }


# Convenience function for scheduled backups
def create_scheduled_backup() -> str:
    """
    Create a backup (for use with scheduler).

    Returns:
        Path to created backup file
    """
    backup = DatabaseBackup()
    return backup.create_backup()


if __name__ == "__main__":
    # CLI for manual backup operations
    import sys

    logging.basicConfig(level=logging.INFO)

    backup = DatabaseBackup()

    if len(sys.argv) < 2:
        print("Usage: python -m backend.utils.backup <command>")
        print("Commands:")
        print("  create    - Create a new backup")
        print("  list      - List all backups")
        print("  stats     - Show backup statistics")
        print("  restore <name> - Restore from backup")
        sys.exit(1)

    command = sys.argv[1]

    if command == "create":
        backup_file = backup.create_backup()
        print(f"Backup created: {backup_file}")

    elif command == "list":
        backups = backup.list_backups()
        if not backups:
            print("No backups found")
        else:
            print(f"{'Name':<40} {'Size (MB)':<12} {'Created':<25}")
            print("-" * 77)
            for b in backups:
                print(f"{b['name']:<40} {b['size_mb']:<12} {b['created']:<25}")

    elif command == "stats":
        stats = backup.get_backup_stats()
        print(f"Backup Statistics:")
        print(f"  Count: {stats['count']}")
        print(f"  Total Size: {stats['total_size_mb']} MB")
        print(f"  Oldest: {stats['oldest']}")
        print(f"  Newest: {stats['newest']}")
        print(f"  Directory: {stats['backup_dir']}")
        print(f"  Retention: {stats['retention_days']} days")

    elif command == "restore":
        if len(sys.argv) < 3:
            print("Usage: python -m backend.utils.backup restore <backup_name>")
            sys.exit(1)

        backup_name = sys.argv[2]
        print(f"WARNING: This will restore from {backup_name}")
        print("This will OVERWRITE the current database!")
        confirm = input("Type 'yes' to confirm: ")

        if confirm.lower() == 'yes':
            backup.restore_backup(backup_name, confirm=True)
            print("Restore completed successfully")
        else:
            print("Restore cancelled")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
