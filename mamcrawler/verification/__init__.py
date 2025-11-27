"""
Verification System Package
Comprehensive audiobook verification with narrator, duration, ISBN, and chapter checks.

Usage:
    from mamcrawler.verification import get_verification_orchestrator

    orchestrator = get_verification_orchestrator()
    result = orchestrator.verify_audiobook(
        audio_path="/path/to/audiobook.m4b",
        metadata={...},
        title="Book Title",
        author="Author Name"
    )

    # Check result
    if result['passed']:
        print("Audiobook verified successfully")
    else:
        print(f"Failed checks: {result['failures']}")
"""

from mamcrawler.verification.narrator_verifier import NarratorVerifier, get_narrator_verifier
from mamcrawler.verification.duration_verifier import DurationVerifier, get_duration_verifier
from mamcrawler.verification.isbn_verifier import ISBNVerifier, get_isbn_verifier
from mamcrawler.verification.chapter_verifier import ChapterVerifier, get_chapter_verifier
from mamcrawler.verification.verification_orchestrator import VerificationOrchestrator, get_verification_orchestrator

__all__ = [
    'NarratorVerifier',
    'DurationVerifier',
    'ISBNVerifier',
    'ChapterVerifier',
    'VerificationOrchestrator',
    'get_narrator_verifier',
    'get_duration_verifier',
    'get_isbn_verifier',
    'get_chapter_verifier',
    'get_verification_orchestrator',
]

__version__ = "1.0.0"
__description__ = "Comprehensive audiobook verification system"
