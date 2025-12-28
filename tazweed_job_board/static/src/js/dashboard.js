/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";

/**
 * Job Board Dashboard - Odoo 16 OWL Component
 * Modern dashboard for job posting management and analytics
 */
export class JobBoardDashboard extends Component {
    static template = "tazweed_job_board.Dashboard";
    
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            isLoading: true,
            dateRange: 30,
            dashboardData: {
                active_postings: 0,
                total_views: 0,
                total_applications: 0,
                total_hires: 0,
                applications_over_time: [],
                board_distribution: [],
                funnel: {},
                cost_per_hire: [],
                top_postings: [],
                board_performance: [],
                alerts: [],
                recent_postings: [],
            },
        });
        
        this.charts = {};
        
        onWillStart(async () => {
            await this.fetchDashboardData();
        });
        
        onMounted(() => {
            this.renderCharts();
        });
        
        onWillUnmount(() => {
            this.destroyCharts();
        });
    }
    
    async fetchDashboardData() {
        this.state.isLoading = true;
        try {
            const result = await this.orm.call(
                "job.board.analytics",
                "get_dashboard_data",
                [this.state.dateRange]
            );
            this.state.dashboardData = result || this.state.dashboardData;
        } catch (error) {
            console.error("Error fetching dashboard data:", error);
            // Use default empty data
            this.notification.add("Could not load dashboard data. Using default values.", {
                type: "warning",
            });
        }
        this.state.isLoading = false;
    }
    
    renderCharts() {
        // Wait for DOM to be ready
        setTimeout(() => {
            this.renderApplicationsChart();
            this.renderBoardDistributionChart();
            this.renderFunnelChart();
            this.renderCostChart();
        }, 100);
    }
    
    destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }
    
    renderApplicationsChart() {
        const canvas = document.getElementById('applications_chart');
        if (!canvas) return;
        
        const data = this.state.dashboardData.applications_over_time || [];
        
        if (this.charts.applications) {
            this.charts.applications.destroy();
        }
        
        this.charts.applications = new Chart(canvas.getContext('2d'), {
            type: 'line',
            data: {
                labels: data.map(d => d.date),
                datasets: [{
                    label: 'Views',
                    data: data.map(d => d.views),
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2,
                }, {
                    label: 'Applications',
                    data: data.map(d => d.applications),
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    fill: true,
                    tension: 0.4,
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                        }
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)',
                        }
                    },
                    x: {
                        grid: {
                            display: false,
                        }
                    }
                }
            }
        });
    }
    
    renderBoardDistributionChart() {
        const canvas = document.getElementById('board_distribution_chart');
        if (!canvas) return;
        
        const data = this.state.dashboardData.board_distribution || [];
        
        if (this.charts.distribution) {
            this.charts.distribution.destroy();
        }
        
        this.charts.distribution = new Chart(canvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.board),
                datasets: [{
                    data: data.map(d => d.applications),
                    backgroundColor: [
                        '#667eea', '#764ba2', '#28a745', '#ffc107',
                        '#dc3545', '#17a2b8', '#6c757d', '#e83e8c'
                    ],
                    borderWidth: 0,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            usePointStyle: true,
                            padding: 15,
                        }
                    },
                },
            }
        });
    }
    
    renderFunnelChart() {
        const canvas = document.getElementById('funnel_chart');
        if (!canvas) return;
        
        const data = this.state.dashboardData.funnel || {};
        
        if (this.charts.funnel) {
            this.charts.funnel.destroy();
        }
        
        this.charts.funnel = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Views', 'Applications', 'Interviews', 'Offers', 'Hires'],
                datasets: [{
                    label: 'Candidates',
                    data: [
                        data.views || 0,
                        data.applications || 0,
                        data.interviews || 0,
                        data.offers || 0,
                        data.hires || 0
                    ],
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(255, 193, 7, 0.8)',
                        'rgba(40, 167, 69, 0.8)',
                        'rgba(32, 201, 151, 0.8)'
                    ],
                    borderRadius: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: {
                        display: false,
                    },
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)',
                        }
                    },
                    y: {
                        grid: {
                            display: false,
                        }
                    }
                }
            }
        });
    }
    
    renderCostChart() {
        const canvas = document.getElementById('cost_chart');
        if (!canvas) return;
        
        const data = this.state.dashboardData.cost_per_hire || [];
        
        if (this.charts.cost) {
            this.charts.cost.destroy();
        }
        
        this.charts.cost = new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.map(d => d.board),
                datasets: [{
                    label: 'Cost per Hire (AED)',
                    data: data.map(d => d.cost),
                    backgroundColor: 'rgba(220, 53, 69, 0.8)',
                    borderRadius: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)',
                        }
                    },
                    x: {
                        grid: {
                            display: false,
                        }
                    }
                }
            }
        });
    }
    
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
    
    async onDateRangeChange(ev) {
        this.state.dateRange = parseInt(ev.target.value);
        await this.fetchDashboardData();
        this.renderCharts();
    }
    
    // Navigation Actions
    openJobPostings() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Job Postings',
            res_model: 'job.posting',
            view_mode: 'kanban,tree,form',
            views: [[false, 'kanban'], [false, 'tree'], [false, 'form']],
            target: 'current',
        });
    }
    
    openActivePostings() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Active Postings',
            res_model: 'job.posting',
            view_mode: 'kanban,tree,form',
            views: [[false, 'kanban'], [false, 'tree'], [false, 'form']],
            domain: [['state', '=', 'active']],
            target: 'current',
        });
    }
    
    openCandidates() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Candidates',
            res_model: 'candidate.source',
            view_mode: 'tree,form',
            views: [[false, 'tree'], [false, 'form']],
            target: 'current',
        });
    }
    
    openAnalytics() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Analytics',
            res_model: 'job.board.analytics',
            view_mode: 'graph,pivot,tree',
            views: [[false, 'graph'], [false, 'pivot'], [false, 'tree']],
            target: 'current',
        });
    }
    
    openJobBoards() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Job Boards',
            res_model: 'job.board',
            view_mode: 'kanban,tree,form',
            views: [[false, 'kanban'], [false, 'tree'], [false, 'form']],
            target: 'current',
        });
    }
    
    createNewPosting() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'New Job Posting',
            res_model: 'job.posting',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }
    
    openPosting(postingId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Job Posting',
            res_model: 'job.posting',
            res_id: postingId,
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }
}

JobBoardDashboard.template = "tazweed_job_board.Dashboard";

// Register the component as a client action
registry.category("actions").add("job_board_dashboard", JobBoardDashboard);
