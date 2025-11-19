/**
 * Maintenance Tools Component for MAMcrawler Admin Panel
 * Handles system maintenance operations
 */

class MaintenanceTools {
    constructor() {
        this.init();
    }

    /**
     * Initialize maintenance tools
     */
    init() {
        this.bindEvents();
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        const actions = [
            'optimize-db-btn',
            'cleanup-old-data-btn',
            'clear-cache-btn',
            'restart-scheduler-btn',
            'create-backup-btn',
            'download-backup-btn'
        ];

        actions.forEach(actionId => {
            const button = document.getElementById(actionId);
            if (button) {
                button.addEventListener('click', () => this.handleMaintenanceAction(actionId));
            }
        });
    }

    /**
     * Handle maintenance action
     */
    async handleMaintenanceAction(actionId) {
        const actions = {
            'optimize-db-btn': {
                action: 'optimize_database',
                confirm: 'This will optimize the database. Continue?',
                service: 'optimizeDatabase'
            },
            'cleanup-old-data-btn': {
                action: 'cleanup_data',
                confirm: 'This will delete old data. Continue?',
                service: 'cleanupOldData'
            },
            'clear-cache-btn': {
                action: 'clear_cache',
                confirm: 'This will clear all cached data. Continue?',
                service: 'clearCache'
            },
            'restart-scheduler-btn': {
                action: 'restart_scheduler',
                confirm: 'This will restart the task scheduler. Continue?',
                service: 'restartScheduler'
            },
            'create-backup-btn': {
                action: 'create_backup',
                confirm: 'This will create a system backup. Continue?',
                service: 'createBackup'
            },
            'download-backup-btn': {
                action: 'download_backup',
                confirm: false,
                service: 'downloadBackup'
            }
        };

        const config = actions[actionId];
        if (!config) return;

        if (config.confirm && !confirm(config.confirm)) {
            return;
        }

        try {
            window.adminPanel.showLoading(true);
            const result = await window.maintenanceService[config.service]();

            if (result && result.success !== false) {
                window.adminPanel.showToast(`${config.action.replace('_', ' ')} completed successfully`, 'success');
            } else {
                window.adminPanel.showToast(result?.error || `Failed to ${config.action.replace('_', ' ')}`, 'error');
            }
        } catch (error) {
            console.error(`${config.action} error:`, error);
            window.adminPanel.showToast(`Failed to ${config.action.replace('_', ' ')}`, 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Get database statistics
     */
    async getDatabaseStats() {
        try {
            const stats = await window.maintenanceService.getDatabaseStats();
            return stats;
        } catch (error) {
            console.error('Failed to get database stats:', error);
            throw error;
        }
    }

    /**
     * Get backup status
     */
    async getBackupStatus() {
        try {
            const status = await window.maintenanceService.getBackupStatus();
            return status;
        } catch (error) {
            console.error('Failed to get backup status:', error);
            throw error;
        }
    }

    /**
     * List available backups
     */
    async listBackups() {
        try {
            const backups = await window.maintenanceService.listBackups();
            return backups;
        } catch (error) {
            console.error('Failed to list backups:', error);
            throw error;
        }
    }

    /**
     * Restore from backup
     */
    async restoreBackup(backupId) {
        if (!confirm('Are you sure you want to restore from this backup? This will overwrite current data.')) {
            return;
        }

        try {
            window.adminPanel.showLoading(true);
            const result = await window.maintenanceService.restoreBackup(backupId);

            if (result.success) {
                window.adminPanel.showToast('Backup restored successfully', 'success');
            } else {
                window.adminPanel.showToast(result.error || 'Failed to restore backup', 'error');
            }
        } catch (error) {
            console.error('Backup restore error:', error);
            window.adminPanel.showToast('Failed to restore backup', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Delete backup
     */
    async deleteBackup(backupId) {
        if (!confirm('Are you sure you want to delete this backup?')) {
            return;
        }

        try {
            const result = await window.maintenanceService.deleteBackup(backupId);

            if (result.success) {
                window.adminPanel.showToast('Backup deleted successfully', 'success');
            } else {
                window.adminPanel.showToast(result.error || 'Failed to delete backup', 'error');
            }
        } catch (error) {
            console.error('Backup delete error:', error);
            window.adminPanel.showToast('Failed to delete backup', 'error');
        }
    }

    /**
     * Get cache status
     */
    async getCacheStatus() {
        try {
            const status = await window.maintenanceService.getCacheStatus();
            return status;
        } catch (error) {
            console.error('Failed to get cache status:', error);
            throw error;
        }
    }

    /**
     * Get scheduler status
     */
    async getSchedulerStatus() {
        try {
            const status = await window.maintenanceService.getSchedulerStatus();
            return status;
        } catch (error) {
            console.error('Failed to get scheduler status:', error);
            throw error;
        }
    }

    /**
     * Run system diagnostics
     */
    async runDiagnostics() {
        try {
            window.adminPanel.showLoading(true);
            const result = await window.maintenanceService.runDiagnostics();

            if (result.success) {
                window.adminPanel.showToast('Diagnostics completed successfully', 'success');
                return result.data;
            } else {
                window.adminPanel.showToast(result.error || 'Diagnostics failed', 'error');
            }
        } catch (error) {
            console.error('Diagnostics error:', error);
            window.adminPanel.showToast('Diagnostics failed', 'error');
        } finally {
            window.adminPanel.showLoading(false);
        }
    }

    /**
     * Export maintenance report
     */
    async exportMaintenanceReport() {
        try {
            await window.maintenanceService.exportMaintenanceReport();
            window.adminPanel.showToast('Maintenance report exported successfully', 'success');
        } catch (error) {
            console.error('Export error:', error);
            window.adminPanel.showToast('Failed to export maintenance report', 'error');
        }
    }
}

// Create global instance
window.maintenanceTools = new MaintenanceTools();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MaintenanceTools;
}