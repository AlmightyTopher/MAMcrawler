"""
Repair Orchestrator Module
Coordinates the repair and replacement workflow for failed audiobooks.

Repair Pipeline:
1. Quality comparison (codec, bitrate, duration validation)
2. Replacement candidate selection
3. Decision logic (approve/reject replacement)
4. Backup and replacement execution

Failed repairs are logged with detailed diagnostic information.
"""

import logging
import shutil
from typing import Dict, Any, Optional, List
from pathlib import Path
import json

from mamcrawler.repair.quality_comparator import get_quality_comparator
from backend.safety_validator import get_safety_validator
from backend.logging.operation_logger import get_operation_logger

logger = logging.getLogger(__name__)


class RepairOrchestrator:
    """Orchestrates complete repair and replacement workflow"""

    def __init__(self, max_replacement_candidates: int = 5):
        """
        Initialize repair orchestrator.

        Args:
            max_replacement_candidates: Maximum number of replacement candidates to evaluate
        """
        self.max_replacement_candidates = max_replacement_candidates
        self.quality_comparator = get_quality_comparator()
        self.safety_validator = get_safety_validator()
        self.logger = get_operation_logger()

    def evaluate_replacement(
        self,
        original_file: str,
        replacement_file: str,
        audiobook_title: str = "Unknown",
        author: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Evaluate if a replacement file is acceptable for the original.

        Args:
            original_file: Path to original audio file
            replacement_file: Path to replacement candidate file
            audiobook_title: Audiobook title (for logging)
            author: Author name (for logging)

        Returns:
            dict: {
                'is_acceptable': bool,
                'quality_comparison': quality comparison result,
                'decision': str,
                'reason': str,
                'audiobook_title': str,
                'author': str
            }
        """
        logger.info(f"Evaluating replacement for: {audiobook_title} by {author}")

        # Step 1: Compare audio quality
        comparison = self.quality_comparator.compare_quality(
            original_file,
            replacement_file
        )

        # Step 2: Make replacement decision
        decision = self._make_replacement_decision(comparison)

        result = {
            'is_acceptable': decision['is_acceptable'],
            'quality_comparison': comparison,
            'decision': decision['decision'],
            'reason': decision['reason'],
            'audiobook_title': audiobook_title,
            'author': author
        }

        # Log the evaluation
        self.logger.log_repair(
            title=audiobook_title,
            author=author,
            reason=f"Quality comparison: {decision['reason']}",
            result='EVALUATED',
            details={
                'decision': decision['decision'],
                'is_acceptable': decision['is_acceptable'],
                'quality_issues': comparison['comparison'].get('issues', [])
            }
        )

        return result

    def execute_replacement(
        self,
        original_file: str,
        replacement_file: str,
        audiobook_title: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Execute the replacement operation (backup original, replace with new file).

        Args:
            original_file: Path to original audio file
            replacement_file: Path to replacement file
            audiobook_title: Audiobook title (for logging)

        Returns:
            dict: {
                'success': bool,
                'original_file': str,
                'replacement_file': str,
                'backup_file': str (if successful),
                'error': str (if failed),
                'message': str
            }
        """
        logger.info(f"Executing replacement for: {audiobook_title}")

        try:
            # Step 1: Validate paths
            original_path = Path(original_file)
            replacement_path = Path(replacement_file)

            if not original_path.exists():
                error_msg = f"Original file not found: {original_file}"
                logger.error(error_msg)
                self.logger.log_repair(
                    title=audiobook_title,
                    author='Unknown',
                    reason=error_msg,
                    result='FAILED'
                )
                return {
                    'success': False,
                    'original_file': original_file,
                    'replacement_file': replacement_file,
                    'error': error_msg,
                    'message': 'Replacement execution failed'
                }

            if not replacement_path.exists():
                error_msg = f"Replacement file not found: {replacement_file}"
                logger.error(error_msg)
                self.logger.log_repair(
                    title=audiobook_title,
                    author='Unknown',
                    reason=error_msg,
                    result='FAILED'
                )
                return {
                    'success': False,
                    'original_file': original_file,
                    'replacement_file': replacement_file,
                    'error': error_msg,
                    'message': 'Replacement execution failed'
                }

            # Step 2: Safety validation - ensure operation is safe
            if not self.safety_validator.validate_operation('replace_audiobook'):
                error_msg = "Repair operation not validated as safe"
                logger.error(error_msg)
                self.logger.log_repair(
                    title=audiobook_title,
                    author='Unknown',
                    reason=error_msg,
                    result='FAILED'
                )
                return {
                    'success': False,
                    'original_file': original_file,
                    'replacement_file': replacement_file,
                    'error': error_msg,
                    'message': 'Safety validation failed'
                }

            # Step 3: Create backup
            backup_file = self._create_backup(original_path)
            if not backup_file:
                error_msg = "Failed to create backup of original file"
                logger.error(error_msg)
                self.logger.log_repair(
                    title=audiobook_title,
                    author='Unknown',
                    reason=error_msg,
                    result='FAILED'
                )
                return {
                    'success': False,
                    'original_file': original_file,
                    'replacement_file': replacement_file,
                    'error': error_msg,
                    'message': 'Backup creation failed'
                }

            # Step 4: Replace the file
            try:
                # Remove original
                original_path.unlink()

                # Copy replacement to original location
                shutil.copy2(replacement_path, original_path)

                logger.info(f"Successfully replaced: {audiobook_title}")
                self.logger.log_repair(
                    title=audiobook_title,
                    author='Unknown',
                    reason='Replacement executed successfully',
                    result='REPLACED',
                    details={'backup_file': str(backup_file)}
                )

                return {
                    'success': True,
                    'original_file': original_file,
                    'replacement_file': replacement_file,
                    'backup_file': str(backup_file),
                    'message': f'Replacement completed. Backup: {backup_file}'
                }

            except Exception as e:
                error_msg = f"Error during file replacement: {str(e)}"
                logger.error(error_msg)

                # Attempt to restore from backup
                if backup_file and backup_file.exists():
                    try:
                        shutil.copy2(backup_file, original_path)
                        logger.info(f"Restored original from backup: {backup_file}")
                    except Exception as restore_error:
                        logger.error(f"Failed to restore backup: {restore_error}")

                self.logger.log_repair(
                    title=audiobook_title,
                    author='Unknown',
                    reason=error_msg,
                    result='FAILED'
                )

                return {
                    'success': False,
                    'original_file': original_file,
                    'replacement_file': replacement_file,
                    'backup_file': str(backup_file) if backup_file else None,
                    'error': error_msg,
                    'message': 'Replacement execution failed'
                }

        except Exception as e:
            error_msg = f"Unexpected error during replacement: {str(e)}"
            logger.error(error_msg)
            self.logger.log_repair(
                title=audiobook_title,
                author='Unknown',
                reason=error_msg,
                result='FAILED'
            )

            return {
                'success': False,
                'original_file': original_file,
                'replacement_file': replacement_file,
                'error': error_msg,
                'message': 'Replacement execution failed'
            }

    def batch_evaluate_replacements(
        self,
        original_file: str,
        replacement_candidates: List[str],
        audiobook_title: str = "Unknown",
        author: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Evaluate multiple replacement candidates and rank by acceptability.

        Args:
            original_file: Path to original audio file
            replacement_candidates: List of replacement candidate file paths
            audiobook_title: Audiobook title (for logging)
            author: Author name (for logging)

        Returns:
            dict: {
                'audiobook_title': str,
                'author': str,
                'candidates_evaluated': int,
                'acceptable_candidates': list of acceptable candidates,
                'best_replacement': str (path to best candidate, if any),
                'evaluations': list of all evaluations
            }
        """
        logger.info(
            f"Batch evaluating {len(replacement_candidates)} replacement candidates "
            f"for: {audiobook_title}"
        )

        evaluations = []
        acceptable = []

        # Limit to max candidates
        candidates_to_eval = replacement_candidates[:self.max_replacement_candidates]

        for candidate in candidates_to_eval:
            evaluation = self.evaluate_replacement(
                original_file,
                candidate,
                audiobook_title,
                author
            )
            evaluations.append({
                'candidate': candidate,
                'evaluation': evaluation
            })

            if evaluation['is_acceptable']:
                acceptable.append(candidate)

        # Rank acceptable candidates by quality metrics
        best_candidate = None
        if acceptable:
            best_candidate = self._rank_candidates(
                acceptable,
                evaluations
            )

        self.logger.log_repair(
            title=audiobook_title,
            author=author,
            reason=f"Batch evaluation of {len(replacement_candidates)} candidates",
            result='EVALUATED',
            details={
                'candidates_total': len(replacement_candidates),
                'candidates_acceptable': len(acceptable),
                'best_candidate': best_candidate if best_candidate else "None"
            }
        )

        return {
            'audiobook_title': audiobook_title,
            'author': author,
            'candidates_evaluated': len(candidates_to_eval),
            'candidates_submitted': len(replacement_candidates),
            'acceptable_candidates': acceptable,
            'best_replacement': best_candidate,
            'evaluations': evaluations
        }

    def _make_replacement_decision(
        self,
        comparison: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make accept/reject decision based on quality comparison.

        Args:
            comparison: Quality comparison result from QualityComparator

        Returns:
            dict: {
                'is_acceptable': bool,
                'decision': str (APPROVED, REJECTED),
                'reason': str
            }
        """
        if comparison['is_better_or_equal']:
            return {
                'is_acceptable': True,
                'decision': 'APPROVED',
                'reason': 'Quality acceptable for replacement'
            }
        else:
            issues = comparison['comparison'].get('issues', [])
            reason = '; '.join(issues) if issues else 'Quality issues detected'
            return {
                'is_acceptable': False,
                'decision': 'REJECTED',
                'reason': reason
            }

    def _create_backup(self, original_path: Path) -> Optional[Path]:
        """
        Create a backup of the original file.

        Args:
            original_path: Path to original file

        Returns:
            Path to backup file, or None if backup failed
        """
        try:
            backup_dir = original_path.parent / '.backup'
            backup_dir.mkdir(exist_ok=True)
            backup_file = backup_dir / f"{original_path.name}.backup"
            shutil.copy2(original_path, backup_file)
            logger.info(f"Created backup: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def _rank_candidates(
        self,
        acceptable_candidates: List[str],
        evaluations: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Rank acceptable candidates by quality metrics (prefer higher bitrate).

        Args:
            acceptable_candidates: List of acceptable file paths
            evaluations: List of all evaluation results

        Returns:
            Path to best candidate, or None if no acceptable candidates
        """
        if not acceptable_candidates:
            return None

        # Find evaluations for acceptable candidates
        candidate_scores = []
        for eval_item in evaluations:
            if eval_item['candidate'] in acceptable_candidates:
                comparison = eval_item['evaluation']['quality_comparison']
                replacement_props = comparison.get('replacement', {})
                bitrate = replacement_props.get('bitrate_kbps', 0)
                candidate_scores.append((eval_item['candidate'], bitrate))

        # Sort by bitrate (descending) - prefer higher quality
        if candidate_scores:
            candidate_scores.sort(key=lambda x: x[1], reverse=True)
            best = candidate_scores[0][0]
            logger.info(f"Selected best replacement candidate: {best}")
            return best

        return acceptable_candidates[0] if acceptable_candidates else None


# Singleton instance
_repair_orchestrator = None


def get_repair_orchestrator() -> RepairOrchestrator:
    """Get RepairOrchestrator instance"""
    global _repair_orchestrator
    if _repair_orchestrator is None:
        _repair_orchestrator = RepairOrchestrator()
    return _repair_orchestrator
