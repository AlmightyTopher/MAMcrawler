/**
 * Monitoring Service for MAMcrawler Admin Panel
 * Handles system monitoring, metrics, and real-time data
 */

class MonitoringService {
    constructor() {
        this.apiBase = '/api/admin';
        this.updateInterval = 30000; // 30 seconds
        this.intervals = new Map();
        this.websocket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    /**
     * Get system health status
     */
    async getSystemHealth() {
        try {
            const response = await window.authService.apiCall('/monitoring/health');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get system health:', error);
            throw error;
        }
    }

    /**
     * Get system metrics
     */
    async getSystemMetrics() {
        try {
            const response = await window.authService.apiCall('/monitoring/metrics');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get system metrics:', error);
            throw error;
        }
    }

    /**
     * Get download statistics
     */
    async getDownloadStats() {
        try {
            const response = await window.authService.apiCall('/monitoring/downloads');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get download stats:', error);
            throw error;
        }
    }

    /**
     * Get crawler performance data
     */
    async getCrawlerPerformance() {
        try {
            const response = await window.authService.apiCall('/monitoring/crawler');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get crawler performance:', error);
            throw error;
        }
    }

    /**
     * Get error logs
     */
    async getErrorLogs(limit = 100, level = null) {
        try {
            let url = `/monitoring/logs/errors?limit=${limit}`;
            if (level) {
                url += `&level=${level}`;
            }
            const response = await window.authService.apiCall(url);
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get error logs:', error);
            throw error;
        }
    }

    /**
     * Get system logs
     */
    async getSystemLogs(limit = 100, component = null) {
        try {
            let url = `/monitoring/logs/system?limit=${limit}`;
            if (component) {
                url += `&component=${component}`;
            }
            const response = await window.authService.apiCall(url);
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get system logs:', error);
            throw error;
        }
    }

    /**
     * Get task execution history
     */
    async getTaskHistory(limit = 50, status = null) {
        try {
            let url = `/monitoring/tasks?limit=${limit}`;
            if (status) {
                url += `&status=${status}`;
            }
            const response = await window.authService.apiCall(url);
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get task history:', error);
            throw error;
        }
    }

    /**
     * Get failed attempts summary
     */
    async getFailedAttempts(limit = 50) {
        try {
            const response = await window.authService.apiCall(`/monitoring/failed-attempts?limit=${limit}`);
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get failed attempts:', error);
            throw error;
        }
    }

    /**
     * Get real-time metrics
     */
    async getRealtimeMetrics() {
        try {
            const response = await window.authService.apiCall('/monitoring/realtime');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get realtime metrics:', error);
            throw error;
        }
    }

    /**
     * Start real-time monitoring
     */
    startRealtimeMonitoring(callback) {
        this.stopRealtimeMonitoring();

        const updateData = async () => {
            try {
                const data = await this.getRealtimeMetrics();
                if (callback && data) {
                    callback(data);
                }
            } catch (error) {
                console.error('Realtime monitoring error:', error);
            }
        };

        // Initial update
        updateData();

        // Set up interval
        const intervalId = setInterval(updateData, this.updateInterval);
        this.intervals.set('realtime', intervalId);

        return intervalId;
    }

    /**
     * Stop real-time monitoring
     */
    stopRealtimeMonitoring() {
        const intervalId = this.intervals.get('realtime');
        if (intervalId) {
            clearInterval(intervalId);
            this.intervals.delete('realtime');
        }
    }

    /**
     * Connect to WebSocket for real-time updates
     */
    connectWebSocket(onMessage, onError, onClose) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            return;
        }

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/admin/monitoring/ws`;

        try {
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = (event) => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;

                // Send authentication
                const token = window.authService.getToken();
                if (token) {
                    this.websocket.send(JSON.stringify({
                        type: 'auth',
                        token: token
                    }));
                }
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (onMessage) {
                        onMessage(data);
                    }
                } catch (error) {
                    console.error('WebSocket message parse error:', error);
                }
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                if (onError) {
                    onError(error);
                }
            };

            this.websocket.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);

                if (onClose) {
                    onClose(event);
                }

                // Attempt to reconnect if not a normal closure
                if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.attemptReconnect(onMessage, onError, onClose);
                }
            };

        } catch (error) {
            console.error('WebSocket connection error:', error);
            if (onError) {
                onError(error);
            }
        }
    }

    /**
     * Attempt to reconnect WebSocket
     */
    attemptReconnect(onMessage, onError, onClose) {
        this.reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

        console.log(`Attempting WebSocket reconnect ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay}ms`);

        setTimeout(() => {
            this.connectWebSocket(onMessage, onError, onClose);
        }, delay);
    }

    /**
     * Disconnect WebSocket
     */
    disconnectWebSocket() {
        if (this.websocket) {
            this.websocket.close(1000, 'Client disconnect');
            this.websocket = null;
        }
        this.reconnectAttempts = 0;
    }

    /**
     * Send WebSocket message
     */
    sendWebSocketMessage(message) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify(message));
        } else {
            console.warn('WebSocket not connected, cannot send message');
        }
    }

    /**
     * Get performance report
     */
    async getPerformanceReport(timeRange = '24h') {
        try {
            const response = await window.authService.apiCall(`/monitoring/performance?range=${timeRange}`);
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get performance report:', error);
            throw error;
        }
    }

    /**
     * Get system alerts
     */
    async getSystemAlerts(activeOnly = true) {
        try {
            const response = await window.authService.apiCall(`/monitoring/alerts?active=${activeOnly}`);
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get system alerts:', error);
            throw error;
        }
    }

    /**
     * Acknowledge alert
     */
    async acknowledgeAlert(alertId) {
        try {
            const response = await window.authService.apiCall(`/monitoring/alerts/${alertId}/acknowledge`, {
                method: 'POST'
            });
            return response;
        } catch (error) {
            console.error('Failed to acknowledge alert:', error);
            throw error;
        }
    }

    /**
     * Export monitoring data
     */
    async exportMonitoringData(type, format = 'json', timeRange = '24h') {
        try {
            const response = await window.authService.apiCall(`/monitoring/export/${type}?format=${format}&range=${timeRange}`);
            if (response.success) {
                // Create download link
                const blob = new Blob([JSON.stringify(response.data, null, 2)], {
                    type: 'application/json'
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `mamcrawler-monitoring-${type}-${new Date().toISOString().split('T')[0]}.${format}`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                return { success: true };
            } else {
                return response;
            }
        } catch (error) {
            console.error('Failed to export monitoring data:', error);
            throw error;
        }
    }

    /**
     * Clear old logs
     */
    async clearOldLogs(olderThanDays = 30) {
        try {
            const response = await window.authService.apiCall('/monitoring/logs/clear', {
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
     * Get monitoring configuration
     */
    async getMonitoringConfig() {
        try {
            const response = await window.authService.apiCall('/monitoring/config');
            return response.success ? response.data : null;
        } catch (error) {
            console.error('Failed to get monitoring config:', error);
            throw error;
        }
    }

    /**
     * Update monitoring configuration
     */
    async updateMonitoringConfig(config) {
        try {
            const response = await window.authService.apiCall('/monitoring/config', {
                method: 'PUT',
                body: JSON.stringify(config)
            });
            return response;
        } catch (error) {
            console.error('Failed to update monitoring config:', error);
            throw error;
        }
    }

    /**
     * Cleanup resources
     */
    cleanup() {
        this.stopRealtimeMonitoring();
        this.disconnectWebSocket();

        // Clear all intervals
        this.intervals.forEach((intervalId) => {
            clearInterval(intervalId);
        });
        this.intervals.clear();
    }
}

// Create global instance
window.monitoringService = new MonitoringService();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.monitoringService) {
        window.monitoringService.cleanup();
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MonitoringService;
}