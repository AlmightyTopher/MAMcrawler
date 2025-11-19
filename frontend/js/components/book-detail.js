/**
 * Book detail component for displaying detailed book information in a modal
 */

import { formatDuration } from '../utils/search-utils.js';
import { searchService } from '../services/search-service.js';

class BookDetail {
    constructor(container) {
        this.container = container;
        this.modal = null;
        this.currentBook = null;
        this.relatedBooks = [];

        this.init();
    }

    /**
     * Initializes the book detail component
     */
    init() {
        this.findElements();
        this.setupEventListeners();
    }

    /**
     * Finds DOM elements
     */
    findElements() {
        this.modal = this.container.querySelector('#book-detail-modal');
        this.modalBackdrop = this.container.querySelector('#modal-backdrop');
        this.closeBtn = this.container.querySelector('#close-modal');
        this.modalTitle = this.container.querySelector('#modal-title');
        this.modalBody = this.container.querySelector('#modal-body');
    }

    /**
     * Sets up event listeners
     */
    setupEventListeners() {
        // Close modal events
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.hide());
        }
        if (this.modalBackdrop) {
            this.modalBackdrop.addEventListener('click', () => this.hide());
        }

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (this.isVisible() && e.key === 'Escape') {
                this.hide();
            }
        });

        // Listen for book selection events
        this.container.addEventListener('book-selected', (e) => {
            this.showBook(e.detail.book);
        });
    }

    /**
     * Shows the book detail modal with book information
     */
    async showBook(book) {
        if (!book) return;

        this.currentBook = book;

        try {
            // Fetch full book details if we don't have them
            if (!book.description || !book.full_metadata) {
                const fullBook = await searchService.getBookDetails(book.id);
                this.currentBook = { ...book, ...fullBook };
            }

            // Fetch related books (same series or author)
            await this.loadRelatedBooks();

            this.renderBookDetail();
            this.show();

        } catch (error) {
            console.error('Failed to load book details:', error);
            this.showError('Failed to load book details. Please try again.');
        }
    }

    /**
     * Loads related books for recommendations
     */
    async loadRelatedBooks() {
        this.relatedBooks = [];

        try {
            // Get books from same series
            if (this.currentBook.series) {
                const seriesBooks = await searchService.getSeriesBooks(this.currentBook.series);
                this.relatedBooks = seriesBooks.data.filter(book => book.id !== this.currentBook.id).slice(0, 6);
            }

            // If no series books, get books by same author
            if (this.relatedBooks.length === 0 && this.currentBook.author) {
                // This would require a new API endpoint for author books
                // For now, we'll leave this as a placeholder
            }

        } catch (error) {
            console.warn('Failed to load related books:', error);
        }
    }

    /**
     * Renders the book detail content
     */
    renderBookDetail() {
        if (!this.modalTitle || !this.modalBody) return;

        // Update modal title
        this.modalTitle.textContent = this.currentBook.title || 'Book Details';

        // Create book detail content
        const content = document.createElement('div');
        content.className = 'book-detail-content';

        // Main book info grid
        const grid = document.createElement('div');
        grid.className = 'book-detail-grid';

        // Cover and basic info
        const coverSection = document.createElement('div');
        coverSection.className = 'book-detail-cover-section';

        const cover = document.createElement('div');
        cover.className = 'book-detail-cover';

        if (this.currentBook.cover_url) {
            const img = document.createElement('img');
            img.src = this.currentBook.cover_url;
            img.alt = `Cover for ${this.currentBook.title}`;
            cover.appendChild(img);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'book-cover-placeholder';
            placeholder.textContent = '📖';
            cover.appendChild(placeholder);
        }

        coverSection.appendChild(cover);

        // Action buttons
        const actions = document.createElement('div');
        actions.className = 'book-detail-actions';

        const downloadBtn = this.createActionButton('⬇️ Download', 'download', () => this.downloadBook());
        const favoriteBtn = this.createActionButton('❤️ Favorite', 'favorite', () => this.toggleFavorite());
        const shareBtn = this.createActionButton('📤 Share', 'share', () => this.shareBook());

        actions.appendChild(downloadBtn);
        actions.appendChild(favoriteBtn);
        actions.appendChild(shareBtn);

        coverSection.appendChild(actions);

        // Book information
        const infoSection = document.createElement('div');
        infoSection.className = 'book-detail-info';

        // Title and author
        const title = document.createElement('h1');
        title.className = 'book-detail-title';
        title.textContent = this.currentBook.title || 'Unknown Title';
        infoSection.appendChild(title);

        if (this.currentBook.author) {
            const author = document.createElement('div');
            author.className = 'book-detail-author';
            author.textContent = `by ${this.currentBook.author}`;
            infoSection.appendChild(author);
        }

        // Series information
        if (this.currentBook.series) {
            const series = document.createElement('div');
            series.className = 'book-detail-series';
            series.textContent = `Part of ${this.currentBook.series}`;
            if (this.currentBook.series_number) {
                series.textContent += ` (Book ${this.currentBook.series_number})`;
            }
            infoSection.appendChild(series);
        }

        // Metadata grid
        const metaGrid = document.createElement('div');
        metaGrid.className = 'book-detail-meta';

        this.addMetaItem(metaGrid, 'Duration', formatDuration(this.currentBook.duration_minutes));
        this.addMetaItem(metaGrid, 'Published', this.currentBook.published_year || 'Unknown');
        this.addMetaItem(metaGrid, 'Language', this.currentBook.language || 'English');
        this.addMetaItem(metaGrid, 'Format', this.currentBook.format || 'Unknown');
        this.addMetaItem(metaGrid, 'File Size', this.formatFileSize(this.currentBook.file_size_bytes));
        this.addMetaItem(metaGrid, 'Quality', `${this.currentBook.metadata_completeness_percent || 0}% complete`);

        infoSection.appendChild(metaGrid);

        // Description
        if (this.currentBook.description) {
            const descriptionSection = document.createElement('div');
            descriptionSection.className = 'book-detail-description';

            const descTitle = document.createElement('h3');
            descTitle.textContent = 'Description';
            descriptionSection.appendChild(descTitle);

            const description = document.createElement('p');
            description.textContent = this.currentBook.description;
            descriptionSection.appendChild(description);

            infoSection.appendChild(descriptionSection);
        }

        // Additional metadata
        if (this.currentBook.publisher || this.currentBook.isbn || this.currentBook.asin) {
            const additionalMeta = document.createElement('div');
            additionalMeta.className = 'book-detail-additional-meta';

            const metaTitle = document.createElement('h3');
            metaTitle.textContent = 'Additional Information';
            additionalMeta.appendChild(metaTitle);

            const metaList = document.createElement('dl');
            if (this.currentBook.publisher) {
                metaList.appendChild(this.createMetaPair('Publisher', this.currentBook.publisher));
            }
            if (this.currentBook.isbn) {
                metaList.appendChild(this.createMetaPair('ISBN', this.currentBook.isbn));
            }
            if (this.currentBook.asin) {
                metaList.appendChild(this.createMetaPair('ASIN', this.currentBook.asin));
            }

            additionalMeta.appendChild(metaList);
            infoSection.appendChild(additionalMeta);
        }

        grid.appendChild(coverSection);
        grid.appendChild(infoSection);
        content.appendChild(grid);

        // Related books section
        if (this.relatedBooks.length > 0) {
            const relatedSection = document.createElement('div');
            relatedSection.className = 'book-detail-related';

            const relatedTitle = document.createElement('h3');
            relatedTitle.textContent = `More in ${this.currentBook.series || 'this series'}`;
            relatedSection.appendChild(relatedTitle);

            const relatedGrid = document.createElement('div');
            relatedGrid.className = 'related-books-grid';

            this.relatedBooks.forEach(book => {
                const relatedCard = this.createRelatedBookCard(book);
                relatedGrid.appendChild(relatedCard);
            });

            relatedSection.appendChild(relatedGrid);
            content.appendChild(relatedSection);
        }

        // Clear and append content
        this.modalBody.innerHTML = '';
        this.modalBody.appendChild(content);
    }

    /**
     * Creates an action button
     */
    createActionButton(text, action, handler) {
        const button = document.createElement('button');
        button.className = `btn-primary book-action-btn action-${action}`;
        button.textContent = text;
        button.addEventListener('click', handler);
        return button;
    }

    /**
     * Adds a metadata item to the grid
     */
    addMetaItem(container, label, value) {
        const item = document.createElement('div');
        item.className = 'meta-item';

        const itemLabel = document.createElement('div');
        itemLabel.className = 'meta-label';
        itemLabel.textContent = label;

        const itemValue = document.createElement('div');
        itemValue.className = 'meta-value';
        itemValue.textContent = value;

        item.appendChild(itemLabel);
        item.appendChild(itemValue);
        container.appendChild(item);
    }

    /**
     * Creates a metadata definition pair
     */
    createMetaPair(term, definition) {
        const dt = document.createElement('dt');
        dt.textContent = term;

        const dd = document.createElement('dd');
        dd.textContent = definition;

        return [dt, dd];
    }

    /**
     * Creates a related book card
     */
    createRelatedBookCard(book) {
        const card = document.createElement('div');
        card.className = 'related-book-card';
        card.setAttribute('data-book-id', book.id);
        card.setAttribute('tabindex', '0');
        card.setAttribute('role', 'button');

        const cover = document.createElement('div');
        cover.className = 'related-book-cover';

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

        const info = document.createElement('div');
        info.className = 'related-book-info';

        const title = document.createElement('div');
        title.className = 'related-book-title';
        title.textContent = book.title || 'Unknown Title';
        info.appendChild(title);

        if (book.series_number) {
            const number = document.createElement('div');
            number.className = 'related-book-number';
            number.textContent = `Book ${book.series_number}`;
            info.appendChild(number);
        }

        card.appendChild(cover);
        card.appendChild(info);

        // Click handler
        card.addEventListener('click', () => this.showBook(book));
        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.showBook(book);
            }
        });

        return card;
    }

    /**
     * Formats file size in human-readable format
     */
    formatFileSize(bytes) {
        if (!bytes) return 'Unknown';

        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let size = bytes;
        let unitIndex = 0;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        return `${size.toFixed(1)} ${units[unitIndex]}`;
    }

    /**
     * Downloads the book
     */
    downloadBook() {
        if (!this.currentBook) return;

        // This would integrate with the download system
        console.log('Downloading book:', this.currentBook.title);

        // Show notification
        this.showNotification('Download started for: ' + this.currentBook.title);

        // Trigger download event
        this.container.dispatchEvent(new CustomEvent('book-download', {
            detail: { book: this.currentBook }
        }));
    }

    /**
     * Toggles favorite status
     */
    toggleFavorite() {
        if (!this.currentBook) return;

        // This would integrate with a favorites system
        console.log('Toggling favorite for:', this.currentBook.title);

        // Update button text
        const favoriteBtn = this.modal.querySelector('.action-favorite');
        if (favoriteBtn) {
            const isFavorited = favoriteBtn.classList.contains('favorited');
            if (isFavorited) {
                favoriteBtn.textContent = '❤️ Favorite';
                favoriteBtn.classList.remove('favorited');
            } else {
                favoriteBtn.textContent = '💖 Favorited';
                favoriteBtn.classList.add('favorited');
            }
        }

        // Trigger favorite event
        this.container.dispatchEvent(new CustomEvent('book-favorite-toggle', {
            detail: { book: this.currentBook }
        }));
    }

    /**
     * Shares the book
     */
    shareBook() {
        if (!this.currentBook) return;

        const shareData = {
            title: this.currentBook.title,
            text: `Check out this audiobook: ${this.currentBook.title} by ${this.currentBook.author}`,
            url: window.location.href
        };

        if (navigator.share) {
            navigator.share(shareData);
        } else {
            // Fallback: copy to clipboard
            const shareText = `${shareData.title}\n${shareData.text}\n${shareData.url}`;
            navigator.clipboard.writeText(shareText).then(() => {
                this.showNotification('Book details copied to clipboard!');
            });
        }
    }

    /**
     * Shows an error message
     */
    showError(message) {
        if (!this.modalBody) return;

        const errorDiv = document.createElement('div');
        errorDiv.className = 'book-detail-error';
        errorDiv.innerHTML = `
            <div class="error-icon">⚠️</div>
            <h3>Error Loading Book</h3>
            <p>${message}</p>
            <button class="btn-primary" onclick="this.parentElement.remove(); this.closest('.modal').querySelector('#close-modal').click();">Close</button>
        `;

        this.modalBody.innerHTML = '';
        this.modalBody.appendChild(errorDiv);
        this.show();
    }

    /**
     * Shows a notification
     */
    showNotification(message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = 'notification notification-success';
        notification.textContent = message;

        // Add to modal temporarily
        if (this.modal) {
            this.modal.appendChild(notification);

            // Auto-remove after 3 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 3000);
        }
    }

    /**
     * Shows the modal
     */
    show() {
        if (this.modal) {
            this.modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden'; // Prevent background scrolling

            // Focus management
            this.modal.setAttribute('aria-hidden', 'false');
            this.closeBtn.focus();
        }
    }

    /**
     * Hides the modal
     */
    hide() {
        if (this.modal) {
            this.modal.classList.add('hidden');
            document.body.style.overflow = ''; // Restore scrolling

            // Focus management
            this.modal.setAttribute('aria-hidden', 'true');

            // Trigger hide event
            this.container.dispatchEvent(new CustomEvent('book-detail-hidden'));
        }
    }

    /**
     * Checks if modal is visible
     */
    isVisible() {
        return this.modal && !this.modal.classList.contains('hidden');
    }

    /**
     * Gets current book
     */
    getCurrentBook() {
        return this.currentBook;
    }

    /**
     * Destroys the component
     */
    destroy() {
        this.hide();
        // Remove event listeners if needed
    }
}

export default BookDetail;