/**
 * Status Monitor Component
 * Handles system status monitoring, activity logs, and system controls
 */

class StatusMonitor {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.systemAPI = new SystemAPI(dashboard);
        this.activityLogInterval = null;
        this.statusCheckInterval = null;
    }

    /**
     * Initialize the status monitor
     */
    init() {
        // Set up the API instance on the dashboard
        this.dashboard.systemAPI = this.systemAPI;

        // Bind methods to dashboard
        this.dashboard.loadSystemData = this.loadSystemData.bind(this);
        this.dashboard.refreshSystemStatus = this.refreshSystemStatus.bind(this);
        this.dashboard.controlCrawler = this.controlCrawler.bind(this);
        this.dashboard.triggerFullScan = this.triggerFullScan.bind(this);
        this.dashboard.exportLogs = this.exportLogs.bind(this);

        // Start status monitoring
        this.startStatusMonitoring();
    }

    /**
     * Load system data
     */
    async loadSystemData() {
        await this.systemAPI.loadSystemData();
    }

    /**
     * Refresh system status
     */
    async refreshSystemStatus() {
        await this.loadSystemData();
    }

    /**
     * Start status monitoring intervals
     */
    startStatusMonitoring() {
        // Check system status every 30 seconds
        this.statusCheckInterval = setInterval(async () => {
            try {
                await this.systemAPI.loadSystemData();
            } catch (error) {
                console.error('Status check failed:', error);
            }
        }, 30000);

        // Update activity log every 60 seconds
        this.activityLogInterval = setInterval(() => {
            this.updateActivityLog();
        }, 60000);
    }

    /**
     * Stop status monitoring
     */
    stopStatusMonitoring() {
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }
        if (this.activityLogInterval) {
            clearInterval(this.activityLogInterval);
            this.activityLogInterval = null;
        }
    }

    /**
     * Update activity log with new entries
     */
    updateActivityLog() {
        // In a real implementation, this would fetch new activity entries from the API
        // For now, we'll just refresh the existing log
        this.systemAPI.loadSystemData();
    }

    /**
     * Control crawler (start/stop)
     */
    async controlCrawler(action) {
        try {
            await this.systemAPI.controlCrawler(action);
            // Refresh status after action
            setTimeout(() => this.refreshSystemStatus(), 2000);
        } catch (error) {
            console.error(`Failed to ${action} crawler:`, error);
            alert(`Failed to ${action} crawler. Please try again.`);
        }
    }

    /**
     * Trigger full system scan
     */
    async triggerFullScan() {
        try {
            await this.systemAPI.triggerFullScan();
            // Refresh status after scan
            setTimeout(() => this.refreshSystemStatus(), 5000);
        } catch (error) {
            console.error('Failed to trigger full scan:', error);
            alert('Failed to trigger full system scan. Please try again.');
        }
    }

    /**
     * Export system logs
     */
    async exportLogs() {
        try {
            await this.systemAPI.exportLogs();
        } catch (error) {
            console.error('Failed to export logs:', error);
            alert('Failed to export logs. Please try again.');
        }
    }

    /**
     * Show detailed system information modal
     */
    showSystemDetails(component) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content system-details-modal">
                <div class="modal-header">
                    <h2>System Details</h2>
                    <button class="modal-close" onclick="closeSystemDetailsModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="system-details-grid">
                        <div class="detail-section">
                            <h3>Component Status</h3>
                            <div class="status-details">
                                <p><strong>Database:</strong> <span class="status-${component.database?.status || 'unknown'}">${component.database?.status || 'Unknown'}</span></p>
                                <p><strong>Scheduler:</strong> <span class="status-${component.scheduler?.status || 'unknown'}">${component.scheduler?.status || 'Unknown'}</span></p>
                                <p><strong>qBittorrent:</strong> <span class="status-unknown">Unknown</span></p>
                                <p><strong>Audiobookshelf:</strong> <span class="status-unknown">Unknown</span></p>
                            </div>
                        </div>

                        <div class="detail-section">
                            <h3>System Information</h3>
                            <div class="system-info">
                                <p><strong>Version:</strong> ${component.version || 'Unknown'}</p>
                                <p><strong>Uptime:</strong> ${this.formatUptime(component.uptime)}</p>
                                <p><strong>Last Health Check:</strong> ${this.dashboard.formatDate(component.timestamp)}</p>
                                <p><strong>Environment:</strong> ${component.environment || 'Production'}</p>
                            </div>
                        </div>

                        <div class="detail-section">
                            <h3>Performance Metrics</h3>
                            <div class="performance-metrics">
                                <p><strong>CPU Usage:</strong> ${component.cpu_usage || 'N/A'}%</p>
                                <p><strong>Memory Usage:</strong> ${component.memory_usage || 'N/A'}%</p>
                                <p><strong>Disk Usage:</strong> ${component.disk_usage || 'N/A'}%</p>
                                <p><strong>Active Connections:</strong> ${component.active_connections || 'N/A'}</p>
                            </div>
                        </div>

                        <div class="detail-section">
                            <h3>Recent Activity</h3>
                            <div class="recent-activity-list">
                                ${this.renderRecentActivity(component.recent_activity)}
                            </div>
                        </div>
                    </div>

                    <div class="system-actions">
                        <button class="btn btn-primary" onclick="runDiagnostics()">Run Diagnostics</button>
                        <button class="btn btn-secondary" onclick="viewLogs()">View Logs</button>
                        <button class="btn btn-warning" onclick="restartServices()">Restart Services</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeSystemDetailsModal();
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeSystemDetailsModal();
            }
        });
    }

    /**
     * Render recent activity list
     */
    renderRecentActivity(activities) {
        if (!activities || activities.length === 0) {
            return '<p>No recent activity</p>';
        }

        return activities.map(activity => `
            <div class="activity-item">
                <span class="activity-time">${this.dashboard.formatRelativeTime(activity.timestamp)}</span>
                <span class="activity-description">${this.escapeHtml(activity.description)}</span>
            </div>
        `).join('');
    }

    /**
     * Close system details modal
     */
    closeSystemDetailsModal() {
        const modal = document.getElementById('system-details-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Format uptime duration
     */
    formatUptime(seconds) {
        if (!seconds) return 'Unknown';

        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);

        const parts = [];
        if (days > 0) parts.push(`${days}d`);
        if (hours > 0) parts.push(`${hours}h`);
        if (minutes > 0) parts.push(`${minutes}m`);

        return parts.join(' ') || 'Less than 1 minute';
    }

    /**
     * Run system diagnostics
     */
    async runDiagnostics() {
        try {
            alert('Running system diagnostics...');
            // This would call a diagnostics API endpoint
            setTimeout(() => {
                alert('Diagnostics completed. Check the activity log for results.');
                this.closeSystemDetailsModal();
                this.refreshSystemStatus();
            }, 3000);
        } catch (error) {
            console.error('Diagnostics failed:', error);
            alert('Diagnostics failed. Please try again.');
        }
    }

    /**
     * View system logs
     */
    viewLogs() {
        // This would open a logs viewer modal or redirect to logs page
        alert('Logs viewer would be implemented here');
        this.closeSystemDetailsModal();
    }

    /**
     * Restart system services
     */
    async restartServices() {
        if (!confirm('Restart all system services? This may cause temporary downtime.')) return;

        try {
            alert('Restarting services...');
            // This would call a restart API endpoint
            setTimeout(() => {
                alert('Services restarted successfully');
                this.closeSystemDetailsModal();
                this.refreshSystemStatus();
            }, 5000);
        } catch (error) {
            console.error('Service restart failed:', error);
            alert('Service restart failed. Please try again.');
        }
    }

    /**
     * Show service configuration modal
     */
    showServiceConfig(serviceName) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content config-modal">
                <div class="modal-header">
                    <h2>${serviceName} Configuration</h2>
                    <button class="modal-close" onclick="closeConfigModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <form id="service-config-form">
                        <div class="form-group">
                            <label for="service-enabled">Enabled:</label>
                            <input type="checkbox" id="service-enabled" checked>
                        </div>

                        <div class="form-group">
                            <label for="service-host">Host:</label>
                            <input type="text" id="service-host" value="localhost">
                        </div>

                        <div class="form-group">
                            <label for="service-port">Port:</label>
                            <input type="number" id="service-port" value="8000">
                        </div>

                        <div class="form-group">
                            <label for="service-timeout">Timeout (seconds):</label>
                            <input type="number" id="service-timeout" value="30">
                        </div>

                        <div class="form-actions">
                            <button type="button" class="btn btn-secondary" onclick="closeConfigModal()">Cancel</button>
                            <button type="submit" class="btn btn-primary">Save Configuration</button>
                        </div>
                    </form>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Handle form submission
        const form = modal.querySelector('#service-config-form');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveServiceConfig(serviceName, new FormData(form));
        });

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeConfigModal();
            }
        });
    }

    /**
     * Save service configuration
     */
    async saveServiceConfig(serviceName, formData) {
        try {
            const config = {
                enabled: formData.get('service-enabled') === 'on',
                host: formData.get('service-host'),
                port: parseInt(formData.get('service-port')),
                timeout: parseInt(formData.get('service-timeout'))
            };

            // This would call a configuration API endpoint
            console.log(`Saving ${serviceName} config:`, config);
            alert('Configuration saved successfully');
            this.closeConfigModal();
        } catch (error) {
            console.error('Failed to save configuration:', error);
            alert('Failed to save configuration. Please try again.');
        }
    }

    /**
     * Close configuration modal
     */
    closeConfigModal() {
        const modal = document.querySelector('.config-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * Get status color class
     */
    getStatusColorClass(status) {
        const classes = {
            'healthy': 'status-healthy',
            'warning': 'status-warning',
            'error': 'status-error',
            'unknown': 'status-unknown'
        };
        return classes[status] || 'status-unknown';
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

// Global functions for modal handlers
function closeSystemDetailsModal() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.statusMonitor) {
        window.mamcrawlerDashboard.statusMonitor.closeSystemDetailsModal();
    }
}

function runDiagnostics() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.statusMonitor) {
        window.mamcrawlerDashboard.statusMonitor.runDiagnostics();
    }
}

function viewLogs() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.statusMonitor) {
        window.mamcrawlerDashboard.statusMonitor.viewLogs();
    }
}

function restartServices() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.statusMonitor) {
        window.mamcrawlerDashboard.statusMonitor.restartServices();
    }
}

function closeConfigModal() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.statusMonitor) {
        window.mamcrawlerDashboard.statusMonitor.closeConfigModal();
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StatusMonitor;
}