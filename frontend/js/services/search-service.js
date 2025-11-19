/**
 * Search service for API communication
 * Adapted to work with the existing MAMcrawler backend API
 */

const API_BASE_URL = 'http://localhost:8000';

class SearchService {
    constructor() {
        this.cache = new Map();
        this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
    }

    /**
     * Perform a search query
     * Note: The current backend has limited search capabilities.
     * This implementation works with the existing /api/books/search endpoint
     * and applies client-side filtering for advanced features.
     */
    async searchBooks(query, options = {}) {
        const cacheKey = this._getCacheKey('search', query, options);

        // Check cache first
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
            this.cache.delete(cacheKey);
        }

        try {
            // The current backend only supports basic title/author search
            // We'll use the existing search endpoint and apply client-side filtering
            const params = new URLSearchParams({
                query: query,
                limit: Math.max(options.limit || 24, 100) // Get more results for client-side filtering
            });

            const url = `${API_BASE_URL}/api/books/search?${params}`;
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Search failed: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Search failed');
            }

            let books = result.data.books || [];

            // Apply client-side filtering for advanced features
            if (options.filters) {
                books = this._applyClientSideFilters(books, options.filters);
            }

            // Apply client-side sorting
            if (options.sortBy) {
                books = this._applyClientSideSorting(books, options.sortBy, options.sortDirection || 'desc');
            }

            // Apply pagination
            const totalBooks = books.length;
            const offset = options.offset || 0;
            const limit = options.limit || 24;
            books = books.slice(offset, offset + limit);

            // Transform books to match expected format
            const transformedBooks = books.map(book => ({
                id: book.id,
                title: book.title || 'Unknown Title',
                author: book.author || '',
                series: book.series || '',
                series_number: book.series_number || '',
                abs_id: book.abs_id || '',
                metadata_completeness_percent: book.metadata_completeness_percent || 0,
                status: book.status || 'active',
                date_added: book.date_added || null,
                // Add placeholder fields for UI compatibility
                cover_url: null, // No cover images in current backend
                description: '', // No descriptions in current search results
                published_year: null,
                duration_minutes: null,
                language: 'English', // Default assumption
                format: 'Unknown',
                file_size_bytes: null,
                narrator: '',
                publisher: '',
                isbn: book.isbn || '',
                asin: book.asin || '',
                relevance_score: 1.0 // Default relevance score
            }));

            const transformedResult = {
                success: true,
                data: transformedBooks,
                total: totalBooks,
                error: null,
                query: query,
                timestamp: Date.now()
            };

            // Cache the result
            this.cache.set(cacheKey, {
                data: transformedResult,
                timestamp: Date.now()
            });

            return transformedResult;

        } catch (error) {
            console.error('Search API error:', error);
            return {
                success: false,
                data: [],
                total: 0,
                error: error.message,
                query: query,
                timestamp: Date.now()
            };
        }
    }

    /**
     * Apply client-side filtering (for features not supported by backend)
     */
    _applyClientSideFilters(books, filters) {
        return books.filter(book => {
            // Status filter
            if (filters.status && filters.status !== 'active' && book.status !== filters.status) {
                return false;
            }

            // Author filter (case-insensitive partial match)
            if (filters.author && book.author &&
                !book.author.toLowerCase().includes(filters.author.toLowerCase())) {
                return false;
            }

            // Series filter (case-insensitive partial match)
            if (filters.series && book.series &&
                !book.series.toLowerCase().includes(filters.series.toLowerCase())) {
                return false;
            }

            // Language filter (placeholder - backend doesn't have this)
            if (filters.language && filters.language !== '' && filters.language !== 'english') {
                return false; // Only English books in current system
            }

            // Format filter (placeholder - backend doesn't have this)
            if (filters.format && filters.format !== '') {
                return false; // No format filtering available
            }

            // Completeness filter
            if (filters.completenessMin && book.metadata_completeness_percent < filters.completenessMin) {
                return false;
            }

            return true;
        });
    }

    /**
     * Apply client-side sorting
     */
    _applyClientSideSorting(books, sortBy, direction) {
        const sortOrder = direction === 'asc' ? 1 : -1;

        return books.sort((a, b) => {
            let aValue, bValue;

            switch (sortBy) {
                case 'title':
                    aValue = (a.title || '').toLowerCase();
                    bValue = (b.title || '').toLowerCase();
                    break;
                case 'author':
                    aValue = (a.author || '').toLowerCase();
                    bValue = (b.author || '').toLowerCase();
                    break;
                case 'series':
                    aValue = (a.series || '').toLowerCase();
                    bValue = (b.series || '').toLowerCase();
                    break;
                case 'date_added':
                    aValue = a.date_added ? new Date(a.date_added) : new Date(0);
                    bValue = b.date_added ? new Date(b.date_added) : new Date(0);
                    break;
                case 'metadata_completeness_percent':
                    aValue = a.metadata_completeness_percent || 0;
                    bValue = b.metadata_completeness_percent || 0;
                    break;
                case 'relevance':
                default:
                    // Keep original order for relevance (already sorted by backend)
                    return 0;
            }

            if (aValue < bValue) return -sortOrder;
            if (aValue > bValue) return sortOrder;
            return 0;
        });
    }

    /**
     * Get book details by ID
     */
    async getBookDetails(bookId) {
        const cacheKey = this._getCacheKey('book', bookId);

        // Check cache
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
            this.cache.delete(cacheKey);
        }

        try {
            const url = `${API_BASE_URL}/api/books/${bookId}`;
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to get book details: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Failed to get book details');
            }

            const book = result.data;

            // Transform to match expected format
            const transformedBook = {
                id: book.id,
                title: book.title || 'Unknown Title',
                author: book.author || '',
                series: book.series || '',
                series_number: book.series_number || '',
                abs_id: book.abs_id || '',
                metadata_completeness_percent: book.metadata_completeness_percent || 0,
                status: book.status || 'active',
                date_added: book.date_added || null,
                last_metadata_update: book.last_metadata_update || null,
                metadata_source: book.metadata_source || {},
                import_source: book.import_source || '',
                // Add placeholder fields
                cover_url: null,
                description: book.description || '',
                published_year: book.published_year || null,
                duration_minutes: book.duration_minutes || null,
                language: 'English',
                format: 'Unknown',
                file_size_bytes: null,
                narrator: '',
                publisher: book.publisher || '',
                isbn: book.isbn || '',
                asin: book.asin || ''
            };

            // Cache the result
            this.cache.set(cacheKey, {
                data: transformedBook,
                timestamp: Date.now()
            });

            return transformedBook;

        } catch (error) {
            console.error('Book details API error:', error);
            throw error;
        }
    }

    /**
     * Get books in a series
     */
    async getSeriesBooks(seriesName) {
        const cacheKey = this._getCacheKey('series', seriesName);

        // Check cache
        if (this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < this.cacheTimeout) {
                return cached.data;
            }
            this.cache.delete(cacheKey);
        }

        try {
            const url = `${API_BASE_URL}/api/books/series/${encodeURIComponent(seriesName)}`;
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Failed to get series books: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();

            if (!result.success) {
                throw new Error(result.error || 'Failed to get series books');
            }

            // Transform books
            const transformedBooks = (result.data.books || []).map(book => ({
                id: book.id,
                title: book.title || 'Unknown Title',
                author: book.author || '',
                series: book.series || '',
                series_number: book.series_number || '',
                published_year: book.published_year || null,
                metadata_completeness_percent: book.metadata_completeness_percent || 0,
                status: book.status || 'active'
            }));

            const transformedResult = {
                series_name: result.data.series_name,
                books: transformedBooks,
                total_books: result.data.total_books
            };

            // Cache the result
            this.cache.set(cacheKey, {
                data: transformedResult,
                timestamp: Date.now()
            });

            return transformedResult;

        } catch (error) {
            console.error('Series books API error:', error);
            throw error;
        }
    }

    /**
     * Get search suggestions
     */
    async getSearchSuggestions(query, limit = 10) {
        if (!query || query.length < 2) {
            return [];
        }

        try {
            // Use the existing search endpoint with a small limit
            const result = await this.searchBooks(query, { limit: limit });
            if (result.success && result.data) {
                return result.data.map(book => ({
                    text: book.title,
                    type: 'title',
                    book: book
                })).slice(0, limit);
            }
            return [];
        } catch (error) {
            console.error('Suggestions API error:', error);
            return [];
        }
    }

    /**
     * Health check for the API
     */
    async healthCheck() {
        try {
            // Try to access the books endpoint as a health check
            const response = await fetch(`${API_BASE_URL}/api/books/?limit=1`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                signal: AbortSignal.timeout(5000)
            });

            return response.ok;
        } catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    }

    /**
     * Clear the cache
     */
    clearCache() {
        this.cache.clear();
    }

    /**
     * Generate cache key
     */
    _getCacheKey(type, ...params) {
        return `${type}:${params.join(':')}`;
    }

    /**
     * Get cache statistics
     */
    getCacheStats() {
        return {
            size: this.cache.size,
            entries: Array.from(this.cache.keys())
        };
    }
}

// Create singleton instance
const searchService = new SearchService();

export { searchService };