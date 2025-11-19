/**
 * Monitoring Dashboard Component for MAMcrawler Admin Panel
 * Handles real-time monitoring and metrics display
 */

class MonitoringDashboard {
    constructor() {
        this.updateInterval = 30000; // 30 seconds
        this.intervalId = null;
        this.init();
    }

    /**
     * Initialize monitoring dashboard
     */
    init() {
        this.bindEvents();
        this.startRealtimeUpdates();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Refresh logs button
        const refreshBtn = document.getElementById('refresh-logs-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshLogs());
        }
    }

    /**
     * Start real-time updates
     */
    startRealtimeUpdates() {
        this.updateDashboard();
        this.intervalId = setInterval(() => this.updateDashboard(), this.updateInterval);
    }

    /**
     * Stop real-time updates
     */
    stopRealtimeUpdates() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    /**
     * Update dashboard data
     */
    async updateDashboard() {
        try {
            await Promise.all([
                this.updateSystemMetrics(),
                this.updateDownloadStats(),
                this.updateErrorLogs()
            ]);
        } catch (error) {
            console.error('Dashboard update error:', error);
        }
    }

    /**
     * Update system metrics
     */
    async updateSystemMetrics() {
        try {
            const metrics = await window.monitoringService.getSystemMetrics();
            if (metrics) {
                this.setMetricValue('cpu-usage', `${metrics.cpu_percent || 0}%`);
                this.setMetricValue('memory-usage', this.formatBytes(metrics.memory_used || 0));
                this.setMetricValue('disk-usage', this.formatBytes(metrics.disk_used || 0));
            }
        } catch (error) {
            console.error('Failed to update system metrics:', error);
        }
    }

    /**
     * Update download statistics
     */
    async updateDownloadStats() {
        try {
            const stats = await window.monitoringService.getDownloadStats();
            if (stats) {
                this.setMetricValue('queued-downloads', stats.queued || 0);
                this.setMetricValue('downloading-count', stats.downloading || 0);
                this.setMetricValue('completed-downloads', stats.completed || 0);
                this.setMetricValue('failed-downloads', stats.failed || 0);
            }
        } catch (error) {
            console.error('Failed to update download stats:', error);
        }
    }

    /**
     * Update error logs
     */
    async updateErrorLogs() {
        try {
            const logs = await window.monitoringService.getErrorLogs(50);
            if (logs) {
                const logsContent = logs.map(log =>
                    `[${new Date(log.timestamp).toLocaleString()}] ${log.level}: ${log.message}`
                ).join('\n');
                this.setLogsContent(logsContent || 'No recent errors');
            }
        } catch (error) {
            console.error('Failed to update error logs:', error);
            this.setLogsContent('Failed to load error logs');
        }
    }

    /**
     * Refresh logs manually
     */
    async refreshLogs() {
        const btn = document.getElementById('refresh-logs-btn');
        if (btn) {
            btn.disabled = true;
            btn.textContent = 'Refreshing...';
        }

        await this.updateErrorLogs();

        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Refresh Logs';
        }

        window.adminPanel.showToast('Logs refreshed', 'success');
    }

    /**
     * Set metric value in DOM
     */
    setMetricValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    /**
     * Set logs content
     */
    setLogsContent(content) {
        const logsElement = document.getElementById('error-logs-content');
        if (logsElement) {
            logsElement.textContent = content;
        }
    }

    /**
     * Format bytes to human readable
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /**
     * Get performance report
     */
    async getPerformanceReport(timeRange = '24h') {
        try {
            const report = await window.monitoringService.getPerformanceReport(timeRange);
            return report;
        } catch (error) {
            console.error('Failed to get performance report:', error);
            throw error;
        }
    }

    /**
     * Export monitoring data
     */
    async exportMonitoringData(type = 'all', format = 'json') {
        try {
            await window.monitoringService.exportMonitoringData(type, format);
            window.adminPanel.showToast('Monitoring data exported successfully', 'success');
        } catch (error) {
            console.error('Export error:', error);
            window.adminPanel.showToast('Failed to export monitoring data', 'error');
        }
    }

    /**
     * Get system alerts
     */
    async getSystemAlerts() {
        try {
            const alerts = await window.monitoringService.getSystemAlerts();
            return alerts;
        } catch (error) {
            console.error('Failed to get system alerts:', error);
            throw error;
        }
    }

    /**
     * Acknowledge alert
     */
    async acknowledgeAlert(alertId) {
        try {
            await window.monitoringService.acknowledgeAlert(alertId);
            window.adminPanel.showToast('Alert acknowledged', 'success');
        } catch (error) {
            console.error('Failed to acknowledge alert:', error);
            window.adminPanel.showToast('Failed to acknowledge alert', 'error');
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopRealtimeUpdates();
    }
}

// Create global instance
window.monitoringDashboard = new MonitoringDashboard();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.monitoringDashboard) {
        window.monitoringDashboard.cleanup();
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MonitoringDashboard;
}