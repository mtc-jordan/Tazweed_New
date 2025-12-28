/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";

export class EmployeeDashboard extends Component {
    static template = "tazweed_employee_portal.EmployeeDashboard";
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
            employee: null,
            stats: {
                leaveBalance: 0,
                pendingRequests: 0,
                upcomingHolidays: 0,
                attendanceRate: 0,
                trainingHours: 0,
                performanceRating: 0,
                documentsExpiring: 0,
                announcements: 0,
            },
            leaveBalances: [],
            recentActivities: [],
            upcomingEvents: [],
            quickLinks: [],
            announcements: [],
            teamMembers: [],
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
                "hr.employee",
                "get_employee_dashboard_data",
                []
            );
            
            this.state.employee = data.employee || null;
            this.state.stats = data.stats || this.state.stats;
            this.state.leaveBalances = data.leave_balances || [];
            this.state.recentActivities = data.recent_activities || [];
            this.state.upcomingEvents = data.upcoming_events || [];
            this.state.quickLinks = data.quick_links || [];
            this.state.announcements = data.announcements || [];
            this.state.teamMembers = data.team_members || [];
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading employee dashboard data:", error);
            this.state.loading = false;
        }
    }

    renderCharts() {
        this.renderLeaveChart();
        this.renderAttendanceChart();
    }

    renderLeaveChart() {
        const canvas = document.getElementById("leaveBalanceChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.leaveBalances;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        const colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"];

        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    data: data.map(d => d.balance),
                    backgroundColor: colors.slice(0, data.length),
                    borderWidth: 0,
                    hoverOffset: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "65%",
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: {
                            padding: 12,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
    }

    renderAttendanceChart() {
        const canvas = document.getElementById("attendanceChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        
        // Sample attendance data for the last 7 days
        const labels = this.getLast7Days();
        const data = [8, 8.5, 7.5, 8, 9, 0, 0]; // Sample hours

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Hours Worked",
                    data: data,
                    backgroundColor: "#3B82F6",
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
                        max: 12,
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

    onRequestLeave() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Request Leave",
            res_model: "hr.leave",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }

    onViewPayslips() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Payslips",
            res_model: "hr.payslip",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["employee_id.user_id", "=", this.env.services.user.userId]],
            target: "current",
        });
    }

    onViewAttendance() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Attendance",
            res_model: "hr.attendance",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["employee_id.user_id", "=", this.env.services.user.userId]],
            target: "current",
        });
    }

    onViewDocuments() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Documents",
            res_model: "hr.employee.document",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    onViewProfile() {
        if (this.state.employee) {
            this.action.doAction({
                type: "ir.actions.act_window",
                name: "My Profile",
                res_model: "hr.employee",
                res_id: this.state.employee.id,
                view_mode: "form",
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    onViewTeam() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "My Team",
            res_model: "hr.employee",
            view_mode: "kanban,list,form",
            views: [[false, "kanban"], [false, "list"], [false, "form"]],
            target: "current",
        });
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString("en-US", { 
            month: "short", 
            day: "numeric"
        });
    }

    getActivityIcon(type) {
        const icons = {
            leave: "fa-calendar-check-o",
            attendance: "fa-clock-o",
            payslip: "fa-money",
            document: "fa-file-text-o",
            training: "fa-graduation-cap",
            performance: "fa-line-chart",
        };
        return icons[type] || "fa-info-circle";
    }

    getActivityColor(type) {
        const colors = {
            leave: "activity-blue",
            attendance: "activity-green",
            payslip: "activity-purple",
            document: "activity-orange",
            training: "activity-teal",
            performance: "activity-pink",
        };
        return colors[type] || "activity-gray";
    }
}

registry.category("actions").add("employee_dashboard", EmployeeDashboard);
