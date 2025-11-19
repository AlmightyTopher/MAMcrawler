/**
 * Utility functions for input debouncing
 */

/**
 * Creates a debounced version of a function that delays invoking func
 * until after wait milliseconds have elapsed since the last time
 * the debounced function was invoked.
 *
 * @param {Function} func - The function to debounce
 * @param {number} wait - The number of milliseconds to delay
 * @param {boolean} immediate - Whether to invoke immediately
 * @returns {Function} The debounced function
 */
export function debounce(func, wait, immediate = false) {
    let timeout;

    return function executedFunction(...args) {
        const later = () => {
            timeout = null;
            if (!immediate) func(...args);
        };

        const callNow = immediate && !timeout;

        clearTimeout(timeout);
        timeout = setTimeout(later, wait);

        if (callNow) func(...args);
    };
}

/**
 * Creates a throttled version of a function that only invokes func
 * at most once per every wait milliseconds.
 *
 * @param {Function} func - The function to throttle
 * @param {number} wait - The number of milliseconds to throttle
 * @returns {Function} The throttled function
 */
export function throttle(func, wait) {
    let inThrottle;

    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, wait);
        }
    };
}

/**
 * Creates a debounced function specifically for search inputs
 * with a default delay of 300ms
 *
 * @param {Function} func - The search function to debounce
 * @param {number} delay - Delay in milliseconds (default: 300)
 * @returns {Function} The debounced search function
 */
export function debounceSearch(func, delay = 300) {
    return debounce(func, delay);
}

/**
 * Creates a throttled function for scroll events
 *
 * @param {Function} func - The scroll handler function
 * @param {number} delay - Throttle delay in milliseconds (default: 100)
 * @returns {Function} The throttled scroll function
 */
export function throttleScroll(func, delay = 100) {
    return throttle(func, delay);
}