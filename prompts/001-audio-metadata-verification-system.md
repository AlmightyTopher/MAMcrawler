# Audio-Based Metadata Verification and Correction System

<objective>
Create a fully automated system that verifies and corrects the metadata for 68 uncertain audiobooks by:
1. Extracting and transcribing the opening audio segment (30-60 seconds) from each book
2. Using speech-to-text to identify the title, author, and series information
3. Cross-referencing extracted audio data against reliable external sources (Goodreads, Amazon, Audible, GoodReads API)
4. Automatically updating Audiobookshelf metadata when confidence > 95% is achieved
5. Logging all verifications and updates for audit trail

This system will achieve 100% confidence ratings on all 68 uncertain books by using audio as the primary source of truth, validated against external databases.

Why this matters: Your audiobook library currently has 4% uncertain metadata (68 books). By listening to the actual audiobooks and cross-checking against trusted sources, we can achieve a production-ready 99%+ confidence level across the entire 1,700-book library.
</objective>

<context>
**Project**: Audiobookshelf Metadata Management System
**Current Status**: 1,632/1,700 books (96%) have high-confidence metadata; 68 books flagged as uncertain
**Target**: Achieve 100% verified metadata across all 1,700 books
**Tech Stack**: Python, asyncio, aiohttp, FFmpeg, speech recognition APIs
**Key Files**:
  - Uncertain books: `./uncertain_books.json`
  - Existing tooling: `audiobook_metadata_extractor.py`, `update_from_verification.py`
  - Audiobookshelf API: `http://localhost:13378/api`

**Audiobook Library Location**: Stored in Audiobookshelf library directories (accessible via API)
**External Data Sources**: Goodreads API, Amazon Product Data, Audible catalog

Read `CLAUDE.md` for project conventions and dependencies.
</context>

<requirements>
**Functional Requirements**:
1. Extract the first 30-60 seconds of audio from each uncertain book using the Audiobookshelf library
2. Transcribe audio segments using speech-to-text (prefer free tier: Google Speech Recognition, fallback to pydub + librosa analysis)
3. Parse transcribed text to extract: exact title, author name, series name, book sequence number
4. Query external APIs to verify extracted data against reliable sources:
   - Goodreads API (primary: comprehensive metadata)
   - Search patterns: Goodreads book search by title + author, return official series info
   - Amazon/Audible search as secondary validation
5. Apply confidence scoring: metadata confirmed from audio + validated by external source = proceed with update
6. Automatically update Audiobookshelf metadata via REST API when confidence >= 95%
7. Track all verifications: what was found in audio, what was confirmed externally, what was updated
8. Continue until all 68 uncertain books are verified and updated

**Non-Functional Requirements**:
- Respect API rate limits (no more than 5 requests/second to external services)
- Handle network failures gracefully with retry logic (exponential backoff)
- Comprehensive logging of every step: audio extraction, transcription, verification, API lookups, updates
- Generate summary report showing: books verified, sources used, confidence levels, any failures

**Technical Constraints**:
- Use existing Audiobookshelf API token (in `.env`)
- Extract audio files from Audiobookshelf library paths (accessible via API or filesystem)
- Avoid modifying the Audiobookshelf database directly; use REST API only
- Speech-to-text should handle variable audio quality and narrator accents
- External API queries should cache results to minimize redundant lookups
</requirements>

<implementation>
**Approach**:

1. **Audio Extraction Pipeline**
   - Query Audiobookshelf API for each uncertain book's audio files
   - Use FFmpeg to extract first 30-60 seconds from the first audio file
   - Convert to WAV format for compatibility with speech recognition

2. **Speech-to-Text Processing**
   - Try Google Speech Recognition API (free, no auth required for short clips)
   - If that fails, use Librosa + WAV analysis for fallback extraction
   - Transcribe the extracted audio segment to text

3. **Text Parsing & Extraction**
   - Parse transcribed text using regex patterns for:
     - "Title by Author, Book X in Series" format
     - "Series Name Book X: Title by Author" format
     - Other common announcement patterns
   - Extract: `{title, author, series_name, sequence_number}`

4. **External Source Verification**
   - Query Goodreads API: search for book by (title + author)
   - Return: official title, author, series information from Goodreads
   - Cross-check extracted audio data against Goodreads results
   - Confidence = match between audio AND external source

5. **Metadata Update**
   - When confidence >= 95%, prepare update payload
   - Call Audiobookshelf PATCH `/api/items/{book_id}/media`
   - Update: title, authorName, series array with {id, name, sequence}
   - Log the update with sources and confidence level

6. **Error Handling & Fallbacks**
   - If audio extraction fails: skip that book, log reason
   - If speech-to-text fails: try multiple audio segments or longer clips
   - If external API fails: retry with exponential backoff, then manual flag for review
   - If confidence < 95%: don't update, flag for manual review with partial results

**What to Avoid and WHY**:
- Don't modify Audiobookshelf database directly (this would bypass API validation and could cause data corruption)
- Don't update metadata without external verification (ensures accuracy - audio alone could be narrator error or audio quality issue)
- Don't call external APIs more than 5/sec (respects rate limits and prevents IP blocking)
- Don't assume similar titles are the same book (always verify with author + year if available)
- Don't update if confidence < 95% (ensures only high-quality corrections are applied automatically)

**Implementation Strategy**:

1. Create `audiobook_audio_verifier.py` with classes:
   - `AudioExtractor`: Get audio from Audiobookshelf, extract 30-60 sec segment
   - `SpeechTranscriber`: Convert audio to text
   - `MetadataParser`: Parse transcribed text into structured data
   - `ExternalVerifier`: Query Goodreads and other sources, validate extracted data
   - `MetadataUpdater`: Apply verified corrections to Audiobookshelf
   - `VerificationController`: Orchestrate the full workflow

2. Create `goodreads_api_client.py`:
   - Query Goodreads by title and author
   - Parse responses to extract series information
   - Cache results locally to minimize API calls

3. Create logging and reporting:
   - Log each book's verification process: audio transcript, external lookup results, final confidence
   - Generate `./verification_results.json` with all details
   - Generate `./verification_summary.txt` with statistics and any manual review flagged books

4. Main workflow script `verify_all_uncertain_books.py`:
   - Load `uncertain_books.json`
   - For each book: extract audio → transcribe → parse → verify externally → update if confident
   - Track progress and report on completion

**Dependencies to Install**:
```bash
pip install pydub speechrecognition librosa google-cloud-speech beautifulsoup4 goodreads-api aiohttp
```

And install FFmpeg:
```bash
# Windows
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```
</implementation>

<output>
Create the following files in `./`:

**Core Implementation**:
- `./audiobook_audio_verifier.py` - Main audio verification system with all classes
- `./goodreads_api_client.py` - External API integration for Goodreads verification
- `./verify_all_uncertain_books.py` - Orchestration script to run complete verification workflow

**Outputs**:
- `./verification_results.json` - Detailed results for each of 68 books: audio transcript, external lookup, confidence, update status
- `./verification_summary.txt` - Summary statistics and human-readable report
- `./verification_audit.log` - Detailed logging of every operation
- `./books_needing_manual_review.json` - Any books that couldn't be auto-verified (confidence < 95%)

**Expected Content**:

`verification_results.json` structure:
```json
[
  {
    "book_id": "cd97fca8-a351-4e53-8098-7afda1a80a90",
    "current_title": "Terminator Gene - Ian Irvine (MP3)",
    "audio_transcript": "This is Terminator Gene by Ian Irvine, book one of the Terminator Gene series",
    "extracted_from_audio": {
      "title": "Terminator Gene",
      "author": "Ian Irvine",
      "series_name": "Terminator Gene",
      "sequence": "1"
    },
    "external_verification": {
      "source": "Goodreads",
      "title": "Terminator Gene",
      "author": "Ian Irvine",
      "series": "Terminator Gene #1",
      "confidence_match": 1.0
    },
    "final_confidence": 0.99,
    "updated": true,
    "update_timestamp": "2025-11-17T12:45:00Z"
  },
  ...
]
```
</output>

<success_criteria>
Before declaring complete, verify:

1. **Audio Processing**: Successfully extracted and transcribed audio from at least 80% of uncertain books
2. **External Verification**: Successfully queried external sources for at least 80% of books
3. **Automatic Updates**: Applied metadata updates to books with confidence >= 95%
4. **Data Quality**: All 68 uncertain books now have verified metadata OR are flagged for manual review
5. **Reporting**: Generated `verification_results.json`, `verification_summary.txt`, and audit log
6. **Final Confidence**: Verify that books updated now have >= 98% confidence in metadata

**Manual Verification Check**:
- Pick 5 random books from the updated list
- Open Audiobookshelf and play first 30 seconds
- Confirm the metadata matches what's displayed in the UI
</success_criteria>

<verification>
After implementation is complete:

1. Check output files exist:
   - `ls -lh ./verification_results.json ./verification_summary.txt ./verification_audit.log`

2. Validate JSON structure:
   - Confirm `verification_results.json` contains entries for all 68 books or documented reasons for skipped books

3. Review summary statistics:
   - `cat ./verification_summary.txt` should show:
     - Total books processed
     - Successfully verified and updated
     - Failed/manual review needed
     - Confidence distribution

4. Test API updates worked:
   - For 5 updated books, query the API to confirm metadata changed:
     ```bash
     python -c "
     import asyncio, aiohttp, json, os
     async def check(book_id):
         token = open('.env').read().split('ABS_TOKEN=')[1].split()[0]
         async with aiohttp.ClientSession(headers={'Authorization': f'Bearer {token}'}) as s:
             async with s.get(f'http://localhost:13378/api/items/{book_id}') as r:
                 data = await r.json()
                 print(json.dumps(data['media']['metadata'], indent=2))
     # Test with a known updated book_id
     asyncio.run(check('BOOK_ID'))
     "
     ```

5. Re-run confidence analyzer:
   - Execute `python audiobook_metadata_extractor.py` to confirm uncertainty count dropped from 68
   - New result should show near 0% uncertain books, or only those flagged for manual review
</verification>

</objective>
