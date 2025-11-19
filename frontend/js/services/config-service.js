/**
 * Configuration Service for MAMcrawler Admin Panel
 * Handles system configuration management
 */

class ConfigService {
    constructor() {
        this.apiBase = '/api/admin';
    }

    /**
     * Get system configuration
     */
    async getSystemConfig() {
        try {
            const response = await window.authService.apiCall('/config/system');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get system config:', error);
            throw error;
        }
    }

    /**
     * Update system configuration
     */
    async updateSystemConfig(config) {
        try {
            const response = await window.authService.apiCall('/config/system', {
                method: 'PUT',
                body: JSON.stringify(config)
            });
            return response;
        } catch (error) {
            console.error('Failed to update system config:', error);
            throw error;
        }
    }

    /**
     * Get crawler configuration
     */
    async getCrawlerConfig() {
        try {
            const response = await window.authService.apiCall('/config/crawler');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get crawler config:', error);
            throw error;
        }
    }

    /**
     * Update crawler configuration
     */
    async updateCrawlerConfig(config) {
        try {
            const response = await window.authService.apiCall('/config/crawler', {
                method: 'PUT',
                body: JSON.stringify(config)
            });
            return response;
        } catch (error) {
            console.error('Failed to update crawler config:', error);
            throw error;
        }
    }

    /**
     * Get database configuration
     */
    async getDatabaseConfig() {
        try {
            const response = await window.authService.apiCall('/config/database');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get database config:', error);
            throw error;
        }
    }

    /**
     * Update database configuration
     */
    async updateDatabaseConfig(config) {
        try {
            const response = await window.authService.apiCall('/config/database', {
                method: 'PUT',
                body: JSON.stringify(config)
            });
            return response;
        } catch (error) {
            console.error('Failed to update database config:', error);
            throw error;
        }
    }

    /**
     * Get feature flags
     */
    async getFeatureFlags() {
        try {
            const response = await window.authService.apiCall('/config/features');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get feature flags:', error);
            throw error;
        }
    }

    /**
     * Update feature flags
     */
    async updateFeatureFlags(flags) {
        try {
            const response = await window.authService.apiCall('/config/features', {
                method: 'PUT',
                body: JSON.stringify(flags)
            });
            return response;
        } catch (error) {
            console.error('Failed to update feature flags:', error);
            throw error;
        }
    }

    /**
     * Get integration configurations
     */
    async getIntegrationConfig(integration) {
        try {
            const response = await window.authService.apiCall(`/config/integrations/${integration}`);
            return response.success ? response.data : null;
        } catch (error) {
            console.error(`Failed to get ${integration} config:`, error);
            throw error;
        }
    }

    /**
     * Update integration configuration
     */
    async updateIntegrationConfig(integration, config) {
        try {
            const response = await window.authService.apiCall(`/config/integrations/${integration}`, {
                method: 'PUT',
                body: JSON.stringify(config)
            });
            return response;
        } catch (error) {
            console.error(`Failed to update ${integration} config:`, error);
            throw error;
        }
    }

    /**
     * Test integration connection
     */
    async testIntegrationConnection(integration) {
        try {
            const response = await window.authService.apiCall(`/config/integrations/${integration}/test`, {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error(`Failed to test ${integration} connection:`, error);
            throw error;
        }
    }

    /**
     * Get security settings
     */
    async getSecuritySettings() {
        try {
            const response = await window.authService.apiCall('/config/security');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get security settings:', error);
            throw error;
        }
    }

    /**
     * Update security settings
     */
    async updateSecuritySettings(settings) {
        try {
            const response = await window.authService.apiCall('/config/security', {
                method: 'PUT',
                body: JSON.stringify(settings)
            });
            return response;
        } catch (error) {
            console.error('Failed to update security settings:', error);
            throw error;
        }
    }

    /**
     * Get password policy
     */
    async getPasswordPolicy() {
        try {
            const response = await window.authService.apiCall('/config/security/password-policy');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get password policy:', error);
            throw error;
        }
    }

    /**
     * Update password policy
     */
    async updatePasswordPolicy(policy) {
        try {
            const response = await window.authService.apiCall('/config/security/password-policy', {
                method: 'PUT',
                body: JSON.stringify(policy)
            });
            return response;
        } catch (error) {
            console.error('Failed to update password policy:', error);
            throw error;
        }
    }

    /**
     * Export configuration
     */
    async exportConfig() {
        try {
            const response = await window.authService.apiCall('/config/export');
            if (response.success) {
                // Create download link
                const blob = new Blob([JSON.stringify(response.data, null, 2)], {
                    type: 'application/json'
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `mamcrawler-config-${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                return { success: true };
            } else {
                return response;
            }
        } catch (error) {
            console.error('Failed to export config:', error);
            throw error;
        }
    }

    /**
     * Import configuration
     */
    async importConfig(configFile) {
        try {
            const formData = new FormData();
            formData.append('config', configFile);

            const response = await window.authService.apiCall('/config/import', {
                method: 'POST',
                body: formData,
                headers: {} // Let browser set content-type for FormData
            });
            return response;
        } catch (error) {
            console.error('Failed to import config:', error);
            throw error;
        }
    }

    /**
     * Reset configuration to defaults
     */
    async resetConfig(section = null) {
        try {
            const url = section ? `/config/reset/${section}` : '/config/reset';
            const response = await window.authService.apiCall(url, {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Failed to reset config:', error);
            throw error;
        }
    }

    /**
     * Validate configuration
     */
    async validateConfig(config, section) {
        try {
            const response = await window.authService.apiCall('/config/validate', {
                method: 'POST',
                body: JSON.stringify({ config, section })
            });
            return response;
        } catch (error) {
            console.error('Failed to validate config:', error);
            throw error;
        }
    }

    /**
     * Get configuration history
     */
    async getConfigHistory(section = null, limit = 50) {
        try {
            const url = section ?
                `/config/history/${section}?limit=${limit}` :
                `/config/history?limit=${limit}`;
            const response = await window.authService.apiCall(url);
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get config history:', error);
            throw error;
        }
    }

    /**
     * Restore configuration from history
     */
    async restoreConfigFromHistory(historyId) {
        try {
            const response = await window.authService.apiCall(`/config/restore/${historyId}`, {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Failed to restore config from history:', error);
            throw error;
        }
    }
}

// Create global instance
window.configService = new ConfigService();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ConfigService;
}