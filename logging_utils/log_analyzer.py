"""
Log analysis utilities for the unified logging system.

Provides tools for analyzing log files, extracting insights, and generating reports.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import gzip
import statistics


class LogAnalyzer:
    """Analyzes log files and extracts insights"""

    def __init__(self, log_directory: str = "logs"):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(parents=True, exist_ok=True)

    def analyze_log_files(self, days: int = 7) -> Dict[str, Any]:
        """Analyze recent log files and return comprehensive statistics"""
        cutoff_date = datetime.now() - timedelta(days=days)
        analysis = {
            'period': f"{days} days",
            'files_analyzed': [],
            'summary': {},
            'errors': {},
            'performance': {},
            'security': {},
            'trends': {}
        }

        # Find log files
        log_files = []
        for pattern in ["*.log", "*.log.*"]:
            log_files.extend(self.log_directory.glob(pattern))

        # Filter by date and analyze
        for log_file in log_files:
            if self._is_recent_file(log_file, cutoff_date):
                file_analysis = self._analyze_single_file(log_file)
                analysis['files_analyzed'].append({
                    'name': log_file.name,
                    'size_mb': log_file.stat().st_size / (1024 * 1024),
                    'analysis': file_analysis
                })

        # Aggregate results
        analysis['summary'] = self._aggregate_summary(analysis['files_analyzed'])
        analysis['errors'] = self._aggregate_errors(analysis['files_analyzed'])
        analysis['performance'] = self._aggregate_performance(analysis['files_analyzed'])
        analysis['security'] = self._aggregate_security(analysis['files_analyzed'])
        analysis['trends'] = self._analyze_trends(analysis['files_analyzed'])

        return analysis

    def _is_recent_file(self, file_path: Path, cutoff_date: datetime) -> bool:
        """Check if file was modified recently"""
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            return mtime >= cutoff_date
        except OSError:
            return False

    def _analyze_single_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single log file"""
        analysis = {
            'total_lines': 0,
            'error_count': 0,
            'warning_count': 0,
            'info_count': 0,
            'debug_count': 0,
            'security_events': 0,
            'performance_metrics': [],
            'errors_by_type': Counter(),
            'top_modules': Counter(),
            'hourly_distribution': defaultdict(int),
            'response_times': []
        }

        try:
            with self._open_log_file(file_path) as f:
                for line in f:
                    analysis['total_lines'] += 1
                    line_data = self._parse_log_line(line.strip())
                    if line_data:
                        self._update_analysis(analysis, line_data)

        except Exception as e:
            analysis['error'] = f"Failed to analyze {file_path.name}: {e}"

        return analysis

    def _open_log_file(self, file_path: Path):
        """Open log file, handling compression"""
        if file_path.suffix == '.gz':
            return gzip.open(file_path, 'rt', encoding='utf-8')
        else:
            return open(file_path, 'r', encoding='utf-8')

    def _parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single log line"""
        # Try JSON format first
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass

        # Try structured format
        # 2024-01-01 12:00:00 | INFO | module | message
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (\w+) \| ([^|]+) \| (.+)'
        match = re.match(pattern, line)
        if match:
            timestamp, level, module, message = match.groups()
            return {
                'timestamp': timestamp,
                'level': level,
                'logger': module.strip(),
                'message': message.strip()
            }

        return None

    def _update_analysis(self, analysis: Dict, line_data: Dict):
        """Update analysis with parsed line data"""
        # Count by level
        level = line_data.get('level', '').upper()
        if level == 'ERROR':
            analysis['error_count'] += 1
        elif level == 'WARNING':
            analysis['warning_count'] += 1
        elif level == 'INFO':
            analysis['info_count'] += 1
        elif level == 'DEBUG':
            analysis['debug_count'] += 1
        elif level == 'SECURITY':
            analysis['security_events'] += 1

        # Track modules
        module = line_data.get('logger', 'unknown')
        analysis['top_modules'][module] += 1

        # Hourly distribution
        if 'timestamp' in line_data:
            try:
                dt = datetime.fromisoformat(line_data['timestamp'].replace('Z', '+00:00'))
                analysis['hourly_distribution'][dt.hour] += 1
            except:
                pass

        # Performance metrics
        if 'performance' in line_data:
            perf_data = line_data['performance']
            if 'duration_ms' in perf_data:
                analysis['response_times'].append(perf_data['duration_ms'])

        # Error categorization
        if level == 'ERROR' and 'message' in line_data:
            error_type = self._categorize_error(line_data['message'])
            analysis['errors_by_type'][error_type] += 1

    def _categorize_error(self, message: str) -> str:
        """Categorize error messages"""
        message_lower = message.lower()

        if 'connection' in message_lower or 'timeout' in message_lower:
            return 'Connection/Network'
        elif 'permission' in message_lower or 'access' in message_lower:
            return 'Permission/Access'
        elif 'database' in message_lower or 'sql' in message_lower:
            return 'Database'
        elif 'validation' in message_lower or 'invalid' in message_lower:
            return 'Validation'
        elif 'memory' in message_lower or 'out of memory' in message_lower:
            return 'Memory'
        else:
            return 'Other'

    def _aggregate_summary(self, file_analyses: List[Dict]) -> Dict[str, Any]:
        """Aggregate summary statistics"""
        total_lines = sum(f['analysis']['total_lines'] for f in file_analyses)
        total_errors = sum(f['analysis']['error_count'] for f in file_analyses)
        total_warnings = sum(f['analysis']['warning_count'] for f in file_analyses)

        return {
            'total_log_lines': total_lines,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'error_rate': total_errors / total_lines if total_lines > 0 else 0,
            'files_analyzed': len(file_analyses)
        }

    def _aggregate_errors(self, file_analyses: List[Dict]) -> Dict[str, Any]:
        """Aggregate error statistics"""
        all_errors = Counter()
        for f in file_analyses:
            all_errors.update(f['analysis']['errors_by_type'])

        return dict(all_errors.most_common(10))

    def _aggregate_performance(self, file_analyses: List[Dict]) -> Dict[str, Any]:
        """Aggregate performance statistics"""
        all_response_times = []
        for f in file_analyses:
            all_response_times.extend(f['analysis']['response_times'])

        if all_response_times:
            return {
                'avg_response_time_ms': statistics.mean(all_response_times),
                'median_response_time_ms': statistics.median(all_response_times),
                '95p_response_time_ms': statistics.quantiles(all_response_times, n=20)[18],  # 95th percentile
                'max_response_time_ms': max(all_response_times),
                'total_measurements': len(all_response_times)
            }
        else:
            return {'message': 'No performance metrics found'}

    def _aggregate_security(self, file_analyses: List[Dict]) -> Dict[str, Any]:
        """Aggregate security event statistics"""
        total_security_events = sum(f['analysis']['security_events'] for f in file_analyses)

        return {
            'total_security_events': total_security_events,
            'security_events_per_file': total_security_events / len(file_analyses) if file_analyses else 0
        }

    def _analyze_trends(self, file_analyses: List[Dict]) -> Dict[str, Any]:
        """Analyze trends in log data"""
        trends = {
            'error_trend': 'stable',
            'activity_trend': 'stable'
        }

        # Simple trend analysis based on file ordering
        if len(file_analyses) >= 2:
            mid = len(file_analyses) // 2
            first_half = file_analyses[:mid]
            second_half = file_analyses[mid:]

            first_errors = sum(f['analysis']['error_count'] for f in first_half)
            second_errors = sum(f['analysis']['error_count'] for f in second_half)

            if second_errors > first_errors * 1.5:
                trends['error_trend'] = 'increasing'
            elif second_errors < first_errors * 0.5:
                trends['error_trend'] = 'decreasing'

        return trends

    def generate_report(self, analysis: Dict[str, Any], output_file: str = None) -> str:
        """Generate a human-readable report from analysis"""
        report = []
        report.append("=" * 80)
        report.append("LOG ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Analysis Period: {analysis['period']}")
        report.append(f"Files Analyzed: {analysis['summary']['files_analyzed']}")
        report.append("")

        # Summary
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Log Lines: {analysis['summary']['total_log_lines']:,}")
        report.append(f"Total Errors: {analysis['summary']['total_errors']:,}")
        report.append(f"Total Warnings: {analysis['summary']['total_warnings']:,}")
        report.append(f"Error Rate: {analysis['summary']['error_rate']:.2%}")
        report.append("")

        # Errors
        if analysis['errors']:
            report.append("TOP ERROR TYPES")
            report.append("-" * 40)
            for error_type, count in analysis['errors'].items():
                report.append(f"{error_type}: {count}")
            report.append("")

        # Performance
        if isinstance(analysis['performance'], dict) and 'avg_response_time_ms' in analysis['performance']:
            report.append("PERFORMANCE METRICS")
            report.append("-" * 40)
            perf = analysis['performance']
            report.append(f"Average Response Time: {perf['avg_response_time_ms']:.2f}ms")
            report.append(f"Median Response Time: {perf['median_response_time_ms']:.2f}ms")
            report.append(f"95th Percentile: {perf['95p_response_time_ms']:.2f}ms")
            report.append(f"Max Response Time: {perf['max_response_time_ms']:.2f}ms")
            report.append("")

        # Security
        report.append("SECURITY EVENTS")
        report.append("-" * 40)
        report.append(f"Total Security Events: {analysis['security']['total_security_events']}")
        report.append("")

        # Trends
        report.append("TRENDS")
        report.append("-" * 40)
        report.append(f"Error Trend: {analysis['trends']['error_trend']}")
        report.append(f"Activity Trend: {analysis['trends']['activity_trend']}")
        report.append("")

        report.append("=" * 80)

        final_report = "\n".join(report)

        if output_file:
            Path(output_file).write_text(final_report, encoding='utf-8')

        return final_report