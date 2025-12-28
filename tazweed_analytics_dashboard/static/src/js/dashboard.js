/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart, onMounted } = owl;

/**
 * Tazweed Analytics Dashboard Component
 */
class TazweedAnalyticsDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            loading: true,
            dashboardId: this.props.action?.params?.dashboard_id || null,
            dashboard: null,
            kpis: [],
            charts: [],
            summary: {},
        });
        
        onWillStart(async () => {
            await this.loadDashboard();
        });
        
        onMounted(() => {
            this.renderCharts();
        });
    }
    
    async loadDashboard() {
        try {
            if (this.state.dashboardId) {
                const data = await this.orm.call(
                    'analytics.dashboard',
                    'get_dashboard_data',
                    [this.state.dashboardId]
                );
                
                this.state.dashboard = data.dashboard;
                this.state.kpis = data.kpis;
                this.state.charts = data.charts;
                this.state.summary = data.summary;
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
        } finally {
            this.state.loading = false;
        }
    }
    
    renderCharts() {
        if (!this.state.charts || !window.Chart) return;
        
        this.state.charts.forEach(chart => {
            const canvas = document.getElementById(`chart-${chart.id}`);
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            
            new Chart(ctx, {
                type: chart.type === 'horizontalBar' ? 'bar' : chart.type,
                data: {
                    labels: chart.labels,
                    datasets: chart.datasets,
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    indexAxis: chart.type === 'horizontalBar' ? 'y' : 'x',
                    plugins: {
                        legend: {
                            display: chart.datasets.length > 1,
                            position: 'bottom',
                        },
                    },
                    scales: chart.type === 'pie' || chart.type === 'doughnut' ? {} : {
                        y: {
                            beginAtZero: true,
                        },
                    },
                },
            });
        });
    }
    
    getTrendIcon(trend) {
        if (trend > 0) return 'fa-arrow-up';
        if (trend < 0) return 'fa-arrow-down';
        return 'fa-minus';
    }
    
    getTrendClass(trend) {
        if (trend > 0) return 'up';
        if (trend < 0) return 'down';
        return 'neutral';
    }
    
    formatTrend(trend) {
        const sign = trend > 0 ? '+' : '';
        return `${sign}${trend.toFixed(1)}%`;
    }
    
    async refreshDashboard() {
        this.state.loading = true;
        await this.loadDashboard();
        this.renderCharts();
    }
    
    async exportToPDF() {
        // Would trigger report generation
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'analytics.report',
            view_mode: 'form',
            target: 'new',
            context: {
                default_name: `${this.state.dashboard?.name || 'Dashboard'} Export`,
                default_category: this.state.dashboard?.type || 'executive',
                default_output_format: 'pdf',
            },
        });
    }
}

TazweedAnalyticsDashboard.template = "tazweed_analytics_dashboard.Dashboard";

// Register the client action
registry.category("actions").add("tazweed_analytics_dashboard", TazweedAnalyticsDashboard);

export default TazweedAnalyticsDashboard;
