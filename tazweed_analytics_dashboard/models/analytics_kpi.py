# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AnalyticsKPI(models.Model):
    _name = 'analytics.kpi'
    _description = 'Analytics KPI'
    _order = 'sequence, name'

    name = fields.Char(string='KPI Name', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    category = fields.Selection([
        ('workforce', 'Workforce'),
        ('payroll', 'Payroll'),
        ('recruitment', 'Recruitment'),
        ('performance', 'Performance'),
        ('compliance', 'Compliance'),
        ('financial', 'Financial'),
    ], string='Category', required=True)
    
    description = fields.Text(string='Description')
    
    # Value Configuration
    value_type = fields.Selection([
        ('count', 'Count'),
        ('sum', 'Sum'),
        ('average', 'Average'),
        ('percentage', 'Percentage'),
        ('ratio', 'Ratio'),
        ('currency', 'Currency'),
        ('custom', 'Custom Formula'),
    ], string='Value Type', required=True, default='count')
    
    model_id = fields.Many2one('ir.model', string='Model')
    domain = fields.Char(string='Domain', default='[]')
    field_name = fields.Char(string='Field Name')
    
    # Display
    display_format = fields.Selection([
        ('number', 'Number'),
        ('currency', 'Currency (AED)'),
        ('percentage', 'Percentage'),
        ('decimal', 'Decimal'),
    ], string='Display Format', default='number')
    
    decimal_places = fields.Integer(string='Decimal Places', default=0)
    prefix = fields.Char(string='Prefix')
    suffix = fields.Char(string='Suffix')
    
    icon = fields.Char(string='Icon', default='fa-chart-line')
    color = fields.Char(string='Color', default='#2196F3')
    
    # Target & Thresholds
    has_target = fields.Boolean(string='Has Target')
    target_value = fields.Float(string='Target Value')
    target_type = fields.Selection([
        ('higher', 'Higher is Better'),
        ('lower', 'Lower is Better'),
        ('exact', 'Exact Match'),
    ], string='Target Type', default='higher')
    
    warning_threshold = fields.Float(string='Warning Threshold (%)', default=80)
    danger_threshold = fields.Float(string='Danger Threshold (%)', default=60)
    
    # Trend
    show_trend = fields.Boolean(string='Show Trend', default=True)
    trend_period = fields.Selection([
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly'),
    ], string='Trend Period', default='month')
    
    # Computed Values
    current_value = fields.Float(string='Current Value', compute='_compute_values')
    previous_value = fields.Float(string='Previous Value', compute='_compute_values')
    trend_value = fields.Float(string='Trend (%)', compute='_compute_values')
    status = fields.Selection([
        ('success', 'On Track'),
        ('warning', 'Warning'),
        ('danger', 'Critical'),
    ], string='Status', compute='_compute_values')

    @api.depends('code', 'model_id', 'domain', 'field_name')
    def _compute_values(self):
        for kpi in self:
            kpi.current_value = kpi._calculate_value()
            kpi.previous_value = kpi._calculate_value(previous=True)
            
            # Calculate trend
            if kpi.previous_value:
                kpi.trend_value = ((kpi.current_value - kpi.previous_value) / kpi.previous_value) * 100
            else:
                kpi.trend_value = 0
            
            # Calculate status
            kpi.status = kpi._calculate_status()

    def _calculate_value(self, previous=False):
        """Calculate KPI value based on configuration."""
        self.ensure_one()
        
        # Handle predefined KPIs
        method_name = f'_calc_{self.code}'
        if hasattr(self, method_name):
            return getattr(self, method_name)(previous)
        
        # Handle model-based KPIs
        if not self.model_id:
            return 0
        
        Model = self.env[self.model_id.model].sudo()
        domain = eval(self.domain or '[]')
        
        # Adjust domain for previous period
        if previous:
            domain = self._adjust_domain_for_previous(domain)
        
        if self.value_type == 'count':
            return Model.search_count(domain)
        elif self.value_type == 'sum' and self.field_name:
            records = Model.search(domain)
            return sum(records.mapped(self.field_name))
        elif self.value_type == 'average' and self.field_name:
            records = Model.search(domain)
            values = records.mapped(self.field_name)
            return sum(values) / len(values) if values else 0
        
        return 0

    def _adjust_domain_for_previous(self, domain):
        """Adjust domain to get previous period data."""
        # This would need to be customized based on the KPI
        return domain

    def _calculate_status(self):
        """Calculate KPI status based on target and thresholds."""
        self.ensure_one()
        
        if not self.has_target or not self.target_value:
            return 'success'
        
        if self.target_type == 'higher':
            percentage = (self.current_value / self.target_value) * 100 if self.target_value else 0
        elif self.target_type == 'lower':
            percentage = (self.target_value / self.current_value) * 100 if self.current_value else 100
        else:
            diff = abs(self.current_value - self.target_value)
            percentage = 100 - (diff / self.target_value * 100) if self.target_value else 0
        
        if percentage >= self.warning_threshold:
            return 'success'
        elif percentage >= self.danger_threshold:
            return 'warning'
        else:
            return 'danger'

    def get_kpi_data(self):
        """Get KPI data for dashboard display."""
        self.ensure_one()
        
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'category': self.category,
            'value': self.current_value,
            'previous_value': self.previous_value,
            'trend': self.trend_value,
            'status': self.status,
            'target': self.target_value if self.has_target else None,
            'display': self._format_value(self.current_value),
            'icon': self.icon,
            'color': self.color,
        }

    def _format_value(self, value):
        """Format value for display."""
        self.ensure_one()
        
        if self.display_format == 'currency':
            formatted = f"{value:,.{self.decimal_places}f}"
            return f"AED {formatted}"
        elif self.display_format == 'percentage':
            return f"{value:.{self.decimal_places}f}%"
        elif self.display_format == 'decimal':
            return f"{value:.{self.decimal_places}f}"
        else:
            return f"{int(value):,}"

    # Predefined KPI Calculations
    def _calc_total_employees(self, previous=False):
        """Calculate total active employees."""
        return self.env['hr.employee'].sudo().search_count([('active', '=', True)])

    def _calc_turnover_rate(self, previous=False):
        """Calculate employee turnover rate."""
        Employee = self.env['hr.employee'].sudo()
        today = fields.Date.today()
        
        if previous:
            end_date = today.replace(day=1) - timedelta(days=1)
            start_date = end_date.replace(day=1)
        else:
            start_date = today.replace(day=1)
            end_date = today
        
        departed = Employee.search_count([
            ('departure_date', '>=', start_date),
            ('departure_date', '<=', end_date)
        ])
        
        total = Employee.search_count([
            ('create_date', '<=', end_date)
        ]) or 1
        
        return (departed / total) * 100

    def _calc_avg_tenure(self, previous=False):
        """Calculate average employee tenure in years."""
        Employee = self.env['hr.employee'].sudo()
        employees = Employee.search([('active', '=', True)])
        
        if not employees:
            return 0
        
        today = fields.Date.today()
        total_days = 0
        
        for emp in employees:
            if emp.create_date:
                days = (today - emp.create_date.date()).days
                total_days += days
        
        avg_days = total_days / len(employees)
        return avg_days / 365  # Convert to years

    def _calc_open_positions(self, previous=False):
        """Calculate open positions."""
        # Would need job requisition model
        return 0

    def _calc_time_to_hire(self, previous=False):
        """Calculate average time to hire in days."""
        # Would calculate from placement records
        return 21  # Placeholder

    def _calc_cost_per_hire(self, previous=False):
        """Calculate average cost per hire."""
        return 5000  # Placeholder

    def _calc_payroll_cost(self, previous=False):
        """Calculate total payroll cost."""
        # Would sum from payslips
        return 500000  # Placeholder

    def _calc_revenue_per_employee(self, previous=False):
        """Calculate revenue per employee."""
        # Would calculate from invoices and employee count
        return 25000  # Placeholder

    def _calc_emiratization_rate(self, previous=False):
        """Calculate Emiratization percentage."""
        Employee = self.env['hr.employee'].sudo()
        total = Employee.search_count([('active', '=', True)]) or 1
        # Would filter by nationality
        uae_nationals = 0
        return (uae_nationals / total) * 100

    def _calc_leave_utilization(self, previous=False):
        """Calculate leave utilization rate."""
        return 75  # Placeholder percentage

    def _calc_training_hours(self, previous=False):
        """Calculate average training hours per employee."""
        return 8  # Placeholder

    def _calc_placement_fill_rate(self, previous=False):
        """Calculate placement fill rate."""
        return 85  # Placeholder percentage
