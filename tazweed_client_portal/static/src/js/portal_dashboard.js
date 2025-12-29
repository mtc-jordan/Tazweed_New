/**
 * Enhanced Client Portal Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard
    initDashboard();
    
    // Event listeners
    document.getElementById('refreshDashboard')?.addEventListener('click', refreshDashboard);
    
    // Auto-refresh every 5 minutes
    setInterval(refreshDashboard, 300000);
});

/**
 * Initialize the dashboard
 */
async function initDashboard() {
    try {
        showLoading();
        const data = await fetchDashboardData();
        updateKPIs(data.kpis);
        updateAlerts(data.alerts);
        updatePendingActions(data.pending_actions);
        updateRecentActivity(data.recent_activity);
        initCharts(data.charts);
        hideLoading();
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showError('Failed to load dashboard data');
    }
}

/**
 * Fetch dashboard data from server
 */
async function fetchDashboardData() {
    const response = await fetch('/my/dashboard/data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            jsonrpc: '2.0',
            method: 'call',
            params: {},
            id: Date.now()
        })
    });
    
    const result = await response.json();
    return result.result || {};
}

/**
 * Refresh dashboard data
 */
async function refreshDashboard() {
    const btn = document.getElementById('refreshDashboard');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa fa-spinner fa-spin me-1"></i>Refreshing...';
    }
    
    try {
        await initDashboard();
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa fa-sync-alt me-1"></i>Refresh';
        }
    }
}

/**
 * Update KPI cards
 */
function updateKPIs(kpis) {
    if (!kpis) return;
    
    const kpiElements = {
        'kpi-employees': kpis.active_employees || 0,
        'kpi-job-orders': kpis.active_job_orders || 0,
        'kpi-pending': kpis.pending_reviews || 0,
        'kpi-fill-rate': (kpis.fill_rate || 0).toFixed(1) + '%'
    };
    
    for (const [id, value] of Object.entries(kpiElements)) {
        const el = document.getElementById(id);
        if (el) {
            animateValue(el, value);
        }
    }
}

/**
 * Animate value change
 */
function animateValue(element, newValue) {
    element.style.opacity = '0';
    setTimeout(() => {
        element.textContent = newValue;
        element.style.opacity = '1';
    }, 150);
}

/**
 * Update alerts section
 */
function updateAlerts(alerts) {
    const container = document.getElementById('alertsSection');
    if (!container || !alerts || alerts.length === 0) {
        if (container) container.innerHTML = '';
        return;
    }
    
    let html = '';
    for (const alert of alerts) {
        const levelClass = alert.level === 'critical' ? 'critical' : 
                          alert.level === 'warning' ? 'warning' : 'info';
        const icon = alert.level === 'critical' ? 'exclamation-circle' :
                    alert.level === 'warning' ? 'exclamation-triangle' : 'info-circle';
        
        html += `
            <div class="portal-alert ${levelClass}">
                <div class="portal-alert-icon">
                    <i class="fa fa-${icon}"></i>
                </div>
                <div class="portal-alert-content">
                    <strong>${alert.title}</strong>
                    <p class="mb-0">${alert.message}</p>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

/**
 * Update pending actions
 */
function updatePendingActions(actions) {
    const container = document.getElementById('pendingActions');
    if (!container) return;
    
    if (!actions || actions.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-3">No pending actions</p>';
        return;
    }
    
    let html = '';
    for (const action of actions) {
        const iconClass = action.type === 'candidate' ? 'fa-user-check text-primary' :
                         action.type === 'document' ? 'fa-file-alt text-warning' :
                         action.type === 'invoice' ? 'fa-file-invoice text-danger' :
                         'fa-tasks text-info';
        
        html += `
            <a href="${action.url}" class="pending-action text-decoration-none text-dark">
                <div class="pending-action-icon">
                    <i class="fa ${iconClass}"></i>
                </div>
                <div class="pending-action-content">
                    <h6>${action.title}</h6>
                    <small>${action.description}</small>
                </div>
                <i class="fa fa-chevron-right text-muted"></i>
            </a>
        `;
    }
    
    container.innerHTML = html;
}

/**
 * Update recent activity
 */
function updateRecentActivity(activities) {
    const container = document.getElementById('recentActivity');
    if (!container) return;
    
    if (!activities || activities.length === 0) {
        container.innerHTML = '<p class="text-muted text-center py-3">No recent activity</p>';
        return;
    }
    
    let html = '';
    for (const activity of activities) {
        const iconClass = getActivityIcon(activity.type);
        const colorClass = getActivityColor(activity.type);
        
        html += `
            <div class="activity-item">
                <div class="activity-icon ${colorClass}">
                    <i class="fa ${iconClass}"></i>
                </div>
                <div class="activity-content">
                    <h6>${activity.title}</h6>
                    <p>${activity.description}</p>
                </div>
                <span class="activity-time">${activity.time}</span>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

/**
 * Get activity icon based on type
 */
function getActivityIcon(type) {
    const icons = {
        'placement': 'fa-user-plus',
        'candidate': 'fa-user',
        'invoice': 'fa-file-invoice-dollar',
        'document': 'fa-file-alt',
        'request': 'fa-ticket-alt',
        'job_order': 'fa-briefcase',
        'message': 'fa-envelope'
    };
    return icons[type] || 'fa-circle';
}

/**
 * Get activity color based on type
 */
function getActivityColor(type) {
    const colors = {
        'placement': 'success',
        'candidate': 'primary',
        'invoice': 'warning',
        'document': 'info',
        'request': 'secondary',
        'job_order': 'success',
        'message': 'primary'
    };
    return colors[type] || 'secondary';
}

/**
 * Initialize charts
 */
function initCharts(chartData) {
    if (!chartData) return;
    
    // Placement Trend Chart
    const trendCtx = document.getElementById('placementTrendChart');
    if (trendCtx && chartData.placement_trend) {
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: chartData.placement_trend.labels,
                datasets: [{
                    label: 'Placements',
                    data: chartData.placement_trend.data,
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
    
    // Cost Breakdown Chart
    const costCtx = document.getElementById('costBreakdownChart');
    if (costCtx && chartData.cost_breakdown) {
        new Chart(costCtx, {
            type: 'doughnut',
            data: {
                labels: chartData.cost_breakdown.labels,
                datasets: [{
                    data: chartData.cost_breakdown.data,
                    backgroundColor: [
                        '#007bff',
                        '#28a745',
                        '#ffc107',
                        '#dc3545',
                        '#17a2b8'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

/**
 * Show loading state
 */
function showLoading() {
    const kpiCards = document.getElementById('kpiCards');
    if (kpiCards) {
        kpiCards.querySelectorAll('h3').forEach(el => {
            el.innerHTML = '<span class="loading-skeleton" style="display:inline-block;width:60px;height:24px;"></span>';
        });
    }
}

/**
 * Hide loading state
 */
function hideLoading() {
    // Loading is hidden when data is populated
}

/**
 * Show error message
 */
function showError(message) {
    const alertsSection = document.getElementById('alertsSection');
    if (alertsSection) {
        alertsSection.innerHTML = `
            <div class="alert alert-danger">
                <i class="fa fa-exclamation-circle me-2"></i>${message}
            </div>
        `;
    }
}

/**
 * Export functionality
 */
document.querySelectorAll('[data-export]').forEach(btn => {
    btn.addEventListener('click', async function(e) {
        e.preventDefault();
        const format = this.dataset.export;
        
        try {
            const response = await fetch('/my/reports/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        report_type: 'dashboard',
                        format: format,
                        date_from: getDateRange().from,
                        date_to: getDateRange().to
                    },
                    id: Date.now()
                })
            });
            
            const result = await response.json();
            if (result.result && result.result.success) {
                window.location.href = `/my/reports/${result.result.report_id}/download`;
            }
        } catch (error) {
            console.error('Export error:', error);
            alert('Failed to generate export');
        }
    });
});

/**
 * Get current date range
 */
function getDateRange() {
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
    
    return {
        from: thirtyDaysAgo.toISOString().split('T')[0],
        to: today.toISOString().split('T')[0]
    };
}
