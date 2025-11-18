/**
 * Library View Component
 * Handles library display, search, filtering, and book management
 */

class LibraryView {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.audiobooksAPI = new AudiobooksAPI(dashboard);
        this.currentView = 'grid'; // 'grid' or 'list'
        this.selectedBooks = new Set();
    }

    /**
     * Initialize the library view
     */
    init() {
        // Set up the API instance on the dashboard
        this.dashboard.audiobooksAPI = this.audiobooksAPI;

        // Bind methods to dashboard
        this.dashboard.loadLibraryData = this.loadLibraryData.bind(this);
        this.dashboard.performSearch = this.audiobooksAPI.performSearch.bind(this.audiobooksAPI);
        this.dashboard.applyFilters = this.audiobooksAPI.applyFilters.bind(this.audiobooksAPI);
        this.dashboard.clearFilters = this.audiobooksAPI.clearFilters.bind(this.audiobooksAPI);
        this.dashboard.applySorting = this.audiobooksAPI.applySorting.bind(this.audiobooksAPI);
        this.dashboard.changePage = this.audiobooksAPI.changePage.bind(this.audiobooksAPI);
    }

    /**
     * Load library data
     */
    async loadLibraryData() {
        await this.audiobooksAPI.loadLibraryData();
        this.updateViewToggle();
        this.updateBulkActions();
    }

    /**
     * Update view toggle buttons
     */
    updateViewToggle() {
        // Could add grid/list view toggle here
        const container = document.getElementById('library-content');
        if (container) {
            // Add view toggle buttons if they don't exist
            if (!document.getElementById('view-toggle')) {
                const toggleContainer = document.createElement('div');
                toggleContainer.id = 'view-toggle';
                toggleContainer.className = 'view-toggle';
                toggleContainer.innerHTML = `
                    <button class="view-btn active" data-view="grid">
                        <span class="view-icon">⊞</span>
                        Grid
                    </button>
                    <button class="view-btn" data-view="list">
                        <span class="view-icon">☰</span>
                        List
                    </button>
                `;

                // Insert before the book grid
                const bookGrid = container.querySelector('.book-grid');
                if (bookGrid) {
                    container.insertBefore(toggleContainer, bookGrid);

                    // Add event listeners
                    toggleContainer.addEventListener('click', (e) => {
                        if (e.target.closest('.view-btn')) {
                            const view = e.target.closest('.view-btn').dataset.view;
                            this.switchView(view);
                        }
                    });
                }
            }
        }
    }

    /**
     * Switch between grid and list views
     */
    switchView(view) {
        this.currentView = view;

        // Update toggle buttons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-view="${view}"]`).classList.add('active');

        // Re-render current data with new view
        this.refreshCurrentView();
    }

    /**
     * Refresh the current view
     */
    async refreshCurrentView() {
        await this.loadLibraryData();
    }

    /**
     * Update bulk actions visibility
     */
    updateBulkActions() {
        const selectedCount = this.selectedBooks.size;

        // Show/hide bulk actions based on selection
        let bulkActions = document.getElementById('bulk-actions');
        if (selectedCount > 0) {
            if (!bulkActions) {
                bulkActions = this.createBulkActions();
                const container = document.getElementById('library-content');
                const bookGrid = container.querySelector('.book-grid');
                if (bookGrid) {
                    container.insertBefore(bulkActions, bookGrid);
                }
            }
            bulkActions.style.display = 'block';
            bulkActions.querySelector('.selected-count').textContent = selectedCount;
        } else if (bulkActions) {
            bulkActions.style.display = 'none';
        }
    }

    /**
     * Create bulk actions bar
     */
    createBulkActions() {
        const bulkActions = document.createElement('div');
        bulkActions.id = 'bulk-actions';
        bulkActions.className = 'bulk-actions';
        bulkActions.innerHTML = `
            <div class="bulk-info">
                <span class="selected-count">0</span> books selected
            </div>
            <div class="bulk-buttons">
                <button class="btn btn-secondary" onclick="clearSelection()">
                    <span class="btn-icon">✕</span>
                    Clear
                </button>
                <button class="btn btn-primary" onclick="bulkDownload()">
                    <span class="btn-icon">⬇️</span>
                    Download Selected
                </button>
                <button class="btn btn-warning" onclick="bulkArchive()">
                    <span class="btn-icon">📦</span>
                    Archive Selected
                </button>
                <button class="btn btn-danger" onclick="bulkDelete()">
                    <span class="btn-icon">🗑️</span>
                    Delete Selected
                </button>
            </div>
        `;

        return bulkActions;
    }

    /**
     * Toggle book selection
     */
    toggleBookSelection(bookId) {
        if (this.selectedBooks.has(bookId)) {
            this.selectedBooks.delete(bookId);
        } else {
            this.selectedBooks.add(bookId);
        }
        this.updateBulkActions();
        this.updateBookSelectionUI();
    }

    /**
     * Clear all selections
     */
    clearSelection() {
        this.selectedBooks.clear();
        this.updateBulkActions();
        this.updateBookSelectionUI();
    }

    /**
     * Update book selection UI
     */
    updateBookSelectionUI() {
        document.querySelectorAll('.book-card').forEach(card => {
            const bookId = parseInt(card.dataset.bookId);
            if (this.selectedBooks.has(bookId)) {
                card.classList.add('selected');
            } else {
                card.classList.remove('selected');
            }
        });
    }

    /**
     * Select all visible books
     */
    selectAllVisible() {
        document.querySelectorAll('.book-card').forEach(card => {
            const bookId = parseInt(card.dataset.bookId);
            this.selectedBooks.add(bookId);
        });
        this.updateBulkActions();
        this.updateBookSelectionUI();
    }

    /**
     * Bulk download selected books
     */
    async bulkDownload() {
        if (this.selectedBooks.size === 0) return;

        try {
            const bookIds = Array.from(this.selectedBooks);
            // This would need to be implemented with the downloads API
            alert(`Downloading ${bookIds.length} books...`);
            this.clearSelection();
        } catch (error) {
            console.error('Bulk download failed:', error);
            alert('Failed to start bulk download');
        }
    }

    /**
     * Bulk archive selected books
     */
    async bulkArchive() {
        if (this.selectedBooks.size === 0) return;

        if (!confirm(`Archive ${this.selectedBooks.size} selected books?`)) return;

        try {
            const bookIds = Array.from(this.selectedBooks);
            // This would need to be implemented with the books API
            alert(`Archiving ${bookIds.length} books...`);
            this.clearSelection();
            await this.loadLibraryData(); // Refresh
        } catch (error) {
            console.error('Bulk archive failed:', error);
            alert('Failed to archive books');
        }
    }

    /**
     * Bulk delete selected books
     */
    async bulkDelete() {
        if (this.selectedBooks.size === 0) return;

        if (!confirm(`Permanently delete ${this.selectedBooks.size} selected books? This cannot be undone!`)) return;

        try {
            const bookIds = Array.from(this.selectedBooks);
            // This would need to be implemented with the books API
            alert(`Deleting ${bookIds.length} books...`);
            this.clearSelection();
            await this.loadLibraryData(); // Refresh
        } catch (error) {
            console.error('Bulk delete failed:', error);
            alert('Failed to delete books');
        }
    }

    /**
     * Show book details modal
     */
    async showBookDetails(bookId) {
        try {
            const bookData = await this.audiobooksAPI.getBook(bookId);
            this.renderBookDetailsModal(bookData);
        } catch (error) {
            console.error('Failed to load book details:', error);
            alert('Failed to load book details');
        }
    }

    /**
     * Render book details modal
     */
    renderBookDetailsModal(book) {
        // Remove existing modal
        const existingModal = document.getElementById('book-details-modal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.id = 'book-details-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content book-details-modal">
                <div class="modal-header">
                    <h2>${this.escapeHtml(book.title)}</h2>
                    <button class="modal-close" onclick="closeBookDetailsModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="book-details-grid">
                        <div class="book-cover-large">
                            <span class="cover-placeholder">${book.title.charAt(0).toUpperCase()}</span>
                        </div>
                        <div class="book-info-detailed">
                            <div class="info-row">
                                <strong>Author:</strong>
                                <span>${this.escapeHtml(book.author || 'Unknown')}</span>
                            </div>
                            <div class="info-row">
                                <strong>Series:</strong>
                                <span>${this.escapeHtml(book.series || 'Standalone')}</span>
                            </div>
                            <div class="info-row">
                                <strong>Published:</strong>
                                <span>${book.published_year || 'Unknown'}</span>
                            </div>
                            <div class="info-row">
                                <strong>Duration:</strong>
                                <span>${book.duration_minutes ? `${book.duration_minutes} minutes` : 'Unknown'}</span>
                            </div>
                            <div class="info-row">
                                <strong>Status:</strong>
                                <span class="status-badge ${book.status}">${book.status}</span>
                            </div>
                            <div class="info-row">
                                <strong>Metadata Quality:</strong>
                                <span>${book.metadata_completeness_percent || 0}% complete</span>
                            </div>
                        </div>
                    </div>
                    <div class="book-description">
                        <h3>Description</h3>
                        <p>${this.escapeHtml(book.description || 'No description available.')}</p>
                    </div>
                    <div class="book-actions">
                        <button class="btn btn-primary" onclick="downloadBook(${book.id})">
                            <span class="btn-icon">⬇️</span>
                            Download
                        </button>
                        <button class="btn btn-secondary" onclick="editBook(${book.id})">
                            <span class="btn-icon">✏️</span>
                            Edit Metadata
                        </button>
                        <button class="btn btn-warning" onclick="archiveBook(${book.id})">
                            <span class="btn-icon">📦</span>
                            Archive
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeBookDetailsModal();
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeBookDetailsModal();
            }
        });
    }

    /**
     * Close book details modal
     */
    closeBookDetailsModal() {
        const modal = document.getElementById('book-details-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Download a single book
     */
    async downloadBook(bookId) {
        try {
            // This would integrate with the downloads API
            alert('Download started for book ID: ' + bookId);
            this.closeBookDetailsModal();
        } catch (error) {
            console.error('Download failed:', error);
            alert('Failed to start download');
        }
    }

    /**
     * Edit book metadata
     */
    async editBook(bookId) {
        // This would open an edit form
        alert('Edit functionality would be implemented here for book ID: ' + bookId);
    }

    /**
     * Archive a book
     */
    async archiveBook(bookId) {
        if (!confirm('Archive this book?')) return;

        try {
            // This would call the books API
            alert('Book archived: ' + bookId);
            this.closeBookDetailsModal();
            await this.loadLibraryData(); // Refresh
        } catch (error) {
            console.error('Archive failed:', error);
            alert('Failed to archive book');
        }
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

// Global functions for button handlers
function clearSelection() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.libraryView) {
        window.mamcrawlerDashboard.libraryView.clearSelection();
    }
}

function bulkDownload() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.libraryView) {
        window.mamcrawlerDashboard.libraryView.bulkDownload();
    }
}

function bulkArchive() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.libraryView) {
        window.mamcrawlerDashboard.libraryView.bulkArchive();
    }
}

function bulkDelete() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.libraryView) {
        window.mamcrawlerDashboard.libraryView.bulkDelete();
    }
}

function closeBookDetailsModal() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.libraryView) {
        window.mamcrawlerDashboard.libraryView.closeBookDetailsModal();
    }
}

function downloadBook(bookId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.libraryView) {
        window.mamcrawlerDashboard.libraryView.downloadBook(bookId);
    }
}

function editBook(bookId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.libraryView) {
        window.mamcrawlerDashboard.libraryView.editBook(bookId);
    }
}

function archiveBook(bookId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.libraryView) {
        window.mamcrawlerDashboard.libraryView.archiveBook(bookId);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = LibraryView;
}