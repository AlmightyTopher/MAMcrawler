/**
 * MAMcrawler Admin Panel Main Script
 * Handles authentication, navigation, and panel initialization
 */

class AdminPanel {
    constructor() {
        this.currentTab = 'dashboard';
        this.isAuthenticated = false;
        this.user = null;
        this.init();
    }

    /**
     * Initialize the admin panel
     */
    init() {
        this.bindEvents();
        this.checkAuthentication();
        this.setupPeriodicUpdates();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Login form
        const loginForm = document.getElementById('login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // Navigation tabs
        const navTabs = document.querySelectorAll('.nav-tab');
        navTabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e));
        });

        // Modal close buttons
        const modalCloses = document.querySelectorAll('.modal-close, .modal-cancel');
        modalCloses.forEach(close => {
            close.addEventListener('click', () => this.hideModals());
        });

        // Modal overlay click
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModals();
                }
            });
        });

        // Window resize for responsive design
        window.addEventListener('resize', () => this.handleResize());

        // Handle browser back/forward
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.tab) {
                this.switchTabByName(e.state.tab);
            }
        });
    }

    /**
     * Check if user is authenticated
     */
    async checkAuthentication() {
        try {
            this.showLoading(true);
            const isAuth = window.authService.isAuthenticated();

            if (isAuth) {
                // Validate session with server
                const isValid = await window.authService.validateSession();
                if (isValid) {
                    this.user = window.authService.getUser();
                    this.showAdminInterface();
                    this.initializeComponents();
                } else {
                    this.showLoginScreen();
                }
            } else {
                this.showLoginScreen();
            }
        } catch (error) {
            console.error('Authentication check error:', error);
            this.showLoginScreen();
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Handle login form submission
     */
    async handleLogin(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const credentials = {
            username: formData.get('username'),
            password: formData.get('password')
        };

        // Clear previous errors
        this.showLoginError('');

        try {
            this.showLoading(true);
            const result = await window.authService.login(credentials);

            if (result.success) {
                this.user = result.user;
                this.showAdminInterface();
                this.initializeComponents();

                // Update URL without triggering navigation
                history.replaceState({ tab: 'dashboard' }, '', '#dashboard');
            } else {
                this.showLoginError(result.error || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showLoginError('An error occurred during login');
        } finally {
            this.showLoading(false);
        }
    }

    /**
     * Handle logout
     */
    async handleLogout() {
        try {
            await window.authService.logout();
            this.user = null;
            this.showLoginScreen();
            history.replaceState({}, '', window.location.pathname);
        } catch (error) {
            console.error('Logout error:', error);
            // Force logout on client side
            window.authService.clearSession();
            this.user = null;
            this.showLoginScreen();
        }
    }

    /**
     * Show login screen
     */
    showLoginScreen() {
        document.getElementById('login-screen').style.display = 'flex';
        document.getElementById('admin-interface').style.display = 'none';
        this.isAuthenticated = false;
    }

    /**
     * Show admin interface
     */
    showAdminInterface() {
        document.getElementById('login-screen').style.display = 'none';
        document.getElementById('admin-interface').style.display = 'flex';
        this.isAuthenticated = true;

        // Update user display
        const userElement = document.getElementById('current-user');
        if (userElement && this.user) {
            userElement.textContent = `${this.user.username} (${this.user.role})`;
        }
    }

    /**
     * Show login error
     */
    showLoginError(message) {
        const errorElement = document.getElementById('login-error');
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = message ? 'block' : 'none';
        }
    }

    /**
     * Switch navigation tab
     */
    switchTab(event) {
        event.preventDefault();
        const tabName = event.target.getAttribute('data-tab');
        this.switchTabByName(tabName);

        // Update URL
        history.pushState({ tab: tabName }, '', `#${tabName}`);
    }

    /**
     * Switch tab by name
     */
    switchTabByName(tabName) {
        // Check permissions
        if (!this.checkTabPermission(tabName)) {
            this.showToast('You do not have permission to access this section', 'error');
            return;
        }

        // Update navigation
        const navTabs = document.querySelectorAll('.nav-tab');
        navTabs.forEach(tab => {
            tab.classList.remove('active');
            if (tab.getAttribute('data-tab') === tabName) {
                tab.classList.add('active');
            }
        });

        // Update content
        const tabContents = document.querySelectorAll('.tab-content');
        tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === `${tabName}-tab`) {
                content.classList.add('active');
            }
        });

        this.currentTab = tabName;

        // Load tab-specific data
        this.loadTabData(tabName);
    }

    /**
     * Check if user has permission to access tab
     */
    checkTabPermission(tabName) {
        if (!this.user) return false;

        const permissions = window.authService.getPermissions();

        switch (tabName) {
            case 'dashboard':
                return permissions.canViewDashboard;
            case 'config':
                return permissions.canViewSystemConfig;
            case 'integrations':
                return permissions.canViewIntegrations;
            case 'user-management':
                return permissions.canViewUsers;
            case 'monitoring':
                return permissions.canViewMonitoring;
            case 'maintenance':
                return permissions.canViewMaintenance;
            case 'security':
                return permissions.canViewSecurity;
            default:
                return false;
        }
    }

    /**
     * Load tab-specific data
     */
    async loadTabData(tabName) {
        switch (tabName) {
            case 'user-management':
                if (window.userManagement) {
                    await window.userManagement.loadUsers();
                }
                break;
            case 'monitoring':
                if (window.monitoringDashboard) {
                    await window.monitoringDashboard.updateDashboard();
                }
                break;
            case 'security':
                if (window.securitySettings) {
                    await window.securitySettings.loadSecuritySettings();
                    await window.securitySettings.loadAuditLogs();
                }
                break;
        }
    }

    /**
     * Initialize components
     */
    initializeComponents() {
        // Initialize all components
        if (window.configPanel) {
            window.configPanel.init();
        }

        if (window.integrationPanel) {
            window.integrationPanel.init();
        }

        if (window.userManagement) {
            window.userManagement.init();
        }

        if (window.monitoringDashboard) {
            window.monitoringDashboard.init();
        }

        if (window.maintenanceTools) {
            window.maintenanceTools.init();
        }

        if (window.securitySettings) {
            window.securitySettings.init();
        }

        // Load initial tab data
        this.loadTabData(this.currentTab);
    }

    /**
     * Setup periodic updates
     */
    setupPeriodicUpdates() {
        // Update system status every 30 seconds
        setInterval(() => {
            if (this.isAuthenticated && this.currentTab === 'dashboard') {
                this.updateSystemStatus();
            }
        }, 30000);
    }

    /**
     * Update system status
     */
    async updateSystemStatus() {
        try {
            const health = await window.monitoringService.getSystemHealth();
            if (health) {
                // Update status indicators
                this.updateStatusIndicator('db-status', health.database);
                this.updateStatusIndicator('scheduler-status', health.scheduler);
                this.updateStatusIndicator('api-status', health.api);
            }
        } catch (error) {
            console.error('Failed to update system status:', error);
        }
    }

    /**
     * Update status indicator
     */
    updateStatusIndicator(elementId, status) {
        const element = document.getElementById(elementId);
        if (element) {
            element.className = `status-value status-${status === 'healthy' ? 'healthy' : 'error'}`;
            element.textContent = status === 'healthy' ? 'Healthy' : 'Error';
        }
    }

    /**
     * Handle window resize
     */
    handleResize() {
        // Handle responsive navigation
        const nav = document.querySelector('.admin-nav');
        const content = document.querySelector('.admin-content');

        if (window.innerWidth <= 768) {
            // Mobile layout
            nav.style.position = 'static';
            nav.style.width = '100%';
            content.style.marginLeft = '0';
        } else {
            // Desktop layout
            nav.style.position = 'fixed';
            nav.style.width = '250px';
            content.style.marginLeft = '250px';
        }
    }

    /**
     * Show loading overlay
     */
    showLoading(show) {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = show ? 'flex' : 'none';
        }
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info', duration = 5000) {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">${this.escapeHtml(message)}</div>
            <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
        `;

        toastContainer.appendChild(toast);

        // Auto remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, duration);
        }

        return toast;
    }

    /**
     * Hide all modals
     */
    hideModals() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.style.display = 'none';
        });
    }

    /**
     * Escape HTML for security
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Get current user permissions
     */
    getPermissions() {
        return window.authService.getPermissions();
    }

    /**
     * Check if user has role
     */
    hasRole(role) {
        return window.authService.hasRole(role);
    }

    /**
     * Refresh current tab data
     */
    refreshCurrentTab() {
        this.loadTabData(this.currentTab);
        this.showToast('Data refreshed', 'success');
    }

    /**
     * Export current configuration
     */
    async exportConfiguration() {
        try {
            await window.configService.exportConfig();
        } catch (error) {
            console.error('Export error:', error);
            this.showToast('Failed to export configuration', 'error');
        }
    }

    /**
     * Show help for current section
     */
    showHelp() {
        const helpContent = {
            dashboard: 'Dashboard shows system overview, quick stats, and recent activity.',
            config: 'Configure system settings, crawler parameters, database options, and feature flags.',
            integrations: 'Manage connections to external services like qBittorrent, Audiobookshelf, and APIs.',
            'user-management': 'Create, edit, and manage user accounts with role-based permissions.',
            monitoring: 'View real-time system metrics, logs, and performance data.',
            maintenance: 'Perform database optimization, backups, cache clearing, and system maintenance.',
            security: 'Configure security settings, password policies, and view audit logs.'
        };

        const content = helpContent[this.currentTab] || 'Select a section to view help.';
        this.showToast(content, 'info', 10000);
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(event) {
        // Ctrl/Cmd + R to refresh
        if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
            event.preventDefault();
            this.refreshCurrentTab();
        }

        // Ctrl/Cmd + H for help
        if ((event.ctrlKey || event.metaKey) && event.key === 'h') {
            event.preventDefault();
            this.showHelp();
        }

        // Escape to close modals
        if (event.key === 'Escape') {
            this.hideModals();
        }
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }

    /**
     * Initialize keyboard shortcuts
     */
    initKeyboardShortcuts() {
        this.setupKeyboardShortcuts();
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        // Cleanup components
        if (window.monitoringDashboard) {
            window.monitoringDashboard.cleanup();
        }

        // Remove event listeners
        window.removeEventListener('resize', this.handleResize);
        window.removeEventListener('popstate', this.handlePopState);
    }
}

// Create global instance
window.adminPanel = new AdminPanel();

// Initialize keyboard shortcuts when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.adminPanel.initKeyboardShortcuts();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (window.adminPanel) {
        window.adminPanel.cleanup();
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminPanel;
}