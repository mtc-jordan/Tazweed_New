from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class PayrollAnalytics(models.Model):
    """Payroll analytics and metrics tracking."""
    
    _name = 'tazweed.payroll.analytics'
    _description = 'Payroll Analytics'
    _rec_name = 'analytics_name'
    
    analytics_name = fields.Char(
        string='Analytics Name',
        required=True,
        help='Name of analytics record'
    )
    
    # Period
    period_start = fields.Date(
        string='Period Start',
        required=True,
        help='Analysis period start'
    )
    
    period_end = fields.Date(
        string='Period End',
        required=True,
        help='Analysis period end'
    )
    
    # Payroll Metrics
    total_employees = fields.Integer(
        string='Total Employees',
        compute='_compute_payroll_metrics',
        store=True,
        help='Total employees in period'
    )
    
    total_payroll = fields.Float(
        string='Total Payroll',
        compute='_compute_payroll_metrics',
        store=True,
        help='Total payroll amount'
    )
    
    average_salary = fields.Float(
        string='Average Salary',
        compute='_compute_payroll_metrics',
        store=True,
        help='Average salary per employee'
    )
    
    total_deductions = fields.Float(
        string='Total Deductions',
        compute='_compute_payroll_metrics',
        store=True,
        help='Total deductions'
    )
    
    total_net_salary = fields.Float(
        string='Total Net Salary',
        compute='_compute_payroll_metrics',
        store=True,
        help='Total net salary'
    )
    
    total_employer_contribution = fields.Float(
        string='Total Employer Contribution',
        compute='_compute_payroll_metrics',
        store=True,
        help='Total employer contribution'
    )
    
    # Salary Distribution
    salary_min = fields.Float(
        string='Minimum Salary',
        compute='_compute_salary_distribution',
        store=True,
        help='Minimum salary'
    )
    
    salary_max = fields.Float(
        string='Maximum Salary',
        compute='_compute_salary_distribution',
        store=True,
        help='Maximum salary'
    )
    
    salary_median = fields.Float(
        string='Median Salary',
        compute='_compute_salary_distribution',
        store=True,
        help='Median salary'
    )
    
    salary_std_dev = fields.Float(
        string='Salary Std Dev',
        compute='_compute_salary_distribution',
        store=True,
        help='Salary standard deviation'
    )
    
    # Deduction Analysis
    leave_deduction_total = fields.Float(
        string='Leave Deduction Total',
        help='Total leave deductions'
    )
    
    overtime_total = fields.Float(
        string='Overtime Total',
        help='Total overtime payments'
    )
    
    performance_bonus_total = fields.Float(
        string='Performance Bonus Total',
        help='Total performance bonuses'
    )
    
    tax_deduction_total = fields.Float(
        string='Tax Deduction Total',
        help='Total tax deductions'
    )
    
    # Cost Analysis
    cost_per_employee = fields.Float(
        string='Cost Per Employee',
        compute='_compute_cost_analysis',
        store=True,
        help='Average cost per employee'
    )
    
    payroll_percentage_of_revenue = fields.Float(
        string='Payroll % of Revenue',
        help='Payroll as percentage of revenue'
    )
    
    # Bank Transfer Analytics
    total_transfers = fields.Integer(
        string='Total Transfers',
        help='Total bank transfers'
    )
    
    successful_transfers = fields.Integer(
        string='Successful Transfers',
        help='Successful transfers'
    )
    
    failed_transfers = fields.Integer(
        string='Failed Transfers',
        help='Failed transfers'
    )
    
    transfer_success_rate = fields.Float(
        string='Transfer Success Rate %',
        help='Transfer success rate'
    )
    
    # Trends
    payroll_trend = fields.Selection(
        [('up', 'Up'), ('down', 'Down'), ('stable', 'Stable')],
        string='Payroll Trend',
        help='Payroll trend'
    )
    
    salary_trend = fields.Selection(
        [('up', 'Up'), ('down', 'Down'), ('stable', 'Stable')],
        string='Salary Trend',
        help='Salary trend'
    )
    
    deduction_trend = fields.Selection(
        [('up', 'Up'), ('down', 'Down'), ('stable', 'Stable')],
        string='Deduction Trend',
        help='Deduction trend'
    )
    
    @api.depends('period_start', 'period_end')
    def _compute_payroll_metrics(self):
        """Compute payroll metrics using hr.payslip if available."""
        for record in self:
            # Try to use hr.payslip from hr_payroll module
            try:
                Payslip = self.env['hr.payslip']
                payslips = Payslip.search([
                    ('date_from', '>=', record.period_start),
                    ('date_to', '<=', record.period_end),
                    ('state', '=', 'done'),
                ])
                
                record.total_employees = len(set(payslips.mapped('employee_id')))
                
                # Calculate totals from payslip lines
                total_gross = 0
                total_deductions = 0
                total_net = 0
                
                for payslip in payslips:
                    for line in payslip.line_ids:
                        if line.category_id.code == 'GROSS':
                            total_gross += line.total
                        elif line.category_id.code == 'DED':
                            total_deductions += line.total
                        elif line.category_id.code == 'NET':
                            total_net += line.total
                
                record.total_payroll = total_gross
                record.total_deductions = abs(total_deductions)
                record.total_net_salary = total_net
                record.total_employer_contribution = 0
                
                if record.total_employees > 0:
                    record.average_salary = record.total_payroll / record.total_employees
                else:
                    record.average_salary = 0
                    
            except Exception:
                # Fallback to employee count if payroll not available
                employees = self.env['hr.employee'].search([
                    ('active', '=', True),
                ])
                record.total_employees = len(employees)
                record.total_payroll = 0
                record.total_deductions = 0
                record.total_net_salary = 0
                record.total_employer_contribution = 0
                record.average_salary = 0
    
    @api.depends('period_start', 'period_end')
    def _compute_salary_distribution(self):
        """Compute salary distribution metrics."""
        for record in self:
            try:
                contracts = self.env['hr.contract'].search([
                    ('state', '=', 'open'),
                ])
                
                salaries = contracts.mapped('wage')
                
                if salaries:
                    record.salary_min = min(salaries)
                    record.salary_max = max(salaries)
                    record.salary_median = sorted(salaries)[len(salaries) // 2]
                    
                    # Calculate standard deviation
                    mean = sum(salaries) / len(salaries)
                    variance = sum((x - mean) ** 2 for x in salaries) / len(salaries)
                    record.salary_std_dev = variance ** 0.5
                else:
                    record.salary_min = 0
                    record.salary_max = 0
                    record.salary_median = 0
                    record.salary_std_dev = 0
            except Exception:
                record.salary_min = 0
                record.salary_max = 0
                record.salary_median = 0
                record.salary_std_dev = 0
    
    @api.depends('total_payroll', 'total_employees')
    def _compute_cost_analysis(self):
        """Compute cost analysis."""
        for record in self:
            if record.total_employees > 0:
                record.cost_per_employee = record.total_payroll / record.total_employees
            else:
                record.cost_per_employee = 0
    
    def action_refresh_analytics(self):
        """Refresh analytics data."""
        self._compute_payroll_metrics()
        self._compute_salary_distribution()
        self._compute_cost_analysis()
        return True


class PayrollAnalyticsLine(models.Model):
    """Payroll analytics detailed breakdown by department."""
    
    _name = 'tazweed.payroll.analytics.line'
    _description = 'Payroll Analytics Line'
    
    analytics_id = fields.Many2one(
        'tazweed.payroll.analytics',
        string='Analytics',
        required=True,
        ondelete='cascade'
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=True
    )
    
    employee_count = fields.Integer(
        string='Employee Count',
        help='Number of employees'
    )
    
    total_salary = fields.Float(
        string='Total Salary',
        help='Total salary for department'
    )
    
    average_salary = fields.Float(
        string='Average Salary',
        help='Average salary per employee'
    )
    
    total_deductions = fields.Float(
        string='Total Deductions',
        help='Total deductions'
    )
    
    total_net = fields.Float(
        string='Total Net',
        help='Total net salary'
    )
    
    percentage_of_total = fields.Float(
        string='% of Total',
        help='Percentage of total payroll'
    )
