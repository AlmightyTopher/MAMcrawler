# absToolbox Integration Guide

## Overview

**absToolbox** is a collection of tools designed to assist with AudiobookShelf metadata management tasks. It provides both web-based and legacy Python-based interfaces for manipulating audiobook metadata at scale.

**Repository**: https://github.com/Vito0912/absToolbox
**Web Interface**: https://abstoolbox.vito0912.de
**Language**: TypeScript/Vue (modern) | Python (legacy)

---

## Integration Purpose in MAMcrawler

The absToolbox integration enables MAMcrawler to:

1. **Batch Metadata Editing** - Apply consistent metadata across multiple books
2. **Series Completion** - Automatically organize books by series
3. **Author Management** - Link books to correct authors
4. **Narrator Detection** - Identify and tag narrators
5. **Quality Rules Enforcement** - Apply custom metadata rules
6. **Bulk Operations** - Perform operations on 100+ books efficiently

---

## Access Methods

### Method 1: Web Interface (Recommended)

**Advantages:**
- No installation required
- Visual interface for safe operations
- Real-time preview before applying changes
- Works with local AudiobookShelf servers

**Steps:**
1. Navigate to https://abstoolbox.vito0912.de
2. Connect to local AudiobookShelf server (http://localhost:13378)
3. Authenticate with ABS token
4. Select desired tool from menu
5. Configure parameters
6. Review changes
7. Apply to library

### Method 2: Docker Deployment

**For self-hosted setup:**
```bash
docker run -p 3000:3000 vito0912/abstoolbox:latest
```

Access at `http://localhost:3000`

### Method 3: Legacy Python Scripts (Not Recommended)

**Status**: Deprecated - Use web interface instead

**Warning**: "All scripts may have unforeseen side effects or might even crash the server completely"

**If using:**
```bash
git clone https://github.com/Vito0912/absToolbox.git
cd absToolbox
# Edit scripts with your configuration
python script_name.py
```

---

## Available Tools & Their Purposes

### 1. Metadata Editor
**Purpose**: Bulk edit metadata fields (title, author, series, narrator, etc.)

**Use Cases:**
- Fix incorrect author names across multiple books
- Add missing series information
- Correct narrator names and spelling
- Update cover images

**Recommended Usage Pattern:**
```
1. Export current library state
2. Identify issues (duplicates, inconsistencies)
3. Apply metadata fixes
4. Verify changes in ABS
5. Document applied rules for future automation
```

### 2. Series Organizer
**Purpose**: Organize books into series and set proper book numbers

**Use Cases:**
- Group books by series name
- Auto-assign book numbers within series
- Sort series by publication order
- Link prequels/sequels

**Recommended Usage Pattern:**
```
1. Identify series from book titles/metadata
2. Create series groupings
3. Assign sequential numbers
4. Verify ordering matches publication date
5. Add series descriptions
```

### 3. Author Linker
**Purpose**: Link books to correct author records

**Use Cases:**
- Merge duplicate author records
- Link co-authored works to all authors
- Organize author discographies
- Create author collections

**Recommended Usage Pattern:**
```
1. Scan for duplicate author names (variations)
2. Merge variants to primary author record
3. Link all books to correct author
4. Update author metadata (biography, image)
5. Generate author statistics
```

### 4. Narrator Detector
**Purpose**: Extract and standardize narrator information

**Use Cases:**
- Extract narrator names from metadata
- Standardize narrator name spelling
- Create narrator-based collections
- Track narrators across series

**Recommended Usage Pattern:**
```
1. Scan library for narrator information
2. Extract narrator names from titles/descriptions
3. Standardize spelling and formatting
4. Create narrator database
5. Tag books by narrator
```

### 5. Batch Operations
**Purpose**: Apply operations to multiple books simultaneously

**Use Cases:**
- Update metadata for all books by author
- Apply formatting rules to entire series
- Add tags/genres in bulk
- Rename/relocate files

**Recommended Usage Pattern:**
```
1. Define selection criteria (author, series, genre)
2. Preview affected books
3. Define operation parameters
4. Execute batch operation
5. Verify changes
6. Document for future runs
```

---

## Integration with MAMcrawler Workflow

### Integration Points

**Phase 8 Enhancement: Metadata Sync with absToolbox**

```
Current Flow:
  PHASE 8: Sync Metadata (API calls)
  ↓
  Query Google Books API
  Query Goodreads for metadata
  Update ABS records

Enhanced Flow:
  PHASE 8A: Query APIs for metadata
  PHASE 8B: Apply absToolbox rules
  PHASE 8C: Batch standardization via absToolbox
  PHASE 8D: Verify and log changes
```

### Safety Protocols

**CRITICAL**: Before running absToolbox operations:

1. **Create Backup**
   ```bash
   # In AudiobookShelf: Settings > Backups > Create Backup
   # Or manual: Backup database and metadata files
   ```

2. **Test on Sample**
   - Run operation on 5-10 books first
   - Verify changes before full library
   - Document any side effects

3. **Monitor Execution**
   - Keep server logs open
   - Monitor CPU/memory usage
   - Be ready to stop operation if issues occur

4. **Verify Results**
   - Check affected books in ABS UI
   - Verify metadata is correct
   - Ensure no file corruption

5. **Document Changes**
   - Log operation name and parameters
   - Record number of items affected
   - Note any errors or edge cases
   - Keep rules for future automation

---

## Template: Metadata Standardization Operation

```yaml
# absToolbox Metadata Standardization Template
# Purpose: Apply consistent metadata formatting across library

operation_name: "Standardize Author Names and Series"
operation_type: "batch_edit"
target_library: "local_abs_server"

authentication:
  abs_url: "http://localhost:13378"
  abs_token: "${ABS_TOKEN}"

selection_criteria:
  # Select books matching these criteria
  filters:
    - match_field: "author_name"
      contains: [".", ","]  # Author names with special characters
      action: "standardize"

operations:
  - step: 1
    name: "Fix Author Name Formatting"
    rules:
      - field: "author_name"
        find_replace:
          - pattern: "([A-Z][a-z]+),\s*([A-Z][a-z]+)"
            replacement: "$2 $1"  # Convert "Smith, John" to "John Smith"
          - pattern: "\s{2,}"
            replacement: " "  # Remove extra spaces
    preview: true
    confirm_before: true

  - step: 2
    name: "Standardize Series Names"
    rules:
      - field: "series_name"
        find_replace:
          - pattern: "Series\s*#?"
            replacement: ""
          - pattern: "\s*Vol\\.?\s*"
            replacement: " - Volume "
    preview: true
    confirm_before: true

  - step: 3
    name: "Add Missing Narrator Information"
    rules:
      - field: "narrator"
        condition: "empty"
        action: "extract_from_title"
        pattern: "Narrated by (.+)$"
    preview: true
    confirm_before: true

backup_before: true
log_changes: true
rollback_available: true

execution:
  max_items: 500
  batch_size: 50
  delay_between_batches_ms: 1000
  timeout_per_item_ms: 5000

success_criteria:
  - all_items_processed_successfully
  - no_critical_errors
  - metadata_validated_post_operation

notifications:
  - notify_on_completion
  - log_any_warnings
  - generate_change_report
```

---

## Template: Series Completion Operation

```yaml
# absToolbox Series Completion Template
# Purpose: Identify missing books in series and prepare queue

operation_name: "Complete Author Series"
operation_type: "series_completion"

target_author: "${AUTHOR_NAME}"

steps:
  1_scan_library:
    action: "get_books_by_author"
    author: "${AUTHOR_NAME}"
    return: "list_of_books_with_series"

  2_identify_gaps:
    action: "cross_reference_goodreads"
    author: "${AUTHOR_NAME}"
    return: "books_not_in_library"
    match_on: "exact_title_match"

  3_create_queue:
    action: "generate_download_queue"
    items: "missing_books"
    priority: "publication_date_ascending"
    output: "queue_file"

  4_tag_books:
    action: "tag_existing_books"
    tags: ["series_name", "complete_status"]
    complete_percentage: "books_in_library / total_books * 100"

output:
  - missing_books_list: "json"
  - download_queue: "csv"
  - completion_report: "markdown"

metadata_to_update:
  series_complete: false
  missing_count: "total - in_library"
  completion_percentage: "calculated"
```

---

## Template: Bulk Quality Rules

```yaml
# absToolbox Quality Rules Template
# Purpose: Enforce consistent metadata quality standards

rule_set_name: "AudioBook Quality Standards"
version: "1.0"

rules:
  author_name:
    required: true
    format: "FirstName LastName"
    min_length: 2
    max_length: 100
    reject_if:
      - contains: "Unknown"
      - contains: "Anonymous"
      - matches: "^\d+$"  # Numeric only

  narrator:
    required: true
    format: "FirstName LastName"
    standardize_on_match: true

  series_name:
    required: false
    reject_if:
      - contains: "TBD"
      - contains: "TBA"
    warn_if:
      - missing_book_number: true

  cover_art:
    required: true
    warn_if:
      - file_size_mb: "> 2"
      - dimensions_pixels: "< 300x300"

  description:
    required: false
    warn_if:
      - length_chars: "< 50"
      - length_chars: "> 5000"

  rating:
    required: false
    range: "0-5"
    decimal_places: 1

enforcement:
  auto_fix:
    - whitespace_normalization
    - case_standardization
    - special_character_handling

  manual_review_required:
    - missing_required_fields
    - suspicious_metadata
    - duplicate_detection

reporting:
  generate_quality_report: true
  flag_non_compliant_books: true
  suggest_corrections: true
```

---

## Integration Implementation Steps

### Step 1: Create absToolbox Configuration Module

Create `backend/integrations/abstoolbox_client.py`:
```python
"""
absToolbox Integration Client
Provides async interface to absToolbox operations
"""

import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class absToolboxClient:
    """Client for interacting with absToolbox services"""

    def __init__(
        self,
        abs_url: str,
        abs_token: str,
        toolbox_url: Optional[str] = None
    ):
        self.abs_url = abs_url
        self.abs_token = abs_token
        self.toolbox_url = toolbox_url or "https://abstoolbox.vito0912.de"

    async def standardize_metadata(
        self,
        operation_template: Dict[str, Any],
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Execute metadata standardization operation"""
        logger.info(f"Starting metadata standardization (dry_run={dry_run})")
        # Implementation
        pass

    async def complete_series(
        self,
        author_name: str
    ) -> Dict[str, Any]:
        """Identify and queue missing books in series"""
        logger.info(f"Analyzing series for author: {author_name}")
        # Implementation
        pass

    async def validate_metadata_quality(
        self,
        quality_rules: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate library against quality rules"""
        logger.info("Running quality validation")
        # Implementation
        pass

    async def batch_update_metadata(
        self,
        book_ids: List[str],
        metadata_updates: Dict[str, Any],
        backup_first: bool = True
    ) -> Dict[str, Any]:
        """Apply metadata updates to multiple books"""
        logger.info(f"Batch updating {len(book_ids)} books")
        # Implementation
        pass
```

### Step 2: Create Workflow Phase 8B

Update `execute_full_workflow.py` to include absToolbox operations:
```python
async def sync_metadata_with_abstoolbox(self) -> Dict:
    """Phase 8B: Apply absToolbox metadata standardization"""
    self.log("PHASE 8B: Apply absToolbox Metadata Rules", "PHASE")

    # Load quality rules template
    quality_rules = self.load_quality_rules_template()

    # Validate metadata quality
    validation_result = await self.abs_toolbox.validate_metadata_quality(
        quality_rules
    )

    # Apply standardization
    std_result = await self.abs_toolbox.standardize_metadata(
        operation_template=self.get_standardization_template(),
        dry_run=True  # First pass
    )

    # Log results
    self.log(f"Quality issues found: {validation_result.get('issues_count', 0)}", "WARN")
    self.log(f"Standardization preview: {std_result.get('preview_count')} items", "OK")

    return validation_result
```

### Step 3: Create Documentation Template

Create `ABSTOOLBOX_OPERATION_LOG.md` for tracking operations:
```markdown
# absToolbox Operation Log

Date: YYYY-MM-DD
Operation: [Operation Name]
Status: [IN_PROGRESS / COMPLETED / FAILED]

## Configuration
- Template: [Template Name]
- Target: [Number] items
- Dry Run: [Yes/No]

## Pre-Execution
- Backup Created: [Yes/No]
- Backup Path: [Path]
- Affected Books: [List]

## Execution
- Start Time: [Timestamp]
- End Time: [Timestamp]
- Duration: [Minutes]
- Items Processed: [Number]
- Success Rate: [Percentage]

## Changes Made
- [Change 1]
- [Change 2]
- [Change 3]

## Issues Encountered
- [Issue 1]
- [Issue 2]

## Verification
- Manual Verification: [In Progress / Completed]
- Issues Found: [Number]
- Rollback Required: [Yes/No]

## Notes
[Additional observations]
```

---

## Safety Checklist

Before executing any absToolbox operation:

- [ ] Created backup in AudiobookShelf settings
- [ ] Tested operation on sample (5-10 books)
- [ ] Reviewed operation parameters
- [ ] Confirmed dry run shows expected changes
- [ ] Logged operation with timestamp and configuration
- [ ] Monitoring server logs during execution
- [ ] Prepared rollback plan if needed
- [ ] Verified results post-execution
- [ ] Documented results and any issues
- [ ] Notified team of changes made

---

## Troubleshooting

### Operation Crashes Server
- Stop operation immediately
- Restore from backup
- Report to absToolbox GitHub issues
- Use smaller batch size (50 instead of 500)

### Metadata Not Applied
- Verify ABS token is valid
- Check server logs for errors
- Retry operation with dry_run=true
- Verify book IDs are correct

### Performance Issues
- Reduce batch_size parameter
- Increase delay_between_batches_ms
- Close other applications
- Monitor server resources

### Unexpected Changes
- Revert using backup
- Review operation template for errors
- Test template on new sample
- Contact absToolbox maintainer

---

## References

- **Repository**: https://github.com/Vito0912/absToolbox
- **Web Interface**: https://abstoolbox.vito0912.de
- **AudiobookShelf Docs**: https://www.audiobookshelf.org/docs
- **GitHub Issues**: https://github.com/Vito0912/absToolbox/issues

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-27 | Initial integration guide |

