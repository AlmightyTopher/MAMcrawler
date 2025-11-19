/**
 * Validation Utilities for MAMcrawler Admin Panel
 * Provides form validation and data sanitization functions
 */

class ValidationUtils {
    constructor() {
        this.rules = {
            required: (value) => value !== null && value !== undefined && String(value).trim() !== '',
            email: (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value),
            url: (value) => {
                try {
                    new URL(value);
                    return true;
                } catch {
                    return false;
                }
            },
            minLength: (value, min) => String(value).length >= min,
            maxLength: (value, max) => String(value).length <= max,
            numeric: (value) => !isNaN(value) && !isNaN(parseFloat(value)),
            integer: (value) => Number.isInteger(Number(value)),
            positive: (value) => Number(value) > 0,
            range: (value, min, max) => {
                const num = Number(value);
                return num >= min && num <= max;
            },
            pattern: (value, pattern) => new RegExp(pattern).test(value),
            oneOf: (value, options) => options.includes(value),
            json: (value) => {
                try {
                    JSON.parse(value);
                    return true;
                } catch {
                    return false;
                }
            }
        };
    }

    /**
     * Validate a single field
     */
    validateField(value, rules) {
        const errors = [];

        for (const [ruleName, ruleValue] of Object.entries(rules)) {
            const rule = this.rules[ruleName];
            if (!rule) {
                console.warn(`Unknown validation rule: ${ruleName}`);
                continue;
            }

            let isValid;
            if (ruleName === 'range') {
                isValid = rule(value, ruleValue.min, ruleValue.max);
            } else if (ruleName === 'minLength' || ruleName === 'maxLength') {
                isValid = rule(value, ruleValue);
            } else if (ruleName === 'pattern' || ruleName === 'oneOf') {
                isValid = rule(value, ruleValue);
            } else {
                isValid = rule(value);
            }

            if (!isValid) {
                errors.push(this.getErrorMessage(ruleName, ruleValue));
            }
        }

        return errors;
    }

    /**
     * Validate an entire form
     */
    validateForm(formData, validationSchema) {
        const errors = {};
        let isValid = true;

        for (const [fieldName, rules] of Object.entries(validationSchema)) {
            const value = formData.get ? formData.get(fieldName) : formData[fieldName];
            const fieldErrors = this.validateField(value, rules);

            if (fieldErrors.length > 0) {
                errors[fieldName] = fieldErrors;
                isValid = false;
            }
        }

        return { isValid, errors };
    }

    /**
     * Get error message for a rule
     */
    getErrorMessage(ruleName, ruleValue) {
        const messages = {
            required: 'This field is required',
            email: 'Please enter a valid email address',
            url: 'Please enter a valid URL',
            minLength: `Must be at least ${ruleValue} characters long`,
            maxLength: `Must be no more than ${ruleValue} characters long`,
            numeric: 'Must be a valid number',
            integer: 'Must be a whole number',
            positive: 'Must be a positive number',
            range: `Must be between ${ruleValue.min} and ${ruleValue.max}`,
            pattern: 'Invalid format',
            oneOf: `Must be one of: ${ruleValue.join(', ')}`,
            json: 'Must be valid JSON'
        };

        return messages[ruleName] || 'Invalid value';
    }

    /**
     * Sanitize input value
     */
    sanitize(value, type = 'string') {
        if (value === null || value === undefined) {
            return value;
        }

        switch (type) {
            case 'string':
                return String(value).trim();
            case 'number':
                const num = Number(value);
                return isNaN(num) ? null : num;
            case 'boolean':
                return Boolean(value);
            case 'email':
                return this.sanitizeEmail(value);
            case 'url':
                return this.sanitizeUrl(value);
            case 'json':
                return this.sanitizeJson(value);
            default:
                return value;
        }
    }

    /**
     * Sanitize email
     */
    sanitizeEmail(email) {
        if (!email) return '';
        return String(email).toLowerCase().trim();
    }

    /**
     * Sanitize URL
     */
    sanitizeUrl(url) {
        if (!url) return '';
        try {
            const urlObj = new URL(url);
            return urlObj.toString();
        } catch {
            return '';
        }
    }

    /**
     * Sanitize JSON string
     */
    sanitizeJson(jsonString) {
        if (!jsonString) return '';
        try {
            const parsed = JSON.parse(jsonString);
            return JSON.stringify(parsed, null, 2);
        } catch {
            return '';
        }
    }

    /**
     * Validate and sanitize form data
     */
    validateAndSanitize(formData, schema) {
        const sanitized = {};
        const errors = {};
        let isValid = true;

        for (const [fieldName, config] of Object.entries(schema)) {
            const rawValue = formData.get ? formData.get(fieldName) : formData[fieldName];
            const sanitizedValue = this.sanitize(rawValue, config.type || 'string');

            // Validate if rules are provided
            if (config.rules) {
                const fieldErrors = this.validateField(sanitizedValue, config.rules);
                if (fieldErrors.length > 0) {
                    errors[fieldName] = fieldErrors;
                    isValid = false;
                }
            }

            sanitized[fieldName] = sanitizedValue;
        }

        return { isValid, data: sanitized, errors };
    }

    /**
     * Show validation errors on form
     */
    showValidationErrors(formElement, errors) {
        // Clear previous errors
        this.clearValidationErrors(formElement);

        for (const [fieldName, fieldErrors] of Object.entries(errors)) {
            const field = formElement.querySelector(`[name="${fieldName}"]`);
            if (field) {
                // Add error class to field
                field.classList.add('error');

                // Create error message element
                const errorElement = document.createElement('div');
                errorElement.className = 'field-error';
                errorElement.textContent = fieldErrors[0]; // Show first error

                // Insert after field
                field.parentNode.insertBefore(errorElement, field.nextSibling);
            }
        }
    }

    /**
     * Clear validation errors from form
     */
    clearValidationErrors(formElement) {
        // Remove error classes
        const errorFields = formElement.querySelectorAll('.error');
        errorFields.forEach(field => field.classList.remove('error'));

        // Remove error messages
        const errorMessages = formElement.querySelectorAll('.field-error');
        errorMessages.forEach(message => message.remove());
    }

    /**
     * Validate password strength
     */
    validatePasswordStrength(password) {
        const errors = [];

        if (password.length < 8) {
            errors.push('Password must be at least 8 characters long');
        }

        if (!/[A-Z]/.test(password)) {
            errors.push('Password must contain at least one uppercase letter');
        }

        if (!/[a-z]/.test(password)) {
            errors.push('Password must contain at least one lowercase letter');
        }

        if (!/\d/.test(password)) {
            errors.push('Password must contain at least one number');
        }

        if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
            errors.push('Password must contain at least one special character');
        }

        return {
            isValid: errors.length === 0,
            errors,
            strength: this.calculatePasswordStrength(password)
        };
    }

    /**
     * Calculate password strength
     */
    calculatePasswordStrength(password) {
        let score = 0;

        if (password.length >= 8) score += 1;
        if (password.length >= 12) score += 1;
        if (/[A-Z]/.test(password)) score += 1;
        if (/[a-z]/.test(password)) score += 1;
        if (/\d/.test(password)) score += 1;
        if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) score += 1;

        if (score <= 2) return 'weak';
        if (score <= 4) return 'medium';
        return 'strong';
    }

    /**
     * Validate username
     */
    validateUsername(username) {
        const errors = [];

        if (!username || username.length < 3) {
            errors.push('Username must be at least 3 characters long');
        }

        if (username.length > 50) {
            errors.push('Username must be no more than 50 characters long');
        }

        if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
            errors.push('Username can only contain letters, numbers, underscores, and hyphens');
        }

        return {
            isValid: errors.length === 0,
            errors
        };
    }

    /**
     * Validate IP address
     */
    validateIPAddress(ip) {
        const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}$/;
        const ipv6Regex = /^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$/;

        if (!ipv4Regex.test(ip) && !ipv6Regex.test(ip)) {
            return { isValid: false, errors: ['Invalid IP address format'] };
        }

        // Additional validation for IPv4
        if (ipv4Regex.test(ip)) {
            const parts = ip.split('.');
            for (const part of parts) {
                const num = parseInt(part);
                if (num < 0 || num > 255) {
                    return { isValid: false, errors: ['Invalid IPv4 address'] };
                }
            }
        }

        return { isValid: true, errors: [] };
    }

    /**
     * Validate port number
     */
    validatePort(port) {
        const portNum = parseInt(port);
        const errors = [];

        if (isNaN(portNum)) {
            errors.push('Port must be a number');
        } else if (portNum < 1 || portNum > 65535) {
            errors.push('Port must be between 1 and 65535');
        }

        return {
            isValid: errors.length === 0,
            errors,
            value: portNum
        };
    }

    /**
     * Validate file upload
     */
    validateFileUpload(file, options = {}) {
        const errors = [];
        const maxSize = options.maxSize || 10 * 1024 * 1024; // 10MB default
        const allowedTypes = options.allowedTypes || [];

        if (!file) {
            errors.push('No file selected');
            return { isValid: false, errors };
        }

        if (file.size > maxSize) {
            errors.push(`File size must be less than ${this.formatFileSize(maxSize)}`);
        }

        if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
            errors.push(`File type must be one of: ${allowedTypes.join(', ')}`);
        }

        return {
            isValid: errors.length === 0,
            errors,
            file
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
     * Real-time validation for input fields
     */
    setupRealtimeValidation(formElement, schema) {
        for (const [fieldName, config] of Object.entries(schema)) {
            const field = formElement.querySelector(`[name="${fieldName}"]`);
            if (field && config.rules) {
                field.addEventListener('blur', () => {
                    const value = field.value;
                    const errors = this.validateField(value, config.rules);
                    this.showFieldErrors(field, errors);
                });

                field.addEventListener('input', () => {
                    // Clear errors on input
                    this.clearFieldErrors(field);
                });
            }
        }
    }

    /**
     * Show field-specific errors
     */
    showFieldErrors(field, errors) {
        this.clearFieldErrors(field);

        if (errors.length > 0) {
            field.classList.add('error');

            const errorElement = document.createElement('div');
            errorElement.className = 'field-error';
            errorElement.textContent = errors[0];

            field.parentNode.insertBefore(errorElement, field.nextSibling);
        }
    }

    /**
     * Clear field-specific errors
     */
    clearFieldErrors(field) {
        field.classList.remove('error');
        const existingError = field.parentNode.querySelector('.field-error');
        if (existingError) {
            existingError.remove();
        }
    }
}

// Create global instance
window.validationUtils = new ValidationUtils();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ValidationUtils;
}