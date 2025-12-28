from odoo import models, fields, api
from datetime import datetime


class AnalyticsReport(models.Model):
    """Advanced analytics reports."""
    
    _name = 'tazweed.analytics.report'
    _description = 'Analytics Report'
    _rec_name = 'report_name'
    
    report_name = fields.Char(
        string='Report Name',
        required=True
    )
    
    report_type = fields.Selection(
        [
            ('payroll_summary', 'Payroll Summary'),
            ('compliance_report', 'Compliance Report'),
            ('performance_report', 'Performance Report'),
            ('employee_report', 'Employee Report'),
            ('cost_analysis', 'Cost Analysis'),
            ('salary_distribution', 'Salary Distribution'),
            ('custom', 'Custom Report'),
        ],
        string='Report Type',
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
    
    # Filters
    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Filter by departments'
    )
    
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Filter by employees'
    )
    
    # Report Settings
    include_charts = fields.Boolean(
        string='Include Charts',
        default=True
    )
    
    include_summary = fields.Boolean(
        string='Include Summary',
        default=True
    )
    
    include_details = fields.Boolean(
        string='Include Details',
        default=True
    )
    
    # Export Options
    export_format = fields.Selection(
        [('pdf', 'PDF'), ('excel', 'Excel'), ('csv', 'CSV')],
        string='Export Format',
        default='pdf'
    )
    
    # Status
    state = fields.Selection(
        [('draft', 'Draft'), ('generated', 'Generated'), ('exported', 'Exported')],
        string='Status',
        default='draft'
    )
    
    # Report Data
    report_data = fields.Text(
        string='Report Data',
        help='Generated report data'
    )
    
    # File
    report_file = fields.Binary(
        string='Report File',
        attachment=True
    )
    
    report_filename = fields.Char(
        string='Report Filename'
    )
    
    # Metadata
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True
    )
    
    generated_date = fields.Datetime(
        string='Generated Date',
        readonly=True
    )
    
    def action_generate_report(self):
        """Generate report."""
        for record in self:
            # Generate report based on type
            if record.report_type == 'payroll_summary':
                record._generate_payroll_summary()
            elif record.report_type == 'compliance_report':
                record._generate_compliance_report()
            elif record.report_type == 'performance_report':
                record._generate_performance_report()
            elif record.report_type == 'employee_report':
                record._generate_employee_report()
            elif record.report_type == 'cost_analysis':
                record._generate_cost_analysis()
            elif record.report_type == 'salary_distribution':
                record._generate_salary_distribution()
            
            record.state = 'generated'
            record.generated_date = datetime.now()
    
    def _generate_payroll_summary(self):
        """Generate payroll summary report."""
        payroll_analytics = self.env['tazweed.payroll.analytics'].search([
            ('period_start', '=', self.period_start),
            ('period_end', '=', self.period_end),
        ], limit=1)
        
        if not payroll_analytics:
            payroll_analytics = self.env['tazweed.payroll.analytics'].create({
                'analytics_name': f'Analytics {self.period_start} to {self.period_end}',
                'period_start': self.period_start,
                'period_end': self.period_end,
            })
        
        report_data = {
            'title': 'Payroll Summary Report',
            'period': f'{self.period_start} to {self.period_end}',
            'total_employees': payroll_analytics.total_employees,
            'total_payroll': payroll_analytics.total_payroll,
            'average_salary': payroll_analytics.average_salary,
            'total_deductions': payroll_analytics.total_deductions,
            'total_net_salary': payroll_analytics.total_net_salary,
            'total_employer_contribution': payroll_analytics.total_employer_contribution,
            'salary_min': payroll_analytics.salary_min,
            'salary_max': payroll_analytics.salary_max,
            'salary_median': payroll_analytics.salary_median,
            'leave_deduction_total': payroll_analytics.leave_deduction_total,
            'overtime_total': payroll_analytics.overtime_total,
            'performance_bonus_total': payroll_analytics.performance_bonus_total,
        }
        
        self.report_data = str(report_data)
    
    def _generate_compliance_report(self):
        """Generate compliance report."""
        compliance_analytics = self.env['tazweed.compliance.analytics'].search([
            ('period_start', '=', self.period_start),
            ('period_end', '=', self.period_end),
        ], limit=1)
        
        if not compliance_analytics:
            compliance_analytics = self.env['tazweed.compliance.analytics'].create({
                'analytics_name': f'Compliance Analytics {self.period_start} to {self.period_end}',
                'period_start': self.period_start,
                'period_end': self.period_end,
            })
        
        report_data = {
            'title': 'Compliance Report',
            'period': f'{self.period_start} to {self.period_end}',
            'emiratization_percentage': compliance_analytics.emiratization_percentage,
            'emiratization_compliant': compliance_analytics.emiratization_compliant,
            'wps_compliance_rate': compliance_analytics.wps_compliance_rate,
            'mohre_compliance_rate': compliance_analytics.mohre_compliance_rate,
            'minimum_wage_compliance_rate': compliance_analytics.minimum_wage_compliance_rate,
            'leave_compliance_rate': compliance_analytics.leave_compliance_rate,
            'overall_compliance_score': compliance_analytics.overall_compliance_score,
            'compliance_status': compliance_analytics.compliance_status,
            'high_risk_count': compliance_analytics.high_risk_count,
            'medium_risk_count': compliance_analytics.medium_risk_count,
            'low_risk_count': compliance_analytics.low_risk_count,
        }
        
        self.report_data = str(report_data)
    
    def _generate_performance_report(self):
        """Generate performance report."""
        performance_analytics = self.env['tazweed.performance.analytics'].search([
            ('period_start', '=', self.period_start),
            ('period_end', '=', self.period_end),
        ], limit=1)
        
        if not performance_analytics:
            performance_analytics = self.env['tazweed.performance.analytics'].create({
                'analytics_name': f'Performance Analytics {self.period_start} to {self.period_end}',
                'period_start': self.period_start,
                'period_end': self.period_end,
            })
        
        report_data = {
            'title': 'Performance Report',
            'period': f'{self.period_start} to {self.period_end}',
            'total_employees': performance_analytics.total_employees,
            'average_rating': performance_analytics.average_rating,
            'excellent_count': performance_analytics.excellent_count,
            'good_count': performance_analytics.good_count,
            'average_count': performance_analytics.average_count,
            'poor_count': performance_analytics.poor_count,
            'goal_achievement_rate': performance_analytics.goal_achievement_rate,
            'kpi_achievement_rate': performance_analytics.kpi_achievement_rate,
            'performance_trend': performance_analytics.performance_trend,
        }
        
        self.report_data = str(report_data)
    
    def _generate_employee_report(self):
        """Generate employee report."""
        employee_analytics = self.env['tazweed.employee.analytics'].search([
            ('period_start', '=', self.period_start),
            ('period_end', '=', self.period_end),
        ], limit=1)
        
        if not employee_analytics:
            employee_analytics = self.env['tazweed.employee.analytics'].create({
                'analytics_name': f'Employee Analytics {self.period_start} to {self.period_end}',
                'period_start': self.period_start,
                'period_end': self.period_end,
            })
        
        report_data = {
            'title': 'Employee Report',
            'period': f'{self.period_start} to {self.period_end}',
            'total_headcount': employee_analytics.total_headcount,
            'new_hires': employee_analytics.new_hires,
            'separations': employee_analytics.separations,
            'turnover_rate': employee_analytics.turnover_rate,
            'average_tenure_years': employee_analytics.average_tenure_years,
            'average_attendance_rate': employee_analytics.average_attendance_rate,
            'average_leave_balance': employee_analytics.average_leave_balance,
            'average_salary': employee_analytics.average_salary,
            'salary_min': employee_analytics.salary_min,
            'salary_max': employee_analytics.salary_max,
        }
        
        self.report_data = str(report_data)
    
    def _generate_cost_analysis(self):
        """Generate cost analysis report."""
        payroll_analytics = self.env['tazweed.payroll.analytics'].search([
            ('period_start', '=', self.period_start),
            ('period_end', '=', self.period_end),
        ], limit=1)
        
        if not payroll_analytics:
            payroll_analytics = self.env['tazweed.payroll.analytics'].create({
                'analytics_name': f'Analytics {self.period_start} to {self.period_end}',
                'period_start': self.period_start,
                'period_end': self.period_end,
            })
        
        report_data = {
            'title': 'Cost Analysis Report',
            'period': f'{self.period_start} to {self.period_end}',
            'total_payroll': payroll_analytics.total_payroll,
            'cost_per_employee': payroll_analytics.cost_per_employee,
            'payroll_percentage_of_revenue': payroll_analytics.payroll_percentage_of_revenue,
            'total_employer_contribution': payroll_analytics.total_employer_contribution,
            'average_salary': payroll_analytics.average_salary,
        }
        
        self.report_data = str(report_data)
    
    def _generate_salary_distribution(self):
        """Generate salary distribution report."""
        payroll_analytics = self.env['tazweed.payroll.analytics'].search([
            ('period_start', '=', self.period_start),
            ('period_end', '=', self.period_end),
        ], limit=1)
        
        if not payroll_analytics:
            payroll_analytics = self.env['tazweed.payroll.analytics'].create({
                'analytics_name': f'Analytics {self.period_start} to {self.period_end}',
                'period_start': self.period_start,
                'period_end': self.period_end,
            })
        
        report_data = {
            'title': 'Salary Distribution Report',
            'period': f'{self.period_start} to {self.period_end}',
            'average_salary': payroll_analytics.average_salary,
            'salary_min': payroll_analytics.salary_min,
            'salary_max': payroll_analytics.salary_max,
            'salary_median': payroll_analytics.salary_median,
            'salary_std_dev': payroll_analytics.salary_std_dev,
            'salary_range': payroll_analytics.salary_max - payroll_analytics.salary_min,
        }
        
        self.report_data = str(report_data)
    
    def action_export_report(self):
        """Export report."""
        for record in self:
            if record.export_format == 'pdf':
                record._export_pdf()
            elif record.export_format == 'excel':
                record._export_excel()
            elif record.export_format == 'csv':
                record._export_csv()
            
            record.state = 'exported'
    
    def _export_pdf(self):
        """Export report to PDF."""
        # Implementation for PDF export
        self.report_filename = f'{self.report_name}_{self.period_start}_{self.period_end}.pdf'
    
    def _export_excel(self):
        """Export report to Excel."""
        # Implementation for Excel export
        self.report_filename = f'{self.report_name}_{self.period_start}_{self.period_end}.xlsx'
    
    def _export_csv(self):
        """Export report to CSV."""
        # Implementation for CSV export
        self.report_filename = f'{self.report_name}_{self.period_start}_{self.period_end}.csv'
