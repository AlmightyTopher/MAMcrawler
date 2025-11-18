"""
Unified markdown file writer for guide output.
Single implementation for consistent file formatting.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from mamcrawler.utils.sanitize import sanitize_filename
from mamcrawler.config import OutputConfig, DEFAULT_OUTPUT_CONFIG


class GuideMarkdownWriter:
    """
    Writes guide data to markdown files.

    Provides consistent formatting across all crawlers.
    """

    def __init__(self, output_dir: str = None, config: OutputConfig = None):
        """
        Initialize the writer.

        Args:
            output_dir: Output directory path
            config: Output configuration
        """
        self.config = config or DEFAULT_OUTPUT_CONFIG
        output_path = output_dir or self.config.guides_dir
        self.output_dir = Path(output_path)
        self.output_dir.mkdir(exist_ok=True)

    def save_guide(self, guide_data: Dict[str, Any]) -> Optional[Path]:
        """
        Save guide data to markdown file.

        Args:
            guide_data: Dictionary with guide information

        Returns:
            Path to saved file, or None if guide failed
        """
        if not guide_data.get('success'):
            return None

        filename = sanitize_filename(guide_data['title']) + ".md"
        filepath = self.output_dir / filename

        content = self._build_markdown(guide_data)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _build_markdown(self, data: Dict[str, Any]) -> str:
        """
        Build markdown content from guide data.

        Args:
            data: Guide data dictionary

        Returns:
            Formatted markdown string
        """
        lines = [
            f"# {data['title']}",
            "",
            f"**URL:** {data['url']}",
            f"**Category:** {data.get('category', 'General')}",
        ]

        # Optional metadata
        if data.get('description'):
            lines.append(f"**Description:** {data['description']}")
        if data.get('author'):
            lines.append(f"**Author:** {data['author']}")
        if data.get('last_updated'):
            lines.append(f"**Last Updated:** {data['last_updated']}")
        if data.get('tags'):
            lines.append(f"**Tags:** {data['tags']}")

        # Crawl metadata
        crawled_at = data.get('crawled_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        lines.append(f"**Crawled:** {crawled_at}")

        if data.get('attempt'):
            lines.append(f"**Attempts:** {data['attempt']}")

        lines.extend(["", "---", ""])

        # Related links section
        sub_links = self._extract_links(data)
        if sub_links:
            lines.append("## Related Guides")
            lines.append("")
            for link in sub_links[:20]:  # Limit to 20 links
                if isinstance(link, dict):
                    lines.append(f"- [{link.get('title', 'Link')}]({link.get('url', '#')})")
                else:
                    lines.append(f"- {link}")
            lines.extend(["", "---", ""])

        # Main content
        lines.extend([
            "## Content",
            "",
            data.get('content', 'No content extracted')
        ])

        return "\n".join(lines)

    def _extract_links(self, data: Dict[str, Any]) -> List:
        """Extract links from various data formats."""
        # Try sub_links first (comprehensive crawler format)
        if data.get('sub_links'):
            return data['sub_links']

        # Try links.internal (stealth crawler format)
        if data.get('links') and isinstance(data['links'], dict):
            internal = data['links'].get('internal', [])
            # Filter to only guide links
            return [link for link in internal if '/guides/' in str(link)]

        return []

    def save_index(self, guides: List[Dict[str, Any]], title: str = "Guides Index") -> Path:
        """
        Save an index file listing all guides.

        Args:
            guides: List of guide metadata dictionaries
            title: Index page title

        Returns:
            Path to index file
        """
        filepath = self.output_dir / "00_GUIDES_INDEX.md"

        lines = [
            f"# {title}",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Guides:** {len(guides)}",
            "",
            "---",
            "",
        ]

        # Organize by category
        categories = {}
        for guide in guides:
            cat = guide.get('category', 'General')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(guide)

        lines.append("## Guides by Category")
        lines.append("")

        for category, cat_guides in sorted(categories.items()):
            lines.append(f"### {category} ({len(cat_guides)} guides)")
            lines.append("")
            for guide in sorted(cat_guides, key=lambda x: x.get('title', '')):
                filename = sanitize_filename(guide.get('title', 'Untitled'))
                lines.append(f"- [{guide.get('title', 'Untitled')}]({filename}.md)")
            lines.append("")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        return filepath

    def save_summary(self, guides: List[Dict[str, Any]],
                     failed: List[Dict[str, Any]] = None) -> Path:
        """
        Save a crawl summary report.

        Args:
            guides: List of successfully crawled guides
            failed: List of failed guides

        Returns:
            Path to summary file
        """
        filepath = self.output_dir / "CRAWL_SUMMARY.md"
        failed = failed or []

        lines = [
            "# Crawl Summary",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Successful:** {len(guides)}",
            f"**Failed:** {len(failed)}",
            f"**Output Directory:** `{self.output_dir.absolute()}`",
            "",
            "---",
            "",
        ]

        if failed:
            lines.append("## Failed Guides")
            lines.append("")
            for guide in failed:
                lines.append(f"- {guide.get('title', 'Unknown')}: {guide.get('error', 'Unknown error')}")
            lines.extend(["", "---", ""])

        lines.append("## Successfully Crawled")
        lines.append("")
        for guide in sorted(guides, key=lambda x: x.get('title', '')):
            filename = sanitize_filename(guide.get('title', 'Untitled'))
            lines.append(f"- [{guide.get('title', 'Untitled')}]({filename}.md)")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        return filepath
