# AudiobookShelf Capabilities Analysis

**Analysis Date**: 2025-11-28
**Source**: AudiobookShelf Official Documentation
**Status**: Ready for Implementation Discussion

---

## Overview

This document catalogues AudiobookShelf capabilities extracted from official documentation, organized into:
1. **Facts** - Confirmed capabilities that exist
2. **Directives** - Recommended implementations or configurations
3. **Implementation Recommendations** - Options requiring your decision

---

## Section 1: FACTS (Confirmed Capabilities)

### Core System Features

**Fact 1.1: Multi-User Support with Custom Permissions**
- AudiobookShelf supports multiple user accounts
- Each user has customizable permission levels
- Progress is tracked per user and syncs across devices
- **Current Status**: Feature exists, not yet implemented in our workflow

**Fact 1.2: Metadata Provider Integration**
- AudiobookShelf can lookup and apply metadata from several providers
- Cover art can be retrieved from metadata providers
- Metadata can be applied automatically during library scan
- **Current Status**: We use AudiobookShelf API but don't leverage built-in providers

**Fact 1.3: Audiobook Chapter Editor**
- AudiobookShelf includes chapter editor functionality
- Chapter lookup is available (can auto-detect chapters from source)
- Chapters can be manually edited
- **Current Status**: Available but not integrated into our workflow

**Fact 1.4: Audiobook Tools**
- Can embed metadata directly into audio files (ID3 tags)
- Can merge multiple audio files into single m4b file
- **Current Status**: Available but not used in our automated workflow

**Fact 1.5: Podcast Support**
- AudiobookShelf can search and add podcasts
- Auto-download episodes functionality available
- Open RSS feeds for podcast episodes
- **Current Status**: Feature exists, not part of current scope

**Fact 1.6: EBook Support**
- Basic ebook support for epub, pdf, cbr, cbz formats
- Send to device functionality (e.g., send to Kindle)
- EBooks can be mixed with audiobooks in same library
- **Current Status**: Feature exists, potential future expansion

**Fact 1.7: Automated Backups**
- Backups can be scheduled automatically
- Backups contain database and metadata
- Custom backup path can be configured
- **Current Status**: Available, not integrated into workflow

**Fact 1.8: Directory Structure Parsing**
- AudiobookShelf automatically parses folder structures
- Supports complex naming conventions with series, volume, narrator info
- Can extract publish year, series sequence, subtitle, narrator from folder names
- Narrator is identified via {bracketed names} in folder structure
- **Current Status**: We rely on this for library import

**Fact 1.9: ID3 Metadata Tag Support**
- AudiobookShelf reads ID3 tags from audio files
- Supports genre, artist, album, chapter markers
- Overdrive MediaMarkers can be extracted as chapters (if enabled)
- Embedded cover art is used if no folder images exist
- **Current Status**: Files may have ID3 tags, not being written by our tools

**Fact 1.10: API Availability**
- Full REST API for library management
- Authentication via Bearer tokens (JWT)
- Can query, create, update, delete library items
- Can manage users, permissions, and settings
- **Current Status**: We actively use the API in all phases

**Fact 1.11: Search and Filtering**
- Library supports full-text search across metadata
- Can filter by title, author, series, genre, narrator, etc.
- Search results can be paginated
- **Current Status**: Manual searches performed, not automated

**Fact 1.12: RSS Feeds**
- AudiobookShelf generates RSS feeds for audiobooks and podcast episodes
- Feeds can be subscribed to by external services
- **Current Status**: Feature exists, not leveraged

**Fact 1.13: OPF File Support**
- Can parse OPF (Open Packaging Format) files
- OPF files can provide enhanced metadata
- Located as `filename.opf` in library item folder
- **Current Status**: Not currently used

**Fact 1.14: Configuration via Environment Variables**
- AudiobookShelf is fully configurable via env vars
- Key configurations include:
  - Path settings (config, metadata, backup)
  - Security settings (tokens, CORS, SSRF filtering)
  - External tools (ffmpeg, ffprobe paths)
  - Network settings (host, port)
  - Database parameters (SQLite pragmas)
- **Current Status**: We use HOST, PORT, TOKEN but not advanced configs

---

## Section 2: DIRECTIVES (Recommended Practices)

### Directory Structure Guidelines

**Directive 2.1: Proper Folder Naming Convention**
*From docs: Title folders should follow specific naming patterns*
- Include narrator in curly braces: `{Sam Tsoutsouvas}`
- Include publish year: `1994 - Book Title`
- Include series sequence: `Vol 1 - Book Title` or `Book 1 - Title`
- Subtitles separated by " - " (optional, must be enabled)
- Disc numbers in subfolders: `Disc 1`, `CD 2`, `Disk 3`

**Action**: Ensure MAM downloads are renamed/organized before import

**Directive 2.2: Author Folder Naming**
*From docs: Author folders support multiple formats*
- Supports "Last, First" format: `Kishimi, Ichiro`
- Supports multiple authors: `Ichiro Kishimi, Fumitake Koga`
- Multiple separators work: `,` `;` `&` `and`

**Action**: Standardize author names in downloaded files

**Directive 2.3: Metadata Priority Settings**
*From docs: Must match metadata priority to file structure*
- Configure which metadata source takes priority (filename vs ID3 tags)
- Should be done in AudiobookShelf settings
- Affects how narrator, title, author info is applied

**Action**: Verify metadata priority setting in AudiobookShelf web UI

**Directive 2.4: Separate Directory Mappings**
*From docs: Volume mappings must not be contained in each other*
- `/audiobooks` directory must be separate
- `/podcasts` directory must be separate
- `/config` directory must be separate
- `/metadata` directory must be separate

**Action**: Confirm Docker volume mappings don't overlap (already correct)

**Directive 2.5: Token Secret Management**
*From docs: JWT_SECRET_KEY should not be changed on existing servers*
- Changing JWT secret invalidates all existing tokens
- Only change before first app deployment OR after all apps updated
- Better to let system auto-generate if not provided

**Action**: Document that changing JWT_SECRET_KEY requires coordination

### Security Recommendations

**Directive 2.6: SSRF Request Filter Configuration**
*From docs: May need adjustment for self-hosted podcasts*
- By default, AudiobookShelf blocks self-referential requests (SSRF protection)
- If self-hosting podcasts on same server, may need to whitelist
- Can disable entirely or use SSRF_REQUEST_FILTER_WHITELIST

**Action**: Document for future podcast support

**Directive 2.7: Rate Limiting for Authentication**
*From docs: Security rate limiting can be configured*
- Default: 40 attempts per 10 minutes
- Can be disabled (set to 0) if not needed
- RATE_LIMIT_AUTH_MAX and RATE_LIMIT_AUTH_WINDOW env vars

**Action**: Monitor if we encounter rate limiting issues

---

## Section 3: IMPLEMENTATION OPTIONS (Awaiting Your Decision)

### Option 1: Narrator Metadata Enhancement

**Current State**:
- Phase 8E populates narrators from Google Books API
- Phase 8F validates narrator coverage
- AudiobookShelf supports narrator in folder names: `{Narrator Name}`

**Possible Implementations**:

**Option 1A: Rename Downloaded Files with Narrator**
- Update MAM download handler to rename files including narrator
- Format: `1994 - Book Title {Narrator Name}`
- Benefit: Narrator persists even if AudiobookShelf DB lost
- Effort: Medium (requires filename parsing logic)

**Option 1B: Use Metadata Provider Built-in**
- Let AudiobookShelf's built-in metadata lookup find narrators
- User enables metadata provider in settings
- Benefit: Less API calls from our system
- Effort: Low (user configuration only)

**Option 1C: Enhanced ID3 Tag Writing**
- Write narrator to ID3 tags in audio files
- AudiobookShelf reads ID3 narrator on import
- Benefit: Metadata embedded in files
- Effort: High (requires audio file manipulation)

**Option 1D: Hybrid Approach**
- Use folders + ID3 tags + metadata provider
- Multiple fallback sources for narrator data
- Benefit: Maximum reliability
- Effort: High (all three approaches)

**DECISION NEEDED**: Which approach aligns with your goals?

---

### Option 2: Metadata Provider Leverage

**Current State**:
- We query Google Books API directly
- AudiobookShelf has built-in metadata providers

**Possible Integrations**:

**Option 2A: Use AudiobookShelf's Built-in Providers**
- Let users configure metadata providers in ABS settings
- ABS handles provider queries automatically during scan
- Providers supported: Multiple (exact list in their settings)
- Benefit: No need for Phase 8 metadata phases
- Concern: User must configure, less automated

**Option 2B: Continue Custom API Integration**
- Keep Phase 8E Google Books integration
- Add more providers (Goodreads, Audible, etc.)
- Benefit: Automated, doesn't require user config
- Concern: More API dependencies

**Option 2C: Hybrid**
- Use AudiobookShelf metadata for some fields
- Use custom APIs for specialized needs (narrator detection)
- Benefit: Flexibility + automation
- Effort: Medium coordination needed

**DECISION NEEDED**: Should we leverage ABS providers or maintain custom APIs?

---

### Option 3: EBook Support Expansion

**Current State**:
- AudiobookShelf supports ebook formats: epub, pdf, cbr, cbz
- We only handle audiobooks currently

**Possible Extensions**:

**Option 3A: Add Ebook Searching to MAM**
- Extend workflow to include ebook searches
- Download ebooks alongside audiobooks
- Benefit: More comprehensive library
- Concern: Different torrent profiles, quality considerations

**Option 3B: Send to Device Integration**
- Integrate "send to Kindle" for ebooks
- Benefit: Seamless reading experience
- Effort: Medium (requires Kindle API integration)

**Option 3C: Ignore for Now**
- Keep focus on audiobooks only
- EBooks can be added later
- Benefit: Simpler, focused scope

**DECISION NEEDED**: Should we expand to ebooks, or keep audiobook-only scope?

---

### Option 4: Backup and Recovery

**Current State**:
- AudiobookShelf supports automated backups
- We don't integrate backup management

**Possible Integrations**:

**Option 4A: Automated Backup Scheduling**
- Add phase to schedule ABS backups via API
- Ensure regular backups are created
- Benefit: Data protection
- Effort: Low

**Option 4B: Backup Validation**
- Verify backups complete successfully
- Check backup integrity
- Benefit: Confidence in recovery capability
- Effort: Medium

**Option 4C: Backup Retention Policy**
- Implement rotation (keep last N backups)
- Clean old backups to save space
- Benefit: Cost and storage management
- Effort: Medium

**Option 4D: Ignore for Now**
- User manually configures backups in ABS settings
- We don't integrate backup management
- Benefit: Simpler implementation
- Concern: Reliance on user to configure

**DECISION NEEDED**: What backup strategy do you want?

---

### Option 5: Multi-User Progress Tracking

**Current State**:
- AudiobookShelf supports per-user progress tracking
- We have single user focus currently

**Possible Enhancements**:

**Option 5A: Multi-User Reporting**
- Phase 11 report shows progress per user
- Identify which users have completed books
- Benefit: Better library usage visibility
- Effort: Low

**Option 5B: Per-User Recommendations**
- Track reading patterns per user
- Suggest books based on user's completed audiobooks
- Benefit: Personalized experience
- Effort: Medium

**Option 5C: Per-User Quality Settings**
- Different quality preferences per user
- Implement separate download profiles
- Benefit: Customization
- Effort: High

**Option 5D: Ignore for Now**
- Single user focus adequate
- Multi-user features available but not integrated
- Benefit: Simpler implementation

**DECISION NEEDED**: Do you need multi-user features integrated?

---

### Option 6: Chapter Management Integration

**Current State**:
- AudiobookShelf has chapter editor and chapter lookup
- Our workflow doesn't touch chapters

**Possible Integrations**:

**Option 6A: Automatic Chapter Detection**
- Enable chapter lookup during library scan
- Let ABS auto-detect chapters from metadata
- Benefit: Better navigation within audiobooks
- Effort: Low (ABS configuration)

**Option 6B: Manual Chapter Assignment**
- Add phase to validate/fix chapters
- Ensure all books have proper chapters
- Benefit: Consistent chapter experience
- Effort: Medium

**Option 6C: Ignore for Now**
- Chapter support available but not managed
- Users can manually fix via ABS web UI
- Benefit: Simpler workflow

**DECISION NEEDED**: Should chapters be auto-detected and validated?

---

### Option 7: RSS Feed Leverage

**Current State**:
- AudiobookShelf generates RSS feeds automatically
- We don't utilize RSS feeds

**Possible Uses**:

**Option 7A: Subscribe from Podcast Apps**
- Users subscribe to ABS RSS feed in podcast app
- Audiobooks appear alongside podcasts
- Benefit: Unified interface for audio content
- Effort: Low (user configuration)

**Option 7B: External Integration**
- Third-party services subscribe to our feeds
- Enable cross-platform discovery
- Benefit: Broader accessibility
- Effort: Medium

**Option 7C: Ignore for Now**
- RSS feature available if users need it
- Not part of core workflow
- Benefit: Simpler scope

**DECISION NEEDED**: Should RSS feeds be part of distribution strategy?

---

## Summary of Decisions Needed

| # | Option | Question | Impact |
|---|--------|----------|--------|
| 1 | Narrator Metadata | Which approach: rename files, use ABS providers, write ID3 tags, or hybrid? | High - affects entire metadata strategy |
| 2 | Metadata Providers | Leverage ABS built-in or maintain custom APIs? | High - architecture decision |
| 3 | EBook Support | Audiobooks only, or expand to ebooks? | Medium - scope expansion |
| 4 | Backups | What backup strategy: auto-scheduled, validated, rotated, or manual? | Low - operational choice |
| 5 | Multi-User Features | Integrate multi-user tracking/recommendations, or single-user focus? | Medium - feature scope |
| 6 | Chapters | Auto-detect chapters or manual handling? | Low - quality-of-life feature |
| 7 | RSS Feeds | Enable RSS for discovery, or user-optional? | Low - distribution option |

---

## Next Steps

1. **Review** this analysis with your preferences
2. **Decide** which options align with your goals
3. **Communicate** your preferences for each section
4. **I will implement** according to your decisions

**Note**: Implementation will only proceed after you provide guidance on the decision points above. No changes will be made to code until you explicitly approve the approach.

---

**Document Status**: Ready for review and decision input
**Last Updated**: 2025-11-28
**Awaiting**: User input on 7 decision points
