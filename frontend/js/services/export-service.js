/**
 * Export service for handling data export functionality
 */

class ExportService {
    constructor() {
        this.supportedFormats = {
            csv: 'text/csv',
            json: 'application/json',
            txt: 'text/plain'
        };
    }

    /**
     * Exports search results to CSV format
     *
     * @param {Array} books - Array of book objects
     * @param {Object} options - Export options
     * @returns {string} CSV content
     */
    exportToCSV(books, options = {}) {
        if (!books || books.length === 0) {
            throw new Error('No books to export');
        }

        const fields = options.fields || [
            'title', 'author', 'series', 'series_number', 'published_year',
            'duration_minutes', 'description', 'metadata_completeness_percent',
            'date_added', 'status'
        ];

        // Create CSV header
        const headers = fields.map(field => this.formatCSVField(this.getFieldLabel(field)));
        let csv = headers.join(',') + '\n';

        // Add data rows
        books.forEach(book => {
            const row = fields.map(field => {
                const value = this.getBookFieldValue(book, field);
                return this.formatCSVField(value);
            });
            csv += row.join(',') + '\n';
        });

        return csv;
    }

    /**
     * Exports search results to JSON format
     *
     * @param {Array} books - Array of book objects
     * @param {Object} options - Export options
     * @returns {string} JSON content
     */
    exportToJSON(books, options = {}) {
        if (!books || books.length === 0) {
            throw new Error('No books to export');
        }

        const exportData = {
            export_info: {
                timestamp: new Date().toISOString(),
                total_books: books.length,
                format: 'json',
                version: '1.0'
            },
            books: books.map(book => this.sanitizeBookForExport(book, options))
        };

        return JSON.stringify(exportData, null, 2);
    }

    /**
     * Exports search results to plain text format
     *
     * @param {Array} books - Array of book objects
     * @param {Object} options - Export options
     * @returns {string} Text content
     */
    exportToText(books, options = {}) {
        if (!books || books.length === 0) {
            throw new Error('No books to export');
        }

        let text = `Audiobook Catalog Export\n`;
        text += `Generated: ${new Date().toLocaleString()}\n`;
        text += `Total Books: ${books.length}\n`;
        text += '='.repeat(50) + '\n\n';

        books.forEach((book, index) => {
            text += `${index + 1}. ${book.title || 'Unknown Title'}\n`;
            if (book.author) text += `   Author: ${book.author}\n`;
            if (book.series) text += `   Series: ${book.series}`;
            if (book.series_number) text += ` #${book.series_number}`;
            text += '\n';
            if (book.published_year) text += `   Published: ${book.published_year}\n`;
            if (book.duration_minutes) text += `   Duration: ${this.formatDuration(book.duration_minutes)}\n`;
            if (book.metadata_completeness_percent !== undefined) {
                text += `   Metadata Quality: ${book.metadata_completeness_percent}%\n`;
            }
            if (book.description) {
                text += `   Description: ${book.description.substring(0, 200)}${book.description.length > 200 ? '...' : ''}\n`;
            }
            text += '\n';
        });

        return text;
    }

    /**
     * Downloads exported data as a file
     *
     * @param {string} content - File content
     * @param {string} filename - File name
     * @param {string} mimeType - MIME type
     */
    downloadFile(content, filename, mimeType = 'text/plain') {
        try {
            const blob = new Blob([content], { type: mimeType });
            const url = URL.createObjectURL(blob);

            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            link.style.display = 'none';

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            // Clean up the URL object
            setTimeout(() => URL.revokeObjectURL(url), 100);
        } catch (error) {
            console.error('Failed to download file:', error);
            throw new Error('Failed to download file: ' + error.message);
        }
    }

    /**
     * Exports and downloads data in the specified format
     *
     * @param {Array} books - Array of book objects
     * @param {string} format - Export format ('csv', 'json', 'txt')
     * @param {Object} options - Export options
     */
    exportBooks(books, format = 'csv', options = {}) {
        if (!this.supportedFormats[format]) {
            throw new Error(`Unsupported export format: ${format}`);
        }

        let content, mimeType, extension;

        switch (format) {
            case 'csv':
                content = this.exportToCSV(books, options);
                mimeType = this.supportedFormats.csv;
                extension = 'csv';
                break;
            case 'json':
                content = this.exportToJSON(books, options);
                mimeType = this.supportedFormats.json;
                extension = 'json';
                break;
            case 'txt':
                content = this.exportToText(books, options);
                mimeType = this.supportedFormats.txt;
                extension = 'txt';
                break;
        }

        const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
        const filename = `audiobooks_export_${timestamp}.${extension}`;

        this.downloadFile(content, filename, mimeType);
    }

    /**
     * Gets a human-readable label for a field
     *
     * @param {string} field - Field name
     * @returns {string} Field label
     */
    getFieldLabel(field) {
        const labels = {
            title: 'Title',
            author: 'Author',
            series: 'Series',
            series_number: 'Series Number',
            published_year: 'Publication Year',
            duration_minutes: 'Duration (minutes)',
            description: 'Description',
            metadata_completeness_percent: 'Metadata Quality (%)',
            date_added: 'Date Added',
            status: 'Status',
            abs_id: 'Audiobookshelf ID',
            isbn: 'ISBN',
            asin: 'ASIN',
            publisher: 'Publisher',
            last_metadata_update: 'Last Updated'
        };

        return labels[field] || field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    /**
     * Gets a field value from a book object
     *
     * @param {Object} book - Book object
     * @param {string} field - Field name
     * @returns {string} Field value
     */
    getBookFieldValue(book, field) {
        const value = book[field];

        if (value === null || value === undefined) {
            return '';
        }

        switch (field) {
            case 'duration_minutes':
                return value ? this.formatDuration(value) : '';
            case 'date_added':
            case 'last_metadata_update':
                return value ? new Date(value).toLocaleDateString() : '';
            case 'description':
                return value ? value.replace(/\n/g, ' ').substring(0, 500) : '';
            default:
                return String(value);
        }
    }

    /**
     * Formats CSV field (escapes quotes and commas)
     *
     * @param {string} value - Field value
     * @returns {string} Formatted CSV field
     */
    formatCSVField(value) {
        if (value === null || value === undefined) {
            return '';
        }

        const stringValue = String(value);

        // If value contains comma, newline, or quote, wrap in quotes
        if (stringValue.includes(',') || stringValue.includes('\n') || stringValue.includes('"')) {
            return '"' + stringValue.replace(/"/g, '""') + '"';
        }

        return stringValue;
    }

    /**
     * Formats duration in minutes to human-readable string
     *
     * @param {number} minutes - Duration in minutes
     * @returns {string} Formatted duration
     */
    formatDuration(minutes) {
        if (!minutes || minutes <= 0) return '';

        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;

        if (hours > 0) {
            return `${hours}h ${remainingMinutes}m`;
        }
        return `${remainingMinutes}m`;
    }

    /**
     * Sanitizes book data for export (removes circular references, etc.)
     *
     * @param {Object} book - Book object
     * @param {Object} options - Export options
     * @returns {Object} Sanitized book data
     */
    sanitizeBookForExport(book, options = {}) {
        const sanitized = { ...book };

        // Remove internal fields that shouldn't be exported
        const fieldsToRemove = ['downloads', 'metadata_corrections', 'missing_book_entries'];

        fieldsToRemove.forEach(field => {
            delete sanitized[field];
        });

        // Format dates
        if (sanitized.date_added) {
            sanitized.date_added = new Date(sanitized.date_added).toISOString();
        }
        if (sanitized.date_updated) {
            sanitized.date_updated = new Date(sanitized.date_updated).toISOString();
        }
        if (sanitized.last_metadata_update) {
            sanitized.last_metadata_update = new Date(sanitized.last_metadata_update).toISOString();
        }

        // Limit description length if specified
        if (options.maxDescriptionLength && sanitized.description) {
            sanitized.description = sanitized.description.substring(0, options.maxDescriptionLength);
        }

        return sanitized;
    }

    /**
     * Gets export statistics
     *
     * @param {Array} books - Array of book objects
     * @returns {Object} Export statistics
     */
    getExportStats(books) {
        if (!books || books.length === 0) {
            return { totalBooks: 0, fields: [], stats: {} };
        }

        const stats = {
            totalBooks: books.length,
            averageMetadataCompleteness: 0,
            booksByStatus: {},
            booksByAuthor: {},
            seriesCount: 0,
            oldestBook: null,
            newestBook: null
        };

        let totalCompleteness = 0;

        books.forEach(book => {
            // Metadata completeness
            if (book.metadata_completeness_percent !== undefined) {
                totalCompleteness += book.metadata_completeness_percent;
            }

            // Status distribution
            const status = book.status || 'unknown';
            stats.booksByStatus[status] = (stats.booksByStatus[status] || 0) + 1;

            // Author distribution
            if (book.author) {
                stats.booksByAuthor[book.author] = (stats.booksByAuthor[book.author] || 0) + 1;
            }

            // Series count
            if (book.series) {
                stats.seriesCount++;
            }

            // Date tracking
            if (book.published_year) {
                if (!stats.oldestBook || book.published_year < stats.oldestBook) {
                    stats.oldestBook = book.published_year;
                }
                if (!stats.newestBook || book.published_year > stats.newestBook) {
                    stats.newestBook = book.published_year;
                }
            }
        });

        stats.averageMetadataCompleteness = stats.totalBooks > 0
            ? Math.round(totalCompleteness / stats.totalBooks)
            : 0;

        return stats;
    }

    /**
     * Validates export data
     *
     * @param {Array} books - Array of book objects
     * @returns {Object} Validation result
     */
    validateExportData(books) {
        const errors = [];
        const warnings = [];

        if (!Array.isArray(books)) {
            errors.push('Books data must be an array');
            return { valid: false, errors, warnings };
        }

        if (books.length === 0) {
            warnings.push('No books to export');
        }

        books.forEach((book, index) => {
            if (!book || typeof book !== 'object') {
                errors.push(`Book at index ${index} is not a valid object`);
                return;
            }

            if (!book.title && !book.id) {
                warnings.push(`Book at index ${index} has no title or ID`);
            }
        });

        return {
            valid: errors.length === 0,
            errors,
            warnings
        };
    }
}

// Export singleton instance
export const exportService = new ExportService();
export default exportService;