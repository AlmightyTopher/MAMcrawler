/**
 * Search filters component for managing filter controls
 */

import { filterService } from '../services/filter-service.js';

class SearchFilters {
    constructor(container) {
        this.container = container;
        this.advancedFilters = null;
        this.filterElements = new Map();

        this.init();
    }

    /**
     * Initializes the filters component
     */
    init() {
        this.createFilterElements();
        this.setupEventListeners();
        this.loadSavedFilters();
    }

    /**
     * Creates filter form elements
     */
    createFilterElements() {
        // Get references to existing elements
        this.advancedFilters = this.container.querySelector('#advanced-filters');
        this.advancedToggle = this.container.querySelector('#advanced-toggle');

        // Create filter element references
        this.filterElements.set('author', this.container.querySelector('#author-filter'));
        this.filterElements.set('narrator', this.container.querySelector('#narrator-filter'));
        this.filterElements.set('series', this.container.querySelector('#series-filter'));
        this.filterElements.set('language', this.container.querySelector('#language-filter'));
        this.filterElements.set('format', this.container.querySelector('#format-filter'));
        this.filterElements.set('pubYearFrom', this.container.querySelector('#pub-year-from'));
        this.filterElements.set('pubYearTo', this.container.querySelector('#pub-year-to'));
        this.filterElements.set('durationFrom', this.container.querySelector('#duration-from'));
        this.filterElements.set('durationTo', this.container.querySelector('#duration-to'));
        this.filterElements.set('completenessMin', this.container.querySelector('#completeness-filter'));
        this.filterElements.set('status', this.container.querySelector('#status-filter'));

        // Action buttons
        this.applyBtn = this.container.querySelector('#apply-filters');
        this.clearBtn = this.container.querySelector('#clear-filters');
        this.saveBtn = this.container.querySelector('#save-search');
    }

    /**
     * Sets up event listeners
     */
    setupEventListeners() {
        // Advanced filters toggle
        if (this.advancedToggle) {
            this.advancedToggle.addEventListener('click', () => this.toggleAdvancedFilters());
        }

        // Apply filters
        if (this.applyBtn) {
            this.applyBtn.addEventListener('click', () => this.applyFilters());
        }

        // Clear filters
        if (this.clearBtn) {
            this.clearBtn.addEventListener('click', () => this.clearFilters());
        }

        // Save search
        if (this.saveBtn) {
            this.saveBtn.addEventListener('click', () => this.saveSearch());
        }

        // Real-time filter updates (debounced)
        this.setupRealTimeUpdates();

        // Listen for filter service changes
        filterService.addListener((filters) => this.updateUIFromFilters(filters));
    }

    /**
     * Sets up real-time filter updates
     */
    setupRealTimeUpdates() {
        const debounceDelay = 300;
        let debounceTimer;

        const debouncedUpdate = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                this.updateFiltersFromUI();
            }, debounceDelay);
        };

        // Text inputs
        ['author', 'narrator', 'series'].forEach(field => {
            const element = this.filterElements.get(field);
            if (element) {
                element.addEventListener('input', debouncedUpdate);
            }
        });

        // Select elements
        ['language', 'format', 'completenessMin', 'status'].forEach(field => {
            const element = this.filterElements.get(field);
            if (element) {
                element.addEventListener('change', () => this.updateFiltersFromUI());
            }
        });

        // Number inputs
        ['pubYearFrom', 'pubYearTo', 'durationFrom', 'durationTo'].forEach(field => {
            const element = this.filterElements.get(field);
            if (element) {
                element.addEventListener('input', debouncedUpdate);
                element.addEventListener('change', () => this.updateFiltersFromUI());
            }
        });
    }

    /**
     * Toggles advanced filters visibility
     */
    toggleAdvancedFilters() {
        if (!this.advancedFilters) return;

        const isHidden = this.advancedFilters.classList.contains('hidden');

        if (isHidden) {
            this.advancedFilters.classList.remove('hidden');
            this.advancedToggle.textContent = 'Hide Advanced Filters';
            this.advancedToggle.setAttribute('aria-expanded', 'true');
        } else {
            this.advancedFilters.classList.add('hidden');
            this.advancedToggle.textContent = 'Advanced Filters';
            this.advancedToggle.setAttribute('aria-expanded', 'false');
        }
    }

    /**
     * Applies current filters
     */
    applyFilters() {
        this.updateFiltersFromUI();

        // Trigger search update (this will be handled by the main search component)
        this.container.dispatchEvent(new CustomEvent('filters-applied', {
            detail: { filters: filterService.getFilters() }
        }));
    }

    /**
     * Clears all filters
     */
    clearFilters() {
        filterService.clearFilters();
        this.updateUIFromFilters(filterService.getFilters());

        // Trigger search update
        this.container.dispatchEvent(new CustomEvent('filters-cleared'));
    }

    /**
     * Saves current search configuration
     */
    saveSearch() {
        const filters = filterService.getFilters();
        const searchName = prompt('Enter a name for this saved search:');

        if (!searchName || !searchName.trim()) {
            return;
        }

        const savedSearch = {
            id: Date.now().toString(),
            name: searchName.trim(),
            filters: { ...filters },
            created: new Date().toISOString()
        };

        // Save to localStorage
        const savedSearches = this.getSavedSearches();
        savedSearches.push(savedSearch);
        localStorage.setItem('mam_saved_searches', JSON.stringify(savedSearches));

        // Show confirmation
        this.showNotification(`Search "${searchName}" saved successfully!`);

        // Trigger event for saved searches modal update
        this.container.dispatchEvent(new CustomEvent('search-saved', {
            detail: { savedSearch }
        }));
    }

    /**
     * Loads a saved search
     */
    loadSavedSearch(savedSearch) {
        filterService.setFilters(savedSearch.filters);
        this.updateUIFromFilters(filterService.getFilters());

        // Trigger search update
        this.container.dispatchEvent(new CustomEvent('filters-applied', {
            detail: { filters: savedSearch.filters }
        }));
    }

    /**
     * Deletes a saved search
     */
    deleteSavedSearch(searchId) {
        const savedSearches = this.getSavedSearches();
        const filtered = savedSearches.filter(search => search.id !== searchId);
        localStorage.setItem('mam_saved_searches', JSON.stringify(filtered));

        // Trigger event for saved searches modal update
        this.container.dispatchEvent(new CustomEvent('search-deleted', {
            detail: { searchId }
        }));
    }

    /**
     * Gets saved searches from localStorage
     */
    getSavedSearches() {
        try {
            const saved = localStorage.getItem('mam_saved_searches');
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.error('Failed to load saved searches:', error);
            return [];
        }
    }

    /**
     * Updates filter service from UI values
     */
    updateFiltersFromUI() {
        const updates = {};

        // Text filters
        ['author', 'narrator', 'series'].forEach(field => {
            const element = this.filterElements.get(field);
            if (element && element.value.trim()) {
                updates[field] = element.value.trim();
            } else {
                updates[field] = '';
            }
        });

        // Select filters
        ['language', 'format', 'status'].forEach(field => {
            const element = this.filterElements.get(field);
            if (element && element.value && element.value !== '') {
                updates[field] = field === 'status' && element.value === 'active' ? 'active' : element.value;
            } else {
                updates[field] = field === 'status' ? 'active' : '';
            }
        });

        // Number filters
        ['pubYearFrom', 'pubYearTo', 'durationFrom', 'durationTo'].forEach(field => {
            const element = this.filterElements.get(field);
            if (element && element.value && !isNaN(parseInt(element.value))) {
                updates[field] = parseInt(element.value);
            } else {
                updates[field] = null;
            }
        });

        // Completeness filter
        const completenessElement = this.filterElements.get('completenessMin');
        if (completenessElement && completenessElement.value) {
            updates.completenessMin = parseInt(completenessElement.value);
        } else {
            updates.completenessMin = 0;
        }

        filterService.setFilters(updates);
    }

    /**
     * Updates UI from filter service values
     */
    updateUIFromFilters(filters) {
        // Text filters
        ['author', 'narrator', 'series'].forEach(field => {
            const element = this.filterElements.get(field);
            if (element) {
                element.value = filters[field] || '';
            }
        });

        // Select filters
        ['language', 'format', 'status'].forEach(field => {
            const element = this.filterElements.get(field);
            if (element) {
                element.value = filters[field] || '';
            }
        });

        // Number filters
        ['pubYearFrom', 'pubYearTo', 'durationFrom', 'durationTo'].forEach(field => {
            const element = this.filterElements.get(field);
            if (element) {
                element.value = filters[field] !== null && filters[field] !== undefined ? filters[field] : '';
            }
        });

        // Completeness filter
        const completenessElement = this.filterElements.get('completenessMin');
        if (completenessElement) {
            completenessElement.value = filters.completenessMin || 0;
        }

        // Update filter summary
        this.updateFilterSummary();
    }

    /**
     * Updates filter summary display
     */
    updateFilterSummary() {
        const summary = filterService.getFilterSummary();
        const summaryContainer = this.container.querySelector('.filter-summary');

        if (summaryContainer) {
            if (summary.length > 0) {
                summaryContainer.innerHTML = `
                    <div class="active-filters">
                        <span class="filter-label">Active filters:</span>
                        ${summary.map(filter => `<span class="filter-tag">${filter}</span>`).join('')}
                    </div>
                `;
                summaryContainer.style.display = 'block';
            } else {
                summaryContainer.style.display = 'none';
            }
        }
    }

    /**
     * Loads saved filters from localStorage
     */
    loadSavedFilters() {
        filterService.loadFromStorage();
        this.updateUIFromFilters(filterService.getFilters());
    }

    /**
     * Shows a notification message
     */
    showNotification(message, type = 'success') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Add to container
        this.container.appendChild(notification);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }

    /**
     * Gets current filter state
     */
    getFilters() {
        return filterService.getFilters();
    }

    /**
     * Checks if any filters are active
     */
    hasActiveFilters() {
        return filterService.hasActiveFilters();
    }

    /**
     * Gets active filter count
     */
    getActiveFilterCount() {
        return filterService.getActiveFilterCount();
    }

    /**
     * Resets the component
     */
    reset() {
        this.clearFilters();
        this.loadSavedFilters();
    }

    /**
     * Destroys the component
     */
    destroy() {
        filterService.removeListener(this.updateUIFromFilters);
        // Remove event listeners if needed
    }
}

export default SearchFilters;