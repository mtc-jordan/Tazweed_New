/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class ProDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: null,
            loading: true,
        });
        
        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            const data = await this.orm.call("pro.dashboard", "get_dashboard_data", []);
            this.state.data = data;
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.loading = false;
        }
    }

    async refresh() {
        this.state.loading = true;
        await this.loadDashboardData();
    }

    openRequests(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Service Requests",
            res_model: "pro.service.request",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: state ? [["state", "=", state]] : [],
        });
    }

    openTasks(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Tasks",
            res_model: "pro.task",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: state ? [["state", "=", state]] : [],
        });
    }

    openBilling(status) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Billing",
            res_model: "pro.billing",
            view_mode: "tree,form",
            views: [[false, "list"], [false, "form"]],
            domain: status ? [["payment_status", "=", status]] : [],
        });
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('en-AE', {
            style: 'currency',
            currency: 'AED',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(amount);
    }
}

ProDashboard.template = "tazweed_pro_services.ProDashboard";

registry.category("actions").add("pro_dashboard", ProDashboard);
