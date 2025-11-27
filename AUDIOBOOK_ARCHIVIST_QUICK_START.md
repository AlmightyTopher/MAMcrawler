# Audiobook Archivist - Quick Start Guide

**For Developers:** Reference guide for using the implemented Phase 1-2 modules

---

## Phase 1: Safety Framework

### Using the Safety Validator

```python
from backend.safety_validator import get_safety_validator

validator = get_safety_validator()

# Check if operation is allowed
is_valid, error_msg = validator.validate_operation(
    operation_type="delete_metadata",
    flags={
        "backup_created": True,
        "confirmed_irreversible": True
    }
)

if not is_valid:
    print(f"Operation blocked: {error_msg}")
    exit(1)

# Create backup before editing metadata
success, backup_path = validator.require_backup_before_edit("path/to/metadata.json")
if not success:
    print(f"Backup failed: {backup_path}")
    exit(1)

# Verify backup exists and is valid
if not validator.verify_backup_exists(backup_path):
    print("Backup verification failed")
    exit(1)

# Log operation to audit trail
validator.log_operation(
    operation_type="metadata_update",
    target="Book Title",
    result=True,
    details="Updated series name from X to Y"
)
```

### Using the Operation Logger

```python
from backend.logging.operation_logger import get_operation_logger

logger = get_operation_logger()

# Log new acquisition
logger.log_acquisition(
    title="System Overclocked Book 1",
    author="Randi Darren",
    source="prowlarr",
    status="new",
    details={"magnet_link": "magnet:..."}
)

# Log verification result
logger.log_verification(
    title="System Overclocked Book 1",
    author="Randi Darren",
    passed=True,
    failures=None,
    details={"narrator_confidence": 0.95}
)

# Log failed verification
logger.log_verification(
    title="Some Book",
    author="Some Author",
    passed=False,
    failures=["narrator_mismatch", "duration_out_of_range"],
    details={"actual_duration": 3600, "expected_duration": 3700}
)

# Get today's log
log_content = logger.get_todays_log('verification')
print(log_content)

# Get summary statistics
summary = logger.get_category_summary('verification')
print(f"Total verification entries today: {summary['total_entries']}")
print(f"Passed: {summary['status_breakdown'].get('passed', 0)}")
print(f"Failed: {summary['status_breakdown'].get('failed', 0)}")
```

---

## Phase 2: Verification System

### Basic Narrator Verification

```python
from mamcrawler.verification import get_narrator_verifier

narrator_verifier = get_narrator_verifier()

# Extract narrator from audio file
audio_narrator = narrator_verifier.extract_narrator_from_audio("audiobook.m4b")

# Extract narrator from metadata
metadata = {"narrator": "John Smith"}
metadata_narrator = narrator_verifier.extract_narrator_from_metadata(metadata)

# Verify match
result = narrator_verifier.verify_narrator_match(audio_narrator, metadata_narrator)
print(f"Match: {result['match']} (confidence: {result['confidence']:.2f})")
print(f"Primary narrator: {result['narrator_primary']}")
```

### Duration Verification

```python
from mamcrawler.verification import get_duration_verifier

duration_verifier = get_duration_verifier(tolerance_percent=2.0)

# Get actual duration from audio file
actual_duration = duration_verifier.get_actual_duration("audiobook.m4b")
print(f"Actual duration: {actual_duration/3600:.2f} hours")

# Get expected duration from metadata
expected_duration = duration_verifier.get_expected_duration(
    "Book Title",
    "Author Name",
    metadata={"durationMs": 14400000}  # 4 hours in milliseconds
)

# Verify tolerance
result = duration_verifier.verify_tolerance(actual_duration, expected_duration)
print(f"Duration valid: {result['valid']}")
print(f"Variance: {result['variance_percent']:+.2f}%")
```

### ISBN Verification

```python
from mamcrawler.verification import get_isbn_verifier

isbn_verifier = get_isbn_verifier()

# Extract ISBN from metadata
metadata = {"isbn": "978-1-234-56789-0"}
isbn = isbn_verifier.extract_isbn_from_metadata(metadata)

# Verify identifier
result = isbn_verifier.verify_audiobook(metadata)
print(f"ISBN found: {result['isbn']}")
print(f"Valid: {result['valid']}")
```

### Chapter Verification

```python
from mamcrawler.verification import get_chapter_verifier

chapter_verifier = get_chapter_verifier(min_chapters=3)

# Extract chapters from audio file
chapters = chapter_verifier.extract_chapters("audiobook.m4b")
print(f"Found {len(chapters)} chapters")

# Validate chapter structure
structure = chapter_verifier.validate_chapter_structure(chapters)
print(f"Structure valid: {structure['valid']}")

# Check minimum chapters
result = chapter_verifier.verify_minimum_chapters(
    chapter_count=len(chapters),
    title="Book Title",
    is_single_track=False  # Set to True for collections/short stories
)
print(f"Chapters meet minimum: {result['valid']}")
```

### Complete Verification with Orchestrator

```python
from mamcrawler.verification import get_verification_orchestrator

orchestrator = get_verification_orchestrator(max_retries=3)

# Run complete verification
result = orchestrator.verify_audiobook(
    audio_path="path/to/audiobook.m4b",
    metadata={
        "title": "System Overclocked Book 1",
        "author": "Randi Darren",
        "narrator": "Michael Kramer",
        "durationMs": 14400000
    },
    title="System Overclocked Book 1",
    author="Randi Darren"
)

# Check results
if result['passed']:
    print("All verifications passed!")
else:
    print(f"Failed checks: {result['failures']}")
    for check_name, check_result in result['checks'].items():
        print(f"  {check_name}: {check_result}")

# If verification failed, retry
if not result['passed'] and result['retry_count'] < 3:
    print("Retrying verification...")
    result = orchestrator.retry_failed_verification(
        failed_result=result,
        audio_path="path/to/audiobook.m4b",
        metadata={...}
    )

# Generate batch report
all_results = [result1, result2, result3, ...]
report = orchestrator.generate_verification_report(all_results)
print(f"Pass rate: {report['pass_rate']:.1%}")
print(f"Manual review needed: {len(report['items_for_manual_review'])}")
```

---

## Configuration

### Safety Settings (backend/config.py)

```python
# Protect critical operations
PROTECTED_OPERATIONS = [
    "delete_audiobook",
    "delete_metadata",
    "drm_removal",
    "replace_audio_file",
    "modify_env_file"
]

# DRM removal is disabled by default
ALLOW_DRM_REMOVAL = False  # Set to True in .env to enable

# Backup retention policy
BACKUP_ENABLED = True
BACKUP_RETENTION_DAYS = 30  # Auto-cleanup old backups

# Audit logging
AUDIT_LOG_ENABLED = True
```

### Verification Settings

```python
from mamcrawler.verification import get_narrator_verifier, get_duration_verifier

# Narrator confidence threshold
narrator = get_narrator_verifier(confidence_threshold=0.85)  # 85% minimum match

# Duration tolerance
duration = get_duration_verifier(tolerance_percent=2.0)  # ±2% allowed

# Maximum retry attempts
orchestrator = get_verification_orchestrator(max_retries=3)  # 3 retries max
```

---

## Error Handling

### Safety Validator Errors

```python
try:
    success, backup_path = validator.require_backup_before_edit("metadata.json")
    if not success:
        logger.log_failure(
            title="Book Title",
            author="Author",
            reason=f"Backup creation failed: {backup_path}",
            retry_count=0
        )
        raise Exception(backup_path)
except Exception as e:
    print(f"Safety error: {e}")
```

### Verification Errors

```python
try:
    result = orchestrator.verify_audiobook(
        audio_path="nonexistent.m4b",
        metadata={...}
    )
    if not result['passed']:
        logger.log_failure(
            title="Book Title",
            author="Author",
            reason=f"Verification failed: {result['failures']}",
            retry_count=result['retry_count']
        )
except Exception as e:
    logger.log_failure(
        title="Book Title",
        author="Author",
        reason=f"Verification exception: {str(e)}",
        retry_count=0,
        details={"error_type": type(e).__name__}
    )
```

---

## Logging Integration

### Viewing Today's Logs

```bash
# View verification logs
cat logs/2025-11-27/verification.md

# View all acquisition events
cat logs/2025-11-27/acquisitions.md

# View failures requiring manual action
cat logs/2025-11-27/failures.md
```

### Log File Format

Each log is append-only JSON lines, one entry per line:

```json
{"timestamp":"2025-11-27T14:30:00.123456","operation":"verification","target":"Book Title","status":"PASSED","details":"..."}
{"timestamp":"2025-11-27T14:31:00.234567","operation":"verification","target":"Another Book","status":"FAILED","details":"..."}
```

---

## Common Workflows

### Workflow 1: Verify New Audiobook Import

```python
from mamcrawler.verification import get_verification_orchestrator
from backend.logging.operation_logger import get_operation_logger

orchestrator = get_verification_orchestrator()
logger = get_operation_logger()

# Verify the audiobook
result = orchestrator.verify_audiobook(
    audio_path="/library/new_book.m4b",
    metadata={...},
    title="New Book",
    author="New Author"
)

# Log result
if result['passed']:
    logger.log_verification("New Book", "New Author", True)
    print("Audiobook is ready for library")
else:
    logger.log_verification("New Book", "New Author", False, result['failures'])
    print(f"Please fix: {result['failures']}")
```

### Workflow 2: Batch Verification with Retries

```python
audiobooks = [...]  # List of {audio_path, metadata, title, author}

for audiobook in audiobooks:
    result = orchestrator.verify_audiobook(**audiobook)

    # Retry if failed
    while not result['passed'] and result['retry_count'] < 3:
        print(f"Retrying {audiobook['title']}...")
        result = orchestrator.retry_failed_verification(
            result, audiobook['audio_path'], audiobook['metadata']
        )

    # Log final result
    if result['passed']:
        logger.log_verification(
            audiobook['title'],
            audiobook['author'],
            True
        )
    else:
        logger.log_failure(
            audiobook['title'],
            audiobook['author'],
            f"Failed after {result['retry_count']} retries",
            result['retry_count']
        )

# Generate summary report
summary = orchestrator.generate_verification_report([all_results])
print(f"Summary: {summary['passed']}/{summary['total_verified']} passed")
```

### Workflow 3: Safe Metadata Update

```python
from backend.safety_validator import get_safety_validator

validator = get_safety_validator()

# Validate operation
is_valid, error = validator.validate_operation(
    "metadata_edit",  # Custom operation type
    flags={}
)

# Create backup
success, backup_path = validator.require_backup_before_edit("metadata.json")
if not success:
    print(f"Cannot proceed: {backup_path}")
    exit(1)

# Read old data
with open("metadata.json") as f:
    old_data = json.load(f)

# Prepare new data
new_data = old_data.copy()
new_data["seriesName"] = "New Series Name"

# Verify non-destructive
is_safe, details = validator.verify_non_destructive(
    "metadata.json",
    old_data,
    new_data
)
if not is_safe:
    print(f"Change is destructive: {details}")
    exit(1)

# Apply changes
with open("metadata.json", "w") as f:
    json.dump(new_data, f)

# Verify integrity
if validator.verify_file_integrity("metadata.json", validator.get_file_hash("metadata.json")):
    logger.log_operation(
        "metadata_update",
        "Book Title",
        True,
        f"Updated series name to '{new_data['seriesName']}'"
    )
    print("Metadata updated safely")
```

---

## Troubleshooting

### "ffprobe not found"
- Install ffmpeg: `apt-get install ffmpeg` (Linux) or `brew install ffmpeg` (Mac)
- On Windows, ensure ffmpeg is in PATH

### "Backup creation failed"
- Check `BACKUP_DIR` permissions (default: `backups/`)
- Ensure disk has free space
- Verify metadata.json is readable

### "Narrator fuzzy match fails"
- Check narrator names are strings, not lists
- Try increasing confidence_threshold if false negatives
- Try decreasing confidence_threshold if false positives

### "Verification timeout"
- Check ffprobe is responsive: `ffprobe -h`
- Verify audio file is not corrupted
- Check system load is not excessive

---

## Performance Tips

### For Large Batch Processing
```python
# Process audiobooks in parallel
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(verify_audiobook, audiobooks))
```

### For Memory-Constrained Systems
```python
# Process in chunks instead of all at once
chunk_size = 100
for i in range(0, len(audiobooks), chunk_size):
    chunk = audiobooks[i:i+chunk_size]
    results = [orchestrator.verify_audiobook(**ab) for ab in chunk]
    # Process results immediately, don't keep all in memory
```

---

## What's Next?

Once Phase 1-2 modules are unit tested:

- **Phase 3:** Audio Processing (normalize, merge, chapters, rename)
- **Phase 4:** Metadata Enrichment (Audible, Goodreads, OpenLibrary)
- **Phase 5:** Repair & Replacement (failed audiobook handling)
- **Phase 6:** Scheduling & Monitoring (daily automated searches)
- **Phase 7:** Reporting & Documentation (summary generation)
- **Phase 8:** Audiobookshelf Integration (library sync)
- **Phase 9:** Testing & Validation (full test suite)

See `AUDIOBOOK_ARCHIVIST_BUILD_PROMPT.md` for complete specification.
