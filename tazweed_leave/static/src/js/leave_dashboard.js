/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";

export class LeaveDashboard extends Component {
    static template = "tazweed_leave.LeaveDashboard";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
        className: { type: String, optional: true },
        globalState: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            dateRange: "month",
            stats: {
                totalEmployees: 0,
                onLeaveToday: 0,
                pendingRequests: 0,
                approvedThisMonth: 0,
                avgLeaveDays: 0,
                leaveUtilization: 0,
            },
            leaveByType: [],
            leaveByDepartment: [],
            recentRequests: [],
            upcomingLeaves: [],
            leaveCalendar: [],
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
                "hr.leave",
                "get_leave_dashboard_data",
                [this.state.dateRange]
            );
            
            this.state.stats = data.stats || this.state.stats;
            this.state.leaveByType = data.leave_by_type || [];
            this.state.leaveByDepartment = data.leave_by_department || [];
            this.state.recentRequests = data.recent_requests || [];
            this.state.upcomingLeaves = data.upcoming_leaves || [];
            this.state.leaveCalendar = data.leave_calendar || [];
            this.state.alerts = data.alerts || [];
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading leave dashboard data:", error);
            this.state.loading = false;
        }
    }

    renderCharts() {
        this.renderLeaveTypeChart();
        this.renderDepartmentChart();
        this.renderTrendChart();
    }

    renderLeaveTypeChart() {
        const canvas = document.getElementById("leaveTypeChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.leaveByType;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        const colors = [
            "#10B981", "#3B82F6", "#F59E0B", "#EF4444", 
            "#8B5CF6", "#EC4899", "#06B6D4", "#84CC16"
        ];

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
                cutout: "70%",
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

    renderDepartmentChart() {
        const canvas = document.getElementById("departmentChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.leaveByDepartment;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    label: "Leave Days",
                    data: data.map(d => d.days),
                    backgroundColor: "#3B82F6",
                    borderRadius: 6,
                    barThickness: 30,
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
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    }
                }
            }
        });
    }

    renderTrendChart() {
        const canvas = document.getElementById("trendChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        
        // Generate sample trend data
        const labels = this.getLast7Days();
        const requestsData = [5, 8, 3, 12, 7, 4, 9];
        const approvalsData = [4, 6, 3, 10, 5, 4, 7];

        new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Requests",
                        data: requestsData,
                        borderColor: "#3B82F6",
                        backgroundColor: "rgba(59, 130, 246, 0.1)",
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                    },
                    {
                        label: "Approvals",
                        data: approvalsData,
                        borderColor: "#10B981",
                        backgroundColor: "rgba(16, 185, 129, 0.1)",
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                        labels: {
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 10 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(0,0,0,0.05)" },
                        ticks: { font: { size: 10 } }
                    }
                }
            }
        });
    }

    getLast7Days() {
        const days = [];
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            days.push(date.toLocaleDateString("en-US", { weekday: "short" }));
        }
        return days;
    }

    drawNoDataMessage(ctx, canvas) {
        ctx.fillStyle = "#9CA3AF";
        ctx.font = "14px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("No data available", canvas.width / 2, canvas.height / 2);
    }

    async onDateRangeChange(ev) {
        this.state.dateRange = ev.target.value;
        this.state.loading = true;
        await this.loadDashboardData();
        this.renderCharts();
    }

    onNewRequest() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Leave Request",
            res_model: "hr.leave",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    onViewAllRequests() {
        this.action.doAction("hr_holidays.hr_leave_action_action_approve_department");
    }

    onViewAllocations() {
        this.action.doAction("hr_holidays.hr_leave_allocation_action_all");
    }

    onViewCalendar() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Leave Calendar",
            res_model: "hr.leave",
            view_mode: "calendar",
            views: [[false, "calendar"]],
            target: "current",
        });
    }

    onViewPendingRequests() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Pending Requests",
            res_model: "hr.leave",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "confirm"]],
            target: "current",
        });
    }

    getStatusClass(state) {
        const classes = {
            draft: "badge-secondary",
            confirm: "badge-warning",
            validate1: "badge-info",
            validate: "badge-success",
            refuse: "badge-danger",
        };
        return classes[state] || "badge-secondary";
    }

    getStatusLabel(state) {
        const labels = {
            draft: "Draft",
            confirm: "Pending",
            validate1: "First Approval",
            validate: "Approved",
            refuse: "Refused",
        };
        return labels[state] || state;
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString("en-US", { 
            month: "short", 
            day: "numeric",
            year: "numeric"
        });
    }
}

registry.category("actions").add("leave_dashboard", LeaveDashboard);
