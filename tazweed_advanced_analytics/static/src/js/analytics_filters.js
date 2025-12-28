/**
 * Tazweed Advanced Analytics - Filters JavaScript
 * Advanced Filtering and Data Interactions
 */

(function() {
    'use strict';

    // ============================================================
    // Filter Manager
    // ============================================================

    class FilterManager {
        constructor() {
            this.filters = {};
            this.activeFilters = {};
            this.init();
        }

        init() {
            this.setupFilterListeners();
            this.loadSavedFilters();
        }

        /**
         * Setup filter event listeners
         */
        setupFilterListeners() {
            // Date range filter
            const dateFromInput = document.querySelector('[data-filter-date-from]');
            const dateToInput = document.querySelector('[data-filter-date-to]');
            
            if (dateFromInput && dateToInput) {
                dateFromInput.addEventListener('change', () => this.applyDateFilter());
                dateToInput.addEventListener('change', () => this.applyDateFilter());
            }

            // Department filter
            const deptSelect = document.querySelector('[data-filter-department]');
            if (deptSelect) {
                deptSelect.addEventListener('change', () => this.applyDepartmentFilter());
            }

            // Employee filter
            const empSelect = document.querySelector('[data-filter-employee]');
            if (empSelect) {
                empSelect.addEventListener('change', () => this.applyEmployeeFilter());
            }

            // Status filter
            document.querySelectorAll('[data-filter-status]').forEach(btn => {
                btn.addEventListener('click', (e) => this.applyStatusFilter(e.target.value));
            });

            // Period filter
            document.querySelectorAll('[data-filter-period]').forEach(btn => {
                btn.addEventListener('click', (e) => this.applyPeriodFilter(e.target.value));
            });

            // Reset filters
            const resetBtn = document.querySelector('[data-action="reset-filters"]');
            if (resetBtn) {
                resetBtn.addEventListener('click', () => this.resetFilters());
            }

            // Save filters
            const saveBtn = document.querySelector('[data-action="save-filters"]');
            if (saveBtn) {
                saveBtn.addEventListener('click', () => this.saveFilters());
            }
        }

        /**
         * Apply date filter
         */
        applyDateFilter() {
            const dateFrom = document.querySelector('[data-filter-date-from]').value;
            const dateTo = document.querySelector('[data-filter-date-to]').value;

            this.activeFilters.dateRange = {
                from: dateFrom,
                to: dateTo
            };

            this.applyFilters();
        }

        /**
         * Apply department filter
         */
        applyDepartmentFilter() {
            const dept = document.querySelector('[data-filter-department]').value;

            if (dept) {
                this.activeFilters.department = dept;
            } else {
                delete this.activeFilters.department;
            }

            this.applyFilters();
        }

        /**
         * Apply employee filter
         */
        applyEmployeeFilter() {
            const emp = document.querySelector('[data-filter-employee]').value;

            if (emp) {
                this.activeFilters.employee = emp;
            } else {
                delete this.activeFilters.employee;
            }

            this.applyFilters();
        }

        /**
         * Apply status filter
         */
        applyStatusFilter(status) {
            if (status) {
                this.activeFilters.status = status;
            } else {
                delete this.activeFilters.status;
            }

            this.updateStatusButtons(status);
            this.applyFilters();
        }

        /**
         * Apply period filter
         */
        applyPeriodFilter(period) {
            const today = new Date();
            let dateFrom, dateTo;

            switch(period) {
                case 'today':
                    dateFrom = today;
                    dateTo = today;
                    break;
                case 'week':
                    dateFrom = new Date(today.setDate(today.getDate() - today.getDay()));
                    dateTo = new Date();
                    break;
                case 'month':
                    dateFrom = new Date(today.getFullYear(), today.getMonth(), 1);
                    dateTo = new Date();
                    break;
                case 'quarter':
                    const quarter = Math.floor(today.getMonth() / 3);
                    dateFrom = new Date(today.getFullYear(), quarter * 3, 1);
                    dateTo = new Date();
                    break;
                case 'year':
                    dateFrom = new Date(today.getFullYear(), 0, 1);
                    dateTo = new Date();
                    break;
            }

            this.activeFilters.dateRange = {
                from: dateFrom.toISOString().split('T')[0],
                to: dateTo.toISOString().split('T')[0]
            };

            this.updatePeriodButtons(period);
            this.applyFilters();
        }

        /**
         * Apply all active filters
         */
        applyFilters() {
            console.log('Applying filters:', this.activeFilters);

            // Update UI
            this.updateFilterBadges();

            // Trigger data reload
            if (window.analyticsDashboard) {
                window.analyticsDashboard.loadDashboardData();
            }

            // Update charts
            if (window.chartManager) {
                Object.keys(window.chartManager.charts).forEach(chartId => {
                    window.chartManager.updateChart(chartId, this.getFilteredData(chartId));
                });
            }

            // Update tables
            this.updateTables();
        }

        /**
         * Get filtered data
         */
        getFilteredData(chartId) {
            // This would normally fetch filtered data from server
            // For now, return mock data
            return {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Filtered Data',
                    data: [65000, 72000, 68000, 75000, 80000, 78000]
                }]
            };
        }

        /**
         * Update filter badges
         */
        updateFilterBadges() {
            const badgeContainer = document.querySelector('[data-filter-badges]');
            if (!badgeContainer) return;

            badgeContainer.innerHTML = '';

            Object.keys(this.activeFilters).forEach(filterKey => {
                const filterValue = this.activeFilters[filterKey];
                const badge = document.createElement('span');
                badge.className = 'filter-badge';
                badge.innerHTML = `
                    ${filterKey}: ${JSON.stringify(filterValue)}
                    <button data-remove-filter="${filterKey}">×</button>
                `;

                badge.querySelector('button').addEventListener('click', () => {
                    delete this.activeFilters[filterKey];
                    this.applyFilters();
                });

                badgeContainer.appendChild(badge);
            });
        }

        /**
         * Update status buttons
         */
        updateStatusButtons(status) {
            document.querySelectorAll('[data-filter-status]').forEach(btn => {
                btn.classList.remove('active');
                if (btn.value === status) {
                    btn.classList.add('active');
                }
            });
        }

        /**
         * Update period buttons
         */
        updatePeriodButtons(period) {
            document.querySelectorAll('[data-filter-period]').forEach(btn => {
                btn.classList.remove('active');
                if (btn.value === period) {
                    btn.classList.add('active');
                }
            });
        }

        /**
         * Update tables with filters
         */
        updateTables() {
            const tables = document.querySelectorAll('.analytics-table');
            tables.forEach(table => {
                const rows = table.querySelectorAll('tbody tr');
                let visibleCount = 0;

                rows.forEach(row => {
                    if (this.rowMatchesFilters(row)) {
                        row.style.display = '';
                        visibleCount++;
                    } else {
                        row.style.display = 'none';
                    }
                });

                // Show empty state if no rows visible
                if (visibleCount === 0) {
                    const emptyRow = document.createElement('tr');
                    emptyRow.innerHTML = '<td colspan="100%">No data matches the selected filters</td>';
                    table.querySelector('tbody').appendChild(emptyRow);
                }
            });
        }

        /**
         * Check if row matches filters
         */
        rowMatchesFilters(row) {
            // Implement filter matching logic
            return true;
        }

        /**
         * Reset all filters
         */
        resetFilters() {
            this.activeFilters = {};
            
            // Reset UI
            document.querySelector('[data-filter-date-from]').value = '';
            document.querySelector('[data-filter-date-to]').value = '';
            document.querySelector('[data-filter-department]').value = '';
            document.querySelector('[data-filter-employee]').value = '';
            
            document.querySelectorAll('[data-filter-status]').forEach(btn => {
                btn.classList.remove('active');
            });
            
            document.querySelectorAll('[data-filter-period]').forEach(btn => {
                btn.classList.remove('active');
            });

            this.applyFilters();
        }

        /**
         * Save filters to localStorage
         */
        saveFilters() {
            const filterName = prompt('Enter filter name:');
            if (filterName) {
                const savedFilters = JSON.parse(localStorage.getItem('analyticsFilters') || '{}');
                savedFilters[filterName] = this.activeFilters;
                localStorage.setItem('analyticsFilters', JSON.stringify(savedFilters));
                this.showNotification(`Filters saved as "${filterName}"`, 'success');
            }
        }

        /**
         * Load saved filters
         */
        loadSavedFilters() {
            const savedFilters = JSON.parse(localStorage.getItem('analyticsFilters') || '{}');
            
            const filterSelect = document.querySelector('[data-saved-filters]');
            if (filterSelect) {
                Object.keys(savedFilters).forEach(filterName => {
                    const option = document.createElement('option');
                    option.value = filterName;
                    option.textContent = filterName;
                    filterSelect.appendChild(option);
                });

                filterSelect.addEventListener('change', (e) => {
                    if (e.target.value) {
                        this.activeFilters = savedFilters[e.target.value];
                        this.applyFilters();
                    }
                });
            }
        }

        /**
         * Show notification
         */
        showNotification(message, type) {
            const notification = document.createElement('div');
            notification.className = `notification notification-${type}`;
            notification.textContent = message;
            document.body.appendChild(notification);

            setTimeout(() => {
                notification.remove();
            }, 3000);
        }
    }

    // ============================================================
    // Search Manager
    // ============================================================

    class SearchManager {
        constructor() {
            this.searchInput = document.querySelector('[data-search-analytics]');
            this.init();
        }

        init() {
            if (this.searchInput) {
                this.searchInput.addEventListener('input', (e) => this.performSearch(e.target.value));
            }
        }

        /**
         * Perform search
         */
        performSearch(query) {
            console.log('Searching for:', query);

            const tables = document.querySelectorAll('.analytics-table');
            tables.forEach(table => {
                const rows = table.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    if (this.rowMatches(row, query)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
        }

        /**
         * Check if row matches search query
         */
        rowMatches(row, query) {
            const text = row.textContent.toLowerCase();
            return text.includes(query.toLowerCase());
        }
    }

    // ============================================================
    // Sort Manager
    // ============================================================

    class SortManager {
        constructor() {
            this.init();
        }

        init() {
            document.querySelectorAll('[data-sortable]').forEach(header => {
                header.addEventListener('click', (e) => this.sortTable(e.target));
            });
        }

        /**
         * Sort table
         */
        sortTable(header) {
            const table = header.closest('table');
            const columnIndex = Array.from(header.parentNode.children).indexOf(header);
            const rows = Array.from(table.querySelectorAll('tbody tr'));

            const isAscending = header.classList.toggle('sort-asc');
            header.classList.remove('sort-desc');
            if (!isAscending) {
                header.classList.add('sort-desc');
                header.classList.remove('sort-asc');
            }

            rows.sort((a, b) => {
                const aValue = a.children[columnIndex].textContent;
                const bValue = b.children[columnIndex].textContent;

                if (isAscending) {
                    return aValue.localeCompare(bValue);
                } else {
                    return bValue.localeCompare(aValue);
                }
            });

            rows.forEach(row => table.querySelector('tbody').appendChild(row));
        }
    }

    // ============================================================
    // Initialize on DOM Ready
    // ============================================================

    document.addEventListener('DOMContentLoaded', function() {
        window.filterManager = new FilterManager();
        window.searchManager = new SearchManager();
        window.sortManager = new SortManager();

        console.log('Analytics Filters initialized');
    });

})();
