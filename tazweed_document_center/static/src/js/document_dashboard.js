/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onWillStart } = owl;

/**
 * Document Dashboard Widget
 * Displays document expiry statistics and alerts
 */
export class DocumentDashboardWidget extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        
        this.state = useState({
            loading: true,
            stats: {
                total: 0,
                expired: 0,
                expiring_7: 0,
                expiring_15: 0,
                expiring_30: 0,
                valid: 0,
            },
            alerts: {
                critical: 0,
                high: 0,
                normal: 0,
                low: 0,
            },
            compliance: {
                compliant: 0,
                warning: 0,
                non_compliant: 0,
                rate: 0,
            }
        });
        
        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }
    
    async loadDashboardData() {
        try {
            const data = await this.rpc("/document/dashboard/data");
            if (data) {
                this.state.stats = data.stats || this.state.stats;
                this.state.alerts = data.alerts || this.state.alerts;
                this.state.compliance = data.compliance || this.state.compliance;
            }
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }
    
    async refreshData() {
        this.state.loading = true;
        await this.loadDashboardData();
    }
    
    viewExpired() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Expired Documents',
            res_model: 'tazweed.employee.document',
            view_mode: 'tree,form',
            domain: [['expiry_date', '<', new Date().toISOString().split('T')[0]]],
        });
    }
    
    viewExpiring(days) {
        const today = new Date();
        const futureDate = new Date();
        futureDate.setDate(today.getDate() + days);
        
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: `Expiring in ${days} Days`,
            res_model: 'tazweed.employee.document',
            view_mode: 'tree,form',
            domain: [
                ['expiry_date', '>=', today.toISOString().split('T')[0]],
                ['expiry_date', '<=', futureDate.toISOString().split('T')[0]]
            ],
        });
    }
    
    viewAlerts() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Document Alerts',
            res_model: 'document.alert',
            view_mode: 'tree,kanban,form',
            domain: [['state', 'not in', ['resolved']]],
        });
    }
    
    viewCompliance() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Compliance Report',
            res_model: 'document.compliance.report',
            view_mode: 'tree,pivot,graph',
        });
    }
}

DocumentDashboardWidget.template = "tazweed_document_center.DashboardWidget";

// Register the widget
registry.category("actions").add("document_dashboard_widget", DocumentDashboardWidget);

/**
 * Document Alert Counter
 * Shows alert count in systray
 */
export class DocumentAlertCounter extends Component {
    setup() {
        this.rpc = useService("rpc");
        
        this.state = useState({
            count: 0,
            critical: 0,
        });
        
        onWillStart(async () => {
            await this.loadAlertCount();
        });
        
        // Refresh every 5 minutes
        setInterval(() => this.loadAlertCount(), 300000);
    }
    
    async loadAlertCount() {
        try {
            const data = await this.rpc("/document/alerts/count");
            if (data) {
                this.state.count = data.total || 0;
                this.state.critical = data.critical || 0;
            }
        } catch (error) {
            console.error("Error loading alert count:", error);
        }
    }
}

DocumentAlertCounter.template = "tazweed_document_center.AlertCounter";

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
