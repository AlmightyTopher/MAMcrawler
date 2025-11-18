# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project consists of two main systems:

1. **MAM Crawler**: A passive web crawler for MyAnonamouse.net (MAM) that uses Crawl4AI to perform stealthy, ethical web scraping
2. **Local RAG System**: A Retrieval-Augmented Generation system that transforms crawled MAM documentation into an interactive, queryable knowledge base

**Key Principles:**
- Passive crawling only - respects MAM's terms of service
- Rate-limited requests (1 request per 3 seconds minimum for basic crawler, 10-30 seconds for stealth crawler)
- User agent rotation to mimic real browser behavior
- Only crawls publicly accessible paths (guides, forums, torrent pages)
- Anonymizes extracted data to remove user-specific information
- Local-first RAG with no cloud dependencies except Claude API for queries

## Development Commands

### Python Environment

```bash
# Activate virtual environment
# Windows
venv\Scripts\activate.bat

# Unix/Mac
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt  # Note: requirements.txt needs to be created
```

### Running the Crawlers

```bash
# Set environment variables first (Windows)
set MAM_USERNAME=your_username
set MAM_PASSWORD=your_password
export PYTHONIOENCODING=utf-8

# Or use the runner script which prompts for credentials
python run_mam_crawler.py

# Run basic crawler (legacy)
python mam_crawler.py

# Run comprehensive guide crawler (extracts individual guide files)
python comprehensive_guide_crawler.py

# Run stealth crawler (human-like behavior, 10-30 second delays)
python stealth_mam_crawler.py

# Check crawling progress
python check_progress.py

# Run tests
python -m pytest test_mam_crawler.py

# Run specific test
python -m pytest test_mam_crawler.py::TestMAMPassiveCrawler::test_is_allowed_path -v
```

### Running the RAG System

```bash
# Setup environment with Anthropic API key
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY

# Index crawled documentation (run after crawling guides)
venv\Scripts\python ingest.py

# Query the knowledge base with Claude
venv\Scripts\python cli.py "How do I convert AA files?"

# Get context only (for VS Code/Copilot integration)
venv\Scripts\python cli.py "CD ripping guide" --context-only > .ai/docs.md

# Start file watcher (auto-updates index when files change)
venv\Scripts\python watcher.py
```

### Key Dependencies

**Crawler Dependencies:**
- `crawl4ai` (0.7.6) - Core crawling framework
- `aiohttp` - Async HTTP client
- `beautifulsoup4` - HTML parsing
- `lxml` - XML/HTML processing
- `tenacity` - Retry logic
- `ratelimit` - Rate limiting
- `pytest` - Testing framework
- `markdown` - Markdown processing

**RAG System Dependencies:**
- `sentence-transformers` - Embeddings model (all-MiniLM-L6-v2)
- `faiss-cpu` - Vector similarity search
- `langchain-text-splitters` - Markdown header-aware chunking
- `anthropic` - Claude API client
- `watchdog` - File system monitoring

## Architecture

The project has two major subsystems that work together:

### Crawler Components

**mam_crawler.py** - Basic passive crawler (legacy)
- `MAMPassiveCrawler` - Async crawler class that handles:
  - Authentication with session management (2-hour expiry)
  - Rate limiting (3-10 second delays between requests)
  - URL validation against allowed paths
  - User agent rotation
  - Data anonymization
- `MAMDataProcessor` - Processes and formats crawled data:
  - Converts crawl results to Markdown
  - Validates data completeness
  - Saves structured output files

**comprehensive_guide_crawler.py** - Extracts individual guide files
- `EnhancedGuideCrawler` - Crawls all guides from `/guides/` page
- Creates separate `.md` files for each guide in `guides_output/`
- Sanitizes filenames and handles duplicates
- Uses base `MAMPassiveCrawler` for authentication and rate limiting

**stealth_mam_crawler.py** - Advanced stealth crawler
- `StealthMAMCrawler` - Human-like behavior simulation:
  - Random delays (10-30 seconds between pages)
  - Mouse movement and scroll simulation
  - Viewport randomization (multiple screen resolutions)
  - Sequential processing (no batch operations)
  - State persistence for resume capability (`crawler_state.json`)
  - Retry logic with exponential backoff
- Most realistic option for avoiding detection

**mam_crawler_config.py** - Configuration and procedures
- `MAMCrawlingProcedures` - Defines crawling rules:
  - Allowed/forbidden URL patterns
  - Rate limit configurations
  - CSS extraction schemas for different page types
  - Dynamic procedure updates and persistence

**run_mam_crawler.py** - Entry point script
- Prompts for credentials if not set in environment
- Sets up logging and environment
- Runs the main crawler asynchronously

**xml_parser.py** - Robust XML parsing utilities
- `ApplyDiffXMLParser` - Parse and validate apply_diff XML structures
- `XMLParseError` - Custom exception with detailed error reporting
- Supports error recovery and generates helpful suggestions

**test_mam_crawler.py** - Unit tests
- Tests for authentication, URL validation, crawling logic
- Mocked AsyncWebCrawler for isolated testing
- Tests data processing and Markdown generation

### RAG System Components

**database.py** - SQLite metadata storage
- `create_tables()` - Initialize database schema
- `files` table - Tracks processed files with hash and modification time
- `chunks` table - Stores text chunks with header metadata
- Functions for CRUD operations on files and chunks

**ingest.py** - Indexing pipeline
- Processes all `.md` files in `guides_output/` directory
- Markdown header-aware chunking using LangChain
- Embeds chunks with SentenceTransformers (all-MiniLM-L6-v2, 384 dimensions)
- Stores embeddings in FAISS index (`index.faiss`)
- Stores chunk text and metadata in SQLite (`metadata.sqlite`)
- Skips unchanged files based on hash comparison

**cli.py** - Query interface
- Command-line RAG query system
- Takes natural language queries as arguments
- Performs FAISS similarity search (top-5 results)
- Retrieves chunk text and metadata from SQLite
- Sends context + query to Claude API (Haiku model for cost efficiency)
- Supports `--context-only` flag for VS Code/Copilot integration

**watcher.py** - File change monitor
- Uses `watchdog` to monitor `guides_output/` directory
- Automatically updates FAISS index and SQLite on file changes
- Handles file creation, modification, and deletion
- Maintains index consistency with file system state
- Runs continuously in background

### Authentication Flow

1. Check if session is valid (within 2-hour expiry)
2. If expired/missing, perform login via POST to `/takelogin.php`
3. Validate login by checking response for "logout" or "my account" text
4. Store session cookies for subsequent requests
5. Auto-refresh before expiry (handled by `_ensure_authenticated`)

### Allowed Crawl Paths

The crawler ONLY accesses these paths:
- `/` - Homepage
- `/t/` - Torrent detail pages (public)
- `/tor/browse.php` - Browse listings
- `/tor/search.php` - Search results
- `/guides/` - Guides section
- `/f/` - Forum sections (public only)

All other paths (user profiles, admin areas, upload pages, direct downloads) are forbidden.

### Rate Limiting Strategy

- Minimum 3 seconds between requests
- Random delays (3-10 seconds) to mimic human behavior
- Additional 1-3 second delays between bulk operations
- Decorator-based rate limiting with `@limits` and `@sleep_and_retry`
- Max 50 pages per session to avoid detection

### Data Anonymization

The crawler sanitizes all extracted content:
- Removes email addresses (replaced with `[EMAIL]`)
- Removes username patterns (replaced with `[USER]`)
- Limits content length (5000 chars max)
- Only includes data from validated public pages
- Strips sensitive metadata

### Data Flow: End-to-End

**Crawling → Indexing → Querying**

1. **Crawl MAM Guides**
   - Choose crawler based on needs (comprehensive, stealth, basic)
   - Crawler authenticates and extracts guides
   - Saves individual `.md` files to `guides_output/`

2. **Index Documentation**
   - Run `ingest.py` to process all `.md` files
   - Chunks documents by Markdown headers (#, ##, ###)
   - Generates embeddings using SentenceTransformers
   - Stores vectors in FAISS, metadata in SQLite

3. **Query Knowledge Base**
   - Run `cli.py` with natural language query
   - Embeds query and searches FAISS for similar chunks
   - Retrieves matching text from SQLite
   - Sends context + query to Claude API
   - Returns AI-generated answer with source citations

4. **Continuous Updates** (Optional)
   - Run `watcher.py` to monitor `guides_output/`
   - Automatically re-indexes when files change
   - Keeps RAG system in sync with latest data

### Specialized Crawlers

**Guide Extraction** (`crawl_guides_section` in basic crawler)
- Crawls `/guides/` to find all guide links
- Extracts: title, description, author, timestamp, content, tags
- Limits to 10 guides per run to respect rate limits
- Outputs structured Markdown

**Comprehensive Guide Crawler** (`comprehensive_guide_crawler.py`)
- Extracts ALL guides from MAM as individual files
- Each guide becomes a separate `.md` file
- Better for RAG indexing (one guide = one source file)
- Recommended for building complete knowledge base

**qBittorrent Settings** (`crawl_qbittorrent_settings` in basic crawler)
- Searches forum (`/f/`) for qBittorrent-related threads
- Extracts configuration code blocks, settings discussions
- Limits to 5 threads per run
- Useful for finding recommended qBittorrent configurations for MAM

## Testing Notes

The test suite uses `pytest` with async support. Tests are mocked to avoid actual network calls to MAM.

Key test areas:
- Credential handling (env vars vs direct)
- URL path validation (allowed vs forbidden)
- Login success/failure scenarios
- Crawl page allowed/forbidden paths
- Data validation and Markdown generation

To add new tests, follow the pattern in `test_mam_crawler.py` using `@patch` decorators for `AsyncWebCrawler`.

## Important Constraints

### Crawler Constraints

1. **Never crawl forbidden paths** - The crawler has hardcoded restrictions to protect user privacy and respect MAM's ToS
2. **Always use rate limiting** - Don't bypass the delays; they're critical for ethical crawling
3. **Credentials via env vars** - Never hardcode `MAM_USERNAME` or `MAM_PASSWORD`
4. **Async/await required** - All crawler methods are async; use `asyncio.run()` for execution
5. **Data anonymization is mandatory** - All extracted data goes through `_anonymize_data()`
6. **UTF-8 encoding** - Set `PYTHONIOENCODING=utf-8` on Windows to handle special characters
7. **Session persistence** - Stealth crawler saves state to `crawler_state.json` for resume capability

### RAG System Constraints

1. **Index before querying** - Must run `ingest.py` before `cli.py` works
2. **FAISS uses L2 distance** - Embeddings are normalized with `faiss.normalize_L2()`
3. **Chunk IDs must match** - FAISS vector IDs correspond to SQLite `chunk_id` primary keys
4. **Header-aware chunking** - Markdown headers become part of chunk metadata for better retrieval
5. **API key required** - `ANTHROPIC_API_KEY` must be set in environment or `.env` file
6. **Top-5 retrieval** - Queries return 5 most similar chunks by default (configurable in `cli.py`)
7. **Haiku model** - Uses `claude-haiku-4-5` for cost efficiency (~$0.02 per query)

## XML Parser Usage

The `xml_parser.py` module provides robust XML parsing for apply_diff operations:

```python
from xml_parser import ApplyDiffXMLParser

parser = ApplyDiffXMLParser()
root = parser.parse_xml_string(xml_string)

if root and parser.validate_apply_diff_structure(root):
    diffs = parser.extract_diffs(root)
    # Process diffs...
else:
    print(parser.get_error_summary())
```

Expected XML structure:
```xml
<apply_diff>
    <args>
        <file>
            <path>file/path.py</path>
            <diff>
                <content>code content</content>
                <start_line>1</start_line>
            </diff>
        </file>
    </args>
</apply_diff>
```

## Output Format

### Crawler Output

**Basic Crawler** (`mam_crawler.py`) - Single consolidated file:
```markdown
# MAM Guides

Crawl Timestamp: 2025-11-03T...

## Guide Title

- **Description**: ...
- **Author**: ...
- **Timestamp**: ...
- **Tags**: ...
- **Source URL**: ...

### Content

[Guide content here]

---
```

**Comprehensive/Stealth Crawlers** - Individual files in `guides_output/`:
- Each guide becomes a separate `.md` file
- Filename: sanitized version of guide title (e.g., `How_to_Rip_CDs.md`)
- Contains full guide content with metadata header
- Better for RAG indexing (source attribution per file)

### RAG System Output

**CLI Query** (`cli.py "query"`):
```
[Claude's answer with source citations]
```

**Context-Only Mode** (`cli.py "query" --context-only`):
```markdown
--- CONTEXT (Source: guides_output/Guide_Title.md, Section: H1 > H2) ---
[Relevant chunk text]

--- CONTEXT (Source: guides_output/Another_Guide.md, Section: H1 > H2 > H3) ---
[Another relevant chunk]
```

### File Structure

```
MAMcrawler/
├── venv/                          # Virtual environment
├── guides_output/                 # Crawled guides (individual .md files)
├── mam_crawler.py                 # Basic crawler
├── comprehensive_guide_crawler.py # Enhanced guide extraction
├── stealth_mam_crawler.py         # Stealth crawler
├── run_mam_crawler.py             # Entry point script
├── check_progress.py              # Progress checker
├── database.py                    # SQLite operations
├── ingest.py                      # RAG indexing
├── cli.py                         # RAG query interface
├── watcher.py                     # File system monitor
├── metadata.sqlite                # RAG metadata database
├── index.faiss                    # RAG vector index
├── crawler_state.json             # Stealth crawler state
├── requirements.txt               # Dependencies
└── .env                           # API keys and credentials
```

## Extending the System

### Adding New Crawler Targets

1. Add URL patterns to `allowed_paths` in `MAMPassiveCrawler.__init__`
2. Define CSS extraction schema in `mam_crawler_config.py` under `extraction_schemas`
3. Create new method following pattern of `crawl_guides_section` or `crawl_qbittorrent_settings`
4. Add corresponding processor method in `MAMDataProcessor`
5. Add tests to `test_mam_crawler.py`

Example extraction config:
```python
"my_new_page": {
    "name": "MyPageExtractor",
    "fields": [
        {"name": "title", "selector": "h1", "type": "text"},
        {"name": "content", "selector": ".content", "type": "text"}
    ]
}
```

### Improving RAG Retrieval

**Adjust Chunk Size** (in `ingest.py` and `watcher.py`):
- Modify `MarkdownHeaderTextSplitter` parameters
- Consider max_chunk_size if chunks are too large

**Change Retrieval Count** (in `cli.py`):
- Modify `k = 5` to retrieve more/fewer chunks
- Trade-off: more context vs. Claude API cost

**Use Better Embeddings Model**:
- Replace `all-MiniLM-L6-v2` with larger model (e.g., `all-mpnet-base-v2`)
- Update `dimension` parameter to match model output
- Better accuracy but slower and larger storage

**Switch to Claude Sonnet/Opus** (in `cli.py`):
- Change `model="claude-haiku-4-5"` to `claude-sonnet-4-5` or `claude-opus-4-5`
- Better quality answers but higher cost

### VS Code Integration

Add to `.vscode/settings.json`:
```json
{
  "github.copilot.chat.codeGeneration.instructions": [
    { "file": ".ai/docs.md" }
  ],
  "aider.read": [
    ".ai/docs.md"
  ]
}
```

Then generate context for your IDE:
```bash
venv\Scripts\python cli.py "your question" --context-only > .ai/docs.md
```
