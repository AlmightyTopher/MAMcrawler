# Unified Search System

## Overview

The Unified Search System consolidates all audiobook search and discovery functionality into a single, modular framework. This replaces 10+ scattered search scripts with a unified interface supporting MAM, Audiobookshelf, Goodreads, Prowlarr, and local search providers.

## Architecture

```
search_system.py (Main Entry Point)
├── search_types.py (Common Types & Interfaces)
├── search_providers/ (Modular Providers)
│   ├── audiobookshelf_provider.py
│   ├── prowlarr_provider.py
│   ├── local_provider.py
│   └── README.md
└── search_cache/ (Caching System)
    └── cache_manager.py
```

## Key Features

- **Single Entry Point**: `search_system.py` provides unified access to all search functionality
- **Modular Providers**: Each search source is a separate, pluggable module
- **Unified Results**: All providers return standardized `SearchResult` objects
- **Intelligent Caching**: TTL-based caching with automatic cleanup
- **Rate Limiting**: Built-in rate limiting for API compliance
- **Concurrent Search**: Parallel searching across multiple providers
- **Result Deduplication**: Automatic removal of duplicate results
- **Health Monitoring**: Provider health checks and status monitoring

## Quick Start

### Basic Usage

```python
from search_system import UnifiedSearchSystem

async def main():
    async with UnifiedSearchSystem() as search:
        # Search for audiobooks
        results = await search.search_audiobooks("Foundation Asimov")
        print(f"Found {len(results)} results")

        for result in results[:3]:
            print(f"- {result.title} by {result.author} ({result.provider})")

asyncio.run(main())
```

### Convenience Functions

```python
from search_system import search_audiobooks, search_by_author

# Quick search
results = await search_audiobooks("Dune")

# Author search
results = await search_by_author("Brandon Sanderson")
```

## Configuration

Configure providers via environment variables or config objects:

```python
from search_system import SearchConfig, UnifiedSearchSystem

config = SearchConfig(
    audiobookshelf={
        "base_url": "http://localhost:13378",
        "api_token": "your_token"
    },
    prowlarr={
        "base_url": "http://localhost:9696",
        "api_key": "your_key"
    }
)

search = UnifiedSearchSystem(config)
```

### Environment Variables

- `ABS_URL`: Audiobookshelf server URL
- `ABS_TOKEN`: Audiobookshelf API token
- `PROWLARR_URL`: Prowlarr server URL
- `PROWLARR_API_KEY`: Prowlarr API key

## Search Modes

### Quick Search
Fast search prioritizing quality over comprehensiveness:
```python
results = await search.search_audiobooks("query", mode="quick")
```

### Comprehensive Search
Thorough search across all providers and pages:
```python
results = await search.search_audiobooks("query", mode="comprehensive")
```

### Batch Search
Optimized for bulk operations with reliability focus:
```python
results = await search.search_audiobooks("query", mode="batch")
```

## Provider Capabilities

| Provider | Search Types | Key Features |
|----------|-------------|--------------|
| **Audiobookshelf** | Library, Metadata | Owned books, series info, missing detection |
| **Prowlarr** | Torrents, Indexers | Magnet links, multi-indexer, quality scoring |
| **Local** | Vector, Semantic | FAISS similarity, document search |
| **MAM** | Direct, Authenticated | Private tracker, authenticated access |
| **Goodreads** | Metadata, Verification | Author verification, series matching |

## Caching

The system includes intelligent caching:

- **TTL-based expiration**: Different TTLs per provider type
- **Automatic cleanup**: Removes expired entries
- **Size limits**: Prevents cache from growing too large
- **Statistics**: Cache hit/miss monitoring

```python
# Get cache statistics
stats = await search.cache.get_stats()
print(f"Cache size: {stats['size_mb']}MB, {stats['total_entries']} entries")
```

## Result Format

All providers return standardized `SearchResult` objects:

```python
@dataclass
class SearchResult:
    provider: str          # Provider name (e.g., "audiobookshelf")
    query: str            # Original search query
    title: str            # Book title
    author: str           # Author name
    series_name: str      # Series name (if applicable)
    series_position: str  # Position in series (e.g., "#1")
    url: str             # Source URL
    description: str     # Description/summary
    confidence: float    # Result confidence (0.0-1.0)
    magnet_link: str     # Magnet link (for torrents)
    size: int            # Size in bytes
    seeders: int         # Number of seeders
    leechers: int        # Number of leechers
    metadata: dict       # Additional provider-specific data
```

## Advanced Usage

### Provider-Specific Search

```python
# Search only specific providers
from search_system import SearchProvider

results = await search.search_audiobooks(
    "query",
    providers=[SearchProvider.AUDIOBOOKSHELF, SearchProvider.PROWLARR]
)
```

### Custom Filtering

```python
# Search with custom parameters
results = await search.search_audiobooks(
    "query",
    limit=50,
    min_confidence=0.7,
    author="specific_author"
)
```

### Health Monitoring

```python
# Check provider health
health = await search.health_check()
for provider, status in health.items():
    print(f"{provider}: {'✓' if status else '✗'}")
```

### Finding Missing Books

```python
# Compare against owned library
owned_titles = ["Book 1", "Book 2", "Book 3"]
missing = await search.find_missing_books(owned_titles, "Author Name")
```

## Migration from Old Scripts

### Old Approach (Scattered Scripts)
```python
# Multiple separate scripts
from mam_direct_search import MAMDirectSearch
from goodreads_api_client import GoodreadsClient
from prowlarr_title_search import ProwlarrTitleSearch

# Separate initialization and calls
mam = MAMDirectSearch()
goodreads = GoodreadsClient()
prowlarr = ProwlarrTitleSearch()

mam_results = mam.search_audiobooks("query")
gr_results = goodreads.search_books("query")
pr_results = prowlarr.search_prowlarr_for_title("query")
```

### New Approach (Unified System)
```python
# Single unified interface
from search_system import UnifiedSearchSystem

async with UnifiedSearchSystem() as search:
    results = await search.search_audiobooks("query")
    # All providers searched automatically
```

## Performance Considerations

- **Concurrent Execution**: Multiple providers searched in parallel
- **Rate Limiting**: Built-in delays prevent API throttling
- **Caching**: Reduces redundant API calls
- **Pagination**: Automatic handling of paginated results
- **Timeout Handling**: Configurable timeouts prevent hanging

## Error Handling

The system provides comprehensive error handling:

- **Network Errors**: Automatic retries with exponential backoff
- **API Limits**: Rate limiting and quota management
- **Authentication**: Clear error messages for auth failures
- **Timeouts**: Configurable timeouts with graceful degradation
- **Partial Failures**: Continues with available providers if some fail

## Extending the System

### Adding New Providers

1. Create provider in `search_providers/`
2. Implement `SearchProviderInterface`
3. Add to `UnifiedSearchSystem.providers`
4. Update configuration

### Custom Result Processing

```python
# Custom result filtering/sorting
results = await search.search_audiobooks("query")
filtered = [r for r in results if r.confidence > 0.8 and r.seeders > 5]
```

## Troubleshooting

### Common Issues

1. **Provider Not Available**: Check configuration and network connectivity
2. **No Results**: Verify search terms and provider capabilities
3. **Slow Searches**: Check rate limiting and cache status
4. **Authentication Errors**: Verify API keys and tokens

### Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check provider health
health = await search.health_check()
print("Provider status:", health)

# Get cache stats
cache_stats = await search.cache.get_stats()
print("Cache stats:", cache_stats)
```

## API Reference

See individual provider documentation in `search_providers/README.md` for detailed API references.

## Changelog

### v1.0.0
- Initial unified search system
- Consolidated 10+ search scripts
- Modular provider architecture
- Caching and rate limiting
- Comprehensive documentation