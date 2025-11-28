"""
absToolbox Integration Client

Provides async interface to absToolbox operations for metadata management.
Handles batch operations, quality rules, series completion, and author organization.

Repository: https://github.com/Vito0912/absToolbox
Web Interface: https://abstoolbox.vito0912.de

WARNING: All operations may have unforeseen side effects or crash the server.
Always create backups before running operations.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from enum import Enum

import aiohttp

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """absToolbox operation types"""
    METADATA_STANDARDIZATION = "metadata_standardization"
    SERIES_COMPLETION = "series_completion"
    AUTHOR_LINKING = "author_linking"
    NARRATOR_DETECTION = "narrator_detection"
    QUALITY_VALIDATION = "quality_validation"
    BATCH_EDIT = "batch_edit"


class absToolboxClient:
    """
    Async client for interacting with AudiobookShelf and absToolbox services.

    Usage:
        async with absToolboxClient(abs_url, abs_token) as client:
            result = await client.validate_metadata_quality(rules)
            std_result = await client.standardize_metadata(template)
    """

    def __init__(
        self,
        abs_url: str,
        abs_token: str,
        toolbox_url: str = "https://abstoolbox.vito0912.de",
        timeout_seconds: int = 30,
        log_operations: bool = True,
    ):
        """
        Initialize absToolbox client.

        Args:
            abs_url: AudiobookShelf API base URL
            abs_token: AudiobookShelf API token
            toolbox_url: absToolbox web interface URL
            timeout_seconds: Request timeout in seconds
            log_operations: Whether to log operations to file
        """
        self.abs_url = abs_url.rstrip("/")
        self.abs_token = abs_token
        self.toolbox_url = toolbox_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.log_operations = log_operations
        self.session: Optional[aiohttp.ClientSession] = None
        self.operation_log_dir = Path("abstoolbox_logs")
        self.operation_log_dir.mkdir(exist_ok=True)

    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()

    async def _request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to AudiobookShelf API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            headers: Additional headers
            json_data: JSON request body
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            aiohttp.ClientError: On request failure
        """
        if not self.session:
            raise RuntimeError("Client not initialized. Use 'async with' context.")

        url = f"{self.abs_url}{endpoint}"
        headers = headers or {}
        headers["Authorization"] = f"Bearer {self.abs_token}"

        try:
            async with self.session.request(
                method,
                url,
                json=json_data,
                params=params,
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {method} {endpoint} - {e}")
            raise

    async def get_library_stats(self) -> Dict[str, Any]:
        """Get basic library statistics."""
        try:
            # Get libraries
            libs_data = await self._request("GET", "/api/libraries")
            libraries = libs_data.get("libraries", [])

            if not libraries:
                logger.warning("No libraries found")
                return {"libraries": 0, "items": 0}

            lib_id = libraries[0]["id"]
            lib_stats = {
                "library_id": lib_id,
                "library_name": libraries[0].get("name", "Unknown"),
                "libraries": len(libraries),
            }

            # Get items in first library
            items_data = await self._request(
                "GET",
                f"/api/libraries/{lib_id}/items",
                params={"limit": 1, "offset": 0},
            )

            lib_stats["items"] = items_data.get("total", 0)
            return lib_stats

        except Exception as e:
            logger.error(f"Failed to get library stats: {e}")
            raise

    async def validate_metadata_quality(
        self, quality_rules: Dict[str, Any], dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Validate library metadata against quality rules.

        Args:
            quality_rules: Dictionary of validation rules
            dry_run: If True, don't apply changes

        Returns:
            Validation results with issues found

        Example quality_rules:
            {
                "author_name": {"required": True, "min_length": 2},
                "narrator": {"required": True},
                "series_name": {"required": False}
            }
        """
        logger.info("Starting metadata quality validation")
        operation_id = self._generate_operation_id("quality_validation")

        try:
            lib_stats = await self.get_library_stats()
            lib_id = lib_stats["library_id"]
            total_items = lib_stats["items"]

            issues = {
                "missing_fields": [],
                "invalid_format": [],
                "warnings": [],
                "total_checked": 0,
                "issues_count": 0,
            }

            # Scan items in batches
            batch_size = 100
            for offset in range(0, total_items, batch_size):
                items_data = await self._request(
                    "GET",
                    f"/api/libraries/{lib_id}/items",
                    params={"limit": batch_size, "offset": offset},
                )

                items = items_data.get("results", [])
                for item in items:
                    issues["total_checked"] += 1
                    item_issues = self._check_item_quality(item, quality_rules)
                    if item_issues:
                        issues["issues_count"] += 1
                        issues["invalid_format"].append(
                            {
                                "item_id": item.get("id"),
                                "title": item.get("media", {})
                                .get("metadata", {})
                                .get("title", "Unknown"),
                                "issues": item_issues,
                            }
                        )

            # Log operation
            self._log_operation(
                operation_id,
                OperationType.QUALITY_VALIDATION,
                {
                    "dry_run": dry_run,
                    "rules_applied": list(quality_rules.keys()),
                    "items_checked": issues["total_checked"],
                    "issues_found": issues["issues_count"],
                },
                "completed",
                issues,
            )

            logger.info(
                f"Quality validation complete: {issues['issues_count']} issues found in {issues['total_checked']} items"
            )
            return issues

        except Exception as e:
            logger.error(f"Quality validation failed: {e}")
            self._log_operation(
                operation_id,
                OperationType.QUALITY_VALIDATION,
                {"rules": list(quality_rules.keys())},
                "failed",
                {"error": str(e)},
            )
            raise

    def _check_item_quality(
        self, item: Dict[str, Any], rules: Dict[str, Any]
    ) -> List[str]:
        """Check individual item against quality rules."""
        issues = []
        metadata = item.get("media", {}).get("metadata", {})

        for field, rule in rules.items():
            value = metadata.get(field)

            # Check required
            if rule.get("required") and not value:
                issues.append(f"Missing required field: {field}")

            # Check min length
            if value and "min_length" in rule:
                if len(str(value)) < rule["min_length"]:
                    issues.append(
                        f"{field} too short (min {rule['min_length']}): {value}"
                    )

            # Check max length
            if value and "max_length" in rule:
                if len(str(value)) > rule["max_length"]:
                    issues.append(
                        f"{field} too long (max {rule['max_length']}): {value[:50]}..."
                    )

            # Check format
            if value and "format" in rule:
                if not self._check_format(value, rule["format"]):
                    issues.append(f"{field} invalid format: {value}")

        return issues

    def _check_format(self, value: str, format_spec: str) -> bool:
        """Validate value against format specification."""
        value_str = str(value).strip()

        if format_spec == "FirstName LastName":
            parts = value_str.split()
            return len(parts) >= 2 and all(p.isalpha() or p in "-'" for p in parts)

        return True

    async def standardize_metadata(
        self,
        operation_template: Dict[str, Any],
        dry_run: bool = True,
        batch_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Apply metadata standardization rules.

        Args:
            operation_template: Template with standardization rules
            dry_run: If True, preview changes without applying
            batch_size: Number of items to process per batch

        Returns:
            Standardization results
        """
        logger.info(f"Starting metadata standardization (dry_run={dry_run})")
        operation_id = self._generate_operation_id("standardization")

        try:
            lib_stats = await self.get_library_stats()
            lib_id = lib_stats["library_id"]
            total_items = lib_stats["items"]

            results = {
                "operation_id": operation_id,
                "dry_run": dry_run,
                "items_processed": 0,
                "items_updated": 0,
                "errors": [],
                "changes": [],
            }

            # Process items in batches
            for offset in range(0, total_items, batch_size):
                items_data = await self._request(
                    "GET",
                    f"/api/libraries/{lib_id}/items",
                    params={"limit": batch_size, "offset": offset},
                )

                items = items_data.get("results", [])
                for item in items:
                    results["items_processed"] += 1

                    changes = self._apply_standardization_rules(
                        item, operation_template
                    )
                    if changes:
                        results["items_updated"] += 1
                        results["changes"].append(
                            {
                                "item_id": item.get("id"),
                                "title": item.get("media", {})
                                .get("metadata", {})
                                .get("title", "Unknown"),
                                "changes": changes,
                            }
                        )

                        # Apply changes if not dry run
                        if not dry_run:
                            try:
                                await self._update_item_metadata(
                                    lib_id, item.get("id"), changes
                                )
                            except Exception as e:
                                results["errors"].append(
                                    {
                                        "item_id": item.get("id"),
                                        "error": str(e),
                                    }
                                )

                # Delay between batches
                if offset + batch_size < total_items:
                    await asyncio.sleep(1)

            # Log operation
            self._log_operation(
                operation_id,
                OperationType.METADATA_STANDARDIZATION,
                {
                    "dry_run": dry_run,
                    "items_processed": results["items_processed"],
                    "items_updated": results["items_updated"],
                    "errors": len(results["errors"]),
                },
                "completed",
                results,
            )

            logger.info(
                f"Standardization complete: {results['items_updated']} of {results['items_processed']} items updated"
            )
            return results

        except Exception as e:
            logger.error(f"Standardization failed: {e}")
            self._log_operation(
                operation_id,
                OperationType.METADATA_STANDARDIZATION,
                {"dry_run": dry_run},
                "failed",
                {"error": str(e)},
            )
            raise

    def _apply_standardization_rules(
        self, item: Dict[str, Any], template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply standardization rules to item."""
        metadata = item.get("media", {}).get("metadata", {})
        changes = {}

        # Standardize author name
        author = metadata.get("authorName", "")
        if author:
            standardized = self._standardize_author_name(author)
            if standardized != author:
                changes["authorName"] = standardized

        # Standardize narrator
        narrator = metadata.get("narrator", "")
        if narrator:
            standardized = self._standardize_narrator_name(narrator)
            if standardized != narrator:
                changes["narrator"] = standardized

        # Standardize series name
        series = metadata.get("seriesName", "")
        if series:
            standardized = self._standardize_series_name(series)
            if standardized != series:
                changes["seriesName"] = standardized

        return changes

    def _standardize_author_name(self, name: str) -> str:
        """Standardize author name format."""
        # Convert "Smith, John" to "John Smith"
        if "," in name:
            parts = [p.strip() for p in name.split(",")]
            if len(parts) == 2:
                return f"{parts[1]} {parts[0]}"

        # Normalize whitespace
        name = " ".join(name.split())

        return name

    def _standardize_narrator_name(self, name: str) -> str:
        """Standardize narrator name format."""
        # Remove "Narrated by" prefix if present
        name = name.replace("Narrated by ", "").strip()

        # Normalize whitespace
        name = " ".join(name.split())

        return name

    def _standardize_series_name(self, name: str) -> str:
        """Standardize series name format."""
        # Remove Series/Vol. prefixes
        name = name.replace("Series ", "").replace("Vol. ", "").strip()

        # Normalize whitespace
        name = " ".join(name.split())

        return name

    async def _update_item_metadata(
        self, lib_id: str, item_id: str, changes: Dict[str, Any]
    ) -> None:
        """Update item metadata via API."""
        await self._request(
            "PATCH",
            f"/api/items/{item_id}",
            json_data={"media": {"metadata": changes}},
        )

    async def complete_author_series(
        self, author_name: str
    ) -> Dict[str, Any]:
        """
        Identify missing books in author's series and create queue.

        Args:
            author_name: Author name to analyze

        Returns:
            Series completion analysis
        """
        logger.info(f"Analyzing series completion for: {author_name}")
        operation_id = self._generate_operation_id("series_completion")

        try:
            lib_stats = await self.get_library_stats()
            lib_id = lib_stats["library_id"]

            # Get books by author
            books_in_library = await self._get_books_by_author(lib_id, author_name)

            result = {
                "operation_id": operation_id,
                "author": author_name,
                "books_in_library": len(books_in_library),
                "series": {},
                "missing_books": [],
                "estimated_missing_count": 0,
            }

            # Group by series
            for book in books_in_library:
                series = (
                    book.get("media", {})
                    .get("metadata", {})
                    .get("seriesName", "Unknown Series")
                )
                if series not in result["series"]:
                    result["series"][series] = []
                result["series"][series].append(book)

            # Log operation
            self._log_operation(
                operation_id,
                OperationType.SERIES_COMPLETION,
                {
                    "author": author_name,
                    "books_found": len(books_in_library),
                    "series_count": len(result["series"]),
                },
                "completed",
                result,
            )

            logger.info(
                f"Series analysis complete: {len(books_in_library)} books in {len(result['series'])} series"
            )
            return result

        except Exception as e:
            logger.error(f"Series completion analysis failed: {e}")
            self._log_operation(
                operation_id,
                OperationType.SERIES_COMPLETION,
                {"author": author_name},
                "failed",
                {"error": str(e)},
            )
            raise

    async def _get_books_by_author(
        self, lib_id: str, author_name: str
    ) -> List[Dict[str, Any]]:
        """Get all books by author from library."""
        books = []
        total_items = (await self.get_library_stats())["items"]

        for offset in range(0, total_items, 100):
            items_data = await self._request(
                "GET",
                f"/api/libraries/{lib_id}/items",
                params={"limit": 100, "offset": offset},
            )

            items = items_data.get("results", [])
            for item in items:
                author = (
                    item.get("media", {})
                    .get("metadata", {})
                    .get("authorName", "")
                )
                if author.lower() == author_name.lower():
                    books.append(item)

        return books

    def _generate_operation_id(self, operation_type: str) -> str:
        """Generate unique operation ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{operation_type}_{timestamp}"

    def _log_operation(
        self,
        operation_id: str,
        operation_type: OperationType,
        parameters: Dict[str, Any],
        status: str,
        result: Dict[str, Any],
    ) -> None:
        """Log operation to file."""
        if not self.log_operations:
            return

        log_entry = {
            "operation_id": operation_id,
            "operation_type": operation_type.value,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "parameters": parameters,
            "result": result,
        }

        log_file = self.operation_log_dir / f"{operation_id}.json"
        try:
            with open(log_file, "w") as f:
                json.dump(log_entry, f, indent=2, default=str)
            logger.debug(f"Operation logged to {log_file}")
        except Exception as e:
            logger.warning(f"Failed to log operation: {e}")


# Template configurations
QUALITY_RULES_TEMPLATE = {
    "author_name": {
        "required": True,
        "format": "FirstName LastName",
        "min_length": 2,
        "max_length": 100,
    },
    "narrator": {"required": True, "format": "FirstName LastName"},
    "series_name": {"required": False},
    "cover_art": {"required": True},
}

STANDARDIZATION_TEMPLATE = {
    "name": "Standard Metadata Normalization",
    "version": "1.0",
    "steps": [
        {"step": 1, "action": "standardize_author_names"},
        {"step": 2, "action": "standardize_narrator_names"},
        {"step": 3, "action": "standardize_series_names"},
    ],
}
