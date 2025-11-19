/**
 * Activity Feed Component
 * Displays real-time log streaming and activity monitoring
 */

class ActivityFeedComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container element with id '${containerId}' not found`);
        }

        this.entries = [];
        this.maxEntries = 100;
        this.autoScroll = true;
        this.isLoading = false;
        this.filters = {
            level: 'all',
            search: ''
        };
    }

    /**
     * Update component with new log data
     * @param {Array} data - Log entries array
     */
    async update(data) {
        if (Array.isArray(data)) {
            this.entries = data.slice(-this.maxEntries);
        } else if (data) {
            this.addEntry(data);
        }

        this.render();
        this.scrollToBottom();
    }

    /**
     * Add a single log entry
     * @param {Object} entry - Log entry
     */
    addEntry(entry) {
        this.entries.push(entry);

        // Maintain max entries
        if (this.entries.length > this.maxEntries) {
            this.entries.shift();
        }
    }

    /**
     * Filter entries by level
     * @param {string} level - Log level filter
     */
    filterByLevel(level) {
        this.filters.level = level;
        this.render();
    }

    /**
     * Search entries
     * @param {string} query - Search query
     */
    search(query) {
        this.filters.search = query.toLowerCase();
        this.render();
    }

    /**
     * Clear all entries
     */
    clear() {
        this.entries = [];
        this.render();
    }

    /**
     * Show loading state
     */
    showLoading() {
        this.isLoading = true;
        this.render();
    }

    /**
     * Hide loading state
     */
    hideLoading() {
        this.isLoading = false;
        this.render();
    }

    /**
     * Show error state
     * @param {string} message - Error message
     */
    showError(message) {
        this.container.innerHTML = `
            <div class="error-state">
                <div class="error-icon">📋</div>
                <h3>Activity Feed Unavailable</h3>
                <p>${message}</p>
                <button class="btn btn-secondary" onclick="window.statusDashboard.refreshLogs()">
                    Retry
                </button>
            </div>
        `;
    }

    /**
     * Render the component
     */
    render() {
        if (this.isLoading) {
            this.renderLoading();
            return;
        }

        const filteredEntries = this.getFilteredEntries();

        this.container.innerHTML = `
            <div class="activity-feed-content">
                <div class="activity-entries">
                    ${filteredEntries.length > 0 ?
                        filteredEntries.map(entry => this.renderEntry(entry)).join('') :
                        this.renderEmpty()
                    }
                </div>
            </div>
        `;
    }

    /**
     * Render loading state
     */
    renderLoading() {
        this.container.innerHTML = `
            <div class="activity-feed-content">
                <div class="activity-entries">
                    ${Array.from({length: 5}, () => `
                        <div class="activity-entry loading-skeleton">
                            <div class="skeleton-text" style="width: 80px;"></div>
                            <div class="skeleton-text" style="width: 200px;"></div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Render empty state
     * @returns {string} HTML string
     */
    renderEmpty() {
        return `
            <div class="empty-state">
                <div class="empty-icon">📝</div>
                <p>No activity entries found</p>
                <small>Activity logs will appear here as the system operates</small>
            </div>
        `;
    }

    /**
     * Render a single log entry
     * @param {Object} entry - Log entry
     * @returns {string} HTML string
     */
    renderEntry(entry) {
        const timestamp = TimeUtils.formatTimestamp(entry.timestamp, true);
        const level = entry.level || 'info';
        const levelClass = `activity-level-${level.toLowerCase()}`;
        const icon = this.getLogIcon(level);

        return `
            <div class="activity-entry" data-level="${level}" data-id="${entry.id || ''}">
                <div class="activity-timestamp" title="${TimeUtils.formatTimestamp(entry.timestamp)}">
                    ${timestamp}
                </div>
                <div class="activity-icon">
                    ${icon}
                </div>
                <div class="activity-content">
                    <div class="activity-message">
                        ${this.escapeHtml(entry.message || 'No message')}
                    </div>
                    <div class="activity-details">
                        <span class="activity-level ${levelClass}">${level.toUpperCase()}</span>
                        ${entry.source ? `<span>Source: ${this.escapeHtml(entry.source)}</span>` : ''}
                        ${entry.user ? `<span>User: ${this.escapeHtml(entry.user)}</span>` : ''}
                        ${entry.ip ? `<span>IP: ${entry.ip}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * Get filtered entries based on current filters
     * @returns {Array} Filtered entries
     */
    getFilteredEntries() {
        return this.entries.filter(entry => {
            // Level filter
            if (this.filters.level !== 'all' &&
                !StatusUtils.shouldShowLogEntry(entry.level, this.filters.level)) {
                return false;
            }

            // Search filter
            if (this.filters.search) {
                const searchText = `${entry.message} ${entry.source} ${entry.level}`.toLowerCase();
                if (!searchText.includes(this.filters.search)) {
                    return false;
                }
            }

            return true;
        });
    }

    /**
     * Get icon for log level
     * @param {string} level - Log level
     * @returns {string} Icon emoji
     */
    getLogIcon(level) {
        const icons = {
            'error': '❌',
            'warning': '⚠️',
            'warn': '⚠️',
            'info': 'ℹ️',
            'debug': '🔍',
            'success': '✅',
            'critical': '🚨',
            'fatal': '💀'
        };

        return icons[level?.toLowerCase()] || '📝';
    }

    /**
     * Escape HTML characters
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Scroll to bottom of feed
     */
    scrollToBottom() {
        if (this.autoScroll) {
            const feedContent = this.container.querySelector('.activity-feed-content');
            if (feedContent) {
                feedContent.scrollTop = feedContent.scrollHeight;
            }
        }
    }

    /**
     * Toggle auto-scroll
     * @param {boolean} enabled - Whether to enable auto-scroll
     */
    setAutoScroll(enabled) {
        this.autoScroll = enabled;
    }

    /**
     * Set maximum number of entries
     * @param {number} max - Maximum entries
     */
    setMaxEntries(max) {
        this.maxEntries = max;

        // Trim existing entries if needed
        if (this.entries.length > this.maxEntries) {
            this.entries = this.entries.slice(-this.maxEntries);
            this.render();
        }
    }

    /**
     * Get current entries
     * @returns {Array} Current entries
     */
    getEntries() {
        return [...this.entries];
    }

    /**
     * Get entry count
     * @returns {number} Number of entries
     */
    getEntryCount() {
        return this.entries.length;
    }

    /**
     * Get entries by level
     * @param {string} level - Log level
     * @returns {Array} Entries of specified level
     */
    getEntriesByLevel(level) {
        return this.entries.filter(entry => entry.level === level);
    }

    /**
     * Get entries by time range
     * @param {Date} startTime - Start time
     * @param {Date} endTime - End time
     * @returns {Array} Entries in time range
     */
    getEntriesByTimeRange(startTime, endTime) {
        return this.entries.filter(entry => {
            const entryTime = new Date(entry.timestamp);
            return entryTime >= startTime && entryTime <= endTime;
        });
    }

    /**
     * Export entries to JSON
     * @returns {string} JSON string
     */
    exportToJson() {
        return JSON.stringify(this.entries, null, 2);
    }

    /**
     * Export entries to CSV
     * @returns {string} CSV string
     */
    exportToCsv() {
        if (this.entries.length === 0) return '';

        const headers = ['timestamp', 'level', 'message', 'source', 'user', 'ip'];
        const csvRows = [headers.join(',')];

        this.entries.forEach(entry => {
            const row = headers.map(header => {
                const value = entry[header] || '';
                // Escape quotes and wrap in quotes if contains comma or quote
                if (value.includes(',') || value.includes('"')) {
                    return `"${value.replace(/"/g, '""')}"`;
                }
                return value;
            });
            csvRows.push(row.join(','));
        });

        return csvRows.join('\n');
    }

    /**
     * Destroy component
     */
    destroy() {
        this.container.innerHTML = '';
        this.entries = [];
        this.filters = {
            level: 'all',
            search: ''
        };
    }
}