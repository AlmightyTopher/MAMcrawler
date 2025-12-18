# Audiobookshelf API Documentation

## ⚠️ CRITICAL ERROR: Source Data Missing

**Status**: Documentation generation FAILED
**Reason**: Input file `./audiobookshelf.har` not found
**Timestamp**: 2025-12-07

---

## Issue Summary

The reverse-engineering process cannot proceed because the required HAR (HTTP Archive) file is not present in the working directory.

### Expected Input
- **File**: `./audiobookshelf.har`
- **Location**: `C:\Users\dogma\Projects\MAMcrawler\`
- **Status**: **NOT FOUND**

### Search Results
```
Directory scan: No .har files found in current directory or subdirectories
```

---

## Required Action

To generate the complete Audiobookshelf API documentation, you must:

1. **Capture a HAR file** from your browser while using Audiobookshelf:
   - Open Chrome/Edge DevTools (F12)
   - Go to Network tab
   - Check "Preserve log"
   - Interact with Audiobookshelf (login, browse libraries, play audiobooks, etc.)
   - Right-click in Network tab → "Save all as HAR with content"

2. **Save the file** as `audiobookshelf.har` in this directory:
   ```
   C:\Users\dogma\Projects\MAMcrawler\audiobookshelf.har
   ```

3. **Re-run the documentation generator** with the HAR file present

---

## What Would Have Been Generated

If the HAR file were present, this document would contain:

### 1. API Overview
- Service purpose and architecture
- Client types and protocols
- Base URLs and environments
- Content types and data formats

### 2. Authentication & Session Model
- Login flows and token management
- Session lifecycle
- Required authentication headers
- Device binding and fingerprinting

### 3. Global Headers & Conventions
- Standard request/response headers
- Client identification
- Localization and caching

### 4. Complete Endpoint Catalog
- Every unique API endpoint discovered
- Request/response schemas with types
- Query parameters and headers
- Status codes and error formats
- Pagination and caching behavior

### 5. Object & Data Model Reconstruction
- Domain entities (User, Library, Book, Audiobook, Chapter, Playlist, etc.)
- Field types and relationships
- Enumerations and constraints

### 6. Workflows & State Machines
- User authentication flow
- Library scanning and sync
- Playback and progress tracking
- Cross-device synchronization

### 7. Streaming & File Transfer Mechanics
- Audio streaming protocols
- Range requests and partial content
- URL signing and expiration
- Resume and seeking behavior

### 8. Security Model Analysis
- TLS usage and certificate handling
- Anti-replay mechanisms
- Request/response signing
- Sensitive data exposure patterns

### 9. Rate Limiting & Abuse Controls
- Throttling behavior
- Rate limit headers
- Backoff strategies

### 10. Infrastructure & Backend Topology
- CDN usage
- API gateway patterns
- Microservice boundaries
- Regional routing

### 11. Undocumented / Internal Endpoints
- Admin-only routes
- Debug and diagnostic endpoints
- Experimental features

### 12. API Usage Examples
- Authentication
- Library and item retrieval
- Playback initiation and progress updates
- Error handling patterns

### 13. OpenAPI 3.1 Specification
- Complete machine-readable API spec
- All endpoints with schemas
- Security definitions

### 14. Engineering Risk & Stability Assessment
- API stability analysis
- Breaking change risks
- Versioning approach
- Deployment considerations

---

## Next Steps

1. Capture the HAR file following the instructions above
2. Ensure the file is named exactly `audiobookshelf.har`
3. Place it in: `C:\Users\dogma\Projects\MAMcrawler\`
4. Re-run the documentation generator

---

**Generated**: 2025-12-07
**Status**: Awaiting source data
**Required File**: `./audiobookshelf.har`
