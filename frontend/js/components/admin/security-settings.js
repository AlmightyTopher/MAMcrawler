/**
 * Security Settings Component for MAMcrawler Admin Panel
 * Handles security configuration and audit logging
 */

class SecuritySettings {
    constructor() {
        this.auditLogs = [];
        this.init();
    }

    /**
     * Initialize security settings
     */
    init() {
        this.bindEvents();
        this.loadSecuritySettings();
        this.loadAuditLogs();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Security settings form
        const securityForm = document.getElementById('security-settings-form');
        if (securityForm) {
            securityForm.addEventListener('submit', (e) => this.handleSecuritySettingsSubmit(e));
        }

        // Password policy form
        const passwordForm = document.getElementById('password-policy-form');
        if (passwordForm) {
            passwordForm.addEventListener('submit', (e) => this.handlePasswordPolicySubmit(e));
        }
    }

    /**
     * Load security settings
     */
    async loadSecuritySettings() {
        try {
            const settings = await window.configService.getSecuritySettings();
            if (settings) {
                this.populateSecuritySettings(settings);
            }

            const policy = await window.configService.getPasswordPolicy();
            if (policy) {
                this.populatePasswordPolicy(policy);
            }
        } catch (error) {
            console.error('Failed to load security settings:', error);
            window.adminPanel.showToast('Failed to load security settings', 'error');
        }
    }

    /**
     * Load audit logs
     */
    async loadAuditLogs(limit = 100) {
        try {
            const response = await window.monitoringService.getSystemLogs(limit);
            if (response) {
                this.auditLogs = response;
                this.renderAuditTable();
            }
        } catch (error) {
            console.error('Failed to load audit logs:', error);
            window.adminPanel.showToast('Failed to load audit logs', 'error');
        }
    }

    /**
     * Populate security settings form
     */
    populateSecuritySettings(settings) {
        this.setCheckboxValue('enable-audit-logging', settings.audit_logging || false);
        this.setCheckboxValue('enable-session-timeout', settings.session_timeout || false);
        this.setFormValue('session-timeout-minutes', settings.session_timeout_minutes || 60);
        this.setCheckboxValue('enable-ip-whitelist', settings.ip_whitelist_enabled || false);
        this.setFormValue('max-login-attempts', settings.max_login_attempts || 5);
        this.setCheckboxValue('enable-two-factor', settings.two_factor_enabled || false);
    }

    /**
     * Populate password policy form
     */
    populatePasswordPolicy(policy) {
        this.setFormValue('min-password-length', policy.min_length || 8);
        this.setCheckboxValue('require-uppercase', policy.require_uppercase || false);
        this.setCheckboxValue('require-lowercase', policy.require_lowercase || false);
        this.setCheckboxValue('require-numbers', policy.require_numbers || false);
        this.setCheckboxValue('require-special-chars', policy.require_special_chars || false);
        this.setFormValue('password-expiry-days', policy.expiry_days || 90);
    }

    /**
     * Handle security settings form submission
     */
    async handleSecuritySettingsSubmit(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const settings = {
            audit_logging: formData.get('enable-audit-logging') === 'on',
            session_timeout: formData.get('enable-session-timeout') === 'on',
            session_timeout_minutes: parseInt(formData.get('session-timeout-minutes')),
            ip_whitelist_enabled: formData.get('enable-ip-whitelist') === 'on',
            max_login_attempts: parseInt(formData.get('max-login-attempts')),
            two_factor_enabled: formData.get('enable-two-factor') === 'on'
        };

        // Validate settings
        if (!this.validateSecuritySettings(settings)) {
            return;
        }

        try {
            window.adminPanel.showLoading(true);
            const response = await window.configService.updateSecuritySettings(settings);

            if (response.success) {
                window.adminPanel.showToast('Security settings saved successfully', 'success');
            } else {
                window.adminPanel.showToast(response.error || 'Failed to save security settings', 'error');
            }
        } catch (error) {
            console.error('Security settings save error:', error);
            window.adminPanel.showToast('Failed to save security settings', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Handle password policy form submission
     */
    async handlePasswordPolicySubmit(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const policy = {
            min_length: parseInt(formData.get('min-password-length')),
            require_uppercase: formData.get('require-uppercase') === 'on',
            require_lowercase: formData.get('require-lowercase') === 'on',
            require_numbers: formData.get('require-numbers') === 'on',
            require_special_chars: formData.get('require-special-chars') === 'on',
            expiry_days: parseInt(formData.get('password-expiry-days'))
        };

        // Validate policy
        if (!this.validatePasswordPolicy(policy)) {
            return;
        }

        try {
            window.adminPanel.showLoading(true);
            const response = await window.configService.updatePasswordPolicy(policy);

            if (response.success) {
                window.adminPanel.showToast('Password policy updated successfully', 'success');
            } else {
                window.adminPanel.showToast(response.error || 'Failed to update password policy', 'error');
            }
        } catch (error) {
            console.error('Password policy save error:', error);
            window.adminPanel.showToast('Failed to update password policy', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Validate security settings
     */
    validateSecuritySettings(settings) {
        const errors = [];

        if (settings.session_timeout && (settings.session_timeout_minutes < 5 || settings.session_timeout_minutes > 480)) {
            errors.push('Session timeout must be between 5 and 480 minutes');
        }

        if (settings.max_login_attempts < 3 || settings.max_login_attempts > 10) {
            errors.push('Max login attempts must be between 3 and 10');
        }

        if (errors.length > 0) {
            errors.forEach(error => window.adminPanel.showToast(error, 'error'));
            return false;
        }

        return true;
    }

    /**
     * Validate password policy
     */
    validatePasswordPolicy(policy) {
        const errors = [];

        if (policy.min_length < 8 || policy.min_length > 128) {
            errors.push('Minimum password length must be between 8 and 128 characters');
        }

        if (policy.expiry_days < 30 || policy.expiry_days > 365) {
            errors.push('Password expiry must be between 30 and 365 days');
        }

        if (errors.length > 0) {
            errors.forEach(error => window.adminPanel.showToast(error, 'error'));
            return false;
        }

        return true;
    }

    /**
     * Render audit logs table
     */
    renderAuditTable() {
        const tbody = document.getElementById('audit-table-body');
        if (!tbody) return;

        if (this.auditLogs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="loading">No audit logs found</td></tr>';
            return;
        }

        tbody.innerHTML = this.auditLogs.slice(0, 50).map(log => `
            <tr>
                <td>${new Date(log.timestamp).toLocaleString()}</td>
                <td>${this.escapeHtml(log.username || 'System')}</td>
                <td><span class="action-badge action-${log.level?.toLowerCase() || 'info'}">${log.level || 'INFO'}</span></td>
                <td>${this.escapeHtml(log.message || '')}</td>
                <td>${log.details ? JSON.stringify(log.details) : '-'}</td>
            </tr>
        `).join('');
    }

    /**
     * Export audit logs
     */
    exportAuditLogs() {
        const csvContent = [
            ['Timestamp', 'User', 'Action', 'Resource', 'Details'],
            ...this.auditLogs.map(log => [
                log.timestamp,
                log.username || 'System',
                log.level || 'INFO',
                log.message || '',
                log.details ? JSON.stringify(log.details) : ''
            ])
        ].map(row => row.map(cell => `"${cell}"`).join(',')).join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mamcrawler-audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        window.adminPanel.showToast('Audit logs exported successfully', 'success');
    }

    /**
     * Clear old audit logs
     */
    async clearOldAuditLogs(days = 90) {
        if (!confirm(`Are you sure you want to clear audit logs older than ${days} days?`)) {
            return;
        }

        try {
            window.adminPanel.showLoading(true);
            const result = await window.monitoringService.clearOldLogs(days);

            if (result.success) {
                window.adminPanel.showToast('Old audit logs cleared successfully', 'success');
                await this.loadAuditLogs(); // Refresh the table
            } else {
                window.adminPanel.showToast(result.error || 'Failed to clear old logs', 'error');
            }
        } catch (error) {
            console.error('Clear logs error:', error);
            window.adminPanel.showToast('Failed to clear old logs', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
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
     * Escape HTML for security
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Get security statistics
     */
    getSecurityStats() {
        const stats = {
            totalLogs: this.auditLogs.length,
            errorLogs: this.auditLogs.filter(log => log.level === 'ERROR').length,
            warningLogs: this.auditLogs.filter(log => log.level === 'WARNING').length,
            loginAttempts: this.auditLogs.filter(log => log.message?.includes('login')).length
        };

        return stats;
    }
}

// Create global instance
window.securitySettings = new SecuritySettings();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SecuritySettings;
}