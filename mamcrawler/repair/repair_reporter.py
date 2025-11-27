"""
Repair Reporter Module
Generates comprehensive reports on repair operations and replacement results.

Report Types:
1. Evaluation Report - Quality comparison results
2. Execution Report - Replacement operation results
3. Batch Report - Multiple replacement candidate evaluations
4. Summary Report - Overall repair statistics
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class RepairReporter:
    """Generates reports for repair operations"""

    def __init__(self):
        """Initialize repair reporter"""
        self.report_timestamp = datetime.now()

    def generate_evaluation_report(
        self,
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a report for a replacement evaluation.

        Args:
            evaluation: Result from RepairOrchestrator.evaluate_replacement()

        Returns:
            dict: Formatted evaluation report
        """
        comparison = evaluation.get('quality_comparison', {})
        original_props = comparison.get('original', {}) or {}
        replacement_props = comparison.get('replacement', {}) or {}
        comparison_details = comparison.get('comparison', {})

        report = {
            'report_type': 'EVALUATION',
            'timestamp': datetime.now().isoformat(),
            'audiobook': evaluation.get('audiobook_title', 'Unknown'),
            'author': evaluation.get('author', 'Unknown'),
            'decision': evaluation.get('decision', 'UNKNOWN'),
            'reason': evaluation.get('reason', 'No reason provided'),
            'original_properties': {
                'codec': original_props.get('codec', 'Unknown') if original_props else 'Unknown',
                'bitrate_kbps': original_props.get('bitrate_kbps', 'Unknown') if original_props else 'Unknown',
                'duration_seconds': original_props.get('duration_seconds', 'Unknown') if original_props else 'Unknown',
                'sample_rate': original_props.get('sample_rate', 'Unknown') if original_props else 'Unknown',
                'channels': original_props.get('channels', 'Unknown') if original_props else 'Unknown',
                'file_size_bytes': original_props.get('file_size_bytes', 'Unknown') if original_props else 'Unknown'
            },
            'replacement_properties': {
                'codec': replacement_props.get('codec', 'Unknown') if replacement_props else 'Unknown',
                'bitrate_kbps': replacement_props.get('bitrate_kbps', 'Unknown') if replacement_props else 'Unknown',
                'duration_seconds': replacement_props.get('duration_seconds', 'Unknown') if replacement_props else 'Unknown',
                'sample_rate': replacement_props.get('sample_rate', 'Unknown') if replacement_props else 'Unknown',
                'channels': replacement_props.get('channels', 'Unknown') if replacement_props else 'Unknown',
                'file_size_bytes': replacement_props.get('file_size_bytes', 'Unknown') if replacement_props else 'Unknown'
            },
            'comparison_results': {
                'codec_match': comparison_details.get('codec_match', False),
                'bitrate_acceptable': comparison_details.get('bitrate_acceptable', False),
                'duration_match': comparison_details.get('duration_match', False),
                'issues': comparison_details.get('issues', [])
            }
        }

        return report

    def generate_execution_report(
        self,
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a report for a replacement execution.

        Args:
            execution_result: Result from RepairOrchestrator.execute_replacement()

        Returns:
            dict: Formatted execution report
        """
        report = {
            'report_type': 'EXECUTION',
            'timestamp': datetime.now().isoformat(),
            'success': execution_result.get('success', False),
            'message': execution_result.get('message', 'No message'),
            'original_file': execution_result.get('original_file', 'Unknown'),
            'replacement_file': execution_result.get('replacement_file', 'Unknown'),
            'backup_file': execution_result.get('backup_file', 'None'),
            'error': execution_result.get('error', None)
        }

        return report

    def generate_batch_report(
        self,
        batch_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a report for batch replacement evaluations.

        Args:
            batch_result: Result from RepairOrchestrator.batch_evaluate_replacements()

        Returns:
            dict: Formatted batch report
        """
        evaluations = batch_result.get('evaluations', [])
        acceptable_count = len(batch_result.get('acceptable_candidates', []))
        total_count = batch_result.get('candidates_evaluated', 0)

        # Summarize acceptability by candidate
        candidate_summaries = []
        for eval_item in evaluations:
            candidate_summaries.append({
                'candidate': eval_item['candidate'],
                'acceptable': eval_item['evaluation']['is_acceptable'],
                'decision': eval_item['evaluation']['decision'],
                'reason': eval_item['evaluation']['reason']
            })

        report = {
            'report_type': 'BATCH_EVALUATION',
            'timestamp': datetime.now().isoformat(),
            'audiobook': batch_result.get('audiobook_title', 'Unknown'),
            'author': batch_result.get('author', 'Unknown'),
            'candidates_submitted': batch_result.get('candidates_submitted', 0),
            'candidates_evaluated': total_count,
            'candidates_acceptable': acceptable_count,
            'acceptable_percentage': (acceptable_count / total_count * 100) if total_count > 0 else 0,
            'best_replacement': batch_result.get('best_replacement', 'None'),
            'candidate_summaries': candidate_summaries
        }

        return report

    def generate_summary_report(
        self,
        repairs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an overall summary report of repair operations.

        Args:
            repairs: List of repair results (evaluations, executions, or batch results)

        Returns:
            dict: Formatted summary report
        """
        total_repairs = len(repairs)
        successful_executions = sum(
            1 for r in repairs
            if r.get('report_type') == 'EXECUTION' and r.get('success', False)
        )
        approved_evaluations = sum(
            1 for r in repairs
            if r.get('report_type') == 'EVALUATION' and r.get('decision') == 'APPROVED'
        )
        failed_repairs = sum(
            1 for r in repairs
            if r.get('report_type') == 'EXECUTION' and not r.get('success', True)
        )

        # Collect unique audiobooks
        audiobooks = set()
        for repair in repairs:
            if 'audiobook' in repair:
                audiobooks.add(repair['audiobook'])

        report = {
            'report_type': 'SUMMARY',
            'timestamp': datetime.now().isoformat(),
            'total_operations': total_repairs,
            'successful_executions': successful_executions,
            'approved_evaluations': approved_evaluations,
            'failed_repairs': failed_repairs,
            'unique_audiobooks': len(audiobooks),
            'success_rate': (successful_executions / total_repairs * 100) if total_repairs > 0 else 0,
            'approval_rate': (approved_evaluations / total_repairs * 100) if total_repairs > 0 else 0
        }

        return report

    def format_report_as_json(self, report: Dict[str, Any]) -> str:
        """
        Format a report as JSON string.

        Args:
            report: Report dictionary

        Returns:
            str: JSON formatted report
        """
        try:
            return json.dumps(report, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to format report as JSON: {e}")
            return json.dumps({'error': str(e)})

    def format_report_as_markdown(self, report: Dict[str, Any]) -> str:
        """
        Format a report as Markdown string.

        Args:
            report: Report dictionary

        Returns:
            str: Markdown formatted report
        """
        report_type = report.get('report_type', 'UNKNOWN')

        if report_type == 'EVALUATION':
            return self._format_evaluation_markdown(report)
        elif report_type == 'EXECUTION':
            return self._format_execution_markdown(report)
        elif report_type == 'BATCH_EVALUATION':
            return self._format_batch_markdown(report)
        elif report_type == 'SUMMARY':
            return self._format_summary_markdown(report)
        else:
            return f"# Unknown Report Type: {report_type}\n\n{json.dumps(report, indent=2, default=str)}"

    def _format_evaluation_markdown(self, report: Dict[str, Any]) -> str:
        """Format evaluation report as Markdown"""
        md = f"""# Replacement Evaluation Report

**Timestamp**: {report.get('timestamp')}
**Audiobook**: {report.get('audiobook')}
**Author**: {report.get('author')}

## Decision

**Status**: {report.get('decision')}
**Reason**: {report.get('reason')}

## Original Audio Properties

| Property | Value |
|----------|-------|
| Codec | {report['original_properties'].get('codec', 'Unknown')} |
| Bitrate | {report['original_properties'].get('bitrate_kbps', 'Unknown')} kbps |
| Duration | {report['original_properties'].get('duration_seconds', 'Unknown')} seconds |
| Sample Rate | {report['original_properties'].get('sample_rate', 'Unknown')} Hz |
| Channels | {report['original_properties'].get('channels', 'Unknown')} |
| File Size | {report['original_properties'].get('file_size_bytes', 'Unknown')} bytes |

## Replacement Audio Properties

| Property | Value |
|----------|-------|
| Codec | {report['replacement_properties'].get('codec', 'Unknown')} |
| Bitrate | {report['replacement_properties'].get('bitrate_kbps', 'Unknown')} kbps |
| Duration | {report['replacement_properties'].get('duration_seconds', 'Unknown')} seconds |
| Sample Rate | {report['replacement_properties'].get('sample_rate', 'Unknown')} Hz |
| Channels | {report['replacement_properties'].get('channels', 'Unknown')} |
| File Size | {report['replacement_properties'].get('file_size_bytes', 'Unknown')} bytes |

## Comparison Results

- **Codec Match**: {report['comparison_results'].get('codec_match')}
- **Bitrate Acceptable**: {report['comparison_results'].get('bitrate_acceptable')}
- **Duration Match**: {report['comparison_results'].get('duration_match')}

## Issues

{self._format_issues(report['comparison_results'].get('issues', []))}
"""
        return md

    def _format_execution_markdown(self, report: Dict[str, Any]) -> str:
        """Format execution report as Markdown"""
        status = "✓ SUCCESS" if report.get('success') else "✗ FAILED"
        md = f"""# Replacement Execution Report

**Timestamp**: {report.get('timestamp')}
**Status**: {status}

## File Information

| Field | Value |
|-------|-------|
| Original File | {report.get('original_file')} |
| Replacement File | {report.get('replacement_file')} |
| Backup File | {report.get('backup_file')} |

## Message

{report.get('message')}

"""
        if report.get('error'):
            md += f"## Error\n\n{report.get('error')}\n"

        return md

    def _format_batch_markdown(self, report: Dict[str, Any]) -> str:
        """Format batch report as Markdown"""
        md = f"""# Batch Evaluation Report

**Timestamp**: {report.get('timestamp')}
**Audiobook**: {report.get('audiobook')}
**Author**: {report.get('author')}

## Summary

- **Candidates Submitted**: {report.get('candidates_submitted')}
- **Candidates Evaluated**: {report.get('candidates_evaluated')}
- **Acceptable Candidates**: {report.get('candidates_acceptable')}
- **Acceptable Rate**: {report.get('acceptable_percentage', 0):.1f}%
- **Best Replacement**: {report.get('best_replacement', 'None')}

## Candidate Evaluations

| Candidate | Acceptable | Decision | Reason |
|-----------|-----------|----------|--------|
"""
        for summary in report.get('candidate_summaries', []):
            acceptable = "Yes" if summary.get('acceptable') else "No"
            md += f"| {summary.get('candidate')} | {acceptable} | {summary.get('decision')} | {summary.get('reason')} |\n"

        return md

    def _format_summary_markdown(self, report: Dict[str, Any]) -> str:
        """Format summary report as Markdown"""
        md = f"""# Repair Operations Summary Report

**Report Timestamp**: {report.get('timestamp')}

## Statistics

- **Total Operations**: {report.get('total_operations')}
- **Successful Executions**: {report.get('successful_executions')}
- **Approved Evaluations**: {report.get('approved_evaluations')}
- **Failed Repairs**: {report.get('failed_repairs')}
- **Unique Audiobooks**: {report.get('unique_audiobooks')}

## Success Rates

- **Execution Success Rate**: {report.get('success_rate', 0):.1f}%
- **Approval Rate**: {report.get('approval_rate', 0):.1f}%
"""
        return md

    def _format_issues(self, issues: List[str]) -> str:
        """Format issues list as Markdown bullet points"""
        if not issues:
            return "No issues detected"
        return "\n".join(f"- {issue}" for issue in issues)

    def save_report(
        self,
        report: Dict[str, Any],
        output_path: str,
        format: str = 'json'
    ) -> bool:
        """
        Save report to file.

        Args:
            report: Report dictionary
            output_path: Path to save report
            format: 'json', 'markdown', or 'both'

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if format in ['json', 'both']:
                json_file = output_file.with_suffix('.json')
                json_file.write_text(self.format_report_as_json(report))
                logger.info(f"Saved JSON report: {json_file}")

            if format in ['markdown', 'both']:
                md_file = output_file.with_suffix('.md')
                md_file.write_text(self.format_report_as_markdown(report))
                logger.info(f"Saved Markdown report: {md_file}")

            return True

        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            return False


# Singleton instance
_repair_reporter = None


def get_repair_reporter() -> RepairReporter:
    """Get RepairReporter instance"""
    global _repair_reporter
    if _repair_reporter is None:
        _repair_reporter = RepairReporter()
    return _repair_reporter
