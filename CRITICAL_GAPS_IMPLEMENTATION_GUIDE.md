# CRITICAL GAPS IMPLEMENTATION GUIDE

**Created**: 2025-11-21
**Purpose**: Detailed implementation strategy for 4 critical specification gaps
**Status**: Ready for immediate implementation
**Total Effort**: 40 developer hours
**Priority**: CRITICAL (blocks production deployment)

---

## OVERVIEW

The MAMcrawler system has 4 critical gaps preventing 100% specification compliance. Each gap is isolated, well-defined, and has clear implementation paths. This guide provides step-by-step implementation instructions for each gap.

**Gap Priority**:
1. **GAP 1** - Auto-trigger metadata scan (8 hours) - CRITICAL
2. **GAP 4** - Auto-trigger integrity check (12 hours) - CRITICAL
3. **GAP 2** - Narrator detection pipeline (10 hours) - HIGH
4. **GAP 3** - Drift correction algorithm (10 hours) - HIGH

---

## GAP 1: Auto-Trigger Metadata Scan After Download Completion

### Specification Requirement
```
When a new audiobook appears in Audiobookshelf (i.e., qBittorrent marks
torrent complete), perform a **full scan** (Section 14). After scanning,
update metadata using verified and Goodreads data.
```

### Current State Analysis

**What Exists**:
- ✅ `backend/services/metadata_service.py` - Full scan capability with `full_scan()` method
- ✅ `backend/services/download_service.py` - Download management
- ✅ `backend/routes/downloads.py` - Download API endpoints
- ✅ `backend/integrations/qbittorrent_client.py` - qBittorrent integration
- ✅ `backend/models/download.py` - Download model with status tracking

**What's Missing**:
- ❌ Webhook/callback trigger when torrent completes
- ❌ Event listener for qBittorrent completion
- ❌ Auto-invocation of metadata scan
- ❌ Metadata update after scan completion

### Implementation Strategy

#### Step 1: Add Event Handler in Download Service

**File**: `backend/services/download_service.py`

**Current structure**:
```python
class DownloadService:
    async def queue_download(self, ...):
        # Download queuing logic

    async def retry_failed(self, ...):
        # Retry logic
```

**Required additions**:
```python
from backend.services.metadata_service import MetadataService

class DownloadService:
    def __init__(self, db_session, metadata_service: MetadataService):
        self.db = db_session
        self.metadata_service = metadata_service

    async def on_download_completed(self, download_id: int, torrent_name: str):
        """
        Triggered when qBittorrent marks torrent as complete.

        Performs:
        1. Verify download record in database
        2. Trigger full metadata scan
        3. Update book metadata from Goodreads
        4. Mark download as fully processed
        """
        # 1. Load download record
        download = self.db.query(Download).filter(
            Download.id == download_id
        ).first()

        if not download:
            raise ValueError(f"Download {download_id} not found")

        # 2. Update status to processing
        download.status = "metadata_processing"
        self.db.commit()

        # 3. Trigger metadata scan
        try:
            book = download.book
            scan_result = await self.metadata_service.full_scan(
                book_id=book.id,
                source="qbittorrent_completion"
            )

            # 4. Update from Goodreads
            enriched = await self.metadata_service.enrich_from_goodreads(
                book_id=book.id
            )

            # 5. Mark complete
            download.status = "seeding"
            download.metadata_processed_at = datetime.utcnow()
            self.db.commit()

            return {"status": "success", "scan_result": scan_result}

        except Exception as e:
            download.status = "metadata_error"
            download.error_message = str(e)
            self.db.commit()
            raise
```

#### Step 2: Add Polling/Monitoring in qBittorrent Service

**File**: `backend/services/qbittorrent_monitor_service.py`

**Current structure**:
```python
class QBittorrentMonitorService:
    async def monitor_all(self):
        # Monitor all torrents
```

**Required additions**:
```python
class QBittorrentMonitorService:
    def __init__(self, db_session, qbit_client, download_service):
        self.db = db_session
        self.qbit_client = qbit_client
        self.download_service = download_service
        self.last_checked_torrents = {}

    async def monitor_all(self):
        """Enhanced monitoring that detects completion events"""
        torrents = self.qbit_client.get_torrents()

        for torrent in torrents:
            torrent_name = torrent['name']
            torrent_hash = torrent['hash']
            current_state = torrent['state']

            # Check if torrent was downloading and is now complete
            previous_state = self.last_checked_torrents.get(torrent_hash, {}).get('state')

            if (previous_state in ['downloading', 'forcedDL'] and
                current_state in ['uploading', 'forcedUP', 'allocating']):

                # Torrent just completed! Trigger metadata scan
                await self._handle_completion_event(torrent_name, torrent_hash)

            # Update state tracking
            self.last_checked_torrents[torrent_hash] = {
                'state': current_state,
                'name': torrent_name,
                'checked_at': datetime.utcnow()
            }

    async def _handle_completion_event(self, torrent_name: str, torrent_hash: str):
        """Handle completion by finding associated download and scanning metadata"""
        # Find download by torrent name
        download = self.db.query(Download).filter(
            Download.torrent_name == torrent_name
        ).first()

        if download:
            await self.download_service.on_download_completed(
                download_id=download.id,
                torrent_name=torrent_name
            )
```

#### Step 3: Add API Endpoint for Manual Trigger

**File**: `backend/routes/downloads.py`

**Add endpoint**:
```python
@router.post("/api/downloads/{download_id}/trigger-scan")
async def trigger_metadata_scan(
    download_id: int,
    db_session: Session = Depends(get_db),
    current_user = Depends(check_token)
):
    """
    Manually trigger metadata scan for a completed download.
    Also useful for retrying failed scans.
    """
    download_service = DownloadService(db_session, MetadataService(db_session))

    result = await download_service.on_download_completed(
        download_id=download_id,
        torrent_name=None  # Will be loaded from database
    )

    return {
        "status": "success",
        "message": f"Metadata scan triggered for download {download_id}",
        "scan_result": result
    }
```

#### Step 4: Integration with Scheduled Monitor Task

**File**: `backend/schedulers/tasks.py`

**Modify existing task**:
```python
@scheduler.scheduled_job('interval', seconds=60, id='qbittorrent_monitor_enhanced')
async def qbittorrent_monitor_task_enhanced():
    """
    Monitor qBittorrent every 60 seconds.
    Detects completion events and triggers metadata scans.
    """
    try:
        qbit_service = QBittorrentMonitorService(
            db_session=SessionLocal(),
            qbit_client=QBittorrentClient(...),
            download_service=DownloadService(...)
        )

        await qbit_service.monitor_all()

    except Exception as e:
        logger.error(f"qBittorrent monitor task failed: {e}")
```

### Implementation Checklist

- [ ] Add `on_download_completed()` method to `DownloadService`
- [ ] Add completion detection to `QBittorrentMonitorService.monitor_all()`
- [ ] Add `_handle_completion_event()` helper method
- [ ] Add `/api/downloads/{id}/trigger-scan` endpoint
- [ ] Test with manual download completion
- [ ] Test with simulated qBittorrent events
- [ ] Verify metadata updates after scan
- [ ] Monitor for missed completion events

### Testing Strategy

```python
# Test file: tests/test_download_auto_scan.py

@pytest.mark.asyncio
async def test_auto_scan_on_completion():
    """Test that metadata scan is triggered when download completes"""
    # 1. Create download record
    download = Download(...)
    db.add(download)
    db.commit()

    # 2. Trigger completion event
    await download_service.on_download_completed(
        download_id=download.id,
        torrent_name=download.torrent_name
    )

    # 3. Verify metadata was updated
    updated_book = db.query(Book).get(download.book_id)
    assert updated_book.metadata_completeness_percent > 0
    assert updated_book.narrator is not None

@pytest.mark.asyncio
async def test_completion_detection_in_monitor():
    """Test that monitor service detects completion state change"""
    # 1. Set initial state (downloading)
    monitor_service.last_checked_torrents['hash123'] = {'state': 'downloading'}

    # 2. Simulate completion event
    mock_torrents = [{'name': 'test.torrent', 'hash': 'hash123', 'state': 'uploading'}]

    # 3. Run monitor
    await monitor_service.monitor_all()

    # 4. Verify completion was detected
    # (Check that on_download_completed was called)
```

### Success Criteria

1. ✅ Download completion detected within 60 seconds
2. ✅ Metadata scan triggered automatically
3. ✅ Goodreads data fetched and stored
4. ✅ Book fields updated: title, author, narrator, series, description
5. ✅ Download status changed to "seeding"
6. ✅ All operations logged with timestamps

---

## GAP 4: Auto-Trigger Integrity Check After Download

### Specification Requirement
```
After qBittorrent marks complete:
1. Verify file count matches torrent metadata
2. Verify total size matches torrent
3. Confirm audio decodes fully
4. Check duration within 1% tolerance
5. If failure → re-download, trying alternate release if needed
```

### Current State Analysis

**What Exists**:
- ✅ `audiobook_audio_verifier.py` (22 KB) - Complete audio verification
- ✅ `backend/models/download.py` - integrity_status field
- ✅ `backend/services/download_service.py` - Download management
- ✅ File count, size, duration verification in audio verifier

**What's Missing**:
- ❌ Auto-trigger after download completion
- ❌ Failure handling and re-download logic
- ❌ Alternate release selection on failure
- ❌ Integration into completion workflow

### Implementation Strategy

#### Step 1: Convert Audio Verifier to Service

**File**: Create `backend/services/integrity_check_service.py`

```python
from audiobook_audio_verifier import AudiobookVerifier
from typing import Optional, Dict
import asyncio

class IntegrityCheckService:
    """
    Performs post-download integrity verification.

    Checks:
    - File count matches torrent
    - Total size matches torrent
    - Audio files decode without errors
    - Duration within 1% tolerance
    """

    def __init__(self, db_session, qbit_client, abs_client):
        self.db = db_session
        self.qbit_client = qbit_client
        self.abs_client = abs_client
        self.verifier = AudiobookVerifier()

    async def verify_download(
        self,
        download_id: int,
        torrent_hash: str
    ) -> Dict[str, any]:
        """
        Perform full integrity check on completed download.

        Returns:
            {
                "status": "passed" | "failed",
                "file_count_valid": bool,
                "size_valid": bool,
                "audio_valid": bool,
                "duration_valid": bool,
                "errors": [str],
                "files_checked": int
            }
        """
        # 1. Load download record
        download = self.db.query(Download).get(download_id)
        if not download:
            raise ValueError(f"Download {download_id} not found")

        # 2. Get torrent metadata
        torrent = self.qbit_client.get_torrent_info(torrent_hash=torrent_hash)
        if not torrent:
            raise ValueError(f"Torrent {torrent_hash} not found")

        # 3. Get download path
        download_path = torrent['content_path']

        # 4. Run verification
        result = self.verifier.verify_audiobook(
            directory=download_path,
            expected_file_count=torrent['nb_connections'],  # approximate
            expected_total_size=torrent['total_size']
        )

        # 5. Store results
        download.integrity_status = "valid" if result['status'] == "passed" else "corrupt"
        download.integrity_check_results = result
        download.integrity_checked_at = datetime.utcnow()
        self.db.commit()

        return result

    async def handle_integrity_failure(
        self,
        download_id: int
    ) -> Optional[int]:
        """
        Handle failed integrity check.

        Strategy:
        1. Mark current version as corrupt
        2. Find alternate releases of same book
        3. Select next best release using quality rules
        4. Queue new download for alternate
        5. Keep original in qBittorrent (for seeding if useful)

        Returns: New download_id if re-download queued, None if no alternatives
        """
        from backend.services.quality_rules_service import QualityRulesService
        from backend.services.download_service import DownloadService

        # 1. Load original download
        original = self.db.query(Download).get(download_id)
        if not original:
            raise ValueError(f"Download {download_id} not found")

        original.integrity_status = "corrupt"
        original.retry_count = original.retry_count + 1
        self.db.commit()

        # 2. Load book
        book = original.book

        # 3. Find alternate releases from MAM or Prowlarr
        quality_service = QualityRulesService(self.db)
        alternatives = await quality_service.find_alternate_releases(
            title=book.title,
            author=book.author,
            exclude_torrent=original.torrent_name,
            max_results=5
        )

        if not alternatives:
            logger.warning(
                f"No alternate releases found for {book.title} "
                f"after integrity failure"
            )
            return None

        # 4. Select best alternative
        best_alternative = alternatives[0]  # Quality service returns sorted

        # 5. Queue new download
        download_service = DownloadService(self.db)
        new_download = await download_service.queue_download(
            book_id=book.id,
            magnet=best_alternative['magnet'],
            source="integrity_check_retry",
            parent_download_id=download_id  # Track retry chain
        )

        logger.info(
            f"Integrity check failed for download {download_id}. "
            f"Queued alternate: {best_alternative['name']} "
            f"(new download_id: {new_download.id})"
        )

        return new_download.id
```

#### Step 2: Add Integrity Check to Completion Handler

**File**: `backend/services/download_service.py`

**Modify `on_download_completed()` method**:
```python
class DownloadService:

    async def on_download_completed(
        self,
        download_id: int,
        torrent_name: str
    ):
        """
        Triggered when qBittorrent marks torrent as complete.

        Workflow:
        1. Verify download record
        2. Run integrity check
        3. If integrity fails → queue alternate
        4. If integrity passes → trigger metadata scan
        5. Update download status
        """
        download = self.db.query(Download).get(download_id)
        if not download:
            raise ValueError(f"Download {download_id} not found")

        try:
            # 1. Run integrity check
            integrity_service = IntegrityCheckService(
                self.db,
                self.qbit_client,
                self.abs_client
            )

            integrity_result = await integrity_service.verify_download(
                download_id=download_id,
                torrent_hash=download.torrent_hash
            )

            # 2. Handle failure
            if integrity_result['status'] == 'failed':
                new_download_id = await integrity_service.handle_integrity_failure(
                    download_id=download_id
                )

                download.status = "integrity_failed"
                if new_download_id:
                    download.status = "integrity_failed_retrying"
                self.db.commit()

                return {
                    "status": "integrity_failed",
                    "retry_download_id": new_download_id
                }

            # 3. If integrity passes, scan metadata
            download.status = "metadata_processing"
            self.db.commit()

            scan_result = await self.metadata_service.full_scan(
                book_id=download.book_id,
                source="download_completion"
            )

            # 4. Update from Goodreads
            await self.metadata_service.enrich_from_goodreads(
                book_id=download.book_id
            )

            # 5. Mark complete
            download.status = "seeding"
            download.metadata_processed_at = datetime.utcnow()
            download.fully_processed = True
            self.db.commit()

            return {"status": "success", "scan_result": scan_result}

        except Exception as e:
            download.status = "processing_error"
            download.error_message = str(e)
            self.db.commit()
            raise
```

#### Step 3: Add Model Fields for Tracking

**File**: `backend/models/download.py`

**Add fields**:
```python
from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer

class Download(Base):
    __tablename__ = "downloads"

    # Existing fields...

    # Integrity check fields (NEW)
    integrity_status = Column(
        String,
        default="pending_check",  # pending_check|valid|corrupt|skipped
        nullable=False
    )
    integrity_checked_at = Column(DateTime, nullable=True)
    integrity_check_results = Column(JSON, nullable=True)  # Full verification results

    # Metadata processing fields
    metadata_processed_at = Column(DateTime, nullable=True)
    fully_processed = Column(Boolean, default=False)

    # Retry chain tracking
    parent_download_id = Column(Integer, ForeignKey('downloads.id'), nullable=True)
    retry_count = Column(Integer, default=0)

    # Status history
    status_history = Column(JSON, default={})  # Track state transitions
```

#### Step 4: Add Database Migration

**File**: Create `backend/migrations/add_integrity_fields.py`

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('downloads', sa.Column('integrity_status', sa.String(), nullable=False, server_default='pending_check'))
    op.add_column('downloads', sa.Column('integrity_checked_at', sa.DateTime(), nullable=True))
    op.add_column('downloads', sa.Column('integrity_check_results', sa.JSON(), nullable=True))
    op.add_column('downloads', sa.Column('metadata_processed_at', sa.DateTime(), nullable=True))
    op.add_column('downloads', sa.Column('fully_processed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('downloads', sa.Column('parent_download_id', sa.Integer(), nullable=True))
    op.add_column('downloads', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('downloads', sa.Column('status_history', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('downloads', 'integrity_status')
    op.drop_column('downloads', 'integrity_checked_at')
    op.drop_column('downloads', 'integrity_check_results')
    op.drop_column('downloads', 'metadata_processed_at')
    op.drop_column('downloads', 'fully_processed')
    op.drop_column('downloads', 'parent_download_id')
    op.drop_column('downloads', 'retry_count')
    op.drop_column('downloads', 'status_history')
```

#### Step 5: Update API Endpoints

**File**: `backend/routes/downloads.py`

```python
@router.get("/api/downloads/{download_id}/integrity-status")
async def get_integrity_status(
    download_id: int,
    db_session: Session = Depends(get_db)
):
    """Get integrity check results for a download"""
    download = db_session.query(Download).get(download_id)
    if not download:
        raise HTTPException(status_code=404)

    return {
        "download_id": download_id,
        "status": download.integrity_status,
        "checked_at": download.integrity_checked_at,
        "results": download.integrity_check_results,
        "retry_count": download.retry_count
    }

@router.post("/api/downloads/{download_id}/retry-integrity")
async def retry_integrity_check(
    download_id: int,
    db_session: Session = Depends(get_db),
    current_user = Depends(check_token)
):
    """Manually retry integrity check for a download"""
    integrity_service = IntegrityCheckService(db_session, ...)

    result = await integrity_service.verify_download(
        download_id=download_id,
        torrent_hash=None  # Will load from DB
    )

    return result
```

### Implementation Checklist

- [ ] Create `backend/services/integrity_check_service.py`
- [ ] Convert `audiobook_audio_verifier.py` to service-compatible module
- [ ] Update `on_download_completed()` in `DownloadService`
- [ ] Add model fields to `backend/models/download.py`
- [ ] Create database migration
- [ ] Add API endpoints for status and manual retry
- [ ] Implement alternate release selection logic
- [ ] Test with simulated integrity failures
- [ ] Test re-download with alternate release
- [ ] Verify retry chain tracking

### Testing Strategy

```python
# tests/test_integrity_check.py

@pytest.mark.asyncio
async def test_integrity_check_passes():
    """Test that integrity check passes for valid downloads"""
    # Create valid download files
    # Run integrity check
    # Verify status is 'valid'

@pytest.mark.asyncio
async def test_integrity_check_fails():
    """Test that integrity check fails for corrupt files"""
    # Create corrupt files
    # Run integrity check
    # Verify status is 'corrupt'

@pytest.mark.asyncio
async def test_integrity_failure_triggers_retry():
    """Test that failed integrity triggers re-download"""
    # Simulate integrity failure
    # Verify alternate release was found
    # Verify new download was queued
    # Verify parent_download_id tracking

@pytest.mark.asyncio
async def test_no_alternatives_available():
    """Test handling when no alternate releases exist"""
    # Mock no alternatives found
    # Run integrity failure handler
    # Verify download marked as failed but not retried
```

### Success Criteria

1. ✅ Integrity check runs within 5 minutes of download completion
2. ✅ All 4 verification checks pass or fail appropriately
3. ✅ Corrupt files trigger automatic re-download
4. ✅ Alternate release properly selected using quality rules
5. ✅ Retry chain tracked via parent_download_id
6. ✅ Original torrent kept seeding if beneficial
7. ✅ All operations logged with full details

---

## GAP 2: Narrator Detection Pipeline Integration

### Specification Requirement
```
Narrator must be recognized using:
1. Speech-to-text detection
2. MAM metadata comparison
3. Audible narrator scraping (fallback)
4. Fuzzy matching if uncertain
```

### Current State Analysis

**What Exists**:
- ✅ `audiobook_audio_verifier.py` - Speech-to-text detection capability
- ✅ `backend/models/book.py` - narrator field
- ✅ `secure_stealth_audiobookshelf_crawler.py` - Narrator detection logic
- ✅ Fuzzy matching utilities

**What's Missing**:
- ❌ Narrator detection not wired into automated pipeline
- ❌ Not called after download completion
- ❌ No MAM metadata comparison
- ❌ No storage of detected narrator in book model
- ❌ No duplicate narrator detection to prevent duplicates

### Implementation Strategy

#### Step 1: Create Narrator Detection Service

**File**: Create `backend/services/narrator_detection_service.py`

```python
from difflib import SequenceMatcher
from backend.models.book import Book
from backend.integrations.abs_client import AudiobookshelfClient
import logging

logger = logging.getLogger(__name__)

class NarratorDetectionService:
    """
    Detects narrator from:
    1. Speech-to-text analysis of audio files
    2. MAM metadata (if available)
    3. Audible database (fallback)
    4. Fuzzy matching against known narrators
    """

    def __init__(self, db_session, audio_verifier, abs_client):
        self.db = db_session
        self.audio_verifier = audio_verifier
        self.abs_client = abs_client
        self.similarity_threshold = 0.85  # 85% match required

    async def detect_narrator(
        self,
        download_id: int,
        book_id: int,
        audio_directory: str,
        mam_metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Detect narrator using multiple methods.

        Priority:
        1. MAM metadata (most reliable)
        2. Speech-to-text from audio files
        3. Audible database lookup (fallback)
        4. Fuzzy match against known narrators

        Returns:
            Narrator name or None if unable to detect
        """
        detected_narrator = None
        detection_method = None
        confidence = 0.0

        # Method 1: MAM metadata
        if mam_metadata and mam_metadata.get('narrator'):
            detected_narrator = mam_metadata['narrator']
            detection_method = "mam_metadata"
            confidence = 0.95
            logger.info(f"Narrator from MAM: {detected_narrator}")

        # Method 2: Speech-to-text from audio files
        if not detected_narrator:
            try:
                speech_result = await self._extract_narrator_speech_to_text(
                    audio_directory
                )
                if speech_result['confidence'] > self.similarity_threshold:
                    detected_narrator = speech_result['narrator']
                    detection_method = "speech_to_text"
                    confidence = speech_result['confidence']
                    logger.info(
                        f"Narrator from speech-to-text: {detected_narrator} "
                        f"(confidence: {confidence:.2%})"
                    )
            except Exception as e:
                logger.warning(f"Speech-to-text detection failed: {e}")

        # Method 3: Audible database lookup
        if not detected_narrator:
            try:
                book = self.db.query(Book).get(book_id)
                audible_result = await self._lookup_narrator_audible(
                    title=book.title,
                    author=book.author
                )
                if audible_result:
                    detected_narrator = audible_result['narrator']
                    detection_method = "audible_database"
                    confidence = audible_result.get('confidence', 0.7)
                    logger.info(f"Narrator from Audible: {detected_narrator}")
            except Exception as e:
                logger.warning(f"Audible lookup failed: {e}")

        # Method 4: Fuzzy match against library
        if not detected_narrator:
            try:
                fuzzy_result = await self._fuzzy_match_narrator(
                    audio_directory
                )
                if fuzzy_result['confidence'] > self.similarity_threshold:
                    detected_narrator = fuzzy_result['narrator']
                    detection_method = "fuzzy_match"
                    confidence = fuzzy_result['confidence']
                    logger.info(
                        f"Narrator from fuzzy match: {detected_narrator} "
                        f"(confidence: {confidence:.2%})"
                    )
            except Exception as e:
                logger.warning(f"Fuzzy matching failed: {e}")

        # Store result
        if detected_narrator:
            book = self.db.query(Book).get(book_id)
            book.narrator = detected_narrator
            book.narrator_detection_method = detection_method
            book.narrator_confidence = confidence
            book.narrator_detected_at = datetime.utcnow()
            self.db.commit()

            logger.info(
                f"Narrator for book {book_id} ({book.title}): "
                f"{detected_narrator} (via {detection_method})"
            )

        return detected_narrator

    async def _extract_narrator_speech_to_text(
        self,
        audio_directory: str
    ) -> Dict[str, any]:
        """
        Use speech-to-text on audio files to detect narrator.

        Searches for:
        - "Narrated by [Name]" patterns
        - "Read by [Name]" patterns
        - Voice recognition at intro/outro
        """
        from audiobook_audio_verifier import AudiobookVerifier

        verifier = AudiobookVerifier()
        result = verifier.extract_narrator_from_audio(audio_directory)

        return {
            "narrator": result.get('narrator'),
            "confidence": result.get('confidence', 0.0),
            "method": "speech_to_text"
        }

    async def _lookup_narrator_audible(
        self,
        title: str,
        author: str
    ) -> Optional[Dict[str, any]]:
        """
        Lookup narrator from Audible database.

        Uses web scraping to find Audible listing and extract narrator.
        """
        # Implementation: Audible metadata scraper
        # This would scrape audible.com for the book and extract narrator
        pass

    async def _fuzzy_match_narrator(
        self,
        audio_directory: str
    ) -> Dict[str, any]:
        """
        Fuzzy match detected voice against library of known narrators.

        Process:
        1. Extract voice features from audio file
        2. Compare against known narrator voice prints
        3. Return best match if confidence > threshold
        """
        # Implementation: Voice fingerprinting and matching
        pass

    def _similarity_score(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (0-1)"""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
```

#### Step 2: Add Narrator Duplicate Prevention

**File**: Modify `backend/services/quality_rules_service.py`

```python
class QualityRulesService:

    async def prevent_duplicate_narrator(
        self,
        book_id: int,
        new_narrator: str
    ) -> bool:
        """
        Prevent downloading same narrator of same book.

        Checks:
        1. If same narrator already exists in library
        2. If new release is superior (higher bitrate, unabridged)
        3. Triggers replacement if new is superior

        Returns:
            True if download should proceed
            False if duplicate narrator and not superior
        """
        book = self.db.query(Book).get(book_id)

        # Check if narrator already exists
        existing_narrator = book.narrator

        if existing_narrator and existing_narrator.lower() == new_narrator.lower():
            logger.info(
                f"Duplicate narrator detected for {book.title}: {new_narrator}"
            )

            # Check if new release is superior
            # (This would compare bitrate, abridged/unabridged, etc.)
            # If superior, return True to trigger replacement
            # If not superior, return False to prevent duplicate

            return False  # Default: prevent duplicate

        return True
```

#### Step 3: Integrate into Metadata Scan

**File**: Modify `backend/services/metadata_service.py`

```python
class MetadataService:

    async def full_scan(
        self,
        book_id: int,
        source: str = "manual"
    ) -> Dict[str, any]:
        """
        Enhanced full scan including narrator detection.
        """
        scan_results = {}

        try:
            # Existing scan logic...

            # NEW: Narrator detection
            narrator_service = NarratorDetectionService(
                self.db,
                audio_verifier=...,
                abs_client=...
            )

            # Get book download directory
            book = self.db.query(Book).get(book_id)
            download = self.db.query(Download)\
                .filter(Download.book_id == book_id)\
                .order_by(Download.created_at.desc())\
                .first()

            if download and download.torrent_hash:
                audio_directory = self._get_audio_directory(download.torrent_hash)

                narrator = await narrator_service.detect_narrator(
                    download_id=download.id,
                    book_id=book_id,
                    audio_directory=audio_directory
                )

                scan_results['narrator'] = narrator

            return scan_results

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            raise
```

#### Step 4: Add API Endpoints

**File**: Add to `backend/routes/books.py`

```python
@router.post("/api/books/{book_id}/detect-narrator")
async def detect_narrator(
    book_id: int,
    db_session: Session = Depends(get_db),
    current_user = Depends(check_token)
):
    """
    Manually trigger narrator detection for a book.
    """
    narrator_service = NarratorDetectionService(db_session, ...)

    book = db_session.query(Book).get(book_id)
    if not book:
        raise HTTPException(status_code=404)

    # Get latest download
    download = db_session.query(Download)\
        .filter(Download.book_id == book_id)\
        .order_by(Download.created_at.desc())\
        .first()

    if not download:
        raise HTTPException(
            status_code=400,
            detail="No downloads found for this book"
        )

    narrator = await narrator_service.detect_narrator(
        download_id=download.id,
        book_id=book_id,
        audio_directory=None  # Will be determined automatically
    )

    return {
        "book_id": book_id,
        "narrator": narrator,
        "detected_at": datetime.utcnow()
    }
```

### Implementation Checklist

- [ ] Create `backend/services/narrator_detection_service.py`
- [ ] Implement speech-to-text extraction
- [ ] Implement Audible database lookup
- [ ] Implement fuzzy matching
- [ ] Add narrator duplicate prevention
- [ ] Integrate into metadata scan workflow
- [ ] Add model fields: narrator_detection_method, narrator_confidence, narrator_detected_at
- [ ] Add API endpoints for manual detection
- [ ] Test with various narrator patterns
- [ ] Test duplicate prevention

### Testing Strategy

```python
# tests/test_narrator_detection.py

@pytest.mark.asyncio
async def test_mam_metadata_narrator():
    """Test narrator detection from MAM metadata"""

@pytest.mark.asyncio
async def test_speech_to_text_narrator():
    """Test narrator detection from speech-to-text"""

@pytest.mark.asyncio
async def test_fuzzy_match_narrator():
    """Test narrator detection via fuzzy matching"""

@pytest.mark.asyncio
async def test_duplicate_narrator_prevention():
    """Test that duplicate narrators are prevented"""
```

### Success Criteria

1. ✅ Narrator detected within 10 seconds of audio analysis
2. ✅ MAM metadata method has 95%+ confidence
3. ✅ Speech-to-text method has 70%+ confidence
4. ✅ Duplicate narrators prevented in library
5. ✅ All detection methods logged with confidence scores
6. ✅ Manual detection endpoint available

---

## GAP 3: Monthly Drift Correction Algorithm

### Specification Requirement
```
Every 30 days, re-query Goodreads and update:
* Series order
* Cover art
* Description
* Publication info

Do **not** overwrite:
* Verified scanned title
* Narrator identity
```

### Current State Analysis

**What Exists**:
- ✅ `backend/schedulers/tasks.py` - `metadata_full_refresh_task()` runs monthly
- ✅ `backend/services/metadata_service.py` - Goodreads integration
- ✅ `backend/models/metadata_correction.py` - Correction tracking
- ✅ Scheduled job infrastructure

**What's Missing**:
- ❌ Drift detection algorithm
- ❌ Field-level comparison logic
- ❌ Protected field enforcement
- ❌ Change tracking for corrections

### Implementation Strategy

#### Step 1: Create Drift Detection Service

**File**: Create `backend/services/drift_detection_service.py`

```python
from datetime import datetime, timedelta
from typing import Dict, List
from backend.models.book import Book

class DriftDetectionService:
    """
    Detects and corrects metadata drift.

    Monthly comparison of:
    - Goodreads current data vs stored data
    - Series order/name changes
    - Description updates
    - Cover art changes
    - Publication info updates

    Protected fields (never overwritten):
    - Title (verified from scan)
    - Narrator (detected via speech-to-text)
    """

    # Fields that can be updated
    UPDATABLE_FIELDS = {
        'series_name': 'Series Name',
        'series_order': 'Series Order',
        'description': 'Description',
        'cover_url': 'Cover Art URL',
        'published_year': 'Publication Year',
        'publisher': 'Publisher',
        'language': 'Language'
    }

    # Fields that cannot be overwritten (verified data)
    PROTECTED_FIELDS = {
        'title': 'Title (verified from audio scan)',
        'narrator': 'Narrator (detected from audio)',
        'duration_minutes': 'Duration (verified from audio)'
    }

    def __init__(self, db_session, goodreads_scraper):
        self.db = db_session
        self.goodreads = goodreads_scraper

    async def detect_drift_for_book(
        self,
        book_id: int
    ) -> Dict[str, any]:
        """
        Detect metadata drift for a single book.

        Returns:
            {
                "book_id": int,
                "drifted_fields": ["field1", "field2"],
                "changes": {
                    "field_name": {
                        "old_value": "...",
                        "new_value": "...",
                        "source": "goodreads",
                        "change_type": "updated" | "new" | "removed"
                    }
                },
                "drift_detected": bool
            }
        """
        book = self.db.query(Book).get(book_id)
        if not book:
            raise ValueError(f"Book {book_id} not found")

        # Check if metadata is old enough to warrant refresh
        if not self._should_refresh(book):
            return {"book_id": book_id, "drift_detected": False}

        # Fetch latest Goodreads data
        goodreads_data = await self.goodreads.fetch_book(
            title=book.title,
            author=book.author
        )

        if not goodreads_data:
            return {
                "book_id": book_id,
                "drift_detected": False,
                "reason": "Goodreads data not found"
            }

        # Compare fields
        drift_report = {
            "book_id": book_id,
            "book_title": book.title,
            "drifted_fields": [],
            "changes": {},
            "drift_detected": False
        }

        # Check each updatable field
        for field_name, display_name in self.UPDATABLE_FIELDS.items():
            current_value = getattr(book, field_name, None)
            new_value = goodreads_data.get(field_name)

            if self._has_drifted(current_value, new_value):
                drift_report["drifted_fields"].append(field_name)
                drift_report["drift_detected"] = True
                drift_report["changes"][field_name] = {
                    "old_value": current_value,
                    "new_value": new_value,
                    "source": "goodreads",
                    "change_type": self._classify_change(current_value, new_value)
                }

        return drift_report

    async def detect_drift_all_books(
        self,
        days_since_update: int = 30,
        limit: int = None
    ) -> List[Dict]:
        """
        Detect drift for all books not updated in X days.

        Args:
            days_since_update: Only check books older than this (default 30 days)
            limit: Max books to check (default None = all)

        Returns:
            List of drift reports for books with detected drift
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_since_update)

        # Find books that haven't been updated recently
        query = self.db.query(Book).filter(
            Book.metadata_last_updated < cutoff_date
        ).order_by(Book.metadata_last_updated)

        if limit:
            query = query.limit(limit)

        books_to_check = query.all()

        drift_reports = []

        for book in books_to_check:
            try:
                report = await self.detect_drift_for_book(book.id)
                if report.get('drift_detected'):
                    drift_reports.append(report)
            except Exception as e:
                logger.error(
                    f"Drift detection failed for book {book.id}: {e}"
                )

        return drift_reports

    async def apply_drift_corrections(
        self,
        drift_report: Dict[str, any],
        auto_correct: bool = True
    ) -> Dict[str, any]:
        """
        Apply corrections from drift report.

        Args:
            drift_report: Report from detect_drift_for_book()
            auto_correct: If False, require manual approval

        Returns:
            {
                "book_id": int,
                "corrections_applied": int,
                "fields_updated": ["field1", "field2"],
                "protected_fields_detected": ["field"],
                "timestamp": datetime
            }
        """
        book_id = drift_report['book_id']
        book = self.db.query(Book).get(book_id)

        corrections_applied = 0
        fields_updated = []
        protected_detected = []

        for field_name, change_info in drift_report['changes'].items():
            # Verify field is not protected
            if field_name in self.PROTECTED_FIELDS:
                logger.warning(
                    f"Attempted to update protected field {field_name} "
                    f"for book {book_id}. Change blocked."
                )
                protected_detected.append(field_name)
                continue

            if auto_correct:
                # Apply correction
                new_value = change_info['new_value']
                setattr(book, field_name, new_value)
                corrections_applied += 1
                fields_updated.append(field_name)

                logger.info(
                    f"Applied drift correction for {field_name} "
                    f"on book {book_id}"
                )

        # Update last corrected timestamp
        if corrections_applied > 0:
            book.metadata_last_updated = datetime.utcnow()
            book.last_drift_correction = datetime.utcnow()
            self.db.commit()

        return {
            "book_id": book_id,
            "corrections_applied": corrections_applied,
            "fields_updated": fields_updated,
            "protected_fields_detected": protected_detected,
            "timestamp": datetime.utcnow()
        }

    def _should_refresh(self, book: Book) -> bool:
        """Check if book metadata is old enough to warrant refresh"""
        if not book.metadata_last_updated:
            return True

        age = datetime.utcnow() - book.metadata_last_updated
        return age > timedelta(days=30)

    def _has_drifted(self, current_value, new_value) -> bool:
        """Check if value has drifted from current"""
        # None -> new value is drift
        if current_value is None and new_value is not None:
            return True

        # Different values is drift
        if str(current_value) != str(new_value):
            return True

        return False

    def _classify_change(self, old_value, new_value) -> str:
        """Classify the type of change"""
        if old_value is None:
            return "new"
        if new_value is None:
            return "removed"
        return "updated"
```

#### Step 2: Integrate into Monthly Task

**File**: Modify `backend/schedulers/tasks.py`

```python
from backend.services.drift_detection_service import DriftDetectionService

@scheduler.scheduled_job('cron', day_of_week='0', hour=3, minute=0, id='drift_correction_monthly')
async def metadata_drift_correction_task():
    """
    Monthly drift correction task.

    Runs every Sunday at 3:00 AM.

    Process:
    1. Find books not updated in 30+ days
    2. Fetch latest Goodreads data
    3. Detect field-level drift
    4. Apply corrections to non-protected fields
    5. Log all changes
    """
    db_session = SessionLocal()
    task_record = Task(
        task_name="metadata_drift_correction",
        status="running",
        scheduled_time=datetime.utcnow()
    )
    db_session.add(task_record)
    db_session.commit()

    try:
        drift_service = DriftDetectionService(
            db_session,
            goodreads_scraper=GoodreadsScraper()
        )

        # Detect drift for all old books
        drift_reports = await drift_service.detect_drift_all_books(
            days_since_update=30,
            limit=100  # Process 100 books per run
        )

        total_corrections = 0
        books_corrected = 0
        protected_field_attempts = 0

        # Apply corrections
        for drift_report in drift_reports:
            correction_result = await drift_service.apply_drift_corrections(
                drift_report=drift_report,
                auto_correct=True
            )

            if correction_result['corrections_applied'] > 0:
                total_corrections += correction_result['corrections_applied']
                books_corrected += 1

            if correction_result['protected_fields_detected']:
                protected_field_attempts += 1

        task_record.status = "completed"
        task_record.items_processed = len(drift_reports)
        task_record.items_succeeded = books_corrected
        task_record.items_failed = len(drift_reports) - books_corrected
        task_record.metadata = {
            "total_corrections": total_corrections,
            "books_corrected": books_corrected,
            "protected_field_attempts": protected_field_attempts,
            "drift_reports": drift_reports
        }

        logger.info(
            f"Drift correction complete: {books_corrected} books corrected, "
            f"{total_corrections} fields updated"
        )

    except Exception as e:
        task_record.status = "failed"
        task_record.error_message = str(e)
        logger.error(f"Drift correction task failed: {e}")

    finally:
        task_record.actual_end = datetime.utcnow()
        task_record.duration_seconds = (
            task_record.actual_end - task_record.actual_start
        ).total_seconds()
        db_session.commit()
        db_session.close()
```

#### Step 3: Add API Endpoints

**File**: Add to `backend/routes/metadata.py`

```python
@router.post("/api/metadata/detect-drift/{book_id}")
async def detect_drift_single(
    book_id: int,
    db_session: Session = Depends(get_db),
    current_user = Depends(check_token)
):
    """Detect metadata drift for a single book"""
    drift_service = DriftDetectionService(db_session, ...)
    report = await drift_service.detect_drift_for_book(book_id)
    return report

@router.post("/api/metadata/detect-drift-all")
async def detect_drift_all(
    days_since_update: int = 30,
    limit: int = 100,
    db_session: Session = Depends(get_db),
    current_user = Depends(check_token)
):
    """Detect drift for all old books"""
    drift_service = DriftDetectionService(db_session, ...)
    reports = await drift_service.detect_drift_all_books(
        days_since_update=days_since_update,
        limit=limit
    )
    return {"drift_reports": reports, "total": len(reports)}

@router.post("/api/metadata/apply-corrections")
async def apply_corrections(
    drift_report: Dict,
    auto_correct: bool = True,
    db_session: Session = Depends(get_db),
    current_user = Depends(check_token)
):
    """Apply drift corrections"""
    drift_service = DriftDetectionService(db_session, ...)
    result = await drift_service.apply_drift_corrections(
        drift_report=drift_report,
        auto_correct=auto_correct
    )
    return result
```

#### Step 4: Add Model Fields

**File**: Modify `backend/models/book.py`

```python
from sqlalchemy import Column, DateTime

class Book(Base):
    __tablename__ = "books"

    # Existing fields...

    # Drift detection fields
    metadata_last_updated = Column(DateTime, nullable=True)
    last_drift_correction = Column(DateTime, nullable=True)
    drift_correction_count = Column(Integer, default=0)
```

### Implementation Checklist

- [ ] Create `backend/services/drift_detection_service.py`
- [ ] Implement field-level comparison logic
- [ ] Add protected field enforcement
- [ ] Integrate into scheduled monthly task
- [ ] Add API endpoints for drift detection
- [ ] Add model fields for tracking corrections
- [ ] Test drift detection with sample data
- [ ] Test protected field enforcement
- [ ] Verify corrections are applied correctly

### Success Criteria

1. ✅ Drift detected within 30 seconds for book
2. ✅ Protected fields (title, narrator) never overwritten
3. ✅ Updatable fields correctly updated
4. ✅ All changes logged with old/new values
5. ✅ Monthly task runs on schedule
6. ✅ Reports generated for each corrected book

---

## IMPLEMENTATION PRIORITY & TIMELINE

### Week 1: Critical Gaps (GAP 1 & GAP 4)
- **40 hours total effort**
- **Priority**: CRITICAL (blocks production)
- **Impact**: Automatic download processing becomes fully functional

### Week 2: High-Priority Gaps (GAP 2 & GAP 3)
- **20 hours total effort**
- **Priority**: HIGH (improves data quality)
- **Impact**: Metadata accuracy and library integrity

### Implementation Order
1. **Day 1-2**: GAP 1 (auto-trigger scan) - 8 hours
2. **Day 2-4**: GAP 4 (integrity check) - 12 hours
3. **Day 4-6**: GAP 2 (narrator detection) - 10 hours
4. **Day 6-8**: GAP 3 (drift correction) - 10 hours

### Cumulative Testing
- **Daily**: Unit tests for implemented components
- **End of Week 1**: Integration test for download → scan workflow
- **End of Week 2**: Full E2E test with all gaps closed

---

## SUCCESS METRICS

After all gaps are closed:
- ✅ 100% specification compliance
- ✅ Fully automated download lifecycle (queue → download → integrity → scan → metadata)
- ✅ Zero manual intervention required for standard downloads
- ✅ Monthly drift corrections automatic
- ✅ Narrator detection for all new downloads
- ✅ Integrity failures automatically handled with re-downloads
- ✅ All operations logged and auditable

---

**Document Status**: Ready for Implementation
**Created**: 2025-11-21
**Estimated Completion**: 2025-12-05 (2 weeks)
