/**
 * Downloads API Module
 * Handles all download-related API communications
 */

class DownloadsAPI {
    constructor(dashboard) {
        this.dashboard = dashboard;
    }

    /**
     * Get list of downloads with optional status filtering
     */
    async getDownloads(status = null, limit = 100, offset = 0) {
        try {
            let url = `/downloads/?limit=${limit}&offset=${offset}`;
            if (status) {
                url += `&status_filter=${status}`;
            }

            const response = await this.dashboard.apiRequest(url);
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'downloads');
            throw error;
        }
    }

    /**
     * Get download details by ID
     */
    async getDownload(downloadId) {
        try {
            const response = await this.dashboard.apiRequest(`/downloads/${downloadId}`);
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'download details');
            throw error;
        }
    }

    /**
     * Queue a new download
     */
    async queueDownload(downloadData) {
        try {
            const response = await this.dashboard.apiRequest('/downloads/', {
                method: 'POST',
                body: JSON.stringify(downloadData)
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'download queue');
            throw error;
        }
    }

    /**
     * Update download status
     */
    async updateDownloadStatus(downloadId, status, qbHash = null, qbStatus = null) {
        try {
            const response = await this.dashboard.apiRequest(`/downloads/${downloadId}/status`, {
                method: 'PUT',
                body: JSON.stringify({
                    status: status,
                    qb_hash: qbHash,
                    qb_status: qbStatus
                })
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'download status update');
            throw error;
        }
    }

    /**
     * Mark download as completed
     */
    async markDownloadComplete(downloadId, absImportStatus = 'pending') {
        try {
            const response = await this.dashboard.apiRequest(`/downloads/${downloadId}/mark-complete`, {
                method: 'PUT',
                body: JSON.stringify({
                    abs_import_status: absImportStatus
                })
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'download completion');
            throw error;
        }
    }

    /**
     * Mark download as failed
     */
    async markDownloadFailed(downloadId, errorMsg, retryAttempt = 1) {
        try {
            const response = await this.dashboard.apiRequest(`/downloads/${downloadId}/mark-failed`, {
                method: 'PUT',
                body: JSON.stringify({
                    error_msg: errorMsg,
                    retry_attempt: retryAttempt
                })
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'download failure');
            throw error;
        }
    }

    /**
     * Schedule download retry
     */
    async scheduleDownloadRetry(downloadId, daysUntilRetry = 1) {
        try {
            const response = await this.dashboard.apiRequest(`/downloads/${downloadId}/retry`, {
                method: 'PUT',
                body: JSON.stringify({
                    days_until_retry: daysUntilRetry
                })
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'download retry');
            throw error;
        }
    }

    /**
     * Get pending downloads
     */
    async getPendingDownloads() {
        try {
            const response = await this.dashboard.apiRequest('/downloads/pending');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'pending downloads');
            throw error;
        }
    }

    /**
     * Get failed downloads
     */
    async getFailedDownloads() {
        try {
            const response = await this.dashboard.apiRequest('/downloads/failed');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'failed downloads');
            throw error;
        }
    }

    /**
     * Get downloads ready for retry
     */
    async getRetryDueDownloads() {
        try {
            const response = await this.dashboard.apiRequest('/downloads/retry-due');
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'retry due downloads');
            throw error;
        }
    }

    /**
     * Remove download (hard delete)
     */
    async removeDownload(downloadId) {
        try {
            const response = await this.dashboard.apiRequest(`/downloads/${downloadId}`, {
                method: 'DELETE'
            });
            return response.data;
        } catch (error) {
            this.dashboard.handleApiError(error, 'download removal');
            throw error;
        }
    }

    /**
     * Load downloads data for the dashboard
     */
    async loadDownloadsData() {
        try {
            // Get all downloads for the table
            const allDownloads = await this.getDownloads(null, 100, 0);

            // Get summary stats
            const pendingData = await this.getPendingDownloads();
            const failedData = await this.getFailedDownloads();

            this.renderDownloadsTable(allDownloads.downloads);
            this.updateDownloadsOverview(allDownloads.downloads, pendingData, failedData);

            return {
                downloads: allDownloads.downloads,
                pending: pendingData,
                failed: failedData
            };
        } catch (error) {
            console.error('Failed to load downloads data:', error);
            this.renderEmptyDownloads('Failed to load downloads. Please try again.');
        }
    }

    /**
     * Update downloads overview stats
     */
    updateDownloadsOverview(allDownloads, pendingData, failedData) {
        const stats = {
            active: allDownloads.filter(d => d.status === 'downloading').length,
            queued: pendingData.total_pending || 0,
            completed: allDownloads.filter(d => d.status === 'completed').length,
            failed: failedData.total_failed || 0
        };

        document.getElementById('active-downloads-count').textContent = stats.active;
        document.getElementById('queued-downloads-count').textContent = stats.queued;
        document.getElementById('completed-today-count').textContent = stats.completed;
        document.getElementById('failed-downloads-count').textContent = stats.failed;
    }

    /**
     * Render downloads table
     */
    renderDownloadsTable(downloads) {
        const container = document.getElementById('downloads-content');

        if (!downloads || downloads.length === 0) {
            this.renderEmptyDownloads('No downloads found.');
            return;
        }

        const table = document.createElement('table');
        table.className = 'downloads-table';

        // Table header
        table.innerHTML = `
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Author</th>
                    <th>Source</th>
                    <th>Status</th>
                    <th>Progress</th>
                    <th>Actions</th>
                </tr>
            </thead>
        `;

        const tbody = document.createElement('tbody');

        downloads.forEach(download => {
            const row = this.createDownloadRow(download);
            tbody.appendChild(row);
        });

        table.appendChild(tbody);
        container.innerHTML = '';
        container.appendChild(table);
    }

    /**
     * Create a download table row
     */
    createDownloadRow(download) {
        const row = document.createElement('tr');

        // Status styling
        const statusClass = this.getStatusClass(download.status);
        const statusText = this.formatStatusText(download.status);

        // Progress bar
        const progressPercent = this.calculateProgress(download);
        const progressBar = progressPercent > 0 ? `
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progressPercent}%"></div>
            </div>
            <span class="progress-text">${progressPercent}%</span>
        ` : '<span class="progress-text">-</span>';

        row.innerHTML = `
            <td>
                <div class="download-title">${this.escapeHtml(download.title)}</div>
                <div class="download-meta">${this.escapeHtml(download.author || 'Unknown')}</div>
            </td>
            <td>${this.escapeHtml(download.author || 'Unknown')}</td>
            <td>${this.escapeHtml(download.source)}</td>
            <td>
                <span class="status-badge ${statusClass}">${statusText}</span>
            </td>
            <td>
                ${progressBar}
            </td>
            <td>
                <div class="download-actions">
                    ${this.getActionButtons(download)}
                </div>
            </td>
        `;

        return row;
    }

    /**
     * Get action buttons for download
     */
    getActionButtons(download) {
        const actions = [];

        switch (download.status) {
            case 'queued':
                actions.push('<button class="btn btn-secondary btn-sm" onclick="cancelDownload(' + download.id + ')">Cancel</button>');
                break;
            case 'downloading':
                actions.push('<button class="btn btn-warning btn-sm" onclick="pauseDownload(' + download.id + ')">Pause</button>');
                actions.push('<button class="btn btn-danger btn-sm" onclick="cancelDownload(' + download.id + ')">Cancel</button>');
                break;
            case 'failed':
                if (download.retry_count < download.max_retries) {
                    actions.push('<button class="btn btn-primary btn-sm" onclick="retryDownload(' + download.id + ')">Retry</button>');
                }
                actions.push('<button class="btn btn-danger btn-sm" onclick="removeDownload(' + download.id + ')">Remove</button>');
                break;
            case 'abandoned':
                actions.push('<button class="btn btn-danger btn-sm" onclick="removeDownload(' + download.id + ')">Remove</button>');
                break;
            case 'completed':
                actions.push('<button class="btn btn-success btn-sm" onclick="viewDownload(' + download.id + ')">View</button>');
                break;
        }

        return actions.join('');
    }

    /**
     * Get status class for styling
     */
    getStatusClass(status) {
        const classes = {
            'queued': 'status-queued',
            'downloading': 'status-downloading',
            'completed': 'status-completed',
            'failed': 'status-failed',
            'abandoned': 'status-abandoned'
        };
        return classes[status] || 'status-unknown';
    }

    /**
     * Format status text for display
     */
    formatStatusText(status) {
        const texts = {
            'queued': 'Queued',
            'downloading': 'Downloading',
            'completed': 'Completed',
            'failed': 'Failed',
            'abandoned': 'Abandoned'
        };
        return texts[status] || status;
    }

    /**
     * Calculate progress percentage
     */
    calculateProgress(download) {
        // This would need to be enhanced with actual qBittorrent progress data
        // For now, return a mock progress based on status
        if (download.status === 'completed') return 100;
        if (download.status === 'downloading') return Math.floor(Math.random() * 90) + 10;
        return 0;
    }

    /**
     * Render empty downloads state
     */
    renderEmptyDownloads(message) {
        const container = document.getElementById('downloads-content');
        container.innerHTML = `
            <div class="empty-state">
                <p>${message}</p>
            </div>
        `;
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DownloadsAPI;
}