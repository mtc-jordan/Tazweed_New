/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";

export class PayrollDashboard extends Component {
    static template = "tazweed_payroll.PayrollDashboard";
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
            selectedPeriod: "current",
            stats: {
                totalPayroll: 0,
                employeesPaid: 0,
                pendingPayslips: 0,
                avgSalary: 0,
                totalDeductions: 0,
                totalAllowances: 0,
                wpsGenerated: 0,
                loansOutstanding: 0,
            },
            payrollByDepartment: [],
            salaryDistribution: [],
            monthlyTrend: [],
            recentPayslips: [],
            pendingLoans: [],
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
                "hr.payslip",
                "get_payroll_dashboard_data",
                [this.state.selectedPeriod]
            );
            
            this.state.stats = data.stats || this.state.stats;
            this.state.payrollByDepartment = data.payroll_by_department || [];
            this.state.salaryDistribution = data.salary_distribution || [];
            this.state.monthlyTrend = data.monthly_trend || [];
            this.state.recentPayslips = data.recent_payslips || [];
            this.state.pendingLoans = data.pending_loans || [];
            this.state.alerts = data.alerts || [];
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading payroll dashboard data:", error);
            this.state.loading = false;
        }
    }

    renderCharts() {
        this.renderDepartmentChart();
        this.renderDistributionChart();
        this.renderTrendChart();
    }

    renderDepartmentChart() {
        const canvas = document.getElementById("departmentPayrollChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.payrollByDepartment;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    label: "Payroll Amount",
                    data: data.map(d => d.amount),
                    backgroundColor: "#3B82F6",
                    borderRadius: 6,
                    barThickness: 35,
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
                        ticks: { font: { size: 11 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(0,0,0,0.05)" },
                        ticks: {
                            font: { size: 11 },
                            callback: (value) => this.formatCurrency(value)
                        }
                    }
                }
            }
        });
    }

    renderDistributionChart() {
        const canvas = document.getElementById("salaryDistributionChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.salaryDistribution;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        const colors = [
            "#10B981", "#3B82F6", "#F59E0B", "#EF4444", 
            "#8B5CF6", "#EC4899", "#06B6D4"
        ];

        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map(d => d.range),
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
                cutout: "65%",
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

    renderTrendChart() {
        const canvas = document.getElementById("payrollTrendChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        
        // Generate sample trend data
        const labels = this.getLast6Months();
        const payrollData = [450000, 465000, 480000, 475000, 490000, 510000];
        const employeesData = [45, 47, 48, 48, 50, 52];

        new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Total Payroll (AED)",
                        data: payrollData,
                        borderColor: "#3B82F6",
                        backgroundColor: "rgba(59, 130, 246, 0.1)",
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y',
                    },
                    {
                        label: "Employees",
                        data: employeesData,
                        borderColor: "#10B981",
                        backgroundColor: "transparent",
                        borderDash: [5, 5],
                        tension: 0.4,
                        yAxisID: 'y1',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
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
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: "rgba(0,0,0,0.05)" },
                        ticks: {
                            font: { size: 10 },
                            callback: (value) => this.formatCurrency(value)
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: { drawOnChartArea: false },
                        ticks: { font: { size: 10 } }
                    },
                }
            }
        });
    }

    getLast6Months() {
        const months = [];
        for (let i = 5; i >= 0; i--) {
            const date = new Date();
            date.setMonth(date.getMonth() - i);
            months.push(date.toLocaleDateString("en-US", { month: "short" }));
        }
        return months;
    }

    drawNoDataMessage(ctx, canvas) {
        ctx.fillStyle = "#9CA3AF";
        ctx.font = "14px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("No data available", canvas.width / 2, canvas.height / 2);
    }

    formatCurrency(value) {
        if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        } else if (value >= 1000) {
            return (value / 1000).toFixed(0) + 'K';
        }
        return value.toLocaleString();
    }

    async onPeriodChange(ev) {
        this.state.selectedPeriod = ev.target.value;
        this.state.loading = true;
        await this.loadDashboardData();
        this.renderCharts();
    }

    onGeneratePayslips() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Generate Payslips",
            res_model: "hr.payslip.run",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    onViewAllPayslips() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Payslips",
            res_model: "hr.payslip",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    onViewLoans() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Loans",
            res_model: "payroll.loan",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    onGenerateWPS() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Generate WPS File",
            res_model: "wps.file.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }

    onViewGratuity() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Gratuity",
            res_model: "hr.gratuity",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    getStatusClass(state) {
        const classes = {
            draft: "badge-secondary",
            verify: "badge-info",
            done: "badge-success",
            cancel: "badge-danger",
        };
        return classes[state] || "badge-secondary";
    }

    getStatusLabel(state) {
        const labels = {
            draft: "Draft",
            verify: "Waiting",
            done: "Done",
            cancel: "Cancelled",
        };
        return labels[state] || state;
    }
}

registry.category("actions").add("payroll_dashboard", PayrollDashboard);
