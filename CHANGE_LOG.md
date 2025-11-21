# Project Change Log

## [2025-11-21 10:30:00]
- **Description**: ✅ ALL 12 MISSING FEATURES IMPLEMENTED
- **Reason**: Complete spec compliance - all critical features now implemented
- **Files Created**:
  - mamcrawler/metadata_scanner.py (full metadata scanner)
  - mamcrawler/series_completion.py (series completion logic)
  - mamcrawler/author_series_completion.py (author/series expansion)
  - mamcrawler/edition_replacement.py (quality-based upgrades)
  - mamcrawler/qbittorrent_monitor.py (continuous monitoring)
  - mamcrawler/ratio_emergency.py (VIP protection system)
  - mamcrawler/event_pacing.py (freeleech/bonus detection)
  - mamcrawler/mam_categories.py (all 40 categories + scheduling)
  - mamcrawler/metadata_maintenance.py (weekly/monthly scans)
- **Total Lines**: ~3,500 lines of new code
- **User Action Required**: Yes - Review and integrate into main downloader
- **Status**: ✅ COMPLETE - Ready for integration and testing

## [2025-11-21 09:46:00]
- **Description**: Implemented Missing Core Features (Sections 11, 13, 14)
- **Reason**: Fulfill spec requirements for integrity checks, narrator detection, and Goodreads metadata
- **Files Affected**:
  - mamcrawler/quality.py (full integrity check with ffprobe)
  - mamcrawler/narrator_detector.py (speech-to-text narrator detection)
  - mamcrawler/goodreads.py (Goodreads metadata scraping)
  - mamcrawler/stealth.py (helper functions for Scraper B config)
- **User Action Required**: Yes - Install dependencies:
  - `pip install openai-whisper fuzzywuzzy python-Levenshtein`
  - Ensure `ffmpeg` and `ffprobe` are installed and in PATH
- **Status**: ✅ IMPLEMENTED - Ready for integration testing

## [2025-11-21 09:18:00]
- **Description**: Resolved MAM Login and Added Docker Deployment
- **Reason**: Fixed persistent login issues by implementing cookie-based authentication; created Docker deployment configuration for production use
- **Files Affected**: 
  - mam_audiobook_qbittorrent_downloader.py (cookie-based login)
  - Dockerfile, docker-compose.yml, Dockerfile.proxy (Docker deployment)
  - .dockerignore (build optimization)
  - DEPLOYMENT.md (comprehensive deployment guide)
- **User Action Required**: Yes - Add `uid` and `mam_id` cookies to .env file
- **Status**: ✅ WORKING - Successfully tested and functional

## [2025-11-21 08:30:29]
- **Description**: Updated Metadata Sync to use Scraper B Identity
- **Reason**: Ensure metadata scraping uses WAN IP and human-like behavior (Section 21)
- **Files Affected**: audiobookshelf_metadata_sync.py
- **User Action Required**: No

## [2025-11-21 08:30:29]
- **Description**: Integrated Prowlarr and Updated Downloader Workflow
- **Reason**: Implement Section 7 (Prowlarr -> MAM Fallback) and Section 21.4 (IP Validation)
- **Files Affected**: mam_audiobook_qbittorrent_downloader.py, backend/__init__.py
- **User Action Required**: Yes

## [2025-11-21 08:30:29]
- **Description**: Implemented Split Identity (Scraper A/B) and Strict Quality Rules
- **Reason**: Enforce Section 21 (Identity) and Section 5 (Quality) of Spec
- **Files Affected**: mamcrawler/stealth.py, mamcrawler/metadata_scraper.py, mamcrawler/quality.py
- **User Action Required**: No

## [2025-11-21 08:29:51]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:28:39]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:22:47]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:21:20]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:19:47]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:18:39]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:17:38]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:16:53]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:16:33]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:16:09]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No

## [2025-11-21 08:15:04]
- **Description**: Test Change
- **Reason**: Testing logger
- **Files Affected**: test.py
- **User Action Required**: No


## [Unreleased]

### Added
- Initial Change Log creation to comply with Section 17 of the specification.
