/**
 * Download Manager Component
 * Handles download queue display, progress tracking, and download controls
 */

class DownloadManager {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.downloadsAPI = new DownloadsAPI(dashboard);
        this.activeDownloads = new Map();
        this.refreshInterval = null;
    }

    /**
     * Initialize the download manager
     */
    init() {
        // Set up the API instance on the dashboard
        this.dashboard.downloadsAPI = this.downloadsAPI;

        // Bind methods to dashboard
        this.dashboard.loadDownloadsData = this.loadDownloadsData.bind(this);
        this.dashboard.refreshDownloads = this.refreshDownloads.bind(this);

        // Start auto-refresh for active downloads
        this.startAutoRefresh();
    }

    /**
     * Load downloads data
     */
    async loadDownloadsData() {
        await this.downloadsAPI.loadDownloadsData();
    }

    /**
     * Refresh downloads data
     */
    async refreshDownloads() {
        await this.loadDownloadsData();
    }

    /**
     * Start auto-refresh for active downloads
     */
    startAutoRefresh() {
        // Refresh every 5 seconds when there are active downloads
        this.refreshInterval = setInterval(() => {
            if (this.hasActiveDownloads()) {
                this.refreshDownloads();
            }
        }, 5000);
    }

    /**
     * Stop auto-refresh
     */
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Check if there are active downloads
     */
    hasActiveDownloads() {
        const activeCount = document.getElementById('active-downloads-count');
        return activeCount && parseInt(activeCount.textContent) > 0;
    }

    /**
     * Pause a download
     */
    async pauseDownload(downloadId) {
        try {
            // This would need to integrate with qBittorrent API
            alert('Pause functionality would be implemented here for download ID: ' + downloadId);
            await this.refreshDownloads();
        } catch (error) {
            console.error('Failed to pause download:', error);
            alert('Failed to pause download');
        }
    }

    /**
     * Resume a download
     */
    async resumeDownload(downloadId) {
        try {
            // This would need to integrate with qBittorrent API
            alert('Resume functionality would be implemented here for download ID: ' + downloadId);
            await this.refreshDownloads();
        } catch (error) {
            console.error('Failed to resume download:', error);
            alert('Failed to resume download');
        }
    }

    /**
     * Cancel a download
     */
    async cancelDownload(downloadId) {
        if (!confirm('Cancel this download?')) return;

        try {
            await this.downloadsAPI.updateDownloadStatus(downloadId, 'cancelled');
            alert('Download cancelled');
            await this.refreshDownloads();
        } catch (error) {
            console.error('Failed to cancel download:', error);
            alert('Failed to cancel download');
        }
    }

    /**
     * Retry a failed download
     */
    async retryDownload(downloadId) {
        try {
            await this.downloadsAPI.scheduleDownloadRetry(downloadId);
            alert('Download retry scheduled');
            await this.refreshDownloads();
        } catch (error) {
            console.error('Failed to retry download:', error);
            alert('Failed to retry download');
        }
    }

    /**
     * Remove a download from the queue
     */
    async removeDownload(downloadId) {
        if (!confirm('Remove this download from the queue?')) return;

        try {
            await this.downloadsAPI.removeDownload(downloadId);
            alert('Download removed');
            await this.refreshDownloads();
        } catch (error) {
            console.error('Failed to remove download:', error);
            alert('Failed to remove download');
        }
    }

    /**
     * View download details
     */
    async viewDownload(downloadId) {
        try {
            const downloadData = await this.downloadsAPI.getDownload(downloadId);
            this.showDownloadDetailsModal(downloadData);
        } catch (error) {
            console.error('Failed to load download details:', error);
            alert('Failed to load download details');
        }
    }

    /**
     * Show download details modal
     */
    showDownloadDetailsModal(download) {
        // Remove existing modal
        const existingModal = document.getElementById('download-details-modal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.id = 'download-details-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content download-details-modal">
                <div class="modal-header">
                    <h2>Download Details</h2>
                    <button class="modal-close" onclick="closeDownloadDetailsModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="download-info-grid">
                        <div class="info-section">
                            <h3>Book Information</h3>
                            <div class="info-row">
                                <strong>Title:</strong>
                                <span>${this.escapeHtml(download.title)}</span>
                            </div>
                            <div class="info-row">
                                <strong>Author:</strong>
                                <span>${this.escapeHtml(download.author || 'Unknown')}</span>
                            </div>
                            <div class="info-row">
                                <strong>Source:</strong>
                                <span>${this.escapeHtml(download.source)}</span>
                            </div>
                        </div>

                        <div class="info-section">
                            <h3>Download Status</h3>
                            <div class="info-row">
                                <strong>Status:</strong>
                                <span class="status-badge ${download.status}">${download.status}</span>
                            </div>
                            <div class="info-row">
                                <strong>Progress:</strong>
                                <span>${this.calculateProgress(download)}%</span>
                            </div>
                            <div class="info-row">
                                <strong>Created:</strong>
                                <span>${this.dashboard.formatDate(download.created_at)}</span>
                            </div>
                            <div class="info-row">
                                <strong>Updated:</strong>
                                <span>${this.dashboard.formatDate(download.updated_at)}</span>
                            </div>
                        </div>

                        <div class="info-section">
                            <h3>Technical Details</h3>
                            <div class="info-row">
                                <strong>Download ID:</strong>
                                <span>${download.id}</span>
                            </div>
                            <div class="info-row">
                                <strong>Book ID:</strong>
                                <span>${download.book_id || 'N/A'}</span>
                            </div>
                            <div class="info-row">
                                <strong>Retry Count:</strong>
                                <span>${download.retry_count || 0}</span>
                            </div>
                            <div class="info-row">
                                <strong>qBittorrent Hash:</strong>
                                <span class="mono">${download.qb_hash || 'N/A'}</span>
                            </div>
                        </div>
                    </div>

                    ${download.error_msg ? `
                        <div class="error-section">
                            <h3>Error Information</h3>
                            <p class="error-message">${this.escapeHtml(download.error_msg)}</p>
                        </div>
                    ` : ''}

                    <div class="download-actions">
                        ${this.getDetailedActionButtons(download)}
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeDownloadDetailsModal();
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeDownloadDetailsModal();
            }
        });
    }

    /**
     * Get detailed action buttons for download
     */
    getDetailedActionButtons(download) {
        const actions = [];

        switch (download.status) {
            case 'queued':
                actions.push('<button class="btn btn-danger" onclick="cancelDownloadFromModal(' + download.id + ')">Cancel Download</button>');
                break;
            case 'downloading':
                actions.push('<button class="btn btn-warning" onclick="pauseDownloadFromModal(' + download.id + ')">Pause</button>');
                actions.push('<button class="btn btn-danger" onclick="cancelDownloadFromModal(' + download.id + ')">Cancel</button>');
                break;
            case 'paused':
                actions.push('<button class="btn btn-success" onclick="resumeDownloadFromModal(' + download.id + ')">Resume</button>');
                actions.push('<button class="btn btn-danger" onclick="cancelDownloadFromModal(' + download.id + ')">Cancel</button>');
                break;
            case 'failed':
                if (download.retry_count < (download.max_retries || 3)) {
                    actions.push('<button class="btn btn-primary" onclick="retryDownloadFromModal(' + download.id + ')">Retry Download</button>');
                }
                actions.push('<button class="btn btn-danger" onclick="removeDownloadFromModal(' + download.id + ')">Remove from Queue</button>');
                break;
            case 'completed':
                actions.push('<button class="btn btn-success" onclick="viewInLibrary(' + download.book_id + ')">View in Library</button>');
                actions.push('<button class="btn btn-danger" onclick="removeDownloadFromModal(' + download.id + ')">Remove from History</button>');
                break;
            case 'cancelled':
            case 'abandoned':
                actions.push('<button class="btn btn-primary" onclick="retryDownloadFromModal(' + download.id + ')">Retry Download</button>');
                actions.push('<button class="btn btn-danger" onclick="removeDownloadFromModal(' + download.id + ')">Remove from Queue</button>');
                break;
        }

        return actions.join('');
    }

    /**
     * Close download details modal
     */
    closeDownloadDetailsModal() {
        const modal = document.getElementById('download-details-modal');
        if (modal) {
            modal.remove();
        }
    }

    /**
     * View completed download in library
     */
    viewInLibrary(bookId) {
        if (bookId) {
            // Switch to library tab and show book details
            this.dashboard.switchTab('library');
            if (this.dashboard.libraryView) {
                this.dashboard.libraryView.showBookDetails(bookId);
            }
        }
        this.closeDownloadDetailsModal();
    }

    /**
     * Calculate download progress (mock implementation)
     */
    calculateProgress(download) {
        if (download.status === 'completed') return 100;
        if (download.status === 'downloading') {
            // This would come from qBittorrent API
            return Math.floor(Math.random() * 90) + 10;
        }
        return 0;
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

// Global functions for modal button handlers
function pauseDownload(downloadId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.downloadManager) {
        window.mamcrawlerDashboard.downloadManager.pauseDownload(downloadId);
    }
}

function resumeDownload(downloadId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.downloadManager) {
        window.mamcrawlerDashboard.downloadManager.resumeDownload(downloadId);
    }
}

function cancelDownload(downloadId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.downloadManager) {
        window.mamcrawlerDashboard.downloadManager.cancelDownload(downloadId);
    }
}

function retryDownload(downloadId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.downloadManager) {
        window.mamcrawlerDashboard.downloadManager.retryDownload(downloadId);
    }
}

function removeDownload(downloadId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.downloadManager) {
        window.mamcrawlerDashboard.downloadManager.removeDownload(downloadId);
    }
}

function viewDownload(downloadId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.downloadManager) {
        window.mamcrawlerDashboard.downloadManager.viewDownload(downloadId);
    }
}

// Modal-specific functions
function closeDownloadDetailsModal() {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.downloadManager) {
        window.mamcrawlerDashboard.downloadManager.closeDownloadDetailsModal();
    }
}

function cancelDownloadFromModal(downloadId) {
    cancelDownload(downloadId);
    closeDownloadDetailsModal();
}

function pauseDownloadFromModal(downloadId) {
    pauseDownload(downloadId);
    closeDownloadDetailsModal();
}

function resumeDownloadFromModal(downloadId) {
    resumeDownload(downloadId);
    closeDownloadDetailsModal();
}

function retryDownloadFromModal(downloadId) {
    retryDownload(downloadId);
    closeDownloadDetailsModal();
}

function removeDownloadFromModal(downloadId) {
    removeDownload(downloadId);
    closeDownloadDetailsModal();
}

function viewInLibrary(bookId) {
    if (window.mamcrawlerDashboard && window.mamcrawlerDashboard.downloadManager) {
        window.mamcrawlerDashboard.downloadManager.viewInLibrary(bookId);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DownloadManager;
}