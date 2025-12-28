/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";

export class PerformanceDashboard extends Component {
    static template = "tazweed_performance.PerformanceDashboard";
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
                totalReviews: 0,
                pendingReviews: 0,
                completedReviews: 0,
                avgRating: 0,
                activeGoals: 0,
                goalsAchieved: 0,
                feedbackGiven: 0,
                developmentPlans: 0,
            },
            ratingDistribution: [],
            reviewsByDepartment: [],
            goalProgress: [],
            recentReviews: [],
            topPerformers: [],
            upcomingReviews: [],
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
                "performance.review",
                "get_performance_dashboard_data",
                [this.state.selectedPeriod]
            );
            
            this.state.stats = data.stats || this.state.stats;
            this.state.ratingDistribution = data.rating_distribution || [];
            this.state.reviewsByDepartment = data.reviews_by_department || [];
            this.state.goalProgress = data.goal_progress || [];
            this.state.recentReviews = data.recent_reviews || [];
            this.state.topPerformers = data.top_performers || [];
            this.state.upcomingReviews = data.upcoming_reviews || [];
            this.state.alerts = data.alerts || [];
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading performance dashboard data:", error);
            this.state.loading = false;
        }
    }

    renderCharts() {
        this.renderRatingChart();
        this.renderDepartmentChart();
        this.renderGoalChart();
    }

    renderRatingChart() {
        const canvas = document.getElementById("ratingDistributionChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.ratingDistribution;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        const colors = ["#EF4444", "#F97316", "#F59E0B", "#10B981", "#3B82F6"];

        new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: data.map(d => d.rating),
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

    renderDepartmentChart() {
        const canvas = document.getElementById("departmentReviewChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.reviewsByDepartment;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.name),
                datasets: [
                    {
                        label: "Completed",
                        data: data.map(d => d.completed),
                        backgroundColor: "#10B981",
                        borderRadius: 4,
                    },
                    {
                        label: "Pending",
                        data: data.map(d => d.pending),
                        backgroundColor: "#F59E0B",
                        borderRadius: 4,
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
                        ticks: { font: { size: 10 } },
                        stacked: true,
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(0,0,0,0.05)" },
                        ticks: { font: { size: 10 } },
                        stacked: true,
                    }
                }
            }
        });
    }

    renderGoalChart() {
        const canvas = document.getElementById("goalProgressChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const data = this.state.goalProgress;
        
        if (data.length === 0) {
            this.drawNoDataMessage(ctx, canvas);
            return;
        }

        new Chart(ctx, {
            type: "bar",
            data: {
                labels: data.map(d => d.status),
                datasets: [{
                    label: "Goals",
                    data: data.map(d => d.count),
                    backgroundColor: ["#3B82F6", "#10B981", "#F59E0B", "#EF4444"],
                    borderRadius: 6,
                    barThickness: 40,
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

    drawNoDataMessage(ctx, canvas) {
        ctx.fillStyle = "#9CA3AF";
        ctx.font = "14px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("No data available", canvas.width / 2, canvas.height / 2);
    }

    async onPeriodChange(ev) {
        this.state.selectedPeriod = ev.target.value;
        this.state.loading = true;
        await this.loadDashboardData();
        this.renderCharts();
    }

    onNewReview() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "New Performance Review",
            res_model: "performance.review",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    onViewAllReviews() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Reviews",
            res_model: "performance.review",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    onViewGoals() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Goals",
            res_model: "performance.goal",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    onViewFeedback() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Feedback",
            res_model: "performance.feedback",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    onViewCompetencies() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Competencies",
            res_model: "hr.competency",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    getRatingStars(rating) {
        const fullStars = Math.floor(rating);
        const halfStar = rating % 1 >= 0.5;
        let stars = "★".repeat(fullStars);
        if (halfStar) stars += "½";
        return stars;
    }

    getRatingClass(rating) {
        if (rating >= 4.5) return "rating-excellent";
        if (rating >= 3.5) return "rating-good";
        if (rating >= 2.5) return "rating-average";
        return "rating-poor";
    }

    getStatusClass(state) {
        const classes = {
            draft: "badge-secondary",
            in_progress: "badge-info",
            submitted: "badge-warning",
            completed: "badge-success",
            cancelled: "badge-danger",
        };
        return classes[state] || "badge-secondary";
    }

    getStatusLabel(state) {
        const labels = {
            draft: "Draft",
            in_progress: "In Progress",
            submitted: "Submitted",
            completed: "Completed",
            cancelled: "Cancelled",
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

registry.category("actions").add("performance_dashboard", PerformanceDashboard);
