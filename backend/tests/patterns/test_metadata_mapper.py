"""
Comprehensive tests for MetadataMapper pattern.

Tests cover:
- Basic field mapping
- Field transformation functions
- Nested field extraction
- Optional fields with defaults
- Field validation
- Batch transformation
- Partial transformation (graceful degradation)
- Error handling
"""

import pytest
from datetime import datetime

from backend.integrations.patterns.metadata_mapper import (
    MetadataMapper,
    FieldMapping,
)


class TestFieldMapping:
    """Test suite for FieldMapping class."""

    def test_simple_passthrough(self):
        """Test simple field passthrough mapping."""
        mapping = FieldMapping(source_key="source_field")
        result = mapping.apply({"source_field": "value"})
        assert result == "value"

    def test_with_transform_function(self):
        """Test field mapping with transformation function."""
        mapping = FieldMapping(
            source_key="name",
            transform=str.upper
        )
        result = mapping.apply({"name": "john"})
        assert result == "JOHN"

    def test_with_default_value(self):
        """Test field mapping with default value."""
        mapping = FieldMapping(
            source_key="age",
            optional=True,
            default=0
        )
        result = mapping.apply({})
        assert result == 0

    def test_optional_field_missing(self):
        """Test optional field that's missing uses default."""
        mapping = FieldMapping(
            source_key="email",
            optional=True,
            default="no-email"
        )
        result = mapping.apply({})
        assert result == "no-email"

    def test_required_field_missing_raises_error(self):
        """Test required field missing raises KeyError."""
        mapping = FieldMapping(source_key="required_field")
        with pytest.raises(KeyError):
            mapping.apply({})

    def test_validation_success(self):
        """Test field validation passes."""
        mapping = FieldMapping(
            source_key="age",
            transform=int,
            validate=lambda x: x >= 0
        )
        result = mapping.apply({"age": "25"})
        assert result == 25

    def test_validation_failure(self):
        """Test field validation failure raises ValueError."""
        mapping = FieldMapping(
            source_key="age",
            transform=int,
            validate=lambda x: x >= 18
        )
        with pytest.raises(ValueError):
            mapping.apply({"age": "10"})

    def test_chained_transformations(self):
        """Test multiple transformations can be chained."""
        def transform_func(value):
            return str(value).upper().strip()

        mapping = FieldMapping(
            source_key="name",
            transform=transform_func
        )
        result = mapping.apply({"name": "  john  "})
        assert result == "JOHN"

    def test_nested_field_extraction(self):
        """Test nested field extraction with dot notation."""
        mapping = FieldMapping(
            source_key="author.name",
            nested=True
        )
        source = {
            "author": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }
        result = mapping.apply(source)
        assert result == "John Doe"

    def test_deeply_nested_field(self):
        """Test deeply nested field extraction."""
        mapping = FieldMapping(
            source_key="metadata.author.profile.name",
            nested=True
        )
        source = {
            "metadata": {
                "author": {
                    "profile": {
                        "name": "Jane Smith"
                    }
                }
            }
        }
        result = mapping.apply(source)
        assert result == "Jane Smith"

    def test_nested_field_missing(self):
        """Test nested field missing returns None."""
        mapping = FieldMapping(
            source_key="author.name",
            nested=True,
            optional=True,
            default="Unknown"
        )
        source = {"author": None}
        result = mapping.apply(source)
        assert result == "Unknown"

    def test_get_nested_static_method(self):
        """Test _get_nested static method directly."""
        source = {
            "level1": {
                "level2": {
                    "value": "found"
                }
            }
        }
        result = FieldMapping._get_nested(source, "level1.level2.value")
        assert result == "found"

    def test_get_nested_nonexistent_path(self):
        """Test _get_nested with nonexistent path."""
        source = {"level1": {"level2": "value"}}
        result = FieldMapping._get_nested(source, "level1.level3.value")
        assert result is None


class TestMetadataMapper:
    """Test suite for MetadataMapper class."""

    def test_simple_mapping(self):
        """Test simple field mapping."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "name": FieldMapping("item_name"),
        })
        source = {"item_id": "123", "item_name": "Test"}
        result = mapper.transform(source)
        assert result["id"] == "123"
        assert result["name"] == "Test"

    def test_mapping_with_transform(self):
        """Test mapping with transformation functions."""
        mapper = MetadataMapper({
            "title": FieldMapping("book_title", transform=str.upper),
            "author": FieldMapping("author_name", transform=str.title),
        })
        source = {
            "book_title": "the hobbit",
            "author_name": "j.r.r. tolkien"
        }
        result = mapper.transform(source)
        assert result["title"] == "THE HOBBIT"
        assert result["author"] == "J.R.R. Tolkien"

    def test_simple_function_mapping(self):
        """Test using simple function as mapping."""
        mapper = MetadataMapper({
            "double": lambda x: x * 2,
        })
        result = mapper.transform({"double": 5})
        assert result["double"] == 10

    def test_mapping_with_defaults(self):
        """Test mapping with default values for optional fields."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "description": FieldMapping("desc", optional=True, default="No description"),
        })
        source = {"item_id": "123"}
        result = mapper.transform(source)
        assert result["id"] == "123"
        assert result["description"] == "No description"

    def test_required_field_missing_raises(self):
        """Test missing required field raises error."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "name": FieldMapping("item_name"),
        })
        source = {"item_id": "123"}
        with pytest.raises(KeyError):
            mapper.transform(source)

    def test_partial_transform_skips_optional(self):
        """Test partial transform skips missing optional fields."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "description": FieldMapping("desc", optional=True),
        })
        source = {"item_id": "123"}
        result = mapper.transform_partial(source)
        assert "id" in result
        assert result["id"] == "123"
        # Since desc is missing and optional, should not be in result
        assert len(result) == 1

    def test_partial_transform_includes_required(self):
        """Test partial transform includes required fields."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "name": FieldMapping("item_name"),
        })
        source = {"item_id": "123", "item_name": "Test"}
        result = mapper.transform_partial(source)
        assert "id" in result
        assert "name" in result

    def test_nested_field_mapping(self):
        """Test mapping with nested field extraction."""
        mapper = MetadataMapper({
            "author_name": FieldMapping("author.name", nested=True),
            "author_email": FieldMapping("author.email", nested=True),
        })
        source = {
            "author": {
                "name": "John Doe",
                "email": "john@example.com"
            }
        }
        result = mapper.transform(source)
        assert result["author_name"] == "John Doe"
        assert result["author_email"] == "john@example.com"

    def test_batch_transform(self):
        """Test transforming multiple items."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "name": FieldMapping("item_name"),
        })
        sources = [
            {"item_id": "1", "item_name": "First"},
            {"item_id": "2", "item_name": "Second"},
            {"item_id": "3", "item_name": "Third"},
        ]
        results = mapper.transform_batch(sources)
        assert len(results) == 3
        assert results[0]["id"] == "1"
        assert results[1]["name"] == "Second"
        assert results[2]["id"] == "3"

    def test_batch_transform_with_failures(self):
        """Test batch transform handles individual failures gracefully."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "name": FieldMapping("item_name"),
        })
        sources = [
            {"item_id": "1", "item_name": "First"},
            {"item_id": "2"},  # Missing required field
            {"item_id": "3", "item_name": "Third"},
        ]
        results = mapper.transform_batch(sources)
        # Should only return successfully transformed items
        assert len(results) == 2

    def test_add_mapping_dynamically(self):
        """Test adding mappings dynamically."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
        })
        mapper.add_mapping("name", FieldMapping("item_name"))
        source = {"item_id": "123", "item_name": "Test"}
        result = mapper.transform(source)
        assert "id" in result
        assert "name" in result

    def test_remove_mapping(self):
        """Test removing mappings."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "name": FieldMapping("item_name"),
        })
        mapper.remove_mapping("name")
        source = {"item_id": "123", "item_name": "Test"}
        result = mapper.transform(source)
        assert "id" in result
        assert "name" not in result

    def test_get_field_names(self):
        """Test getting list of field names."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "name": FieldMapping("item_name"),
            "description": FieldMapping("desc"),
        })
        field_names = mapper.get_field_names()
        assert "id" in field_names
        assert "name" in field_names
        assert "description" in field_names
        assert len(field_names) == 3

    def test_validate_source_success(self):
        """Test source validation with all required fields."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "name": FieldMapping("item_name"),
        })
        source = {"item_id": "123", "item_name": "Test"}
        is_valid, missing = mapper.validate_source(source)
        assert is_valid is True
        assert missing == []

    def test_validate_source_missing_fields(self):
        """Test source validation detects missing fields."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "name": FieldMapping("item_name"),
        })
        source = {"item_id": "123"}
        is_valid, missing = mapper.validate_source(source)
        assert is_valid is False
        assert "item_name" in missing

    def test_validate_source_optional_fields(self):
        """Test source validation ignores optional fields."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "description": FieldMapping("desc", optional=True),
        })
        source = {"item_id": "123"}
        is_valid, missing = mapper.validate_source(source)
        assert is_valid is True
        assert missing == []

    def test_complex_transformation(self):
        """Test complex transformation with multiple features."""
        def parse_date(date_str):
            return datetime.fromisoformat(date_str)

        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "title": FieldMapping("book_title", transform=str.upper),
            "author": FieldMapping("author.name", nested=True),
            "published": FieldMapping("pub_date", transform=parse_date),
            "pages": FieldMapping("page_count", optional=True, default=0),
        })

        source = {
            "item_id": "123",
            "book_title": "the hobbit",
            "author": {"name": "J.R.R. Tolkien"},
            "pub_date": "1937-09-21T00:00:00",
        }

        result = mapper.transform(source)
        assert result["id"] == "123"
        assert result["title"] == "THE HOBBIT"
        assert result["author"] == "J.R.R. Tolkien"
        assert isinstance(result["published"], datetime)
        assert result["pages"] == 0

    def test_transformation_with_none_value(self):
        """Test transformation handles None values."""
        mapper = MetadataMapper({
            "name": FieldMapping("item_name", optional=True, default="Unknown"),
        })
        result = mapper.transform({"item_name": None})
        assert result["name"] == "Unknown"

    def test_large_batch_transformation(self):
        """Test batch transformation with large dataset."""
        mapper = MetadataMapper({
            "id": FieldMapping("item_id"),
            "value": FieldMapping("val", transform=int),
        })

        sources = [
            {"item_id": str(i), "val": str(i * 2)}
            for i in range(1000)
        ]

        results = mapper.transform_batch(sources)
        assert len(results) == 1000
        assert results[0]["id"] == "0"
        assert results[999]["value"] == 1998

    def test_identity_mapping(self):
        """Test mapping that doesn't transform values."""
        mapper = MetadataMapper({
            "id": "item_id",  # Simple string mapping
            "name": "item_name",
        })
        source = {"item_id": "123", "item_name": "Test"}
        result = mapper.transform(source)
        assert result["id"] == "123"
        assert result["name"] == "Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
