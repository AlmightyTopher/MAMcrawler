# Master Audiobook Management System - E2E Test Specifications

## Test Matrix Overview

### Commands to Test
- `--status` - System status and configuration check
- `--update-metadata` - Full metadata enrichment
- `--missing-books` - Missing book detection (series/author priority)
- `--top-search` - Top 10 audiobook search
- `--full-sync` - Complete synchronization workflow

### Provider Coverage
- **Primary**: Google Books API
- **Secondary**: Audiobookshelf ABS API
- **Fallback**: GoodReads, Kindle, Hardcover, Audioteka, Lubimyczytac

### Edge Cases Coverage
- Books vs Audiobooks
- Multi-ISBN editions
- Multi-author/multi-narrator
- Series with gaps
- Unicode/non-ASCII titles
- Very long descriptions
- Empty/missing genres
- Conflicting publication years
- Mismatched series numbering
- Duplicate titles

### Language/Region Coverage
- English (US, UK, CA, AU)
- German (DE)
- French (FR)
- Italian (IT)
- Spanish (ES)
- Japanese (JP)
- Indian (IN)
- Polish (PL)
- Czech (CZ)

## Test Specifications

### 1. System Status Command Tests
- Test configuration detection
- Test environment variable validation
- Test directory creation
- Test API connectivity checks
- Test error handling for missing credentials

### 2. Metadata Update Tests
- Test Google Books API integration
- Test Audiobookshelf API integration
- Test series linking functionality
- Test ISBN resolution
- Test genre enrichment
- Test description enhancement
- Test cover image updating
- Test multi-provider consensus
- Test rate limiting and retry logic
- Test partial failure handling

### 3. Missing Book Detection Tests
- Test series gap detection
- Test author gap detection
- Test priority ordering (series before author)
- Test series numbering validation
- Test report generation
- Test empty series handling

### 4. Top Search Tests
- Test MyAnonamouse crawler integration
- Test search term effectiveness
- Test result ranking algorithm
- Test deduplication logic
- Test rate limiting
- Test error recovery

### 5. Full Sync Tests
- Test workflow orchestration
- Test idempotence on re-run
- Test partial failure recovery
- Test comprehensive reporting
- Test performance optimization

## Acceptance Criteria

### Data Normalization
- All titles/authors/series/years/ISBN/covers/languages/genres/descriptions normalized to unified schema
- Field resolution honors priority: Google > Hardcover > GoodReads > Audioteka > Lubimyczytac
- Consensus logic uses majority or weighted winner with confidence scoring

### Series Management
- Series links consistent across library
- Missing book report lists exact gaps with proper series order
- Series numbering validated and corrected

### Search Results
- Top-search produces exactly 10 ranked items with source evidence
- Deduplication prevents adding existing books

### Performance
- Full-sync updates only changed records
- Idempotent on second run with no unintended differences
- All HTTP errors retried per policy with backoff
- Zero unhandled exceptions
- Coverage ≥80% for critical components

## Artifacts Required

### Coverage Reports
- `./out/tests/coverage/*.html` - HTML coverage reports
- `./out/logs/*.ndjson` - JSONL logs with one event per line

### Data Reports
- `./out/reports/metadata_merged.jsonl` - One record per item with confidence scores
- `./out/reports/missing_books.json` - Missing book detection results
- `./out/reports/top_search.json` - Top 10 search results
- `./out/reports/diffs_before_after.json` - Before/after comparison

### Evidence
- `./out/evidence/http/{provider}/YYYYMMDD_HHMM/*.json` - Raw request/response snippets

## Quality Gates
- No 5xx unhandled errors
- All provider failures captured with backoff
- No schema drift
- All acceptance assertions pass
- Coverage thresholds met