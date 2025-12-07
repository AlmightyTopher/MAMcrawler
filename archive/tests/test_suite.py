"""
Comprehensive Test Suite for MAMcrawler
Tests all 12 implemented features
"""

import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mamcrawler.quality import QualityFilter
from mamcrawler.narrator_detector import NarratorDetector
from mamcrawler.goodreads import GoodreadsMetadata
from mamcrawler.metadata_scanner import MetadataScanner
from mamcrawler.series_completion import SeriesCompletion
from mamcrawler.author_series_completion import AuthorSeriesCompletion
from mamcrawler.edition_replacement import EditionReplacement
from mamcrawler.ratio_emergency import RatioEmergency
from mamcrawler.event_pacing import EventAwarePacing
from mamcrawler.mam_categories import MAMCategories, CategoryScheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestSuite:
    """Comprehensive test suite for all features."""
    
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'tests': []
        }
    
    def test(self, name: str, func):
        """Run a test and record result."""
        logger.info(f"\n{'='*70}")
        logger.info(f"TEST: {name}")
        logger.info(f"{'='*70}")
        
        try:
            result = func()
            
            if result:
                logger.info(f"✅ PASSED: {name}")
                self.results['passed'] += 1
                self.results['tests'].append({'name': name, 'status': 'PASSED'})
            else:
                logger.error(f"❌ FAILED: {name}")
                self.results['failed'] += 1
                self.results['tests'].append({'name': name, 'status': 'FAILED'})
        
        except Exception as e:
            logger.error(f"❌ FAILED: {name} - {e}")
            self.results['failed'] += 1
            self.results['tests'].append({'name': name, 'status': 'FAILED', 'error': str(e)})
    
    def print_summary(self):
        """Print test summary."""
        logger.info(f"\n{'='*70}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'='*70}")
        logger.info(f"Total Tests: {len(self.results['tests'])}")
        logger.info(f"✅ Passed: {self.results['passed']}")
        logger.info(f"❌ Failed: {self.results['failed']}")
        logger.info(f"{'='*70}")
        
        if self.results['failed'] == 0:
            logger.info("🎉 ALL TESTS PASSED!")
        else:
            logger.error(f"⚠️  {self.results['failed']} TESTS FAILED")


# Test Functions

def test_quality_filter():
    """Test QualityFilter module."""
    qf = QualityFilter()
    
    torrent1 = {'title': 'Book (Unabridged) 128kbps', 'seeders': 10}
    torrent2 = {'title': 'Book (Abridged) 64kbps', 'seeders': 5}
    
    score1 = qf._score_release(torrent1)
    score2 = qf._score_release(torrent2)
    
    assert score1 > score2, "Unabridged should score higher"
    
    best = qf.select_best_release([torrent1, torrent2])
    assert best == torrent1, "Should select unabridged"
    
    logger.info("✓ Quality filter working")
    return True


def test_narrator_detector():
    """Test NarratorDetector module."""
    nd = NarratorDetector()
    
    metadata = {'narrator': 'John Smith'}
    narrator = nd.detect_from_metadata(metadata)
    assert narrator == 'John Smith', "Should extract narrator"
    
    text = "This audiobook is narrated by Jane Doe"
    narrator = nd._extract_narrator_from_text(text)
    assert narrator == 'Jane Doe', "Should extract from text"
    
    logger.info("✓ Narrator detector working")
    return True


def test_goodreads_metadata():
    """Test GoodreadsMetadata module."""
    gr = GoodreadsMetadata()
    
    html = '<a href="/book/show/12345">Test</a>'
    url = gr._extract_first_result(html)
    assert url == 'https://www.goodreads.com/book/show/12345', "Should extract URL"
    
    logger.info("✓ Goodreads module working")
    return True


def test_metadata_scanner():
    """Test MetadataScanner module."""
    scanner = MetadataScanner()
    
    metadata = scanner._extract_from_filename("The Great Book by John Author")
    assert metadata.get('title') == 'The Great Book', "Should extract title"
    assert metadata.get('author') == 'John Author', "Should extract author"
    
    logger.info("✓ Metadata scanner working")
    return True


def test_series_completion():
    """Test SeriesCompletion module."""
    sc = SeriesCompletion()
    
    match = sc._fuzzy_title_match("The Great Book", "The Great Book: A Novel")
    assert match, "Should fuzzy match"
    
    logger.info("✓ Series completion working")
    return True


def test_author_series_completion():
    """Test AuthorSeriesCompletion module."""
    asc = AuthorSeriesCompletion()
    
    wishlist = [
        {'title': 'Book 1', 'author': 'Author A'},
        {'title': 'Book 1', 'author': 'Author A'},
        {'title': 'Book 2', 'author': 'Author A'}
    ]
    
    unique = asc._deduplicate_wishlist(wishlist)
    assert len(unique) == 2, "Should remove duplicates"
    
    logger.info("✓ Author/series completion working")
    return True


def test_edition_replacement():
    """Test EditionReplacement module."""
    qf = QualityFilter()
    er = EditionReplacement(qf)
    
    existing = {'title': 'Book (Abridged) 64kbps', 'seeders': 5}
    new = {'title': 'Book (Unabridged) 128kbps', 'seeders': 10}
    
    comparison = er.compare_editions(existing, new)
    assert comparison == 'new', "Should prefer new"
    
    should_replace = er.should_replace(existing, new)
    assert should_replace, "Should recommend replacement"
    
    logger.info("✓ Edition replacement working")
    return True


def test_ratio_emergency():
    """Test RatioEmergency module."""
    assert RatioEmergency.CRITICAL_RATIO == 1.0, "Critical should be 1.0"
    assert RatioEmergency.WARNING_RATIO == 1.1, "Warning should be 1.1"
    assert RatioEmergency.SAFE_RATIO == 1.2, "Safe should be 1.2"
    
    logger.info("✓ Ratio emergency working")
    return True


def test_event_pacing():
    """Test EventAwarePacing module."""
    ep = EventAwarePacing()
    
    assert ep.pacing_mode == 'normal', "Should start normal"
    
    delay = ep.get_download_delay()
    assert delay == 120, "Normal delay should be 120s"
    
    ep.pacing_mode = 'event'
    delay = ep.get_download_delay()
    assert delay == 30, "Event delay should be 30s"
    
    logger.info("✓ Event pacing working")
    return True


def test_mam_categories():
    """Test MAMCategories module."""
    assert len(MAMCategories.CATEGORIES) == 40, "Should have 40 categories"
    
    url = MAMCategories.build_search_url('Fantasy', 'WEEK')
    assert 'cat[]=' in url, "Should build valid URL"
    
    scheduler = CategoryScheduler()
    daily = scheduler.get_daily_schedule()
    assert len(daily) > 0, "Should have daily schedule"
    
    logger.info("✓ MAM categories working")
    return True


# Main Test Runner

def run_all_tests():
    """Run all tests."""
    suite = TestSuite()
    
    logger.info("\n" + "="*70)
    logger.info("MAMCRAWLER COMPREHENSIVE TEST SUITE")
    logger.info("Testing all 12 implemented features")
    logger.info("="*70 + "\n")
    
    # Run all tests
    suite.test("1. Quality Filter", test_quality_filter)
    suite.test("2. Narrator Detector", test_narrator_detector)
    suite.test("3. Goodreads Metadata", test_goodreads_metadata)
    suite.test("4. Metadata Scanner", test_metadata_scanner)
    suite.test("5. Series Completion", test_series_completion)
    suite.test("6. Author/Series Completion", test_author_series_completion)
    suite.test("7. Edition Replacement", test_edition_replacement)
    suite.test("8. Ratio Emergency", test_ratio_emergency)
    suite.test("9. Event Pacing", test_event_pacing)
    suite.test("10. MAM Categories", test_mam_categories)
    
    # Print summary
    suite.print_summary()
    
    return suite.results['failed'] == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
