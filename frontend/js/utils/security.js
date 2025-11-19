/**
 * Security Utilities for MAMcrawler Admin Panel
 * Provides security helper functions and CSRF protection
 */

class SecurityUtils {
    constructor() {
        this.csrfToken = null;
        this.init();
    }

    /**
     * Initialize security utilities
     */
    init() {
        this.generateCSRFToken();
        this.setupSecurityHeaders();
    }

    /**
     * Generate CSRF token
     */
    generateCSRFToken() {
        if (!this.csrfToken) {
            this.csrfToken = this.generateRandomString(32);
            // Store in session storage for persistence
            sessionStorage.setItem('csrf_token', this.csrfToken);
        }
        return this.csrfToken;
    }

    /**
     * Get CSRF token
     */
    getCSRFToken() {
        if (!this.csrfToken) {
            this.csrfToken = sessionStorage.getItem('csrf_token') || this.generateCSRFToken();
        }
        return this.csrfToken;
    }

    /**
     * Setup security headers for requests
     */
    setupSecurityHeaders() {
        // Override fetch to include security headers
        const originalFetch = window.fetch;
        window.fetch = (url, options = {}) => {
            const headers = new Headers(options.headers || {});

            // Add CSRF token for non-GET requests
            if (options.method && options.method !== 'GET') {
                headers.set('X-CSRF-Token', this.getCSRFToken());
            }

            // Add security headers
            headers.set('X-Requested-With', 'XMLHttpRequest');
            headers.set('X-Client-Version', '1.0.0');

            // Add Content-Type if not set and body exists
            if (options.body && !headers.has('Content-Type')) {
                headers.set('Content-Type', 'application/json');
            }

            return originalFetch(url, {
                ...options,
                headers
            });
        };
    }

    /**
     * Sanitize HTML content
     */
    sanitizeHTML(html) {
        const temp = document.createElement('div');
        temp.textContent = html;
        return temp.innerHTML;
    }

    /**
     * Sanitize user input
     */
    sanitizeInput(input, options = {}) {
        if (typeof input !== 'string') {
            return input;
        }

        let sanitized = input;

        // Remove null bytes
        sanitized = sanitized.replace(/\0/g, '');

        // Remove potential script tags
        sanitized = sanitized.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
        sanitized = sanitized.replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '');

        // Remove event handlers
        sanitized = sanitized.replace(/on\w+="[^"]*"/gi, '');
        sanitized = sanitized.replace(/on\w+='[^']*'/gi, '');

        // Remove javascript: URLs
        sanitized = sanitized.replace(/javascript:[^"']*/gi, '');

        // Remove data: URLs if not allowed
        if (!options.allowDataUrls) {
            sanitized = sanitized.replace(/data:[^"']*/gi, '');
        }

        // Trim whitespace
        sanitized = sanitized.trim();

        // Limit length if specified
        if (options.maxLength && sanitized.length > options.maxLength) {
            sanitized = sanitized.substring(0, options.maxLength);
        }

        return sanitized;
    }

    /**
     * Validate and sanitize form data
     */
    sanitizeFormData(formData) {
        const sanitized = new FormData();

        for (const [key, value] of formData.entries()) {
            if (typeof value === 'string') {
                sanitized.set(key, this.sanitizeInput(value));
            } else {
                sanitized.set(key, value);
            }
        }

        return sanitized;
    }

    /**
     * Generate random string
     */
    generateRandomString(length = 16) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return result;
    }

    /**
     * Generate secure random bytes (if crypto API available)
     */
    generateSecureRandom(length = 16) {
        if (window.crypto && window.crypto.getRandomValues) {
            const array = new Uint8Array(length);
            window.crypto.getRandomValues(array);
            return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
        } else {
            // Fallback to less secure method
            return this.generateRandomString(length * 2);
        }
    }

    /**
     * Hash string using Web Crypto API
     */
    async hashString(input, algorithm = 'SHA-256') {
        if (!window.crypto || !window.crypto.subtle) {
            throw new Error('Web Crypto API not available');
        }

        const encoder = new TextEncoder();
        const data = encoder.encode(input);
        const hashBuffer = await window.crypto.subtle.digest(algorithm, data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    /**
     * Validate password strength
     */
    validatePasswordStrength(password) {
        const checks = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            numbers: /\d/.test(password),
            special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
        };

        const score = Object.values(checks).filter(Boolean).length;
        let strength = 'weak';

        if (score >= 4) strength = 'medium';
        if (score >= 5) strength = 'strong';

        return {
            score,
            strength,
            checks,
            isValid: score >= 4
        };
    }

    /**
     * Check if content security policy is supported
     */
    isCSPEnabled() {
        return 'securitypolicyviolation' in document;
    }

    /**
     * Setup Content Security Policy violation handler
     */
    setupCSPViolationHandler() {
        document.addEventListener('securitypolicyviolation', (event) => {
            console.error('CSP Violation:', {
                violatedDirective: event.violatedDirective,
                blockedURI: event.blockedURI,
                sourceFile: event.sourceFile,
                lineNumber: event.lineNumber,
                columnNumber: event.columnNumber
            });

            // Report to server if needed
            this.reportSecurityViolation(event);
        });
    }

    /**
     * Report security violation to server
     */
    async reportSecurityViolation(violation) {
        try {
            await fetch('/api/security/report-violation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCSRFToken()
                },
                body: JSON.stringify({
                    type: 'csp_violation',
                    details: violation,
                    timestamp: new Date().toISOString(),
                    userAgent: navigator.userAgent,
                    url: window.location.href
                })
            });
        } catch (error) {
            console.error('Failed to report security violation:', error);
        }
    }

    /**
     * Check for XSS attempts in input
     */
    detectXSS(input) {
        const xssPatterns = [
            /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
            /javascript:[^"']*/gi,
            /on\w+="[^"]*"/gi,
            /on\w+='[^']*'/gi,
            /<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi,
            /<object\b[^<]*(?:(?!<\/object>)<[^<]*)*<\/object>/gi,
            /<embed\b[^<]*(?:(?!<\/embed>)<[^<]*)*<\/embed>/gi
        ];

        return xssPatterns.some(pattern => pattern.test(input));
    }

    /**
     * Escape HTML entities
     */
    escapeHTML(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Check if running in secure context
     */
    isSecureContext() {
        return window.isSecureContext;
    }

    /**
     * Get security headers status
     */
    async checkSecurityHeaders() {
        try {
            const response = await fetch('/api/security/headers-check');
            return await response.json();
        } catch (error) {
            console.error('Failed to check security headers:', error);
            return null;
        }
    }

    /**
     * Setup secure local storage
     */
    setupSecureStorage() {
        // Override localStorage to add encryption for sensitive data
        const originalSetItem = localStorage.setItem;
        const originalGetItem = localStorage.getItem;

        localStorage.setItem = (key, value) => {
            if (this.isSensitiveKey(key)) {
                // Encrypt sensitive data
                const encrypted = this.simpleEncrypt(value);
                return originalSetItem.call(localStorage, key, encrypted);
            }
            return originalSetItem.call(localStorage, key, value);
        };

        localStorage.getItem = (key) => {
            const value = originalGetItem.call(localStorage, key);
            if (value && this.isSensitiveKey(key)) {
                return this.simpleDecrypt(value);
            }
            return value;
        };
    }

    /**
     * Check if key contains sensitive data
     */
    isSensitiveKey(key) {
        const sensitiveKeys = ['token', 'password', 'secret', 'key', 'auth'];
        return sensitiveKeys.some(sensitive => key.toLowerCase().includes(sensitive));
    }

    /**
     * Simple encryption/decryption for local storage
     */
    simpleEncrypt(text) {
        // Simple XOR encryption with a key
        const key = 'mamcrawler_admin_key';
        let result = '';
        for (let i = 0; i < text.length; i++) {
            result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length));
        }
        return btoa(result);
    }

    simpleDecrypt(encrypted) {
        try {
            const decoded = atob(encrypted);
            const key = 'mamcrawler_admin_key';
            let result = '';
            for (let i = 0; i < decoded.length; i++) {
                result += String.fromCharCode(decoded.charCodeAt(i) ^ key.charCodeAt(i % key.length));
            }
            return result;
        } catch (error) {
            console.error('Decryption failed:', error);
            return encrypted;
        }
    }

    /**
     * Clear sensitive data from memory
     */
    clearSensitiveData() {
        // Clear any sensitive data from memory
        this.csrfToken = null;
        sessionStorage.removeItem('csrf_token');

        // Clear encrypted localStorage items
        for (let i = localStorage.length - 1; i >= 0; i--) {
            const key = localStorage.key(i);
            if (this.isSensitiveKey(key)) {
                localStorage.removeItem(key);
            }
        }
    }

    /**
     * Setup secure file upload validation
     */
    validateFileUpload(file, options = {}) {
        const errors = [];

        // Check file size
        const maxSize = options.maxSize || 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            errors.push(`File size exceeds ${this.formatFileSize(maxSize)}`);
        }

        // Check file type
        const allowedTypes = options.allowedTypes || [];
        if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
            errors.push(`File type not allowed. Allowed: ${allowedTypes.join(', ')}`);
        }

        // Check file name for malicious patterns
        const maliciousPatterns = [
            /\.\./,  // Directory traversal
            /[<>:"\/\\|?*\x00-\x1f]/,  // Invalid characters
            /^\./,  // Hidden files
            /script/i,  // Script files
            /exe$/i,  // Executables
            /bat$/i,  // Batch files
            /cmd$/i   // Command files
        ];

        if (maliciousPatterns.some(pattern => pattern.test(file.name))) {
            errors.push('File name contains invalid characters or patterns');
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /**
     * Generate secure password
     */
    generateSecurePassword(length = 12) {
        const lowercase = 'abcdefghijklmnopqrstuvwxyz';
        const uppercase = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        const numbers = '0123456789';
        const symbols = '!@#$%^&*()_+-=[]{}|;:,.<>?';

        const allChars = lowercase + uppercase + numbers + symbols;
        let password = '';

        // Ensure at least one character from each set
        password += lowercase[Math.floor(Math.random() * lowercase.length)];
        password += uppercase[Math.floor(Math.random() * uppercase.length)];
        password += numbers[Math.floor(Math.random() * numbers.length)];
        password += symbols[Math.floor(Math.random() * symbols.length)];

        // Fill remaining length
        for (let i = password.length; i < length; i++) {
            password += allChars[Math.floor(Math.random() * allChars.length)];
        }

        // Shuffle the password
        return password.split('').sort(() => Math.random() - 0.5).join('');
    }

    /**
     * Setup security monitoring
     */
    setupSecurityMonitoring() {
        // Monitor for suspicious activities
        let failedLoginAttempts = 0;
        const maxFailedAttempts = 5;

        // Monitor failed login attempts
        document.addEventListener('login-failed', () => {
            failedLoginAttempts++;
            if (failedLoginAttempts >= maxFailedAttempts) {
                console.warn('Multiple failed login attempts detected');
                this.reportSecurityEvent('multiple_failed_logins', {
                    attempts: failedLoginAttempts,
                    timestamp: new Date().toISOString()
                });
            }
        });

        // Monitor for unusual activity
        let lastActivity = Date.now();
        const checkInterval = 5 * 60 * 1000; // 5 minutes

        setInterval(() => {
            const now = Date.now();
            if (now - lastActivity > checkInterval) {
                // User has been inactive
                this.reportSecurityEvent('user_inactive', {
                    inactive_duration: now - lastActivity,
                    timestamp: new Date().toISOString()
                });
            }
        }, checkInterval);

        // Update activity on user interactions
        ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(event => {
            document.addEventListener(event, () => {
                lastActivity = Date.now();
            }, { passive: true });
        });
    }

    /**
     * Report security event
     */
    async reportSecurityEvent(eventType, details) {
        try {
            await fetch('/api/security/report-event', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCSRFToken()
                },
                body: JSON.stringify({
                    event_type: eventType,
                    details,
                    timestamp: new Date().toISOString(),
                    user_agent: navigator.userAgent,
                    url: window.location.href
                })
            });
        } catch (error) {
            console.error('Failed to report security event:', error);
        }
    }
}

// Create global instance
window.securityUtils = new SecurityUtils();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SecurityUtils;
}