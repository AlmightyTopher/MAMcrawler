/**
 * Metrics Service
 * Handles API calls for system metrics and status data
 */

class MetricsService {
    constructor() {
        this.baseUrl = '/api';
        this.cache = new Map();
        this.cacheTimeout = 30000; // 30 seconds
    }

    /**
     * Make API request with error handling
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
            console.error(`API request failed for ${endpoint}:`, error);
            throw error;
        }
    }

    /**
     * Get cached data or fetch from API
     * @param {string} key - Cache key
     * @param {Function} fetcher - Function to fetch data
     * @returns {Promise<Object>} Cached or fresh data
     */
    async getCached(key, fetcher) {
        const cached = this.cache.get(key);
        const now = Date.now();

        if (cached && (now - cached.timestamp) < this.cacheTimeout) {
            return cached.data;
        }

        const data = await fetcher();
        this.cache.set(key, { data, timestamp: now });
        return data;
    }

    /**
     * Clear cache for specific key or all
     * @param {string} key - Cache key to clear (optional)
     */
    clearCache(key = null) {
        if (key) {
            this.cache.delete(key);
        } else {
            this.cache.clear();
        }
    }

    /**
     * Get system statistics
     * @returns {Promise<Object>} System stats
     */
    async getSystemStats() {
        return this.getCached('systemStats', async () => {
            const response = await this.request('/system/stats');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get system health metrics
     * @returns {Promise<Object>} System health data
     */
    async getSystemHealth() {
        return this.getCached('systemHealth', async () => {
            const response = await this.request('/system/health');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get crawler status
     * @returns {Promise<Object>} Crawler status
     */
    async getCrawlerStatus() {
        return this.getCached('crawlerStatus', async () => {
            const response = await this.request('/crawler/status');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get scheduler status
     * @returns {Promise<Object>} Scheduler status
     */
    async getSchedulerStatus() {
        return this.getCached('schedulerStatus', async () => {
            const response = await this.request('/scheduler/status');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get task status
     * @param {string} taskName - Task name
     * @returns {Promise<Object>} Task status
     */
    async getTaskStatus(taskName) {
        return this.getCached(`taskStatus_${taskName}`, async () => {
            const response = await this.request(`/scheduler/tasks/${taskName}/status`);
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get download statistics
     * @returns {Promise<Object>} Download stats
     */
    async getDownloadStats() {
        return this.getCached('downloadStats', async () => {
            const response = await this.request('/downloads/stats');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get active downloads
     * @returns {Promise<Array>} Active downloads
     */
    async getActiveDownloads() {
        return this.getCached('activeDownloads', async () => {
            const response = await this.request('/downloads/active');
            return StatusUtils.isValidApiResponse(response) ? response.data : [];
        });
    }

    /**
     * Get performance data for charts
     * @param {string} timeframe - Time period (1h, 6h, 24h, 7d)
     * @returns {Promise<Object>} Performance data
     */
    async getPerformanceData(timeframe = '1h') {
        const cacheKey = `performanceData_${timeframe}`;
        return this.getCached(cacheKey, async () => {
            const response = await this.request(`/metrics/performance?timeframe=${timeframe}`);
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get system metrics history
     * @param {string} metric - Metric name (cpu, memory, disk, network)
     * @param {string} timeframe - Time period
     * @returns {Promise<Array>} Metric history data
     */
    async getMetricHistory(metric, timeframe = '1h') {
        const cacheKey = `metricHistory_${metric}_${timeframe}`;
        return this.getCached(cacheKey, async () => {
            const response = await this.request(`/metrics/${metric}/history?timeframe=${timeframe}`);
            return StatusUtils.isValidApiResponse(response) ? response.data : [];
        });
    }

    /**
     * Trigger a task
     * @param {string} taskName - Task name
     * @returns {Promise<Object>} Task trigger result
     */
    async triggerTask(taskName) {
        this.clearCache(`taskStatus_${taskName}`);
        this.clearCache('crawlerStatus');
        this.clearCache('schedulerStatus');

        const response = await this.request(`/scheduler/tasks/${taskName}/trigger`, {
            method: 'POST'
        });

        return StatusUtils.isValidApiResponse(response) ? response : { success: false, error: 'Invalid response' };
    }

    /**
     * Pause a task
     * @param {string} taskName - Task name
     * @returns {Promise<Object>} Task pause result
     */
    async pauseTask(taskName) {
        this.clearCache(`taskStatus_${taskName}`);
        this.clearCache('crawlerStatus');
        this.clearCache('schedulerStatus');

        const response = await this.request(`/scheduler/tasks/${taskName}/pause`, {
            method: 'POST'
        });

        return StatusUtils.isValidApiResponse(response) ? response : { success: false, error: 'Invalid response' };
    }

    /**
     * Resume a task
     * @param {string} taskName - Task name
     * @returns {Promise<Object>} Task resume result
     */
    async resumeTask(taskName) {
        this.clearCache(`taskStatus_${taskName}`);
        this.clearCache('crawlerStatus');
        this.clearCache('schedulerStatus');

        const response = await this.request(`/scheduler/tasks/${taskName}/resume`, {
            method: 'POST'
        });

        return StatusUtils.isValidApiResponse(response) ? response : { success: false, error: 'Invalid response' };
    }

    /**
     * Get system configuration
     * @returns {Promise<Object>} System configuration
     */
    async getSystemConfig() {
        return this.getCached('systemConfig', async () => {
            const response = await this.request('/system/config');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get database statistics
     * @returns {Promise<Object>} Database stats
     */
    async getDatabaseStats() {
        return this.getCached('databaseStats', async () => {
            const response = await this.request('/database/stats');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get VPN/proxy status
     * @returns {Promise<Object>} VPN/proxy status
     */
    async getVpnStatus() {
        return this.getCached('vpnStatus', async () => {
            const response = await this.request('/system/vpn-status');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Get recent errors and warnings
     * @param {number} limit - Number of items to retrieve
     * @returns {Promise<Array>} Recent errors
     */
    async getRecentErrors(limit = 10) {
        return this.getCached(`recentErrors_${limit}`, async () => {
            const response = await this.request(`/system/errors?limit=${limit}`);
            return StatusUtils.isValidApiResponse(response) ? response.data : [];
        });
    }

    /**
     * Get system alerts
     * @returns {Promise<Array>} Active alerts
     */
    async getSystemAlerts() {
        return this.getCached('systemAlerts', async () => {
            const response = await this.request('/system/alerts');
            return StatusUtils.isValidApiResponse(response) ? response.data : [];
        });
    }

    /**
     * Clear system alerts
     * @returns {Promise<Object>} Clear result
     */
    async clearSystemAlerts() {
        this.clearCache('systemAlerts');

        const response = await this.request('/system/alerts', {
            method: 'DELETE'
        });

        return StatusUtils.isValidApiResponse(response) ? response : { success: false, error: 'Invalid response' };
    }

    /**
     * Get backup status
     * @returns {Promise<Object>} Backup status
     */
    async getBackupStatus() {
        return this.getCached('backupStatus', async () => {
            const response = await this.request('/system/backup-status');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Trigger system backup
     * @returns {Promise<Object>} Backup trigger result
     */
    async triggerBackup() {
        this.clearCache('backupStatus');

        const response = await this.request('/system/backup', {
            method: 'POST'
        });

        return StatusUtils.isValidApiResponse(response) ? response : { success: false, error: 'Invalid response' };
    }

    /**
     * Get system logs summary
     * @param {string} level - Log level filter
     * @param {number} hours - Hours to look back
     * @returns {Promise<Object>} Logs summary
     */
    async getLogsSummary(level = 'all', hours = 24) {
        const cacheKey = `logsSummary_${level}_${hours}`;
        return this.getCached(cacheKey, async () => {
            const response = await this.request(`/logs/summary?level=${level}&hours=${hours}`);
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Export system status report
     * @returns {Promise<Blob>} Status report blob
     */
    async exportStatusReport() {
        const response = await fetch(`${this.baseUrl}/system/export-status`, {
            method: 'GET',
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`Export failed: ${response.statusText}`);
        }

        return await response.blob();
    }

    /**
     * Test API connectivity
     * @returns {Promise<boolean>} Connection status
     */
    async testConnection() {
        try {
            await this.request('/system/ping');
            return true;
        } catch (error) {
            console.error('API connection test failed:', error);
            return false;
        }
    }

    /**
     * Get API version information
     * @returns {Promise<Object>} Version info
     */
    async getApiVersion() {
        return this.getCached('apiVersion', async () => {
            const response = await this.request('/system/version');
            return StatusUtils.isValidApiResponse(response) ? response.data : {};
        });
    }

    /**
     * Force refresh all cached data
     */
    refreshAll() {
        this.cache.clear();
    }

    /**
     * Set cache timeout
     * @param {number} timeout - Cache timeout in milliseconds
     */
    setCacheTimeout(timeout) {
        this.cacheTimeout = timeout;
    }

    /**
     * Get cache statistics
     * @returns {Object} Cache stats
     */
    getCacheStats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys()),
            timeout: this.cacheTimeout
        };
    }
}