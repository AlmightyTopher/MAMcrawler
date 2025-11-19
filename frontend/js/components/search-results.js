/**
 * Search results component for displaying books and pagination
 */

import { formatDuration, truncateText, generateExcerpt } from '../utils/search-utils.js';

class SearchResults {
    constructor(container) {
        this.container = container;
        this.resultsContainer = null;
        this.paginationContainer = null;
        this.noResultsContainer = null;

        this.currentResults = [];
        this.currentPage = 1;
        this.totalPages = 1;
        this.pageSize = 24;
        this.totalResults = 0;
        this.viewMode = 'grid'; // 'grid' or 'list'
        this.sortBy = 'relevance';
        this.sortDirection = 'desc';

        this.init();
    }

    /**
     * Initializes the results component
     */
    init() {
        this.findElements();
        this.setupEventListeners();
    }

    /**
     * Finds DOM elements
     */
    findElements() {
        this.resultsContainer = this.container.querySelector('#search-results');
        this.paginationContainer = this.container.querySelector('.pagination-section');
        this.noResultsContainer = this.container.querySelector('#no-results');

        // View controls
        this.gridViewBtn = this.container.querySelector('#grid-view');
        this.listViewBtn = this.container.querySelector('#list-view');

        // Sort controls
        this.sortSelect = this.container.querySelector('#sort-select');
        this.sortDirectionBtn = this.container.querySelector('#sort-direction');

        // Page size control
        this.pageSizeSelect = this.container.querySelector('#page-size');

        // Pagination buttons
        this.firstPageBtn = this.container.querySelector('#first-page');
        this.prevPageBtn = this.container.querySelector('#prev-page');
        this.nextPageBtn = this.container.querySelector('#next-page');
        this.lastPageBtn = this.container.querySelector('#last-page');
        this.pageNumbersContainer = this.container.querySelector('#page-numbers');
    }

    /**
     * Sets up event listeners
     */
    setupEventListeners() {
        // View toggle
        if (this.gridViewBtn) {
            this.gridViewBtn.addEventListener('click', () => this.setViewMode('grid'));
        }
        if (this.listViewBtn) {
            this.listViewBtn.addEventListener('click', () => this.setViewMode('list'));
        }

        // Sort controls
        if (this.sortSelect) {
            this.sortSelect.addEventListener('change', (e) => this.setSortBy(e.target.value));
        }
        if (this.sortDirectionBtn) {
            this.sortDirectionBtn.addEventListener('click', () => this.toggleSortDirection());
        }

        // Page size
        if (this.pageSizeSelect) {
            this.pageSizeSelect.addEventListener('change', (e) => this.setPageSize(parseInt(e.target.value)));
        }

        // Pagination
        if (this.firstPageBtn) {
            this.firstPageBtn.addEventListener('click', () => this.goToPage(1));
        }
        if (this.prevPageBtn) {
            this.prevPageBtn.addEventListener('click', () => this.goToPage(this.currentPage - 1));
        }
        if (this.nextPageBtn) {
            this.nextPageBtn.addEventListener('click', () => this.goToPage(this.currentPage + 1));
        }
        if (this.lastPageBtn) {
            this.lastPageBtn.addEventListener('click', () => this.goToPage(this.totalPages));
        }
    }

    /**
     * Sets the view mode (grid or list)
     */
    setViewMode(mode) {
        if (mode !== 'grid' && mode !== 'list') return;

        this.viewMode = mode;

        // Update button states
        if (this.gridViewBtn) {
            this.gridViewBtn.classList.toggle('active', mode === 'grid');
        }
        if (this.listViewBtn) {
            this.listViewBtn.classList.toggle('active', mode === 'list');
        }

        // Re-render results
        this.renderResults();

        // Save preference
        localStorage.setItem('mam_search_view_mode', mode);
    }

    /**
     * Sets the sort field
     */
    setSortBy(sortBy) {
        this.sortBy = sortBy;
        this.sortAndRender();

        // Trigger sort change event
        this.container.dispatchEvent(new CustomEvent('sort-changed', {
            detail: { sortBy: this.sortBy, direction: this.sortDirection }
        }));
    }

    /**
     * Toggles sort direction
     */
    toggleSortDirection() {
        this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        this.updateSortDirectionButton();
        this.sortAndRender();

        // Trigger sort change event
        this.container.dispatchEvent(new CustomEvent('sort-changed', {
            detail: { sortBy: this.sortBy, direction: this.sortDirection }
        }));
    }

    /**
     * Updates the sort direction button appearance
     */
    updateSortDirectionButton() {
        if (this.sortDirectionBtn) {
            const icon = this.sortDirectionBtn.querySelector('.sort-icon');
            if (icon) {
                icon.textContent = this.sortDirection === 'asc' ? '↑' : '↓';
            }
            this.sortDirectionBtn.setAttribute('data-direction', this.sortDirection);
        }
    }

    /**
     * Sets the page size
     */
    setPageSize(pageSize) {
        this.pageSize = pageSize;
        this.currentPage = 1; // Reset to first page
        this.renderResults();

        // Save preference
        localStorage.setItem('mam_search_page_size', pageSize);

        // Trigger page size change event
        this.container.dispatchEvent(new CustomEvent('page-size-changed', {
            detail: { pageSize }
        }));
    }

    /**
     * Goes to a specific page
     */
    goToPage(page) {
        if (page < 1 || page > this.totalPages) return;

        this.currentPage = page;
        this.renderResults();

        // Trigger page change event
        this.container.dispatchEvent(new CustomEvent('page-changed', {
            detail: { page: this.currentPage, pageSize: this.pageSize }
        }));
    }

    /**
     * Sets search results data
     */
    setResults(results, totalCount = null) {
        this.currentResults = results || [];
        this.totalResults = totalCount !== null ? totalCount : this.currentResults.length;
        this.totalPages = Math.ceil(this.totalResults / this.pageSize);
        this.currentPage = Math.min(this.currentPage, this.totalPages) || 1;

        this.renderResults();
        this.updatePagination();
    }

    /**
     * Sorts results and re-renders
     */
    sortAndRender() {
        // Sorting is handled by the parent component
        // Just trigger the event
        this.container.dispatchEvent(new CustomEvent('sort-changed', {
            detail: { sortBy: this.sortBy, direction: this.sortDirection }
        }));
    }

    /**
     * Renders the search results
     */
    renderResults() {
        if (!this.resultsContainer) return;

        // Clear previous results
        this.resultsContainer.innerHTML = '';

        if (this.currentResults.length === 0) {
            this.showNoResults();
            return;
        }

        this.hideNoResults();

        // Create appropriate container
        const containerClass = this.viewMode === 'grid' ? 'results-grid' : 'results-list';
        const container = document.createElement('div');
        container.className = containerClass;

        // Calculate which results to show for current page
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = Math.min(startIndex + this.pageSize, this.currentResults.length);
        const pageResults = this.currentResults.slice(startIndex, endIndex);

        // Render each result
        pageResults.forEach(book => {
            const bookElement = this.viewMode === 'grid'
                ? this.createGridBookCard(book)
                : this.createListBookItem(book);
            container.appendChild(bookElement);
        });

        this.resultsContainer.appendChild(container);
    }

    /**
     * Creates a grid view book card
     */
    createGridBookCard(book) {
        const card = document.createElement('div');
        card.className = 'book-card';
        card.setAttribute('data-book-id', book.id);
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');
        card.setAttribute('aria-label', `View details for ${book.title}`);

        // Cover image
        const cover = document.createElement('div');
        cover.className = 'book-cover';

        if (book.cover_url) {
            const img = document.createElement('img');
            img.src = book.cover_url;
            img.alt = `Cover for ${book.title}`;
            img.loading = 'lazy';
            cover.appendChild(img);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'book-cover-placeholder';
            placeholder.textContent = '📖';
            cover.appendChild(placeholder);
        }

        // Book info
        const info = document.createElement('div');
        info.className = 'book-info';

        const title = document.createElement('h3');
        title.className = 'book-title';
        title.textContent = book.title || 'Unknown Title';
        info.appendChild(title);

        if (book.author) {
            const author = document.createElement('div');
            author.className = 'book-author';
            author.textContent = book.author;
            info.appendChild(author);
        }

        if (book.series) {
            const series = document.createElement('div');
            series.className = 'book-series';
            series.textContent = book.series;
            if (book.series_number) {
                series.textContent += ` #${book.series_number}`;
            }
            info.appendChild(series);
        }

        const meta = document.createElement('div');
        meta.className = 'book-meta';

        const rating = document.createElement('div');
        rating.className = 'book-rating';
        // Add rating display logic here if available
        rating.innerHTML = '<span class="rating-stars">★★★★☆</span>';
        meta.appendChild(rating);

        const duration = document.createElement('div');
        duration.className = 'book-duration';
        duration.textContent = formatDuration(book.duration_minutes);
        meta.appendChild(duration);

        info.appendChild(meta);

        card.appendChild(cover);
        card.appendChild(info);

        // Click handler
        card.addEventListener('click', () => this.showBookDetails(book));
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.showBookDetails(book);
            }
        });

        return card;
    }

    /**
     * Creates a list view book item
     */
    createListBookItem(book) {
        const item = document.createElement('div');
        item.className = 'list-item';
        item.setAttribute('data-book-id', book.id);
        item.setAttribute('tabindex', '0');
        item.setAttribute('role', 'button');

        // Cover
        const cover = document.createElement('div');
        cover.className = 'list-cover';

        if (book.cover_url) {
            const img = document.createElement('img');
            img.src = book.cover_url;
            img.alt = `Cover for ${book.title}`;
            img.loading = 'lazy';
            cover.appendChild(img);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'book-cover-placeholder';
            placeholder.textContent = '📖';
            cover.appendChild(placeholder);
        }

        // Title
        const title = document.createElement('div');
        title.className = 'list-title';
        title.textContent = book.title || 'Unknown Title';

        // Author
        const author = document.createElement('div');
        author.className = 'list-author';
        author.textContent = book.author || '';

        // Series
        const series = document.createElement('div');
        series.className = 'list-series';
        if (book.series) {
            series.textContent = book.series;
            if (book.series_number) {
                series.textContent += ` #${book.series_number}`;
            }
        }

        // Rating (placeholder)
        const rating = document.createElement('div');
        rating.className = 'list-rating';
        rating.innerHTML = '<span class="rating-stars">★★★★☆</span>';

        // Duration
        const duration = document.createElement('div');
        duration.className = 'list-duration';
        duration.textContent = formatDuration(book.duration_minutes);

        // Actions
        const actions = document.createElement('div');
        actions.className = 'list-actions';
        // Add action buttons here if needed

        item.appendChild(cover);
        item.appendChild(title);
        item.appendChild(author);
        item.appendChild(series);
        item.appendChild(rating);
        item.appendChild(duration);
        item.appendChild(actions);

        // Click handler
        item.addEventListener('click', () => this.showBookDetails(book));
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.showBookDetails(book);
            }
        });

        return item;
    }

    /**
     * Shows book details modal
     */
    showBookDetails(book) {
        this.container.dispatchEvent(new CustomEvent('book-selected', {
            detail: { book }
        }));
    }

    /**
     * Updates pagination controls
     */
    updatePagination() {
        if (!this.paginationContainer) return;

        const paginationControls = this.paginationContainer.querySelector('.pagination-controls');
        const paginationInfo = this.paginationContainer.querySelector('#pagination-info');

        if (this.totalResults === 0) {
            paginationControls.style.display = 'none';
            if (paginationInfo) paginationInfo.textContent = 'No results';
            return;
        }

        paginationControls.style.display = 'flex';

        // Update button states
        if (this.firstPageBtn) {
            this.firstPageBtn.disabled = this.currentPage === 1;
        }
        if (this.prevPageBtn) {
            this.prevPageBtn.disabled = this.currentPage === 1;
        }
        if (this.nextPageBtn) {
            this.nextPageBtn.disabled = this.currentPage === this.totalPages;
        }
        if (this.lastPageBtn) {
            this.lastPageBtn.disabled = this.currentPage === this.totalPages;
        }

        // Update page numbers
        this.renderPageNumbers();

        // Update info
        if (paginationInfo) {
            const start = (this.currentPage - 1) * this.pageSize + 1;
            const end = Math.min(this.currentPage * this.pageSize, this.totalResults);
            paginationInfo.textContent = `Page ${this.currentPage} of ${this.totalPages} (${this.totalResults} results)`;
        }
    }

    /**
     * Renders page number buttons
     */
    renderPageNumbers() {
        if (!this.pageNumbersContainer) return;

        this.pageNumbersContainer.innerHTML = '';

        const maxVisiblePages = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(this.totalPages, startPage + maxVisiblePages - 1);

        // Adjust start page if we're near the end
        if (endPage - startPage + 1 < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.className = `page-number ${i === this.currentPage ? 'active' : ''}`;
            pageBtn.textContent = i;
            pageBtn.addEventListener('click', () => this.goToPage(i));
            this.pageNumbersContainer.appendChild(pageBtn);
        }
    }

    /**
     * Shows no results message
     */
    showNoResults() {
        if (this.noResultsContainer) {
            this.noResultsContainer.classList.remove('hidden');
        }
        if (this.resultsContainer) {
            this.resultsContainer.innerHTML = '';
        }
        if (this.paginationContainer) {
            this.paginationContainer.style.display = 'none';
        }
    }

    /**
     * Hides no results message
     */
    hideNoResults() {
        if (this.noResultsContainer) {
            this.noResultsContainer.classList.add('hidden');
        }
        if (this.paginationContainer) {
            this.paginationContainer.style.display = 'flex';
        }
    }

    /**
     * Loads user preferences from localStorage
     */
    loadPreferences() {
        const savedViewMode = localStorage.getItem('mam_search_view_mode');
        if (savedViewMode === 'list') {
            this.setViewMode('list');
        }

        const savedPageSize = localStorage.getItem('mam_search_page_size');
        if (savedPageSize) {
            this.setPageSize(parseInt(savedPageSize));
        }
    }

    /**
     * Gets current view state
     */
    getState() {
        return {
            viewMode: this.viewMode,
            sortBy: this.sortBy,
            sortDirection: this.sortDirection,
            pageSize: this.pageSize,
            currentPage: this.currentPage,
            totalResults: this.totalResults,
            totalPages: this.totalPages
        };
    }

    /**
     * Resets the component
     */
    reset() {
        this.currentResults = [];
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalResults = 0;
        this.renderResults();
        this.updatePagination();
    }

    /**
     * Destroys the component
     */
    destroy() {
        // Remove event listeners if needed
    }
}

export default SearchResults;