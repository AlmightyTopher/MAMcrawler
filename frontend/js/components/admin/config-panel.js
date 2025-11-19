/**
 * Configuration Panel Component for MAMcrawler Admin Panel
 * Handles system configuration interface and form management
 */

class ConfigPanel {
    constructor() {
        this.currentConfig = {};
        this.init();
    }

    /**
     * Initialize the config panel
     */
    init() {
        this.bindEvents();
        this.loadCurrentConfig();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Crawler config form
        const crawlerForm = document.getElementById('crawler-config-form');
        if (crawlerForm) {
            crawlerForm.addEventListener('submit', (e) => this.handleCrawlerConfigSubmit(e));
        }

        // Database config form
        const dbForm = document.getElementById('database-config-form');
        if (dbForm) {
            dbForm.addEventListener('submit', (e) => this.handleDatabaseConfigSubmit(e));
        }

        // Features config form
        const featuresForm = document.getElementById('features-config-form');
        if (featuresForm) {
            featuresForm.addEventListener('submit', (e) => this.handleFeaturesConfigSubmit(e));
        }
    }

    /**
     * Load current configuration
     */
    async loadCurrentConfig() {
        try {
            // Load crawler config
            const crawlerConfig = await window.configService.getCrawlerConfig();
            if (crawlerConfig) {
                this.populateCrawlerForm(crawlerConfig);
            }

            // Load database config
            const dbConfig = await window.configService.getDatabaseConfig();
            if (dbConfig) {
                this.populateDatabaseForm(dbConfig);
            }

            // Load feature flags
            const features = await window.configService.getFeatureFlags();
            if (features) {
                this.populateFeaturesForm(features);
            }

        } catch (error) {
            console.error('Failed to load current config:', error);
            window.adminPanel.showToast('Failed to load configuration', 'error');
        }
    }

    /**
     * Populate crawler configuration form
     */
    populateCrawlerForm(config) {
        this.setFormValue('crawler-interval', config.crawler_interval || 60);
        this.setFormValue('max-pages', config.max_pages_per_session || 50);
        this.setFormValue('rate-limit-min', config.rate_limit_min || 3);
        this.setFormValue('rate-limit-max', config.rate_limit_max || 10);
    }

    /**
     * Populate database configuration form
     */
    populateDatabaseForm(config) {
        this.setFormValue('retention-days', config.history_retention_days || 30);
    }

    /**
     * Populate features configuration form
     */
    populateFeaturesForm(features) {
        this.setCheckboxValue('metadata-correction', features.metadata_correction || false);
        this.setCheckboxValue('series-completion', features.series_completion || false);
        this.setCheckboxValue('author-completion', features.author_completion || false);
        this.setCheckboxValue('mam-scraping', features.mam_scraping || false);
    }

    /**
     * Handle crawler config form submission
     */
    async handleCrawlerConfigSubmit(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const config = {
            crawler_interval: parseInt(formData.get('crawler_interval')),
            max_pages_per_session: parseInt(formData.get('max_pages')),
            rate_limit_min: parseInt(formData.get('rate_limit_min')),
            rate_limit_max: parseInt(formData.get('rate_limit_max'))
        };

        // Validate config
        if (!this.validateCrawlerConfig(config)) {
            return;
        }

        try {
            window.adminPanel.showLoading(true);
            const response = await window.configService.updateCrawlerConfig(config);

            if (response.success) {
                window.adminPanel.showToast('Crawler configuration saved successfully', 'success');
                this.currentConfig.crawler = config;
            } else {
                window.adminPanel.showToast(response.error || 'Failed to save crawler configuration', 'error');
            }
        } catch (error) {
            console.error('Crawler config save error:', error);
            window.adminPanel.showToast('Failed to save crawler configuration', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Handle database config form submission
     */
    async handleDatabaseConfigSubmit(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const config = {
            history_retention_days: parseInt(formData.get('retention_days'))
        };

        // Validate config
        if (!this.validateDatabaseConfig(config)) {
            return;
        }

        try {
            window.adminPanel.showLoading(true);
            const response = await window.configService.updateDatabaseConfig(config);

            if (response.success) {
                window.adminPanel.showToast('Database configuration saved successfully', 'success');
                this.currentConfig.database = config;
            } else {
                window.adminPanel.showToast(response.error || 'Failed to save database configuration', 'error');
            }
        } catch (error) {
            console.error('Database config save error:', error);
            window.adminPanel.showToast('Failed to save database configuration', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Handle features config form submission
     */
    async handleFeaturesConfigSubmit(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const config = {
            metadata_correction: formData.get('metadata_correction') === 'on',
            series_completion: formData.get('series_completion') === 'on',
            author_completion: formData.get('author_completion') === 'on',
            mam_scraping: formData.get('mam_scraping') === 'on'
        };

        try {
            window.adminPanel.showLoading(true);
            const response = await window.configService.updateFeatureFlags(config);

            if (response.success) {
                window.adminPanel.showToast('Feature settings saved successfully', 'success');
                this.currentConfig.features = config;
            } else {
                window.adminPanel.showToast(response.error || 'Failed to save feature settings', 'error');
            }
        } catch (error) {
            console.error('Features config save error:', error);
            window.adminPanel.showToast('Failed to save feature settings', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Validate crawler configuration
     */
    validateCrawlerConfig(config) {
        const errors = [];

        if (config.crawler_interval < 5 || config.crawler_interval > 1440) {
            errors.push('Crawler interval must be between 5 and 1440 minutes');
        }

        if (config.max_pages_per_session < 1 || config.max_pages_per_session > 1000) {
            errors.push('Max pages per session must be between 1 and 1000');
        }

        if (config.rate_limit_min < 1 || config.rate_limit_min > 60) {
            errors.push('Rate limit min must be between 1 and 60 seconds');
        }

        if (config.rate_limit_max < 1 || config.rate_limit_max > 300) {
            errors.push('Rate limit max must be between 1 and 300 seconds');
        }

        if (config.rate_limit_min >= config.rate_limit_max) {
            errors.push('Rate limit min must be less than rate limit max');
        }

        if (errors.length > 0) {
            errors.forEach(error => window.adminPanel.showToast(error, 'error'));
            return false;
        }

        return true;
    }

    /**
     * Validate database configuration
     */
    validateDatabaseConfig(config) {
        const errors = [];

        if (config.history_retention_days < 1 || config.history_retention_days > 365) {
            errors.push('History retention must be between 1 and 365 days');
            return false;
        }

        if (errors.length > 0) {
            errors.forEach(error => window.adminPanel.showToast(error, 'error'));
            return false;
        }

        return true;
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
     * Set checkbox value
     */
    setCheckboxValue(checkboxId, checked) {
        const checkbox = document.getElementById(checkboxId);
        if (checkbox) {
            checkbox.checked = checked;
        }
    }

    /**
     * Reset form to current config
     */
    resetForm(formType) {
        switch (formType) {
            case 'crawler':
                if (this.currentConfig.crawler) {
                    this.populateCrawlerForm(this.currentConfig.crawler);
                }
                break;
            case 'database':
                if (this.currentConfig.database) {
                    this.populateDatabaseForm(this.currentConfig.database);
                }
                break;
            case 'features':
                if (this.currentConfig.features) {
                    this.populateFeaturesForm(this.currentConfig.features);
                }
                break;
        }
    }

    /**
     * Export current configuration
     */
    async exportConfig() {
        try {
            const response = await window.configService.exportConfig();
            if (response.success) {
                window.adminPanel.showToast('Configuration exported successfully', 'success');
            } else {
                window.adminPanel.showToast('Failed to export configuration', 'error');
            }
        } catch (error) {
            console.error('Config export error:', error);
            window.adminPanel.showToast('Failed to export configuration', 'error');
        }
    }

    /**
     * Import configuration from file
     */
    async importConfig(file) {
        try {
            const response = await window.configService.importConfig(file);
            if (response.success) {
                window.adminPanel.showToast('Configuration imported successfully', 'success');
                // Reload current config
                await this.loadCurrentConfig();
            } else {
                window.adminPanel.showToast(response.error || 'Failed to import configuration', 'error');
            }
        } catch (error) {
            console.error('Config import error:', error);
            window.adminPanel.showToast('Failed to import configuration', 'error');
        }
    }

    /**
     * Reset configuration to defaults
     */
    async resetToDefaults(section = null) {
        const confirmMessage = section ?
            `Are you sure you want to reset ${section} configuration to defaults?` :
            'Are you sure you want to reset all configuration to defaults?';

        if (!confirm(confirmMessage)) {
            return;
        }

        try {
            const response = await window.configService.resetConfig(section);
            if (response.success) {
                window.adminPanel.showToast('Configuration reset to defaults', 'success');
                // Reload current config
                await this.loadCurrentConfig();
            } else {
                window.adminPanel.showToast(response.error || 'Failed to reset configuration', 'error');
            }
        } catch (error) {
            console.error('Config reset error:', error);
            window.adminPanel.showToast('Failed to reset configuration', 'error');
        }
    }

    /**
     * Get configuration validation status
     */
    async validateCurrentConfig() {
        try {
            const allConfig = {
                ...this.currentConfig.crawler,
                ...this.currentConfig.database,
                ...this.currentConfig.features
            };

            const response = await window.configService.validateConfig(allConfig, 'all');

            if (response.success) {
                window.adminPanel.showToast('Configuration is valid', 'success');
            } else {
                window.adminPanel.showToast('Configuration validation failed', 'error');
            }

            return response;
        } catch (error) {
            console.error('Config validation error:', error);
            window.adminPanel.showToast('Failed to validate configuration', 'error');
            return { success: false, error: error.message };
        }
    }
}

// Create global instance
window.configPanel = new ConfigPanel();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ConfigPanel;
}