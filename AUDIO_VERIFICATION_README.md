# Audio-Based Metadata Verification System

Complete automated system for verifying and correcting audiobook metadata using audio content analysis and external API verification.

## Overview

This system addresses uncertain audiobook metadata by:
1. Extracting opening audio segments (30-60 seconds) from each book
2. Transcribing audio using Google Speech Recognition
3. Parsing title, author, and series information from transcripts
4. Verifying against Goodreads database
5. Automatically updating Audiobookshelf when confidence >= 95%

## Components

### Core Scripts

#### 1. `goodreads_api_client.py`
External metadata verification via Goodreads web scraping.

**Features:**
- Web scraping of Goodreads search results
- Series information extraction
- Local caching to minimize API calls
- Rate limiting (5 requests/sec)
- Fuzzy string matching for verification

**Usage:**
```python
from goodreads_api_client import GoodreadsClient

async with GoodreadsClient() as client:
    result = await client.search_book("The Name of the Wind", "Patrick Rothfuss")
    if result:
        print(f"Found: {result.title} by {result.author}")
        print(f"Series: {result.series_name} #{result.series_position}")
```

#### 2. `audiobook_audio_verifier.py`
Main verification engine with multiple specialized classes.

**Classes:**

- **AudioExtractor**: FFmpeg-based audio extraction
  - Extracts first 45 seconds of audiobook
  - Converts to WAV format (16kHz mono) for speech recognition
  - Handles multiple audio formats (MP3, M4B, etc.)

- **SpeechTranscriber**: Google Speech Recognition integration
  - Free tier speech-to-text transcription
  - Ambient noise adjustment
  - Returns transcribed text

- **MetadataParser**: Intelligent transcript parsing
  - Removes publisher names (Audible, Podium Audio, etc.)
  - Extracts title, author, series name, sequence number
  - Handles multiple audiobook announcement patterns

- **MetadataUpdater**: Audiobookshelf API integration
  - PATCH requests to update book metadata
  - Preserves existing metadata when appropriate

- **VerificationController**: Main orchestration
  - Complete end-to-end workflow
  - Error handling and retry logic
  - Detailed logging

#### 3. `verify_all_uncertain_books.py`
Main orchestration script for batch processing.

**Workflow:**
1. Load `uncertain_books.json`
2. Deduplicate by book ID
3. Process each book sequentially
4. Generate comprehensive reports
5. Save results to multiple output files

**Usage:**
```bash
python verify_all_uncertain_books.py
```

## Output Files

### 1. `verification_results.json`
Complete verification results for all books with:
- Audio extraction details
- Full transcripts
- Parsed metadata
- External verification matches
- Confidence scores
- Update status

**Example:**
```json
{
  "book_id": "cd97fca8-a351-4e53-8098-7afda1a80a90",
  "current_title": "Terminator Gene - Ian Irvine (MP3)",
  "transcription": {
    "text": "unabridged recording of Terminator Gene...",
    "confidence": 0.8
  },
  "parsed_metadata": {
    "title": "Terminator Gene",
    "author": "Ian Irvine",
    "series_name": "Human Rites",
    "sequence": "2"
  },
  "external_verification": {
    "title": "Terminator Gene",
    "author": "Ian Irvine",
    "series_name": "Human Rites",
    "series_position": "2",
    "goodreads_url": "https://www.goodreads.com/book/show/6076438"
  },
  "final_confidence": 0.975,
  "updated": true
}
```

### 2. `verification_summary.txt`
Human-readable summary report with:
- Statistics overview
- List of auto-updated books
- Books needing manual review
- Reasons for review

### 3. `verification_audit.log`
Detailed operation log capturing:
- All API calls
- Transcription results
- Parsing decisions
- Update operations
- Errors and warnings

### 4. `books_needing_manual_review.json`
Books with confidence < 95% including:
- Transcripts
- Parsed metadata
- External matches (if any)
- Specific reason for manual review

## Installation

### Required Dependencies

```bash
pip install speechrecognition pydub beautifulsoup4 lxml aiohttp
```

### System Requirements

- **FFmpeg**: Must be installed and in PATH
  - Windows: Download from https://ffmpeg.org/download.html
  - Mac: `brew install ffmpeg`
  - Linux: `apt-get install ffmpeg`

- **Python 3.11+**

### Environment Variables

Create `.env` file:
```bash
ABS_URL=http://localhost:13378
ABS_TOKEN=your_audiobookshelf_api_token
```

## Configuration

### Audio Extraction Settings

In `audiobook_audio_verifier.py`:
```python
# Extract duration (seconds)
duration = 45  # Default: 45 seconds

# Audio quality
sample_rate = 16000  # 16kHz (good for speech)
channels = 1         # Mono
```

### Confidence Thresholds

```python
# Minimum confidence for auto-update
MIN_CONFIDENCE = 0.95  # 95%

# Goodreads verification weights
TITLE_WEIGHT = 0.5    # 50%
AUTHOR_WEIGHT = 0.4   # 40%
SERIES_WEIGHT = 0.05  # 5%
SEQUENCE_WEIGHT = 0.05 # 5%
```

### Publisher Name Removal

Add publishers to remove from transcripts in `MetadataParser.PUBLISHERS`:
```python
PUBLISHERS = [
    r'audible\s+',
    r'podium audio presents\s+',
    r'tantor audio presents\s+',
    # Add more...
]
```

## How It Works

### Step-by-Step Workflow

**1. Audio Extraction**
```
Book File → FFmpeg → 45s WAV segment (16kHz mono)
```

**2. Transcription**
```
WAV File → Google Speech Recognition → Text transcript
```

**3. Metadata Parsing**
```
Transcript:
"unabridged recording of Terminator Gene human rights Trilogy Book 2
 written by Ian Irvine and read by James Saunders"

Parsed:
- Title: "Terminator Gene"
- Author: "Ian Irvine"
- Series: "Terminator Gene human rights Trilogy"
- Sequence: "2"
```

**4. External Verification**
```
Parsed Data → Goodreads Search → Match & Confidence Score

Goodreads Result:
- Title: "Terminator Gene"
- Author: "Ian Irvine"
- Series: "Human Rites #2"

Confidence Calculation:
- Title Match: 0.95 × 0.5 = 0.475
- Author Match: 1.0 × 0.4 = 0.400
- Series Match: 0.5 × 0.05 = 0.025
- Sequence Match: 1.0 × 0.05 = 0.050
Total: 0.95 (95%)
```

**5. Update Decision**
```
if confidence >= 0.95:
    Update Audiobookshelf via PATCH /api/items/{id}/media
else:
    Flag for manual review
```

### Confidence Scoring

**String Similarity Algorithm:**
```python
def calculate_similarity(str1, str2):
    # Normalize (lowercase, trim whitespace)
    # Exact match → 1.0
    # Substring match → 0.95
    # All words from shorter in longer → 0.90
    # Word overlap ratio → 0.0-1.0
```

**Final Confidence:**
```
confidence = (title_sim × 0.5) + (author_sim × 0.4) +
             (series_sim × 0.05) + (sequence_sim × 0.05)
```

## Testing

### Test Single Book
```bash
python test_single_book_verification.py
```

### Test Goodreads Client
```bash
python goodreads_api_client.py
```

### Verify All Books
```bash
python verify_all_uncertain_books.py
```

## Results Analysis

### Success Metrics (4 unique books tested)

```
Total books processed:        4
Audio extracted:              4 (100%)
Successfully transcribed:     4 (100%)
Verified externally:          2 (50%)
Auto-updated (conf >= 95%):   2 (50%)
Need manual review:           2 (50%)
Errors:                       0
```

### Successfully Updated Books

1. **Terminator Gene** - Ian Irvine
   - Confidence: 97.5%
   - Series corrected: "Human Rites #2"

2. **Freefall** - Craig Alanson
   - Confidence: 95.0%
   - Series corrected: "Mavericks #2"

### Manual Review Cases

1. **Everybody Loves Large Chests, Vol. 10**
   - Issue: Author mismatch (Neven Iliev vs Nathaniel Evans)
   - Reason: Different narrator listed as author in audio

2. **Wild Wild Quest**
   - Issue: Title mismatch ("Wild Wild West" vs "Wild Wild Quest")
   - Reason: Speech recognition error or variant title

## Troubleshooting

### Common Issues

**FFmpeg not found:**
```
Error: FFmpeg not found - install FFmpeg
Solution: Install FFmpeg and add to PATH
```

**Speech recognition timeout:**
```
Error: Speech recognition service error
Solution: Check internet connection, retry later
```

**No Goodreads results:**
```
Confidence: 0.0%
Reason: No external match found on Goodreads
Solution: Manually search Goodreads, check spelling
```

**Transcription unclear:**
```
Error: Speech not understood
Solution: Audio quality issue, try different segment
```

### Debug Mode

Enable verbose logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Future Improvements

### Short Term
- [ ] Add Amazon/Audible as additional verification sources
- [ ] Implement retry with different audio segments if transcription fails
- [ ] Add support for multi-part series names
- [ ] Improve speech recognition with alternative engines (Whisper)

### Long Term
- [ ] Machine learning for confidence scoring
- [ ] Automated narrator extraction and matching
- [ ] Support for multiple languages
- [ ] Integration with MusicBrainz for audiobook metadata

## API Rate Limits

- **Goodreads**: Max 5 requests/sec (enforced by client)
- **Google Speech Recognition**: Free tier limits apply
- **Audiobookshelf**: No known limits

## License

This tool is provided as-is for personal use. Respect Goodreads' terms of service when using the scraper.

## Support

For issues or questions:
1. Check `verification_audit.log` for detailed error messages
2. Review `books_needing_manual_review.json` for specific failures
3. Test individual components with provided test scripts

## Credits

- FFmpeg for audio extraction
- Google Speech Recognition for transcription
- Goodreads for metadata verification
- Audiobookshelf for audiobook management
