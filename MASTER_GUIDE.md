# MAMcrawler - Master Navigation Guide

**The Best Audiobook Finder, Downloader, Organizer & Streaming System**

> Complete documentation and feature map for the MAMcrawler system

---

## What is MAMcrawler?

MAMcrawler is a comprehensive audiobook management ecosystem that:

- **Finds** audiobooks from multiple sources (Goodreads, Hardcover, MyAnonamouse, Prowlarr)
- **Downloads** books from torrent sources with VPN failover protection
- **Organizes** your library with automatic metadata enrichment
- **Streams** to Audiobookshelf with perfect organization
- **Completes** series by finding missing books
- **Repairs** low-quality editions with better versions
- **Verifies** metadata accuracy across your library

---

## Quick Start (5 Minutes)

### Install & Run

```bash
# 1. Clone and setup
git clone <repo>
cd MAMcrawler
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your Goodreads/Hardcover credentials

# 3. Run the server
python -m backend.main

# 4. Access the UI
# Open http://localhost:8000 in browser
```

### First Task: Import Your Library

```bash
# Find missing books in your library
curl http://localhost:8000/api/library/gaps --header "Authorization: Bearer YOUR_TOKEN"

# Or use the UI: http://localhost:8000
```

---

## Complete Feature Map

### Library Discovery

**Find Books & Series**
```bash
# Search for author's complete works
python scripts/discovery/author_search.py "Brandon Sanderson"

# Search across torrent indexers
python scripts/discovery/prowlarr_search.py --query "Sanderson" --limit 50

# Search MAM directly
python scripts/discovery/mam_search.py --genre fantasy --limit 20
```

**API Endpoints**
```
GET  /api/library/books              # List all books
GET  /api/library/books/{id}         # Get single book
POST /api/library/books              # Add new book
GET  /api/library/gaps               # Find missing books
GET  /api/library/series             # List series
GET  /api/library/series/{id}/gaps   # Missing in series
```

---

### Metadata Management

**Enrich Metadata from Multiple Sources**
```bash
# Sync with Hardcover.app
python scripts/library/metadata_sync.py --source hardcover --limit 500

# Sync with Goodreads
python scripts/library/metadata_sync.py --source goodreads --limit 500

# Sync both (parallel)
python scripts/library/metadata_sync.py --source all --limit 500
```

**API Endpoints**
```
POST /api/library/metadata/{id}/enrich    # Enrich single book
POST /api/library/metadata/batch-sync     # Batch enrich
GET  /api/library/metadata/{id}           # Get metadata
PATCH /api/library/metadata/{id}          # Update metadata
```

**Features**
- Goodreads web crawler (90%+ success rate)
- Hardcover API integration (when available)
- Google Books fallback
- OpenLibrary support
- Audible metadata extraction
- Narrator detection from metadata
- Cover art management

---

### Series Completion

**Automatically Find Missing Books**
```bash
# Find gaps in all series
python scripts/library/series_completion.py --full-scan

# Find missing for specific author
python scripts/library/series_completion.py --author "Patrick Rothfuss"

# Queue missing books for download
python scripts/library/series_completion.py --auto-queue
```

**API Endpoints**
```
GET  /api/library/series                 # List all series
GET  /api/library/series/{id}            # Get series details
GET  /api/library/series/{id}/gaps       # Missing books
POST /api/library/series/{id}/complete   # Queue missing books
```

---

### Download Management

**Queue & Monitor Downloads**
```bash
# Check qBittorrent status
python scripts/downloads/queue_manager.py --status

# Monitor active downloads
python scripts/downloads/monitor.py --watch --interval 5

# Emergency ratio recovery
python scripts/downloads/ratio_recovery.py --threshold 0.5
```

**API Endpoints**
```
GET  /api/downloads/queue               # Current queue
POST /api/downloads/add                 # Add torrent
GET  /api/downloads/{id}/status         # Download progress
DELETE /api/downloads/{id}              # Cancel download
GET  /api/downloads/stats               # Download statistics
```

**Features**
- Dual qBittorrent instances for resilience
- VPN failover (primary + backup)
- Automatic quality detection
- Series-aware batch downloading
- Rate limiting respects ratio
- Pause/resume controls

---

### Quality & Repair

**Find & Replace Low-Quality Editions**
```bash
# Detect low-quality books
python scripts/library/repair.py --scan

# Auto-repair with better editions
python scripts/library/repair.py --auto-repair

# Manual replacement
python scripts/library/repair.py --book-id 123 --replacement-id 456
```

**API Endpoints**
```
GET  /api/library/quality/audit         # Quality report
GET  /api/library/books/{id}/editions   # Available editions
POST /api/library/books/{id}/repair     # Replace edition
GET  /api/library/repairs/status        # Repair history
```

**Quality Metrics**
- Bitrate >= 128 kbps (preferred >= 192)
- Complete chapter markers
- Narrator accuracy
- Duration accuracy
- Metadata completeness

---

### Library Verification

**Verify Metadata Accuracy**
```bash
# Full library verification
python scripts/library/verify.py --full

# Verify specific book
python scripts/library/verify.py --book-id 123

# Verify entire series
python scripts/library/verify.py --series-id 456

# Check narrator accuracy
python scripts/library/verify.py --check narrator
```

**API Endpoints**
```
POST /api/library/verify/full            # Full verification
POST /api/library/verify/book/{id}       # Verify book
POST /api/library/verify/series/{id}     # Verify series
GET  /api/library/verify/report          # Verification report
```

**Verification Methods**
- ISBN validation
- Goodreads matching
- Chapter count validation
- Duration validation
- Narrator verification
- Author/series cross-checking

---

### System Health & Diagnostics

**Check System Status**
```bash
# Full system diagnostic
python scripts/diagnostics/health.py --full

# Check specific service
python scripts/diagnostics/health.py --service mam
python scripts/diagnostics/health.py --service goodreads
python scripts/diagnostics/health.py --service hardcover
python scripts/diagnostics/health.py --service qbittorrent
python scripts/diagnostics/health.py --service abs
python scripts/diagnostics/health.py --service prowlarr
```

**API Endpoints**
```
GET  /api/health                        # Overall health
GET  /api/health/services               # Service status
GET  /api/health/connections            # Connection checks
GET  /api/system/metrics                # System metrics
```

---

## File Organization

```
MAMcrawler/
├── 📚 docs/                    Master documentation
│   ├── README.md              # This file
│   ├── QUICK_START.md         # Quick setup guide
│   ├── INSTALLATION.md        # Detailed installation
│   ├── API_REFERENCE.md       # REST API docs
│   ├── INTEGRATIONS/          # Service integration guides
│   └── TROUBLESHOOTING.md     # Common issues
│
├── 🔧 scripts/                User-facing tools
│   ├── discovery/             # Search & find books
│   ├── library/               # Library management
│   ├── downloads/             # Download management
│   ├── diagnostics/           # System health checks
│   ├── maintenance/           # Cleanup & backups
│   └── dev/                   # Development tools
│
├── 🚀 backend/                FastAPI REST API
│   ├── main.py               # Server entry point
│   ├── routes/               # API endpoints
│   ├── services/             # Business logic (46 services)
│   ├── integrations/         # External service clients
│   ├── models/               # Data models
│   ├── schedulers/           # Background tasks
│   ├── tests/                # Test suite
│   └── middleware/           # Error handling, CORS, etc.
│
├── 📦 mamcrawler/            Core package
│   ├── audio_processing/     # Audio merging, normalization
│   ├── metadata/             # Multi-source metadata enrichment
│   ├── repair/               # Edition replacement
│   ├── verification/         # Metadata validation
│   ├── rag/                  # RAG system (FAISS + embeddings)
│   ├── series_completion.py  # Series gap detection
│   └── quality.py            # Quality scoring
│
├── 📋 config/                Configuration files
│   ├── .env                  # Secrets (DO NOT COMMIT)
│   ├── .env.example          # Template
│   └── config.py             # Pydantic settings
│
├── 📁 outputs/               Generated reports & data
│   ├── reports/              # Sync reports, analysis
│   ├── data/                 # JSON data exports
│   ├── logs/                 # Application logs
│   └── cache/                # Search result caches
│
├── 💾 state/                 Crawler state persistence
│   ├── abs_crawler_state.json
│   └── stealth_crawler_state.json
│
├── 🗂️ archive/               Legacy & reference code
│   ├── legacy_crawlers/      # Old crawler versions
│   └── deprecated_guides/    # Old documentation
│
└── 📄 README.md              Project overview
```

---

## Common Tasks

### Task: Find Missing Books in a Series

```bash
# Step 1: Find the series
python scripts/discovery/author_search.py "Patrick Rothfuss"

# Step 2: Check what's missing
curl http://localhost:8000/api/library/series/123/gaps

# Step 3: Queue missing books
curl -X POST http://localhost:8000/api/library/series/123/complete
```

### Task: Sync All Books with Metadata

```bash
# Option 1: Use Goodreads (faster, 90%+ success)
python scripts/library/metadata_sync.py --source goodreads --limit 500

# Option 2: Use Hardcover (slower, when API works)
python scripts/library/metadata_sync.py --source hardcover --limit 100

# Option 3: Run both in parallel
python scripts/library/metadata_sync.py --source all --limit 500 --parallel
```

### Task: Replace Low-Quality Edition

```bash
# Step 1: Find the bad edition
python scripts/library/repair.py --scan

# Step 2: Check available replacements
curl http://localhost:8000/api/library/books/123/editions

# Step 3: Replace with better edition
curl -X POST http://localhost:8000/api/library/books/123/repair \
  -H "Content-Type: application/json" \
  -d '{"replacement_goodreads_id": "456789"}'
```

### Task: Download Missing Series

```bash
# Step 1: Identify missing books
python scripts/library/series_completion.py --full-scan

# Step 2: Queue downloads
python scripts/library/series_completion.py --auto-queue

# Step 3: Monitor progress
python scripts/downloads/monitor.py --watch

# Step 4: Verify after download
python scripts/library/verify.py --full
```

### Task: Emergency Ratio Recovery

```bash
# If qBittorrent ratio is below threshold
python scripts/downloads/ratio_recovery.py --threshold 0.5

# This will:
# 1. Stop non-priority downloads
# 2. Use VPN connection if available
# 3. Prioritize high-seed torrents
# 4. Resume when ratio recovered
```

---

## Integration Guides

### Goodreads Integration
- **Status**: Working, 90%+ success rate
- **Guide**: See `docs/integrations/goodreads.md`
- **Command**: `python scripts/library/metadata_sync.py --source goodreads`

### Hardcover Integration
- **Status**: Available, API sometimes returns 404
- **Guide**: See `docs/integrations/hardcover.md`
- **Command**: `python scripts/library/metadata_sync.py --source hardcover`

### AudiobookShelf Integration
- **Status**: Working
- **Guide**: See `docs/integrations/audiobookshelf.md`
- **Features**: Automatic metadata sync, library organization

### Prowlarr Integration
- **Status**: Working
- **Guide**: See `docs/integrations/prowlarr.md`
- **Command**: `python scripts/discovery/prowlarr_search.py`

### qBittorrent Integration
- **Status**: Working with VPN failover
- **Guide**: See `docs/integrations/qbittorrent.md`
- **Features**: Dual instances, ratio monitoring, auto-pausing

### MyAnonamouse Integration
- **Status**: Working (passive crawling only)
- **Guide**: See `docs/integrations/mam.md`
- **Features**: Stealth crawling, category filtering

---

## API Quick Reference

### Authentication
```bash
# Get API token
curl -X POST http://localhost:8000/api/auth/token \
  -d "username=admin&password=password"

# Use token in requests
curl http://localhost:8000/api/library/books \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Browse Books
```bash
# Get all books
GET /api/library/books

# Search books
GET /api/library/books?search=sanderson&limit=10

# Filter by series
GET /api/library/books?series_id=123

# Filter by author
GET /api/library/books?author_id=456
```

### Add/Update Books
```bash
# Add new book
POST /api/library/books
  {
    "title": "Book Title",
    "author_id": 123,
    "isbn": "9780123456789",
    "metadata_from": "goodreads"
  }

# Update book
PATCH /api/library/books/123
  {
    "rating": 4.5,
    "narrator": "Michael Kramer"
  }
```

### Manage Downloads
```bash
# Queue download
POST /api/downloads/add
  {
    "magnet_link": "magnet:?xt=urn:...",
    "book_id": 123,
    "priority": "high"
  }

# Check status
GET /api/downloads/123/status

# Pause download
PATCH /api/downloads/123
  {"action": "pause"}
```

---

## Troubleshooting

### Issue: Goodreads sync failing
**Solution**: See `docs/TROUBLESHOOTING.md#goodreads-sync`

### Issue: qBittorrent not connecting
**Solution**: See `docs/TROUBLESHOOTING.md#qbittorrent-connection`

### Issue: VPN failover not working
**Solution**: See `docs/TROUBLESHOOTING.md#vpn-failover`

### Issue: Metadata missing for books
**Solution**: See `docs/TROUBLESHOOTING.md#metadata-enrichment`

---

## Development

### Running Tests
```bash
# All tests
pytest backend/tests/ -v

# Integration tests only
pytest backend/tests/test_integration.py -v

# With coverage
pytest backend/tests/ --cov=backend --cov-report=html
```

### Code Quality
```bash
# Format code
black scripts/ backend/ mamcrawler/

# Lint
flake8 scripts/ backend/ mamcrawler/

# Type check
mypy scripts/ backend/ mamcrawler/
```

### Adding New Features
1. See `docs/DEVELOPMENT.md` for architecture
2. Create feature branch: `git checkout -b feature/my-feature`
3. Add tests before implementation
4. Update documentation
5. Submit PR

---

## Performance Tips

1. **Use dual qBittorrent instances** for faster downloads
2. **Enable VPN failover** for reliable access
3. **Batch metadata sync** with `--limit 500` for efficiency
4. **Schedule daily syncs** at off-peak hours (midnight)
5. **Monitor ratio** and enable auto-recovery
6. **Keep state files** for resumable crawling

---

## System Requirements

- **Python 3.9+**
- **8GB RAM** (16GB recommended for large libraries)
- **SSD** (for database and cache)
- **Stable internet** with VPN access to torrent sites
- **qBittorrent** or similar torrent client
- **AudiobookShelf** (for library serving)

---

## Support & Troubleshooting

- **Documentation**: `docs/`
- **Common Issues**: `docs/TROUBLESHOOTING.md`
- **API Reference**: `docs/API_REFERENCE.md`
- **Configuration**: `docs/CONFIGURATION.md`
- **Development**: `docs/DEVELOPMENT.md`

---

## License & Credits

See LICENSE file for terms.

---

**Last Updated**: November 29, 2025
**Version**: 2.0 (Post-Refactoring)
**Status**: Production Ready

---

## What's Next?

Check out the [Quick Start Guide](docs/QUICK_START.md) to get up and running in 5 minutes!

Or jump to a specific task:
- [Find Missing Books](docs/EXAMPLES.md#find-missing-books)
- [Download a Series](docs/EXAMPLES.md#download-series)
- [Sync Metadata](docs/EXAMPLES.md#sync-metadata)
- [Fix Bad Metadata](docs/EXAMPLES.md#fix-metadata)
- [Set Up Streaming](docs/INTEGRATIONS.md#audiobookshelf)

