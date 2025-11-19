/**
 * Main search interface logic and state management
 */

import { debounceSearch } from './utils/debounce.js';
import { parseSearchQuery, calculateRelevanceScore, applyFilters, sortBooks } from './utils/search-utils.js';
import { searchService } from './services/search-service.js';
import { filterService } from './services/filter-service.js';
import { exportService } from './services/export-service.js';
import SearchSuggestions from './components/search-suggestions.js';
import SearchFilters from './components/search-filters.js';
import SearchResults from './components/search-results.js';
import BookDetail from './components/book-detail.js';

class MAMSearch {
    constructor() {
        this.container = document.querySelector('.search-main');
        this.currentQuery = '';
        this.currentResults = [];
        this.isLoading = false;
        this.searchTimeout = null;

        // Component instances
        this.suggestions = null;
        this.filters = null;
        this.results = null;
        this.bookDetail = null;

        this.init();
    }

    /**
     * Initializes the search interface
     */
    async init() {
        try {
            this.findElements();
            this.initializeComponents();
            this.setupEventListeners();
            this.loadInitialState();
            this.checkAPIHealth();

            console.log('MAM Search interface initialized');
        } catch (error) {
            console.error('Failed to initialize search interface:', error);
            this.showError('Failed to initialize search interface');
        }
    }

    /**
     * Finds DOM elements
     */
    findElements() {
        this.searchInput = document.getElementById('main-search-input');
        this.searchButton = document.getElementById('search-button');
        this.voiceSearchBtn = document.getElementById('voice-search');
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.errorMessage = document.getElementById('error-message');
        this.exportBtn = document.getElementById('export-results');
        this.savedSearchesBtn = document.getElementById('saved-searches');
        this.savedSearchesModal = document.getElementById('saved-searches-modal');
    }

    /**
     * Initializes component instances
     */
    initializeComponents() {
        // Initialize search suggestions
        const suggestionsContainer = document.getElementById('search-suggestions');
        if (this.searchInput && suggestionsContainer) {
            this.suggestions = new SearchSuggestions(this.searchInput, suggestionsContainer);
        }

        // Initialize filters
        if (this.container) {
            this.filters = new SearchFilters(this.container);
        }

        // Initialize results display
        if (this.container) {
            this.results = new SearchResults(this.container);
        }

        // Initialize book detail modal
        if (this.container) {
            this.bookDetail = new BookDetail(this.container);
        }
    }

    /**
     * Sets up event listeners
     */
    setupEventListeners() {
        // Search input events
        if (this.searchInput) {
            this.searchInput.addEventListener('input', debounceSearch((e) => this.handleSearchInput(e), 300));
            this.searchInput.addEventListener('keydown', (e) => this.handleSearchKeydown(e));
        }

        // Search button
        if (this.searchButton) {
            this.searchButton.addEventListener('click', () => this.performSearch());
        }

        // Voice search
        if (this.voiceSearchBtn) {
            this.voiceSearchBtn.addEventListener('click', () => this.startVoiceSearch());
        }

        // Export button
        if (this.exportBtn) {
            this.exportBtn.addEventListener('click', () => this.showExportOptions());
        }

        // Saved searches
        if (this.savedSearchesBtn) {
            this.savedSearchesBtn.addEventListener('click', () => this.showSavedSearches());
        }

        // Component event listeners
        this.setupComponentEventListeners();

        // URL state management
        window.addEventListener('popstate', () => this.handleURLChange());

        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }

        // Back to dashboard
        const backBtn = document.getElementById('back-to-dashboard');
        if (backBtn) {
            backBtn.addEventListener('click', () => window.location.href = 'index.html');
        }
    }

    /**
     * Sets up component event listeners
     */
    setupComponentEventListeners() {
        if (!this.container) return;

        // Filter events
        this.container.addEventListener('filters-applied', () => this.handleFiltersApplied());
        this.container.addEventListener('filters-cleared', () => this.handleFiltersCleared());
        this.container.addEventListener('search-saved', (e) => this.handleSearchSaved(e.detail));
        this.container.addEventListener('search-deleted', (e) => this.handleSearchDeleted(e.detail));

        // Results events
        this.container.addEventListener('sort-changed', (e) => this.handleSortChanged(e.detail));
        this.container.addEventListener('page-changed', (e) => this.handlePageChanged(e.detail));
        this.container.addEventListener('page-size-changed', (e) => this.handlePageSizeChanged(e.detail));

        // Book detail events
        this.container.addEventListener('book-selected', (e) => this.handleBookSelected(e.detail));
        this.container.addEventListener('book-download', (e) => this.handleBookDownload(e.detail));
        this.container.addEventListener('book-favorite-toggle', (e) => this.handleBookFavoriteToggle(e.detail));
    }

    /**
     * Loads initial state from URL and localStorage
     */
    loadInitialState() {
        const urlParams = new URLSearchParams(window.location.search);

        // Load search query from URL
        const query = urlParams.get('q');
        if (query && this.searchInput) {
            this.searchInput.value = query;
            this.currentQuery = query;
        }

        // Load filters from URL
        if (this.filters) {
            this.filters.loadSavedFilters();
            // URL params override saved filters
            this.filters.fromQueryParams(urlParams);
        }

        // Load view preferences
        if (this.results) {
            this.results.loadPreferences();
        }

        // Perform initial search if query exists
        if (this.currentQuery) {
            this.performSearch();
        }
    }

    /**
     * Checks API health on startup
     */
    async checkAPIHealth() {
        try {
            const isHealthy = await searchService.healthCheck();
            if (!isHealthy) {
                console.warn('API health check failed');
                this.showError('Unable to connect to the search service. Some features may not work properly.');
            }
        } catch (error) {
            console.warn('API health check error:', error);
        }
    }

    /**
     * Handles search input changes
     */
    handleSearchInput(event) {
        const query = event.target.value.trim();

        if (query !== this.currentQuery) {
            this.currentQuery = query;
            this.updateURL();

            if (query.length >= 2) {
                // Trigger search with debouncing
                this.debouncedSearch();
            } else if (query.length === 0) {
                // Clear results for empty query
                this.clearResults();
            }
        }
    }

    /**
     * Handles search input keydown events
     */
    handleSearchKeydown(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            this.performSearch();
        } else if (event.key === 'Escape') {
            this.searchInput.blur();
        }
    }

    /**
     * Debounced search function
     */
    debouncedSearch = debounceSearch(() => {
        if (this.currentQuery.length >= 2) {
            this.performSearch();
        }
    }, 500);

    /**
     * Performs the main search operation
     */
    async performSearch(options = {}) {
        if (this.isLoading) return;

        const query = this.currentQuery;
        if (!query || query.length < 2) {
            this.clearResults();
            return;
        }

        this.isLoading = true;
        this.showLoading();

        try {
            // Parse search query
            const parsedQuery = parseSearchQuery(query);

            // Get current filters
            const filters = this.filters ? this.filters.getFilters() : {};

            // Prepare search options
            const searchOptions = {
                ...options,
                ...filters,
                limit: this.results ? this.results.pageSize : 24,
                offset: options.offset || 0
            };

            // Perform search
            const response = await searchService.searchBooks(query, searchOptions);

            if (response.success && response.data) {
                // Calculate relevance scores
                const booksWithScores = response.data.map(book => ({
                    ...book,
                    relevance_score: calculateRelevanceScore(book, parsedQuery.terms)
                }));

                // Apply client-side filtering if needed
                const filteredBooks = applyFilters(booksWithScores, filters);

                // Sort results
                const sortedBooks = sortBooks(filteredBooks,
                    this.results ? this.results.sortBy : 'relevance',
                    this.results ? this.results.sortDirection : 'desc'
                );

                // Update results
                this.currentResults = sortedBooks;
                this.results.setResults(sortedBooks, response.total || sortedBooks.length);

                // Update export button
                this.updateExportButton(sortedBooks.length > 0);

                // Update URL
                this.updateURL();

            } else {
                throw new Error(response.error || 'Search failed');
            }

        } catch (error) {
            console.error('Search failed:', error);
            this.showError(`Search failed: ${error.message}`);
            this.clearResults();
        } finally {
            this.isLoading = false;
            this.hideLoading();
        }
    }

    /**
     * Handles filter application
     */
    handleFiltersApplied() {
        if (this.currentQuery) {
            this.performSearch();
        }
    }

    /**
     * Handles filter clearing
     */
    handleFiltersCleared() {
        this.clearResults();
        this.updateURL();
    }

    /**
     * Handles sort changes
     */
    handleSortChanged(detail) {
        if (this.currentResults.length > 0) {
            const sortedBooks = sortBooks(this.currentResults, detail.sortBy, detail.direction);
            this.currentResults = sortedBooks;
            this.results.setResults(sortedBooks);
        }
    }

    /**
     * Handles page changes
     */
    handlePageChanged(detail) {
        // Page changes are handled by the results component
        // We may need to fetch more data if paginating beyond cached results
    }

    /**
     * Handles page size changes
     */
    handlePageSizeChanged(detail) {
        if (this.currentQuery) {
            this.performSearch();
        }
    }

    /**
     * Handles book selection
     */
    handleBookSelected(detail) {
        // Book detail modal is handled by the BookDetail component
    }

    /**
     * Handles book downloads
     */
    handleBookDownload(detail) {
        console.log('Download requested for:', detail.book.title);
        // Integrate with download system here
    }

    /**
     * Handles favorite toggles
     */
    handleBookFavoriteToggle(detail) {
        console.log('Favorite toggled for:', detail.book.title);
        // Integrate with favorites system here
    }

    /**
     * Handles saved search events
     */
    handleSearchSaved(detail) {
        this.showNotification(`Search "${detail.savedSearch.name}" saved successfully!`);
    }

    /**
     * Handles search deletion events
     */
    handleSearchDeleted(detail) {
        this.showNotification('Saved search deleted');
    }

    /**
     * Starts voice search
     */
    startVoiceSearch() {
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            this.showError('Voice search is not supported in this browser');
            return;
        }

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();

        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            this.voiceSearchBtn.classList.add('listening');
            this.showNotification('Listening... Speak your search query');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            if (this.searchInput) {
                this.searchInput.value = transcript;
                this.currentQuery = transcript;
                this.performSearch();
            }
        };

        recognition.onerror = (event) => {
            console.error('Voice search error:', event.error);
            this.showError('Voice search failed. Please try again.');
        };

        recognition.onend = () => {
            this.voiceSearchBtn.classList.remove('listening');
        };

        recognition.start();
    }

    /**
     * Shows export options
     */
    showExportOptions() {
        if (this.currentResults.length === 0) {
            this.showNotification('No results to export');
            return;
        }

        const format = prompt('Choose export format (csv, json, txt):', 'csv');
        if (!format || !['csv', 'json', 'txt'].includes(format.toLowerCase())) {
            return;
        }

        try {
            exportService.exportBooks(this.currentResults, format.toLowerCase());
            this.showNotification(`Exporting ${this.currentResults.length} books as ${format.toUpperCase()}`);
        } catch (error) {
            console.error('Export failed:', error);
            this.showError('Export failed: ' + error.message);
        }
    }

    /**
     * Shows saved searches modal
     */
    showSavedSearches() {
        if (!this.savedSearchesModal) return;

        const savedSearches = this.filters ? this.filters.getSavedSearches() : [];
        const modalBody = this.savedSearchesModal.querySelector('.modal-body');

        if (savedSearches.length === 0) {
            modalBody.innerHTML = '<p>No saved searches yet. Save a search to access it quickly later.</p>';
        } else {
            const searchesList = document.createElement('div');
            searchesList.className = 'saved-searches-list';

            savedSearches.forEach(search => {
                const searchItem = document.createElement('div');
                searchItem.className = 'saved-search-item';

                const name = document.createElement('div');
                name.className = 'saved-search-name';
                name.textContent = search.name;

                const query = document.createElement('div');
                query.className = 'saved-search-query';
                query.textContent = search.filters.author || search.filters.series || 'Complex search';

                const meta = document.createElement('div');
                meta.className = 'saved-search-meta';
                meta.innerHTML = `
                    <span>${new Date(search.created).toLocaleDateString()}</span>
                    <span>${this.filters.getActiveFilterCount(search.filters)} filters</span>
                `;

                const actions = document.createElement('div');
                actions.className = 'saved-search-actions';

                const loadBtn = document.createElement('button');
                loadBtn.className = 'btn-secondary';
                loadBtn.textContent = 'Load';
                loadBtn.addEventListener('click', () => {
                    this.filters.loadSavedSearch(search);
                    this.savedSearchesModal.classList.add('hidden');
                });

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn-secondary';
                deleteBtn.textContent = 'Delete';
                deleteBtn.addEventListener('click', () => {
                    if (confirm(`Delete saved search "${search.name}"?`)) {
                        this.filters.deleteSavedSearch(search.id);
                        searchItem.remove();
                    }
                });

                actions.appendChild(loadBtn);
                actions.appendChild(deleteBtn);

                searchItem.appendChild(name);
                searchItem.appendChild(query);
                searchItem.appendChild(meta);
                searchItem.appendChild(actions);

                searchesList.appendChild(searchItem);
            });

            modalBody.innerHTML = '';
            modalBody.appendChild(searchesList);
        }

        this.savedSearchesModal.classList.remove('hidden');
    }

    /**
     * Toggles theme
     */
    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('mam_theme', newTheme);

        const themeIcon = document.querySelector('.theme-icon');
        if (themeIcon) {
            themeIcon.textContent = newTheme === 'dark' ? '☀️' : '🌙';
        }
    }

    /**
     * Updates URL with current search state
     */
    updateURL() {
        const params = new URLSearchParams();

        if (this.currentQuery) {
            params.set('q', this.currentQuery);
        }

        // Add filter params
        if (this.filters) {
            const filterParams = this.filters.getFilters();
            Object.entries(filterParams).forEach(([key, value]) => {
                if (value && value !== '' && value !== null) {
                    if (Array.isArray(value)) {
                        params.set(key, value.join(','));
                    } else {
                        params.set(key, value);
                    }
                }
            });
        }

        const newURL = `${window.location.pathname}${params.toString() ? '?' + params.toString() : ''}`;
        window.history.replaceState(null, '', newURL);
    }

    /**
     * Handles URL changes (browser back/forward)
     */
    handleURLChange() {
        const urlParams = new URLSearchParams(window.location.search);
        const query = urlParams.get('q') || '';

        if (query !== this.currentQuery) {
            this.currentQuery = query;
            if (this.searchInput) {
                this.searchInput.value = query;
            }

            if (this.filters) {
                this.filters.fromQueryParams(urlParams);
            }

            if (query) {
                this.performSearch();
            } else {
                this.clearResults();
            }
        }
    }

    /**
     * Clears search results
     */
    clearResults() {
        this.currentResults = [];
        if (this.results) {
            this.results.setResults([]);
        }
        this.updateExportButton(false);
    }

    /**
     * Updates export button state
     */
    updateExportButton(enabled) {
        if (this.exportBtn) {
            this.exportBtn.disabled = !enabled;
        }
    }

    /**
     * Shows loading overlay
     */
    showLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.classList.remove('hidden');
        }
    }

    /**
     * Hides loading overlay
     */
    hideLoading() {
        if (this.loadingOverlay) {
            this.loadingOverlay.classList.add('hidden');
        }
    }

    /**
     * Shows error message
     */
    showError(message) {
        if (this.errorMessage) {
            const errorText = this.errorMessage.querySelector('#error-text');
            if (errorText) {
                errorText.textContent = message;
            }
            this.errorMessage.classList.remove('hidden');

            // Auto-hide after 5 seconds
            setTimeout(() => {
                this.hideError();
            }, 5000);
        }
    }

    /**
     * Hides error message
     */
    hideError() {
        if (this.errorMessage) {
            this.errorMessage.classList.add('hidden');
        }
    }

    /**
     * Shows a notification
     */
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
            <span class="notification-text">${message}</span>
        `;

        // Add to container
        if (this.container) {
            this.container.appendChild(notification);

            // Auto-remove after 3 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 3000);
        }
    }

    /**
     * Gets current search state
     */
    getState() {
        return {
            query: this.currentQuery,
            results: this.currentResults,
            filters: this.filters ? this.filters.getFilters() : {},
            resultsState: this.results ? this.results.getState() : {},
            isLoading: this.isLoading
        };
    }

    /**
     * Destroys the search interface
     */
    destroy() {
        // Clear timeouts
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        // Destroy components
        if (this.suggestions) {
            this.suggestions.destroy();
        }
        if (this.filters) {
            this.filters.destroy();
        }
        if (this.results) {
            this.results.destroy();
        }
        if (this.bookDetail) {
            this.bookDetail.destroy();
        }

        // Clear cache
        searchService.clearCache();
    }
}

// Initialize search interface when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mamSearch = new MAMSearch();
});

// Export for potential external use
export default MAMSearch;