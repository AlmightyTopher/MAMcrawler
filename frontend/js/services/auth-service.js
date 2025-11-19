/**
 * Authentication Service for MAMcrawler Admin Panel
 * Handles JWT token management, login/logout, and user session
 */

class AuthService {
    constructor() {
        this.apiBase = '/api/admin';
        this.tokenKey = 'admin_token';
        this.userKey = 'admin_user';
        this.refreshPromise = null;
    }

    /**
     * Login user
     */
    async login(credentials) {
        try {
            const response = await this.apiCall('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(credentials)
            });

            if (response.success) {
                this.setToken(response.data.access_token);
                this.setUser(response.data.user);
                return { success: true, user: response.data.user };
            } else {
                return { success: false, error: response.error };
            }
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: 'Login failed' };
        }
    }

    /**
     * Logout user
     */
    async logout() {
        try {
            await this.apiCall('/logout', { method: 'POST' });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.clearSession();
        }
    }

    /**
     * Get current user
     */
    async getCurrentUser() {
        const token = this.getToken();
        const user = this.getUser();

        if (!token || !user) {
            return null;
        }

        // Check if token is expired
        if (this.isTokenExpired(token)) {
            this.clearSession();
            return null;
        }

        return user;
    }

    /**
     * Refresh token
     */
    async refreshToken() {
        if (this.refreshPromise) {
            return this.refreshPromise;
        }

        this.refreshPromise = this.apiCall('/refresh', {
            method: 'POST'
        }).then(response => {
            if (response.success) {
                this.setToken(response.data.access_token);
                return response.data.access_token;
            } else {
                throw new Error(response.error || 'Token refresh failed');
            }
        }).catch(error => {
            console.error('Token refresh error:', error);
            this.clearSession();
            throw error;
        }).finally(() => {
            this.refreshPromise = null;
        });

        return this.refreshPromise;
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        const token = this.getToken();
        const user = this.getUser();

        return token && user && !this.isTokenExpired(token);
    }

    /**
     * Check if user has role
     */
    hasRole(role) {
        const user = this.getUser();
        if (!user) return false;

        if (role === 'admin') return user.role === 'admin';
        if (role === 'moderator') return ['admin', 'moderator'].includes(user.role);
        if (role === 'viewer') return ['admin', 'moderator', 'viewer'].includes(user.role);

        return false;
    }

    /**
     * Get stored token
     */
    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    /**
     * Set token
     */
    setToken(token) {
        localStorage.setItem(this.tokenKey, token);
    }

    /**
     * Get stored user
     */
    getUser() {
        const userJson = localStorage.getItem(this.userKey);
        return userJson ? JSON.parse(userJson) : null;
    }

    /**
     * Set user
     */
    setUser(user) {
        localStorage.setItem(this.userKey, JSON.stringify(user));
    }

    /**
     * Clear session data
     */
    clearSession() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.userKey);
        sessionStorage.removeItem('csrf_token');
    }

    /**
     * Check if token is expired
     */
    isTokenExpired(token) {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            const currentTime = Date.now() / 1000;
            return payload.exp < currentTime;
        } catch (e) {
            return true;
        }
    }

    /**
     * Get token expiration time
     */
    getTokenExpiration(token) {
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.exp * 1000; // Convert to milliseconds
        } catch (e) {
            return 0;
        }
    }

    /**
     * Setup automatic token refresh
     */
    setupAutoRefresh() {
        const token = this.getToken();
        if (!token) return;

        const expirationTime = this.getTokenExpiration(token);
        const currentTime = Date.now();
        const timeUntilExpiry = expirationTime - currentTime;

        // Refresh 5 minutes before expiry
        const refreshTime = timeUntilExpiry - (5 * 60 * 1000);

        if (refreshTime > 0) {
            setTimeout(() => {
                this.refreshToken().catch(error => {
                    console.error('Auto refresh failed:', error);
                });
            }, refreshTime);
        }
    }

    /**
     * API call with authentication
     */
    async apiCall(endpoint, options = {}) {
        const url = `${this.apiBase}${endpoint}`;
        const token = this.getToken();

        const defaultHeaders = {
            'Content-Type': 'application/json'
        };

        if (token) {
            defaultHeaders['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            // Handle token expiration
            if (response.status === 401 && token) {
                // Try to refresh token
                try {
                    await this.refreshToken();
                    // Retry the original request
                    return this.apiCall(endpoint, options);
                } catch (refreshError) {
                    this.clearSession();
                    throw new Error('Session expired');
                }
            }

            if (!response.ok) {
                throw new Error(data.detail || data.error || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API call error:', error);
            throw error;
        }
    }

    /**
     * Validate session
     */
    async validateSession() {
        try {
            const response = await this.apiCall('/me');
            if (response.success) {
                this.setUser(response.data.user);
                return true;
            } else {
                this.clearSession();
                return false;
            }
        } catch (error) {
            console.error('Session validation error:', error);
            this.clearSession();
            return false;
        }
    }

    /**
     * Change password
     */
    async changePassword(userId, passwordData) {
        try {
            const response = await this.apiCall(`/users/${userId}/password`, {
                method: 'POST',
                body: JSON.stringify(passwordData)
            });

            return response;
        } catch (error) {
            console.error('Password change error:', error);
            throw error;
        }
    }

    /**
     * Setup session monitoring
     */
    setupSessionMonitoring() {
        // Check session every 5 minutes
        setInterval(() => {
            if (this.isAuthenticated()) {
                this.validateSession().catch(error => {
                    console.error('Session monitoring error:', error);
                });
            }
        }, 5 * 60 * 1000);

        // Handle visibility change (tab focus/unfocus)
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.isAuthenticated()) {
                this.validateSession().catch(error => {
                    console.error('Session validation on focus error:', error);
                });
            }
        });

        // Handle online/offline events
        window.addEventListener('online', () => {
            if (this.isAuthenticated()) {
                this.validateSession().catch(error => {
                    console.error('Session validation on online error:', error);
                });
            }
        });
    }

    /**
     * Get user permissions
     */
    getPermissions() {
        const user = this.getUser();
        if (!user) return {};

        const permissions = {
            canViewDashboard: true,
            canViewSystemConfig: this.hasRole('moderator'),
            canEditSystemConfig: this.hasRole('admin'),
            canViewIntegrations: this.hasRole('moderator'),
            canEditIntegrations: this.hasRole('admin'),
            canViewUsers: this.hasRole('admin'),
            canEditUsers: this.hasRole('admin'),
            canViewMonitoring: true,
            canViewMaintenance: this.hasRole('moderator'),
            canPerformMaintenance: this.hasRole('admin'),
            canViewSecurity: this.hasRole('admin'),
            canEditSecurity: this.hasRole('admin')
        };

        return permissions;
    }

    /**
     * Initialize service
     */
    init() {
        // Setup auto refresh if authenticated
        if (this.isAuthenticated()) {
            this.setupAutoRefresh();
            this.setupSessionMonitoring();
        }

        // Handle page unload
        window.addEventListener('beforeunload', () => {
            // Could save session state here
        });
    }
}

// Create global instance
window.authService = new AuthService();

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.authService.init();
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthService;
}