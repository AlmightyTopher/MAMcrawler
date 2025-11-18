/**
 * Audiobooks API Module
 * Handles all audiobook-related API communications
 */

class AudiobooksAPI {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.currentPage = 1;
        this.pageSize = 50;
        this.currentFilters = {};
        this.currentSearch = '';
        this.currentSort = 'title';
    }

    /**
     * Get paginated list of books with optional filtering
     */
    async getBooks(page = 1, filters = {}, search = '', sort = 'title') {
        try {
            let url = `/books/?limit=${this.pageSize}&offset=${(page - 1) * this.pageSize}`;

            if (filters.status && filters.status !== '') {
                url += `&status=${filters.status}`;
            }

            if (search && search.trim()) {
                url += `&search=${encodeURIComponent(search.trim())}`;
            }

            const response = await this.dashboard.apiRequest(url);
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'audiobooks');
            throw error;
        }
    }

    /**
     * Get detailed information about a specific book
     */
    async getBook(bookId) {
        try {
            const response = await this.dashboard.apiRequest(`/books/${bookId}`);
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'book details');
            throw error;
        }
    }

    /**
     * Search books by query
     */
    async searchBooks(query, limit = 20) {
        try {
            const response = await this.dashboard.apiRequest(`/books/search?q=${encodeURIComponent(query)}&limit=${limit}`);
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'book search');
            throw error;
        }
    }

    /**
     * Get books in a specific series
     */
    async getBooksBySeries(seriesName) {
        try {
            const response = await this.dashboard.apiRequest(`/books/series/${encodeURIComponent(seriesName)}`);
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'series books');
            throw error;
        }
    }

    /**
     * Get books with incomplete metadata
     */
    async getIncompleteBooks(threshold = 80, limit = 100) {
        try {
            const response = await this.dashboard.apiRequest(`/books/incomplete-metadata?threshold=${threshold}&limit=${limit}`);
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'incomplete books');
            throw error;
        }
    }

    /**
     * Update book metadata
     */
    async updateBook(bookId, updates) {
        try {
            const response = await this.dashboard.apiRequest(`/books/${bookId}`, {
                method: 'PUT',
                body: JSON.stringify(updates)
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'book update');
            throw error;
        }
    }

    /**
     * Delete a book (soft delete)
     */
    async deleteBook(bookId) {
        try {
            const response = await this.dashboard.apiRequest(`/books/${bookId}`, {
                method: 'DELETE'
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'book deletion');
            throw error;
        }
    }

    /**
     * Get metadata correction history for a book
     */
    async getMetadataHistory(bookId) {
        try {
            const response = await this.dashboard.apiRequest(`/books/${bookId}/metadata-history`);
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'metadata history');
            throw error;
        }
    }

    /**
     * Update metadata source tracking
     */
    async updateMetadataSource(bookId, fieldName, source) {
        try {
            const response = await this.dashboard.apiRequest(`/books/${bookId}/metadata-source`, {
                method: 'PUT',
                body: JSON.stringify({
                    field_name: fieldName,
                    source: source
                })
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'metadata source update');
            throw error;
        }
    }

    /**
     * Create a new book
     */
    async createBook(bookData) {
        try {
            const response = await this.dashboard.apiRequest('/books/', {
                method: 'POST',
                body: JSON.stringify(bookData)
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'book creation');
            throw error;
        }
    }

    /**
     * Load library data for the dashboard
     */
    async loadLibraryData() {
        try {
            const data = await this.getBooks(
                this.currentPage,
                this.currentFilters,
                this.currentSearch,
                this.currentSort
            );

            this.renderBookGrid(data.books);
            this.updatePagination(data.page_info, data.total);

            return data;
        } catch (error) {
            console.error('Failed to load library data:', error);
            this.renderEmptyState('Failed to load library. Please try again.');
        }
    }

    /**
     * Perform search
     */
    async performSearch(query) {
        this.currentSearch = query;
        this.currentPage = 1;
        await this.loadLibraryData();
    }

    /**
     * Apply filters
     */
    async applyFilters() {
        const statusFilter = document.getElementById('status-filter')?.value || '';
        const genreFilter = document.getElementById('genre-filter')?.value || '';

        this.currentFilters = {
            status: statusFilter,
            genre: genreFilter
        };
        this.currentPage = 1;
        await this.loadLibraryData();
    }

    /**
     * Clear all filters
     */
    async clearFilters() {
        document.getElementById('status-filter').value = '';
        document.getElementById('genre-filter').value = '';
        document.getElementById('library-search').value = '';

        this.currentFilters = {};
        this.currentSearch = '';
        this.currentPage = 1;
        await this.loadLibraryData();
    }

    /**
     * Apply sorting
     */
    async applySorting() {
        const sortSelect = document.getElementById('library-sort');
        this.currentSort = sortSelect.value;
        this.currentPage = 1;
        await this.loadLibraryData();
    }

    /**
     * Change page
     */
    async changePage(direction) {
        this.currentPage += direction;
        if (this.currentPage < 1) this.currentPage = 1;
        await this.loadLibraryData();
    }

    /**
     * Render book grid
     */
    renderBookGrid(books) {
        const container = document.getElementById('library-content');

        if (!books || books.length === 0) {
            this.renderEmptyState('No books found matching your criteria.');
            return;
        }

        const bookGrid = document.createElement('div');
        bookGrid.className = 'book-grid';

        books.forEach(book => {
            const bookCard = this.createBookCard(book);
            bookGrid.appendChild(bookCard);
        });

        container.innerHTML = '';
        container.appendChild(bookGrid);
    }

    /**
     * Create a book card element
     */
    createBookCard(book) {
        const card = document.createElement('div');
        card.className = 'book-card';
        card.dataset.bookId = book.id;

        // Get first letter of title for cover placeholder
        const coverLetter = book.title.charAt(0).toUpperCase();

        card.innerHTML = `
            <div class="book-cover">
                <span>${coverLetter}</span>
            </div>
            <div class="book-info">
                <h3 class="book-title">${this.escapeHtml(book.title)}</h3>
                <p class="book-author">${this.escapeHtml(book.author || 'Unknown Author')}</p>
                <div class="book-meta">
                    <span class="book-series">${this.escapeHtml(book.series || '')}</span>
                    <span class="book-status ${book.status}">${book.status}</span>
                </div>
            </div>
        `;

        // Add click handler for book details
        card.addEventListener('click', () => {
            this.showBookDetails(book.id);
        });

        return card;
    }

    /**
     * Show book details modal/popup
     */
    async showBookDetails(bookId) {
        try {
            const bookData = await this.getBook(bookId);
            // TODO: Implement modal/popup for book details
            console.log('Book details:', bookData);
        } catch (error) {
            console.error('Failed to load book details:', error);
        }
    }

    /**
     * Update pagination controls
     */
    updatePagination(pageInfo, total) {
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const pageInfoEl = document.getElementById('page-info');

        const totalPages = Math.ceil(total / this.pageSize);
        const hasNext = this.currentPage < totalPages;
        const hasPrev = this.currentPage > 1;

        prevBtn.disabled = !hasPrev;
        nextBtn.disabled = !hasNext;

        pageInfoEl.textContent = `Page ${this.currentPage} of ${totalPages}`;
    }

    /**
     * Render empty state
     */
    renderEmptyState(message) {
        const container = document.getElementById('library-content');
        container.innerHTML = `
            <div class="empty-state">
                <p>${message}</p>
            </div>
        `;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudiobooksAPI;
}