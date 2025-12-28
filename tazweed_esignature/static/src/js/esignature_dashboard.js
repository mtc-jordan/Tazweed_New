/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";

export class ESignatureDashboard extends Component {
    static template = "tazweed_esignature.ESignatureDashboard";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        className: { type: String, optional: true },
        globalState: { type: Object, optional: true },
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            isLoading: true,
            dateRange: "30",
            data: {
                total_requests: 0,
                pending_signatures: 0,
                completed_today: 0,
                avg_completion_time: 0,
                completion_rate: 0,
                status_counts: {},
                recent_activity: [],
                trend_data: [],
            },
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
            this.state.isLoading = true;
            const data = await this.orm.call(
                "signature.request",
                "get_dashboard_data",
                [this.state.dateRange]
            );
            this.state.data = data;
            this.state.isLoading = false;
            setTimeout(() => this.renderCharts(), 100);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add("Failed to load dashboard data", { type: "danger" });
            this.state.isLoading = false;
        }
    }

    async onDateRangeChange(ev) {
        this.state.dateRange = ev.target.value;
        await this.loadDashboardData();
    }

    async onRefresh() {
        await this.loadDashboardData();
        this.notification.add("Dashboard refreshed", { type: "success" });
    }

    renderCharts() {
        this.renderStatusChart();
        this.renderTrendChart();
    }

    renderStatusChart() {
        const canvas = document.getElementById("statusChart");
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        const data = this.state.data.status_counts;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        const colors = {
            draft: "#6c757d",
            sent: "#17a2b8",
            partially_signed: "#ffc107",
            signed: "#28a745",
            expired: "#dc3545",
            cancelled: "#343a40",
        };
        
        const labels = Object.keys(data);
        const values = Object.values(data);
        const total = values.reduce((a, b) => a + b, 0);
        
        if (total === 0) {
            ctx.fillStyle = "#e9ecef";
            ctx.beginPath();
            ctx.arc(100, 100, 80, 0, 2 * Math.PI);
            ctx.fill();
            ctx.fillStyle = "#6c757d";
            ctx.font = "14px sans-serif";
            ctx.textAlign = "center";
            ctx.fillText("No data", 100, 105);
            return;
        }
        
        let startAngle = -Math.PI / 2;
        labels.forEach((label, i) => {
            const sliceAngle = (values[i] / total) * 2 * Math.PI;
            ctx.beginPath();
            ctx.moveTo(100, 100);
            ctx.arc(100, 100, 80, startAngle, startAngle + sliceAngle);
            ctx.closePath();
            ctx.fillStyle = colors[label] || "#999";
            ctx.fill();
            startAngle += sliceAngle;
        });
        
        ctx.beginPath();
        ctx.arc(100, 100, 50, 0, 2 * Math.PI);
        ctx.fillStyle = "#fff";
        ctx.fill();
        
        ctx.fillStyle = "#333";
        ctx.font = "bold 24px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(total, 100, 105);
        ctx.font = "12px sans-serif";
        ctx.fillText("Total", 100, 120);
    }

    renderTrendChart() {
        const canvas = document.getElementById("trendChart");
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        const data = this.state.data.trend_data;
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        if (!data || data.length === 0) return;
        
        const width = canvas.width - 60;
        const height = canvas.height - 40;
        const maxVal = Math.max(...data.map(d => Math.max(d.sent, d.completed)), 1);
        
        ctx.strokeStyle = "#e9ecef";
        ctx.lineWidth = 1;
        for (let i = 0; i <= 4; i++) {
            const y = 20 + (height / 4) * i;
            ctx.beginPath();
            ctx.moveTo(40, y);
            ctx.lineTo(canvas.width - 20, y);
            ctx.stroke();
        }
        
        ctx.strokeStyle = "#17a2b8";
        ctx.lineWidth = 2;
        ctx.beginPath();
        data.forEach((d, i) => {
            const x = 50 + (width / (data.length - 1)) * i;
            const y = 20 + height - (d.sent / maxVal) * height;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
        
        ctx.strokeStyle = "#28a745";
        ctx.beginPath();
        data.forEach((d, i) => {
            const x = 50 + (width / (data.length - 1)) * i;
            const y = 20 + height - (d.completed / maxVal) * height;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
        
        ctx.fillStyle = "#6c757d";
        ctx.font = "10px sans-serif";
        ctx.textAlign = "center";
        data.forEach((d, i) => {
            const x = 50 + (width / (data.length - 1)) * i;
            ctx.fillText(d.date, x, canvas.height - 5);
        });
    }

    openAllRequests() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Signature Requests",
            res_model: "signature.request",
            view_mode: "kanban,tree,form",
            views: [[false, "kanban"], [false, "tree"], [false, "form"]],
            target: "current",
        });
    }

    openPendingRequests() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Signatures",
            res_model: "signature.request",
            view_mode: "kanban,tree,form",
            views: [[false, "kanban"], [false, "tree"], [false, "form"]],
            domain: [["state", "in", ["sent", "partially_signed"]]],
            target: "current",
        });
    }

    openCompletedRequests() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Completed Signatures",
            res_model: "signature.request",
            view_mode: "kanban,tree,form",
            views: [[false, "kanban"], [false, "tree"], [false, "form"]],
            domain: [["state", "=", "signed"]],
            target: "current",
        });
    }

    openTemplates() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Signature Templates",
            res_model: "signature.template",
            view_mode: "kanban,tree,form",
            views: [[false, "kanban"], [false, "tree"], [false, "form"]],
            target: "current",
        });
    }

    createNewRequest() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Signature Request",
            res_model: "signature.request",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    getStatusColor(status) {
        const colors = {
            draft: "secondary",
            sent: "info",
            partially_signed: "warning",
            signed: "success",
            expired: "danger",
            cancelled: "dark",
        };
        return colors[status] || "secondary";
    }

    getActionIcon(action) {
        const icons = {
            created: "fa-plus-circle",
            sent: "fa-paper-plane",
            viewed: "fa-eye",
            signed: "fa-check-circle",
            declined: "fa-times-circle",
            reminder: "fa-bell",
            completed: "fa-trophy",
            cancelled: "fa-ban",
            expired: "fa-clock-o",
            reset: "fa-refresh",
        };
        return icons[action] || "fa-info-circle";
    }

    formatTime(timestamp) {
        if (!timestamp) return "";
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return "Just now";
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return date.toLocaleDateString();
    }
}

registry.category("actions").add("esignature_dashboard", ESignatureDashboard);
