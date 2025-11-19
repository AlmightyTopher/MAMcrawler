/**
 * MAMcrawler Status Dashboard
 * Main controller for real-time status monitoring
 */

class StatusDashboard {
    constructor() {
        this.components = {};
        this.services = {};
        this.updateIntervals = {};
        this.isInitialized = false;
        this.lastUpdate = null;

        this.init();
    }

    async init() {
        try {
            console.log('Initializing Status Dashboard...');

            // Show loading overlay
            this.showLoading();

            // Initialize services
            await this.initializeServices();

            // Initialize components
            await this.initializeComponents();

            // Setup event listeners
            this.setupEventListeners();

            // Start real-time updates
            this.startRealTimeUpdates();

            // Initial data load
            await this.loadInitialData();

            this.isInitialized = true;
            this.hideLoading();

            console.log('Status Dashboard initialized successfully');

        } catch (error) {
            console.error('Failed to initialize Status Dashboard:', error);
            this.showError('Failed to initialize dashboard: ' + error.message);
        }
    }

    async initializeServices() {
        console.log('Initializing services...');

        // Initialize real-time service
        this.services.realtime = new RealtimeService();

        // Initialize metrics service
        this.services.metrics = new MetricsService();

        // Initialize logs service
        this.services.logs = new LogsService();

        console.log('Services initialized');
    }

    async initializeComponents() {
        console.log('Initializing components...');

        // Initialize system overview
        this.components.systemOverview = new SystemOverviewComponent('system-overview-content');

        // Initialize crawler monitor
        this.components.crawlerMonitor = new CrawlerMonitorComponent('crawler-status-content');

        // Initialize download tracker
        this.components.downloadTracker = new DownloadTrackerComponent('download-monitoring-content');

        // Initialize resource monitor
        this.components.resourceMonitor = new ResourceMonitorComponent('system-resources-content');

        // Initialize activity feed
        this.components.activityFeed = new ActivityFeedComponent('activity-feed-content');

        // Initialize performance charts
        this.components.performanceCharts = new PerformanceChartsComponent('performance-charts-content');

        console.log('Components initialized');
    }

    setupEventListeners() {
        console.log('Setting up event listeners...');

        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.manualRefresh());
        }

        // Retry connection
        const retryBtn = document.getElementById('retry-connection');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => this.retryConnection());
        }

        // Section-specific controls
        this.setupSectionControls();

        // Window visibility change
        document.addEventListener('visibilitychange', () => this.handleVisibilityChange());

        console.log('Event listeners setup complete');
    }

    setupSectionControls() {
        // System overview refresh
        const refreshOverview = document.getElementById('refresh-overview');
        if (refreshOverview) {
            refreshOverview.addEventListener('click', () => this.refreshSystemOverview());
        }

        // Crawler controls
        const startCrawler = document.getElementById('start-crawler');
        const stopCrawler = document.getElementById('stop-crawler');

        if (startCrawler) {
            startCrawler.addEventListener('click', () => this.startCrawler());
        }
        if (stopCrawler) {
            stopCrawler.addEventListener('click', () => this.stopCrawler());
        }

        // Downloads refresh
        const refreshDownloads = document.getElementById('refresh-downloads');
        if (refreshDownloads) {
            refreshDownloads.addEventListener('click', () => this.refreshDownloads());
        }

        // Resources refresh
        const refreshResources = document.getElementById('refresh-resources');
        if (refreshResources) {
            refreshResources.addEventListener('click', () => this.refreshResources());
        }

        // Charts refresh and timeframe change
        const refreshCharts = document.getElementById('refresh-charts');
        const chartTimeframe = document.getElementById('chart-timeframe');

        if (refreshCharts) {
            refreshCharts.addEventListener('click', () => this.refreshCharts());
        }
        if (chartTimeframe) {
            chartTimeframe.addEventListener('change', () => this.changeChartTimeframe());
        }

        // Activity feed controls
        const logLevelFilter = document.getElementById('log-level-filter');
        const clearLogs = document.getElementById('clear-logs');

        if (logLevelFilter) {
            logLevelFilter.addEventListener('change', () => this.filterLogs());
        }
        if (clearLogs) {
            clearLogs.addEventListener('click', () => this.clearLogs());
        }
    }

    startRealTimeUpdates() {
        console.log('Starting real-time updates...');

        // Connect to real-time service
        this.services.realtime.connect();

        // Setup periodic updates for different components
        this.updateIntervals.systemOverview = setInterval(() => {
            this.refreshSystemOverview();
        }, 30000); // 30 seconds

        this.updateIntervals.downloads = setInterval(() => {
            this.refreshDownloads();
        }, 10000); // 10 seconds

        this.updateIntervals.resources = setInterval(() => {
            this.refreshResources();
        }, 15000); // 15 seconds

        this.updateIntervals.logs = setInterval(() => {
            this.refreshLogs();
        }, 5000); // 5 seconds

        console.log('Real-time updates started');
    }

    async loadInitialData() {
        console.log('Loading initial data...');

        try {
            // Load all data in parallel
            await Promise.all([
                this.refreshSystemOverview(),
                this.refreshCrawlerStatus(),
                this.refreshDownloads(),
                this.refreshResources(),
                this.refreshLogs(),
                this.refreshCharts()
            ]);

            this.updateLastUpdated();
            console.log('Initial data loaded');

        } catch (error) {
            console.error('Failed to load initial data:', error);
            throw error;
        }
    }

    async refreshSystemOverview() {
        try {
            const data = await this.services.metrics.getSystemStats();
            await this.components.systemOverview.update(data);
        } catch (error) {
            console.error('Failed to refresh system overview:', error);
            this.components.systemOverview.showError(error.message);
        }
    }

    async refreshCrawlerStatus() {
        try {
            const [schedulerData, taskData] = await Promise.all([
                this.services.metrics.getSchedulerStatus(),
                this.services.metrics.getTaskStatus('MAM')
            ]);
            await this.components.crawlerMonitor.update(schedulerData, taskData);
        } catch (error) {
            console.error('Failed to refresh crawler status:', error);
            this.components.crawlerMonitor.showError(error.message);
        }
    }

    async refreshDownloads() {
        try {
            const data = await this.services.metrics.getDownloadStats();
            await this.components.downloadTracker.update(data);
        } catch (error) {
            console.error('Failed to refresh downloads:', error);
            this.components.downloadTracker.showError(error.message);
        }
    }

    async refreshResources() {
        try {
            const data = await this.services.metrics.getSystemHealth();
            await this.components.resourceMonitor.update(data);
        } catch (error) {
            console.error('Failed to refresh resources:', error);
            this.components.resourceMonitor.showError(error.message);
        }
    }

    async refreshLogs() {
        try {
            const data = await this.services.logs.getRecentLogs();
            await this.components.activityFeed.update(data);
        } catch (error) {
            console.error('Failed to refresh logs:', error);
            this.components.activityFeed.showError(error.message);
        }
    }

    async refreshCharts() {
        try {
            const timeframe = document.getElementById('chart-timeframe')?.value || '1h';
            const data = await this.services.metrics.getPerformanceData(timeframe);
            await this.components.performanceCharts.update(data, timeframe);
        } catch (error) {
            console.error('Failed to refresh charts:', error);
            this.components.performanceCharts.showError(error.message);
        }
    }

    async startCrawler() {
        try {
            const result = await this.services.metrics.triggerTask('MAM');
            if (result.success) {
                this.showNotification('Crawler started successfully', 'success');
                await this.refreshCrawlerStatus();
            } else {
                throw new Error(result.error || 'Failed to start crawler');
            }
        } catch (error) {
            console.error('Failed to start crawler:', error);
            this.showNotification('Failed to start crawler: ' + error.message, 'error');
        }
    }

    async stopCrawler() {
        try {
            const result = await this.services.metrics.pauseTask('MAM');
            if (result.success) {
                this.showNotification('Crawler stopped successfully', 'success');
                await this.refreshCrawlerStatus();
            } else {
                throw new Error(result.error || 'Failed to stop crawler');
            }
        } catch (error) {
            console.error('Failed to stop crawler:', error);
            this.showNotification('Failed to stop crawler: ' + error.message, 'error');
        }
    }

    async manualRefresh() {
        console.log('Manual refresh triggered');
        this.showLoading();

        try {
            await this.loadInitialData();
            this.showNotification('Dashboard refreshed successfully', 'success');
        } catch (error) {
            console.error('Manual refresh failed:', error);
            this.showNotification('Failed to refresh dashboard', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async retryConnection() {
        console.log('Retrying connection...');
        this.hideError();

        try {
            await this.services.realtime.reconnect();
            await this.manualRefresh();
        } catch (error) {
            console.error('Connection retry failed:', error);
            this.showError('Failed to reconnect: ' + error.message);
        }
    }

    filterLogs() {
        const level = document.getElementById('log-level-filter')?.value || 'all';
        this.components.activityFeed.filterByLevel(level);
    }

    clearLogs() {
        if (confirm('Are you sure you want to clear all logs?')) {
            this.components.activityFeed.clear();
        }
    }

    changeChartTimeframe() {
        this.refreshCharts();
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);

        // Save theme preference
        localStorage.setItem('theme', newTheme);

        // Update theme icon
        const themeIcon = document.querySelector('.theme-icon');
        if (themeIcon) {
            themeIcon.textContent = newTheme === 'dark' ? '☀️' : '🌙';
        }
    }

    handleVisibilityChange() {
        if (document.hidden) {
            // Pause updates when tab is not visible
            this.pauseUpdates();
        } else {
            // Resume updates when tab becomes visible
            this.resumeUpdates();
        }
    }

    pauseUpdates() {
        console.log('Pausing updates (tab hidden)');
        Object.values(this.updateIntervals).forEach(interval => {
            if (interval) clearInterval(interval);
        });
        this.updateIntervals = {};
    }

    resumeUpdates() {
        console.log('Resuming updates (tab visible)');
        this.startRealTimeUpdates();
    }

    updateLastUpdated() {
        this.lastUpdate = new Date();
        const lastUpdatedEl = document.getElementById('last-updated');
        if (lastUpdatedEl) {
            lastUpdatedEl.textContent = 'Updated: ' + this.lastUpdate.toLocaleTimeString();
        }
    }

    updateConnectionStatus(status, message = '') {
        const indicator = document.getElementById('connection-indicator');
        const text = document.getElementById('connection-text');

        if (indicator && text) {
            indicator.className = 'connection-dot ' + status;
            text.textContent = message || status.charAt(0).toUpperCase() + status.slice(1);
        }
    }

    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    showError(message) {
        const errorEl = document.getElementById('error-message');
        const errorText = errorEl?.querySelector('.error-text p');
        if (errorEl && errorText) {
            errorText.textContent = message;
            errorEl.classList.remove('hidden');
        }
    }

    hideError() {
        const errorEl = document.getElementById('error-message');
        if (errorEl) {
            errorEl.classList.add('hidden');
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-icon">${this.getNotificationIcon(type)}</span>
            <span class="notification-text">${message}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">×</button>
        `;

        // Add to page
        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    getNotificationIcon(type) {
        switch (type) {
            case 'success': return '✅';
            case 'error': return '❌';
            case 'warning': return '⚠️';
            default: return 'ℹ️';
        }
    }

    destroy() {
        console.log('Destroying Status Dashboard...');

        // Clear all intervals
        Object.values(this.updateIntervals).forEach(interval => {
            if (interval) clearInterval(interval);
        });

        // Disconnect real-time service
        if (this.services.realtime) {
            this.services.realtime.disconnect();
        }

        // Destroy components
        Object.values(this.components).forEach(component => {
            if (component && typeof component.destroy === 'function') {
                component.destroy();
            }
        });

        this.isInitialized = false;
        console.log('Status Dashboard destroyed');
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Load saved theme
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Update theme icon
    const themeIcon = document.querySelector('.theme-icon');
    if (themeIcon) {
        themeIcon.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
    }

    // Create dashboard instance
    window.statusDashboard = new StatusDashboard();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.statusDashboard) {
        window.statusDashboard.destroy();
    }
});