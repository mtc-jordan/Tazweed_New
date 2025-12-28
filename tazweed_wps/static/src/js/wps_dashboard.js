/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const { Component, useState, onWillStart, onMounted, useRef } = owl;

export class WPSDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            data: null,
            loading: true,
        });
        
        this.trendChartRef = useRef("trendChart");
        this.statusChartRef = useRef("statusChart");
        
        onWillStart(async () => {
            await this.loadDashboardData();
        });
        
        onMounted(() => {
            this.renderCharts();
        });
    }
    
    async loadDashboardData() {
        try {
            const data = await this.orm.call(
                "tazweed.wps.dashboard",
                "get_wps_dashboard_data",
                []
            );
            this.state.data = data;
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading WPS dashboard data:", error);
            this.state.loading = false;
        }
    }
    
    renderCharts() {
        if (!this.state.data) return;
        
        this.renderTrendChart();
        this.renderStatusChart();
    }
    
    renderTrendChart() {
        const canvas = this.trendChartRef.el;
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        const data = this.state.data.monthly_trend || [];
        
        new Chart(ctx, {
            type: "line",
            data: {
                labels: data.map(d => d.month),
                datasets: [
                    {
                        label: "Files Generated",
                        data: data.map(d => d.files),
                        borderColor: "#3B82F6",
                        backgroundColor: "rgba(59, 130, 246, 0.1)",
                        fill: true,
                        tension: 0.4,
                    },
                    {
                        label: "Files Processed",
                        data: data.map(d => d.processed),
                        borderColor: "#10B981",
                        backgroundColor: "rgba(16, 185, 129, 0.1)",
                        fill: true,
                        tension: 0.4,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                    },
                },
            },
        });
    }
    
    renderStatusChart() {
        const canvas = this.statusChartRef.el;
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        const data = this.state.data.status_distribution || [];
        
        const colors = {
            "Draft": "#6B7280",
            "Generated": "#3B82F6",
            "Submitted": "#F59E0B",
            "Processed": "#10B981",
            "Rejected": "#EF4444",
        };
        
        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map(d => d.status),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: data.map(d => colors[d.status] || "#6B7280"),
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "right",
                    },
                },
            },
        });
    }
    
    openWPSFiles() {
        this.action.doAction("tazweed_wps.action_wps_file");
    }
    
    openCompliance() {
        this.action.doAction("tazweed_wps.action_wps_compliance");
    }
    
    openBanks() {
        this.action.doAction("tazweed_wps.action_wps_bank");
    }
    
    createNewWPS() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "tazweed.wps.file",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }
    
    formatCurrency(value) {
        return new Intl.NumberFormat("en-AE", {
            style: "currency",
            currency: "AED",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value || 0);
    }
}

WPSDashboard.template = "tazweed_wps.WPSDashboard";

registry.category("actions").add("wps_dashboard", WPSDashboard);
