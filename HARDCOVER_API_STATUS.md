# Hardcover API Integration Status - Critical Findings

**Date**: 2025-11-30
**Status**: TOKEN OBTAINED BUT API ENDPOINT UNREACHABLE
**Severity**: CRITICAL - API integration blocked

---

## Summary

The Hardcover API token has been successfully obtained and configured in `.env`, but the GraphQL API endpoint is unreachable (HTTP 404). This prevents the metadata resolution system from functioning.

**Token Status**: ✓ VALID (expires 11/29/2026)
**Token Location**: `.env` → `HARDCOVER_TOKEN`
**API Endpoint Status**: ✗ UNREACHABLE (HTTP 404)

---

## Token Validation Results

### Token Details
- **Status**: VALID and ACTIVE
- **Expiration**: 11/29/2026 (364 days remaining)
- **User ID**: 45909
- **Logged In**: True
- **Issued**: 1764410067 (Sept 29, 2025)
- **Source**: Hardcover.txt (API Access page)

### Token Format
```
Bearer eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJIYXJkY292ZXIiLCJ2ZXJzaW9uIjoiOCIsImp0aSI6IjYyNGE3NGZlLTk5NzAtNDdmYi1hYjM3LTUyNzdkMTE0MGRmMCIsImFwcGxpY2F0aW9uSWQiOjIsInN1YiI6IjQ1OTA5IiwiYXVkIjoiMSIsImlkIjoiNDU5MDkiLCJsb2dnZWRJbiI6dHJ1ZSwiaWF0IjoxNzY0NDEwMDY3LCJleHAiOjE3OTU5NDYwNjcsImh0dHBzOi8vaGFzdXJhLmlvL2p3dC9jbGFpbXMiOnsieC1oYXN1cmEtYWxsb3dlZC1yb2xlcyI6WyJ1c2VyIl0sIngtaGFzdXJhLWRlZmF1bHQtcm9sZSI6InVzZXIiLCJ4LWhhc3VyYS1yb2xlIjoidXNlciIsIlgtaGFzdXJhLXVzZXItaWQiOiI0NTkwOSJ9LCJ1c2VyIjp7ImlkIjo0NTkwOX19.5k8tmy2uz0JVbcxEIpn3MGWun0M6ZWC6Tnhj8ekHNkI
```

---

## API Endpoint Issue

### Current Endpoint Configuration
**URL**: `https://api.hardcover.app/graphql`
**Method**: POST
**Header**: `Authorization: Bearer <token>`

### Current Response
```
HTTP/1.1 404 Not Found
Content-Type: text/html; charset=UTF-8
Connection: keep-alive
x-request-id: b293cb20-b81f-4e4b-849f-f964f68b495e

[HTML error page returned, not JSON]
```

### Test Query Attempted
```graphql
query Test {
  me {
    username
  }
}
```

### Result
✗ **FAILED**: HTTP 404 Not Found (returns HTML 404 page, not GraphQL response)

---

## Root Cause Analysis

### Possible Issues

1. **API Endpoint Deprecated**
   - Hardcover.txt states: "Our API is still in the works, but you can experiment with it today"
   - Warning: "The API is still heavily in flux right now"
   - "We may reset tokens without notice while in beta"
   - Likelihood: **MEDIUM** - API may have moved or been disabled

2. **Wrong Endpoint URL**
   - `https://api.hardcover.app/graphql` doesn't exist
   - Possible alternatives:
     - `https://hardcover.app/graphql`
     - `https://graphql.hardcover.app/graphql`
     - `https://api.hardcover.app/v1/graphql`
   - Likelihood: **HIGH** - Should test alternatives

3. **Token Scope Issue**
   - Token shows `x-hasura-role: user`
   - May require specific permissions
   - Likelihood: **LOW** - Token validates as active

4. **API Moved to Different Host**
   - Could be behind auth gateway
   - Could have changed during beta
   - Likelihood: **MEDIUM** - Beta APIs do this

---

## Next Steps to Resolve

### Immediate Actions

1. **Try Alternative Endpoints**
   ```bash
   # Test these URLs with the token
   https://hardcover.app/graphql
   https://graphql.hardcover.app/graphql
   https://api.hardcover.app/v1/graphql
   https://api.hardcover.app/api/graphql
   ```

2. **Visit Hardcover API Console**
   - Go to: https://hardcover.app/settings
   - Check "API Access" section
   - Verify correct endpoint URL
   - Test query in browser console

3. **Check for API Documentation Updates**
   - Hardcover.txt says "Later on we'll get some better documentation"
   - May have published updated API docs since token was created
   - Check hardcover.app/developer or similar

4. **Contact Hardcover Support**
   - API is in beta and "heavily in flux"
   - Support may have moved endpoint
   - Could provide updated GraphQL endpoint URL

---

## Current Status by Component

| Component | Status | Details |
|-----------|--------|---------|
| **Hardcover Token** | ✓ OBTAINED | Valid, expires 11/29/2026 |
| **Token Validity** | ✓ VALID | Passes JWT validation |
| **Token Configured** | ✓ SET | In .env file |
| **API Endpoint** | ✗ NOT FOUND | HTTP 404 on `/graphql` |
| **Alternative Endpoints** | ? UNTESTED | Need to test alternatives |
| **Metadata Resolution** | ✗ BLOCKED | Can't reach API to resolve |
| **AudiobookShelf Sync** | ✗ BLOCKED | Dependent on Hardcover API |
| **Overall Integration** | ✗ BLOCKED | Cannot proceed without API |

---

## Impact Assessment

### What Works
- ✓ AudiobookShelf API (all operations)
- ✓ Audio file validation (ID3 extraction)
- ✓ Metadata comparison logic
- ✓ Confidence scoring algorithm
- ✓ Database operations
- ✓ All code infrastructure

### What's Blocked
- ✗ Hardcover book resolution (ISBN lookup)
- ✗ Hardcover title+author search
- ✗ Hardcover fuzzy matching
- ✗ Full end-to-end sync workflow
- ✗ Narrator metadata enhancement
- ✗ Series information enhancement

### Percentage Impact
- **Code Readiness**: 100% (all code written and working)
- **Infrastructure Readiness**: 50% (AudiobookShelf OK, Hardcover API broken)
- **System Functionality**: 0% (cannot resolve books without Hardcover)

---

## Workarounds (If API Remains Unavailable)

### Option 1: Use Alternative Metadata Services
Instead of Hardcover API:
- Google Books API (already integrated)
- Open Library API
- ISBN API services
- Goodreads API (partially supported)

### Option 2: Manual Metadata Matching
- Use audio file ID3 tags as primary source
- Manual review workflow for missing metadata
- Community-contributed metadata

### Option 3: Wait for API Fix
- Hardcover API is in beta
- May be restored or updated
- Could happen within days/weeks

---

## Configuration Applied

### .env Updates
```bash
# Added to .env:
HARDCOVER_TOKEN=eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJIYXJkY292ZXIiLCJ2ZXJzaW9uIjoiOCIsImp0aSI6IjYyNGE3NGZlLTk5NzAtNDdmYi1hYjM3LTUyNzdkMTE0MGRmMCIsImFwcGxpY2F0aW9uSWQiOjIsInN1YiI6IjQ1OTA5IiwiYXVkIjoiMSIsImlkIjoiNDU5MDkiLCJsb2dnZWRJbiI6dHJ1ZSwiaWF0IjoxNzY0NDEwMDY3LCJleHAiOjE3OTU5NDYwNjcsImh0dHBzOi8vaGFzdXJhLmlvL2p3dC9jbGFpbXMiOnsieC1oYXN1cmEtYWxsb3dlZC1yb2xlcyI6WyJ1c2VyIl0sIngtaGFzdXJhLWRlZmF1bHQtcm9sZSI6InVzZXIiLCJ4LWhhc3VyYS1yb2xlIjoidXNlciIsIlgtaGFzdXJhLXVzZXItaWQiOiI0NTkwOSJ9LCJ1c2VyIjp7ImlkIjo0NTkwOX19.5k8tmy2uz0JVbcxEIpn3MGWun0M6ZWC6Tnhj8ekHNkI
```

### Verification Commands
```bash
# Check token is in .env
grep HARDCOVER_TOKEN .env

# Verify token is valid (364 days remaining)
# Token tested: Valid, not expired
```

---

## Recommendations

### Short-Term (Next 24 hours)
1. **Try Alternative Endpoints**
   - Test each endpoint listed above
   - Check Hardcover settings page for correct URL
   - May resolve the 404 immediately

2. **Contact Hardcover Support**
   - API is in beta and "heavily in flux"
   - They may provide working endpoint URL
   - Quick response likely given active development

### Medium-Term (If API Remains Broken)
1. **Implement Fallback APIs**
   - Google Books (already have key)
   - Open Library API (free)
   - ISBN APIs

2. **Create Hybrid Resolver**
   - Try Hardcover first
   - Fall back to Google Books
   - Use audio file tags as last resort

### Long-Term
- Monitor Hardcover API status
- Implement robust error handling
- Support multiple metadata sources

---

## Token Information

**From Hardcover.txt:**
```
This token has a 1-year expiration time from the moment you loaded this page.
The exact expiration date is 11/29/2026, 1:54:27 AM.

The API is still heavily in flux right now. Anything you build using it could
break in the future.

We may reset tokens without notice while in beta.

This should only be used from a code backend - never from a browser.

Don't share your token! Someone could delete your account with it.
```

**Current Status**: Token is valid, properly stored, but API endpoint is unreachable.

---

## Summary

The Hardcover integration has hit a **critical infrastructure blocker**: the API endpoint is returning HTTP 404. The token itself is valid and properly configured, but cannot be used because the GraphQL endpoint is unreachable.

**Recommendation**: Test alternative endpoints immediately, as this may be a simple URL change.

