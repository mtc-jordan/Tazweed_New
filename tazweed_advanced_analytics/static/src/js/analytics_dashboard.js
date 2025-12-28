/**
 * Tazweed Advanced Analytics - Dashboard JavaScript
 * Modern, Interactive Dashboard with Real-time Updates
 */

(function() {
    'use strict';

    // ============================================================
    // Analytics Dashboard Manager
    // ============================================================

    class AnalyticsDashboard {
        constructor() {
            this.charts = {};
            this.refreshInterval = 300000; // 5 minutes default
            this.autoRefresh = true;
            this.init();
        }

        /**
         * Initialize dashboard
         */
        init() {
            this.setupEventListeners();
            this.loadDashboardData();
            this.setupAutoRefresh();
            this.setupResponsive();
        }

        /**
         * Setup event listeners
         */
        setupEventListeners() {
            // Refresh button
            document.querySelectorAll('[data-action="refresh"]').forEach(btn => {
                btn.addEventListener('click', () => this.refreshDashboard());
            });

            // Export button
            document.querySelectorAll('[data-action="export"]').forEach(btn => {
                btn.addEventListener('click', () => this.exportDashboard());
            });

            // Filter buttons
            document.querySelectorAll('[data-filter]').forEach(btn => {
                btn.addEventListener('click', (e) => this.applyFilter(e.target.dataset.filter));
            });

            // Period selector
            const periodSelect = document.querySelector('[data-period-select]');
            if (periodSelect) {
                periodSelect.addEventListener('change', (e) => this.changePeriod(e.target.value));
            }
        }

        /**
         * Load dashboard data
         */
        loadDashboardData() {
            console.log('Loading dashboard data...');
            
            // Simulate data loading
            this.updateKPICards();
            this.updateCharts();
            this.updateTables();
            this.updateTrends();
        }

        /**
         * Update KPI cards
         */
        updateKPICards() {
            const cards = document.querySelectorAll('.kpi-card');
            cards.forEach((card, index) => {
                // Animate card appearance
                card.style.animation = `slideInUp 0.6s ease-out ${index * 0.1}s both`;
                
                // Update values (simulated)
                const valueElement = card.querySelector('.kpi-card-value');
                if (valueElement) {
                    this.animateValue(valueElement, 0, Math.random() * 10000, 1000);
                }
            });
        }

        /**
         * Update charts
         */
        updateCharts() {
            const chartContainers = document.querySelectorAll('[data-chart-type]');
            chartContainers.forEach(container => {
                const chartType = container.dataset.chartType;
                const chartId = container.id;
                
                // Initialize chart based on type
                switch(chartType) {
                    case 'bar':
                        this.initBarChart(chartId);
                        break;
                    case 'line':
                        this.initLineChart(chartId);
                        break;
                    case 'pie':
                        this.initPieChart(chartId);
                        break;
                    case 'gauge':
                        this.initGaugeChart(chartId);
                        break;
                }
            });
        }

        /**
         * Update tables
         */
        updateTables() {
            const tables = document.querySelectorAll('.analytics-table');
            tables.forEach(table => {
                // Add row animations
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach((row, index) => {
                    row.style.animation = `slideInLeft 0.6s ease-out ${index * 0.05}s both`;
                });
            });
        }

        /**
         * Update trends
         */
        updateTrends() {
            const trendElements = document.querySelectorAll('[data-trend]');
            trendElements.forEach(element => {
                const trend = element.dataset.trend;
                const value = parseFloat(element.dataset.value) || 0;
                
                // Update trend indicator
                const indicator = element.querySelector('.trend-indicator');
                if (indicator) {
                    if (value > 0) {
                        indicator.className = 'trend-indicator up';
                        indicator.innerHTML = '↑ ' + value.toFixed(2) + '%';
                    } else if (value < 0) {
                        indicator.className = 'trend-indicator down';
                        indicator.innerHTML = '↓ ' + Math.abs(value).toFixed(2) + '%';
                    } else {
                        indicator.className = 'trend-indicator stable';
                        indicator.innerHTML = '→ Stable';
                    }
                }
            });
        }

        /**
         * Animate value counter
         */
        animateValue(element, start, end, duration) {
            const range = end - start;
            const increment = range / (duration / 16);
            let current = start;

            const timer = setInterval(() => {
                current += increment;
                if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                    current = end;
                    clearInterval(timer);
                }
                
                element.textContent = this.formatNumber(current);
            }, 16);
        }

        /**
         * Format number with thousand separators
         */
        formatNumber(num) {
            return new Intl.NumberFormat('en-US', {
                minimumFractionDigits: 0,
                maximumFractionDigits: 2
            }).format(num);
        }

        /**
         * Initialize bar chart
         */
        initBarChart(chartId) {
            console.log('Initializing bar chart:', chartId);
            // Chart.js integration would go here
        }

        /**
         * Initialize line chart
         */
        initLineChart(chartId) {
            console.log('Initializing line chart:', chartId);
            // Chart.js integration would go here
        }

        /**
         * Initialize pie chart
         */
        initPieChart(chartId) {
            console.log('Initializing pie chart:', chartId);
            // Chart.js integration would go here
        }

        /**
         * Initialize gauge chart
         */
        initGaugeChart(chartId) {
            console.log('Initializing gauge chart:', chartId);
            // Gauge.js integration would go here
        }

        /**
         * Refresh dashboard
         */
        refreshDashboard() {
            console.log('Refreshing dashboard...');
            
            // Show loading state
            this.showLoadingState();
            
            // Simulate API call
            setTimeout(() => {
                this.loadDashboardData();
                this.hideLoadingState();
                this.showNotification('Dashboard refreshed successfully', 'success');
            }, 1000);
        }

        /**
         * Export dashboard
         */
        exportDashboard() {
            console.log('Exporting dashboard...');
            
            // Show export options
            const format = prompt('Select export format:\n1. PDF\n2. Excel\n3. CSV', '1');
            
            if (format) {
                this.showLoadingState();
                
                // Simulate export
                setTimeout(() => {
                    this.hideLoadingState();
                    this.showNotification('Dashboard exported successfully', 'success');
                }, 2000);
            }
        }

        /**
         * Apply filter
         */
        applyFilter(filterType) {
            console.log('Applying filter:', filterType);
            
            // Update active filter
            document.querySelectorAll('[data-filter]').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelector(`[data-filter="${filterType}"]`).classList.add('active');
            
            // Reload data with filter
            this.loadDashboardData();
        }

        /**
         * Change period
         */
        changePeriod(period) {
            console.log('Changing period to:', period);
            this.loadDashboardData();
        }

        /**
         * Setup auto refresh
         */
        setupAutoRefresh() {
            if (this.autoRefresh) {
                setInterval(() => {
                    this.refreshDashboard();
                }, this.refreshInterval);
            }
        }

        /**
         * Setup responsive behavior
         */
        setupResponsive() {
            window.addEventListener('resize', () => {
                this.handleResize();
            });
        }

        /**
         * Handle window resize
         */
        handleResize() {
            // Redraw charts on resize
            Object.keys(this.charts).forEach(chartId => {
                const chart = this.charts[chartId];
                if (chart && chart.resize) {
                    chart.resize();
                }
            });
        }

        /**
         * Show loading state
         */
        showLoadingState() {
            const loader = document.createElement('div');
            loader.className = 'dashboard-loader';
            loader.innerHTML = '<div class="spinner"></div>';
            document.body.appendChild(loader);
        }

        /**
         * Hide loading state
         */
        hideLoadingState() {
            const loader = document.querySelector('.dashboard-loader');
            if (loader) {
                loader.remove();
            }
        }

        /**
         * Show notification
         */
        showNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            notification.style.animation = 'slideInDown 0.3s ease-out';
            
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideOutUp 0.3s ease-out';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
    }

    // ============================================================
    // KPI Card Manager
    // ============================================================

    class KPICardManager {
        constructor() {
            this.cards = document.querySelectorAll('.kpi-card');
            this.init();
        }

        init() {
            this.cards.forEach(card => {
                card.addEventListener('mouseenter', () => this.onCardHover(card));
                card.addEventListener('mouseleave', () => this.onCardLeave(card));
                card.addEventListener('click', () => this.onCardClick(card));
            });
        }

        onCardHover(card) {
            card.style.transform = 'translateY(-8px)';
        }

        onCardLeave(card) {
            card.style.transform = 'translateY(0)';
        }

        onCardClick(card) {
            const metric = card.dataset.metric;
            console.log('Navigating to metric:', metric);
            // Navigate to detailed view
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
            this.initializeAllCharts();
        }

        initializeAllCharts() {
            document.querySelectorAll('[data-chart-type]').forEach(container => {
                const chartType = container.dataset.chartType;
                const chartId = container.id;
                
                this.createChart(chartId, chartType);
            });
        }

        createChart(chartId, chartType) {
            console.log(`Creating ${chartType} chart: ${chartId}`);
            
            const container = document.getElementById(chartId);
            if (!container) return;

            // Create chart based on type
            const chart = {
                type: chartType,
                container: container,
                data: this.generateMockData(chartType),
                options: this.getChartOptions(chartType)
            };

            this.charts[chartId] = chart;
            this.renderChart(chartId);
        }

        generateMockData(chartType) {
            switch(chartType) {
                case 'bar':
                    return {
                        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                        datasets: [{
                            label: 'Payroll',
                            data: [65000, 72000, 68000, 75000, 80000, 78000]
                        }]
                    };
                case 'line':
                    return {
                        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                        datasets: [{
                            label: 'Compliance Score',
                            data: [85, 88, 90, 92]
                        }]
                    };
                case 'pie':
                    return {
                        labels: ['Department A', 'Department B', 'Department C'],
                        datasets: [{
                            data: [30, 45, 25]
                        }]
                    };
                default:
                    return {};
            }
        }

        getChartOptions(chartType) {
            return {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 1000,
                    easing: 'easeInOutQuart'
                }
            };
        }

        renderChart(chartId) {
            const chart = this.charts[chartId];
            console.log('Rendering chart:', chartId);
            // Chart.js rendering would go here
        }
    }

    // ============================================================
    // Initialize on DOM Ready
    // ============================================================

    document.addEventListener('DOMContentLoaded', function() {
        // Initialize dashboard
        window.analyticsDashboard = new AnalyticsDashboard();
        
        // Initialize KPI cards
        window.kpiCardManager = new KPICardManager();
        
        // Initialize charts
        window.chartManager = new ChartManager();
        
        console.log('Analytics Dashboard initialized successfully');
    });

    // ============================================================
    // Utility Functions
    // ============================================================

    window.AnalyticsUtils = {
        /**
         * Format currency
         */
        formatCurrency(value, currency = 'AED') {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: 0,
                maximumFractionDigits: 2
            }).format(value);
        },

        /**
         * Format percentage
         */
        formatPercentage(value, decimals = 1) {
            return (value).toFixed(decimals) + '%';
        },

        /**
         * Format date
         */
        formatDate(date, format = 'MM/DD/YYYY') {
            return new Intl.DateTimeFormat('en-US', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit'
            }).format(new Date(date));
        },

        /**
         * Get trend color
         */
        getTrendColor(value) {
            if (value > 0) return 'success';
            if (value < 0) return 'danger';
            return 'neutral';
        },

        /**
         * Get status color
         */
        getStatusColor(status) {
            const colors = {
                'compliant': 'success',
                'non-compliant': 'danger',
                'partial': 'warning',
                'excellent': 'success',
                'good': 'info',
                'fair': 'warning',
                'poor': 'danger'
            };
            return colors[status] || 'info';
        }
    };

})();
