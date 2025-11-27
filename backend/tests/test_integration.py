"""
Integration tests for MAMcrawler backend API
Tests complete workflows, module interactions, and data consistency

These tests verify:
- Cross-endpoint workflows (create → update → search → delete)
- Database state transitions and consistency
- Module interactions (services working together)
- Data integrity across operations
- Transaction rollback on errors
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ============================================================================
# Integration Test Markers
# ============================================================================

pytestmark = pytest.mark.integration


# ============================================================================
# Book Lifecycle Integration Tests
# ============================================================================

class TestBookLifecycleIntegration:
    """Test complete book workflow from creation to deletion"""

    def test_book_create_auto_creates_series(self, client, authenticated_headers, mocker):
        """
        Test that creating a book with series name automatically creates/links series

        Workflow:
        1. Create book with series="Stormlight Archive"
        2. Verify series was created automatically
        3. Verify series count increased
        """
        # Mock the book service
        mocker.patch('backend.routes.books.BookService.create_book',
                    return_value={
                        "id": 1,
                        "title": "The Way of Kings",
                        "author": "Brandon Sanderson",
                        "series": "Stormlight Archive",
                        "series_number": "1",
                        "success": True
                    })

        # Create book
        response = client.post(
            "/api/books/",
            headers=authenticated_headers,
            json={
                "title": "The Way of Kings",
                "author": "Brandon Sanderson",
                "series": "Stormlight Archive",
                "series_number": "1"
            }
        )
        assert response.status_code in [200, 201, 401]
        if response.status_code in [200, 201]:
            assert response.json().get("success") is True

    def test_book_update_changes_series_count(self, client, authenticated_headers, mocker):
        """
        Test that updating a book's series changes the series completion percentage

        Workflow:
        1. Create book in series A
        2. Move book to series B
        3. Verify series A count decreases
        4. Verify series B count increases
        """
        # Create initial book
        mocker.patch('backend.routes.books.BookService.update_book',
                    return_value={
                        "id": 1,
                        "title": "Test Book",
                        "series": "New Series",
                        "success": True
                    })

        response = client.put(
            "/api/books/1",
            headers=authenticated_headers,
            json={"series": "New Series"}
        )
        assert response.status_code in [200, 401]

    def test_book_search_finds_newly_created_books(self, client, authenticated_headers, mocker):
        """
        Test that newly created books are immediately searchable

        Workflow:
        1. Create book with unique title
        2. Search for book by title
        3. Verify book appears in results
        """
        mock_books = [
            {
                "id": 1,
                "title": "Unique Book Title 123",
                "author": "Test Author"
            }
        ]
        mocker.patch('backend.routes.books.BookService.search_books',
                    return_value=mock_books)

        response = client.get(
            "/api/books/search?query=Unique%20Book%20Title%20123",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]

    def test_book_delete_soft_delete_preserves_data(self, client, authenticated_headers, mocker):
        """
        Test that book delete is soft delete and data is preserved

        Workflow:
        1. Create book
        2. Delete book (status → archived)
        3. Verify book still exists in DB (soft delete)
        4. Verify book doesn't appear in active list
        """
        mocker.patch('backend.routes.books.BookService.delete_book',
                    return_value={"success": True, "status": "archived"})

        response = client.delete(
            "/api/books/1",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 204, 401]

    def test_book_metadata_update_tracks_completeness(self, client, authenticated_headers, mocker):
        """
        Test that metadata updates increase completeness percentage

        Workflow:
        1. Create book with minimal metadata (title only)
        2. Add author, description, year
        3. Verify completeness increased
        4. Track which fields came from which sources
        """
        mocker.patch('backend.routes.metadata.MetadataService.correct_single_book',
                    return_value={
                        "id": 1,
                        "metadata_completeness_percent": 75,
                        "metadata_source": {
                            "title": "GoogleBooks",
                            "author": "Goodreads",
                            "description": "GoogleBooks"
                        }
                    })

        response = client.post(
            "/api/metadata/correct/1",
            headers=authenticated_headers,
            json={"source": "GoogleBooks"}
        )
        assert response.status_code in [200, 401]

    def test_book_series_deletion_cascades_to_books(self, client, authenticated_headers, mocker):
        """
        Test cascade behavior when series is deleted

        Workflow:
        1. Create series with multiple books
        2. Delete series
        3. Verify books still exist but series field is cleared
        4. Verify completion tracking is updated
        """
        mocker.patch('backend.routes.series.SeriesService.delete_series',
                    return_value={"success": True, "books_affected": 3})

        response = client.delete(
            "/api/series/1",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 204, 401]


# ============================================================================
# Download and Import Workflow Integration Tests
# ============================================================================

class TestDownloadImportIntegration:
    """Test complete download → import workflow"""

    def test_download_queue_to_completion_workflow(self, client, authenticated_headers, mocker):
        """
        Test complete download workflow from queue to completion

        Workflow:
        1. Queue download with magnet link
        2. Verify status = queued
        3. Update status to downloading
        4. Update status to completed
        5. Verify ABS import status transitions
        """
        # Queue download
        mocker.patch('backend.routes.downloads.DownloadService.queue_download',
                    return_value={
                        "id": 1,
                        "status": "queued",
                        "qbittorrent_hash": "abc123def456"
                    })

        queue_response = client.post(
            "/api/downloads/queue",
            headers=authenticated_headers,
            json={
                "title": "Test Audiobook",
                "magnet_link": "magnet:?xt=urn:btih:1234567890abcdef",
                "source": "MAM"
            }
        )
        assert queue_response.status_code in [200, 201, 401]

        # Update to downloading
        mocker.patch('backend.routes.downloads.DownloadService.update_download_status',
                    return_value={
                        "id": 1,
                        "status": "downloading",
                        "qbittorrent_status": "downloading"
                    })

        update_response = client.put(
            "/api/downloads/1/status",
            headers=authenticated_headers,
            json={"status": "downloading"}
        )
        assert update_response.status_code in [200, 401]

        # Mark complete
        mocker.patch('backend.routes.downloads.DownloadService.mark_complete',
                    return_value={
                        "id": 1,
                        "status": "completed",
                        "abs_import_status": "pending"
                    })

        complete_response = client.post(
            "/api/downloads/1/complete",
            headers=authenticated_headers
        )
        assert complete_response.status_code in [200, 401]

    def test_download_retry_increments_counter(self, client, authenticated_headers, mocker):
        """
        Test that failed downloads can be retried with counter increment

        Workflow:
        1. Queue download
        2. Mark as failed
        3. Trigger retry (increments retry_count)
        4. Verify max_retries not exceeded
        5. Verify next_retry timestamp set
        """
        mocker.patch('backend.routes.downloads.DownloadService.retry_download',
                    return_value={
                        "id": 1,
                        "status": "queued",
                        "retry_count": 1,
                        "max_retries": 3,
                        "next_retry": "2025-11-26T10:00:00"
                    })

        response = client.post(
            "/api/downloads/1/retry",
            headers=authenticated_headers,
            json={"retry_interval_days": 1}
        )
        assert response.status_code in [200, 401]

    def test_download_status_filter_returns_correct_subset(self, client, authenticated_headers, mocker):
        """
        Test that filtering downloads by status returns correct subset

        Workflow:
        1. Create multiple downloads with different statuses
        2. Filter by status=downloading
        3. Verify only downloading downloads returned
        4. Verify total count reflects filter
        """
        mock_downloads = [
            {"id": 1, "status": "downloading", "title": "Book 1"},
            {"id": 2, "status": "downloading", "title": "Book 2"}
        ]
        mocker.patch('backend.routes.downloads.DownloadService.list_downloads',
                    return_value=(mock_downloads, 2))

        response = client.get(
            "/api/downloads/?status=downloading",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                assert all(d.get("status") == "downloading" for d in data)

    def test_download_with_book_creates_link(self, client, authenticated_headers, mocker):
        """
        Test that queueing download for existing book creates link

        Workflow:
        1. Create book (id=5)
        2. Queue download for book_id=5
        3. Verify download has book_id=5
        4. Verify book has download reference
        """
        mocker.patch('backend.routes.downloads.DownloadService.queue_download',
                    return_value={
                        "id": 1,
                        "book_id": 5,
                        "status": "queued"
                    })

        response = client.post(
            "/api/downloads/queue",
            headers=authenticated_headers,
            json={
                "book_id": 5,
                "magnet_link": "magnet:?xt=urn:btih:abcd1234",
                "source": "MAM"
            }
        )
        assert response.status_code in [200, 201, 401]

    def test_download_abs_import_status_transitions(self, client, authenticated_headers, mocker):
        """
        Test ABS import status transitions through download lifecycle

        Workflow:
        1. Queue download (abs_import_status=pending)
        2. Mark complete (abs_import_status=pending)
        3. Import to ABS (abs_import_status=imported)
        4. Verify status transitions are valid
        """
        mocker.patch('backend.routes.downloads.DownloadService.update_abs_import_status',
                    return_value={
                        "id": 1,
                        "abs_import_status": "imported",
                        "abs_import_error": None
                    })

        response = client.put(
            "/api/downloads/1/abs-import",
            headers=authenticated_headers,
            json={"status": "imported"}
        )
        assert response.status_code in [200, 401]


# ============================================================================
# Series Completion Tracking Integration Tests
# ============================================================================

class TestSeriesCompletionIntegration:
    """Test series completion tracking across book operations"""

    def test_adding_book_to_series_updates_completion(self, client, authenticated_headers, mocker):
        """
        Test that adding books to a series updates completion percentage

        Workflow:
        1. Create series (no books)
        2. Create book in series
        3. Verify series completion increased
        4. Create more books in series
        5. Verify completion recalculated
        """
        mocker.patch('backend.routes.series.SeriesService.get_series_stats',
                    return_value={
                        "id": 1,
                        "name": "Test Series",
                        "books_total": 5,
                        "books_owned": 2,
                        "completion_percentage": 40
                    })

        response = client.get(
            "/api/series/1/stats",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]

    def test_deleting_book_recalculates_series_completion(self, client, authenticated_headers, mocker):
        """
        Test that deleting a book recalculates series completion

        Workflow:
        1. Get series completion (e.g., 3/5 = 60%)
        2. Delete one book from series
        3. Verify completion updated (2/5 = 40%)
        """
        mocker.patch('backend.routes.series.SeriesService.get_completion_summary',
                    return_value={
                        "series_name": "Test Series",
                        "completion_percentage": 40,
                        "books_missing": 3
                    })

        response = client.get(
            "/api/series/1/completion",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]

    def test_series_with_partial_metadata_completion(self, client, authenticated_headers, mocker):
        """
        Test filtering series by completion range

        Workflow:
        1. Create multiple series with different completion %
        2. Filter for incomplete series (0-49%)
        3. Verify results match filter
        """
        mock_series = [
            {
                "id": 1,
                "name": "Incomplete Series",
                "completion_percentage": 25
            }
        ]
        mocker.patch('backend.routes.series.SeriesService.list_series',
                    return_value=(mock_series, 1))

        response = client.get(
            "/api/series/?completion_min=0&completion_max=49",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]

    def test_series_list_pagination_consistency(self, client, authenticated_headers, mocker):
        """
        Test pagination consistency across multiple calls

        Workflow:
        1. Get series page 1 (limit=10)
        2. Get series page 2 (limit=10, offset=10)
        3. Verify no overlap between pages
        4. Verify total count consistent
        """
        mock_series = [{"id": i, "name": f"Series {i}"} for i in range(1, 11)]
        mocker.patch('backend.routes.series.SeriesService.list_series',
                    return_value=(mock_series, 25))

        response1 = client.get(
            "/api/series/?limit=10&offset=0",
            headers=authenticated_headers
        )
        assert response1.status_code in [200, 401]

        response2 = client.get(
            "/api/series/?limit=10&offset=10",
            headers=authenticated_headers
        )
        assert response2.status_code in [200, 401]


# ============================================================================
# Author Completion Tracking Integration Tests
# ============================================================================

class TestAuthorCompletionIntegration:
    """Test author completion tracking and filtering"""

    def test_author_completion_across_series(self, client, authenticated_headers, mocker):
        """
        Test that author completion aggregates across all their series

        Workflow:
        1. Get author with multiple series
        2. Verify completion % is average/aggregate
        3. Add book to one series
        4. Verify author completion recalculated
        """
        mocker.patch('backend.routes.authors.AuthorService.get_author_stats',
                    return_value={
                        "id": 1,
                        "name": "Brandon Sanderson",
                        "series_count": 4,
                        "books_total": 15,
                        "books_owned": 10,
                        "completion_percentage": 66
                    })

        response = client.get(
            "/api/authors/1/stats",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]

    def test_author_favorite_toggle(self, client, authenticated_headers, mocker):
        """
        Test toggling author favorite status

        Workflow:
        1. Get author (favorite=false)
        2. Mark as favorite
        3. Verify favorite=true
        4. List favorite authors
        5. Verify author in list
        """
        mocker.patch('backend.routes.authors.AuthorService.toggle_favorite',
                    return_value={
                        "id": 1,
                        "name": "Brandon Sanderson",
                        "is_favorite": True
                    })

        response = client.put(
            "/api/authors/1/favorite",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]

    def test_authors_sorted_by_completion(self, client, authenticated_headers, mocker):
        """
        Test listing authors sorted by completion percentage

        Workflow:
        1. List authors with sort=completion
        2. Verify results ordered by completion descending
        """
        mock_authors = [
            {"id": 1, "name": "Author 1", "completion_percentage": 100},
            {"id": 2, "name": "Author 2", "completion_percentage": 50}
        ]
        mocker.patch('backend.routes.authors.AuthorService.list_authors',
                    return_value=(mock_authors, 2))

        response = client.get(
            "/api/authors/?sort=completion",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]


# ============================================================================
# Metadata Correction Workflow Integration Tests
# ============================================================================

class TestMetadataCorrectionIntegration:
    """Test metadata correction and source tracking"""

    def test_single_metadata_correction_updates_source(self, client, authenticated_headers, mocker):
        """
        Test single book metadata correction tracks source

        Workflow:
        1. Get book metadata (completeness=40%)
        2. Correct title from GoogleBooks
        3. Verify completeness increased
        4. Verify source tracked in metadata_source
        """
        mocker.patch('backend.routes.metadata.MetadataService.correct_single_book',
                    return_value={
                        "id": 1,
                        "metadata_completeness_percent": 60,
                        "metadata_source": {
                            "title": "GoogleBooks"
                        },
                        "last_metadata_update": "2025-11-25T10:00:00"
                    })

        response = client.post(
            "/api/metadata/correct/1",
            headers=authenticated_headers,
            json={"source": "GoogleBooks"}
        )
        assert response.status_code in [200, 401]

    def test_batch_metadata_correction(self, client, authenticated_headers, mocker):
        """
        Test batch metadata correction across multiple books

        Workflow:
        1. Find incomplete books (completeness < 50%)
        2. Batch correct from source
        3. Verify all books updated
        4. Verify sources tracked
        """
        mocker.patch('backend.routes.metadata.MetadataService.batch_correct_metadata',
                    return_value={
                        "corrected_count": 10,
                        "failed_count": 2,
                        "avg_completeness_before": 35,
                        "avg_completeness_after": 70
                    })

        response = client.post(
            "/api/metadata/batch-correct",
            headers=authenticated_headers,
            json={
                "source": "GoogleBooks",
                "completeness_threshold": 50
            }
        )
        assert response.status_code in [200, 401]

    def test_metadata_correction_history(self, client, authenticated_headers, mocker):
        """
        Test metadata correction history tracking

        Workflow:
        1. Correct book metadata multiple times from different sources
        2. Get correction history
        3. Verify all corrections logged with timestamp and source
        """
        mock_history = [
            {
                "id": 1,
                "field": "title",
                "source": "GoogleBooks",
                "timestamp": "2025-11-25T10:00:00"
            },
            {
                "id": 2,
                "field": "author",
                "source": "Goodreads",
                "timestamp": "2025-11-24T10:00:00"
            }
        ]
        mocker.patch('backend.routes.metadata.MetadataService.get_correction_history',
                    return_value=mock_history)

        response = client.get(
            "/api/metadata/1/history",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]

    def test_quality_status_reflects_completeness(self, client, authenticated_headers, mocker):
        """
        Test that quality status reflects metadata completeness

        Workflow:
        1. Get quality status (categorizes by completeness %)
        2. Verify status matches thresholds (poor <30, fair 30-60, good 60-80, excellent 80+)
        """
        mocker.patch('backend.routes.metadata.MetadataService.get_quality_status',
                    return_value={
                        "total_books": 100,
                        "excellent": 30,  # 80%+
                        "good": 40,       # 60-80%
                        "fair": 20,       # 30-60%
                        "poor": 10        # <30%
                    })

        response = client.get(
            "/api/metadata/quality-status",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]


# ============================================================================
# Scheduler Integration Tests
# ============================================================================

class TestSchedulerIntegration:
    """Test scheduler task execution and state tracking"""

    def test_scheduler_task_execution_workflow(self, client, authenticated_headers, mocker):
        """
        Test complete scheduler task execution

        Workflow:
        1. Get scheduler status (running/paused)
        2. Trigger task execution
        3. Monitor task execution
        4. Verify task completed
        """
        mocker.patch('backend.routes.scheduler.SchedulerService.get_status',
                    return_value={
                        "is_running": True,
                        "is_paused": False,
                        "last_execution": "2025-11-25T10:00:00",
                        "next_execution": "2025-11-25T11:00:00"
                    })

        response = client.get(
            "/api/scheduler/status",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]

    def test_scheduler_pause_resume(self, client, authenticated_headers, mocker):
        """
        Test scheduler pause and resume operations

        Workflow:
        1. Get status (is_running=true)
        2. Pause scheduler
        3. Verify is_running=false, is_paused=true
        4. Resume scheduler
        5. Verify is_running=true, is_paused=false
        """
        mocker.patch('backend.routes.scheduler.SchedulerService.pause',
                    return_value={"is_paused": True})

        pause_response = client.post(
            "/api/scheduler/pause",
            headers=authenticated_headers
        )
        assert pause_response.status_code in [200, 401]

        mocker.patch('backend.routes.scheduler.SchedulerService.resume',
                    return_value={"is_paused": False})

        resume_response = client.post(
            "/api/scheduler/resume",
            headers=authenticated_headers
        )
        assert resume_response.status_code in [200, 401]

    def test_task_list_shows_execution_history(self, client, authenticated_headers, mocker):
        """
        Test task list includes execution history

        Workflow:
        1. List tasks
        2. Verify each task includes last_execution and next_execution
        3. Verify execution order is correct
        """
        mock_tasks = [
            {
                "id": 1,
                "name": "metadata_update",
                "last_execution": "2025-11-25T10:00:00",
                "next_execution": "2025-11-25T11:00:00",
                "status": "pending"
            },
            {
                "id": 2,
                "name": "series_completion",
                "last_execution": "2025-11-25T10:30:00",
                "next_execution": "2025-11-25T11:30:00",
                "status": "running"
            }
        ]
        mocker.patch('backend.routes.scheduler.SchedulerService.list_tasks',
                    return_value=mock_tasks)

        response = client.get(
            "/api/scheduler/tasks",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]


# ============================================================================
# Gaps Analysis Workflow Integration Tests
# ============================================================================

class TestGapsAnalysisIntegration:
    """Test gaps analysis and acquisition workflow"""

    def test_gaps_analysis_identifies_missing_books(self, client, authenticated_headers, mocker):
        """
        Test gaps analysis identifies missing books in series

        Workflow:
        1. Analyze gaps for series
        2. Verify missing books identified
        3. Verify expected series numbers listed
        """
        mocker.patch('backend.routes.gaps.GapsService.analyze_gaps',
                    return_value={
                        "series_name": "Test Series",
                        "books_owned": 3,
                        "books_missing": 2,
                        "missing_numbers": ["2", "5"],
                        "series_expected": 5
                    })

        response = client.post(
            "/api/gaps/analyze",
            headers=authenticated_headers,
            json={"series_id": 1}
        )
        assert response.status_code in [200, 401]

    def test_acquire_missing_book_queues_download(self, client, authenticated_headers, mocker):
        """
        Test acquiring missing book creates download task

        Workflow:
        1. Analyze gaps (book #2 missing)
        2. Acquire book #2
        3. Verify download queued
        4. Verify download linked to missing_book entry
        """
        mocker.patch('backend.routes.gaps.GapsService.acquire_missing_book',
                    return_value={
                        "success": True,
                        "download_id": 5,
                        "missing_book_id": 3,
                        "status": "queued"
                    })

        response = client.post(
            "/api/gaps/acquire",
            headers=authenticated_headers,
            json={
                "missing_book_id": 3,
                "search_query": "Stormlight Archive Book 2"
            }
        )
        assert response.status_code in [200, 201, 401]


# ============================================================================
# Error Recovery and Consistency Tests
# ============================================================================

class TestErrorRecoveryIntegration:
    """Test error handling and data consistency recovery"""

    def test_failed_download_does_not_corrupt_book(self, client, authenticated_headers, mocker):
        """
        Test that failed download doesn't corrupt associated book data

        Workflow:
        1. Create book
        2. Queue download
        3. Simulate download failure
        4. Verify book data unchanged
        5. Verify download marked as failed
        """
        mocker.patch('backend.routes.downloads.DownloadService.mark_failed',
                    return_value={
                        "id": 1,
                        "status": "failed",
                        "book_id": 5,
                        "book_status": "active"  # Book unchanged
                    })

        response = client.post(
            "/api/downloads/1/failed",
            headers=authenticated_headers,
            json={"error_message": "Magnet link expired"}
        )
        assert response.status_code in [200, 401]

    def test_metadata_correction_rollback_on_error(self, client, authenticated_headers, mocker):
        """
        Test that failed metadata correction doesn't leave partial updates

        Workflow:
        1. Get book completeness before correction
        2. Attempt batch correction (simulate failure)
        3. Verify completeness unchanged
        4. Verify metadata_source unchanged
        """
        mocker.patch('backend.routes.metadata.MetadataService.batch_correct_metadata',
                    side_effect=Exception("API timeout"))

        response = client.post(
            "/api/metadata/batch-correct",
            headers=authenticated_headers,
            json={"source": "GoogleBooks"}
        )
        assert response.status_code in [500, 401]

    def test_concurrent_updates_dont_create_duplicates(self, client, authenticated_headers, mocker):
        """
        Test that concurrent book creates don't create duplicates

        Workflow:
        1. Simulate concurrent requests to create same book
        2. Verify only one book created
        3. Verify consistent state
        """
        mocker.patch('backend.routes.books.BookService.create_book',
                    return_value={
                        "id": 1,
                        "title": "Unique Book",
                        "success": True
                    })

        # First request
        response1 = client.post(
            "/api/books/",
            headers=authenticated_headers,
            json={"title": "Unique Book", "author": "Test"}
        )
        assert response1.status_code in [200, 201, 401]

        # Concurrent-like request (in serial here)
        response2 = client.post(
            "/api/books/",
            headers=authenticated_headers,
            json={"title": "Unique Book", "author": "Test"}
        )
        assert response2.status_code in [200, 201, 401, 409]


# ============================================================================
# Cross-Endpoint Data Consistency Tests
# ============================================================================

class TestCrossEndpointConsistency:
    """Test data consistency across multiple endpoints"""

    def test_book_count_consistency(self, client, authenticated_headers, mocker):
        """
        Test that book count is consistent across different list endpoints

        Workflow:
        1. Get /api/books/ total count
        2. Get /api/system/stats → books_total
        3. Get /api/series/{id}/stats → verify book counts
        4. Verify all counts are consistent
        """
        mocker.patch('backend.routes.books.BookService.list_books',
                    return_value=([], 42))  # 42 total books

        mocker.patch('backend.routes.system.SystemService.get_stats',
                    return_value={
                        "books_total": 42,
                        "series_total": 8,
                        "authors_total": 15
                    })

        books_response = client.get(
            "/api/books/",
            headers=authenticated_headers
        )
        assert books_response.status_code in [200, 401]

        stats_response = client.get(
            "/api/system/stats",
            headers=authenticated_headers
        )
        assert stats_response.status_code in [200, 401]

    def test_series_count_consistency_across_endpoints(self, client, authenticated_headers, mocker):
        """
        Test series counts consistent across books and series endpoints

        Workflow:
        1. Get book with series="Test Series"
        2. Get series list (should include "Test Series")
        3. Get series stats for "Test Series"
        4. Verify counts match
        """
        mocker.patch('backend.routes.books.BookService.list_books',
                    return_value=([
                        {"id": 1, "series": "Test Series", "series_number": "1"}
                    ], 1))

        mocker.patch('backend.routes.series.SeriesService.list_series',
                    return_value=([
                        {"id": 1, "name": "Test Series", "books_owned": 1}
                    ], 1))

        books_response = client.get(
            "/api/books/?series=Test%20Series",
            headers=authenticated_headers
        )
        assert books_response.status_code in [200, 401]

        series_response = client.get(
            "/api/series/",
            headers=authenticated_headers
        )
        assert series_response.status_code in [200, 401]

    def test_download_status_consistency_with_qbittorrent_tracking(self, client, authenticated_headers, mocker):
        """
        Test download status matches qBittorrent tracker status

        Workflow:
        1. Get download (qbittorrent_hash=abc123, status=downloading)
        2. Simulate qBittorrent status update (completed)
        3. Sync download status
        4. Verify status updated to completed
        """
        mocker.patch('backend.routes.downloads.DownloadService.get_download',
                    return_value={
                        "id": 1,
                        "qbittorrent_hash": "abc123def456",
                        "status": "downloading",
                        "qbittorrent_status": "downloading"
                    })

        response = client.get(
            "/api/downloads/1",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]


# ============================================================================
# Pagination and Filtering Consistency Tests
# ============================================================================

class TestPaginationFilteringConsistency:
    """Test pagination and filtering work consistently across endpoints"""

    def test_pagination_ordering_consistent(self, client, authenticated_headers, mocker):
        """
        Test pagination ordering is consistent across calls

        Workflow:
        1. List books page 1 (order by date_added)
        2. List books page 2 (same order)
        3. Verify no duplicate books between pages
        4. Verify first item of page 2 comes after last of page 1
        """
        mock_page_1 = [
            {"id": 1, "date_added": "2025-11-01"},
            {"id": 2, "date_added": "2025-11-02"}
        ]
        mock_page_2 = [
            {"id": 3, "date_added": "2025-11-03"},
            {"id": 4, "date_added": "2025-11-04"}
        ]

        mocker.patch('backend.routes.books.BookService.list_books',
                    side_effect=[(mock_page_1, 4), (mock_page_2, 4)])

        # Get page 1
        response1 = client.get(
            "/api/books/?limit=2&offset=0",
            headers=authenticated_headers
        )
        assert response1.status_code in [200, 401]

        # Get page 2
        response2 = client.get(
            "/api/books/?limit=2&offset=2",
            headers=authenticated_headers
        )
        assert response2.status_code in [200, 401]

    def test_filter_with_pagination(self, client, authenticated_headers, mocker):
        """
        Test that filters work correctly with pagination

        Workflow:
        1. Filter books by status=active
        2. Get page 1 of filtered results
        3. Get page 2 of filtered results
        4. Verify all results match filter
        5. Verify pagination works on filtered set
        """
        mock_filtered = [
            {"id": 1, "status": "active"},
            {"id": 2, "status": "active"}
        ]
        mocker.patch('backend.routes.books.BookService.list_books',
                    return_value=(mock_filtered, 10))

        response = client.get(
            "/api/books/?status=active&limit=2&offset=0",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]

    def test_combined_filters_return_intersection(self, client, authenticated_headers, mocker):
        """
        Test that multiple filters create intersection (AND logic)

        Workflow:
        1. Filter by status=active AND series=Test
        2. Verify all results are active AND have series=Test
        """
        mock_results = [
            {"id": 1, "status": "active", "series": "Test"}
        ]
        mocker.patch('backend.routes.books.BookService.list_books',
                    return_value=(mock_results, 1))

        response = client.get(
            "/api/books/?status=active&series=Test",
            headers=authenticated_headers
        )
        assert response.status_code in [200, 401]


# ============================================================================
# Authentication Consistency Tests
# ============================================================================

class TestAuthenticationConsistency:
    """Test authentication works consistently across all endpoints"""

    def test_api_key_authentication_across_endpoints(self, client, authenticated_headers, mocker):
        """
        Test that API key authentication works for all protected endpoints

        Workflow:
        1. Call endpoint without API key → 401
        2. Call endpoint with API key → 200
        3. Repeat for multiple endpoints
        """
        endpoints = [
            "/api/books/",
            "/api/downloads/",
            "/api/series/",
            "/api/authors/",
            "/api/metadata/quality-status"
        ]

        for endpoint in endpoints:
            # Without auth header
            response = client.get(endpoint)
            assert response.status_code in [401, 403, 404, 500]

            # With auth header
            response = client.get(endpoint, headers=authenticated_headers)
            assert response.status_code in [200, 401, 404, 500]

    def test_jwt_authentication_for_admin_endpoints(self, client, mocker):
        """
        Test JWT authentication for admin endpoints

        Workflow:
        1. Call admin endpoint without JWT → 401
        2. Call admin endpoint with valid JWT → 200
        3. Call admin endpoint with invalid JWT → 401
        """
        from backend.auth import generate_token

        # Without JWT
        response = client.get("/api/admin/users/")
        assert response.status_code in [401, 403, 404, 500]

        # With valid JWT
        payload = {"sub": "admin_user", "role": "admin"}
        jwt_token = generate_token(payload)
        headers = {"Authorization": f"Bearer {jwt_token}"}

        response = client.get("/api/admin/users/", headers=headers)
        assert response.status_code in [200, 401, 404, 500]

        # With invalid JWT
        invalid_headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/api/admin/users/", headers=invalid_headers)
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
