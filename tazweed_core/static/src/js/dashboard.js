/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class TazweedDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            totalEmployees: 0,
            uaeNationals: 0,
            expiringDocs: 0,
            availableEmployees: 0,
            activeContracts: 0,
            activeSponsors: 0,
            loading: true,
        });
        onWillStart(async () => { await this.loadDashboardData(); });
    }

    async loadDashboardData() {
        try {
            const employees = await this.orm.searchCount("hr.employee", []);
            const uaeNationals = await this.orm.searchCount("hr.employee", [["is_uae_national", "=", true]]);
            const available = await this.orm.searchCount("hr.employee", [["is_available", "=", true]]);
            const expiringDocs = await this.orm.searchCount("tazweed.employee.document", [["state", "in", ["expiring", "expired"]]]);
            const sponsors = await this.orm.searchCount("tazweed.employee.sponsor", [["state", "=", "active"]]);
            const contracts = await this.orm.searchCount("hr.contract", [["state", "=", "open"]]);
            this.state.totalEmployees = employees;
            this.state.uaeNationals = uaeNationals;
            this.state.expiringDocs = expiringDocs;
            this.state.availableEmployees = available;
            this.state.activeContracts = contracts;
            this.state.activeSponsors = sponsors;
            this.state.loading = false;
        } catch (error) {
            console.error("Error loading dashboard:", error);
            this.state.loading = false;
        }
    }

    get uaePercentage() {
        if (this.state.totalEmployees === 0) return 0;
        return Math.round((this.state.uaeNationals / this.state.totalEmployees) * 100);
    }

    openEmployees() { this.action.doAction("hr.open_view_employee_list_my"); }
    openDocuments() {
        this.action.doAction({ type: "ir.actions.act_window", name: "Documents", res_model: "tazweed.employee.document", view_mode: "tree,form", views: [[false, "list"], [false, "form"]] });
    }
    openSponsors() {
        this.action.doAction({ type: "ir.actions.act_window", name: "Sponsors", res_model: "tazweed.employee.sponsor", view_mode: "tree,form", views: [[false, "list"], [false, "form"]] });
    }
    addEmployee() {
        this.action.doAction({ type: "ir.actions.act_window", name: "New Employee", res_model: "hr.employee", view_mode: "form", views: [[false, "form"]], target: "current" });
    }
    addDocument() {
        this.action.doAction({ type: "ir.actions.act_window", name: "New Document", res_model: "tazweed.employee.document", view_mode: "form", views: [[false, "form"]], target: "new" });
    }
}

TazweedDashboard.template = "tazweed_core.Dashboard";
registry.category("actions").add("tazweed_dashboard", TazweedDashboard);
