/**
 * Maintenance Service for MAMcrawler Admin Panel
 * Handles system maintenance, backups, and administrative operations
 */

class MaintenanceService {
    constructor() {
        this.apiBase = '/api/admin';
    }

    /**
     * Get database statistics
     */
    async getDatabaseStats() {
        try {
            const response = await window.authService.apiCall('/maintenance/database/stats');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get database stats:', error);
            throw error;
        }
    }

    /**
     * Optimize database
     */
    async optimizeDatabase() {
        try {
            const response = await window.authService.apiCall('/maintenance/database/optimize', {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Failed to optimize database:', error);
            throw error;
        }
    }

    /**
     * Clean up old data
     */
    async cleanupOldData(olderThanDays = 30) {
        try {
            const response = await window.authService.apiCall('/maintenance/database/cleanup', {
                method: 'POST',
                body: JSON.stringify({ older_than_days: olderThanDays })
            });
            return response;
        } catch (error) {
            console.error('Failed to cleanup old data:', error);
            throw error;
        }
    }

    /**
     * Get backup status
     */
    async getBackupStatus() {
        try {
            const response = await window.authService.apiCall('/maintenance/backup/status');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get backup status:', error);
            throw error;
        }
    }

    /**
     * Create system backup
     */
    async createBackup(options = {}) {
        try {
            const response = await window.authService.apiCall('/maintenance/backup/create', {
                method: 'POST',
                body: JSON.stringify(options)
            });
            return response;
        } catch (error) {
            console.error('Failed to create backup:', error);
            throw error;
        }
    }

    /**
     * List available backups
     */
    async listBackups() {
        try {
            const response = await window.authService.apiCall('/maintenance/backup/list');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to list backups:', error);
            throw error;
        }
    }

    /**
     * Download backup
     */
    async downloadBackup(backupId) {
        try {
            const response = await window.authService.apiCall(`/maintenance/backup/download/${backupId}`);
            if (response.success) {
                // Create download link
                const blob = new Blob([response.data], {
                    type: 'application/octet-stream'
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `mamcrawler-backup-${backupId}.tar.gz`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                return { success: true };
            } else {
                return response;
            }
        } catch (error) {
            console.error('Failed to download backup:', error);
            throw error;
        }
    }

    /**
     * Restore from backup
     */
    async restoreBackup(backupId, options = {}) {
        try {
            const response = await window.authService.apiCall(`/maintenance/backup/restore/${backupId}`, {
                method: 'POST',
                body: JSON.stringify(options)
            });
            return response;
        } catch (error) {
            console.error('Failed to restore backup:', error);
            throw error;
        }
    }

    /**
     * Delete backup
     */
    async deleteBackup(backupId) {
        try {
            const response = await window.authService.apiCall(`/maintenance/backup/delete/${backupId}`, {
                method: 'DELETE'
            });
            return response;
        } catch (error) {
            console.error('Failed to delete backup:', error);
            throw error;
        }
    }

    /**
     * Get system cache status
     */
    async getCacheStatus() {
        try {
            const response = await window.authService.apiCall('/maintenance/cache/status');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get cache status:', error);
            throw error;
        }
    }

    /**
     * Clear system cache
     */
    async clearCache(cacheType = 'all') {
        try {
            const response = await window.authService.apiCall('/maintenance/cache/clear', {
                method: 'POST',
                body: JSON.stringify({ cache_type: cacheType })
            });
            return response;
        } catch (error) {
            console.error('Failed to clear cache:', error);
            throw error;
        }
    }

    /**
     * Get scheduler status
     */
    async getSchedulerStatus() {
        try {
            const response = await window.authService.apiCall('/maintenance/scheduler/status');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get scheduler status:', error);
            throw error;
        }
    }

    /**
     * Restart scheduler
     */
    async restartScheduler() {
        try {
            const response = await window.authService.apiCall('/maintenance/scheduler/restart', {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Failed to restart scheduler:', error);
            throw error;
        }
    }

    /**
     * Get log file status
     */
    async getLogStatus() {
        try {
            const response = await window.authService.apiCall('/maintenance/logs/status');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get log status:', error);
            throw error;
        }
    }

    /**
     * Rotate log files
     */
    async rotateLogs() {
        try {
            const response = await window.authService.apiCall('/maintenance/logs/rotate', {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Failed to rotate logs:', error);
            throw error;
        }
    }

    /**
     * Clear old log files
     */
    async clearOldLogs(olderThanDays = 30) {
        try {
            const response = await window.authService.apiCall('/maintenance/logs/clear', {
                method: 'POST',
                body: JSON.stringify({ older_than_days: olderThanDays })
            });
            return response;
        } catch (error) {
            console.error('Failed to clear old logs:', error);
            throw error;
        }
    }

    /**
     * Get system information
     */
    async getSystemInfo() {
        try {
            const response = await window.authService.apiCall('/maintenance/system/info');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get system info:', error);
            throw error;
        }
    }

    /**
     * Run system diagnostics
     */
    async runDiagnostics() {
        try {
            const response = await window.authService.apiCall('/maintenance/system/diagnostics', {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Failed to run diagnostics:', error);
            throw error;
        }
    }

    /**
     * Get maintenance history
     */
    async getMaintenanceHistory(limit = 50) {
        try {
            const response = await window.authService.apiCall(`/maintenance/history?limit=${limit}`);
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get maintenance history:', error);
            throw error;
        }
    }

    /**
     * Schedule maintenance task
     */
    async scheduleMaintenanceTask(task, schedule) {
        try {
            const response = await window.authService.apiCall('/maintenance/schedule', {
                method: 'POST',
                body: JSON.stringify({ task, schedule })
            });
            return response;
        } catch (error) {
            console.error('Failed to schedule maintenance task:', error);
            throw error;
        }
    }

    /**
     * Get scheduled maintenance tasks
     */
    async getScheduledTasks() {
        try {
            const response = await window.authService.apiCall('/maintenance/scheduled');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get scheduled tasks:', error);
            throw error;
        }
    }

    /**
     * Cancel scheduled maintenance task
     */
    async cancelScheduledTask(taskId) {
        try {
            const response = await window.authService.apiCall(`/maintenance/scheduled/${taskId}`, {
                method: 'DELETE'
            });
            return response;
        } catch (error) {
            console.error('Failed to cancel scheduled task:', error);
            throw error;
        }
    }

    /**
     * Get disk usage information
     */
    async getDiskUsage() {
        try {
            const response = await window.authService.apiCall('/maintenance/disk/usage');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get disk usage:', error);
            throw error;
        }
    }

    /**
     * Clean up disk space
     */
    async cleanupDiskSpace(options = {}) {
        try {
            const response = await window.authService.apiCall('/maintenance/disk/cleanup', {
                method: 'POST',
                body: JSON.stringify(options)
            });
            return response;
        } catch (error) {
            console.error('Failed to cleanup disk space:', error);
            throw error;
        }
    }

    /**
     * Get service status
     */
    async getServiceStatus() {
        try {
            const response = await window.authService.apiCall('/maintenance/services/status');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get service status:', error);
            throw error;
        }
    }

    /**
     * Restart service
     */
    async restartService(serviceName) {
        try {
            const response = await window.authService.apiCall(`/maintenance/services/restart/${serviceName}`, {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Failed to restart service:', error);
            throw error;
        }
    }

    /**
     * Get system performance metrics
     */
    async getPerformanceMetrics() {
        try {
            const response = await window.authService.apiCall('/maintenance/performance');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get performance metrics:', error);
            throw error;
        }
    }

    /**
     * Optimize system performance
     */
    async optimizePerformance() {
        try {
            const response = await window.authService.apiCall('/maintenance/performance/optimize', {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Failed to optimize performance:', error);
            throw error;
        }
    }

    /**
     * Export maintenance report
     */
    async exportMaintenanceReport(timeRange = '30d') {
        try {
            const response = await window.authService.apiCall(`/maintenance/report?range=${timeRange}`);
            if (response.success) {
                // Create download link
                const blob = new Blob([JSON.stringify(response.data, null, 2)], {
                    type: 'application/json'
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `mamcrawler-maintenance-report-${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                return { success: true };
            } else {
                return response;
            }
        } catch (error) {
            console.error('Failed to export maintenance report:', error);
            throw error;
        }
    }

    /**
     * Get maintenance configuration
     */
    async getMaintenanceConfig() {
        try {
            const response = await window.authService.apiCall('/maintenance/config');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get maintenance config:', error);
            throw error;
        }
    }

    /**
     * Update maintenance configuration
     */
    async updateMaintenanceConfig(config) {
        try {
            const response = await window.authService.apiCall('/maintenance/config', {
                method: 'PUT',
                body: JSON.stringify(config)
            });
            return response;
        } catch (error) {
            console.error('Failed to update maintenance config:', error);
            throw error;
        }
    }
}

// Create global instance
window.maintenanceService = new MaintenanceService();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MaintenanceService;
}