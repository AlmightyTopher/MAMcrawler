/**
 * System Overview Component
 * Displays overall system status and key metrics
 */

class SystemOverviewComponent {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container element with id '${containerId}' not found`);
        }

        this.data = null;
        this.isLoading = false;
    }

    /**
     * Update component with new data
     * @param {Object} data - System overview data
     */
    async update(data) {
        this.data = data;
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
                <div class="error-icon">⚠️</div>
                <h3>System Overview Unavailable</h3>
                <p>${message}</p>
                <button class="btn btn-secondary" onclick="window.statusDashboard.refreshSystemOverview()">
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

        if (!this.data) {
            this.renderEmpty();
            return;
        }

        this.container.innerHTML = `
            <div class="system-overview-cards">
                ${this.renderStatusCard()}
                ${this.renderUptimeCard()}
                ${this.renderActivityCard()}
                ${this.renderAlertsCard()}
            </div>
        `;
    }

    /**
     * Render loading state
     */
    renderLoading() {
        this.container.innerHTML = `
            <div class="system-overview-cards">
                <div class="overview-card skeleton-card">
                    <div class="skeleton-text"></div>
                    <div class="skeleton-text"></div>
                </div>
                <div class="overview-card skeleton-card">
                    <div class="skeleton-text"></div>
                    <div class="skeleton-text"></div>
                </div>
                <div class="overview-card skeleton-card">
                    <div class="skeleton-text"></div>
                    <div class="skeleton-text"></div>
                </div>
                <div class="overview-card skeleton-card">
                    <div class="skeleton-text"></div>
                    <div class="skeleton-text"></div>
                </div>
            </div>
        `;
    }

    /**
     * Render empty state
     */
    renderEmpty() {
        this.container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📊</div>
                <h3>No System Data Available</h3>
                <p>System overview information will appear here once data is available.</p>
            </div>
        `;
    }

    /**
     * Render overall system status card
     * @returns {string} HTML string
     */
    renderStatusCard() {
        const status = StatusUtils.getOverallStatus({
            crawler: this.data.crawler_status,
            downloader: this.data.downloader_status,
            database: this.data.database_status,
            system: this.data.system_health
        });

        const statusText = StatusUtils.formatStatusText(status);
        const statusColor = StatusUtils.getStatusColorClass(status);
        const statusIcon = StatusUtils.getStatusIcon(status);

        return `
            <div class="overview-card">
                <div class="overview-card-icon">${statusIcon}</div>
                <h4>System Status</h4>
                <div class="overview-card-value">${statusText}</div>
                <div class="overview-card-status status-${statusColor}">
                    ${statusText}
                </div>
            </div>
        `;
    }

    /**
     * Render system uptime card
     * @returns {string} HTML string
     */
    renderUptimeCard() {
        const uptime = this.data.uptime || 0;
        const uptimeFormatted = TimeUtils.formatUptime(uptime);

        return `
            <div class="overview-card">
                <div class="overview-card-icon">⏱️</div>
                <h4>System Uptime</h4>
                <div class="overview-card-value">${uptimeFormatted}</div>
                <div class="overview-card-status status-healthy">
                    Running
                </div>
            </div>
        `;
    }

    /**
     * Render recent activity card
     * @returns {string} HTML string
     */
    renderActivityCard() {
        const lastActivity = this.data.last_activity;
        const activityText = lastActivity ?
            TimeUtils.formatRelativeTime(new Date(lastActivity)) :
            'No recent activity';

        return `
            <div class="overview-card">
                <div class="overview-card-icon">⚡</div>
                <h4>Last Activity</h4>
                <div class="overview-card-value">${activityText}</div>
                <div class="overview-card-status status-info">
                    Active
                </div>
            </div>
        `;
    }

    /**
     * Render alerts card
     * @returns {string} HTML string
     */
    renderAlertsCard() {
        const alerts = this.data.alerts || [];
        const activeAlerts = alerts.filter(alert => alert.active).length;

        let alertStatus = 'healthy';
        let alertText = 'No alerts';

        if (activeAlerts > 0) {
            alertStatus = activeAlerts > 5 ? 'error' : 'warning';
            alertText = `${activeAlerts} active`;
        }

        return `
            <div class="overview-card">
                <div class="overview-card-icon">🚨</div>
                <h4>Active Alerts</h4>
                <div class="overview-card-value">${activeAlerts}</div>
                <div class="overview-card-status status-${alertStatus}">
                    ${alertText}
                </div>
            </div>
        `;
    }

    /**
     * Get component data
     * @returns {Object} Current data
     */
    getData() {
        return this.data;
    }

    /**
     * Check if component has data
     * @returns {boolean} Whether data is available
     */
    hasData() {
        return this.data !== null;
    }

    /**
     * Clear component data
     */
    clear() {
        this.data = null;
        this.render();
    }

    /**
     * Destroy component
     */
    destroy() {
        this.container.innerHTML = '';
        this.data = null;
    }
}