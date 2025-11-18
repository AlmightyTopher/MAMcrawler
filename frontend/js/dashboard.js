/**
 * MAMcrawler Dashboard - Main Application Logic
 * Handles navigation, theme switching, data loading, and overall application state
 */

class MAMcrawlerDashboard {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000/api';
        this.apiKey = null;
        this.currentTab = 'library';
        this.refreshInterval = null;
        this.isLoading = false;

        // Initialize the dashboard
        this.init();
    }

    /**
     * Initialize the dashboard application
     */
    async init() {
        try {
            this.showLoading();

            // Load user preferences
            this.loadPreferences();

            // Setup event listeners
            this.setupEventListeners();

            // Initialize theme
            this.initializeTheme();

            // Try to connect to backend
            await this.testConnection();

            // Load initial data
            await this.loadDashboardData();

            // Setup auto-refresh
            this.setupAutoRefresh();

            this.hideLoading();

        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showError('Failed to initialize dashboard. Please check your backend connection.');
            this.hideLoading();
        }
    }

    /**
     * Test connection to the backend API
     */
    async testConnection() {
        try {
            const response = await fetch(`${this.apiBaseUrl.replace('/api', '')}/health`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            console.log('Backend connection successful');
        } catch (error) {
            console.warn('Backend connection failed:', error);
            throw error;
        }
    }

    /**
     * Load user preferences from localStorage
     */
    loadPreferences() {
        const theme = localStorage.getItem('mamcrawler-theme') || 'light';
        document.documentElement.setAttribute('data-theme', theme);

        const apiKey = localStorage.getItem('mamcrawler-api-key');
        if (apiKey) {
            this.apiKey = apiKey;
        }

        const refreshInterval = localStorage.getItem('mamcrawler-refresh-interval') || '30000';
        this.refreshInterval = parseInt(refreshInterval);
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Navigation tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = e.currentTarget.dataset.tab;
                this.switchTab(tabName);
            });
        });

        // Theme toggle
        document.getElementById('theme-toggle').addEventListener('click', () => {
            this.toggleTheme();
        });

        // Refresh button
        document.getElementById('refresh-btn').addEventListener('click', () => {
            this.refreshCurrentTab();
        });

        // Retry connection
        document.getElementById('retry-connection').addEventListener('click', async () => {
            this.hideError();
            await this.init();
        });

        // Search functionality
        const searchInput = document.getElementById('library-search');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.performSearch(e.target.value);
                }, 300);
            });
        }

        // Filters
        document.getElementById('status-filter')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('genre-filter')?.addEventListener('change', () => this.applyFilters());
        document.getElementById('clear-filters')?.addEventListener('click', () => this.clearFilters());

        // Sorting
        document.getElementById('library-sort')?.addEventListener('change', () => this.applySorting());

        // Pagination
        document.getElementById('prev-page')?.addEventListener('click', () => this.changePage(-1));
        document.getElementById('next-page')?.addEventListener('click', () => this.changePage(1));

        // System actions
        document.getElementById('refresh-system')?.addEventListener('click', () => this.refreshSystemStatus());
        document.getElementById('start-crawler')?.addEventListener('click', () => this.controlCrawler('start'));
        document.getElementById('stop-crawler')?.addEventListener('click', () => this.controlCrawler('stop'));
        document.getElementById('full-scan')?.addEventListener('click', () => this.triggerFullScan());
        document.getElementById('export-logs')?.addEventListener('click', () => this.exportLogs());

        // Stats refresh
        document.getElementById('refresh-stats')?.addEventListener('click', () => this.refreshStats());

        // Downloads refresh
        document.getElementById('refresh-downloads')?.addEventListener('click', () => this.refreshDownloads());
    }

    /**
     * Initialize theme based on user preference or system preference
     */
    initializeTheme() {
        const savedTheme = localStorage.getItem('mamcrawler-theme');
        const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        const theme = savedTheme || systemTheme;

        document.documentElement.setAttribute('data-theme', theme);
        this.updateThemeIcon(theme);
    }

    /**
     * Toggle between light and dark themes
     */
    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('mamcrawler-theme', newTheme);
        this.updateThemeIcon(newTheme);
    }

    /**
     * Update the theme toggle icon
     */
    updateThemeIcon(theme) {
        const icon = document.querySelector('.theme-icon');
        if (icon) {
            icon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    }

    /**
     * Switch between dashboard tabs
     */
    switchTab(tabName) {
        // Update navigation
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // Load tab-specific data
        this.loadTabData(tabName);
    }

    /**
     * Load data for a specific tab
     */
    async loadTabData(tabName) {
        switch (tabName) {
            case 'library':
                await this.loadLibraryData();
                break;
            case 'downloads':
                await this.loadDownloadsData();
                break;
            case 'stats':
                await this.loadStatsData();
                break;
            case 'system':
                await this.loadSystemData();
                break;
        }
    }

    /**
     * Load all dashboard data
     */
    async loadDashboardData() {
        await Promise.allSettled([
            this.loadLibraryData(),
            this.loadDownloadsData(),
            this.loadStatsData(),
            this.loadSystemData()
        ]);
    }

    /**
     * Setup auto-refresh functionality
     */
    setupAutoRefresh() {
        if (this.refreshInterval > 0) {
            setInterval(() => {
                if (!this.isLoading) {
                    this.refreshCurrentTab();
                }
            }, this.refreshInterval);
        }
    }

    /**
     * Refresh the currently active tab
     */
    async refreshCurrentTab() {
        await this.loadTabData(this.currentTab);
    }

    /**
     * Make authenticated API request
     */
    async apiRequest(endpoint, options = {}) {
        const url = `${this.apiBaseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.apiKey) {
            headers['Authorization'] = `Bearer ${this.apiKey}`;
        }

        const response = await fetch(url, {
            ...options,
            headers
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`API request failed: ${response.status} ${error}`);
        }

        return response.json();
    }

    /**
     * Show loading overlay
     */
    showLoading() {
        this.isLoading = true;
        document.getElementById('loading-overlay').classList.remove('hidden');
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        this.isLoading = false;
        document.getElementById('loading-overlay').classList.add('hidden');
    }

    /**
     * Show error message
     */
    showError(message) {
        const errorElement = document.getElementById('error-message');
        const errorText = errorElement.querySelector('.error-text p');
        errorText.textContent = message;
        errorElement.classList.remove('hidden');
    }

    /**
     * Hide error message
     */
    hideError() {
        document.getElementById('error-message').classList.add('hidden');
    }

    /**
     * Handle API errors gracefully
     */
    handleApiError(error, context) {
        console.error(`Error in ${context}:`, error);
        this.showError(`Failed to load ${context}. Please check your connection and try again.`);
    }

    /**
     * Utility function to format numbers
     */
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    /**
     * Utility function to format file sizes
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Utility function to format dates
     */
    formatDate(dateString) {
        if (!dateString) return 'Never';
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }

    /**
     * Utility function to format relative time
     */
    formatRelativeTime(dateString) {
        if (!dateString) return 'Never';

        const now = new Date();
        const date = new Date(dateString);
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }
}

// Initialize the dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mamcrawlerDashboard = new MAMcrawlerDashboard();
});

// Export for potential use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MAMcrawlerDashboard;
}