/**
 * Real-time Service
 * Handles WebSocket connections and real-time data updates
 */

class RealtimeService {
    constructor() {
        this.ws = null;
        this.eventListeners = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.isConnected = false;
        this.heartbeatInterval = null;
        this.heartbeatTimeout = null;

        // Configuration
        this.config = {
            url: this.getWebSocketUrl(),
            heartbeatInterval: 30000, // 30 seconds
            heartbeatTimeout: 10000, // 10 seconds
            reconnectDelayMax: 30000 // Max 30 seconds
        };
    }

    /**
     * Get WebSocket URL based on current location
     * @returns {string} WebSocket URL
     */
    getWebSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/status`;
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return;
        }

        try {
            console.log('Connecting to WebSocket:', this.config.url);
            this.ws = new WebSocket(this.config.url);

            this.ws.onopen = this.onOpen.bind(this);
            this.ws.onmessage = this.onMessage.bind(this);
            this.ws.onclose = this.onClose.bind(this);
            this.ws.onerror = this.onError.bind(this);

        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.handleConnectionError(error);
        }
    }

    /**
     * Disconnect from WebSocket server
     */
    disconnect() {
        console.log('Disconnecting from WebSocket');

        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }

        if (this.heartbeatTimeout) {
            clearTimeout(this.heartbeatTimeout);
            this.heartbeatTimeout = null;
        }

        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }

        this.isConnected = false;
        this.emit('disconnected');
    }

    /**
     * Reconnect to WebSocket server with exponential backoff
     */
    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            this.emit('maxReconnectAttemptsReached');
            return;
        }

        this.reconnectAttempts++;
        const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), this.config.reconnectDelayMax);

        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    /**
     * Handle successful WebSocket connection
     */
    onOpen(event) {
        console.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000; // Reset delay

        // Start heartbeat
        this.startHeartbeat();

        this.emit('connected', event);
    }

    /**
     * Handle WebSocket message
     */
    onMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error, event.data);
        }
    }

    /**
     * Handle WebSocket close
     */
    onClose(event) {
        console.log('WebSocket closed:', event.code, event.reason);
        this.isConnected = false;

        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }

        this.emit('disconnected', event);

        // Attempt to reconnect unless it was a clean close
        if (event.code !== 1000) {
            this.reconnect();
        }
    }

    /**
     * Handle WebSocket error
     */
    onError(event) {
        console.error('WebSocket error:', event);
        this.emit('error', event);
    }

    /**
     * Handle incoming message based on type
     */
    handleMessage(data) {
        switch (data.type) {
            case 'heartbeat':
                this.handleHeartbeat(data);
                break;
            case 'status_update':
                this.emit('statusUpdate', data.payload);
                break;
            case 'crawler_update':
                this.emit('crawlerUpdate', data.payload);
                break;
            case 'download_update':
                this.emit('downloadUpdate', data.payload);
                break;
            case 'resource_update':
                this.emit('resourceUpdate', data.payload);
                break;
            case 'log_update':
                this.emit('logUpdate', data.payload);
                break;
            case 'alert':
                this.emit('alert', data.payload);
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    /**
     * Handle heartbeat message
     */
    handleHeartbeat(data) {
        // Reset heartbeat timeout
        if (this.heartbeatTimeout) {
            clearTimeout(this.heartbeatTimeout);
        }

        // Send heartbeat response
        this.send({ type: 'heartbeat_ack', timestamp: Date.now() });
    }

    /**
     * Start heartbeat mechanism
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'heartbeat', timestamp: Date.now() });

                // Set timeout for heartbeat response
                this.heartbeatTimeout = setTimeout(() => {
                    console.warn('Heartbeat timeout - connection may be lost');
                    this.emit('heartbeatTimeout');
                    this.ws.close(1000, 'Heartbeat timeout');
                }, this.config.heartbeatTimeout);
            }
        }, this.config.heartbeatInterval);
    }

    /**
     * Send message to WebSocket server
     */
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(data));
            } catch (error) {
                console.error('Failed to send WebSocket message:', error);
            }
        } else {
            console.warn('WebSocket not connected, cannot send message');
        }
    }

    /**
     * Subscribe to real-time updates for specific data type
     */
    subscribe(type, callback) {
        if (!this.eventListeners[type]) {
            this.eventListeners[type] = [];
        }
        this.eventListeners[type].push(callback);

        // Send subscription message to server
        this.send({
            type: 'subscribe',
            dataType: type
        });
    }

    /**
     * Unsubscribe from real-time updates
     */
    unsubscribe(type, callback) {
        if (this.eventListeners[type]) {
            const index = this.eventListeners[type].indexOf(callback);
            if (index > -1) {
                this.eventListeners[type].splice(index, 1);
            }
        }

        // Send unsubscription message to server
        this.send({
            type: 'unsubscribe',
            dataType: type
        });
    }

    /**
     * Emit event to all listeners
     */
    emit(eventType, data) {
        if (this.eventListeners[eventType]) {
            this.eventListeners[eventType].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in ${eventType} callback:`, error);
                }
            });
        }
    }

    /**
     * Add event listener
     */
    addEventListener(eventType, callback) {
        if (!this.eventListeners[eventType]) {
            this.eventListeners[eventType] = [];
        }
        this.eventListeners[eventType].push(callback);
    }

    /**
     * Remove event listener
     */
    removeEventListener(eventType, callback) {
        if (this.eventListeners[eventType]) {
            const index = this.eventListeners[eventType].indexOf(callback);
            if (index > -1) {
                this.eventListeners[eventType].splice(index, 1);
            }
        }
    }

    /**
     * Handle connection error
     */
    handleConnectionError(error) {
        console.error('WebSocket connection error:', error);
        this.emit('connectionError', error);

        // Attempt to reconnect
        this.reconnect();
    }

    /**
     * Get connection status
     */
    getStatus() {
        return {
            connected: this.isConnected,
            readyState: this.ws ? this.ws.readyState : WebSocket.CLOSED,
            reconnectAttempts: this.reconnectAttempts,
            url: this.config.url
        };
    }

    /**
     * Send a ping message
     */
    ping() {
        this.send({ type: 'ping', timestamp: Date.now() });
    }

    /**
     * Request full status update
     */
    requestFullUpdate() {
        this.send({ type: 'request_full_update' });
    }

    /**
     * Request specific data update
     */
    requestUpdate(dataType) {
        this.send({ type: 'request_update', dataType: dataType });
    }

    /**
     * Cleanup resources
     */
    destroy() {
        this.disconnect();
        this.eventListeners = {};
    }
}

// WebSocket ready state constants for reference
RealtimeService.CONNECTING = 0;
RealtimeService.OPEN = 1;
RealtimeService.CLOSING = 2;
RealtimeService.CLOSED = 3;