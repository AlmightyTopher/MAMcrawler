/**
 * Status Utilities
 * Functions for parsing, formatting, and manipulating status data
 */

class StatusUtils {
    /**
     * Get status color class based on status value
     * @param {string} status - Status string
     * @returns {string} CSS class name
     */
    static getStatusColorClass(status) {
        if (!status) return 'unknown';

        const statusMap = {
            'healthy': 'healthy',
            'running': 'healthy',
            'completed': 'healthy',
            'success': 'healthy',
            'active': 'healthy',
            'online': 'healthy',
            'connected': 'healthy',

            'warning': 'warning',
            'degraded': 'warning',
            'paused': 'warning',
            'retrying': 'warning',
            'queued': 'warning',

            'error': 'error',
            'failed': 'error',
            'stopped': 'error',
            'offline': 'error',
            'disconnected': 'error',
            'unhealthy': 'error',

            'unknown': 'unknown',
            'pending': 'unknown'
        };

        return statusMap[status.toLowerCase()] || 'unknown';
    }

    /**
     * Get status icon based on status value
     * @param {string} status - Status string
     * @returns {string} Emoji icon
     */
    static getStatusIcon(status) {
        if (!status) return '❓';

        const iconMap = {
            'healthy': '✅',
            'running': '▶️',
            'completed': '✅',
            'success': '✅',
            'active': '🟢',
            'online': '🟢',
            'connected': '🔗',

            'warning': '⚠️',
            'degraded': '🟡',
            'paused': '⏸️',
            'retrying': '🔄',
            'queued': '⏳',

            'error': '❌',
            'failed': '❌',
            'stopped': '⏹️',
            'offline': '🔴',
            'disconnected': '🔌',
            'unhealthy': '🔴',

            'unknown': '❓',
            'pending': '⏳'
        };

        return iconMap[status.toLowerCase()] || '❓';
    }

    /**
     * Format status text for display
     * @param {string} status - Raw status string
     * @returns {string} Formatted status text
     */
    static formatStatusText(status) {
        if (!status) return 'Unknown';

        return status.charAt(0).toUpperCase() + status.slice(1).toLowerCase();
    }

    /**
     * Get progress percentage from current and total values
     * @param {number} current - Current value
     * @param {number} total - Total value
     * @returns {number} Progress percentage (0-100)
     */
    static getProgressPercentage(current, total) {
        if (!total || total <= 0) return 0;
        if (!current || current < 0) return 0;

        return Math.min((current / total) * 100, 100);
    }

    /**
     * Format progress text
     * @param {number} current - Current value
     * @param {number} total - Total value
     * @param {boolean} showPercentage - Whether to include percentage
     * @returns {string} Formatted progress text
     */
    static formatProgressText(current, total, showPercentage = true) {
        const percentage = this.getProgressPercentage(current, total);

        if (showPercentage) {
            return `${current || 0} / ${total || 0} (${percentage.toFixed(1)}%)`;
        }

        return `${current || 0} / ${total || 0}`;
    }

    /**
     * Determine overall system status from component statuses
     * @param {Object} components - Object with component statuses
     * @returns {string} Overall status
     */
    static getOverallStatus(components) {
        if (!components) return 'unknown';

        const statuses = Object.values(components);
        if (statuses.length === 0) return 'unknown';

        // Priority: error > warning > healthy > unknown
        if (statuses.some(s => this.getStatusColorClass(s) === 'error')) {
            return 'error';
        }
        if (statuses.some(s => this.getStatusColorClass(s) === 'warning')) {
            return 'warning';
        }
        if (statuses.every(s => this.getStatusColorClass(s) === 'healthy')) {
            return 'healthy';
        }

        return 'unknown';
    }

    /**
     * Parse log level from string
     * @param {string} level - Log level string
     * @returns {number} Log level priority (higher = more severe)
     */
    static parseLogLevel(level) {
        if (!level) return 0;

        const levelMap = {
            'debug': 1,
            'info': 2,
            'warning': 3,
            'warn': 3,
            'error': 4,
            'critical': 5,
            'fatal': 5
        };

        return levelMap[level.toLowerCase()] || 0;
    }

    /**
     * Check if log level should be shown based on filter
     * @param {string} entryLevel - Log entry level
     * @param {string} filterLevel - Filter level
     * @returns {boolean} Whether to show the entry
     */
    static shouldShowLogEntry(entryLevel, filterLevel) {
        if (filterLevel === 'all') return true;

        const entryPriority = this.parseLogLevel(entryLevel);
        const filterPriority = this.parseLogLevel(filterLevel);

        return entryPriority >= filterPriority;
    }

    /**
     * Format resource usage percentage
     * @param {number} used - Used amount
     * @param {number} total - Total amount
     * @returns {string} Formatted percentage string
     */
    static formatResourceUsage(used, total) {
        const percentage = this.getProgressPercentage(used, total);
        return `${percentage.toFixed(1)}%`;
    }

    /**
     * Get resource usage color class
     * @param {number} used - Used amount
     * @param {number} total - Total amount
     * @returns {string} Color class
     */
    static getResourceUsageColor(used, total) {
        const percentage = this.getProgressPercentage(used, total);

        if (percentage >= 90) return 'error';
        if (percentage >= 75) return 'warning';
        return 'healthy';
    }

    /**
     * Format system metrics for display
     * @param {Object} metrics - Raw metrics object
     * @returns {Object} Formatted metrics object
     */
    static formatSystemMetrics(metrics) {
        if (!metrics) return {};

        return {
            cpu: {
                usage: this.formatResourceUsage(metrics.cpu_used, 100),
                color: this.getResourceUsageColor(metrics.cpu_used, 100)
            },
            memory: {
                usage: this.formatResourceUsage(metrics.memory_used, metrics.memory_total),
                color: this.getResourceUsageColor(metrics.memory_used, metrics.memory_total),
                used: TimeUtils.formatFileSize(metrics.memory_used),
                total: TimeUtils.formatFileSize(metrics.memory_total)
            },
            disk: {
                usage: this.formatResourceUsage(metrics.disk_used, metrics.disk_total),
                color: this.getResourceUsageColor(metrics.disk_used, metrics.disk_total),
                used: TimeUtils.formatFileSize(metrics.disk_used),
                total: TimeUtils.formatFileSize(metrics.disk_total)
            },
            network: {
                upload: TimeUtils.formatTransferRate(metrics.network_upload_rate || 0),
                download: TimeUtils.formatTransferRate(metrics.network_download_rate || 0)
            }
        };
    }

    /**
     * Parse download status from API response
     * @param {Object} download - Download object from API
     * @returns {Object} Parsed download status
     */
    static parseDownloadStatus(download) {
        return {
            id: download.id,
            title: download.title || 'Unknown',
            status: download.status || 'unknown',
            progress: download.progress || 0,
            size: download.size || 0,
            downloaded: download.downloaded || 0,
            speed: download.speed || 0,
            eta: download.eta || null,
            sources: download.sources || [],
            addedDate: download.added_date,
            completedDate: download.completed_date
        };
    }

    /**
     * Get download status color
     * @param {string} status - Download status
     * @returns {string} Color class
     */
    static getDownloadStatusColor(status) {
        switch (status?.toLowerCase()) {
            case 'downloading':
            case 'downloading_metadata':
                return 'healthy';
            case 'queued':
            case 'stalled':
                return 'warning';
            case 'completed':
                return 'healthy';
            case 'failed':
            case 'error':
                return 'error';
            case 'paused':
                return 'warning';
            default:
                return 'unknown';
        }
    }

    /**
     * Format crawler statistics
     * @param {Object} stats - Raw crawler stats
     * @returns {Object} Formatted stats
     */
    static formatCrawlerStats(stats) {
        if (!stats) return {};

        return {
            booksDiscovered: stats.books_discovered || 0,
            booksProcessed: stats.books_processed || 0,
            booksDownloaded: stats.books_downloaded || 0,
            activeSources: stats.active_sources || 0,
            totalSources: stats.total_sources || 0,
            averageSpeed: stats.average_speed || 0,
            uptime: stats.uptime || 0,
            lastActivity: stats.last_activity
        };
    }

    /**
     * Calculate crawler efficiency metrics
     * @param {Object} stats - Crawler stats
     * @returns {Object} Efficiency metrics
     */
    static calculateCrawlerEfficiency(stats) {
        if (!stats) return {};

        const processed = stats.books_processed || 0;
        const discovered = stats.books_discovered || 0;
        const downloaded = stats.books_downloaded || 0;

        return {
            discoveryRate: discovered > 0 ? (processed / discovered * 100) : 0,
            downloadRate: processed > 0 ? (downloaded / processed * 100) : 0,
            overallEfficiency: discovered > 0 ? (downloaded / discovered * 100) : 0
        };
    }

    /**
     * Validate API response structure
     * @param {Object} response - API response object
     * @returns {boolean} Whether response is valid
     */
    static isValidApiResponse(response) {
        return response &&
               typeof response === 'object' &&
               'success' in response &&
               'data' in response;
    }

    /**
     * Extract error message from API response
     * @param {Object} response - API response object
     * @returns {string} Error message
     */
    static getApiErrorMessage(response) {
        if (!response) return 'Unknown error';

        if (response.error) return response.error;
        if (response.message) return response.message;
        if (response.detail) return response.detail;

        return 'An error occurred';
    }

    /**
     * Create a standardized status object
     * @param {string} status - Status value
     * @param {string} message - Status message
     * @param {Object} data - Additional data
     * @returns {Object} Standardized status object
     */
    static createStatusObject(status, message = '', data = {}) {
        return {
            status: status,
            message: message,
            data: data,
            timestamp: new Date().toISOString(),
            color: this.getStatusColorClass(status),
            icon: this.getStatusIcon(status)
        };
    }

    /**
     * Check if a value is within acceptable range
     * @param {number} value - Value to check
     * @param {number} min - Minimum acceptable value
     * @param {number} max - Maximum acceptable value
     * @returns {boolean} Whether value is in range
     */
    static isInRange(value, min, max) {
        return value >= min && value <= max;
    }

    /**
     * Get severity level for a metric
     * @param {number} value - Metric value
     * @param {Array} thresholds - Array of [min, max, severity] tuples
     * @returns {string} Severity level
     */
    static getSeverityLevel(value, thresholds) {
        for (const [min, max, severity] of thresholds) {
            if (this.isInRange(value, min, max)) {
                return severity;
            }
        }
        return 'unknown';
    }
}