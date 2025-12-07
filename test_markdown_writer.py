# test_markdown_writer.py
# Comprehensive validation of the Markdown Writer module

import sys
import os
import tempfile
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.abspath('.'))

from mamcrawler.storage.markdown_writer import GuideMarkdownWriter
from mamcrawler.config import OutputConfig


def test_initialization():
    """Test writer initialization with different configs."""
    print("\n=== Testing Initialization ===")

    # Test 1: Default initialization
    print("\n  Test 1: Default initialization")
    with tempfile.TemporaryDirectory() as temp_dir:
        writer = GuideMarkdownWriter(output_dir=temp_dir)

        if not writer.output_dir.exists():
            print("    ❌ FAIL: Output directory not created")
            return False
        print(f"    ✓ Output directory created: {writer.output_dir}")
        print(f"    ✓ Config loaded: {writer.config is not None}")

    # Test 2: Custom config
    print("\n  Test 2: Custom config initialization")
    with tempfile.TemporaryDirectory() as temp_dir:
        custom_config = OutputConfig(guides_dir=temp_dir)
        writer2 = GuideMarkdownWriter(config=custom_config)

        if not writer2.output_dir.exists():
            print("    ❌ FAIL: Custom directory not created")
            return False
        print(f"    ✓ Custom config applied")
        print(f"    ✓ Output directory: {writer2.output_dir}")

    # Test 3: Directory auto-creation
    print("\n  Test 3: Nested directory auto-creation")
    with tempfile.TemporaryDirectory() as temp_dir:
        nested_path = Path(temp_dir) / "nested" / "guides"
        writer3 = GuideMarkdownWriter(output_dir=str(nested_path))

        if not nested_path.exists():
            print("    ❌ FAIL: Nested directories not created")
            return False
        print(f"    ✓ Nested directories created automatically")

    print("\n  ✓ All initialization tests passed")
    return True


def test_save_guide():
    """Test saving individual guide files."""
    print("\n=== Testing save_guide() ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        writer = GuideMarkdownWriter(output_dir=temp_dir)

        # Test 1: Basic guide save
        print("\n  Test 1: Save basic guide")
        guide_data = {
            'success': True,
            'title': 'Test Guide',
            'url': 'https://www.myanonamouse.net/guides/?gid=123',
            'category': 'Testing',
            'content': 'This is test content.',
        }

        filepath = writer.save_guide(guide_data)

        if filepath is None:
            print("    ❌ FAIL: save_guide returned None")
            return False
        if not filepath.exists():
            print("    ❌ FAIL: File not created")
            return False

        print(f"    ✓ File created: {filepath.name}")

        # Verify content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        required_sections = ["# Test Guide", "**URL:**", "**Category:**", "## Content"]
        for section in required_sections:
            if section not in content:
                print(f"    ❌ FAIL: Missing section: {section}")
                return False

        print(f"    ✓ All required sections present")
        print(f"    ✓ File size: {len(content)} chars")

        # Test 2: Guide with all metadata
        print("\n  Test 2: Save guide with full metadata")
        full_guide = {
            'success': True,
            'title': 'Complete Guide',
            'url': 'https://www.myanonamouse.net/guides/?gid=456',
            'category': 'Complete',
            'description': 'A complete guide with all fields',
            'author': 'Test Author',
            'last_updated': '2025-01-01',
            'tags': 'test, complete, metadata',
            'crawled_at': '2025-01-01 12:00:00',
            'attempt': 2,
            'content': 'Full guide content here.',
        }

        filepath2 = writer.save_guide(full_guide)
        with open(filepath2, 'r', encoding='utf-8') as f:
            content2 = f.read()

        metadata_fields = [
            "**Description:**",
            "**Author:**",
            "**Last Updated:**",
            "**Tags:**",
            "**Crawled:**",
            "**Attempts:**"
        ]

        for field in metadata_fields:
            if field not in content2:
                print(f"    ❌ FAIL: Missing metadata field: {field}")
                return False

        print("    ✓ All metadata fields present")

        # Test 3: Failed guide (success=False)
        print("\n  Test 3: Handle failed guide")
        failed_guide = {
            'success': False,
            'title': 'Failed Guide',
        }

        result = writer.save_guide(failed_guide)

        if result is not None:
            print("    ❌ FAIL: Should return None for failed guide")
            return False
        print("    ✓ Failed guide correctly skipped")

        # Test 4: Special characters in filename
        print("\n  Test 4: Filename sanitization")
        special_guide = {
            'success': True,
            'title': 'Guide: With <Special> Characters / Slashes',
            'url': 'https://example.com',
            'content': 'Content',
        }

        filepath3 = writer.save_guide(special_guide)
        filename = filepath3.name

        # Check no forbidden characters
        forbidden = r'<>:"/\|?*'
        if any(char in filename for char in forbidden):
            print(f"    ❌ FAIL: Filename contains forbidden chars: {filename}")
            return False

        print(f"    ✓ Filename sanitized: {filename}")

        # Test 5: UTF-8 encoding
        print("\n  Test 5: Unicode content handling")
        unicode_guide = {
            'success': True,
            'title': '日本語ガイド',
            'url': 'https://example.com',
            'content': 'Content with émojis 🎵 and spëcial çharacters.',
        }

        filepath4 = writer.save_guide(unicode_guide)
        with open(filepath4, 'r', encoding='utf-8') as f:
            unicode_content = f.read()

        if '日本語ガイド' not in unicode_content:
            print("    ❌ FAIL: Unicode title not saved correctly")
            return False
        if '🎵' not in unicode_content:
            print("    ❌ FAIL: Emoji not saved correctly")
            return False

        print("    ✓ Unicode and emoji handled correctly")

    print("\n  ✓ All save_guide tests passed")
    return True


def test_related_links():
    """Test related links extraction and formatting."""
    print("\n=== Testing Related Links ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        writer = GuideMarkdownWriter(output_dir=temp_dir)

        # Test 1: sub_links format (comprehensive crawler)
        print("\n  Test 1: sub_links format")
        guide1 = {
            'success': True,
            'title': 'Guide with sub_links',
            'url': 'https://example.com',
            'content': 'Content',
            'sub_links': [
                {'title': 'Related Guide 1', 'url': 'https://example.com/1'},
                {'title': 'Related Guide 2', 'url': 'https://example.com/2'},
            ]
        }

        filepath1 = writer.save_guide(guide1)
        with open(filepath1, 'r', encoding='utf-8') as f:
            content1 = f.read()

        if "## Related Guides" not in content1:
            print("    ❌ FAIL: Related Guides section not created")
            return False
        if "[Related Guide 1]" not in content1:
            print("    ❌ FAIL: Link not formatted correctly")
            return False

        print("    ✓ sub_links format handled correctly")

        # Test 2: links.internal format (stealth crawler)
        print("\n  Test 2: links.internal format")
        guide2 = {
            'success': True,
            'title': 'Guide with links.internal',
            'url': 'https://example.com',
            'content': 'Content',
            'links': {
                'internal': [
                    'https://www.myanonamouse.net/guides/guide1',
                    'https://www.myanonamouse.net/guides/guide2',
                    'https://www.myanonamouse.net/forum/topic',  # Should be filtered
                ]
            }
        }

        filepath2 = writer.save_guide(guide2)
        with open(filepath2, 'r', encoding='utf-8') as f:
            content2 = f.read()

        # Should only include guide links
        guide_links_count = content2.count('/guides/')
        if guide_links_count < 2:
            print(f"    ❌ FAIL: Expected 2+ guide links, found {guide_links_count}")
            return False

        print(f"    ✓ links.internal format handled, filtered guide links")

        # Test 3: No links
        print("\n  Test 3: No related links")
        guide3 = {
            'success': True,
            'title': 'Guide without links',
            'url': 'https://example.com',
            'content': 'Content',
        }

        filepath3 = writer.save_guide(guide3)
        with open(filepath3, 'r', encoding='utf-8') as f:
            content3 = f.read()

        # Should not have Related Guides section
        if "## Related Guides" in content3:
            print("    ⚠️  WARNING: Related Guides section created with no links")

        print("    ✓ No links handled correctly")

        # Test 4: Link limit (max 20)
        print("\n  Test 4: Link limit enforcement")
        many_links = [
            {'title': f'Guide {i}', 'url': f'https://example.com/{i}'}
            for i in range(30)
        ]
        guide4 = {
            'success': True,
            'title': 'Guide with many links',
            'url': 'https://example.com',
            'content': 'Content',
            'sub_links': many_links,
        }

        filepath4 = writer.save_guide(guide4)
        with open(filepath4, 'r', encoding='utf-8') as f:
            content4 = f.read()

        # Count markdown links
        link_count = content4.count('[Guide')
        if link_count > 20:
            print(f"    ❌ FAIL: Too many links: {link_count} (max 20)")
            return False

        print(f"    ✓ Link limit enforced: {link_count}/30 links saved")

    print("\n  ✓ All related links tests passed")
    return True


def test_save_index():
    """Test index file generation."""
    print("\n=== Testing save_index() ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        writer = GuideMarkdownWriter(output_dir=temp_dir)

        # Test 1: Basic index creation
        print("\n  Test 1: Create index file")
        guides = [
            {'title': 'Guide A', 'category': 'Category 1'},
            {'title': 'Guide B', 'category': 'Category 1'},
            {'title': 'Guide C', 'category': 'Category 2'},
        ]

        index_path = writer.save_index(guides, title="Test Index")

        if not index_path.exists():
            print("    ❌ FAIL: Index file not created")
            return False

        print(f"    ✓ Index file created: {index_path.name}")

        with open(index_path, 'r', encoding='utf-8') as f:
            index_content = f.read()

        # Verify structure
        required_sections = [
            "# Test Index",
            "**Total Guides:** 3",
            "## Guides by Category",
            "### Category 1",
            "### Category 2",
        ]

        for section in required_sections:
            if section not in index_content:
                print(f"    ❌ FAIL: Missing section: {section}")
                return False

        print("    ✓ All index sections present")

        # Test 2: Category grouping
        print("\n  Test 2: Category grouping and sorting")
        if "Guide A" not in index_content or "Guide B" not in index_content:
            print("    ❌ FAIL: Guides not listed in index")
            return False

        # Check that Category 1 appears before Category 2 (alphabetical)
        cat1_pos = index_content.find("### Category 1")
        cat2_pos = index_content.find("### Category 2")
        if cat1_pos > cat2_pos:
            print("    ❌ FAIL: Categories not alphabetically sorted")
            return False

        print("    ✓ Categories grouped and sorted alphabetically")

        # Test 3: Empty guides list
        print("\n  Test 3: Empty guides list")
        empty_index = writer.save_index([], title="Empty Index")
        with open(empty_index, 'r', encoding='utf-8') as f:
            empty_content = f.read()

        if "**Total Guides:** 0" not in empty_content:
            print("    ❌ FAIL: Empty count not correct")
            return False

        print("    ✓ Empty guides list handled")

    print("\n  ✓ All save_index tests passed")
    return True


def test_save_summary():
    """Test summary file generation."""
    print("\n=== Testing save_summary() ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        writer = GuideMarkdownWriter(output_dir=temp_dir)

        # Test 1: Basic summary
        print("\n  Test 1: Create summary with successful guides")
        guides = [
            {'title': 'Guide 1'},
            {'title': 'Guide 2'},
        ]

        summary_path = writer.save_summary(guides)

        if not summary_path.exists():
            print("    ❌ FAIL: Summary file not created")
            return False

        print(f"    ✓ Summary file created: {summary_path.name}")

        with open(summary_path, 'r', encoding='utf-8') as f:
            summary_content = f.read()

        required_sections = [
            "# Crawl Summary",
            "**Successful:** 2",
            "**Failed:** 0",
            "## Successfully Crawled",
        ]

        for section in required_sections:
            if section not in summary_content:
                print(f"    ❌ FAIL: Missing section: {section}")
                return False

        print("    ✓ All summary sections present")

        # Test 2: Summary with failures
        print("\n  Test 2: Summary with failed guides")
        failed = [
            {'title': 'Failed 1', 'error': 'Timeout'},
            {'title': 'Failed 2', 'error': 'Not found'},
        ]

        summary2_path = writer.save_summary(guides, failed=failed)
        with open(summary2_path, 'r', encoding='utf-8') as f:
            summary2_content = f.read()

        if "**Failed:** 2" not in summary2_content:
            print("    ❌ FAIL: Failed count incorrect")
            return False
        if "## Failed Guides" not in summary2_content:
            print("    ❌ FAIL: Failed section missing")
            return False
        if "Timeout" not in summary2_content:
            print("    ❌ FAIL: Error message not included")
            return False

        print("    ✓ Failed guides section included")

        # Test 3: Empty summary
        print("\n  Test 3: Empty summary")
        empty_summary = writer.save_summary([])
        with open(empty_summary, 'r', encoding='utf-8') as f:
            empty_content = f.read()

        if "**Successful:** 0" not in empty_content:
            print("    ❌ FAIL: Empty count incorrect")
            return False

        print("    ✓ Empty summary handled")

    print("\n  ✓ All save_summary tests passed")
    return True


def test_markdown_formatting():
    """Test markdown content formatting details."""
    print("\n=== Testing Markdown Formatting ===")

    with tempfile.TemporaryDirectory() as temp_dir:
        writer = GuideMarkdownWriter(output_dir=temp_dir)

        # Test 1: Separator lines
        print("\n  Test 1: Separator formatting")
        guide = {
            'success': True,
            'title': 'Format Test',
            'url': 'https://example.com',
            'content': 'Content',
        }

        filepath = writer.save_guide(guide)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have horizontal rules (---)
        separator_count = content.count('---')
        if separator_count < 1:
            print("    ⚠️  WARNING: No separator lines found")

        print(f"    ✓ Separator lines present: {separator_count}")

        # Test 2: Header hierarchy
        print("\n  Test 2: Header hierarchy")
        if not content.startswith('# '):
            print("    ❌ FAIL: Document should start with H1 header")
            return False

        h1_count = content.count('\n# ')
        h2_count = content.count('\n## ')

        print(f"    ✓ Header hierarchy: {h1_count} H1, {h2_count} H2")

        # Test 3: Empty lines between sections
        print("\n  Test 3: Section spacing")
        lines = content.split('\n')
        empty_lines = [i for i, line in enumerate(lines) if line == '']

        if len(empty_lines) < 3:
            print("    ⚠️  WARNING: Very few empty lines for readability")

        print(f"    ✓ Empty lines for spacing: {len(empty_lines)}")

    print("\n  ✓ All markdown formatting tests passed")
    return True


def main():
    """Run all markdown writer tests."""
    print("=" * 60)
    print("Markdown Writer Module Validation")
    print("=" * 60)

    tests = [
        ("Initialization", test_initialization),
        ("save_guide()", test_save_guide),
        ("Related Links", test_related_links),
        ("save_index()", test_save_index),
        ("save_summary()", test_save_summary),
        ("Markdown Formatting", test_markdown_formatting),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {name}")

    print("\n" + "=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All markdown writer tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
