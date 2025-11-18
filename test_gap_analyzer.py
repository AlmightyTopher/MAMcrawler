#!/usr/bin/env python3
"""
Unit tests for Audiobook Gap Analyzer

Tests the main functionality of the gap analysis system including:
- Library book extraction
- Series gap detection
- Duplicate detection
- Title matching
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from pathlib import Path

# Import the analyzer
from audiobook_gap_analyzer import AudiobookGapAnalyzer


class TestAudiobookGapAnalyzer:
    """Test suite for AudiobookGapAnalyzer class."""

    def setup_method(self):
        """Setup test fixtures."""
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'ABS_URL': 'http://localhost:13378',
            'ABS_TOKEN': 'test_token',
            'MAM_USERNAME': 'test_user',
            'MAM_PASSWORD': 'test_pass',
            'QBITTORRENT_URL': 'http://localhost:52095',
            'QBITTORRENT_USERNAME': 'admin',
            'QBITTORRENT_PASSWORD': 'password'
        })
        self.env_patcher.start()

        # Mock qBittorrent client
        with patch('audiobook_gap_analyzer.qbittorrentapi.Client'):
            self.analyzer = AudiobookGapAnalyzer()

    def teardown_method(self):
        """Cleanup after tests."""
        self.env_patcher.stop()

    def test_init(self):
        """Test analyzer initialization."""
        assert self.analyzer.abs_url == 'http://localhost:13378'
        assert self.analyzer.abs_token == 'test_token'
        assert self.analyzer.mam_username == 'test_user'
        assert self.analyzer.config['max_downloads_per_run'] == 10

    def test_extract_book_metadata(self):
        """Test extracting metadata from Audiobookshelf item."""
        item = {
            'id': 'book123',
            'media': {
                'metadata': {
                    'title': 'The Name of the Wind',
                    'authorName': 'Patrick Rothfuss',
                    'seriesName': 'The Kingkiller Chronicle',
                    'seriesSequence': '1',
                    'isbn': '978-0756404741',
                    'asin': 'B002UZML00'
                }
            }
        }

        book = self.analyzer._extract_book_metadata(item)

        assert book is not None
        assert book['title'] == 'The Name of the Wind'
        assert book['author'] == 'Patrick Rothfuss'
        assert book['series'] == 'The Kingkiller Chronicle'
        assert book['series_sequence'] == '1'
        assert book['abs_id'] == 'book123'

    def test_extract_book_metadata_no_series(self):
        """Test extracting metadata for standalone book."""
        item = {
            'id': 'standalone123',
            'media': {
                'metadata': {
                    'title': 'Standalone Book',
                    'authorName': 'Some Author',
                    'seriesName': '',
                    'seriesSequence': ''
                }
            }
        }

        book = self.analyzer._extract_book_metadata(item)

        assert book is not None
        assert book['title'] == 'Standalone Book'
        assert book['series'] is None
        assert book['series_sequence'] is None

    def test_is_title_owned_exact_match(self):
        """Test duplicate detection with exact match."""
        owned_books = [
            {'title': 'The Name of the Wind', 'author': 'Patrick Rothfuss'},
            {'title': 'The Wise Man\'s Fear', 'author': 'Patrick Rothfuss'}
        ]

        assert self.analyzer._is_title_owned('The Name of the Wind', owned_books) == True
        assert self.analyzer._is_title_owned('The Slow Regard of Silent Things', owned_books) == False

    def test_is_title_owned_fuzzy_match(self):
        """Test duplicate detection with fuzzy matching."""
        owned_books = [
            {'title': 'Harry Potter and the Sorcerer\'s Stone', 'author': 'J.K. Rowling'}
        ]

        # Substring match
        assert self.analyzer._is_title_owned('Sorcerer\'s Stone', owned_books) == True

        # Different title
        assert self.analyzer._is_title_owned('Chamber of Secrets', owned_books) == False

    def test_is_title_owned_case_insensitive(self):
        """Test duplicate detection is case insensitive."""
        owned_books = [
            {'title': 'THE NAME OF THE WIND', 'author': 'Patrick Rothfuss'}
        ]

        assert self.analyzer._is_title_owned('the name of the wind', owned_books) == True

    def test_is_duplicate_in_library(self):
        """Test checking duplicates in library."""
        self.analyzer.library_books = [
            {'title': 'Book One', 'author': 'Author A'},
            {'title': 'Book Two', 'author': 'Author B'}
        ]

        assert self.analyzer._is_duplicate_in_library('Book One', 'Author A') == True
        assert self.analyzer._is_duplicate_in_library('Book Three', 'Author C') == False

    def test_generate_report_success(self):
        """Test report generation on success."""
        self.analyzer.stats['library_books'] = 100
        self.analyzer.stats['gaps_identified'] = 5
        self.analyzer.stats['downloads_queued'] = 3
        self.analyzer.gaps = [
            {'title': 'Gap 1', 'author': 'Author', 'type': 'series_gap', 'download_status': 'queued'}
        ]

        report = self.analyzer._generate_report(success=True)

        assert report['success'] == True
        assert report['error'] is None
        assert report['stats']['library_books'] == 100
        assert len(report['gaps']) == 1

    def test_generate_report_failure(self):
        """Test report generation on failure."""
        report = self.analyzer._generate_report(success=False, error="Test error")

        assert report['success'] == False
        assert report['error'] == "Test error"

    @pytest.mark.asyncio
    async def test_analyze_series(self):
        """Test series grouping."""
        self.analyzer.library_books = [
            {'title': 'Book 1', 'author': 'Author A', 'series': 'Series A', 'series_sequence': '1'},
            {'title': 'Book 2', 'author': 'Author A', 'series': 'Series A', 'series_sequence': '2'},
            {'title': 'Book 3', 'author': 'Author B', 'series': 'Series B', 'series_sequence': '1'},
            {'title': 'Standalone', 'author': 'Author C', 'series': None}
        ]

        await self.analyzer._analyze_series()

        assert len(self.analyzer.series_map) == 2
        assert 'Series A|Author A' in self.analyzer.series_map
        assert len(self.analyzer.series_map['Series A|Author A']) == 2

    @pytest.mark.asyncio
    async def test_analyze_authors(self):
        """Test author grouping."""
        self.analyzer.library_books = [
            {'title': 'Book 1', 'author': 'Author A', 'series': None},
            {'title': 'Book 2', 'author': 'Author A', 'series': None},
            {'title': 'Book 3', 'author': 'Author B', 'series': None}
        ]

        await self.analyzer._analyze_authors()

        assert len(self.analyzer.author_map) == 2
        assert 'Author A' in self.analyzer.author_map
        assert len(self.analyzer.author_map['Author A']) == 2

    def test_state_management(self):
        """Test state save and load."""
        self.analyzer.state['completed_searches'] = ['test_search']
        self.analyzer._save_state()

        # Verify state was saved
        assert self.analyzer.state_file.exists()

        # Load state
        loaded_state = self.analyzer._load_state()
        assert 'test_search' in loaded_state['completed_searches']

        # Cleanup
        if self.analyzer.state_file.exists():
            self.analyzer.state_file.unlink()


class TestGapAnalyzerUtilities:
    """Test utility functions."""

    def test_config_defaults(self):
        """Test default configuration values."""
        with patch.dict('os.environ', {
            'ABS_URL': 'http://test:13378',
            'ABS_TOKEN': 'token',
            'MAM_USERNAME': 'user',
            'MAM_PASSWORD': 'pass'
        }):
            with patch('audiobook_gap_analyzer.qbittorrentapi.Client'):
                analyzer = AudiobookGapAnalyzer()

        assert analyzer.config['max_downloads_per_run'] == 10
        assert analyzer.config['series_priority'] == True
        assert analyzer.config['author_priority'] == True
        assert analyzer.config['min_seeds'] == 1
        assert analyzer.config['title_match_threshold'] == 0.7


class TestGapAnalyzerAsync:
    """Test async operations."""

    @pytest.mark.asyncio
    async def test_scan_library_no_token(self):
        """Test library scan fails gracefully without token."""
        with patch.dict('os.environ', {
            'ABS_URL': 'http://test:13378',
            'ABS_TOKEN': '',
            'MAM_USERNAME': 'user',
            'MAM_PASSWORD': 'pass'
        }):
            with patch('audiobook_gap_analyzer.qbittorrentapi.Client'):
                analyzer = AudiobookGapAnalyzer()

        await analyzer._scan_audiobookshelf_library()

        # Should not crash, but library should be empty
        assert len(analyzer.library_books) == 0


def test_state_file_creation():
    """Test that state file is created on save."""
    with patch.dict('os.environ', {
        'ABS_URL': 'http://test:13378',
        'ABS_TOKEN': 'token',
        'MAM_USERNAME': 'user',
        'MAM_PASSWORD': 'pass'
    }):
        with patch('audiobook_gap_analyzer.qbittorrentapi.Client'):
            analyzer = AudiobookGapAnalyzer()
            # Use a test-specific state file
            analyzer.state_file = Path("test_gap_analyzer_state.json")

            analyzer._save_state()

            assert analyzer.state_file.exists()

            # Cleanup
            analyzer.state_file.unlink()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
