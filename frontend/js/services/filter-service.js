/**
 * Filter service for managing search filter state and logic
 */

class FilterService {
    constructor() {
        this.filters = this.getDefaultFilters();
        this.listeners = new Set();
    }

    /**
     * Gets default filter values
     *
     * @returns {Object} Default filter state
     */
    getDefaultFilters() {
        return {
            // Text filters
            author: '',
            narrator: '',
            series: '',

            // Multi-select filters
            genres: [],
            languages: [],
            formats: [],

            // Range filters
            pubYearFrom: null,
            pubYearTo: null,
            durationFrom: null,
            durationTo: null,

            // Quality filters
            completenessMin: 0,
            status: 'active',

            // Advanced filters
            hasCover: null, // true, false, or null
            dateAddedFrom: null,
            dateAddedTo: null
        };
    }

    /**
     * Gets current filter state
     *
     * @returns {Object} Current filters
     */
    getFilters() {
        return { ...this.filters };
    }

    /**
     * Updates a single filter value
     *
     * @param {string} key - Filter key
     * @param {any} value - Filter value
     */
    setFilter(key, value) {
        if (!(key in this.filters)) {
            console.warn(`Unknown filter key: ${key}`);
            return;
        }

        // Validate value based on filter type
        if (!this.validateFilterValue(key, value)) {
            console.warn(`Invalid value for filter ${key}:`, value);
            return;
        }

        this.filters[key] = value;
        this.notifyListeners();
    }

    /**
     * Updates multiple filters at once
     *
     * @param {Object} updates - Filter updates
     */
    setFilters(updates) {
        let hasChanges = false;

        Object.entries(updates).forEach(([key, value]) => {
            if (key in this.filters && this.validateFilterValue(key, value)) {
                this.filters[key] = value;
                hasChanges = true;
            }
        });

        if (hasChanges) {
            this.notifyListeners();
        }
    }

    /**
     * Validates filter value based on type
     *
     * @param {string} key - Filter key
     * @param {any} value - Filter value
     * @returns {boolean} Whether value is valid
     */
    validateFilterValue(key, value) {
        switch (key) {
            case 'genres':
            case 'languages':
            case 'formats':
                return Array.isArray(value);

            case 'pubYearFrom':
            case 'pubYearTo':
                return value === null || (typeof value === 'number' && value >= 1900 && value <= 2030);

            case 'durationFrom':
            case 'durationTo':
                return value === null || (typeof value === 'number' && value >= 0);

            case 'completenessMin':
                return typeof value === 'number' && value >= 0 && value <= 100;

            case 'status':
                return ['active', 'duplicate', 'archived', ''].includes(value);

            case 'hasCover':
                return value === null || typeof value === 'boolean';

            case 'author':
            case 'narrator':
            case 'series':
                return typeof value === 'string';

            case 'dateAddedFrom':
            case 'dateAddedTo':
                return value === null || (value instanceof Date) || (typeof value === 'string' && !isNaN(Date.parse(value)));

            default:
                return true;
        }
    }

    /**
     * Clears all filters (resets to defaults)
     */
    clearFilters() {
        this.filters = this.getDefaultFilters();
        this.notifyListeners();
    }

    /**
     * Checks if any filters are active (non-default values)
     *
     * @returns {boolean} Whether any filters are active
     */
    hasActiveFilters() {
        const defaults = this.getDefaultFilters();

        return Object.entries(this.filters).some(([key, value]) => {
            const defaultValue = defaults[key];

            if (Array.isArray(value) && Array.isArray(defaultValue)) {
                return value.length !== defaultValue.length ||
                       value.some((v, i) => v !== defaultValue[i]);
            }

            return value !== defaultValue;
        });
    }

    /**
     * Gets active filter count
     *
     * @returns {number} Number of active filters
     */
    getActiveFilterCount() {
        let count = 0;

        if (this.filters.author) count++;
        if (this.filters.narrator) count++;
        if (this.filters.series) count++;
        if (this.filters.genres.length > 0) count++;
        if (this.filters.languages.length > 0) count++;
        if (this.filters.formats.length > 0) count++;
        if (this.filters.pubYearFrom !== null) count++;
        if (this.filters.pubYearTo !== null) count++;
        if (this.filters.durationFrom !== null) count++;
        if (this.filters.durationTo !== null) count++;
        if (this.filters.completenessMin > 0) count++;
        if (this.filters.status !== 'active') count++;
        if (this.filters.hasCover !== null) count++;
        if (this.filters.dateAddedFrom !== null) count++;
        if (this.filters.dateAddedTo !== null) count++;

        return count;
    }

    /**
     * Converts filters to API query parameters
     *
     * @returns {Object} Query parameters for API
     */
    toQueryParams() {
        const params = {};

        // Text filters
        if (this.filters.author) params.author = this.filters.author;
        if (this.filters.narrator) params.narrator = this.filters.narrator;
        if (this.filters.series) params.series = this.filters.series;

        // Multi-select filters (join arrays)
        if (this.filters.genres.length > 0) params.genres = this.filters.genres.join(',');
        if (this.filters.languages.length > 0) params.languages = this.filters.languages.join(',');
        if (this.filters.formats.length > 0) params.formats = this.filters.formats.join(',');

        // Range filters
        if (this.filters.pubYearFrom !== null) params.pub_year_from = this.filters.pubYearFrom;
        if (this.filters.pubYearTo !== null) params.pub_year_to = this.filters.pubYearTo;
        if (this.filters.durationFrom !== null) params.duration_from = this.filters.durationFrom;
        if (this.filters.durationTo !== null) params.duration_to = this.filters.durationTo;

        // Quality filters
        if (this.filters.completenessMin > 0) params.completeness_min = this.filters.completenessMin;
        if (this.filters.status !== 'active') params.status = this.filters.status;

        // Advanced filters
        if (this.filters.hasCover !== null) params.has_cover = this.filters.hasCover;
        if (this.filters.dateAddedFrom !== null) {
            params.date_added_from = this.filters.dateAddedFrom instanceof Date
                ? this.filters.dateAddedFrom.toISOString()
                : this.filters.dateAddedFrom;
        }
        if (this.filters.dateAddedTo !== null) {
            params.date_added_to = this.filters.dateAddedTo instanceof Date
                ? this.filters.dateAddedTo.toISOString()
                : this.filters.dateAddedTo;
        }

        return params;
    }

    /**
     * Loads filters from URL query parameters
     *
     * @param {URLSearchParams} urlParams - URL search parameters
     */
    fromQueryParams(urlParams) {
        const updates = {};

        // Text filters
        if (urlParams.has('author')) updates.author = urlParams.get('author');
        if (urlParams.has('narrator')) updates.narrator = urlParams.get('narrator');
        if (urlParams.has('series')) updates.series = urlParams.get('series');

        // Multi-select filters
        if (urlParams.has('genres')) {
            updates.genres = urlParams.get('genres').split(',').filter(g => g.trim());
        }
        if (urlParams.has('languages')) {
            updates.languages = urlParams.get('languages').split(',').filter(l => l.trim());
        }
        if (urlParams.has('formats')) {
            updates.formats = urlParams.get('formats').split(',').filter(f => f.trim());
        }

        // Range filters
        if (urlParams.has('pub_year_from')) {
            updates.pubYearFrom = parseInt(urlParams.get('pub_year_from'));
        }
        if (urlParams.has('pub_year_to')) {
            updates.pubYearTo = parseInt(urlParams.get('pub_year_to'));
        }
        if (urlParams.has('duration_from')) {
            updates.durationFrom = parseInt(urlParams.get('duration_from'));
        }
        if (urlParams.has('duration_to')) {
            updates.durationTo = parseInt(urlParams.get('duration_to'));
        }

        // Quality filters
        if (urlParams.has('completeness_min')) {
            updates.completenessMin = parseInt(urlParams.get('completeness_min'));
        }
        if (urlParams.has('status')) {
            updates.status = urlParams.get('status');
        }

        // Advanced filters
        if (urlParams.has('has_cover')) {
            updates.hasCover = urlParams.get('has_cover') === 'true';
        }
        if (urlParams.has('date_added_from')) {
            updates.dateAddedFrom = urlParams.get('date_added_from');
        }
        if (urlParams.has('date_added_to')) {
            updates.dateAddedTo = urlParams.get('date_added_to');
        }

        this.setFilters(updates);
    }

    /**
     * Saves current filters to localStorage
     *
     * @param {string} key - Storage key
     */
    saveToStorage(key = 'mam_search_filters') {
        try {
            localStorage.setItem(key, JSON.stringify(this.filters));
        } catch (error) {
            console.warn('Failed to save filters to localStorage:', error);
        }
    }

    /**
     * Loads filters from localStorage
     *
     * @param {string} key - Storage key
     */
    loadFromStorage(key = 'mam_search_filters') {
        try {
            const stored = localStorage.getItem(key);
            if (stored) {
                const parsed = JSON.parse(stored);
                // Validate and merge with defaults
                const validFilters = {};
                Object.keys(this.filters).forEach(filterKey => {
                    if (filterKey in parsed && this.validateFilterValue(filterKey, parsed[filterKey])) {
                        validFilters[filterKey] = parsed[filterKey];
                    }
                });
                this.setFilters(validFilters);
            }
        } catch (error) {
            console.warn('Failed to load filters from localStorage:', error);
        }
    }

    /**
     * Adds a change listener
     *
     * @param {Function} listener - Change listener function
     */
    addListener(listener) {
        this.listeners.add(listener);
    }

    /**
     * Removes a change listener
     *
     * @param {Function} listener - Change listener function
     */
    removeListener(listener) {
        this.listeners.delete(listener);
    }

    /**
     * Notifies all listeners of filter changes
     */
    notifyListeners() {
        this.listeners.forEach(listener => {
            try {
                listener(this.filters);
            } catch (error) {
                console.error('Filter listener error:', error);
            }
        });
    }

    /**
     * Gets filter summary for display
     *
     * @returns {Array} Array of active filter descriptions
     */
    getFilterSummary() {
        const summary = [];

        if (this.filters.author) {
            summary.push(`Author: ${this.filters.author}`);
        }
        if (this.filters.narrator) {
            summary.push(`Narrator: ${this.filters.narrator}`);
        }
        if (this.filters.series) {
            summary.push(`Series: ${this.filters.series}`);
        }
        if (this.filters.genres.length > 0) {
            summary.push(`Genres: ${this.filters.genres.join(', ')}`);
        }
        if (this.filters.languages.length > 0) {
            summary.push(`Languages: ${this.filters.languages.join(', ')}`);
        }
        if (this.filters.formats.length > 0) {
            summary.push(`Formats: ${this.filters.formats.join(', ')}`);
        }
        if (this.filters.pubYearFrom || this.filters.pubYearTo) {
            const from = this.filters.pubYearFrom || 'Any';
            const to = this.filters.pubYearTo || 'Any';
            summary.push(`Published: ${from} - ${to}`);
        }
        if (this.filters.durationFrom || this.filters.durationTo) {
            const from = this.filters.durationFrom ? `${this.filters.durationFrom}h` : 'Any';
            const to = this.filters.durationTo ? `${this.filters.durationTo}h` : 'Any';
            summary.push(`Duration: ${from} - ${to}`);
        }
        if (this.filters.completenessMin > 0) {
            summary.push(`Min Quality: ${this.filters.completenessMin}%`);
        }
        if (this.filters.status !== 'active') {
            summary.push(`Status: ${this.filters.status}`);
        }

        return summary;
    }
}

// Export singleton instance
export const filterService = new FilterService();
export default filterService;