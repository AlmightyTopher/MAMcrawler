/**
 * Time Utilities
 * Functions for formatting, calculating, and manipulating time values
 */

class TimeUtils {
    /**
     * Format a timestamp to a human-readable string
     * @param {string|Date} timestamp - The timestamp to format
     * @param {boolean} relative - Whether to show relative time (e.g., "2 minutes ago")
     * @returns {string} Formatted time string
     */
    static formatTimestamp(timestamp, relative = false) {
        const date = new Date(timestamp);

        if (relative) {
            return this.formatRelativeTime(date);
        }

        return date.toLocaleString();
    }

    /**
     * Format time as relative (e.g., "2 minutes ago", "in 3 hours")
     * @param {Date} date - The date to format
     * @returns {string} Relative time string
     */
    static formatRelativeTime(date) {
        const now = new Date();
        const diffMs = date - now;
        const diffSeconds = Math.abs(diffMs) / 1000;
        const diffMinutes = diffSeconds / 60;
        const diffHours = diffMinutes / 60;
        const diffDays = diffHours / 24;

        const isPast = diffMs < 0;
        const suffix = isPast ? 'ago' : 'from now';

        if (diffSeconds < 60) {
            return isPast ? 'just now' : 'in a few seconds';
        } else if (diffMinutes < 60) {
            const minutes = Math.floor(diffMinutes);
            return `${minutes} minute${minutes !== 1 ? 's' : ''} ${suffix}`;
        } else if (diffHours < 24) {
            const hours = Math.floor(diffHours);
            return `${hours} hour${hours !== 1 ? 's' : ''} ${suffix}`;
        } else if (diffDays < 7) {
            const days = Math.floor(diffDays);
            return `${days} day${days !== 1 ? 's' : ''} ${suffix}`;
        } else {
            return date.toLocaleDateString();
        }
    }

    /**
     * Format duration in seconds to human-readable string
     * @param {number} seconds - Duration in seconds
     * @returns {string} Formatted duration string
     */
    static formatDuration(seconds) {
        if (!seconds || seconds < 0) return '0s';

        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        const parts = [];
        if (days > 0) parts.push(`${days}d`);
        if (hours > 0) parts.push(`${hours}h`);
        if (minutes > 0) parts.push(`${minutes}m`);
        if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

        return parts.join(' ');
    }

    /**
     * Calculate ETA (Estimated Time of Arrival)
     * @param {number} current - Current progress (0-1)
     * @param {number} rate - Progress rate per second
     * @param {number} total - Total amount
     * @returns {number|null} ETA in seconds, or null if cannot calculate
     */
    static calculateETA(current, rate, total) {
        if (!rate || rate <= 0 || !total || total <= 0) return null;

        const remaining = total - (current * total);
        if (remaining <= 0) return 0;

        return remaining / rate;
    }

    /**
     * Format ETA to human-readable string
     * @param {number} etaSeconds - ETA in seconds
     * @returns {string} Formatted ETA string
     */
    static formatETA(etaSeconds) {
        if (etaSeconds === null || etaSeconds === undefined) return 'Unknown';
        if (etaSeconds === 0) return 'Complete';
        if (etaSeconds < 0) return 'Overdue';

        return this.formatDuration(etaSeconds);
    }

    /**
     * Calculate transfer rate (bytes per second)
     * @param {number} bytes - Number of bytes transferred
     * @param {number} seconds - Time elapsed in seconds
     * @returns {number} Transfer rate in bytes per second
     */
    static calculateTransferRate(bytes, seconds) {
        if (!seconds || seconds <= 0) return 0;
        return bytes / seconds;
    }

    /**
     * Format transfer rate to human-readable string
     * @param {number} bytesPerSecond - Transfer rate in bytes per second
     * @returns {string} Formatted transfer rate string
     */
    static formatTransferRate(bytesPerSecond) {
        if (!bytesPerSecond || bytesPerSecond <= 0) return '0 B/s';

        const units = ['B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s'];
        let value = bytesPerSecond;
        let unitIndex = 0;

        while (value >= 1024 && unitIndex < units.length - 1) {
            value /= 1024;
            unitIndex++;
        }

        return `${value.toFixed(1)} ${units[unitIndex]}`;
    }

    /**
     * Format file size to human-readable string
     * @param {number} bytes - Size in bytes
     * @returns {string} Formatted size string
     */
    static formatFileSize(bytes) {
        if (!bytes || bytes <= 0) return '0 B';

        const units = ['B', 'KB', 'MB', 'GB', 'TB'];
        let value = bytes;
        let unitIndex = 0;

        while (value >= 1024 && unitIndex < units.length - 1) {
            value /= 1024;
            unitIndex++;
        }

        return `${value.toFixed(1)} ${units[unitIndex]}`;
    }

    /**
     * Parse duration string to seconds
     * @param {string} durationStr - Duration string (e.g., "2h 30m", "1d 5h")
     * @returns {number} Duration in seconds
     */
    static parseDuration(durationStr) {
        if (!durationStr) return 0;

        const regex = /(\d+)([dhms])/g;
        let totalSeconds = 0;
        let match;

        while ((match = regex.exec(durationStr.toLowerCase())) !== null) {
            const value = parseInt(match[1]);
            const unit = match[2];

            switch (unit) {
                case 'd':
                    totalSeconds += value * 86400;
                    break;
                case 'h':
                    totalSeconds += value * 3600;
                    break;
                case 'm':
                    totalSeconds += value * 60;
                    break;
                case 's':
                    totalSeconds += value;
                    break;
            }
        }

        return totalSeconds;
    }

    /**
     * Get time range for a given period
     * @param {string} period - Time period (e.g., '1h', '6h', '24h', '7d')
     * @returns {Object} Object with start and end dates
     */
    static getTimeRange(period) {
        const now = new Date();
        const end = now;

        let start;
        const match = period.match(/^(\d+)([hd])$/);

        if (!match) {
            // Default to 1 hour
            start = new Date(now.getTime() - (60 * 60 * 1000));
        } else {
            const value = parseInt(match[1]);
            const unit = match[2];

            if (unit === 'h') {
                start = new Date(now.getTime() - (value * 60 * 60 * 1000));
            } else if (unit === 'd') {
                start = new Date(now.getTime() - (value * 24 * 60 * 60 * 1000));
            }
        }

        return { start, end };
    }

    /**
     * Check if a timestamp is within a time range
     * @param {string|Date} timestamp - The timestamp to check
     * @param {Date} start - Start of range
     * @param {Date} end - End of range
     * @returns {boolean} Whether timestamp is in range
     */
    static isInTimeRange(timestamp, start, end) {
        const date = new Date(timestamp);
        return date >= start && date <= end;
    }

    /**
     * Get the start of a time period (e.g., start of hour, day, week)
     * @param {Date} date - The date to get start for
     * @param {string} period - Period type ('hour', 'day', 'week')
     * @returns {Date} Start of the period
     */
    static getPeriodStart(date, period) {
        const d = new Date(date);

        switch (period) {
            case 'hour':
                d.setMinutes(0, 0, 0);
                break;
            case 'day':
                d.setHours(0, 0, 0, 0);
                break;
            case 'week':
                const day = d.getDay();
                const diff = d.getDate() - day;
                d.setDate(diff);
                d.setHours(0, 0, 0, 0);
                break;
        }

        return d;
    }

    /**
     * Format uptime duration
     * @param {number} seconds - Uptime in seconds
     * @returns {string} Formatted uptime string
     */
    static formatUptime(seconds) {
        if (!seconds || seconds < 0) return '0s';

        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);

        if (days > 0) {
            return `${days}d ${hours}h ${minutes}m`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }
}