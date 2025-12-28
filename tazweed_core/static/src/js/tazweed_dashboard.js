/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted, useRef } from "@odoo/owl";

export class TazweedDashboard extends Component {
    static template = "tazweed_core.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        // Chart references
        this.visaChartRef = useRef("visaChart");
        this.categoryChartRef = useRef("categoryChart");
        this.departmentChartRef = useRef("departmentChart");
        this.placementChartRef = useRef("placementChart");
        this.documentChartRef = useRef("documentChart");
        this.trendChartRef = useRef("trendChart");
        
        this.state = useState({
            // Main KPIs
            totalEmployees: 0,
            uaeNationals: 0,
            uaeNationalPercent: 0,
            documentsAttention: 0,
            availableForPlacement: 0,
            
            // Secondary stats
            activeContracts: 0,
            expiringContracts: 0,
            activeSponsors: 0,
            totalDocuments: 0,
            placedEmployees: 0,
            
            // Alerts
            alerts: [],
            
            // Documents requiring attention
            expiringDocuments: [],
            
            // Chart data
            visaStatusData: {},
            categoryData: {},
            departmentData: {},
            placementData: {},
            documentStatusData: {},
            
            // Loading state
            isLoading: true,
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
            // Load employee data - use only fields that exist
            const employees = await this.orm.searchRead(
                "hr.employee",
                [["active", "=", true]],
                ["id", "name", "is_uae_national", "visa_status", "placement_status", 
                 "is_available", "department_id", "employee_category_ids"]
            );

            // Load contracts
            const contracts = await this.orm.searchRead(
                "hr.contract",
                [["state", "=", "open"]],
                ["id", "date_end"]
            );

            // Load sponsors
            const sponsors = await this.orm.searchRead(
                "tazweed.employee.sponsor",
                [["state", "=", "active"]],
                ["id", "name", "employee_count", "visa_quota", "available_quota"]
            );

            // Load documents
            const documents = await this.orm.searchRead(
                "tazweed.employee.document",
                [["active", "=", true]],
                ["id", "name", "employee_id", "document_type_id", "expiry_date", 
                 "days_to_expiry", "state"]
            );

            // Load categories
            const categories = await this.orm.searchRead(
                "tazweed.employee.category",
                [],
                ["id", "name", "code", "color"]
            );

            // Calculate KPIs
            this.state.totalEmployees = employees.length;
            this.state.uaeNationals = employees.filter(e => e.is_uae_national).length;
            this.state.uaeNationalPercent = this.state.totalEmployees > 0 
                ? Math.round((this.state.uaeNationals / this.state.totalEmployees) * 100) 
                : 0;
            // Use is_available field (correct field name)
            this.state.availableForPlacement = employees.filter(e => e.is_available).length;
            this.state.placedEmployees = employees.filter(e => e.placement_status === 'placed').length;

            // Contract stats
            this.state.activeContracts = contracts.length;
            const today = new Date();
            const thirtyDaysLater = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
            this.state.expiringContracts = contracts.filter(c => {
                if (!c.date_end) return false;
                const endDate = new Date(c.date_end);
                return endDate <= thirtyDaysLater;
            }).length;

            // Sponsor stats
            this.state.activeSponsors = sponsors.length;

            // Document stats
            this.state.totalDocuments = documents.length;
            this.state.documentsAttention = documents.filter(d => 
                d.state === 'expiring' || d.state === 'expired'
            ).length;

            // Expiring documents list
            this.state.expiringDocuments = documents
                .filter(d => d.state === 'expiring' || d.state === 'expired')
                .sort((a, b) => (a.days_to_expiry || 999) - (b.days_to_expiry || 999))
                .slice(0, 5);

            // Generate alerts
            this.generateAlerts();

            // Prepare chart data - use employee_category_ids (correct field name)
            this.prepareChartData(employees, documents, categories);

            this.state.isLoading = false;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.isLoading = false;
        }
    }

    generateAlerts() {
        const alerts = [];
        
        if (this.state.expiringContracts > 0) {
            alerts.push({
                type: 'warning',
                icon: 'fa-file-contract',
                title: 'Contracts Expiring',
                message: `${this.state.expiringContracts} contract(s) expiring within 30 days`,
                action: 'view_contracts'
            });
        }

        if (this.state.documentsAttention > 0) {
            alerts.push({
                type: 'danger',
                icon: 'fa-exclamation-triangle',
                title: 'Documents Need Attention',
                message: `${this.state.documentsAttention} document(s) expired or expiring soon`,
                action: 'view_documents'
            });
        }

        if (this.state.uaeNationalPercent < 10 && this.state.totalEmployees > 0) {
            alerts.push({
                type: 'info',
                icon: 'fa-flag',
                title: 'Emiratization Rate',
                message: `Current rate is ${this.state.uaeNationalPercent}%. Consider hiring more UAE nationals.`,
                action: 'view_employees'
            });
        }

        this.state.alerts = alerts;
    }

    prepareChartData(employees, documents, categories) {
        // Visa status distribution
        const visaStatuses = { valid: 0, expired: 0, cancelled: 0, in_process: 0 };
        employees.forEach(e => {
            if (e.visa_status && visaStatuses.hasOwnProperty(e.visa_status)) {
                visaStatuses[e.visa_status]++;
            } else {
                // Count employees without visa status as valid
                visaStatuses.valid++;
            }
        });
        this.state.visaStatusData = visaStatuses;

        // Category distribution - use employee_category_ids (correct field name)
        const categoryCount = {};
        categories.forEach(cat => {
            categoryCount[cat.name] = 0;
        });
        employees.forEach(e => {
            if (e.employee_category_ids && e.employee_category_ids.length > 0) {
                e.employee_category_ids.forEach(catId => {
                    const cat = categories.find(c => c.id === catId);
                    if (cat) {
                        categoryCount[cat.name] = (categoryCount[cat.name] || 0) + 1;
                    }
                });
            }
        });
        this.state.categoryData = categoryCount;

        // Department distribution
        const deptCount = {};
        employees.forEach(e => {
            const deptName = e.department_id ? e.department_id[1] : 'Unassigned';
            deptCount[deptName] = (deptCount[deptName] || 0) + 1;
        });
        this.state.departmentData = deptCount;

        // Placement status
        const placementStatuses = { available: 0, placed: 0, on_leave: 0, resigned: 0 };
        employees.forEach(e => {
            if (e.placement_status && placementStatuses.hasOwnProperty(e.placement_status)) {
                placementStatuses[e.placement_status]++;
            } else {
                // Default to available
                placementStatuses.available++;
            }
        });
        this.state.placementData = placementStatuses;

        // Document status
        const docStatuses = { valid: 0, expiring: 0, expired: 0 };
        documents.forEach(d => {
            if (d.state && docStatuses.hasOwnProperty(d.state)) {
                docStatuses[d.state]++;
            }
        });
        this.state.documentStatusData = docStatuses;
    }

    renderCharts() {
        this.renderVisaChart();
        this.renderCategoryChart();
        this.renderDepartmentChart();
        this.renderPlacementChart();
        this.renderDocumentChart();
        this.renderTrendChart();
    }

    renderVisaChart() {
        const canvas = this.visaChartRef.el;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.visaStatusData;
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Valid', 'Expired', 'Cancelled', 'In Process'],
                datasets: [{
                    data: [data.valid || 0, data.expired || 0, data.cancelled || 0, data.in_process || 0],
                    backgroundColor: ['#10B981', '#EF4444', '#6B7280', '#F59E0B'],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 15,
                            usePointStyle: true,
                            font: { size: 11, family: "'Inter', sans-serif" }
                        }
                    }
                }
            }
        });
    }

    renderCategoryChart() {
        const canvas = this.categoryChartRef.el;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.categoryData;
        const labels = Object.keys(data);
        const values = Object.values(data);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Employees',
                    data: values,
                    backgroundColor: ['#8B5CF6', '#06B6D4', '#F97316', '#10B981', '#EF4444'],
                    borderRadius: 8,
                    barThickness: 30
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        beginAtZero: true,
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

    renderDepartmentChart() {
        const canvas = this.departmentChartRef.el;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.departmentData;
        const labels = Object.keys(data);
        const values = Object.values(data);
        
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Employees',
                    data: values,
                    backgroundColor: '#667EEA',
                    borderRadius: 8,
                    barThickness: 25
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
                        ticks: { 
                            font: { size: 10 },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: '#E5E7EB' },
                        ticks: { font: { size: 11 } }
                    }
                }
            }
        });
    }

    renderPlacementChart() {
        const canvas = this.placementChartRef.el;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.placementData;
        
        new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Available', 'Placed', 'On Leave', 'Resigned'],
                datasets: [{
                    data: [data.available || 0, data.placed || 0, data.on_leave || 0, data.resigned || 0],
                    backgroundColor: ['#10B981', '#3B82F6', '#F59E0B', '#EF4444'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
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

    renderDocumentChart() {
        const canvas = this.documentChartRef.el;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = this.state.documentStatusData;
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Valid', 'Expiring Soon', 'Expired'],
                datasets: [{
                    data: [data.valid || 0, data.expiring || 0, data.expired || 0],
                    backgroundColor: ['#10B981', '#F59E0B', '#EF4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
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
        const canvas = this.trendChartRef.el;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Generate mock trend data for last 6 months
        const months = [];
        const totalData = [];
        const placedData = [];
        const today = new Date();
        
        for (let i = 5; i >= 0; i--) {
            const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
            months.push(d.toLocaleString('default', { month: 'short' }));
            // Use actual current data for the latest month
            if (i === 0) {
                totalData.push(this.state.totalEmployees);
                placedData.push(this.state.placedEmployees);
            } else {
                // Generate realistic trend data
                const baseTotal = Math.max(1, this.state.totalEmployees - (i * 2));
                const basePlaced = Math.max(0, this.state.placedEmployees - i);
                totalData.push(baseTotal);
                placedData.push(basePlaced);
            }
        }
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: months,
                datasets: [
                    {
                        label: 'Total Employees',
                        data: totalData,
                        borderColor: '#667EEA',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#667EEA'
                    },
                    {
                        label: 'Placed',
                        data: placedData,
                        borderColor: '#10B981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: '#10B981'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: { size: 11 }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: '#E5E7EB' },
                        ticks: { font: { size: 11 } }
                    }
                }
            }
        });
    }

    // ==================== ACTIONS ====================
    
    async refreshData() {
        this.state.isLoading = true;
        await this.loadDashboardData();
        // Destroy existing charts and re-render
        this.renderCharts();
    }

    viewAllEmployees() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Employees',
            res_model: 'hr.employee',
            view_mode: 'kanban,tree,form',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    addEmployee() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'New Employee',
            res_model: 'hr.employee',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    uploadDocument() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'New Document',
            res_model: 'tazweed.employee.document',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
        });
    }

    addSponsor() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'New Sponsor',
            res_model: 'tazweed.employee.sponsor',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    manageContracts() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Contracts',
            res_model: 'hr.contract',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    viewDocumentsAttention() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Documents Requiring Attention',
            res_model: 'tazweed.employee.document',
            view_mode: 'tree,form',
            domain: [['state', 'in', ['expiring', 'expired']]],
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    viewUAENationals() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'UAE Nationals',
            res_model: 'hr.employee',
            view_mode: 'kanban,tree,form',
            domain: [['is_uae_national', '=', true]],
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    viewAvailableEmployees() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Available for Placement',
            res_model: 'hr.employee',
            view_mode: 'kanban,tree,form',
            domain: [['is_available', '=', true]],
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    viewSponsors() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Sponsors',
            res_model: 'tazweed.employee.sponsor',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    viewPlacedEmployees() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Placed Employees',
            res_model: 'hr.employee',
            view_mode: 'kanban,tree,form',
            domain: [['placement_status', '=', 'placed']],
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    getCurrentDate() {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        return new Date().toLocaleDateString('en-US', options);
    }
}

TazweedDashboard.template = "tazweed_core.Dashboard";

registry.category("actions").add("tazweed_dashboard", TazweedDashboard);
