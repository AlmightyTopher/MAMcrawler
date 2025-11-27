"""
Repair & Replacement System Package
Handles failed verification recovery and audiobook replacement with quality comparison.

Features:
- Quality comparison (codec, bitrate, duration)
- Repair orchestration (evaluate, approve, execute replacements)
- Comprehensive repair reporting (evaluation, execution, batch, summary)
- Safe replacement candidate validation
- Comprehensive repair logging

Three main components:

1. QualityComparator: Compares audio quality metrics
2. RepairOrchestrator: Coordinates repair/replacement workflow
3. RepairReporter: Generates detailed repair operation reports

Usage:
    from mamcrawler.repair import get_quality_comparator, get_repair_orchestrator, get_repair_reporter

    # Evaluate replacement quality
    comparator = get_quality_comparator()
    comparison = comparator.compare_quality(original_file, replacement_file)

    # Orchestrate replacement
    orchestrator = get_repair_orchestrator()
    evaluation = orchestrator.evaluate_replacement(original_file, replacement_file, title, author)

    # Generate report
    reporter = get_repair_reporter()
    report = reporter.generate_evaluation_report(evaluation)
    reporter.save_report(report, output_path, format='both')
"""

from mamcrawler.repair.quality_comparator import QualityComparator, get_quality_comparator
from mamcrawler.repair.repair_orchestrator import RepairOrchestrator, get_repair_orchestrator
from mamcrawler.repair.repair_reporter import RepairReporter, get_repair_reporter

__all__ = [
    'QualityComparator',
    'get_quality_comparator',
    'RepairOrchestrator',
    'get_repair_orchestrator',
    'RepairReporter',
    'get_repair_reporter',
]

__version__ = "0.2.0"
__description__ = "Complete repair and replacement system for failed audiobooks with quality comparison and reporting"
