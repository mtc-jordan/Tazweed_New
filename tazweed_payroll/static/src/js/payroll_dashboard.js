/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";

export class PayrollDashboard extends Component {
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
        
        this.departmentChartRef = useRef("departmentChart");
        this.distributionChartRef = useRef("distributionChart");
        this.trendChartRef = useRef("trendChart");
        
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
        const canvas = this.departmentChartRef.el;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.payrollByDepartment;
        
        if (this.charts.department) {
            this.charts.department.destroy();
        }
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        this.charts.department = new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.name),
                datasets: [{
                    label: "Payroll Amount",
                    data: data.map(d => d.amount),
                    backgroundColor: "rgba(59, 130, 246, 0.8)",
                    borderColor: "rgb(59, 130, 246)",
                    borderRadius: 6,
                    barThickness: 35,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: "Payroll by Department",
                        font: { size: 16, weight: "bold" },
                        color: "#374151",
                    }
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
        const canvas = this.distributionChartRef.el;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.salaryDistribution;
        
        if (this.charts.distribution) {
            this.charts.distribution.destroy();
        }
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        const colors = [
            "rgba(16, 185, 129, 0.8)", 
            "rgba(59, 130, 246, 0.8)", 
            "rgba(245, 158, 11, 0.8)", 
            "rgba(239, 68, 68, 0.8)", 
            "rgba(139, 92, 246, 0.8)", 
            "rgba(236, 72, 153, 0.8)", 
            "rgba(6, 182, 212, 0.8)"
        ];

        this.charts.distribution = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map(d => d.range),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: colors.slice(0, data.length),
                    borderWidth: 2,
                    borderColor: "#fff",
                    hoverOffset: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "65%",
                plugins: {
                    legend: {
                        position: "right",
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: { size: 11 }
                        }
                    },
                    title: {
                        display: true,
                        text: "Salary Distribution",
                        font: { size: 16, weight: "bold" },
                        color: "#374151",
                    }
                }
            }
        });
    }

    renderTrendChart() {
        const canvas = this.trendChartRef.el;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        
        if (this.charts.trend) {
            this.charts.trend.destroy();
        }
        
        // Generate sample trend data
        const labels = this.getLast6Months();
        const payrollData = [450000, 465000, 480000, 475000, 490000, 510000];
        const employeesData = [45, 47, 48, 48, 50, 52];

        this.charts.trend = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Total Payroll (AED)",
                        data: payrollData,
                        borderColor: "rgb(59, 130, 246)",
                        backgroundColor: "rgba(59, 130, 246, 0.1)",
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: "rgb(59, 130, 246)",
                        pointBorderColor: "#fff",
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        yAxisID: 'y',
                    },
                    {
                        label: "Employees",
                        data: employeesData,
                        borderColor: "rgb(16, 185, 129)",
                        backgroundColor: "transparent",
                        borderDash: [5, 5],
                        tension: 0.4,
                        pointBackgroundColor: "rgb(16, 185, 129)",
                        pointBorderColor: "#fff",
                        pointBorderWidth: 2,
                        pointRadius: 6,
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
                    },
                    title: {
                        display: true,
                        text: "Payroll Trend (Last 6 Months)",
                        font: { size: 16, weight: "bold" },
                        color: "#374151",
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
    
    async refreshData() {
        this.state.loading = true;
        await this.loadDashboardData();
        this.renderCharts();
    }
}

PayrollDashboard.template = "tazweed_payroll.PayrollDashboard";

registry.category("actions").add("payroll_dashboard", PayrollDashboard);
