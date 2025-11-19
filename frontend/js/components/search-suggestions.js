/**
 * Search suggestions component for autocomplete functionality
 */

class SearchSuggestions {
    constructor(searchInput, suggestionsContainer) {
        this.searchInput = searchInput;
        this.suggestionsContainer = suggestionsContainer;
        this.suggestions = [];
        this.selectedIndex = -1;
        this.debounceTimer = null;
        this.minQueryLength = 2;
        this.maxSuggestions = 8;

        this.init();
    }

    /**
     * Initializes the suggestions component
     */
    init() {
        this.setupEventListeners();
        this.hide();
    }

    /**
     * Sets up event listeners
     */
    setupEventListeners() {
        // Input events
        this.searchInput.addEventListener('input', (e) => this.handleInput(e));
        this.searchInput.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.searchInput.addEventListener('focus', () => this.handleFocus());
        this.searchInput.addEventListener('blur', () => this.handleBlur());

        // Container events
        this.suggestionsContainer.addEventListener('mousedown', (e) => {
            e.preventDefault(); // Prevent input blur
        });

        // Global click to hide suggestions
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.suggestionsContainer.contains(e.target)) {
                this.hide();
            }
        });
    }

    /**
     * Handles input events
     */
    async handleInput(event) {
        const query = event.target.value.trim();

        // Clear previous timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Hide suggestions for short queries
        if (query.length < this.minQueryLength) {
            this.hide();
            return;
        }

        // Debounce the search
        this.debounceTimer = setTimeout(async () => {
            await this.fetchSuggestions(query);
        }, 150);
    }

    /**
     * Handles keyboard navigation
     */
    handleKeydown(event) {
        if (!this.isVisible()) return;

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                this.selectNext();
                break;
            case 'ArrowUp':
                event.preventDefault();
                this.selectPrevious();
                break;
            case 'Enter':
                event.preventDefault();
                this.selectCurrent();
                break;
            case 'Escape':
                this.hide();
                break;
            case 'Tab':
                this.hide();
                break;
        }
    }

    /**
     * Handles input focus
     */
    handleFocus() {
        const query = this.searchInput.value.trim();
        if (query.length >= this.minQueryLength && this.suggestions.length > 0) {
            this.show();
        }
    }

    /**
     * Handles input blur (delayed to allow for suggestion clicks)
     */
    handleBlur() {
        setTimeout(() => {
            if (!this.suggestionsContainer.matches(':hover')) {
                this.hide();
            }
        }, 150);
    }

    /**
     * Fetches suggestions from the API
     */
    async fetchSuggestions(query) {
        try {
            // For now, we'll generate mock suggestions
            // In a real implementation, this would call the backend API
            const suggestions = await this.generateMockSuggestions(query);

            if (suggestions.length > 0) {
                this.suggestions = suggestions;
                this.renderSuggestions();
                this.show();
            } else {
                this.hide();
            }
        } catch (error) {
            console.error('Failed to fetch suggestions:', error);
            this.hide();
        }
    }

    /**
     * Generates mock suggestions for demonstration
     * In production, this would be replaced with actual API calls
     */
    async generateMockSuggestions(query) {
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 50));

        const mockData = [
            { text: 'The Name of the Wind', type: 'title', author: 'Patrick Rothfuss' },
            { text: 'Patrick Rothfuss', type: 'author', count: 3 },
            { text: 'The Kingkiller Chronicle', type: 'series', count: 3 },
            { text: 'The Wise Man\'s Fear', type: 'title', author: 'Patrick Rothfuss' },
            { text: 'Brandon Sanderson', type: 'author', count: 12 },
            { text: 'Mistborn', type: 'series', count: 4 },
            { text: 'The Final Empire', type: 'title', author: 'Brandon Sanderson' },
            { text: 'Neil Gaiman', type: 'author', count: 8 },
            { text: 'American Gods', type: 'title', author: 'Neil Gaiman' },
            { text: 'Good Omens', type: 'title', author: 'Neil Gaiman & Terry Pratchett' }
        ];

        // Filter suggestions based on query
        const filtered = mockData.filter(item => {
            const searchText = item.text.toLowerCase();
            const searchQuery = query.toLowerCase();
            return searchText.includes(searchQuery);
        });

        // Sort by relevance (exact matches first, then starts with, then contains)
        filtered.sort((a, b) => {
            const aText = a.text.toLowerCase();
            const bText = b.text.toLowerCase();
            const queryLower = query.toLowerCase();

            // Exact matches first
            if (aText === queryLower && bText !== queryLower) return -1;
            if (bText === queryLower && aText !== queryLower) return 1;

            // Starts with query
            const aStarts = aText.startsWith(queryLower);
            const bStarts = bText.startsWith(queryLower);
            if (aStarts && !bStarts) return -1;
            if (bStarts && !aStarts) return 1;

            // By type priority (titles first, then authors, then series)
            const typePriority = { title: 3, author: 2, series: 1 };
            const aPriority = typePriority[a.type] || 0;
            const bPriority = typePriority[b.type] || 0;
            if (aPriority !== bPriority) return bPriority - aPriority;

            // Alphabetically
            return aText.localeCompare(bText);
        });

        return filtered.slice(0, this.maxSuggestions);
    }

    /**
     * Renders suggestions in the container
     */
    renderSuggestions() {
        this.suggestionsContainer.innerHTML = '';

        this.suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'search-suggestion-item';
            item.dataset.index = index;

            // Add click handler
            item.addEventListener('click', () => this.selectSuggestion(suggestion));

            // Create suggestion content
            const textSpan = document.createElement('span');
            textSpan.className = 'suggestion-text';
            textSpan.textContent = suggestion.text;

            const typeSpan = document.createElement('span');
            typeSpan.className = 'suggestion-type';
            typeSpan.textContent = this.getSuggestionTypeLabel(suggestion);

            item.appendChild(textSpan);
            item.appendChild(typeSpan);

            // Highlight current selection
            if (index === this.selectedIndex) {
                item.classList.add('highlighted');
            }

            this.suggestionsContainer.appendChild(item);
        });
    }

    /**
     * Gets human-readable type label
     */
    getSuggestionTypeLabel(suggestion) {
        switch (suggestion.type) {
            case 'title':
                return suggestion.author ? `Book • ${suggestion.author}` : 'Book';
            case 'author':
                return suggestion.count ? `Author • ${suggestion.count} books` : 'Author';
            case 'series':
                return suggestion.count ? `Series • ${suggestion.count} books` : 'Series';
            default:
                return suggestion.type || '';
        }
    }

    /**
     * Selects the next suggestion
     */
    selectNext() {
        if (this.suggestions.length === 0) return;

        this.selectedIndex = (this.selectedIndex + 1) % this.suggestions.length;
        this.updateSelection();
    }

    /**
     * Selects the previous suggestion
     */
    selectPrevious() {
        if (this.suggestions.length === 0) return;

        this.selectedIndex = this.selectedIndex <= 0
            ? this.suggestions.length - 1
            : this.selectedIndex - 1;
        this.updateSelection();
    }

    /**
     * Selects the currently highlighted suggestion
     */
    selectCurrent() {
        if (this.selectedIndex >= 0 && this.selectedIndex < this.suggestions.length) {
            this.selectSuggestion(this.suggestions[this.selectedIndex]);
        }
    }

    /**
     * Selects a specific suggestion
     */
    selectSuggestion(suggestion) {
        this.searchInput.value = suggestion.text;
        this.hide();

        // Trigger search
        this.searchInput.dispatchEvent(new Event('input', { bubbles: true }));

        // Focus back to input
        this.searchInput.focus();
    }

    /**
     * Updates the visual selection
     */
    updateSelection() {
        // Remove previous selection
        const previousSelected = this.suggestionsContainer.querySelector('.highlighted');
        if (previousSelected) {
            previousSelected.classList.remove('highlighted');
        }

        // Add new selection
        if (this.selectedIndex >= 0) {
            const currentSelected = this.suggestionsContainer.querySelector(
                `[data-index="${this.selectedIndex}"]`
            );
            if (currentSelected) {
                currentSelected.classList.add('highlighted');
                // Scroll into view if needed
                currentSelected.scrollIntoView({ block: 'nearest' });
            }
        }
    }

    /**
     * Shows the suggestions container
     */
    show() {
        this.suggestionsContainer.classList.remove('hidden');
    }

    /**
     * Hides the suggestions container
     */
    hide() {
        this.suggestionsContainer.classList.add('hidden');
        this.selectedIndex = -1;
        this.suggestions = [];
    }

    /**
     * Checks if suggestions are visible
     */
    isVisible() {
        return !this.suggestionsContainer.classList.contains('hidden');
    }

    /**
     * Clears suggestions
     */
    clear() {
        this.suggestions = [];
        this.selectedIndex = -1;
        this.suggestionsContainer.innerHTML = '';
        this.hide();
    }

    /**
     * Updates suggestions data
     */
    setSuggestions(suggestions) {
        this.suggestions = suggestions.slice(0, this.maxSuggestions);
        if (this.suggestions.length > 0) {
            this.renderSuggestions();
            this.show();
        } else {
            this.hide();
        }
    }

    /**
     * Gets current suggestions
     */
    getSuggestions() {
        return [...this.suggestions];
    }

    /**
     * Destroys the component and cleans up event listeners
     */
    destroy() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Remove event listeners
        this.searchInput.removeEventListener('input', this.handleInput);
        this.searchInput.removeEventListener('keydown', this.handleKeydown);
        this.searchInput.removeEventListener('focus', this.handleFocus);
        this.searchInput.removeEventListener('blur', this.handleBlur);

        this.clear();
    }
}

export default SearchSuggestions;