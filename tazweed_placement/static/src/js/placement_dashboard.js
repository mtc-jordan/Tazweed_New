/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";

export class PlacementDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            kpis: {
                total_candidates: 0,
                active_candidates: 0,
                total_clients: 0,
                active_clients: 0,
                open_job_orders: 0,
                total_placements: 0,
                active_placements: 0,
                pending_interviews: 0,
                this_month_placements: 0,
                this_month_revenue: 0,
            },
            pipeline_data: [],
            placement_trend: [],
            source_data: [],
            job_category_data: [],
            recent_placements: [],
            upcoming_interviews: [],
            loading: true,
        });
        
        this.pipelineChartRef = useRef("pipelineChart");
        this.placementTrendChartRef = useRef("placementTrendChart");
        this.sourceChartRef = useRef("sourceChart");
        this.categoryChartRef = useRef("categoryChart");
        
        this.charts = {};
        
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
                "tazweed.placement.dashboard",
                "get_dashboard_data",
                []
            );
            
            this.state.kpis = data.kpis;
            this.state.pipeline_data = data.pipeline_data;
            this.state.placement_trend = data.placement_trend;
            this.state.source_data = data.source_data;
            this.state.job_category_data = data.job_category_data;
            this.state.recent_placements = data.recent_placements;
            this.state.upcoming_interviews = data.upcoming_interviews;
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.loading = false;
        }
    }
    
    renderCharts() {
        this.renderPipelineChart();
        this.renderPlacementTrendChart();
        this.renderSourceChart();
        this.renderCategoryChart();
    }
    
    renderPipelineChart() {
        const canvas = this.pipelineChartRef.el;
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        const data = this.state.pipeline_data;
        
        if (this.charts.pipeline) {
            this.charts.pipeline.destroy();
        }
        
        this.charts.pipeline = new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.stage),
                datasets: [{
                    label: "Candidates",
                    data: data.map(d => d.count),
                    backgroundColor: [
                        "rgba(128, 90, 213, 0.8)",
                        "rgba(20, 184, 166, 0.8)",
                        "rgba(249, 115, 22, 0.8)",
                        "rgba(234, 179, 8, 0.8)",
                        "rgba(59, 130, 246, 0.8)",
                        "rgba(16, 185, 129, 0.8)",
                    ],
                    borderColor: [
                        "rgb(128, 90, 213)",
                        "rgb(20, 184, 166)",
                        "rgb(249, 115, 22)",
                        "rgb(234, 179, 8)",
                        "rgb(59, 130, 246)",
                        "rgb(16, 185, 129)",
                    ],
                    borderWidth: 1,
                    borderRadius: 8,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: "Pipeline by Stage",
                        font: { size: 16, weight: "bold" },
                        color: "#374151",
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
    
    renderPlacementTrendChart() {
        const canvas = this.placementTrendChartRef.el;
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        const data = this.state.placement_trend;
        
        if (this.charts.trend) {
            this.charts.trend.destroy();
        }
        
        this.charts.trend = new Chart(ctx, {
            type: "line",
            data: {
                labels: data.map(d => d.month),
                datasets: [{
                    label: "Placements",
                    data: data.map(d => d.count),
                    borderColor: "rgb(128, 90, 213)",
                    backgroundColor: "rgba(128, 90, 213, 0.1)",
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: "rgb(128, 90, 213)",
                    pointBorderColor: "#fff",
                    pointBorderWidth: 2,
                    pointRadius: 6,
                }, {
                    label: "Revenue (K)",
                    data: data.map(d => d.revenue / 1000),
                    borderColor: "rgb(20, 184, 166)",
                    backgroundColor: "rgba(20, 184, 166, 0.1)",
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: "rgb(20, 184, 166)",
                    pointBorderColor: "#fff",
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    yAxisID: "y1",
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top" },
                    title: {
                        display: true,
                        text: "Placement Trend (Last 6 Months)",
                        font: { size: 16, weight: "bold" },
                        color: "#374151",
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        position: "left",
                        title: { display: true, text: "Placements" }
                    },
                    y1: {
                        beginAtZero: true,
                        position: "right",
                        title: { display: true, text: "Revenue (K)" },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }
    
    renderSourceChart() {
        const canvas = this.sourceChartRef.el;
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        const data = this.state.source_data;
        
        if (this.charts.source) {
            this.charts.source.destroy();
        }
        
        this.charts.source = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map(d => d.source),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: [
                        "rgba(128, 90, 213, 0.8)",
                        "rgba(20, 184, 166, 0.8)",
                        "rgba(249, 115, 22, 0.8)",
                        "rgba(234, 179, 8, 0.8)",
                        "rgba(59, 130, 246, 0.8)",
                        "rgba(236, 72, 153, 0.8)",
                        "rgba(107, 114, 128, 0.8)",
                    ],
                    borderWidth: 2,
                    borderColor: "#fff",
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right" },
                    title: {
                        display: true,
                        text: "Candidates by Source",
                        font: { size: 16, weight: "bold" },
                        color: "#374151",
                    }
                }
            }
        });
    }
    
    renderCategoryChart() {
        const canvas = this.categoryChartRef.el;
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        const data = this.state.job_category_data;
        
        if (this.charts.category) {
            this.charts.category.destroy();
        }
        
        this.charts.category = new Chart(ctx, {
            type: "polarArea",
            data: {
                labels: data.map(d => d.category),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: [
                        "rgba(128, 90, 213, 0.7)",
                        "rgba(20, 184, 166, 0.7)",
                        "rgba(249, 115, 22, 0.7)",
                        "rgba(234, 179, 8, 0.7)",
                        "rgba(59, 130, 246, 0.7)",
                        "rgba(16, 185, 129, 0.7)",
                    ],
                    borderWidth: 1,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right" },
                    title: {
                        display: true,
                        text: "Job Orders by Category",
                        font: { size: 16, weight: "bold" },
                        color: "#374151",
                    }
                }
            }
        });
    }
    
    // Navigation actions
    openCandidates() {
        this.action.doAction("tazweed_placement.action_tazweed_candidate");
    }
    
    openClients() {
        this.action.doAction("tazweed_placement.action_tazweed_client");
    }
    
    openJobOrders() {
        this.action.doAction("tazweed_placement.action_tazweed_job_order");
    }
    
    openPipeline() {
        this.action.doAction("tazweed_placement.action_tazweed_pipeline");
    }
    
    openPlacements() {
        this.action.doAction("tazweed_placement.action_tazweed_placement");
    }
    
    openInterviews() {
        this.action.doAction("tazweed_placement.action_tazweed_interview");
    }
    
    openPlacement(placementId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "tazweed.placement",
            res_id: placementId,
            views: [[false, "form"]],
            target: "current",
        });
    }
    
    openInterview(interviewId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "tazweed.interview",
            res_id: interviewId,
            views: [[false, "form"]],
            target: "current",
        });
    }
    
    async refreshData() {
        this.state.loading = true;
        await this.loadDashboardData();
        this.renderCharts();
    }
}

PlacementDashboard.template = "tazweed_placement.PlacementDashboard";

registry.category("actions").add("tazweed_placement_dashboard", PlacementDashboard);
