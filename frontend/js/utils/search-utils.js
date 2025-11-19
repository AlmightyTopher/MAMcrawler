/**
 * Search utility functions for parsing queries, scoring results, and text processing
 */

/**
 * Parses a search query into individual terms and operators
 * Supports: AND, OR, NOT, quotes for exact phrases
 *
 * @param {string} query - The search query to parse
 * @returns {Object} Parsed query object with terms and operators
 */
export function parseSearchQuery(query) {
    if (!query || typeof query !== 'string') {
        return { terms: [], operators: [], original: query };
    }

    const terms = [];
    const operators = [];
    let currentTerm = '';
    let inQuotes = false;
    let i = 0;

    query = query.trim();

    while (i < query.length) {
        const char = query[i];

        if (char === '"' && (i === 0 || query[i-1] === ' ')) {
            // Start of quoted phrase
            inQuotes = true;
            i++;
            continue;
        }

        if (char === '"' && inQuotes) {
            // End of quoted phrase
            if (currentTerm.trim()) {
                terms.push({
                    text: currentTerm.trim(),
                    exact: true,
                    negated: false
                });
            }
            currentTerm = '';
            inQuotes = false;
            i++;
            continue;
        }

        if (!inQuotes && char === ' ') {
            // Process completed term
            const trimmedTerm = currentTerm.trim();
            if (trimmedTerm) {
                // Check for operators
                const upperTerm = trimmedTerm.toUpperCase();
                if (['AND', 'OR', 'NOT'].includes(upperTerm)) {
                    operators.push(upperTerm);
                } else {
                    terms.push({
                        text: trimmedTerm,
                        exact: false,
                        negated: trimmedTerm.startsWith('-')
                    });
                }
            }
            currentTerm = '';
        } else {
            currentTerm += char;
        }

        i++;
    }

    // Process final term
    const trimmedTerm = currentTerm.trim();
    if (trimmedTerm) {
        const upperTerm = trimmedTerm.toUpperCase();
        if (['AND', 'OR', 'NOT'].includes(upperTerm)) {
            operators.push(upperTerm);
        } else {
            terms.push({
                text: trimmedTerm,
                exact: false,
                negated: trimmedTerm.startsWith('-')
            });
        }
    }

    return {
        terms: terms,
        operators: operators,
        original: query
    };
}

/**
 * Calculates relevance score for a book based on search terms
 *
 * @param {Object} book - Book object with metadata
 * @param {Array} searchTerms - Array of search term objects
 * @returns {number} Relevance score (0-100)
 */
export function calculateRelevanceScore(book, searchTerms) {
    if (!searchTerms || searchTerms.length === 0) {
        return 100; // No search terms = maximum relevance
    }

    let totalScore = 0;
    let maxPossibleScore = 0;

    // Define field weights for scoring
    const fieldWeights = {
        title: 10,
        author: 8,
        series: 7,
        description: 3,
        narrator: 6,
        publisher: 2,
        isbn: 1,
        asin: 1
    };

    // Normalize book data for searching
    const normalizedBook = {};
    for (const [key, value] of Object.entries(book)) {
        if (typeof value === 'string') {
            normalizedBook[key] = value.toLowerCase();
        } else {
            normalizedBook[key] = value;
        }
    }

    searchTerms.forEach(term => {
        const termText = term.text.toLowerCase().replace(/^-/, '');
        let termScore = 0;
        let termMaxScore = 0;

        // Check each field
        for (const [field, weight] of Object.entries(fieldWeights)) {
            if (normalizedBook[field]) {
                const fieldValue = normalizedBook[field];
                termMaxScore += weight;

                if (term.exact) {
                    // Exact phrase matching
                    if (fieldValue.includes(termText)) {
                        termScore += weight;
                    }
                } else {
                    // Fuzzy matching with word boundaries
                    const words = termText.split(/\s+/);
                    let fieldMatchScore = 0;

                    words.forEach(word => {
                        if (fieldValue.includes(word)) {
                            // Boost score for word matches
                            fieldMatchScore += weight;
                            // Extra boost for title/author matches
                            if (['title', 'author'].includes(field)) {
                                fieldMatchScore += weight * 0.5;
                            }
                        }
                    });

                    // Partial score if some words match
                    if (fieldMatchScore > 0) {
                        termScore += Math.min(fieldMatchScore, weight);
                    }
                }
            }
        }

        // Apply negation penalty
        if (term.negated) {
            termScore = -termScore * 2; // Strong negative signal
        }

        totalScore += termScore;
        maxPossibleScore += termMaxScore;
    });

    // Normalize to 0-100 scale
    if (maxPossibleScore === 0) {
        return 0;
    }

    const normalizedScore = (totalScore / maxPossibleScore) * 100;
    return Math.max(0, Math.min(100, normalizedScore));
}

/**
 * Filters books based on applied filters
 *
 * @param {Array} books - Array of book objects
 * @param {Object} filters - Filter criteria object
 * @returns {Array} Filtered books array
 */
export function applyFilters(books, filters) {
    if (!filters || Object.keys(filters).length === 0) {
        return books;
    }

    return books.filter(book => {
        // Genre filter
        if (filters.genres && filters.genres.length > 0) {
            // Note: This would need genre classification logic
            // For now, we'll skip genre filtering as it's not in the current data model
        }

        // Author filter
        if (filters.author && book.author) {
            if (!book.author.toLowerCase().includes(filters.author.toLowerCase())) {
                return false;
            }
        }

        // Narrator filter (not in current model, but placeholder)
        if (filters.narrator) {
            // Would check narrator field if available
        }

        // Series filter
        if (filters.series && book.series) {
            if (!book.series.toLowerCase().includes(filters.series.toLowerCase())) {
                return false;
            }
        }

        // Language filter (not in current model, but placeholder)
        if (filters.language) {
            // Would check language field if available
        }

        // File format filter (not in current model, but placeholder)
        if (filters.format) {
            // Would check format field if available
        }

        // Publication year range
        if (filters.pubYearFrom && book.published_year) {
            if (book.published_year < filters.pubYearFrom) {
                return false;
            }
        }
        if (filters.pubYearTo && book.published_year) {
            if (book.published_year > filters.pubYearTo) {
                return false;
            }
        }

        // Duration range
        if (filters.durationFrom && book.duration_minutes) {
            if (book.duration_minutes < filters.durationFrom) {
                return false;
            }
        }
        if (filters.durationTo && book.duration_minutes) {
            if (book.duration_minutes > filters.durationTo) {
                return false;
            }
        }

        // Metadata completeness
        if (filters.completenessMin && book.metadata_completeness_percent) {
            if (book.metadata_completeness_percent < filters.completenessMin) {
                return false;
            }
        }

        // Status filter
        if (filters.status && book.status !== filters.status) {
            return false;
        }

        return true;
    });
}

/**
 * Sorts books by specified criteria
 *
 * @param {Array} books - Array of book objects
 * @param {string} sortBy - Sort field
 * @param {string} direction - Sort direction ('asc' or 'desc')
 * @returns {Array} Sorted books array
 */
export function sortBooks(books, sortBy = 'relevance', direction = 'desc') {
    const sortDirection = direction === 'asc' ? 1 : -1;

    return [...books].sort((a, b) => {
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
            case 'published_year':
                aValue = a.published_year || 0;
                bValue = b.published_year || 0;
                break;
            case 'duration_minutes':
                aValue = a.duration_minutes || 0;
                bValue = b.duration_minutes || 0;
                break;
            case 'date_added':
                aValue = new Date(a.date_added || 0);
                bValue = new Date(b.date_added || 0);
                break;
            case 'metadata_completeness_percent':
                aValue = a.metadata_completeness_percent || 0;
                bValue = b.metadata_completeness_percent || 0;
                break;
            case 'relevance':
            default:
                aValue = a.relevance_score || 0;
                bValue = b.relevance_score || 0;
                break;
        }

        if (aValue < bValue) return -1 * sortDirection;
        if (aValue > bValue) return 1 * sortDirection;
        return 0;
    });
}

/**
 * Formats duration in minutes to human-readable string
 *
 * @param {number} minutes - Duration in minutes
 * @returns {string} Formatted duration string
 */
export function formatDuration(minutes) {
    if (!minutes || minutes <= 0) {
        return 'Unknown';
    }

    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    if (hours > 0) {
        return `${hours}h ${remainingMinutes}m`;
    } else {
        return `${remainingMinutes}m`;
    }
}

/**
 * Truncates text to specified length with ellipsis
 *
 * @param {string} text - Text to truncate
 * @param {number} maxLength - Maximum length
 * @returns {string} Truncated text
 */
export function truncateText(text, maxLength = 100) {
    if (!text || text.length <= maxLength) {
        return text;
    }

    return text.substring(0, maxLength - 3) + '...';
}

/**
 * Generates excerpt from text with search term highlighting
 *
 * @param {string} text - Full text
 * @param {string} searchTerm - Term to highlight
 * @param {number} maxLength - Maximum excerpt length
 * @returns {string} HTML excerpt with highlighting
 */
export function generateExcerpt(text, searchTerm, maxLength = 200) {
    if (!text) return '';

    const lowerText = text.toLowerCase();
    const lowerTerm = searchTerm.toLowerCase();

    let startIndex = lowerText.indexOf(lowerTerm);
    if (startIndex === -1) {
        return truncateText(text, maxLength);
    }

    // Try to center the match in the excerpt
    const excerptStart = Math.max(0, startIndex - maxLength / 2);
    const excerptEnd = Math.min(text.length, excerptStart + maxLength);

    let excerpt = text.substring(excerptStart, excerptEnd);

    // Add ellipsis if needed
    if (excerptStart > 0) {
        excerpt = '...' + excerpt;
    }
    if (excerptEnd < text.length) {
        excerpt = excerpt + '...';
    }

    // Highlight the search term
    const regex = new RegExp(`(${searchTerm})`, 'gi');
    excerpt = excerpt.replace(regex, '<mark>$1</mark>');

    return excerpt;
}

/**
 * Deburrs text (removes accents and diacritics)
 *
 * @param {string} text - Text to deburr
 * @returns {string} Deburr text
 */
export function deburr(text) {
    return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
}

/**
 * Normalizes text for searching (lowercase, deburr, trim)
 *
 * @param {string} text - Text to normalize
 * @returns {string} Normalized text
 */
export function normalizeText(text) {
    if (!text) return '';
    return deburr(text.toLowerCase().trim());
}