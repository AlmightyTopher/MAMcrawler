<objective>
Build a powerful search interface for the MAMcrawler audiobook catalog that allows users to quickly find and discover audiobooks from their collection. This interface will provide advanced search capabilities with filters, sorting, and rich result displays.

The search interface should enable users to:
- Search across all audiobook metadata (title, author, narrator, description, tags)
- Apply multiple filters simultaneously (genre, series, language, file format, etc.)
- Sort results by relevance, date, popularity, or other criteria
- View detailed book information with cover images
- Save and manage search queries
- Export search results

This will be the primary way users discover and explore their audiobook library.
</objective>

<context>
This is part of the MAMcrawler project, providing search functionality over the aggregated audiobook metadata from multiple sources including MyAnonamouse, Goodreads, and Audiobookshelf integrations.

The search interface should work seamlessly with the existing data structures and provide fast, relevant results. It will complement the dashboard UI by providing focused discovery capabilities.

Key data sources:
- Audiobook metadata database
- Series and author information
- User ratings and reviews
- File format and quality information
- Download status and availability
</context>

<requirements>
Create a comprehensive search interface with the following features:

1. **Search Input**
   - Main search bar with autocomplete suggestions
   - Advanced search syntax support (AND, OR, NOT, quotes for exact phrases)
   - Search history and saved queries
   - Voice search capability (if supported by browser)

2. **Filter System**
   - Genre/category filters with multi-select
   - Author and narrator filters
   - Series and book number filters
   - Language and file format filters
   - Date range filters (publication, added to library)
   - File size and quality filters
   - Download status filters

3. **Results Display**
   - Grid and list view options
   - Rich book cards with cover images, ratings, and key metadata
   - Pagination with configurable page sizes
   - Sort options (relevance, title, author, date, size, rating)
   - Export results to CSV/JSON

4. **Book Detail View**
   - Full metadata display
   - Series information and navigation
   - Related books suggestions
   - Download actions and status
   - User notes and tags

5. **Search Analytics**
   - Popular search terms
   - Search performance metrics
   - User behavior insights

Implement efficient search algorithms and indexing for fast results, even with large catalogs.
</requirements>

<implementation>
**Technology Stack:**
- HTML5 semantic structure
- CSS3 with modern layout techniques
- Vanilla JavaScript with advanced features (ES6 modules, async/await)
- Web Components or custom elements for reusability
- IndexedDB for client-side caching and search history
- Service Worker for offline capabilities

**Search Architecture:**
- Client-side filtering for small datasets
- Server-side search API for large catalogs
- Hybrid approach with local indexing
- Fuzzy search and typo tolerance
- Relevance scoring and ranking

**Performance Optimizations:**
- Lazy loading of search results
- Virtual scrolling for large result sets
- Debounced search input
- Result caching and prefetching
- Progressive loading of images and metadata

**Accessibility:**
- Full keyboard navigation
- Screen reader support
- High contrast mode support
- Focus management and ARIA labels

**Integration:**
- RESTful API for search queries
- WebSocket for real-time search suggestions
- Local storage for user preferences and history
</implementation>

<output>
Create the following files in the `frontend/` directory (extend existing structure):

- `./frontend/search.html` - Main search interface page
- `./frontend/css/search.css` - Search-specific styling
- `./frontend/js/search.js` - Main search logic and state management
- `./frontend/js/components/` - Additional components:
  - `search-filters.js` - Filter panel and controls
  - `search-results.js` - Results display and pagination
  - `book-detail.js` - Detailed book view modal/component
  - `search-suggestions.js` - Autocomplete and suggestions
- `./frontend/js/services/` - Service modules:
  - `search-service.js` - API communication for search
  - `filter-service.js` - Filter logic and state
  - `export-service.js` - Export functionality
- `./frontend/js/utils/` - Utility functions:
  - `search-utils.js` - Search parsing and scoring
  - `debounce.js` - Input debouncing utilities

Update `./frontend/index.html` to include navigation to the search interface.
</output>

<verification>
Before declaring complete, verify:

1. Search functionality works with various query types and filters
2. Results load quickly and display correctly
3. Filter combinations work properly without conflicts
4. Sort and pagination function as expected
5. Book detail view shows complete metadata
6. Export functionality produces correct output
7. Interface is responsive and accessible
8. Search history and saved queries persist
9. Performance remains good with large result sets

Test with real MAMcrawler data to ensure integration works properly.
</verification>

<success_criteria>
- Fast, accurate search across all audiobook metadata
- Intuitive filter system with multiple simultaneous filters
- Rich result display with all relevant information
- Responsive design working on all devices
- Export capabilities for search results
- Clean, maintainable code with proper separation of concerns
- Comprehensive documentation for features and API
</success_criteria>