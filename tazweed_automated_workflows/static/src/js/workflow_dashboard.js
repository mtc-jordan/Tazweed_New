/**
 * Tazweed Automated Workflows - Dashboard JavaScript
 * Manages workflow dashboard functionality and interactions
 */

class WorkflowDashboard {
    constructor() {
        this.workflows = [];
        this.autoRefreshInterval = null;
        this.refreshRate = 5000; // 5 seconds
        this.init();
    }

    /**
     * Initialize dashboard
     */
    init() {
        this.attachEventListeners();
        this.loadDashboardData();
        this.startAutoRefresh();
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('workflow-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadDashboardData());
        }

        // Filter buttons
        const filterBtns = document.querySelectorAll('.workflow-filter-btn');
        filterBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.filterWorkflows(e.target.dataset.filter));
        });

        // Workflow card actions
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('workflow-action-btn')) {
                this.handleWorkflowAction(e.target);
            }
        });
    }

    /**
     * Load dashboard data
     */
    loadDashboardData() {
        console.log('Loading dashboard data...');
        
        // Fetch workflow statistics
        this.fetchWorkflowStats();
        
        // Fetch active workflows
        this.fetchActiveWorkflows();
        
        // Fetch recent activities
        this.fetchRecentActivities();
    }

    /**
     * Fetch workflow statistics
     */
    fetchWorkflowStats() {
        fetch('/api/workflows/stats', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.updateStatsDisplay(data);
        })
        .catch(error => console.error('Error fetching stats:', error));
    }

    /**
     * Update stats display
     */
    updateStatsDisplay(stats) {
        const statsContainer = document.getElementById('workflow-stats-container');
        if (!statsContainer) return;

        const statsHTML = `
            <div class="stat-card active">
                <div class="stat-card-icon">✓</div>
                <div class="stat-card-value">${stats.active || 0}</div>
                <div class="stat-card-label">Active Workflows</div>
            </div>
            <div class="stat-card pending">
                <div class="stat-card-icon">⏳</div>
                <div class="stat-card-value">${stats.pending || 0}</div>
                <div class="stat-card-label">Pending Approvals</div>
            </div>
            <div class="stat-card completed">
                <div class="stat-card-icon">✔</div>
                <div class="stat-card-value">${stats.completed || 0}</div>
                <div class="stat-card-label">Completed</div>
            </div>
            <div class="stat-card rejected">
                <div class="stat-card-icon">✕</div>
                <div class="stat-card-value">${stats.rejected || 0}</div>
                <div class="stat-card-label">Rejected</div>
            </div>
        `;

        statsContainer.innerHTML = statsHTML;
    }

    /**
     * Fetch active workflows
     */
    fetchActiveWorkflows() {
        fetch('/api/workflows/active', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.workflows = data;
            this.displayWorkflows(data);
        })
        .catch(error => console.error('Error fetching workflows:', error));
    }

    /**
     * Display workflows
     */
    displayWorkflows(workflows) {
        const container = document.getElementById('workflow-cards-container');
        if (!container) return;

        if (workflows.length === 0) {
            container.innerHTML = '<p class="no-data">No workflows found</p>';
            return;
        }

        const cardsHTML = workflows.map(workflow => this.createWorkflowCard(workflow)).join('');
        container.innerHTML = cardsHTML;
    }

    /**
     * Create workflow card HTML
     */
    createWorkflowCard(workflow) {
        const statusClass = workflow.state.toLowerCase();
        const progressPercent = workflow.completed_approvals / workflow.total_approvals * 100;

        return `
            <div class="workflow-card" data-workflow-id="${workflow.id}">
                <div class="workflow-card-header">
                    <h3 class="workflow-card-title">${workflow.name}</h3>
                    <span class="workflow-card-status ${statusClass}">${workflow.state}</span>
                </div>
                
                <div class="workflow-card-content">
                    <div class="workflow-card-item">
                        <span class="workflow-card-label">Workflow Type</span>
                        <span class="workflow-card-value">${workflow.workflow_type}</span>
                    </div>
                    <div class="workflow-card-item">
                        <span class="workflow-card-label">Initiated By</span>
                        <span class="workflow-card-value">${workflow.initiated_by}</span>
                    </div>
                    <div class="workflow-card-item">
                        <span class="workflow-card-label">Approvals</span>
                        <span class="workflow-card-value">${workflow.completed_approvals}/${workflow.total_approvals}</span>
                    </div>
                    <div class="workflow-card-item">
                        <span class="workflow-card-label">Started</span>
                        <span class="workflow-card-value">${this.formatDate(workflow.initiated_date)}</span>
                    </div>
                </div>

                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: ${progressPercent}%">
                        ${Math.round(progressPercent)}%
                    </div>
                </div>

                <div class="workflow-card-footer">
                    <button class="workflow-action-btn" data-action="view" data-workflow-id="${workflow.id}">View</button>
                    <button class="workflow-action-btn" data-action="approve" data-workflow-id="${workflow.id}">Approve</button>
                    <button class="workflow-action-btn" data-action="reject" data-workflow-id="${workflow.id}">Reject</button>
                </div>
            </div>
        `;
    }

    /**
     * Fetch recent activities
     */
    fetchRecentActivities() {
        fetch('/api/workflows/activities', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.displayActivities(data);
        })
        .catch(error => console.error('Error fetching activities:', error));
    }

    /**
     * Display recent activities
     */
    displayActivities(activities) {
        const container = document.getElementById('workflow-timeline-container');
        if (!container) return;

        const activitiesHTML = activities.map(activity => this.createActivityItem(activity)).join('');
        container.innerHTML = activitiesHTML;
    }

    /**
     * Create activity item HTML
     */
    createActivityItem(activity) {
        const statusClass = this.getActivityStatusClass(activity.action);
        const icon = this.getActivityIcon(activity.action);

        return `
            <div class="timeline-item">
                <div class="timeline-dot ${statusClass}">${icon}</div>
                <div class="timeline-content">
                    <div class="timeline-content-title">${activity.description}</div>
                    <div class="timeline-content-description">${activity.workflow_name}</div>
                    <div class="timeline-content-time">${this.formatDate(activity.created_date)}</div>
                </div>
            </div>
        `;
    }

    /**
     * Get activity status class
     */
    getActivityStatusClass(action) {
        const statusMap = {
            'approved': 'success',
            'rejected': 'danger',
            'started': 'warning',
            'completed': 'success',
        };
        return statusMap[action] || 'primary';
    }

    /**
     * Get activity icon
     */
    getActivityIcon(action) {
        const iconMap = {
            'approved': '✓',
            'rejected': '✕',
            'started': '▶',
            'completed': '✔',
        };
        return iconMap[action] || '•';
    }

    /**
     * Filter workflows
     */
    filterWorkflows(filter) {
        console.log('Filtering workflows by:', filter);
        
        const filtered = this.workflows.filter(workflow => {
            if (filter === 'all') return true;
            return workflow.state.toLowerCase() === filter.toLowerCase();
        });

        this.displayWorkflows(filtered);
    }

    /**
     * Handle workflow action
     */
    handleWorkflowAction(btn) {
        const action = btn.dataset.action;
        const workflowId = btn.dataset.workflowId;

        switch (action) {
            case 'view':
                this.viewWorkflow(workflowId);
                break;
            case 'approve':
                this.approveWorkflow(workflowId);
                break;
            case 'reject':
                this.rejectWorkflow(workflowId);
                break;
        }
    }

    /**
     * View workflow
     */
    viewWorkflow(workflowId) {
        window.location.href = `/workflows/${workflowId}`;
    }

    /**
     * Approve workflow
     */
    approveWorkflow(workflowId) {
        if (confirm('Are you sure you want to approve this workflow?')) {
            fetch(`/api/workflows/${workflowId}/approve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                this.showNotification('Workflow approved successfully', 'success');
                this.loadDashboardData();
            })
            .catch(error => {
                console.error('Error approving workflow:', error);
                this.showNotification('Error approving workflow', 'error');
            });
        }
    }

    /**
     * Reject workflow
     */
    rejectWorkflow(workflowId) {
        const reason = prompt('Please enter rejection reason:');
        if (reason) {
            fetch(`/api/workflows/${workflowId}/reject`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ reason: reason })
            })
            .then(response => response.json())
            .then(data => {
                this.showNotification('Workflow rejected successfully', 'success');
                this.loadDashboardData();
            })
            .catch(error => {
                console.error('Error rejecting workflow:', error);
                this.showNotification('Error rejecting workflow', 'error');
            });
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background-color: ${type === 'success' ? '#2ecc71' : '#e74c3c'};
            color: white;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            z-index: 9999;
            animation: slideDown 0.3s ease;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    /**
     * Format date
     */
    formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString();
    }

    /**
     * Start auto refresh
     */
    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            this.loadDashboardData();
        }, this.refreshRate);
    }

    /**
     * Stop auto refresh
     */
    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
    }

    /**
     * Destroy dashboard
     */
    destroy() {
        this.stopAutoRefresh();
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.workflowDashboard = new WorkflowDashboard();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (window.workflowDashboard) {
        window.workflowDashboard.destroy();
    }
});
