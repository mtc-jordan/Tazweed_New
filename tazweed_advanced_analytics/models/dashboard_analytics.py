from odoo import models, fields, api
from datetime import datetime, timedelta


class DashboardAnalytics(models.Model):
    """Dashboard analytics for unified view."""
    
    _name = 'tazweed.dashboard.analytics'
    _description = 'Dashboard Analytics'
    _rec_name = 'dashboard_name'
    
    dashboard_name = fields.Char(
        string='Dashboard Name',
        required=True
    )
    
    dashboard_type = fields.Selection(
        [
            ('executive', 'Executive Dashboard'),
            ('payroll', 'Payroll Dashboard'),
            ('compliance', 'Compliance Dashboard'),
            ('performance', 'Performance Dashboard'),
            ('employee', 'Employee Dashboard'),
            ('hr_manager', 'HR Manager Dashboard'),
        ],
        string='Dashboard Type',
        required=True
    )
    
    # Period
    period_start = fields.Date(
        string='Period Start',
        required=True
    )
    
    period_end = fields.Date(
        string='Period End',
        required=True
    )
    
    # Refresh settings
    auto_refresh = fields.Boolean(
        string='Auto Refresh',
        default=True,
        help='Auto refresh dashboard'
    )
    
    refresh_interval = fields.Integer(
        string='Refresh Interval (seconds)',
        default=300,
        help='Refresh interval in seconds'
    )
    
    # Last update
    last_updated = fields.Datetime(
        string='Last Updated',
        compute='_compute_last_updated',
        help='Last update time'
    )
    
    # Executive Dashboard Metrics
    exec_total_employees = fields.Integer(
        string='Total Employees',
        compute='_compute_executive_metrics'
    )
    
    exec_total_payroll = fields.Float(
        string='Total Payroll',
        compute='_compute_executive_metrics'
    )
    
    exec_compliance_score = fields.Float(
        string='Compliance Score',
        compute='_compute_executive_metrics'
    )
    
    exec_performance_rating = fields.Float(
        string='Performance Rating',
        compute='_compute_executive_metrics'
    )
    
    exec_turnover_rate = fields.Float(
        string='Turnover Rate',
        compute='_compute_executive_metrics'
    )
    
    # Payroll Dashboard Metrics
    payroll_total = fields.Float(
        string='Total Payroll',
        compute='_compute_payroll_metrics'
    )
    
    payroll_average_salary = fields.Float(
        string='Average Salary',
        compute='_compute_payroll_metrics'
    )
    
    payroll_total_deductions = fields.Float(
        string='Total Deductions',
        compute='_compute_payroll_metrics'
    )
    
    payroll_total_bonuses = fields.Float(
        string='Total Bonuses',
        compute='_compute_payroll_metrics'
    )
    
    payroll_transfer_success_rate = fields.Float(
        string='Transfer Success Rate',
        compute='_compute_payroll_metrics'
    )
    
    # Compliance Dashboard Metrics
    compliance_emiratization = fields.Float(
        string='Emiratization %',
        compute='_compute_compliance_metrics'
    )
    
    compliance_wps_rate = fields.Float(
        string='WPS Compliance %',
        compute='_compute_compliance_metrics'
    )
    
    compliance_mohre_rate = fields.Float(
        string='MOHRE Compliance %',
        compute='_compute_compliance_metrics'
    )
    
    compliance_overall_score = fields.Float(
        string='Overall Compliance Score',
        compute='_compute_compliance_metrics'
    )
    
    compliance_high_risks = fields.Integer(
        string='High Risk Items',
        compute='_compute_compliance_metrics'
    )
    
    # Performance Dashboard Metrics
    performance_avg_rating = fields.Float(
        string='Average Rating',
        compute='_compute_performance_metrics'
    )
    
    performance_goal_achievement = fields.Float(
        string='Goal Achievement %',
        compute='_compute_performance_metrics'
    )
    
    performance_kpi_achievement = fields.Float(
        string='KPI Achievement %',
        compute='_compute_performance_metrics'
    )
    
    performance_excellent_count = fields.Integer(
        string='Excellent Performers',
        compute='_compute_performance_metrics'
    )
    
    performance_poor_count = fields.Integer(
        string='Poor Performers',
        compute='_compute_performance_metrics'
    )
    
    # Employee Dashboard Metrics
    employee_headcount = fields.Integer(
        string='Headcount',
        compute='_compute_employee_metrics'
    )
    
    employee_avg_tenure = fields.Float(
        string='Average Tenure (Years)',
        compute='_compute_employee_metrics'
    )
    
    employee_avg_attendance = fields.Float(
        string='Average Attendance %',
        compute='_compute_employee_metrics'
    )
    
    employee_avg_leave_balance = fields.Float(
        string='Average Leave Balance',
        compute='_compute_employee_metrics'
    )
    
    employee_new_hires = fields.Integer(
        string='New Hires',
        compute='_compute_employee_metrics'
    )
    
    @api.depends('dashboard_type', 'period_start', 'period_end')
    def _compute_last_updated(self):
        """Compute last update time."""
        for record in self:
            record.last_updated = datetime.now()
    
    @api.depends('period_start', 'period_end')
    def _compute_executive_metrics(self):
        """Compute executive dashboard metrics."""
        for record in self:
            if record.dashboard_type != 'executive':
                continue
            
            # Get analytics records
            payroll_analytics = self.env['tazweed.payroll.analytics'].search([
                ('period_start', '=', record.period_start),
                ('period_end', '=', record.period_end),
            ], limit=1)
            
            compliance_analytics = self.env['tazweed.compliance.analytics'].search([
                ('period_start', '=', record.period_start),
                ('period_end', '=', record.period_end),
            ], limit=1)
            
            performance_analytics = self.env['tazweed.performance.analytics'].search([
                ('period_start', '=', record.period_start),
                ('period_end', '=', record.period_end),
            ], limit=1)
            
            employee_analytics = self.env['tazweed.employee.analytics'].search([
                ('period_start', '=', record.period_start),
                ('period_end', '=', record.period_end),
            ], limit=1)
            
            record.exec_total_employees = payroll_analytics.total_employees if payroll_analytics else 0
            record.exec_total_payroll = payroll_analytics.total_payroll if payroll_analytics else 0
            record.exec_compliance_score = compliance_analytics.overall_compliance_score if compliance_analytics else 0
            record.exec_performance_rating = performance_analytics.average_rating if performance_analytics else 0
            record.exec_turnover_rate = employee_analytics.turnover_rate if employee_analytics else 0
    
    @api.depends('period_start', 'period_end')
    def _compute_payroll_metrics(self):
        """Compute payroll dashboard metrics."""
        for record in self:
            if record.dashboard_type != 'payroll':
                continue
            
            payroll_analytics = self.env['tazweed.payroll.analytics'].search([
                ('period_start', '=', record.period_start),
                ('period_end', '=', record.period_end),
            ], limit=1)
            
            if payroll_analytics:
                record.payroll_total = payroll_analytics.total_payroll
                record.payroll_average_salary = payroll_analytics.average_salary
                record.payroll_total_deductions = payroll_analytics.total_deductions
                record.payroll_total_bonuses = payroll_analytics.performance_bonus_total
                record.payroll_transfer_success_rate = payroll_analytics.transfer_success_rate
    
    @api.depends('period_start', 'period_end')
    def _compute_compliance_metrics(self):
        """Compute compliance dashboard metrics."""
        for record in self:
            if record.dashboard_type != 'compliance':
                continue
            
            compliance_analytics = self.env['tazweed.compliance.analytics'].search([
                ('period_start', '=', record.period_start),
                ('period_end', '=', record.period_end),
            ], limit=1)
            
            if compliance_analytics:
                record.compliance_emiratization = compliance_analytics.emiratization_percentage
                record.compliance_wps_rate = compliance_analytics.wps_compliance_rate
                record.compliance_mohre_rate = compliance_analytics.mohre_compliance_rate
                record.compliance_overall_score = compliance_analytics.overall_compliance_score
                record.compliance_high_risks = compliance_analytics.high_risk_count
    
    @api.depends('period_start', 'period_end')
    def _compute_performance_metrics(self):
        """Compute performance dashboard metrics."""
        for record in self:
            if record.dashboard_type != 'performance':
                continue
            
            performance_analytics = self.env['tazweed.performance.analytics'].search([
                ('period_start', '=', record.period_start),
                ('period_end', '=', record.period_end),
            ], limit=1)
            
            if performance_analytics:
                record.performance_avg_rating = performance_analytics.average_rating
                record.performance_goal_achievement = performance_analytics.goal_achievement_rate
                record.performance_kpi_achievement = performance_analytics.kpi_achievement_rate
                record.performance_excellent_count = performance_analytics.excellent_count
                record.performance_poor_count = performance_analytics.poor_count
    
    @api.depends('period_start', 'period_end')
    def _compute_employee_metrics(self):
        """Compute employee dashboard metrics."""
        for record in self:
            if record.dashboard_type != 'employee':
                continue
            
            employee_analytics = self.env['tazweed.employee.analytics'].search([
                ('period_start', '=', record.period_start),
                ('period_end', '=', record.period_end),
            ], limit=1)
            
            if employee_analytics:
                record.employee_headcount = employee_analytics.total_headcount
                record.employee_avg_tenure = employee_analytics.average_tenure_years
                record.employee_avg_attendance = employee_analytics.average_attendance_rate
                record.employee_avg_leave_balance = employee_analytics.average_leave_balance
                record.employee_new_hires = employee_analytics.new_hires
