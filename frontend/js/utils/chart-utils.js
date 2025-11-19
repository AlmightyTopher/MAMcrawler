/**
 * Chart Utilities
 * Functions for creating and managing charts using Canvas API
 */

class ChartUtils {
    /**
     * Create a line chart on a canvas element
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @param {Array} data - Data points array
     * @param {Object} options - Chart options
     */
    static createLineChart(canvas, data, options = {}) {
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        if (!data || data.length === 0) {
            this.drawNoDataMessage(ctx, width, height);
            return;
        }

        const {
            color = '#007bff',
            backgroundColor = 'rgba(0, 123, 255, 0.1)',
            showGrid = true,
            showLabels = true,
            labelFormat = (value) => value.toString(),
            timeFormat = (timestamp) => new Date(timestamp).toLocaleTimeString()
        } = options;

        // Calculate chart dimensions
        const padding = 60;
        const chartWidth = width - (padding * 2);
        const chartHeight = height - (padding * 2);

        // Find data range
        const values = data.map(d => d.value);
        const timestamps = data.map(d => d.timestamp);

        const minValue = Math.min(...values);
        const maxValue = Math.max(...values);
        const valueRange = maxValue - minValue || 1;

        // Draw grid and axes
        if (showGrid) {
            this.drawGrid(ctx, padding, chartWidth, chartHeight, width, height);
        }

        // Draw axes labels
        if (showLabels) {
            this.drawAxesLabels(ctx, data, padding, chartWidth, chartHeight, width, height,
                              minValue, maxValue, labelFormat, timeFormat);
        }

        // Draw chart area fill
        this.drawChartFill(ctx, data, padding, chartWidth, chartHeight, minValue, valueRange, backgroundColor);

        // Draw line
        this.drawChartLine(ctx, data, padding, chartWidth, chartHeight, minValue, valueRange, color);

        // Draw data points
        this.drawDataPoints(ctx, data, padding, chartWidth, chartHeight, minValue, valueRange, color);
    }

    /**
     * Create a bar chart on a canvas element
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @param {Array} data - Data points array
     * @param {Object} options - Chart options
     */
    static createBarChart(canvas, data, options = {}) {
        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        if (!data || data.length === 0) {
            this.drawNoDataMessage(ctx, width, height);
            return;
        }

        const {
            color = '#28a745',
            showGrid = true,
            showLabels = true,
            labelFormat = (value) => value.toString()
        } = options;

        // Calculate chart dimensions
        const padding = 60;
        const chartWidth = width - (padding * 2);
        const chartHeight = height - (padding * 2);

        // Find data range
        const values = data.map(d => d.value);
        const maxValue = Math.max(...values);
        const barWidth = chartWidth / data.length * 0.8;
        const barSpacing = chartWidth / data.length * 0.2;

        // Draw grid
        if (showGrid) {
            this.drawGrid(ctx, padding, chartWidth, chartHeight, width, height);
        }

        // Draw bars
        data.forEach((item, index) => {
            const barHeight = (item.value / maxValue) * chartHeight;
            const x = padding + (index * (barWidth + barSpacing));
            const y = height - padding - barHeight;

            // Draw bar
            ctx.fillStyle = color;
            ctx.fillRect(x, y, barWidth, barHeight);

            // Draw border
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.strokeRect(x, y, barWidth, barHeight);

            // Draw value label
            if (showLabels && item.value > 0) {
                ctx.fillStyle = '#000';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(
                    labelFormat(item.value),
                    x + barWidth / 2,
                    y - 5
                );
            }
        });

        // Draw axes labels
        if (showLabels) {
            this.drawBarChartLabels(ctx, data, padding, chartWidth, chartHeight, width, height, maxValue);
        }
    }

    /**
     * Draw grid lines
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {number} padding - Chart padding
     * @param {number} chartWidth - Chart width
     * @param {number} chartHeight - Chart height
     * @param {number} width - Canvas width
     * @param {number} height - Canvas height
     */
    static drawGrid(ctx, padding, chartWidth, chartHeight, width, height) {
        ctx.strokeStyle = '#e9ecef';
        ctx.lineWidth = 1;

        // Vertical grid lines
        for (let i = 0; i <= 5; i++) {
            const x = padding + (chartWidth * i / 5);
            ctx.beginPath();
            ctx.moveTo(x, padding);
            ctx.lineTo(x, height - padding);
            ctx.stroke();
        }

        // Horizontal grid lines
        for (let i = 0; i <= 4; i++) {
            const y = padding + (chartHeight * i / 4);
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - padding, y);
            ctx.stroke();
        }
    }

    /**
     * Draw axes labels for line chart
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {Array} data - Chart data
     * @param {number} padding - Chart padding
     * @param {number} chartWidth - Chart width
     * @param {number} chartHeight - Chart height
     * @param {number} width - Canvas width
     * @param {number} height - Canvas height
     * @param {number} minValue - Minimum value
     * @param {number} maxValue - Maximum value
     * @param {Function} labelFormat - Label formatting function
     * @param {Function} timeFormat - Time formatting function
     */
    static drawAxesLabels(ctx, data, padding, chartWidth, chartHeight, width, height,
                         minValue, maxValue, labelFormat, timeFormat) {
        ctx.fillStyle = '#6c757d';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';

        // Y-axis labels (values)
        for (let i = 0; i <= 4; i++) {
            const value = minValue + (maxValue - minValue) * (i / 4);
            const y = height - padding - (chartHeight * i / 4);

            ctx.textAlign = 'right';
            ctx.fillText(labelFormat(value), padding - 10, y + 4);
        }

        // X-axis labels (time)
        if (data.length > 0) {
            const labelCount = Math.min(5, data.length);
            for (let i = 0; i < labelCount; i++) {
                const index = Math.floor((data.length - 1) * i / (labelCount - 1));
                const item = data[index];
                const x = padding + (chartWidth * index / (data.length - 1));

                ctx.textAlign = 'center';
                ctx.fillText(timeFormat(item.timestamp), x, height - padding + 20);
            }
        }
    }

    /**
     * Draw bar chart labels
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {Array} data - Chart data
     * @param {number} padding - Chart padding
     * @param {number} chartWidth - Chart width
     * @param {number} chartHeight - Chart height
     * @param {number} width - Canvas width
     * @param {number} height - Canvas height
     * @param {number} maxValue - Maximum value
     */
    static drawBarChartLabels(ctx, data, padding, chartWidth, chartHeight, width, height, maxValue) {
        ctx.fillStyle = '#6c757d';
        ctx.font = '12px Arial';

        // Y-axis labels
        for (let i = 0; i <= 4; i++) {
            const value = (maxValue * i / 4);
            const y = height - padding - (chartHeight * i / 4);

            ctx.textAlign = 'right';
            ctx.fillText(value.toFixed(0), padding - 10, y + 4);
        }

        // X-axis labels
        if (data.length > 0) {
            const labelCount = Math.min(data.length, 5);
            for (let i = 0; i < labelCount; i++) {
                const index = Math.floor((data.length - 1) * i / (labelCount - 1));
                const item = data[index];
                const x = padding + (chartWidth * index / (data.length - 1));

                ctx.textAlign = 'center';
                ctx.save();
                ctx.translate(x, height - padding + 25);
                ctx.rotate(-Math.PI / 6);
                ctx.fillText(item.label || '', 0, 0);
                ctx.restore();
            }
        }
    }

    /**
     * Draw chart fill area
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {Array} data - Chart data
     * @param {number} padding - Chart padding
     * @param {number} chartWidth - Chart width
     * @param {number} chartHeight - Chart height
     * @param {number} minValue - Minimum value
     * @param {number} valueRange - Value range
     * @param {string} color - Fill color
     */
    static drawChartFill(ctx, data, padding, chartWidth, chartHeight, minValue, valueRange, color) {
        if (data.length < 2) return;

        ctx.fillStyle = color;
        ctx.beginPath();

        // Start from bottom-left
        ctx.moveTo(padding, height - padding);

        // Draw line to first point
        const firstPoint = data[0];
        const firstX = padding;
        const firstY = height - padding - ((firstPoint.value - minValue) / valueRange * chartHeight);
        ctx.lineTo(firstX, firstY);

        // Draw through all points
        data.forEach((point, index) => {
            const x = padding + (chartWidth * index / (data.length - 1));
            const y = height - padding - ((point.value - minValue) / valueRange * chartHeight);
            ctx.lineTo(x, y);
        });

        // Draw to bottom-right
        const lastPoint = data[data.length - 1];
        const lastX = padding + chartWidth;
        ctx.lineTo(lastX, height - padding);

        ctx.closePath();
        ctx.fill();
    }

    /**
     * Draw chart line
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {Array} data - Chart data
     * @param {number} padding - Chart padding
     * @param {number} chartWidth - Chart width
     * @param {number} chartHeight - Chart height
     * @param {number} minValue - Minimum value
     * @param {number} valueRange - Value range
     * @param {string} color - Line color
     */
    static drawChartLine(ctx, data, padding, chartWidth, chartHeight, minValue, valueRange, color) {
        if (data.length < 2) return;

        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();

        data.forEach((point, index) => {
            const x = padding + (chartWidth * index / (data.length - 1));
            const y = height - padding - ((point.value - minValue) / valueRange * chartHeight);

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });

        ctx.stroke();
    }

    /**
     * Draw data points
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {Array} data - Chart data
     * @param {number} padding - Chart padding
     * @param {number} chartWidth - Chart width
     * @param {number} chartHeight - Chart height
     * @param {number} minValue - Minimum value
     * @param {number} valueRange - Value range
     * @param {string} color - Point color
     */
    static drawDataPoints(ctx, data, padding, chartWidth, chartHeight, minValue, valueRange, color) {
        ctx.fillStyle = color;

        data.forEach((point, index) => {
            const x = padding + (chartWidth * index / (data.length - 1));
            const y = height - padding - ((point.value - minValue) / valueRange * chartHeight);

            ctx.beginPath();
            ctx.arc(x, y, 3, 0, Math.PI * 2);
            ctx.fill();

            // Add white border
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1;
            ctx.stroke();
        });
    }

    /**
     * Draw "No Data" message
     * @param {CanvasRenderingContext2D} ctx - Canvas context
     * @param {number} width - Canvas width
     * @param {number} height - Canvas height
     */
    static drawNoDataMessage(ctx, width, height) {
        ctx.fillStyle = '#6c757d';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('No data available', width / 2, height / 2);
    }

    /**
     * Resize canvas for high DPI displays
     * @param {HTMLCanvasElement} canvas - Canvas element
     */
    static resizeForHighDPI(canvas) {
        const ctx = canvas.getContext('2d');
        const dpr = window.devicePixelRatio || 1;

        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;

        ctx.scale(dpr, dpr);
        canvas.style.width = rect.width + 'px';
        canvas.style.height = rect.height + 'px';
    }

    /**
     * Create sample data for testing
     * @param {string} type - Data type ('performance', 'downloads', 'errors')
     * @param {number} count - Number of data points
     * @returns {Array} Sample data array
     */
    static createSampleData(type, count = 20) {
        const data = [];
        const now = Date.now();

        for (let i = 0; i < count; i++) {
            const timestamp = now - ((count - i - 1) * 60000); // 1 minute intervals

            let value;
            switch (type) {
                case 'performance':
                    value = 50 + Math.random() * 50; // 50-100%
                    break;
                case 'downloads':
                    value = Math.floor(Math.random() * 100); // 0-100 downloads
                    break;
                case 'errors':
                    value = Math.floor(Math.random() * 10); // 0-10 errors
                    break;
                default:
                    value = Math.random() * 100;
            }

            data.push({
                timestamp: timestamp,
                value: Math.round(value * 100) / 100,
                label: new Date(timestamp).toLocaleTimeString()
            });
        }

        return data;
    }

    /**
     * Update chart with new data
     * @param {HTMLCanvasElement} canvas - Canvas element
     * @param {Array} newData - New data array
     * @param {Object} options - Chart options
     */
    static updateChart(canvas, newData, options = {}) {
        // Resize for high DPI if needed
        this.resizeForHighDPI(canvas);

        // Create the appropriate chart type
        const chartType = options.type || 'line';

        switch (chartType) {
            case 'line':
                this.createLineChart(canvas, newData, options);
                break;
            case 'bar':
                this.createBarChart(canvas, newData, options);
                break;
            default:
                this.createLineChart(canvas, newData, options);
        }
    }
}