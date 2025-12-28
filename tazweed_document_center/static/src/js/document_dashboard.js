/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";

/**
 * Document Center Dashboard
 * Central hub for all HR documents with expiry tracking and analytics
 */
export class DocumentCenterDashboard extends Component {
    static template = "tazweed_document_center.DocumentCenterDashboard";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        className: { type: String, optional: true },
        globalState: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.categoryChartRef = useRef("categoryChart");
        this.sourceChartRef = useRef("sourceChart");
        this.expiryChartRef = useRef("expiryChart");
        this.departmentChartRef = useRef("departmentChart");
        
        this.state = useState({
            loading: true,
            stats: {
                totalDocuments: 0,
                expiredDocuments: 0,
                expiringDocuments: 0,
                validDocuments: 0,
                verifiedDocuments: 0,
                complianceRate: 100,
                expiring7Days: 0,
                expiring30Days: 0,
            },
            byCategory: [],
            bySource: [],
            byDepartment: [],
            expiryTimeline: [],
            recentDocuments: [],
            expiringSoon: [],
            alerts: [],
        });

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
                "document.center.unified",
                "get_document_center_data",
                []
            );
            
            this.state.stats = data.stats || this.state.stats;
            this.state.byCategory = data.by_category || [];
            this.state.bySource = data.by_source || [];
            this.state.byDepartment = data.by_department || [];
            this.state.expiryTimeline = data.expiry_timeline || [];
            this.state.recentDocuments = data.recent_documents || [];
            this.state.expiringSoon = data.expiring_soon || [];
            this.state.alerts = data.alerts || [];
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading document center dashboard data:", error);
            this.state.loading = false;
        }
    }

    renderCharts() {
        this.renderCategoryChart();
        this.renderSourceChart();
        this.renderExpiryChart();
        this.renderDepartmentChart();
    }

    renderCategoryChart() {
        const canvas = document.getElementById("categoryChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.byCategory;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        const colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"];

        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: colors.slice(0, data.length),
                    borderWidth: 0,
                    hoverOffset: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "60%",
                plugins: {
                    legend: {
                        position: "right",
                        labels: {
                            padding: 10,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
    }

    renderSourceChart() {
        const canvas = document.getElementById("sourceChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.bySource;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        const colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"];

        new Chart(ctx, {
            type: "pie",
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: colors.slice(0, data.length),
                    borderWidth: 2,
                    borderColor: "#fff",
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
    }

    renderExpiryChart() {
        const canvas = document.getElementById("expiryChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.expiryTimeline;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    label: "Documents",
                    data: data.map(d => d.count),
                    backgroundColor: data.map(d => d.color),
                    borderRadius: 6,
                    barThickness: 30,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 10 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(0,0,0,0.05)" },
                        ticks: { 
                            font: { size: 10 },
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    renderDepartmentChart() {
        const canvas = document.getElementById("departmentChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.byDepartment;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    label: "Documents",
                    data: data.map(d => d.count),
                    backgroundColor: "#3B82F6",
                    borderRadius: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: "y",
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: "rgba(0,0,0,0.05)" },
                        ticks: { font: { size: 10 } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { font: { size: 10 } }
                    }
                }
            }
        });
    }

    drawNoDataMessage(ctx, canvas) {
        ctx.fillStyle = "#9CA3AF";
        ctx.font = "14px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("No data available", canvas.width / 2, canvas.height / 2);
    }

    async onSyncDocuments() {
        this.state.loading = true;
        try {
            await this.orm.call(
                "document.center.unified",
                "sync_all_documents",
                []
            );
            await this.loadDashboardData();
            this.renderCharts();
        } catch (error) {
            console.error("Error syncing documents:", error);
        }
        this.state.loading = false;
    }

    onViewAllDocuments() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Documents",
            res_model: "document.center.unified",
            view_mode: "tree,kanban,form",
            views: [[false, "tree"], [false, "kanban"], [false, "form"]],
            target: "current",
        });
    }

    onViewExpired() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Expired Documents",
            res_model: "document.center.unified",
            view_mode: "tree,form",
            views: [[false, "tree"], [false, "form"]],
            domain: [["state", "=", "expired"]],
            target: "current",
        });
    }

    onViewExpiring() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Expiring Documents",
            res_model: "document.center.unified",
            view_mode: "tree,form",
            views: [[false, "tree"], [false, "form"]],
            domain: [["state", "=", "expiring"]],
            target: "current",
        });
    }

    onViewValid() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Valid Documents",
            res_model: "document.center.unified",
            view_mode: "tree,form",
            views: [[false, "tree"], [false, "form"]],
            domain: [["state", "=", "valid"]],
            target: "current",
        });
    }

    onUploadDocument() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Upload Document",
            res_model: "document.center.unified",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            context: { default_source_module: "manual" },
        });
    }

    onViewDocument(docId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Document",
            res_model: "document.center.unified",
            res_id: docId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    getStatusClass(state) {
        const classes = {
            draft: "badge-secondary",
            valid: "badge-success",
            expiring: "badge-warning",
            expired: "badge-danger",
            archived: "badge-dark",
        };
        return classes[state] || "badge-secondary";
    }

    getStatusLabel(state) {
        const labels = {
            draft: "Draft",
            valid: "Valid",
            expiring: "Expiring",
            expired: "Expired",
            archived: "Archived",
        };
        return labels[state] || state;
    }

    formatDate(dateStr) {
        if (!dateStr) return "-";
        const date = new Date(dateStr);
        return date.toLocaleDateString("en-US", { 
            month: "short", 
            day: "numeric",
            year: "numeric"
        });
    }

    getDaysLeftClass(days) {
        if (days < 0) return "text-danger";
        if (days <= 7) return "text-danger";
        if (days <= 15) return "text-warning";
        if (days <= 30) return "text-warning";
        return "text-success";
    }
}

registry.category("actions").add("document_center_dashboard", DocumentCenterDashboard);

// Utility functions
export function formatDaysToExpiry(days) {
    if (days < 0) {
        return `Expired ${Math.abs(days)} days ago`;
    } else if (days === 0) {
        return 'Expires today';
    } else if (days === 1) {
        return 'Expires tomorrow';
    } else {
        return `Expires in ${days} days`;
    }
}

export function getExpiryStatusClass(days) {
    if (days < 0) return 'expired';
    if (days <= 7) return 'critical';
    if (days <= 15) return 'warning';
    if (days <= 30) return 'attention';
    return 'valid';
}

export function getExpiryStatusColor(days) {
    if (days < 0) return '#dc3545';  // Red - Expired
    if (days <= 7) return '#fd7e14';  // Orange - Critical
    if (days <= 15) return '#ffc107'; // Yellow - Warning
    if (days <= 30) return '#17a2b8'; // Blue - Attention
    return '#28a745';  // Green - Valid
}
