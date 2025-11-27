# Autonomous Audiobook Archivist - Complete Build Prompt

**Status:** READY FOR IMPLEMENTATION
**Date:** 2025-11-27
**Scope:** Multi-step automation system for audiobook acquisition, processing, enrichment, and scheduling

---

## Phase 1: Core Architecture & Safety Framework

### 1.1 Safety & Compliance Layer
**Objective:** Implement non-destructive operations with comprehensive safeguards

**Implementation:**
- Create `backend/config.py` extension:
  - Define `PROTECTED_OPERATIONS` list (always require explicit flags)
  - Add `backup_metadata()` function - creates timestamped backup before ANY metadata edit
  - Add `verify_backup_exists()` - confirms backup created successfully before proceeding
  - Implement `.env` validation - reject any write attempts to `.env` file
  - Add `ALLOW_DRM_REMOVAL = False` default, requires user enable in `.env` to change

- Create `backend/safety_validator.py`:
  - `SafetyValidator` class with methods:
    - `validate_operation(operation_type, flags)` - confirms required flags present
    - `check_env_write_attempt()` - blocks any .env modifications
    - `require_backup_before_edit(file_path)` - enforces backup-first policy
    - `verify_non_destructive(old_data, new_data)` - confirms changes are additive/non-destructive

- Create `backend/logs/operations_audit.log` - append-only audit trail of all operations

**Success Criteria:**
- No .env file can be modified by system
- Every metadata.json edit creates timestamped backup
- All destructive operations require explicit user flag
- Audit log tracks every operation with timestamp, user, action, result

---

## Phase 2: Audiobook Verification System

### 2.1 Narrator Verification
**Objective:** Validate narrator matches across audio file and metadata sources

**Implementation:**
- Create `mamcrawler/verification/narrator_verifier.py`:
  - `NarratorVerifier` class with methods:
    - `extract_narrator_from_audio(file_path)` - uses ffmpeg to read metadata
    - `extract_narrator_from_metadata(metadata_json)` - reads seriesName, author fields
    - `verify_narrator_match(audio_narrator, metadata_narrator)` - fuzzy match for typos
    - `get_primary_narrator()` - for multi-narrator titles, identify primary
  - Return: `{'match': bool, 'confidence': 0.0-1.0, 'narrator': str, 'sources': list}`

**Integration:**
- Add narrator field to Audiobookshelf metadata structure: `metadata.json`
- Store verified narrator in both file metadata and API database

### 2.2 Duration Tolerance Verification
**Objective:** Validate audio duration within acceptable tolerance of expected

**Implementation:**
- Create `mamcrawler/verification/duration_verifier.py`:
  - `DurationVerifier` class:
    - `get_expected_duration(title, author)` - queries Audible/Goodreads API
    - `get_actual_duration(audio_file)` - uses ffprobe to extract duration
    - `verify_tolerance(actual, expected, tolerance_percent=2)` - checks ±tolerance
  - Return: `{'valid': bool, 'actual': seconds, 'expected': seconds, 'variance': percent}`

### 2.3 ISBN/ASIN Verification
**Objective:** Match audiobook to authoritative catalog using ISBN or ASIN

**Implementation:**
- Create `mamcrawler/verification/isbn_verifier.py`:
  - `ISBNVerifier` class:
    - `extract_isbn_from_metadata(metadata.json)` - reads identifier field
    - `extract_asin_from_audible(title, author)` - queries Audible for ASIN
    - `verify_identifier_match(isbn, asin)` - validates against database
    - `lookup_audible_edition(asin)` - gets canonical edition info
  - Return: `{'valid': bool, 'isbn': str, 'asin': str, 'edition': dict}`

### 2.4 Chapter Verification
**Objective:** Ensure audiobook has minimum viable chapter structure

**Implementation:**
- Create `mamcrawler/verification/chapter_verifier.py`:
  - `ChapterVerifier` class:
    - `extract_chapters(audio_file)` - uses ffmpeg to read chapter metadata
    - `verify_minimum_chapters(chapter_count, title)` - checks min=3 unless known single-track
    - `validate_chapter_structure(chapters)` - confirms chapter names/times valid
  - Return: `{'valid': bool, 'count': int, 'chapters': list, 'structure_valid': bool}`

### 2.5 Verification Orchestration
**Objective:** Coordinate all verification steps with retry logic

**Implementation:**
- Create `mamcrawler/verification/verification_orchestrator.py`:
  - `VerificationOrchestrator` class:
    - `verify_audiobook(audio_path, metadata)` - runs all 4 verifiers
    - `collect_failures()` - tracks failed verifications
    - `retry_failed(max_attempts=3)` - auto-retry with exponential backoff
    - `generate_verification_report()` - detailed pass/fail per criterion
  - Return: `{'passed': bool, 'details': dict, 'failures': list, 'retry_count': int}`

**Integration Points:**
- POST `/api/audiobooks/verify` - trigger verification for single book
- POST `/api/audiobooks/verify-batch` - verify multiple audiobooks
- GET `/api/verification/reports` - retrieve verification history

**Success Criteria:**
- All 4 verification systems implemented and working
- Retry logic automatically handles transient failures
- Unresolved failures flagged for manual review
- Verification reports append to logs/yyyy-mm-dd/verification.md

---

## Phase 3: Audio Processing Pipeline

### 3.1 Audio Normalization
**Objective:** Standardize loudness levels across diverse audio sources

**Implementation:**
- Create `mamcrawler/audio_processing/normalizer.py`:
  - `AudioNormalizer` class:
    - `analyze_loudness(audio_file)` - uses ffmpeg-normalize to measure LUFS
    - `normalize_to_target(audio_file, target_lufs=-16)` - adjusts loudness
    - `preserve_dynamic_range()` - uses loudnorm filter to avoid over-compression
  - Output format: `.m4b` or `.mp3` (user configurable)

### 3.2 Multi-File Merging
**Objective:** Combine split audio files into single audiobook file

**Implementation:**
- Create `mamcrawler/audio_processing/merger.py`:
  - `AudioMerger` class:
    - `detect_split_files(directory)` - identifies part1, part2, etc. patterns
    - `merge_files(file_list, output_format='m4b')` - combines with ffmpeg
    - `preserve_chapter_boundaries()` - maintains chapter markers at split points
    - `validate_merge_integrity()` - verifies no data loss during merge
  - Output: Single merged `.m4b` or `.mp3` file

### 3.3 Chapter Preservation
**Objective:** Maintain chapter structure through processing

**Implementation:**
- Create `mamcrawler/audio_processing/chapter_handler.py`:
  - `ChapterHandler` class:
    - `extract_chapters(audio_file)` - reads chapter metadata
    - `create_chapters_file(chapters, duration)` - generates m4b-tool compatible format
    - `embed_chapters_in_m4b(audio_file, chapters)` - uses m4b-tool
    - `validate_chapters_embedded(audio_file)` - confirms chapters readable
  - Return: Chapter list with validated timing

### 3.4 File Naming Standardization
**Objective:** Apply consistent naming convention to all audiobooks

**Implementation:**
- Create `mamcrawler/audio_processing/file_namer.py`:
  - `FileNamer` class:
    - `generate_filename(author, series, title, narrator, year)` - creates: `Author/Series(optional)/Title - Narrator (Year).m4b`
    - `sanitize_filename(name)` - removes invalid characters
    - `handle_duplicates(target_path)` - appends counter if file exists
    - `validate_path_structure()` - confirms directory hierarchy correct
  - Return: Standardized full path

### 3.5 Audio Processing Orchestration
**Objective:** Coordinate all audio processing steps

**Implementation:**
- Create `mamcrawler/audio_processing/processor_orchestrator.py`:
  - `AudioProcessorOrchestrator` class:
    - `process_audiobook(input_path, metadata)` - pipeline orchestrator
    - `normalize_loudness()` → `merge_files()` → `embed_chapters()` → `rename_file()`
    - `track_progress()` - logs each step completion
    - `handle_errors()` - captures failures, enables retry
  - Return: Final `.m4b` file path with validation

**Tools Required:**
- `ffmpeg` - audio conversion, metadata extraction
- `m4b-tool` - m4b-specific operations (chapter embedding)
- Optional: `yt-dlp` if user enables

**Integration Points:**
- POST `/api/audiobooks/process` - start processing pipeline
- GET `/api/audiobooks/processing-status/{id}` - check progress
- Logs to: `logs/yyyy-mm-dd/processing.md`

**Success Criteria:**
- All audio files successfully normalized to -16 LUFS
- Multi-file merges complete without data loss
- Chapter structure preserved in output
- Filenames follow convention exactly
- Processing logged with timestamps and status

---

## Phase 4: Metadata Enrichment System

### 4.1 Metadata Source Integration
**Objective:** Pull authoritative metadata from multiple sources in priority order

**Implementation:**
- Create `mamcrawler/metadata/audible_source.py`:
  - `AudibleMetadataSource` class:
    - `search_by_asin(asin)` - direct lookup by ASIN
    - `search_by_title_author(title, author)` - fuzzy search
    - `extract_fields()` - narrator, publisher, release_date, cover_art, genres
  - Return: `{'narrator': str, 'publisher': str, 'release_year': int, 'cover_url': str, 'genres': list}`

- Create `mamcrawler/metadata/goodreads_source.py`:
  - `GoodreadsMetadataSource` class:
    - `search_by_title_author(title, author)` - web scraping via Selenium
    - `extract_fields()` - series_info, genres, ratings, description
    - `get_series_metadata()` - series_name, book_order, total_books
  - Return: `{'series': str, 'series_order': int, 'genres': list, 'rating': float}`

- Create `mamcrawler/metadata/openlibrary_source.py`:
  - `OpenLibraryMetadataSource` class:
    - `search_by_isbn(isbn)` - direct lookup
    - `search_by_title_author(title, author)` - API query
    - `extract_fields()` - publishers, publish_date, descriptions, editions
  - Return: `{'publishers': list, 'publish_date': str, 'edition_count': int}`

### 4.2 Metadata Enrichment Orchestration
**Objective:** Prioritize sources and merge metadata

**Implementation:**
- Create `mamcrawler/metadata/enrichment_orchestrator.py`:
  - `MetadataEnricher` class:
    - `enrich_audiobook(metadata)` - pipeline orchestrator
    - Priority: Audible (primary) → Goodreads → OpenLibrary (fallback)
    - `merge_metadata()` - combines from multiple sources without overwrite conflicts
    - `clean_title()` - removes "The", "A", subtitle cleaning
    - `generate_enriched_metadata()` - creates final unified object
  - Return: Complete enriched metadata object

### 4.3 Metadata Validation & Cleaning
**Objective:** Ensure data quality before storing

**Implementation:**
- Create `mamcrawler/metadata/validator.py`:
  - `MetadataValidator` class:
    - `validate_required_fields()` - title, author, narrator (if available)
    - `validate_format()` - year is 4-digit int, genres is list, etc.
    - `sanitize_text_fields()` - remove invalid characters, normalize whitespace
    - `detect_and_handle_duplicates()` - identifies if this title already exists
  - Return: `{'valid': bool, 'errors': list, 'warnings': list, 'cleaned_metadata': dict}`

### 4.4 Cover Art Acquisition
**Objective:** Download and embed cover art

**Implementation:**
- Create `mamcrawler/metadata/cover_art_handler.py`:
  - `CoverArtHandler` class:
    - `fetch_from_audible(asin)` - primary source
    - `fetch_from_goodreads(isbn)` - fallback
    - `fetch_from_openlibrary(isbn)` - final fallback
    - `embed_in_metadata(audio_file, cover_path)` - uses ffmpeg
    - `optimize_image(image_path)` - resize to 500x500, optimize
  - Return: Path to saved cover image

**Integration Points:**
- POST `/api/audiobooks/enrich-metadata` - start enrichment
- GET `/api/audiobooks/{id}/metadata` - retrieve enriched metadata
- PUT `/api/audiobooks/{id}/metadata` - save enriched metadata to Audiobookshelf
- Logs to: `logs/yyyy-mm-dd/enrichment.md`

**Success Criteria:**
- Audible source pulls narrator, publisher, release_year successfully
- Goodreads source pulls series_info and genres
- OpenLibrary acts as fallback for missing fields
- Metadata merged without conflicts (Audible priority)
- Cover art downloaded and embedded
- Title cleaning removes articles consistently

---

## Phase 5: Repair & Replacement System

### 5.1 Failed Verification Handling
**Objective:** Identify audiobooks failing verification and attempt repair

**Implementation:**
- Create `mamcrawler/repair/repair_orchestrator.py`:
  - `RepairOrchestrator` class:
    - `process_failed_verifications(failures)` - reads failure log
    - `identify_replacement_candidates()` - searches Prowlarr for alternatives
    - `verify_candidate(audio_path, metadata)` - runs full verification on replacement
    - `compare_quality(original, replacement)` - checks codec, bitrate, duration match
    - `execute_replacement()` - only if replacement better AND passes verification
  - Return: `{'replaced': bool, 'reason': str, 'new_file': str, 'report': dict}`

### 5.2 Repair Logging & Reporting
**Objective:** Document all repair attempts and results

**Implementation:**
- Create `mamcrawler/repair/repair_reporter.py`:
  - `RepairReporter` class:
    - `log_repair_attempt(audiobook, reason, result)` - append-only
    - `log_failed_repair(audiobook, reason, attempts)` - for manual review
    - `generate_repair_report()` - daily summary
  - Logs to: `logs/yyyy-mm-dd/repairs.md`

**Success Criteria:**
- Failed verifications automatically searched for replacements
- Replacement candidates verified before use
- Only replacements that improve quality are applied
- All repairs logged with before/after metrics
- Unresolved failures flagged for manual intervention

---

## Phase 6: Scheduling & Monitoring System

### 6.1 Daily Monitoring Tasks
**Objective:** Automate recurring searches based on user preferences

**Implementation:**
- Create `mamcrawler/scheduling/monitor.py`:
  - `DailyMonitor` class with scheduled methods:
    - `monitor_author_releases()` - daily check for new titles by watched authors
    - `monitor_series_continuation()` - daily check if series has new books
    - `monitor_genre_releases()` - daily check for new releases in watched genres
    - `monitor_narrator_releases()` - daily check for new titles by watched narrators
    - `monitor_award_winners()` - check latest award winners
  - Each method queries Goodreads/Audible/Prowlarr APIs

### 6.2 Search Templates
**Objective:** Provide reusable search configurations

**Implementation:**
- Create `automation/templates/title-hunt.yaml`:
  ```yaml
  name: "Specific Title Search"
  query: "{title}"
  sources: [goodreads, audible, prowlarr]
  filters: [narrator_optional, year_range_optional]
  ```

- Create `automation/templates/author-complete.yaml`:
  ```yaml
  name: "Complete Author Bibliography"
  query: "author:{author} -read"
  filters: [exclude_read, exclude_duplicates]
  sort: published_date_asc
  ```

- Create `automation/templates/series-complete.yaml`:
  ```yaml
  name: "Complete Series"
  query: "series:{series_name}"
  filters: [chronological_order]
  ```

- Create `automation/templates/genre-search.yaml`:
  ```yaml
  name: "Genre Search"
  query: "genre:{genre} year:>{year_filter}"
  filters: [rating_minimum, duration_filter]
  ```

- Create `automation/templates/narrator-search.yaml`:
  ```yaml
  name: "Narrator Search"
  query: "narrator:{narrator_name}"
  filters: [publication_year, duration]
  ```

- Create `automation/templates/year-filter.yaml`:
  ```yaml
  name: "Year-Based Search"
  query: "published:{year}"
  filters: [genre_optional, rating_minimum]
  ```

- Create `automation/templates/award-list.yaml`:
  ```yaml
  name: "Award Winners"
  sources: ["Audible Awards", "Goodreads Choice", "Audie Awards"]
  year: 2024
  filters: [category, narrator_optional]
  ```

- Create `automation/templates/duration-filter.yaml`:
  ```yaml
  name: "Duration Filter"
  query: "*"
  filters: [min_duration_hours, max_duration_hours]
  ```

### 6.3 Scheduling Backend
**Objective:** Execute daily monitoring and log results

**Implementation:**
- Create `backend/schedulers/daily_monitor_scheduler.py`:
  - Uses APScheduler to run daily at 2:00 AM UTC
  - Executes all monitor methods
  - Collects results into `DailyAcquisitionResults`
  - Logs to: `logs/yyyy-mm-dd/monitoring.md`

- Extend `backend/routes/scheduler.py`:
  - GET `/api/scheduler/daily-results` - yesterday's monitoring results
  - POST `/api/scheduler/test-monitor` - run monitoring immediately
  - GET `/api/scheduler/next-run` - shows when next scheduled run

**Integration Points:**
- POST `/api/audiobooks/queue-from-search` - add search results to download queue
- Automatic integration with qBittorrent for downloads
- Logs to: `logs/yyyy-mm-dd/acquisitions.md`

**Success Criteria:**
- Daily monitoring runs without manual intervention
- All 7 template types functional and tested
- Monitoring results logged daily
- New acquisitions automatically queued for download
- Search results can be approved/rejected before queueing

---

## Phase 7: Reporting & Documentation

### 7.1 Structured Logging
**Objective:** Maintain comprehensive append-only logs for all operations

**Implementation:**
- Create `backend/logging/operation_logger.py`:
  - `OperationLogger` class:
    - `log_acquisition(title, author, source, status)` - tracks obtained audiobooks
    - `log_verification(title, results, passed)` - tracks verification results
    - `log_processing(title, steps_completed, output_path)` - tracks audio processing
    - `log_enrichment(title, fields_added, sources)` - tracks metadata enrichment
    - `log_repair(title, reason, result)` - tracks repair attempts
    - `log_failure(title, reason, retry_count)` - tracks unresolved failures

- Create daily log rotation:
  - `logs/yyyy-mm-dd/acquisitions.md` - append-only
  - `logs/yyyy-mm-dd/verification.md` - append-only
  - `logs/yyyy-mm-dd/processing.md` - append-only
  - `logs/yyyy-mm-dd/enrichment.md` - append-only
  - `logs/yyyy-mm-dd/repairs.md` - append-only
  - `logs/yyyy-mm-dd/monitoring.md` - append-only
  - `logs/yyyy-mm-dd/failures.md` - append-only for unresolved

### 7.2 Daily Report Generation
**Objective:** Provide end-of-day summary of operations

**Implementation:**
- Create `mamcrawler/reporting/daily_reporter.py`:
  - `DailyReporter` class:
    - `generate_daily_summary()` - counts acquisitions, verifications, processing, repairs
    - `identify_failures()` - lists unresolved issues requiring manual action
    - `output_format()` - markdown with tables and metrics
  - Output: `logs/yyyy-mm-dd/DAILY_SUMMARY.md`

**Log Format Example:**
```markdown
# Daily Operations Summary - 2025-11-27

## Acquisitions (8)
- System Overclocked 1 by Randi Darren (Narrator: TBD) - **NEW**
- Fostering Faust by Randi Darren (Narrator: TBD) - **COMPLETE**
- ...

## Verifications (12)
- Passed: 11
- Failed: 1 (Remnant Book 1 - narrator mismatch)

## Processing (10)
- Completed: 9 (1,245 MB total)
- In Progress: 1 (normalization step)

## Enrichment (10)
- Narrator data: 10/10
- Series data: 10/10
- Cover art: 10/10

## Repairs (0)
- No repairs needed today

## Unresolved Issues (1)
- Remnant Book 1: Narrator verification failed, replacement not found
```

**Integration Points:**
- Logs append to Audiobookshelf API via custom endpoint
- Report viewable via `/api/reports/daily/{yyyy-mm-dd}`
- Historical reports available in `/logs/` directory

**Success Criteria:**
- All logs append-only, never overwritten
- Daily summaries generated automatically
- Failure reports highlight manual review items
- Historical logs queryable by date
- All operations traceable from start to finish

---

## Phase 8: Audiobookshelf Integration

### 8.1 Library Metadata Sync
**Objective:** Keep processed audiobooks synchronized with Audiobookshelf

**Implementation:**
- Extend `backend/integrations/abs_client.py`:
  - `update_audiobook_metadata()` - push enriched metadata to Audiobookshelf
  - `mark_audiobook_processed()` - flag in Audiobookshelf when fully processed
  - `tag_audiobooks_by_source()` - apply tags: "randi_darren", "system_overclocked", etc.

### 8.2 Library Statistics API
**Objective:** Provide dashboard metrics

**Implementation:**
- Extend `backend/routes/system.py`:
  - GET `/api/library/statistics` - returns:
    ```json
    {
      "total_audiobooks": 644,
      "processed_today": 8,
      "processing_in_progress": 1,
      "awaiting_repair": 1,
      "total_gb": 1245,
      "narrator_coverage": 0.98,
      "series_coverage": 0.92
    }
    ```

### 8.3 Quality Metrics Tracking
**Objective:** Monitor library quality over time

**Implementation:**
- Create `backend/models/quality_metrics.py`:
  - Store daily metrics: acquisitions, verifications passed/failed, processing completed, repairs
  - Endpoint: GET `/api/metrics/historical` - returns time-series data
  - Chart: Trend analysis of quality metrics over past 30 days

**Success Criteria:**
- All processed audiobooks appear in Audiobookshelf with enriched metadata
- Processing status visible in Audiobookshelf UI
- Daily statistics accurate and updated
- Historical metrics queryable

---

## Phase 9: Implementation Order & Dependencies

### Recommended Implementation Sequence

1. **Phase 1 (Days 1-2): Safety Framework**
   - Safety validator
   - Backup system
   - Audit logging
   - *No dependencies*

2. **Phase 2 (Days 3-4): Verification System**
   - All 4 verification modules
   - Verification orchestrator
   - *Depends on: Phase 1*

3. **Phase 3 (Days 5-6): Audio Processing**
   - Normalizer, Merger, Chapter handler, File namer
   - Processing orchestrator
   - *Depends on: Phase 1, verify ffmpeg/m4b-tool availability*

4. **Phase 4 (Days 7-8): Metadata Enrichment**
   - Three metadata sources (Audible, Goodreads, OpenLibrary)
   - Enrichment orchestrator
   - Cover art handler
   - *Depends on: Phase 1*

5. **Phase 5 (Days 9): Repair System**
   - Repair orchestrator
   - Repair reporter
   - *Depends on: Phase 2, Phase 3, Phase 4*

6. **Phase 6 (Days 10-11): Scheduling**
   - Daily monitor
   - 7 search templates
   - Scheduling backend
   - *Depends on: Phase 1, Prowlarr integration*

7. **Phase 7 (Day 12): Reporting**
   - Operation logger
   - Daily reporter
   - *Depends on: All previous phases*

8. **Phase 8 (Day 13): Audiobookshelf Integration**
   - Library sync
   - Statistics API
   - Quality metrics
   - *Depends on: All previous phases*

9. **Phase 9 (Days 14-15): Testing & Validation**
   - Unit tests for each module
   - Integration tests
   - End-to-end workflow validation
   - *Depends on: All phases complete*

---

## Phase 10: Testing Strategy

### Unit Tests
- Each module has dedicated test file: `backend/tests/test_{module}.py`
- Mock external APIs (Audible, Goodreads, Prowlarr)
- Test both success and failure paths

### Integration Tests
- Test interaction between modules (e.g., Verification → Repair → Processing)
- Verify logs are written correctly
- Test Audiobookshelf API calls

### End-to-End Tests
- Full workflow: Acquisition → Verification → Processing → Enrichment → Sync to Audiobookshelf
- Daily monitoring run with test data
- Report generation validation

### Success Criteria for All Tests
- Minimum 80% code coverage
- All critical paths tested
- All error conditions handled
- Logs verified in all test runs

---

## Summary of Deliverables

**Files to Create:** 40+ new Python modules
**Configuration Templates:** 8 YAML files
**Database Migrations:** 3 new tables (verification_results, repair_log, quality_metrics)
**API Endpoints:** 12 new endpoints
**Scheduled Jobs:** 7 daily monitoring tasks
**Documentation:** Full docstrings + architecture guide

**System Capabilities After Completion:**
- Automated audiobook acquisition from Prowlarr/qBittorrent
- Comprehensive verification (narrator, duration, ISBN, chapters)
- Automatic audio processing (normalize, merge, chapters, rename)
- Metadata enrichment from 3 authoritative sources
- Automatic repair/replacement of failed audiobooks
- Daily monitoring for new releases by author/series/narrator/genre
- Complete audit trail and reporting
- Audiobookshelf integration and sync

**Non-Destructive Operations:**
- All .env protected
- All metadata.json backed up before editing
- No audio files deleted unless verified better replacement found
- DRM removal disabled by default (opt-in only)
- All operations logged and auditable

---

**Ready for implementation. All phases clearly defined with specific files, classes, methods, and success criteria.**
