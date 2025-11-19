/**
 * Logs Service
 * Handles log streaming, filtering, and management
 */

class LogsService {
    constructor() {
        this.baseUrl = '/api';
        this.logBuffer = [];
        this.maxBufferSize = 1000;
        this.filters = {
            level: 'all',
            source: 'all',
            search: ''
        };
        this.isStreaming = false;
        this.eventSource = null;
    }

    /**
     * Make API request for logs
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<Object>} API response
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            return data;
        } catch (error) {
            console.error(`Logs API request failed for ${endpoint}:`, error);
            throw error;
        }
    }

    /**
     * Get recent logs
     * @param {Object} options - Query options
     * @returns {Promise<Array>} Recent log entries
     */
    async getRecentLogs(options = {}) {
        const params = new URLSearchParams({
            limit: options.limit || 100,
            level: this.filters.level,
            source: this.filters.source,
            search: this.filters.search,
            ...options
        });

        const response = await this.request(`/logs/recent?${params}`);
        return StatusUtils.isValidApiResponse(response) ? response.data : [];
    }

    /**
     * Get logs by time range
     * @param {Date} startTime - Start time
     * @param {Date} endTime - End time
     * @param {Object} options - Query options
     * @returns {Promise<Array>} Log entries in time range
     */
    async getLogsByTimeRange(startTime, endTime, options = {}) {
        const params = new URLSearchParams({
            start: startTime.toISOString(),
            end: endTime.toISOString(),
            level: this.filters.level,
            source: this.filters.source,
            search: this.filters.search,
            ...options
        });

        const response = await this.request(`/logs/range?${params}`);
        return StatusUtils.isValidApiResponse(response) ? response.data : [];
    }

    /**
     * Search logs
     * @param {string} query - Search query
     * @param {Object} options - Search options
     * @returns {Promise<Array>} Matching log entries
     */
    async searchLogs(query, options = {}) {
        const params = new URLSearchParams({
            q: query,
            limit: options.limit || 100,
            level: this.filters.level,
            source: this.filters.source,
            ...options
        });

        const response = await this.request(`/logs/search?${params}`);
        return StatusUtils.isValidApiResponse(response) ? response.data : [];
    }

    /**
     * Start log streaming
     * @param {Object} options - Streaming options
     */
    startStreaming(options = {}) {
        if (this.isStreaming) {
            console.warn('Log streaming already active');
            return;
        }

        const params = new URLSearchParams({
            level: this.filters.level,
            source: this.filters.source,
            search: this.filters.search,
            ...options
        });

        const url = `${this.baseUrl.replace('http', 'ws')}/logs/stream?${params}`;

        try {
            this.eventSource = new EventSource(url);

            this.eventSource.onopen = () => {
                console.log('Log streaming connected');
                this.isStreaming = true;
                this.emit('streamingStarted');
            };

            this.eventSource.onmessage = (event) => {
                try {
                    const logEntry = JSON.parse(event.data);
                    this.addToBuffer(logEntry);
                    this.emit('logEntry', logEntry);
                } catch (error) {
                    console.error('Failed to parse log entry:', error, event.data);
                }
            };

            this.eventSource.onerror = (error) => {
                console.error('Log streaming error:', error);
                this.emit('streamingError', error);
                this.stopStreaming();
            };

        } catch (error) {
            console.error('Failed to start log streaming:', error);
            this.emit('streamingError', error);
        }
    }

    /**
     * Stop log streaming
     */
    stopStreaming() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.isStreaming = false;
        this.emit('streamingStopped');
    }

    /**
     * Add log entry to buffer
     * @param {Object} entry - Log entry
     */
    addToBuffer(entry) {
        this.logBuffer.push(entry);

        // Maintain buffer size
        if (this.logBuffer.length > this.maxBufferSize) {
            this.logBuffer.shift();
        }
    }

    /**
     * Get buffered logs
     * @param {number} limit - Maximum number of entries
     * @returns {Array} Buffered log entries
     */
    getBufferedLogs(limit = null) {
        const logs = [...this.logBuffer];

        if (limit && limit > 0) {
            return logs.slice(-limit);
        }

        return logs;
    }

    /**
     * Clear log buffer
     */
    clearBuffer() {
        this.logBuffer = [];
    }

    /**
     * Set log filters
     * @param {Object} filters - Filter options
     */
    setFilters(filters) {
        this.filters = { ...this.filters, ...filters };

        // Restart streaming if active
        if (this.isStreaming) {
            this.stopStreaming();
            this.startStreaming();
        }

        this.emit('filtersChanged', this.filters);
    }

    /**
     * Get current filters
     * @returns {Object} Current filters
     */
    getFilters() {
        return { ...this.filters };
    }

    /**
     * Get available log levels
     * @returns {Promise<Array>} Available log levels
     */
    async getLogLevels() {
        const response = await this.request('/logs/levels');
        return StatusUtils.isValidApiResponse(response) ? response.data : ['debug', 'info', 'warning', 'error'];
    }

    /**
     * Get available log sources
     * @returns {Promise<Array>} Available log sources
     */
    async getLogSources() {
        const response = await this.request('/logs/sources');
        return StatusUtils.isValidApiResponse(response) ? response.data : ['crawler', 'downloader', 'system', 'api'];
    }

    /**
     * Get log statistics
     * @param {string} timeframe - Time period
     * @returns {Promise<Object>} Log statistics
     */
    async getLogStats(timeframe = '24h') {
        const response = await this.request(`/logs/stats?timeframe=${timeframe}`);
        return StatusUtils.isValidApiResponse(response) ? response.data : {};
    }

    /**
     * Export logs
     * @param {Object} options - Export options
     * @returns {Promise<Blob>} Log export blob
     */
    async exportLogs(options = {}) {
        const params = new URLSearchParams({
            format: options.format || 'json',
            level: this.filters.level,
            source: this.filters.source,
            search: this.filters.search,
            start: options.startTime ? options.startTime.toISOString() : '',
            end: options.endTime ? options.endTime.toISOString() : '',
            ...options
        });

        const response = await fetch(`${this.baseUrl}/logs/export?${params}`, {
            method: 'GET',
            headers: {
                'Accept': options.format === 'csv' ? 'text/csv' : 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Export failed: ${response.statusText}`);
        }

        return await response.blob();
    }

    /**
     * Clear logs on server
     * @param {Object} options - Clear options
     * @returns {Promise<Object>} Clear result
     */
    async clearLogs(options = {}) {
        const params = new URLSearchParams({
            level: options.level || 'all',
            source: options.source || 'all',
            before: options.before ? options.before.toISOString() : '',
            ...options
        });

        const response = await this.request(`/logs/clear?${params}`, {
            method: 'DELETE'
        });

        if (StatusUtils.isValidApiResponse(response)) {
            this.clearBuffer();
            this.emit('logsCleared', options);
        }

        return response;
    }

    /**
     * Get log entry details
     * @param {string} logId - Log entry ID
     * @returns {Promise<Object>} Log entry details
     */
    async getLogDetails(logId) {
        const response = await this.request(`/logs/${logId}`);
        return StatusUtils.isValidApiResponse(response) ? response.data : null;
    }

    /**
     * Get logs summary
     * @param {string} timeframe - Time period
     * @returns {Promise<Object>} Logs summary
     */
    async getLogsSummary(timeframe = '24h') {
        const response = await this.request(`/logs/summary?timeframe=${timeframe}`);
        return StatusUtils.isValidApiResponse(response) ? response.data : {};
    }

    /**
     * Subscribe to log events
     * @param {string} event - Event name
     * @param {Function} callback - Event callback
     */
    on(event, callback) {
        if (!this.eventListeners) {
            this.eventListeners = {};
        }

        if (!this.eventListeners[event]) {
            this.eventListeners[event] = [];
        }

        this.eventListeners[event].push(callback);
    }

    /**
     * Unsubscribe from log events
     * @param {string} event - Event name
     * @param {Function} callback - Event callback
     */
    off(event, callback) {
        if (this.eventListeners && this.eventListeners[event]) {
            const index = this.eventListeners[event].indexOf(callback);
            if (index > -1) {
                this.eventListeners[event].splice(index, 1);
            }
        }
    }

    /**
     * Emit log event
     * @param {string} event - Event name
     * @param {*} data - Event data
     */
    emit(event, data) {
        if (this.eventListeners && this.eventListeners[event]) {
            this.eventListeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in log event callback for ${event}:`, error);
                }
            });
        }
    }

    /**
     * Get streaming status
     * @returns {boolean} Whether streaming is active
     */
    isStreamingActive() {
        return this.isStreaming;
    }

    /**
     * Get buffer statistics
     * @returns {Object} Buffer stats
     */
    getBufferStats() {
        return {
            size: this.logBuffer.length,
            maxSize: this.maxBufferSize,
            isFull: this.logBuffer.length >= this.maxBufferSize
        };
    }

    /**
     * Set maximum buffer size
     * @param {number} size - Maximum buffer size
     */
    setMaxBufferSize(size) {
        this.maxBufferSize = size;

        // Trim buffer if needed
        if (this.logBuffer.length > this.maxBufferSize) {
            this.logBuffer = this.logBuffer.slice(-this.maxBufferSize);
        }
    }

    /**
     * Filter buffered logs
     * @param {Function} filterFn - Filter function
     * @returns {Array} Filtered logs
     */
    filterBufferedLogs(filterFn) {
        return this.logBuffer.filter(filterFn);
    }

    /**
     * Search buffered logs
     * @param {string} query - Search query
     * @returns {Array} Matching logs
     */
    searchBufferedLogs(query) {
        if (!query) return this.logBuffer;

        const lowerQuery = query.toLowerCase();
        return this.logBuffer.filter(entry =>
            entry.message && entry.message.toLowerCase().includes(lowerQuery) ||
            entry.source && entry.source.toLowerCase().includes(lowerQuery) ||
            entry.level && entry.level.toLowerCase().includes(lowerQuery)
        );
    }

    /**
     * Destroy service and clean up resources
     */
    destroy() {
        this.stopStreaming();
        this.clearBuffer();
        this.eventListeners = {};
    }
}