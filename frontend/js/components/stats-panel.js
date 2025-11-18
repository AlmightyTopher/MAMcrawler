/**
 * Statistics Panel Component
 * Handles statistics display, charts, and data visualization
 */

class StatsPanel {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.systemAPI = new SystemAPI(dashboard);
        this.charts = {};
    }

    /**
     * Initialize the stats panel
     */
    init() {
        // Set up the API instance on the dashboard
        this.dashboard.systemAPI = this.systemAPI;

        // Bind methods to dashboard
        this.dashboard.loadStatsData = this.loadStatsData.bind(this);
        this.dashboard.refreshStats = this.refreshStats.bind(this);
    }

    /**
     * Load stats data
     */
    async loadStatsData() {
        await this.systemAPI.loadStatsData();
        this.renderCharts();
    }

    /**
     * Refresh stats data
     */
    async refreshStats() {
        await this.loadStatsData();
    }

    /**
     * Render charts using Canvas API
     */
    renderCharts() {
        this.renderGenreChart();
        this.renderActivityChart();
    }

    /**
     * Render genre distribution chart
     */
    renderGenreChart() {
        const canvas = document.getElementById('genre-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Mock genre data - in real implementation, this would come from API
        const genres = [
            { name: 'Fantasy', count: 45, color: '#FF6B6B' },
            { name: 'Science Fiction', count: 32, color: '#4ECDC4' },
            { name: 'Mystery', count: 28, color: '#45B7D1' },
            { name: 'Romance', count: 22, color: '#FFA07A' },
            { name: 'Thriller', count: 18, color: '#98D8C8' },
            { name: 'Historical', count: 15, color: '#F7DC6F' },
            { name: 'Other', count: 12, color: '#BB8FCE' }
        ];

        const total = genres.reduce((sum, genre) => sum + genre.count, 0);
        let currentAngle = -Math.PI / 2; // Start from top

        // Draw pie chart
        genres.forEach(genre => {
            const sliceAngle = (genre.count / total) * 2 * Math.PI;

            // Draw slice
            ctx.beginPath();
            ctx.moveTo(width / 2, height / 2);
            ctx.arc(width / 2, height / 2, Math.min(width, height) / 3, currentAngle, currentAngle + sliceAngle);
            ctx.closePath();
            ctx.fillStyle = genre.color;
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 2;
            ctx.stroke();

            // Draw label
            const labelAngle = currentAngle + sliceAngle / 2;
            const labelRadius = Math.min(width, height) / 2.5;
            const labelX = width / 2 + Math.cos(labelAngle) * labelRadius;
            const labelY = height / 2 + Math.sin(labelAngle) * labelRadius;

            ctx.fillStyle = '#000000';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(`${genre.name}: ${genre.count}`, labelX, labelY);

            currentAngle += sliceAngle;
        });

        // Draw legend
        const legendX = 20;
        let legendY = height - 120;

        ctx.font = '11px Arial';
        ctx.textAlign = 'left';

        genres.forEach(genre => {
            // Color box
            ctx.fillStyle = genre.color;
            ctx.fillRect(legendX, legendY - 8, 12, 12);

            // Text
            ctx.fillStyle = '#000000';
            ctx.fillText(`${genre.name} (${genre.count})`, legendX + 20, legendY);

            legendY += 18;
        });
    }

    /**
     * Render activity chart (line chart)
     */
    renderActivityChart() {
        const canvas = document.getElementById('activity-chart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        // Mock activity data - last 30 days
        const days = 30;
        const data = [];
        for (let i = 0; i < days; i++) {
            data.push(Math.floor(Math.random() * 20) + 1); // Random downloads per day
        }

        const maxValue = Math.max(...data);
        const padding = 40;
        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;

        // Draw axes
        ctx.strokeStyle = '#cccccc';
        ctx.lineWidth = 1;

        // X-axis
        ctx.beginPath();
        ctx.moveTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();

        // Y-axis
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.stroke();

        // Draw grid lines
        ctx.strokeStyle = '#f0f0f0';
        ctx.lineWidth = 1;

        // Horizontal grid lines
        for (let i = 0; i <= 5; i++) {
            const y = padding + (chartHeight / 5) * i;
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - padding, y);
            ctx.stroke();

            // Y-axis labels
            ctx.fillStyle = '#666666';
            ctx.font = '10px Arial';
            ctx.textAlign = 'right';
            ctx.fillText(Math.round((maxValue / 5) * (5 - i)), padding - 5, y + 3);
        }

        // Draw data line
        ctx.strokeStyle = '#007bff';
        ctx.lineWidth = 2;
        ctx.beginPath();

        data.forEach((value, index) => {
            const x = padding + (chartWidth / (days - 1)) * index;
            const y = height - padding - (chartHeight / maxValue) * value;

            if (index === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }

            // Draw data points
            ctx.fillStyle = '#007bff';
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, 2 * Math.PI);
            ctx.fill();
        });

        ctx.stroke();

        // Fill area under the line
        ctx.fillStyle = 'rgba(0, 123, 255, 0.1)';
        ctx.beginPath();
        ctx.moveTo(padding, height - padding);

        data.forEach((value, index) => {
            const x = padding + (chartWidth / (days - 1)) * index;
            const y = height - padding - (chartHeight / maxValue) * value;
            ctx.lineTo(x, y);
        });

        ctx.lineTo(width - padding, height - padding);
        ctx.closePath();
        ctx.fill();

        // Draw labels
        ctx.fillStyle = '#666666';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Downloads Over Last 30 Days', width / 2, 20);

        // X-axis label
        ctx.fillText('Days', width / 2, height - 5);
    }

    /**
     * Create a simple bar chart for any data
     */
    createBarChart(canvasId, data, title) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const width = canvas.width;
        const height = canvas.height;

        // Clear canvas
        ctx.clearRect(0, 0, width, height);

        const padding = 40;
        const chartWidth = width - padding * 2;
        const chartHeight = height - padding * 2;
        const barWidth = chartWidth / data.length * 0.8;
        const maxValue = Math.max(...data.map(d => d.value));

        // Draw bars
        data.forEach((item, index) => {
            const barHeight = (item.value / maxValue) * chartHeight;
            const x = padding + (chartWidth / data.length) * index + (chartWidth / data.length - barWidth) / 2;
            const y = height - padding - barHeight;

            // Bar
            ctx.fillStyle = item.color || '#007bff';
            ctx.fillRect(x, y, barWidth, barHeight);

            // Bar border
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1;
            ctx.strokeRect(x, y, barWidth, barHeight);

            // Value label on top of bar
            ctx.fillStyle = '#000000';
            ctx.font = '10px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(item.value.toString(), x + barWidth / 2, y - 5);

            // Category label below bar
            ctx.fillText(item.label, x + barWidth / 2, height - padding + 15);
        });

        // Draw axes
        ctx.strokeStyle = '#cccccc';
        ctx.lineWidth = 1;

        // X-axis
        ctx.beginPath();
        ctx.moveTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();

        // Y-axis
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.stroke();

        // Title
        ctx.fillStyle = '#000000';
        ctx.font = '14px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(title, width / 2, 20);
    }

    /**
     * Update chart data (called when new data arrives)
     */
    updateChartData(chartType, newData) {
        // This would update the chart with new data
        // For now, just re-render
        this.renderCharts();
    }

    /**
     * Export chart as image
     */
    exportChart(canvasId, filename) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const link = document.createElement('a');
        link.download = filename;
        link.href = canvas.toDataURL();
        link.click();
    }

    /**
     * Toggle chart visibility
     */
    toggleChart(chartId) {
        const chart = document.getElementById(chartId);
        if (chart) {
            chart.style.display = chart.style.display === 'none' ? 'block' : 'none';
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StatsPanel;
}