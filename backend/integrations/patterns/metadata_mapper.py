"""
Metadata field mapping and transformation pattern.

Provides a framework for mapping and transforming fields from API responses
or client requests. Useful for:
- Converting API response fields to internal model fields
- Transforming data types (e.g., string timestamps to datetime)
- Validating field values
- Extracting nested fields
- Filtering sensitive data

Usage:
    >>> mapper = MetadataMapper({
    ...     "title": lambda x: x,  # Pass through
    ...     "author_name": FieldMapping("author", transform=str.upper),
    ...     "pub_date": FieldMapping("publishedAt", transform=parse_date),
    ...     "isbn": FieldMapping("id", optional=True),
    ... })
    >>> result = mapper.transform(api_response)
"""

import logging
from typing import Any, Callable, Dict, Optional, List

logger = logging.getLogger(__name__)


class FieldMapping:
    """
    Specification for mapping a single field.

    Defines how to extract, transform, and validate a field during mapping.

    Args:
        source_key: Key in source dict to extract (if different from dest key)
        transform: Function to transform the value
        optional: If True, missing source key doesn't raise error
        default: Default value if source key is missing
        validate: Function to validate transformed value (raises if False)
        nested: For nested fields like "author.name", use dot notation
    """

    def __init__(
        self,
        source_key: Optional[str] = None,
        transform: Optional[Callable] = None,
        optional: bool = False,
        default: Any = None,
        validate: Optional[Callable] = None,
        nested: bool = False,
    ):
        self.source_key = source_key
        self.transform = transform or (lambda x: x)  # Identity function
        self.optional = optional
        self.default = default
        self.validate = validate
        self.nested = nested

    def apply(self, source: Dict[str, Any]) -> Any:
        """
        Extract and transform a field from source dict.

        Args:
            source: Source dictionary to extract from

        Returns:
            Transformed value

        Raises:
            KeyError: If required field is missing
            ValueError: If validation fails
        """
        # Get source value
        if self.nested and self.source_key:
            # Handle nested keys like "author.name"
            value = self._get_nested(source, self.source_key)
        else:
            value = source.get(self.source_key) if self.source_key else source

        # Handle missing values
        if value is None:
            if self.optional:
                return self.default
            elif self.default is not None:
                value = self.default
            else:
                raise KeyError(f"Required field missing: {self.source_key}")

        # Transform
        transformed = self.transform(value)

        # Validate
        if self.validate and not self.validate(transformed):
            raise ValueError(f"Validation failed for field: {self.source_key}")

        return transformed

    @staticmethod
    def _get_nested(source: Dict, path: str) -> Any:
        """Extract value from nested dict using dot notation."""
        keys = path.split(".")
        value = source
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


class MetadataMapper:
    """
    Framework for mapping and transforming field dictionaries.

    Provides a declarative way to specify field mappings, transformations,
    and validations.

    Args:
        mappings: Dict where:
            - key: destination field name
            - value: FieldMapping instance or transform function

    Example:
        >>> from datetime import datetime
        >>> def parse_date(s):
        ...     return datetime.fromisoformat(s) if s else None
        ...
        >>> mapper = MetadataMapper({
        ...     "title": FieldMapping("bookTitle"),
        ...     "author": FieldMapping("authorName", transform=str.title),
        ...     "published": FieldMapping("pubDate", transform=parse_date),
        ...     "pages": FieldMapping(
        ...         "pageCount",
        ...         transform=int,
        ...         optional=True,
        ...         default=0
        ...     ),
        ... })
        >>>
        >>> result = mapper.transform({
        ...     "bookTitle": "The Hobbit",
        ...     "authorName": "j.r.r. tolkien",
        ...     "pubDate": "1937-09-21",
        ... })
        >>> print(result)
        {'title': 'The Hobbit', 'author': 'J.R.R. Tolkien', ...}
    """

    def __init__(self, mappings: Dict[str, Any]):
        """Initialize mapper with field mappings."""
        self.mappings = {}

        for dest_key, mapping in mappings.items():
            if isinstance(mapping, FieldMapping):
                self.mappings[dest_key] = mapping
            elif callable(mapping):
                # Simple function as mapping
                self.mappings[dest_key] = FieldMapping(
                    source_key=dest_key,
                    transform=mapping
                )
            elif isinstance(mapping, str):
                # String means source_key different from dest_key
                self.mappings[dest_key] = FieldMapping(source_key=mapping)
            else:
                # Simple passthrough
                self.mappings[dest_key] = FieldMapping(source_key=dest_key)

        logger.debug(f"Initialized MetadataMapper with {len(self.mappings)} fields")

    def transform(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform source dictionary using defined mappings.

        Args:
            source: Source dictionary to transform

        Returns:
            Transformed dictionary with mapped fields

        Raises:
            KeyError: If required field is missing
            ValueError: If validation fails

        Example:
            >>> mapper = MetadataMapper({"name": "full_name"})
            >>> result = mapper.transform({"full_name": "John Doe"})
            >>> print(result["name"])
            'John Doe'
        """
        result = {}

        for dest_key, mapping in self.mappings.items():
            try:
                result[dest_key] = mapping.apply(source)
            except KeyError as e:
                logger.error(f"Missing required field: {e}")
                raise
            except ValueError as e:
                logger.error(f"Validation error: {e}")
                raise

        return result

    def transform_partial(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform with graceful error handling.

        Missing optional fields are skipped, required fields are included.

        Args:
            source: Source dictionary

        Returns:
            Partially transformed dictionary (may have fewer fields)
        """
        result = {}

        for dest_key, mapping in self.mappings.items():
            try:
                # For optional fields, skip if source key is missing
                if mapping.optional and mapping.source_key:
                    # For nested fields, check if path exists
                    if mapping.nested:
                        if FieldMapping._get_nested(source, mapping.source_key) is None:
                            logger.debug(f"Skipping optional nested field {dest_key}")
                            continue
                    else:
                        # For regular fields, check if key exists
                        if mapping.source_key not in source:
                            logger.debug(f"Skipping optional field {dest_key}")
                            continue

                result[dest_key] = mapping.apply(source)
            except (KeyError, ValueError) as e:
                if mapping.optional:
                    logger.debug(f"Skipping optional field {dest_key}: {e}")
                    continue
                else:
                    logger.error(f"Error transforming {dest_key}: {e}")
                    raise

        return result

    def transform_batch(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform a batch of dictionaries.

        Args:
            sources: List of source dictionaries

        Returns:
            List of transformed dictionaries

        Raises:
            ValueError: If any item fails transformation
        """
        results = []
        failed = []

        for i, source in enumerate(sources):
            try:
                results.append(self.transform(source))
            except (KeyError, ValueError) as e:
                failed.append({"index": i, "error": str(e)})
                logger.warning(f"Failed to transform item {i}: {e}")

        if failed:
            logger.error(f"Failed to transform {len(failed)}/{len(sources)} items")

        return results

    def add_mapping(self, dest_key: str, mapping: FieldMapping):
        """Add or update a field mapping."""
        self.mappings[dest_key] = mapping
        logger.debug(f"Added mapping for {dest_key}")

    def remove_mapping(self, dest_key: str):
        """Remove a field mapping."""
        if dest_key in self.mappings:
            del self.mappings[dest_key]
            logger.debug(f"Removed mapping for {dest_key}")

    def get_field_names(self) -> List[str]:
        """Get list of all destination field names."""
        return list(self.mappings.keys())

    def validate_source(self, source: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate that source contains all required fields.

        Args:
            source: Source dictionary to validate

        Returns:
            Tuple of (is_valid, missing_fields_list)
        """
        missing = []

        for dest_key, mapping in self.mappings.items():
            if not mapping.optional and mapping.source_key not in source:
                missing.append(mapping.source_key)

        return len(missing) == 0, missing


__all__ = [
    "MetadataMapper",
    "FieldMapping",
]
