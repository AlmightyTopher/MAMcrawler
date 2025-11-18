# Architecture Proposal: MAMcrawler Modular Refactoring

**Date:** 2025-11-18
**Status:** Proposal

---

## Executive Summary

This document proposes a modular architecture to eliminate duplicate code, improve maintainability, and enable easier testing. The refactoring maintains all existing features while organizing the codebase around single-responsibility principles.

---

## Current State Analysis

### Core Workflows Identified

| Workflow | Files Involved | Duplication Level |
|----------|----------------|-------------------|
| Authentication | mam_crawler.py, stealth_mam_crawler.py | High |
| Rate Limiting | mam_crawler.py, comprehensive_guide_crawler.py | Medium |
| HTML Parsing | All crawlers | High |
| Chunking | ingest.py, watcher.py | Critical |
| Embedding | ingest.py, watcher.py | Critical |
| FAISS Operations | ingest.py, watcher.py, cli.py | High |
| File Sanitization | comprehensive_guide_crawler.py, stealth_mam_crawler.py | High |
| Logging Setup | All files | High |

---

## Duplicate Logic Inventory

### 1. Chunking Logic (CRITICAL)

**Location A:** `ingest.py:23-43`
```python
headers_to_split_on = [("#", "H1"), ("##", "H2"), ("###", "H3")]
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on, strip_headers=False
)
splits = markdown_splitter.split_text(markdown_content)

for split in splits:
    header_context = " > ".join(split.metadata.values())
    text_to_embed = f"CONTEXT: {header_context}\n\nCONTENT:\n{split.page_content}"
```

**Location B:** `watcher.py:92-117`
```python
headers_to_split_on = [("#", "H1"), ("##", "H2"), ("###", "H3")]
splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on, strip_headers=False
)
splits = splitter.split_text(content)

for split in splits:
    header_context = " > ".join(split.metadata.values())
    text_to_embed = f"CONTEXT: {header_context}\n\nCONTENT:\n{split.page_content}"
```

**Impact:** Any change to chunking strategy requires updates in both files.

---

### 2. Embedding & FAISS Operations (CRITICAL)

**Location A:** `ingest.py:59-82`
```python
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(all_chunks)
faiss.normalize_L2(embeddings.astype(np.float32))
index.add_with_ids(embeddings.astype(np.float32), np.array(all_chunk_ids))
faiss.write_index(index, "index.faiss")
```

**Location B:** `watcher.py:14, 46-49`
```python
self.model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = self.model.encode(chunks)
faiss.normalize_L2(embeddings.astype(np.float32))
self.index.add_with_ids(embeddings.astype(np.float32), np.array(chunk_ids))
faiss.write_index(self.index, "index.faiss")
```

**Location C:** `cli.py:18-19, 42-47`
```python
index = faiss.read_index("index.faiss")
model = SentenceTransformer('all-MiniLM-L6-v2')
query_vector = model.encode([user_query])
faiss.normalize_L2(query_vector.astype(np.float32))
D, I = index.search(query_vector.astype(np.float32), k)
```

**Impact:** Model name, dimension (384), and normalization strategy duplicated across 3 files.

---

### 3. Filename Sanitization (HIGH)

**Location A:** `comprehensive_guide_crawler.py:36-43`
```python
def sanitize_filename(self, title: str) -> str:
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    filename = re.sub(r'\s+', '_', filename)
    filename = filename[:100]
    return filename
```

**Location B:** `stealth_mam_crawler.py:414-418`
```python
def sanitize_filename(self, title: str) -> str:
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    filename = re.sub(r'\s+', '_', filename)
    return filename[:100]
```

**Impact:** Identical implementation in two files.

---

### 4. User Agent Lists (HIGH)

**Location A:** `mam_crawler.py:59-64` - 3 agents (Chrome 91)
**Location B:** `stealth_mam_crawler.py:75-80` - 4 agents (Chrome 119/120, Firefox 121, Edge)

**Impact:** Inconsistent browser versions; stealth crawler more up-to-date.

---

### 5. Category Extraction (MEDIUM)

**Location A:** `comprehensive_guide_crawler.py:125-140`
```python
def extract_category(self, link_element, href: str) -> str:
    parent = link_element.find_parent(['div', 'section', 'article'])
    if parent:
        heading = parent.find(['h1', 'h2', 'h3', 'h4'])
        if heading:
            return heading.get_text(strip=True)
    # ... URL fallback
```

**Location B:** `stealth_mam_crawler.py:341-350`
```python
def extract_category_from_url(self, url: str) -> str:
    if '?gid=' in url:
        return "Guide"
    path_parts = url.rstrip('/').split('/')
    # ...
```

**Impact:** Different extraction strategies produce inconsistent categories.

---

### 6. Guide Saving to Markdown (MEDIUM)

**Location A:** `comprehensive_guide_crawler.py:313-363`
**Location B:** `stealth_mam_crawler.py:420-458`

Both methods build markdown with:
- Title, URL, Category header
- Metadata (description, author, date)
- Crawled timestamp
- Related links section
- Main content

**Impact:** Similar structure but slightly different field handling.

---

### 7. Logging Configuration (HIGH)

Every file has its own logging setup:
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
```

**Impact:** Inconsistent logging behavior; cannot centrally configure log levels.

---

### 8. BeautifulSoup Import & Parsing (MEDIUM)

Imported inside functions in multiple places:
- `comprehensive_guide_crawler.py:79, 216`
- `stealth_mam_crawler.py:307`

**Impact:** Import overhead on each function call; inconsistent patterns.

---

## Proposed Modular Architecture

### Directory Structure

```
mamcrawler/
├── __init__.py
├── config.py                 # Centralized configuration
├── logging_config.py         # Shared logging setup
│
├── core/
│   ├── __init__.py
│   ├── base_crawler.py       # Abstract base crawler class
│   ├── auth.py               # Authentication module
│   └── rate_limiter.py       # Rate limiting utilities
│
├── crawlers/
│   ├── __init__.py
│   ├── basic.py              # MAMPassiveCrawler
│   ├── comprehensive.py      # EnhancedGuideCrawler
│   └── stealth.py            # StealthMAMCrawler
│
├── rag/
│   ├── __init__.py
│   ├── chunking.py           # Markdown chunking
│   ├── embeddings.py         # SentenceTransformer operations
│   ├── indexing.py           # FAISS index management
│   └── query.py              # Query interface
│
├── storage/
│   ├── __init__.py
│   ├── database.py           # SQLite operations (existing)
│   └── markdown_writer.py    # Guide file operations
│
├── utils/
│   ├── __init__.py
│   ├── sanitize.py           # Filename sanitization
│   ├── html_parser.py        # BeautifulSoup utilities
│   └── category.py           # Category extraction
│
├── cli.py                    # CLI entry point
├── ingest.py                 # Ingestion entry point
└── watcher.py                # File watcher entry point
```

---

## Module Specifications

### 1. config.py - Centralized Configuration

```python
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class CrawlerConfig:
    base_url: str = "https://www.myanonamouse.net"
    min_delay: int = 3
    max_delay: int = 10
    session_timeout: int = 7200  # 2 hours
    max_content_length: int = 5000

@dataclass
class StealthConfig(CrawlerConfig):
    min_delay: int = 10
    max_delay: int = 30
    viewports: List[Tuple[int, int]] = None

    def __post_init__(self):
        self.viewports = [
            (1920, 1080), (1366, 768), (1536, 864),
            (1440, 900), (1600, 900)
        ]

@dataclass
class RAGConfig:
    model_name: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    index_path: str = "index.faiss"
    db_path: str = "metadata.sqlite"
    top_k: int = 5
    headers_to_split: List[Tuple[str, str]] = None

    def __post_init__(self):
        self.headers_to_split = [
            ("#", "H1"), ("##", "H2"), ("###", "H3")
        ]

# Shared user agents (kept up-to-date)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

# Allowed paths (single source of truth)
ALLOWED_PATHS = ["/", "/t/", "/tor/browse.php", "/tor/search.php", "/guides/", "/f/"]
```

---

### 2. rag/chunking.py - Unified Chunking

```python
from typing import List, Tuple
from langchain_text_splitters.markdown import MarkdownHeaderTextSplitter
from ..config import RAGConfig

class MarkdownChunker:
    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.config.headers_to_split,
            strip_headers=False
        )

    def chunk(self, content: str) -> List[Tuple[str, str, str]]:
        """
        Chunk markdown content.

        Returns:
            List of (text_to_embed, raw_text, header_context) tuples
        """
        splits = self.splitter.split_text(content)
        results = []

        for split in splits:
            header_context = " > ".join(split.metadata.values())
            text_to_embed = f"CONTEXT: {header_context}\n\nCONTENT:\n{split.page_content}"
            results.append((text_to_embed, split.page_content, header_context))

        return results
```

---

### 3. rag/embeddings.py - Unified Embedding Operations

```python
import numpy as np
from sentence_transformers import SentenceTransformer
from ..config import RAGConfig

class EmbeddingService:
    _instance = None

    def __new__(cls, config: RAGConfig = None):
        # Singleton to avoid loading model multiple times
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: RAGConfig = None):
        if self._initialized:
            return
        self.config = config or RAGConfig()
        self.model = SentenceTransformer(self.config.model_name)
        self._initialized = True

    def encode(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """Encode texts to embeddings."""
        embeddings = self.model.encode(texts)
        if normalize:
            import faiss
            embeddings = embeddings.astype(np.float32)
            faiss.normalize_L2(embeddings)
        return embeddings

    @property
    def dimension(self) -> int:
        return self.config.dimension
```

---

### 4. rag/indexing.py - FAISS Index Management

```python
import faiss
import numpy as np
from pathlib import Path
from ..config import RAGConfig

class FAISSIndexManager:
    def __init__(self, config: RAGConfig = None):
        self.config = config or RAGConfig()
        self.index_path = Path(self.config.index_path)
        self.index = self._load_or_create()

    def _load_or_create(self) -> faiss.Index:
        if self.index_path.exists():
            return faiss.read_index(str(self.index_path))
        base_index = faiss.IndexFlatL2(self.config.dimension)
        return faiss.IndexIDMap(base_index)

    def add(self, embeddings: np.ndarray, ids: np.ndarray):
        """Add embeddings with IDs."""
        self.index.add_with_ids(embeddings, ids)

    def remove(self, ids: np.ndarray):
        """Remove embeddings by IDs."""
        self.index.remove_ids(ids)

    def search(self, query_embedding: np.ndarray, k: int = None) -> Tuple[np.ndarray, np.ndarray]:
        """Search for similar embeddings."""
        k = k or self.config.top_k
        return self.index.search(query_embedding, k)

    def save(self):
        """Persist index to disk."""
        faiss.write_index(self.index, str(self.index_path))
```

---

### 5. utils/sanitize.py - Unified Sanitization

```python
import re

def sanitize_filename(title: str, max_length: int = 100) -> str:
    """Convert title to valid filename."""
    filename = re.sub(r'[<>:"/\\|?*]', '', title)
    filename = re.sub(r'\s+', '_', filename)
    return filename[:max_length]

def anonymize_content(content: str, max_length: int = 5000) -> str:
    """Remove PII from content."""
    # Remove emails
    content = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL]', content
    )
    # Remove usernames
    content = re.sub(r'\buser[_-]\w+\b', '[USER]', content, flags=re.IGNORECASE)
    return content[:max_length]
```

---

### 6. storage/markdown_writer.py - Unified File Writer

```python
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from ..utils.sanitize import sanitize_filename

class GuideMarkdownWriter:
    def __init__(self, output_dir: str = "guides_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def save_guide(self, guide_data: Dict[str, Any]) -> Path:
        """Save guide to markdown file."""
        if not guide_data.get('success'):
            return None

        filename = sanitize_filename(guide_data['title']) + ".md"
        filepath = self.output_dir / filename

        content = self._build_markdown(guide_data)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        return filepath

    def _build_markdown(self, data: Dict[str, Any]) -> str:
        """Build markdown content from guide data."""
        lines = [
            f"# {data['title']}",
            "",
            f"**URL:** {data['url']}",
            f"**Category:** {data.get('category', 'General')}",
        ]

        if data.get('description'):
            lines.append(f"**Description:** {data['description']}")
        if data.get('author'):
            lines.append(f"**Author:** {data['author']}")
        if data.get('last_updated'):
            lines.append(f"**Last Updated:** {data['last_updated']}")
        if data.get('tags'):
            lines.append(f"**Tags:** {data['tags']}")

        lines.extend([
            f"**Crawled:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
        ])

        # Related links
        sub_links = data.get('sub_links') or data.get('links', {}).get('internal', [])
        if sub_links:
            lines.append("## Related Guides")
            lines.append("")
            for link in sub_links[:20]:
                if isinstance(link, dict):
                    lines.append(f"- [{link['title']}]({link['url']})")
                else:
                    lines.append(f"- {link}")
            lines.extend(["", "---", ""])

        lines.extend([
            "## Content",
            "",
            data.get('content', 'No content extracted')
        ])

        return "\n".join(lines)
```

---

### 7. core/base_crawler.py - Abstract Base

```python
from abc import ABC, abstractmethod
import random
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
from ..config import CrawlerConfig, USER_AGENTS, ALLOWED_PATHS

class BaseCrawler(ABC):
    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        self.base_url = self.config.base_url
        self.last_request = datetime.now()
        self.user_agents = USER_AGENTS
        self.allowed_paths = ALLOWED_PATHS

    def get_random_user_agent(self) -> str:
        return random.choice(self.user_agents)

    def is_allowed_path(self, url: str) -> bool:
        from urllib.parse import urlparse
        parsed = urlparse(url)

        if parsed.netloc != "www.myanonamouse.net":
            return False

        path = parsed.path
        for allowed in self.allowed_paths:
            if allowed == "/" and path == "/":
                return True
            elif allowed != "/" and path.startswith(allowed):
                return True
        return False

    async def rate_limit(self):
        """Enforce rate limiting."""
        elapsed = (datetime.now() - self.last_request).total_seconds()
        if elapsed < self.config.min_delay:
            delay = random.uniform(self.config.min_delay, self.config.max_delay)
            await asyncio.sleep(delay)
        self.last_request = datetime.now()

    @abstractmethod
    async def crawl_page(self, url: str) -> dict:
        pass
```

---

## Migration Strategy

### Phase 1: Create Core Infrastructure (Low Risk)
1. Create `config.py` with all constants
2. Create `logging_config.py`
3. Create `utils/sanitize.py`
4. All existing code continues working

### Phase 2: Extract RAG Components (Medium Risk)
1. Create `rag/chunking.py`
2. Create `rag/embeddings.py`
3. Create `rag/indexing.py`
4. Update `ingest.py` to use new modules
5. Update `watcher.py` to use new modules
6. Update `cli.py` to use new modules
7. Run tests to verify behavior

### Phase 3: Extract Storage Layer (Low Risk)
1. Create `storage/markdown_writer.py`
2. Update crawlers to use writer
3. Keep database.py as-is (already well-abstracted)

### Phase 4: Refactor Crawlers (Higher Risk)
1. Create `core/base_crawler.py`
2. Create `core/auth.py`
3. Refactor `MAMPassiveCrawler` to inherit from base
4. Refactor `EnhancedGuideCrawler` to use shared components
5. Refactor `StealthMAMCrawler` to use shared components
6. Extensive testing required

### Phase 5: Testing & Documentation
1. Add unit tests for each new module
2. Add integration tests
3. Update CLAUDE.md with new architecture

---

## Benefits of Refactoring

| Benefit | Impact |
|---------|--------|
| Reduced code duplication | ~40% less code |
| Single source of truth | Config changes propagate everywhere |
| Better testability | Each module can be unit tested |
| Easier maintenance | Bug fixes apply everywhere |
| Consistent behavior | Same chunking/embedding across system |
| Faster onboarding | Clear module responsibilities |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Phased migration with tests |
| Import complexity | Clear package structure with `__init__.py` |
| Performance regression | Singleton for embedding model |
| Backward compatibility | Keep entry points (cli.py, ingest.py) |

---

## Estimated Effort

| Phase | Effort | Risk |
|-------|--------|------|
| Phase 1: Core Infrastructure | 2-3 hours | Low |
| Phase 2: RAG Components | 3-4 hours | Medium |
| Phase 3: Storage Layer | 1-2 hours | Low |
| Phase 4: Crawler Refactor | 4-6 hours | High |
| Phase 5: Testing & Docs | 3-4 hours | Low |
| **Total** | **13-19 hours** | - |

---

## Conclusion

The proposed architecture eliminates critical code duplication while maintaining all existing functionality. The phased migration approach minimizes risk and allows for incremental validation.

### Immediate Quick Wins (< 2 hours)
1. Extract `utils/sanitize.py` - Used by 2 crawlers
2. Extract `rag/chunking.py` - Critical duplication
3. Create `config.py` - Centralize constants

### High-Value Refactors
1. Unified RAG pipeline - Fixes the critical chunking/embedding duplication
2. Base crawler class - Reduces crawler maintenance burden

The modular architecture will significantly improve code quality while enabling easier feature additions and bug fixes across the entire system.
