# absToolbox Integration Improvements Guide

**Date**: November 27, 2025
**Status**: Ready for Implementation
**Priority**: High (All three improvements have measurable impact)

---

## Overview

This guide addresses three critical improvement areas identified during the workflow test:

1. **Continue with absToolbox improvements** - Enhance phases 8B, 8C, 8D
2. **Address narrator population gap** - 100% of library missing narrator data
3. **Fix Phase 8C API permission issues** - Standardization updates failing

---

## Problem 1: Phase 8C API Permission Issues

### Current Status
- **Phase 8C Location**: execute_full_workflow.py, lines 670-766
- **Issue**: PATCH requests to `/api/items/{item_id}` returning 403 Forbidden
- **Impact**: Cannot update metadata fields programmatically
- **Root Cause**: Incorrect JSON payload format or insufficient token permissions

### Root Cause Analysis

The issue is in **line 739** of execute_full_workflow.py:

```python
json={'mediaMetadata': updates},  # WRONG - this key doesn't exist
```

AudiobookShelf API expects:
```python
json={'media': {'metadata': updates}}  # CORRECT - nested structure
```

### Solution 1A: Fix API Payload Structure

**File**: execute_full_workflow.py, line 736-741

**Current (Broken)**:
```python
async with session.patch(
    f'{self.abs_url}/api/items/{item_id}',
    headers=headers,
    json={'mediaMetadata': updates},  # Wrong key
    timeout=aiohttp.ClientTimeout(total=30)
) as update_resp:
```

**Fixed Version**:
```python
async with session.patch(
    f'{self.abs_url}/api/items/{item_id}',
    headers=headers,
    json={'media': {'metadata': updates}},  # Correct nested structure
    timeout=aiohttp.ClientTimeout(total=30)
) as update_resp:
```

### Solution 1B: Add Token Verification

Add a pre-flight check to verify token permissions:

```python
async def verify_abs_token_permissions(self) -> bool:
    """Verify ABS token has write permissions"""
    try:
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {self.abs_token}'}

            # Try to get token info
            async with session.get(
                f'{self.abs_url}/api/me',
                headers=headers
            ) as resp:
                if resp.status == 200:
                    user_info = await resp.json()
                    is_admin = user_info.get('isAdmin', False)
                    if is_admin:
                        self.log("Token has admin permissions", "OK")
                        return True
                    else:
                        self.log("WARNING: Token is not admin, updates may fail", "WARN")
                        return False
    except Exception as e:
        self.log(f"Could not verify token: {e}", "WARN")
        return False
```

### Solution 1C: Implement Retry Logic with Fallback

```python
async def update_item_metadata_with_retry(self, session, item_id, updates, max_retries=3):
    """Update item metadata with retry logic and fallback"""
    headers = {'Authorization': f'Bearer {self.abs_token}'}

    for attempt in range(max_retries):
        try:
            async with session.patch(
                f'{self.abs_url}/api/items/{item_id}',
                headers=headers,
                json={'media': {'metadata': updates}},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in [200, 204]:
                    return True
                elif resp.status == 403:
                    # Permission issue - log and abort
                    error_text = await resp.text()
                    self.log(f"Permission denied (403): {error_text}", "WARN")
                    return False
                elif resp.status == 404:
                    # Item not found - skip
                    self.log(f"Item {item_id} not found (404)", "WARN")
                    return False
                else:
                    # Other errors - retry
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        self.log(f"Failed after {max_retries} attempts: {resp.status}", "WARN")
                        return False
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
                continue
            else:
                self.log(f"Error updating {item_id}: {e}", "WARN")
                return False

    return False
```

### Solution 1D: Add Web UI Alternative Instructions

For users experiencing persistent permission issues, provide absToolbox Web UI instructions:

```python
async def suggest_web_ui_alternative(self):
    """Log instructions for using absToolbox Web UI instead"""
    self.log("=" * 80, "WARN")
    self.log("Phase 8C Update Failed - Using absToolbox Web UI Instead", "WARN")
    self.log("=" * 80, "WARN")
    self.log("", "WARN")
    self.log("1. Visit: https://abstoolbox.vito0912.de", "WARN")
    self.log("2. Connect to your AudiobookShelf server", "WARN")
    self.log("3. Authenticate with your ABS token", "WARN")
    self.log("4. Select 'Metadata Standardization' tool", "WARN")
    self.log("5. Apply author name and narrator fixes", "WARN")
    self.log("6. Review changes in dry-run mode first", "WARN")
    self.log("", "WARN")
    self.log("=" * 80, "WARN")
```

---

## Problem 2: Narrator Population Gap

### Current Status
- **Finding**: 0 narrators across 50,000 items (100% gap)
- **Phase Location**: Phase 8D, lines 768-850
- **Impact**: Cannot perform narrator-based search, filtering, or organization
- **Priority**: CRITICAL - This is the largest metadata gap

### Root Cause
Library was populated without narrator information. No fallback source available in AudiobookShelf API responses.

### Solution 2A: Google Books API Narrator Detection

Leverage Google Books API to populate narrator data:

```python
async def populate_narrators_from_google_books(self, authors_list) -> Dict:
    """Detect and populate narrator info from Google Books API"""
    self.log("PHASE 8E: NARRATOR POPULATION (Google Books)", "PHASE")

    google_key = os.getenv('GOOGLE_BOOKS_API_KEY')
    if not google_key:
        self.log("Google Books API key not configured", "WARN")
        return {'error': 'Google Books API key missing'}

    populated = 0
    failed = 0

    try:
        async with aiohttp.ClientSession() as session:
            headers = {'Authorization': f'Bearer {self.abs_token}'}

            # Get all books
            async with session.get(
                f'{self.abs_url}/api/libraries',
                headers=headers
            ) as resp:
                libs = (await resp.json())['libraries']
                lib_id = libs[0]['id']

            # Process books in batches
            offset = 0
            while True:
                async with session.get(
                    f'{self.abs_url}/api/libraries/{lib_id}/items',
                    headers=headers,
                    params={'limit': 50, 'offset': offset}
                ) as resp:
                    if resp.status != 200:
                        break

                    items = (await resp.json()).get('results', [])
                    if not items:
                        break

                    for item in items:
                        metadata = item.get('media', {}).get('metadata', {})
                        narrator = metadata.get('narrator', '').strip()

                        # Skip if already has narrator
                        if narrator:
                            continue

                        title = metadata.get('title', '')
                        author = metadata.get('authorName', '')

                        if not title or not author:
                            failed += 1
                            continue

                        # Query Google Books for narrator
                        narrator_found = await self.query_google_books_narrator(
                            session, google_key, title, author
                        )

                        if narrator_found:
                            # Update item with narrator
                            update_success = await self.update_item_metadata_with_retry(
                                session,
                                item.get('id'),
                                {'narrator': narrator_found},
                                max_retries=2
                            )
                            if update_success:
                                populated += 1
                            else:
                                failed += 1
                        else:
                            failed += 1

                        # Rate limit Google Books requests
                        await asyncio.sleep(0.5)

                    offset += 50

    except Exception as e:
        self.log(f"Narrator population error: {e}", "FAIL")

    self.log(f"Narrator population complete: {populated} added, {failed} failed", "OK")
    return {
        'populated': populated,
        'failed': failed,
        'timestamp': datetime.now().isoformat()
    }

async def query_google_books_narrator(self, session, api_key, title, author):
    """Query Google Books API for narrator information"""
    try:
        query = f"{title} {author}"
        url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            'q': query,
            'key': api_key,
            'maxResults': 1,
            'projection': 'full'
        }

        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                result = await resp.json()
                volumes = result.get('items', [])

                if volumes:
                    item = volumes[0]
                    # Try to extract narrator from description or other fields
                    description = item.get('volumeInfo', {}).get('description', '')

                    # Look for "narrated by" pattern
                    if 'narrated by' in description.lower():
                        # Extract narrator name
                        import re
                        match = re.search(r'narrated by ([^,.]+)', description, re.IGNORECASE)
                        if match:
                            return match.group(1).strip()

        return None
    except Exception as e:
        self.log(f"Google Books query error: {e}", "WARN")
        return None
```

### Solution 2B: Goodreads Narrator Extraction

Use Goodreads data as secondary source:

```python
async def populate_narrators_from_goodreads(self, books_list) -> Dict:
    """Extract narrator info from Goodreads"""
    self.log("Populating narrators from Goodreads...", "NARRATOR")

    # Use Goodreads API to find audiobook editions
    # Goodreads returns audiobook format info with narrator

    populated = 0

    for book in books_list:
        try:
            # Search Goodreads for audiobook edition
            audiobook_info = await self.search_goodreads_audiobook(
                book.get('title'),
                book.get('author')
            )

            if audiobook_info and audiobook_info.get('narrator'):
                # Update AudiobookShelf with narrator
                await self.update_item_metadata_with_retry(
                    session,
                    book.get('id'),
                    {'narrator': audiobook_info['narrator']},
                    max_retries=2
                )
                populated += 1
        except Exception as e:
            self.log(f"Goodreads lookup error for {book.get('title')}: {e}", "WARN")

    return {'populated': populated}
```

### Solution 2C: Manual Bulk Upload Template

Provide a CSV template for manual narrator population:

**File**: `templates/narrator_import.csv`

```csv
title,author,narrator
"The Hobbit","J.R.R. Tolkien","Rob Inglis"
"Foundation","Isaac Asimov","Scott Brick"
"Dune","Frank Herbert","Scott Brick"
```

**Script to import**:
```python
async def import_narrators_from_csv(self, csv_path: str) -> Dict:
    """Import narrator data from CSV file"""
    self.log(f"Importing narrators from {csv_path}", "NARRATOR")

    import csv

    imported = 0
    failed = 0

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                title = row.get('title', '').strip()
                narrator = row.get('narrator', '').strip()

                if not title or not narrator:
                    failed += 1
                    continue

                # Find and update item
                update_success = await self.find_and_update_item_narrator(
                    title, narrator
                )

                if update_success:
                    imported += 1
                else:
                    failed += 1

    except Exception as e:
        self.log(f"CSV import error: {e}", "FAIL")

    self.log(f"Import complete: {imported} updated, {failed} failed", "OK")
    return {'imported': imported, 'failed': failed}
```

### Solution 2D: Narrator Detection from Title/Description

Extract narrator info from existing fields:

```python
def extract_narrator_from_metadata(self, item) -> Optional[str]:
    """Try to extract narrator from existing metadata"""
    metadata = item.get('media', {}).get('metadata', {})

    # Check description for narrator hints
    description = metadata.get('description', '') or metadata.get('summary', '')
    if 'narrated by' in description.lower():
        import re
        match = re.search(r'narrated by ([^,.;]+)', description, re.IGNORECASE)
        if match:
            narrator = match.group(1).strip()
            # Remove common suffixes
            narrator = narrator.replace('Jr.', '').replace('Sr.', '').strip()
            return narrator

    # Check subtitle
    subtitle = metadata.get('subtitle', '')
    if subtitle and 'narrated by' in subtitle.lower():
        import re
        match = re.search(r'narrated by ([^,.;]+)', subtitle, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return None
```

---

## Problem 3: Continue with absToolbox Improvements

### Current absToolbox Capabilities

**Phase 8B - Quality Validation** ✅ Working
- Identifies missing author names
- Detects narrator field gaps
- Reports format issues

**Phase 8C - Standardization** ⚠️ Needs API fix
- Author name normalization
- Narrator prefix removal
- Series name standardization

**Phase 8D - Narrator Detection** ✅ Working
- Scans full library
- Builds narrator frequency map
- Reports coverage gaps

### Enhancement 3A: Add Phase 8E - Narrator Population

```python
async def execute(self) -> None:
    """Main workflow execution with new Phase 8E"""

    # ... existing phases 1-8D ...

    # NEW: Phase 8E - Narrator Population
    self.log("PHASE 8E: NARRATOR POPULATION", "PHASE")
    narrator_result = await self.populate_narrators_from_google_books(
        authors_to_focus=['Brandon Sanderson', 'Robert Jordan', 'Terry Pratchett']
    )
    self.log(f"Phase 8E Result: {narrator_result.get('populated')} narrators added", "OK")
```

### Enhancement 3B: Add Phase 8F - Quality Recheck

```python
async def recheck_metadata_quality(self) -> Dict:
    """Phase 8F: Recheck quality after standardization"""
    self.log("PHASE 8F: QUALITY RECHECK", "PHASE")

    # Get updated items
    async with aiohttp.ClientSession() as session:
        headers = {'Authorization': f'Bearer {self.abs_token}'}

        async with session.get(
            f'{self.abs_url}/api/libraries',
            headers=headers
        ) as resp:
            lib_id = (await resp.json())['libraries'][0]['id']

        # Recheck quality on recent items
        async with session.get(
            f'{self.abs_url}/api/libraries/{lib_id}/items',
            headers=headers,
            params={'limit': 100, 'sortBy': 'updatedAt'}
        ) as resp:
            items = (await resp.json()).get('results', [])

        # Compare with Phase 8B results
        improvement_count = 0
        for item in items:
            metadata = item.get('media', {}).get('metadata', {})

            # Check if narrator was populated
            if metadata.get('narrator'):
                improvement_count += 1

        self.log(f"Quality Improvement: {improvement_count} items now have narrator info", "OK")

        return {
            'improvements': improvement_count,
            'total_checked': len(items)
        }
```

### Enhancement 3C: Add Dry-Run Mode for Phase 8C

```python
async def standardize_metadata_abstoolbox(self, dry_run=True) -> Dict:
    """Phase 8C with dry-run capability"""
    self.log(f"PHASE 8C: STANDARDIZE METADATA (dry_run={dry_run})", "PHASE")

    # ... existing logic ...

    if dry_run:
        self.log("DRY-RUN MODE: No changes will be applied", "WARN")
        # Just return what would change, don't apply
        return {
            'processed': len(items),
            'would_standardize': len(changes_made),
            'changes': changes_made,
            'dry_run': True
        }
    else:
        # Apply actual changes
        # ... existing update logic ...
        return {
            'processed': len(items),
            'standardized': standardized,
            'changes': changes_made,
            'dry_run': False
        }
```

### Enhancement 3D: Add Summary Statistics

```python
async def generate_abstoolbox_summary(self, phase_8b, phase_8c, phase_8d, phase_8e=None) -> Dict:
    """Generate comprehensive absToolbox summary"""
    summary = {
        'quality_validation': {
            'checked': phase_8b.get('checked'),
            'issues_found': phase_8b.get('issues_count'),
            'issue_rate': f"{(phase_8b.get('issues_count', 0) / phase_8b.get('checked', 1) * 100):.1f}%"
        },
        'standardization': {
            'processed': phase_8c.get('processed'),
            'standardized': phase_8c.get('standardized'),
            'success_rate': f"{(phase_8c.get('standardized', 0) / phase_8c.get('processed', 1) * 100):.1f}%"
        },
        'narrator_detection': {
            'total_items': phase_8d.get('total_items'),
            'with_narrator': phase_8d.get('with_narrator'),
            'coverage': f"{(phase_8d.get('with_narrator', 0) / phase_8d.get('total_items', 1) * 100):.1f}%"
        }
    }

    if phase_8e:
        summary['narrator_population'] = {
            'populated': phase_8e.get('populated'),
            'failed': phase_8e.get('failed')
        }

    return summary
```

---

## Implementation Roadmap

### Immediate (Today - Next Few Hours)
- [ ] Fix Phase 8C API payload structure (1-2 lines of code)
- [ ] Add token verification function (10 lines)
- [ ] Test with fixed payload

### Short Term (This Week)
- [ ] Implement retry logic for Phase 8C
- [ ] Add Web UI alternative instructions
- [ ] Test Phase 8C standardization with fixed API calls

### Medium Term (Next 2 Weeks)
- [ ] Implement Phase 8E - Google Books narrator population
- [ ] Create narrator import CSV template
- [ ] Add Phase 8F - Quality recheck
- [ ] Test end-to-end with narrator population

### Long Term (Next Month)
- [ ] Add Goodreads narrator extraction
- [ ] Implement Phase 8G - Advanced metadata enrichment
- [ ] Create absToolbox dashboard/reporting
- [ ] Schedule daily/weekly narrator population jobs

---

## Testing Plan

### Phase 8C Fix Testing
```bash
# 1. Run workflow with fixed API payload
python execute_full_workflow.py

# 2. Check log for successful updates
grep "Standardized" real_workflow_execution.log

# 3. Verify items were updated in AudiobookShelf UI
```

### Phase 8E Testing (Once Implemented)
```bash
# 1. Test Google Books API integration
python -c "
import asyncio
from execute_full_workflow import FullWorkflow

wf = FullWorkflow(...)
result = asyncio.run(wf.populate_narrators_from_google_books(['Brandon Sanderson']))
print(result)
"

# 2. Verify narrators were populated
# Check AudiobookShelf UI for narrator field population
```

---

## Success Metrics

| Metric | Current | Target | Timeline |
|--------|---------|--------|----------|
| Phase 8C Success Rate | 0% | 90%+ | 1 day |
| Narrator Coverage | 0% | 50% | 2 weeks |
| Metadata Issues | 100/100 items | <20/100 items | 3 weeks |
| Quality Score | Low | High | 1 month |

---

## Files to Modify

1. **execute_full_workflow.py**
   - Line 739: Fix API payload structure
   - Lines 670-766: Add retry logic, token verification
   - New section: Add Phase 8E and 8F methods
   - New section: Add narrator population functions

2. **Templates** (to create)
   - `templates/narrator_import.csv` - CSV import template
   - `NARRATOR_POPULATION_GUIDE.md` - User guide

3. **Documentation** (to update)
   - `ABSTOOLBOX_IMPLEMENTATION_SUMMARY.md` - Add new phases
   - `WORKFLOW_PHASES_DOCUMENTATION.md` - Document Phase 8E, 8F

---

## Risk Mitigation

**Risk**: API changes break Phase 8C again
**Mitigation**: Add comprehensive error handling, logging, and fallback to Web UI

**Risk**: Google Books API rate limiting during narrator population
**Mitigation**: Implement configurable delays, batch processing, retry logic

**Risk**: Narrator data quality issues
**Mitigation**: Validate narrator format, add manual review step, create override mechanism

---

## Questions for User

Before implementing, clarify:

1. **Phase 8C API Fix**: Should I apply the API payload structure fix immediately?
2. **Narrator Priority**: Do you want to prioritize specific authors for narrator population?
3. **Google Books**: Do you want automated narrator extraction, or prefer manual CSV import first?
4. **Testing**: Should I test against your live library or create a test subset first?

---

**Created**: November 27, 2025
**Status**: Ready for Review and Implementation

