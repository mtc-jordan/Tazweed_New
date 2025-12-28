/**
 * Tazweed Advanced Analytics - Charts JavaScript
 * Interactive Chart Management with Chart.js
 */

(function() {
    'use strict';

    // ============================================================
    // Chart Configuration
    // ============================================================

    const CHART_COLORS = {
        primary: '#3498db',
        success: '#2ecc71',
        danger: '#e74c3c',
        warning: '#f39c12',
        info: '#9b59b6',
        dark: '#2c3e50',
        light: '#ecf0f1'
    };

    const CHART_DEFAULTS = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'bottom',
                labels: {
                    font: {
                        size: 12,
                        weight: '600'
                    },
                    padding: 15,
                    usePointStyle: true
                }
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                padding: 12,
                titleFont: {
                    size: 13,
                    weight: 'bold'
                },
                bodyFont: {
                    size: 12
                },
                borderColor: 'rgba(255, 255, 255, 0.2)',
                borderWidth: 1,
                displayColors: true,
                callbacks: {
                    label: function(context) {
                        return context.label + ': ' + formatValue(context.parsed.y);
                    }
                }
            }
        },
        animation: {
            duration: 1000,
            easing: 'easeInOutQuart'
        }
    };

    // ============================================================
    // Chart Builder
    // ============================================================

    class ChartBuilder {
        constructor(containerId, chartType) {
            this.containerId = containerId;
            this.chartType = chartType;
            this.container = document.getElementById(containerId);
            this.chart = null;
            this.data = null;
            this.options = null;
        }

        /**
         * Build bar chart
         */
        buildBarChart(data, options = {}) {
            const defaultOptions = {
                ...CHART_DEFAULTS,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return formatValue(value);
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            };

            const chartOptions = {
                type: 'bar',
                data: data,
                options: { ...defaultOptions, ...options }
            };

            this.createChart(chartOptions);
            return this.chart;
        }

        /**
         * Build line chart
         */
        buildLineChart(data, options = {}) {
            const defaultOptions = {
                ...CHART_DEFAULTS,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return formatValue(value);
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            };

            const chartOptions = {
                type: 'line',
                data: data,
                options: { ...defaultOptions, ...options }
            };

            this.createChart(chartOptions);
            return this.chart;
        }

        /**
         * Build pie chart
         */
        buildPieChart(data, options = {}) {
            const defaultOptions = {
                ...CHART_DEFAULTS,
                plugins: {
                    ...CHART_DEFAULTS.plugins,
                    legend: {
                        ...CHART_DEFAULTS.plugins.legend,
                        position: 'right'
                    }
                }
            };

            const chartOptions = {
                type: 'doughnut',
                data: data,
                options: { ...defaultOptions, ...options }
            };

            this.createChart(chartOptions);
            return this.chart;
        }

        /**
         * Build area chart
         */
        buildAreaChart(data, options = {}) {
            const defaultOptions = {
                ...CHART_DEFAULTS,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        },
                        ticks: {
                            callback: function(value) {
                                return formatValue(value);
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            };

            // Add fill to datasets
            data.datasets.forEach(dataset => {
                dataset.fill = true;
                dataset.tension = 0.4;
                dataset.borderWidth = 2;
            });

            const chartOptions = {
                type: 'line',
                data: data,
                options: { ...defaultOptions, ...options }
            };

            this.createChart(chartOptions);
            return this.chart;
        }

        /**
         * Create chart
         */
        createChart(config) {
            if (this.chart) {
                this.chart.destroy();
            }

            if (typeof Chart === 'undefined') {
                console.warn('Chart.js not loaded');
                return;
            }

            const ctx = this.container.querySelector('canvas');
            if (!ctx) {
                console.warn('Canvas element not found');
                return;
            }

            this.chart = new Chart(ctx, config);
            return this.chart;
        }

        /**
         * Update chart data
         */
        updateData(newData) {
            if (this.chart) {
                this.chart.data = newData;
                this.chart.update();
            }
        }

        /**
         * Destroy chart
         */
        destroy() {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
        }
    }

    // ============================================================
    // Gauge Chart
    // ============================================================

    class GaugeChart {
        constructor(containerId) {
            this.containerId = containerId;
            this.container = document.getElementById(containerId);
            this.value = 0;
            this.maxValue = 100;
            this.init();
        }

        init() {
            this.drawGauge();
        }

        drawGauge() {
            const canvas = this.container.querySelector('canvas');
            if (!canvas) return;

            const ctx = canvas.getContext('2d');
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            const radius = Math.min(centerX, centerY) - 10;

            // Clear canvas
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Draw background arc
            this.drawArc(ctx, centerX, centerY, radius, 0, Math.PI, '#ecf0f1');

            // Draw value arc
            const valueAngle = (this.value / this.maxValue) * Math.PI;
            const color = this.getGaugeColor(this.value);
            this.drawArc(ctx, centerX, centerY, radius, 0, valueAngle, color);

            // Draw center circle
            ctx.fillStyle = 'white';
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius * 0.7, 0, 2 * Math.PI);
            ctx.fill();

            // Draw value text
            ctx.fillStyle = color;
            ctx.font = 'bold 24px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(this.value.toFixed(0) + '%', centerX, centerY);
        }

        drawArc(ctx, centerX, centerY, radius, startAngle, endAngle, color) {
            ctx.strokeStyle = color;
            ctx.lineWidth = 15;
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, startAngle, endAngle);
            ctx.stroke();
        }

        getGaugeColor(value) {
            if (value >= 80) return CHART_COLORS.success;
            if (value >= 60) return CHART_COLORS.warning;
            return CHART_COLORS.danger;
        }

        setValue(value) {
            this.value = Math.min(value, this.maxValue);
            this.drawGauge();
        }
    }

    // ============================================================
    // Heatmap Chart
    // ============================================================

    class HeatmapChart {
        constructor(containerId, rows, cols) {
            this.containerId = containerId;
            this.container = document.getElementById(containerId);
            this.rows = rows;
            this.cols = cols;
            this.data = [];
            this.init();
        }

        init() {
            this.generateGrid();
        }

        generateGrid() {
            const grid = document.createElement('div');
            grid.className = 'heatmap-grid';

            for (let i = 0; i < this.rows * this.cols; i++) {
                const cell = document.createElement('div');
                cell.className = 'heatmap-cell';
                cell.dataset.index = i;
                cell.addEventListener('mouseenter', () => this.onCellHover(cell));
                grid.appendChild(cell);
            }

            this.container.appendChild(grid);
        }

        setCellValue(index, value) {
            const cell = this.container.querySelector(`[data-index="${index}"]`);
            if (cell) {
                cell.textContent = value;
                cell.className = 'heatmap-cell ' + this.getHeatmapColor(value);
            }
        }

        getHeatmapColor(value) {
            if (value >= 80) return 'hot';
            if (value >= 60) return 'warm';
            if (value >= 40) return 'cool';
            return 'cold';
        }

        onCellHover(cell) {
            const tooltip = document.createElement('div');
            tooltip.className = 'heatmap-tooltip';
            tooltip.textContent = 'Value: ' + cell.textContent;
            cell.appendChild(tooltip);
        }
    }

    // ============================================================
    // Chart Manager
    // ============================================================

    class ChartManager {
        constructor() {
            this.charts = {};
            this.init();
        }

        init() {
            this.initializeCharts();
        }

        initializeCharts() {
            document.querySelectorAll('[data-chart-type]').forEach(container => {
                const chartType = container.dataset.chartType;
                const chartId = container.id;
                const dataSource = container.dataset.dataSource || 'mock';

                this.createChart(chartId, chartType, dataSource);
            });
        }

        createChart(chartId, chartType, dataSource) {
            const builder = new ChartBuilder(chartId, chartType);
            const data = this.getChartData(chartType, dataSource);

            switch(chartType) {
                case 'bar':
                    builder.buildBarChart(data);
                    break;
                case 'line':
                    builder.buildLineChart(data);
                    break;
                case 'pie':
                    builder.buildPieChart(data);
                    break;
                case 'area':
                    builder.buildAreaChart(data);
                    break;
                case 'gauge':
                    new GaugeChart(chartId);
                    break;
                case 'heatmap':
                    new HeatmapChart(chartId, 5, 5);
                    break;
            }

            this.charts[chartId] = builder;
        }

        getChartData(chartType, dataSource) {
            switch(chartType) {
                case 'bar':
                    return {
                        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                        datasets: [{
                            label: 'Payroll',
                            data: [65000, 72000, 68000, 75000, 80000, 78000],
                            backgroundColor: CHART_COLORS.primary,
                            borderRadius: 6,
                            borderSkipped: false
                        }]
                    };
                case 'line':
                    return {
                        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                        datasets: [{
                            label: 'Compliance Score',
                            data: [85, 88, 90, 92],
                            borderColor: CHART_COLORS.success,
                            backgroundColor: 'rgba(46, 204, 113, 0.1)',
                            borderWidth: 3,
                            fill: false,
                            tension: 0.4
                        }]
                    };
                case 'pie':
                    return {
                        labels: ['Department A', 'Department B', 'Department C'],
                        datasets: [{
                            data: [30, 45, 25],
                            backgroundColor: [
                                CHART_COLORS.primary,
                                CHART_COLORS.success,
                                CHART_COLORS.warning
                            ],
                            borderColor: 'white',
                            borderWidth: 2
                        }]
                    };
                case 'area':
                    return {
                        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                        datasets: [{
                            label: 'Revenue',
                            data: [100000, 120000, 115000, 130000, 140000, 135000],
                            borderColor: CHART_COLORS.primary,
                            backgroundColor: 'rgba(52, 152, 219, 0.1)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.4
                        }]
                    };
                default:
                    return {};
            }
        }

        updateChart(chartId, newData) {
            const chart = this.charts[chartId];
            if (chart) {
                chart.updateData(newData);
            }
        }

        destroyChart(chartId) {
            const chart = this.charts[chartId];
            if (chart) {
                chart.destroy();
                delete this.charts[chartId];
            }
        }
    }

    // ============================================================
    // Utility Functions
    // ============================================================

    function formatValue(value) {
        if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        } else if (value >= 1000) {
            return (value / 1000).toFixed(1) + 'K';
        }
        return value.toFixed(0);
    }

    // ============================================================
    // Export
    // ============================================================

    window.ChartBuilder = ChartBuilder;
    window.GaugeChart = GaugeChart;
    window.HeatmapChart = HeatmapChart;
    window.ChartManager = ChartManager;

    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        window.chartManager = new ChartManager();
        console.log('Chart Manager initialized');
    });

})();
