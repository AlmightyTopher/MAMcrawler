"""
Log export utilities for the unified logging system.

Provides tools for exporting log data to various formats and destinations.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
import csv
import sqlite3
from datetime import datetime


class LogExporter:
    """Export log data to various formats"""

    def __init__(self, logs: List[Dict[str, Any]]):
        self.logs = logs

    def to_json(self, output_file: str, pretty: bool = True) -> str:
        """Export logs to JSON format"""
        indent = 2 if pretty else None
        json_data = json.dumps(self.logs, indent=indent, default=str)

        if output_file:
            Path(output_file).write_text(json_data, encoding='utf-8')

        return json_data

    def to_csv(self, output_file: str, fields: List[str] = None) -> str:
        """Export logs to CSV format"""
        if not self.logs:
            return ""

        # Determine fields
        if not fields:
            fields = []
            for log in self.logs[:10]:  # Sample first 10 logs
                for key in log.keys():
                    if key not in fields:
                        fields.append(key)

        # Write CSV
        import io
        output = io.StringIO()

        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()

        for log in self.logs:
            row = {}
            for field in fields:
                value = log.get(field, '')
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                row[field] = str(value)
            writer.writerow(row)

        csv_data = output.getvalue()

        if output_file:
            Path(output_file).write_text(csv_data, encoding='utf-8')

        return csv_data

    def to_database(self, db_path: str, table_name: str = "logs") -> int:
        """Export logs to SQLite database"""
        conn = sqlite3.connect(db_path)

        # Create table
        columns = []
        for log in self.logs[:5]:  # Sample to determine schema
            for key, value in log.items():
                col_type = "TEXT"
                if isinstance(value, (int, float)):
                    col_type = "REAL"
                elif isinstance(value, bool):
                    col_type = "INTEGER"
                columns.append(f"{key} {col_type}")

        columns_sql = ", ".join(set(columns))  # Remove duplicates
        conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})")

        # Insert data
        inserted_count = 0
        for log in self.logs:
            columns = list(log.keys())
            placeholders = ", ".join(["?" for _ in columns])
            values = []
            for col in columns:
                value = log.get(col, '')
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                values.append(value)

            try:
                conn.execute(f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})", values)
                inserted_count += 1
            except Exception as e:
                print(f"Failed to insert log: {e}")

        conn.commit()
        conn.close()

        return inserted_count

    def to_markdown(self, output_file: str) -> str:
        """Export logs to Markdown format"""
        if not self.logs:
            return "# No logs to export\n"

        lines = ["# Log Export\n", f"Generated: {datetime.now().isoformat()}\n", f"Total logs: {len(self.logs)}\n"]

        # Summary table
        lines.extend([
            "## Summary\n",
            "| Level | Count |",
            "|-------|-------|"
        ])

        level_counts = {}
        for log in self.logs:
            level = log.get('level', 'UNKNOWN')
            level_counts[level] = level_counts.get(level, 0) + 1

        for level, count in sorted(level_counts.items()):
            lines.append(f"| {level} | {count} |")

        lines.append("")

        # Recent logs
        lines.extend(["## Recent Logs\n"])
        for log in self.logs[-20:]:  # Last 20 logs
            timestamp = log.get('timestamp', 'Unknown')
            level = log.get('level', 'UNKNOWN')
            message = log.get('message', 'No message')[:100]  # Truncate long messages
            lines.append(f"- **{level}** [{timestamp}]: {message}")

        markdown_content = "\n".join(lines)

        if output_file:
            Path(output_file).write_text(markdown_content, encoding='utf-8')

        return markdown_content