# -*- coding: utf-8 -*-
"""
Dashboard Widgets Module
Provides quick KPI widgets for Odoo dashboard
"""

from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class AnalyticsDashboardWidget(models.Model):
    """Analytics Dashboard Widget for quick KPI display."""
    _name = 'analytics.dashboard.widget'
    _description = 'Analytics Dashboard Widget'
    _order = 'sequence, id'

    name = fields.Char(string='Widget Name', required=True)
    widget_type = fields.Selection([
        ('cost_center', 'Cost Center'),
        ('recruitment', 'Recruitment'),
        ('compliance', 'Compliance'),
        ('payroll', 'Payroll'),
        ('executive', 'Executive Summary'),
    ], string='Widget Type', required=True, default='executive')
    
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Display settings
    color = fields.Selection([
        ('primary', 'Blue'),
        ('success', 'Green'),
        ('warning', 'Orange'),
        ('danger', 'Red'),
        ('info', 'Cyan'),
        ('secondary', 'Gray'),
    ], string='Color Theme', default='primary')
    
    icon = fields.Char(string='Icon', default='fa-chart-bar')
    show_trend = fields.Boolean(string='Show Trend', default=True)
    
    # User assignment
    user_ids = fields.Many2many('res.users', string='Visible to Users',
                                 help='Leave empty to show to all users')
    
    # Computed KPI values
    kpi_value = fields.Char(string='KPI Value', compute='_compute_kpi_values')
    kpi_label = fields.Char(string='KPI Label', compute='_compute_kpi_values')
    kpi_trend = fields.Float(string='KPI Trend %', compute='_compute_kpi_values')
    kpi_trend_direction = fields.Selection([
        ('up', 'Up'),
        ('down', 'Down'),
        ('stable', 'Stable'),
    ], string='Trend Direction', compute='_compute_kpi_values')
    
    @api.depends('widget_type')
    def _compute_kpi_values(self):
        """Compute KPI values based on widget type."""
        for widget in self:
            try:
                if widget.widget_type == 'cost_center':
                    widget._compute_cost_center_kpi()
                elif widget.widget_type == 'recruitment':
                    widget._compute_recruitment_kpi()
                elif widget.widget_type == 'compliance':
                    widget._compute_compliance_kpi()
                elif widget.widget_type == 'payroll':
                    widget._compute_payroll_kpi()
                else:
                    widget._compute_executive_kpi()
            except Exception as e:
                _logger.warning(f"Error computing KPI for widget {widget.name}: {e}")
                widget.kpi_value = '--'
                widget.kpi_label = widget.widget_type.replace('_', ' ').title()
                widget.kpi_trend = 0.0
                widget.kpi_trend_direction = 'stable'

    def _compute_cost_center_kpi(self):
        """Compute cost center KPI."""
        self.ensure_one()
        CostCenter = self.env['employee.cost.center']
        
        total_cost = sum(CostCenter.search([]).mapped('total_cost'))
        total_revenue = sum(CostCenter.search([]).mapped('revenue'))
        margin = total_revenue - total_cost if total_revenue else 0
        
        self.kpi_value = f"AED {margin:,.0f}"
        self.kpi_label = 'Gross Margin'
        self.kpi_trend = 5.2  # Placeholder - would calculate from historical data
        self.kpi_trend_direction = 'up' if self.kpi_trend > 0 else ('down' if self.kpi_trend < 0 else 'stable')

    def _compute_recruitment_kpi(self):
        """Compute recruitment KPI."""
        self.ensure_one()
        Candidate = self.env['tazweed.candidate']
        Placement = self.env['tazweed.placement']
        
        try:
            total_candidates = Candidate.search_count([])
            total_placements = Placement.search_count([('state', '=', 'active')])
            conversion = (total_placements / total_candidates * 100) if total_candidates else 0
            
            self.kpi_value = f"{conversion:.1f}%"
            self.kpi_label = 'Conversion Rate'
            self.kpi_trend = 2.3
            self.kpi_trend_direction = 'up'
        except Exception:
            self.kpi_value = '--'
            self.kpi_label = 'Conversion Rate'
            self.kpi_trend = 0.0
            self.kpi_trend_direction = 'stable'

    def _compute_compliance_kpi(self):
        """Compute compliance KPI."""
        self.ensure_one()
        Employee = self.env['hr.employee']
        
        try:
            employees = Employee.search([])
            today = date.today()
            expiring_count = 0
            
            for emp in employees:
                # Check various document expiry fields
                if emp.visa_expiry and emp.visa_expiry <= today + timedelta(days=30):
                    expiring_count += 1
                elif emp.passport_expiry and emp.passport_expiry <= today + timedelta(days=30):
                    expiring_count += 1
                elif emp.emirates_id_expiry and emp.emirates_id_expiry <= today + timedelta(days=30):
                    expiring_count += 1
            
            total = len(employees)
            compliance_rate = ((total - expiring_count) / total * 100) if total else 100
            
            self.kpi_value = f"{compliance_rate:.1f}%"
            self.kpi_label = 'Compliance Rate'
            self.kpi_trend = -1.5 if expiring_count > 0 else 0.5
            self.kpi_trend_direction = 'down' if expiring_count > 0 else 'up'
        except Exception:
            self.kpi_value = '--'
            self.kpi_label = 'Compliance Rate'
            self.kpi_trend = 0.0
            self.kpi_trend_direction = 'stable'

    def _compute_payroll_kpi(self):
        """Compute payroll KPI."""
        self.ensure_one()
        CostCenter = self.env['employee.cost.center']
        
        try:
            records = CostCenter.search([])
            total_salary = sum(records.mapped('salary_cost'))
            employee_count = len(records.mapped('employee_id'))
            avg_salary = total_salary / employee_count if employee_count else 0
            
            self.kpi_value = f"AED {avg_salary:,.0f}"
            self.kpi_label = 'Avg Salary'
            self.kpi_trend = 3.1
            self.kpi_trend_direction = 'up'
        except Exception:
            self.kpi_value = '--'
            self.kpi_label = 'Avg Salary'
            self.kpi_trend = 0.0
            self.kpi_trend_direction = 'stable'

    def _compute_executive_kpi(self):
        """Compute executive summary KPI."""
        self.ensure_one()
        CostCenter = self.env['employee.cost.center']
        
        try:
            records = CostCenter.search([])
            total_revenue = sum(records.mapped('revenue'))
            
            self.kpi_value = f"AED {total_revenue:,.0f}"
            self.kpi_label = 'Total Revenue'
            self.kpi_trend = 8.5
            self.kpi_trend_direction = 'up'
        except Exception:
            self.kpi_value = '--'
            self.kpi_label = 'Total Revenue'
            self.kpi_trend = 0.0
            self.kpi_trend_direction = 'stable'

    @api.model
    def get_user_widgets(self):
        """Get widgets visible to current user."""
        user = self.env.user
        domain = [
            '|',
            ('user_ids', '=', False),
            ('user_ids', 'in', [user.id])
        ]
        widgets = self.search(domain, order='sequence')
        
        return [{
            'id': w.id,
            'name': w.name,
            'type': w.widget_type,
            'value': w.kpi_value,
            'label': w.kpi_label,
            'trend': w.kpi_trend,
            'trend_direction': w.kpi_trend_direction,
            'color': w.color,
            'icon': w.icon,
        } for w in widgets]

    @api.model
    def create_default_widgets(self):
        """Create default widgets if none exist."""
        if not self.search_count([]):
            defaults = [
                {'name': 'Gross Margin', 'widget_type': 'cost_center', 'color': 'primary', 'icon': 'fa-money-bill', 'sequence': 1},
                {'name': 'Conversion Rate', 'widget_type': 'recruitment', 'color': 'success', 'icon': 'fa-users', 'sequence': 2},
                {'name': 'Compliance Rate', 'widget_type': 'compliance', 'color': 'warning', 'icon': 'fa-shield-alt', 'sequence': 3},
                {'name': 'Avg Salary', 'widget_type': 'payroll', 'color': 'info', 'icon': 'fa-wallet', 'sequence': 4},
                {'name': 'Total Revenue', 'widget_type': 'executive', 'color': 'secondary', 'icon': 'fa-chart-line', 'sequence': 5},
            ]
            for vals in defaults:
                self.create(vals)
        return True


class DashboardNotification(models.Model):
    """Dashboard Notification for alerts and updates."""
    _name = 'analytics.dashboard.notification'
    _description = 'Dashboard Notification'
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message')
    notification_type = fields.Selection([
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('danger', 'Alert'),
        ('success', 'Success'),
    ], string='Type', default='info')
    
    category = fields.Selection([
        ('compliance', 'Compliance'),
        ('payroll', 'Payroll'),
        ('recruitment', 'Recruitment'),
        ('cost_center', 'Cost Center'),
        ('system', 'System'),
    ], string='Category', default='system')
    
    is_read = fields.Boolean(string='Read', default=False)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    
    # Related record
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related Record ID')
    
    @api.model
    def get_unread_count(self):
        """Get count of unread notifications for current user."""
        return self.search_count([
            ('user_id', '=', self.env.user.id),
            ('is_read', '=', False)
        ])

    @api.model
    def get_recent_notifications(self, limit=10):
        """Get recent notifications for current user."""
        notifications = self.search([
            ('user_id', '=', self.env.user.id)
        ], limit=limit, order='create_date desc')
        
        return [{
            'id': n.id,
            'title': n.name,
            'message': n.message,
            'type': n.notification_type,
            'category': n.category,
            'is_read': n.is_read,
            'date': n.create_date.strftime('%Y-%m-%d %H:%M') if n.create_date else '',
        } for n in notifications]

    def action_mark_read(self):
        """Mark notification as read."""
        self.write({'is_read': True})

    @api.model
    def create_notification(self, title, message, notification_type='info', category='system', user_id=None, res_model=None, res_id=None):
        """Create a new notification."""
        vals = {
            'name': title,
            'message': message,
            'notification_type': notification_type,
            'category': category,
            'user_id': user_id or self.env.user.id,
        }
        if res_model:
            vals['res_model'] = res_model
        if res_id:
            vals['res_id'] = res_id
        
        return self.create(vals)
