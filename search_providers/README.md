# Search Providers

This directory contains modular search provider implementations for the unified search system.

## Architecture

Each search provider implements the `SearchProviderInterface` and provides:

- **Standardized Interface**: All providers use the same `SearchQuery` input and return `SearchResult` objects
- **Configuration**: Provider-specific configuration via config dictionaries
- **Rate Limiting**: Built-in rate limiting to respect API limits
- **Health Checks**: Provider health monitoring
- **Error Handling**: Consistent error handling and logging

## Available Providers

### AudiobookshelfSearchProvider (`audiobookshelf_provider.py`)

**Purpose**: Search local Audiobookshelf library

**Capabilities**:
- `library_search`: Search owned audiobooks
- `metadata_search`: Get detailed metadata
- `collection_search`: Search collections

**Configuration**:
```python
{
    "base_url": "http://localhost:13378",
    "api_token": "your_token_here"
}
```

**Features**:
- Full library search with pagination
- Author-based filtering
- Series information extraction
- Missing book detection

### ProwlarrSearchProvider (`prowlarr_provider.py`)

**Purpose**: Search torrent indexers via Prowlarr

**Capabilities**:
- `torrent_search`: Search for torrent files
- `indexer_search`: Multi-indexer search
- `magnet_extraction`: Extract magnet links

**Configuration**:
```python
{
    "base_url": "http://localhost:9696",
    "api_key": "your_api_key_here"
}
```

**Features**:
- Multi-indexer search
- Audiobook category filtering
- Quality scoring based on seeders/size
- Magnet link extraction

### LocalSearchProvider (`local_provider.py`)

**Purpose**: Vector similarity search using FAISS

**Capabilities**:
- `vector_search`: Semantic similarity search
- `semantic_search`: Meaning-based search
- `local_knowledge`: Search indexed documents

**Configuration**:
```python
{
    "index_file": "index.faiss",
    "metadata_file": "metadata.sqlite",
    "model_name": "all-MiniLM-L6-v2"
}
```

**Features**:
- FAISS vector similarity search
- SQLite metadata storage
- Configurable embedding models
- Document chunking and indexing

## Provider Interface

All providers must implement:

```python
class SearchProviderInterface(ABC):
    PROVIDER_TYPE: str = "base"
    CAPABILITIES: List[str] = []
    RATE_LIMITS: Dict[str, Union[int, float]] = {...}
    CONFIG_REQUIRED: List[str] = []

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform search"""
        pass

    async def health_check(self) -> bool:
        """Check provider health"""
        pass
```

## Adding New Providers

To add a new search provider:

1. Create a new file in this directory
2. Implement `SearchProviderInterface`
3. Set appropriate `PROVIDER_TYPE`, `CAPABILITIES`, and `RATE_LIMITS`
4. Add configuration requirements to `CONFIG_REQUIRED`
5. Update the main `search_system.py` to import and initialize the provider

## Configuration

Providers are configured via the `SearchConfig` class in `search_system.py`:

```python
config = SearchConfig(
    audiobookshelf={
        "base_url": "http://localhost:13378",
        "api_token": "..."
    },
    prowlarr={
        "base_url": "http://localhost:9696",
        "api_key": "..."
    },
    local={
        "index_file": "path/to/index.faiss",
        "metadata_file": "path/to/metadata.sqlite"
    }
)
```

## Rate Limiting

Each provider includes built-in rate limiting:

- **Requests per minute**: Maximum API calls per minute
- **Delay seconds**: Minimum delay between requests

These can be customized per provider based on API limits.

## Error Handling

Providers handle errors consistently:

- Network timeouts and connection errors
- API rate limiting
- Invalid responses
- Authentication failures

All errors are logged and converted to appropriate exceptions.

## Testing

Each provider includes a `health_check()` method for testing connectivity and basic functionality.

Run health checks:

```python
async with UnifiedSearchSystem() as search:
    health = await search.health_check()
    print(f"Provider health: {health}")