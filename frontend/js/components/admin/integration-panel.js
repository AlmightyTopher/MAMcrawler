/**
 * Integration Panel Component for MAMcrawler Admin Panel
 * Handles integration configuration and testing
 */

class IntegrationPanel {
    constructor() {
        this.integrations = ['qbittorrent', 'audiobookshelf', 'google-books'];
        this.init();
    }

    /**
     * Initialize the integration panel
     */
    init() {
        this.bindEvents();
        this.loadCurrentIntegrations();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Integration forms
        this.integrations.forEach(integration => {
            const form = document.getElementById(`${integration}-form`);
            if (form) {
                form.addEventListener('submit', (e) => this.handleIntegrationSubmit(e, integration));
            }
        });
    }

    /**
     * Load current integration configurations
     */
    async loadCurrentIntegrations() {
        for (const integration of this.integrations) {
            try {
                const config = await window.configService.getIntegrationConfig(integration);
                if (config) {
                    this.populateIntegrationForm(integration, config);
                }
            } catch (error) {
                console.error(`Failed to load ${integration} config:`, error);
            }
        }
    }

    /**
     * Populate integration form
     */
    populateIntegrationForm(integration, config) {
        switch (integration) {
            case 'qbittorrent':
                this.setFormValue('qb-host', config.host || '');
                this.setFormValue('qb-port', config.port || 52095);
                this.setFormValue('qb-username', config.username || '');
                this.setFormValue('qb-password', config.password || '');
                break;
            case 'audiobookshelf':
                this.setFormValue('abs-url', config.url || '');
                this.setFormValue('abs-token', config.token || '');
                break;
            case 'google-books':
                this.setFormValue('google-api-key', config.api_key || '');
                break;
        }
    }

    /**
     * Handle integration form submission
     */
    async handleIntegrationSubmit(event, integration) {
        event.preventDefault();

        const formData = new FormData(event.target);
        let config = {};

        // Build config based on integration type
        switch (integration) {
            case 'qbittorrent':
                config = {
                    host: formData.get('host'),
                    port: parseInt(formData.get('port')),
                    username: formData.get('username'),
                    password: formData.get('password')
                };
                break;
            case 'audiobookshelf':
                config = {
                    url: formData.get('url'),
                    token: formData.get('token')
                };
                break;
            case 'google-books':
                config = {
                    api_key: formData.get('api_key')
                };
                break;
        }

        // Validate config
        if (!this.validateIntegrationConfig(integration, config)) {
            return;
        }

        try {
            window.adminPanel.showLoading(true);

            // Test connection first
            const testResult = await window.configService.testIntegrationConnection(integration);
            if (!testResult.success) {
                window.adminPanel.showToast(`${integration} connection test failed: ${testResult.error}`, 'warning');
                // Continue with save anyway
            }

            // Save configuration
            const response = await window.configService.updateIntegrationConfig(integration, config);

            if (response.success) {
                window.adminPanel.showToast(`${integration} configuration saved successfully`, 'success');
            } else {
                window.adminPanel.showToast(response.error || `Failed to save ${integration} configuration`, 'error');
            }
        } catch (error) {
            console.error(`${integration} config save error:`, error);
            window.adminPanel.showToast(`Failed to save ${integration} configuration`, 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Validate integration configuration
     */
    validateIntegrationConfig(integration, config) {
        const errors = [];

        switch (integration) {
            case 'qbittorrent':
                if (!config.host) errors.push('Host is required');
                if (!config.port || config.port < 1 || config.port > 65535) {
                    errors.push('Port must be between 1 and 65535');
                }
                if (!config.username) errors.push('Username is required');
                if (!config.password) errors.push('Password is required');
                break;

            case 'audiobookshelf':
                if (!config.url) errors.push('Server URL is required');
                try {
                    new URL(config.url);
                } catch {
                    errors.push('Server URL must be a valid URL');
                }
                if (!config.token) errors.push('API token is required');
                break;

            case 'google-books':
                if (!config.api_key) errors.push('API key is required');
                break;
        }

        if (errors.length > 0) {
            errors.forEach(error => window.adminPanel.showToast(error, 'error'));
            return false;
        }

        return true;
    }

    /**
     * Test integration connection
     */
    async testConnection(integration) {
        try {
            window.adminPanel.showLoading(true);
            const response = await window.configService.testIntegrationConnection(integration);

            if (response.success) {
                window.adminPanel.showToast(`${integration} connection successful`, 'success');
            } else {
                window.adminPanel.showToast(`${integration} connection failed: ${response.error}`, 'error');
            }
        } catch (error) {
            console.error(`Connection test error for ${integration}:`, error);
            window.adminPanel.showToast(`Failed to test ${integration} connection`, 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Reset integration configuration
     */
    async resetIntegration(integration) {
        if (!confirm(`Are you sure you want to reset ${integration} configuration?`)) {
            return;
        }

        try {
            const response = await window.configService.resetConfig(`integration_${integration}`);
            if (response.success) {
                window.adminPanel.showToast(`${integration} configuration reset`, 'success');
                // Clear form
                const form = document.getElementById(`${integration}-form`);
                if (form) {
                    form.reset();
                }
            } else {
                window.adminPanel.showToast(response.error || `Failed to reset ${integration} configuration`, 'error');
            }
        } catch (error) {
            console.error(`Reset error for ${integration}:`, error);
            window.adminPanel.showToast(`Failed to reset ${integration} configuration`, 'error');
        }
    }

    /**
     * Get integration status
     */
    async getIntegrationStatus(integration) {
        try {
            const response = await window.configService.testIntegrationConnection(integration);
            return {
                name: integration,
                status: response.success ? 'connected' : 'disconnected',
                lastTest: new Date().toISOString(),
                error: response.error
            };
        } catch (error) {
            return {
                name: integration,
                status: 'error',
                lastTest: new Date().toISOString(),
                error: error.message
            };
        }
    }

    /**
     * Get all integration statuses
     */
    async getAllIntegrationStatuses() {
        const statuses = {};
        for (const integration of this.integrations) {
            statuses[integration] = await this.getIntegrationStatus(integration);
        }
        return statuses;
    }

    /**
     * Set form input value
     */
    setFormValue(inputId, value) {
        const input = document.getElementById(inputId);
        if (input) {
            input.value = value;
        }
    }

    /**
     * Show integration details
     */
    showIntegrationDetails(integration) {
        // Could show a modal with detailed integration information
        console.log(`Showing details for ${integration}`);
    }

    /**
     * Export integration configurations
     */
    async exportIntegrations() {
        try {
            const configs = {};
            for (const integration of this.integrations) {
                const config = await window.configService.getIntegrationConfig(integration);
                if (config) {
                    configs[integration] = config;
                }
            }

            // Create download
            const blob = new Blob([JSON.stringify(configs, null, 2)], {
                type: 'application/json'
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `mamcrawler-integrations-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            window.adminPanel.showToast('Integration configurations exported', 'success');
        } catch (error) {
            console.error('Export error:', error);
            window.adminPanel.showToast('Failed to export integration configurations', 'error');
        }
    }

    /**
     * Import integration configurations
     */
    async importIntegrations(file) {
        try {
            const text = await file.text();
            const configs = JSON.parse(text);

            let successCount = 0;
            let errorCount = 0;

            for (const [integration, config] of Object.entries(configs)) {
                if (this.integrations.includes(integration)) {
                    try {
                        await window.configService.updateIntegrationConfig(integration, config);
                        successCount++;
                    } catch (error) {
                        console.error(`Failed to import ${integration}:`, error);
                        errorCount++;
                    }
                }
            }

            if (successCount > 0) {
                window.adminPanel.showToast(`Successfully imported ${successCount} integration(s)`, 'success');
                // Reload configurations
                await this.loadCurrentIntegrations();
            }

            if (errorCount > 0) {
                window.adminPanel.showToast(`Failed to import ${errorCount} integration(s)`, 'warning');
            }

        } catch (error) {
            console.error('Import error:', error);
            window.adminPanel.showToast('Failed to import integration configurations', 'error');
        }
    }
}

// Create global instance
window.integrationPanel = new IntegrationPanel();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = IntegrationPanel;
}