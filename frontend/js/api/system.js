/**
 * System API Module
 * Handles all system-related API communications
 */

class SystemAPI {
    constructor(dashboard) {
        this.dashboard = dashboard;
    }

    /**
     * Get system statistics
     */
    async getSystemStats() {
        try {
            const response = await this.dashboard.apiRequest('/system/stats');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'system stats');
            throw error;
        }
    }

    /**
     * Get library health status
     */
    async getLibraryStatus() {
        try {
            const response = await this.dashboard.apiRequest('/system/library-status');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'library status');
            throw error;
        }
    }

    /**
     * Get download queue statistics
     */
    async getDownloadStats() {
        try {
            const response = await this.dashboard.apiRequest('/system/download-stats');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'download stats');
            throw error;
        }
    }

    /**
     * Get storage usage statistics
     */
    async getStorageUsage() {
        try {
            const response = await this.dashboard.apiRequest('/system/storage');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'storage usage');
            throw error;
        }
    }

    /**
     * Get API usage statistics
     */
    async getApiUsage() {
        try {
            const response = await this.dashboard.apiRequest('/system/api-usage');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'API usage');
            throw error;
        }
    }

    /**
     * Trigger full system scan
     */
    async triggerFullScan() {
        try {
            const response = await this.dashboard.apiRequest('/system/trigger-full-scan', {
                method: 'POST'
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'full system scan');
            throw error;
        }
    }

    /**
     * Get system configuration
     */
    async getConfiguration() {
        try {
            const response = await this.dashboard.apiRequest('/system/configuration');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'system configuration');
            throw error;
        }
    }

    /**
     * Export system logs
     */
    async exportLogs(lines = 500) {
        try {
            const response = await this.dashboard.apiRequest('/system/logs/export', {
                method: 'POST',
                body: JSON.stringify({ lines })
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'log export');
            throw error;
        }
    }

    /**
     * Get comprehensive health check
     */
    async getHealthCheck() {
        try {
            const response = await this.dashboard.apiRequest('/system/health');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'health check');
            throw error;
        }
    }

    /**
     * Load system data for the dashboard
     */
    async loadSystemData() {
        try {
            const [healthData, configData] = await Promise.allSettled([
                this.getHealthCheck(),
                this.getConfiguration()
            ]);

            if (healthData.status === 'fulfilled') {
                this.updateSystemStatusCards(healthData.value);
            }

            if (configData.status === 'fulfilled') {
                this.updateSystemConfig(configData.value);
            }

            // Load recent activity (mock data for now)
            this.loadRecentActivity();

            return {
                health: healthData.status === 'fulfilled' ? healthData.value : null,
                config: configData.status === 'fulfilled' ? configData.value : null
            };
        } catch (error) {
            console.error('Failed to load system data:', error);
        }
    }

    /**
     * Load stats data for the dashboard
     */
    async loadStatsData() {
        try {
            const [systemStats, libraryStatus, downloadStats, storageUsage] = await Promise.allSettled([
                this.getSystemStats(),
                this.getLibraryStatus(),
                this.getDownloadStats(),
                this.getStorageUsage()
            ]);

            if (systemStats.status === 'fulfilled') {
                this.updateSystemStats(systemStats.value);
            }

            if (libraryStatus.status === 'fulfilled') {
                this.updateLibraryStatus(libraryStatus.value);
            }

            if (downloadStats.status === 'fulfilled') {
                this.updateDownloadStats(downloadStats.value);
            }

            if (storageUsage.status === 'fulfilled') {
                this.updateStorageStats(storageUsage.value);
            }

            return {
                system: systemStats.status === 'fulfilled' ? systemStats.value : null,
                library: libraryStatus.status === 'fulfilled' ? libraryStatus.value : null,
                downloads: downloadStats.status === 'fulfilled' ? downloadStats.value : null,
                storage: storageUsage.status === 'fulfilled' ? storageUsage.value : null
            };
        } catch (error) {
            console.error('Failed to load stats data:', error);
        }
    }

    /**
     * Update system status cards
     */
    updateSystemStatusCards(healthData) {
        const components = healthData.components || {};

        // Update crawler status
        this.updateStatusCard('crawler-status', 'crawler-status-text', components.scheduler);

        // Update qBittorrent status
        this.updateStatusCard('qbittorrent-status', 'qbittorrent-status-text', { status: 'unknown' }); // Mock for now

        // Update Audiobookshelf status
        this.updateStatusCard('abs-status', 'abs-status-text', { status: 'unknown' }); // Mock for now

        // Update database status
        this.updateStatusCard('db-status', 'db-status-text', components.database);

        // Update details
        this.updateStatusDetails(components);
    }

    /**
     * Update individual status card
     */
    updateStatusCard(dotId, textId, component) {
        const dot = document.getElementById(dotId);
        const text = document.getElementById(textId);

        if (!dot || !text) return;

        let status = 'unknown';
        let statusText = 'Unknown';

        if (component) {
            if (component.status === 'ok' || component.status === 'healthy') {
                status = 'healthy';
                statusText = 'Healthy';
            } else if (component.status === 'error' || component.status === 'unhealthy') {
                status = 'error';
                statusText = 'Error';
            } else if (component.status === 'degraded') {
                status = 'warning';
                statusText = 'Warning';
            }
        }

        dot.className = `status-dot ${status}`;
        text.textContent = statusText;
    }

    /**
     * Update status details
     */
    updateStatusDetails(components) {
        // Scheduler details
        const scheduler = components.scheduler;
        if (scheduler) {
            document.getElementById('crawler-last-run').textContent =
                scheduler.last_run ? `Last run: ${this.dashboard.formatDate(scheduler.last_run)}` : 'Last run: Never';
            document.getElementById('crawler-next-run').textContent =
                scheduler.next_run ? `Next run: ${this.dashboard.formatDate(scheduler.next_run)}` : 'Next run: Scheduled';
        }

        // Database details
        const db = components.database;
        if (db) {
            document.getElementById('db-connections').textContent = 'Active connections: 1'; // Mock
            document.getElementById('db-size-system').textContent = 'Size: Unknown'; // Would need separate API call
        }
    }

    /**
     * Update system configuration display
     */
    updateSystemConfig(configData) {
        // This could be used to show configuration details in the UI
        console.log('System config:', configData);
    }

    /**
     * Update system statistics
     */
    updateSystemStats(stats) {
        // Library overview
        document.getElementById('total-books').textContent = this.dashboard.formatNumber(stats.books.grand_total);
        document.getElementById('active-books').textContent = this.dashboard.formatNumber(stats.books.total_active);
        document.getElementById('total-series').textContent = this.dashboard.formatNumber(stats.series.total);
        document.getElementById('total-authors').textContent = this.dashboard.formatNumber(stats.authors.total);

        // Download activity
        document.getElementById('total-downloads').textContent = this.dashboard.formatNumber(stats.downloads.total);
        document.getElementById('completed-downloads').textContent = this.dashboard.formatNumber(stats.downloads.completed);

        const successRate = stats.downloads.total > 0 ?
            Math.round((stats.downloads.completed / stats.downloads.total) * 100) : 0;
        document.getElementById('success-rate').textContent = `${successRate}%`;
    }

    /**
     * Update library status
     */
    updateLibraryStatus(libraryStatus) {
        const quality = libraryStatus.metadata_quality || {};

        document.getElementById('avg-completeness').textContent = `${quality.average_completeness_percent || 0}%`;
        document.getElementById('complete-books').textContent = this.dashboard.formatNumber(quality.books_100_percent || 0);
        document.getElementById('incomplete-books').textContent = this.dashboard.formatNumber(quality.books_below_80_percent || 0);
    }

    /**
     * Update download statistics
     */
    updateDownloadStats(downloadStats) {
        // Could be used for additional download stats display
        console.log('Download stats:', downloadStats);
    }

    /**
     * Update storage statistics
     */
    updateStorageStats(storageStats) {
        document.getElementById('estimated-storage').textContent = `${storageStats.estimated_audiobook_storage_gb || 0} GB`;
        document.getElementById('db-size').textContent = `${storageStats.database_size_mb || 0} MB`;
    }

    /**
     * Load recent activity (mock data for now)
     */
    loadRecentActivity() {
        const activities = [
            {
                time: '2 minutes ago',
                message: 'Download completed: "The Name of the Wind"',
                type: 'download'
            },
            {
                time: '15 minutes ago',
                message: 'Metadata updated for 5 books',
                type: 'metadata'
            },
            {
                time: '1 hour ago',
                message: 'Crawler scan completed',
                type: 'crawler'
            },
            {
                time: '2 hours ago',
                message: 'New book added: "The Wise Man\'s Fear"',
                type: 'library'
            },
            {
                time: '3 hours ago',
                message: 'Failed download retry scheduled',
                type: 'download'
            }
        ];

        this.renderActivityLog(activities);
    }

    /**
     * Render activity log
     */
    renderActivityLog(activities) {
        const container = document.getElementById('activity-log');

        if (!activities || activities.length === 0) {
            container.innerHTML = '<p>No recent activity</p>';
            return;
        }

        container.innerHTML = '';

        activities.forEach(activity => {
            const entry = document.createElement('div');
            entry.className = 'activity-entry';

            entry.innerHTML = `
                <div class="activity-time">${activity.time}</div>
                <div class="activity-content">
                    <div class="activity-message">${this.escapeHtml(activity.message)}</div>
                    <div class="activity-type">${activity.type}</div>
                </div>
            `;

            container.appendChild(entry);
        });
    }

    /**
     * Refresh system status
     */
    async refreshSystemStatus() {
        await this.loadSystemData();
    }

    /**
     * Refresh stats
     */
    async refreshStats() {
        await this.loadStatsData();
    }

    /**
     * Control crawler (start/stop)
     */
    async controlCrawler(action) {
        try {
            // This would need a specific API endpoint for crawler control
            // For now, just show a message
            alert(`${action.charAt(0).toUpperCase() + action.slice(1)} crawler command sent`);
        } catch (error) {
            this.dashboard.handleApiError(error, `crawler ${action}`);
        }
    }

    /**
     * Trigger full scan
     */
    async triggerFullScan() {
        try {
            const result = await this.triggerFullScan();
            alert('Full system scan triggered successfully');
            console.log('Full scan result:', result);
        } catch (error) {
            alert('Failed to trigger full system scan');
        }
    }

    /**
     * Export logs
     */
    async exportLogs() {
        try {
            const result = await this.exportLogs();
            // Create download link for logs
            const blob = new Blob([result.content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `mamcrawler_logs_${new Date().toISOString().split('T')[0]}.txt`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (error) {
            alert('Failed to export logs');
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SystemAPI;
}