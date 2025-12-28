/**
 * Tazweed Client Portal - Charts Module
 * Advanced chart configurations and utilities
 */

const TazweedCharts = {
    // Default chart colors
    colors: {
        primary: '#2196F3',
        success: '#4CAF50',
        warning: '#FF9800',
        danger: '#F44336',
        info: '#00BCD4',
        purple: '#9C27B0',
        gray: '#607D8B'
    },

    // Chart defaults
    defaults: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
                labels: {
                    padding: 20,
                    usePointStyle: true
                }
            },
            tooltip: {
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                titleFont: { size: 14 },
                bodyFont: { size: 13 },
                padding: 12,
                cornerRadius: 8
            }
        }
    },

    /**
     * Create a line chart
     */
    createLineChart: function(ctx, labels, datasets, options = {}) {
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets.map((ds, i) => ({
                    ...ds,
                    borderColor: ds.borderColor || Object.values(this.colors)[i],
                    backgroundColor: ds.backgroundColor || this.hexToRgba(Object.values(this.colors)[i], 0.1),
                    fill: ds.fill !== undefined ? ds.fill : true,
                    tension: ds.tension || 0.4,
                    pointRadius: ds.pointRadius || 4,
                    pointHoverRadius: ds.pointHoverRadius || 6
                }))
            },
            options: {
                ...this.defaults,
                ...options,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    /**
     * Create a bar chart
     */
    createBarChart: function(ctx, labels, datasets, options = {}) {
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets.map((ds, i) => ({
                    ...ds,
                    backgroundColor: ds.backgroundColor || Object.values(this.colors)[i],
                    borderRadius: ds.borderRadius || 4,
                    maxBarThickness: ds.maxBarThickness || 50
                }))
            },
            options: {
                ...this.defaults,
                ...options,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    /**
     * Create a doughnut chart
     */
    createDoughnutChart: function(ctx, labels, data, options = {}) {
        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: options.colors || Object.values(this.colors).slice(0, data.length),
                    borderWidth: 0
                }]
            },
            options: {
                ...this.defaults,
                ...options,
                cutout: options.cutout || '70%',
                plugins: {
                    ...this.defaults.plugins,
                    legend: {
                        position: 'right',
                        labels: {
                            padding: 15,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    },

    /**
     * Create a pie chart
     */
    createPieChart: function(ctx, labels, data, options = {}) {
        return new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: options.colors || Object.values(this.colors).slice(0, data.length),
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                ...this.defaults,
                ...options
            }
        });
    },

    /**
     * Create a horizontal bar chart
     */
    createHorizontalBarChart: function(ctx, labels, datasets, options = {}) {
        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets.map((ds, i) => ({
                    ...ds,
                    backgroundColor: ds.backgroundColor || Object.values(this.colors)[i],
                    borderRadius: ds.borderRadius || 4
                }))
            },
            options: {
                ...this.defaults,
                ...options,
                indexAxis: 'y',
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    },
                    y: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    },

    /**
     * Helper: Convert hex color to rgba
     */
    hexToRgba: function(hex, alpha) {
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    },

    /**
     * Update chart data
     */
    updateChart: function(chart, labels, data) {
        chart.data.labels = labels;
        chart.data.datasets.forEach((dataset, i) => {
            dataset.data = Array.isArray(data[0]) ? data[i] : data;
        });
        chart.update();
    },

    /**
     * Destroy chart instance
     */
    destroyChart: function(chart) {
        if (chart) {
            chart.destroy();
        }
    }
};

// Export for use in other modules
window.TazweedCharts = TazweedCharts;
