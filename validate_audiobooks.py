#!/usr/bin/env python3
"""
Audiobook Audio File Validator

Validates audiobook files to confirm Hardcover metadata match:
1. Extract ID3 metadata from audio files
2. Analyze audio properties (duration, codec, bitrate)
3. Compare with Hardcover resolution
4. Generate confidence scores
5. Optionally open in player for manual verification

Usage:
    # Validate a single file
    python validate_audiobooks.py "/path/to/audiobook.m4b"

    # Validate audiobook files from specific audiobook
    python validate_audiobooks.py \
        --hardcover-title "The Way of Kings" \
        --hardcover-author "Brandon Sanderson" \
        --library-path "/path/to/audiobook/folder"

    # Validate files and open in player if low confidence
    python validate_audiobooks.py \
        --hardcover-title "The Way of Kings" \
        --hardcover-author "Brandon Sanderson" \
        --hardcover-series "Stormlight Archive" \
        --library-path "/path/to/audiobook/folder" \
        --auto-open
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import argparse

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.integrations.audio_validator import AudioValidator, validate_and_compare

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class AudiobookValidator:
    """Validate audiobook files against Hardcover metadata"""

    def __init__(self, auto_open: bool = False):
        self.validator = AudioValidator()
        self.auto_open = auto_open
        self.validations: List[Dict] = []

    async def validate_file(
        self,
        file_path: str,
        hardcover_title: str,
        hardcover_author: str,
        hardcover_series: Optional[str] = None
    ) -> Dict:
        """
        Validate a single audio file

        Args:
            file_path: Path to audio file
            hardcover_title: Expected title from Hardcover
            hardcover_author: Expected author from Hardcover
            hardcover_series: Expected series name (optional)

        Returns:
            Validation result with confidence score
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return {
                "valid": False,
                "file": str(file_path),
                "error": f"File not found"
            }

        logger.info(f"\nValidating: {file_path.name}")
        logger.info(f"  Expected: {hardcover_title} by {hardcover_author}")

        # Validate file
        result = await validate_and_compare(
            file_path=str(file_path),
            hardcover_title=hardcover_title,
            hardcover_author=hardcover_author,
            hardcover_series=(hardcover_series, 0) if hardcover_series else None,
            auto_open=self.auto_open
        )

        # Pretty print results
        if result.get("valid"):
            file_info = result.get("file_info", {})
            metadata = file_info.get("metadata", {})
            confidence = result.get("confidence", 0.0)

            logger.info(f"  ✓ File validated")
            logger.info(f"    Duration: {file_info.get('duration', 'unknown')}s")
            logger.info(f"    Codec: {file_info.get('codec', 'unknown')}")
            logger.info(f"    Bitrate: {file_info.get('bitrate', 'unknown')}")
            logger.info(f"    Confidence: {confidence:.0%}")

            if metadata:
                logger.info(f"    Metadata found:")
                if metadata.get("title"):
                    logger.info(f"      Title: {metadata.get('title')}")
                if metadata.get("artist"):
                    logger.info(f"      Artist: {metadata.get('artist')}")
                if metadata.get("narrator"):
                    logger.info(f"      Narrator: {metadata.get('narrator')}")

            if result.get("differences"):
                logger.info(f"    Differences:")
                for diff in result.get("differences", []):
                    logger.info(f"      • {diff}")

            if result.get("requires_verification"):
                logger.warning(f"    ⚠ Low confidence - manual verification recommended")

        else:
            logger.error(f"  ✗ Validation failed: {result.get('error')}")

        self.validations.append(result)
        return result

    async def validate_directory(
        self,
        directory: str,
        hardcover_title: str,
        hardcover_author: str,
        hardcover_series: Optional[str] = None
    ) -> List[Dict]:
        """
        Validate all audio files in directory

        Args:
            directory: Path to audiobook directory
            hardcover_title: Expected title from Hardcover
            hardcover_author: Expected author from Hardcover
            hardcover_series: Expected series name (optional)

        Returns:
            List of validation results
        """
        dir_path = Path(directory)

        if not dir_path.is_dir():
            logger.error(f"Directory not found: {directory}")
            return []

        # Find audio files
        audio_extensions = {'.m4b', '.mp3', '.flac', '.ogg', '.wma', '.aac'}
        audio_files = [
            f for f in dir_path.rglob('*')
            if f.suffix.lower() in audio_extensions
        ]

        if not audio_files:
            logger.warning(f"No audio files found in: {directory}")
            return []

        logger.info(f"Found {len(audio_files)} audio file(s)")

        # Validate each file
        for audio_file in sorted(audio_files):
            await self.validate_file(
                str(audio_file),
                hardcover_title,
                hardcover_author,
                hardcover_series
            )

        return self.validations

    async def generate_report(self) -> Dict:
        """Generate validation report"""
        if not self.validations:
            return {}

        valid = sum(1 for v in self.validations if v.get("valid"))
        invalid = sum(1 for v in self.validations if not v.get("valid"))
        high_confidence = sum(
            1 for v in self.validations
            if v.get("valid") and v.get("confidence", 0) >= 0.95
        )
        low_confidence = sum(
            1 for v in self.validations
            if v.get("valid") and v.get("confidence", 0) < 0.95
        )

        avg_confidence = (
            sum(v.get("confidence", 0) for v in self.validations if v.get("valid"))
            / valid
            if valid > 0
            else 0
        )

        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(self.validations),
                "valid": valid,
                "invalid": invalid,
                "high_confidence": high_confidence,
                "low_confidence": low_confidence,
                "average_confidence": avg_confidence,
            },
            "validations": self.validations,
        }

        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION REPORT")
        logger.info("=" * 80)
        logger.info(f"Total Files: {len(self.validations)}")
        logger.info(f"Valid: {valid}")
        logger.info(f"Invalid: {invalid}")
        logger.info(f"High Confidence (≥95%): {high_confidence}")
        logger.info(f"Low Confidence (<95%): {low_confidence}")
        logger.info(f"Average Confidence: {avg_confidence:.0%}")
        logger.info("=" * 80)

        # Save report
        report_file = Path("audiobook_validation_report.json")
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"\n✓ Report saved to: {report_file}")

        # Recommendations
        logger.info("\nRECOMMENDATIONS:")
        if high_confidence == len(self.validations):
            logger.info("✓ All files match Hardcover metadata with high confidence")
            logger.info("  → Ready to update AudiobookShelf")
        elif low_confidence > 0:
            logger.info(f"⚠ {low_confidence} file(s) have low confidence matches")
            logger.info("  → Manually verify these files:")
            for v in self.validations:
                if v.get("valid") and v.get("confidence", 0) < 0.95:
                    logger.info(f"    - {Path(v.get('file')).name}")
            logger.info("  → Use --auto-open to open files in player")
        if invalid > 0:
            logger.info(f"✗ {invalid} file(s) failed validation")
            logger.info("  → Check file format and availability")

        return report


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validate audiobook files against Hardcover metadata"
    )

    parser.add_argument(
        "file_path",
        nargs="?",
        help="Path to single audio file to validate"
    )
    parser.add_argument(
        "--hardcover-title",
        help="Expected title from Hardcover"
    )
    parser.add_argument(
        "--hardcover-author",
        help="Expected author from Hardcover"
    )
    parser.add_argument(
        "--hardcover-series",
        help="Expected series name from Hardcover (optional)"
    )
    parser.add_argument(
        "--library-path",
        help="Path to audiobook directory (validate all files)"
    )
    parser.add_argument(
        "--auto-open",
        action="store_true",
        help="Automatically open files in player if confidence < 95%"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.file_path and not args.library_path:
        parser.print_help()
        logger.error("Either FILE_PATH or --library-path is required")
        sys.exit(1)

    if (args.file_path or args.library_path) and not args.hardcover_title:
        parser.print_help()
        logger.error("--hardcover-title is required")
        sys.exit(1)

    if not args.hardcover_author:
        parser.print_help()
        logger.error("--hardcover-author is required")
        sys.exit(1)

    validator = AudiobookValidator(auto_open=args.auto_open)

    logger.info("=" * 80)
    logger.info("Audiobook Audio File Validator")
    logger.info("=" * 80)

    # Validate single file or directory
    if args.file_path:
        logger.info(f"Mode: Single File Validation")
        logger.info(f"File: {args.file_path}")
        logger.info(f"Expected: {args.hardcover_title} by {args.hardcover_author}")
        if args.hardcover_series:
            logger.info(f"Series: {args.hardcover_series}")

        result = await validator.validate_file(
            args.file_path,
            args.hardcover_title,
            args.hardcover_author,
            args.hardcover_series
        )

        logger.info("\nResult:")
        logger.info(json.dumps(result, indent=2, default=str))

    elif args.library_path:
        logger.info(f"Mode: Directory Validation")
        logger.info(f"Directory: {args.library_path}")
        logger.info(f"Expected: {args.hardcover_title} by {args.hardcover_author}")
        if args.hardcover_series:
            logger.info(f"Series: {args.hardcover_series}")

        await validator.validate_directory(
            args.library_path,
            args.hardcover_title,
            args.hardcover_author,
            args.hardcover_series
        )

        report = await validator.generate_report()

    logger.info("\n" + "=" * 80)
    logger.info("Validation Complete")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
