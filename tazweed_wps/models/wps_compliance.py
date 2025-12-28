# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date


class WPSCompliance(models.Model):
    """WPS Compliance Report"""
    _name = 'tazweed.wps.compliance'
    _description = 'WPS Compliance Report'
    _order = 'period_year desc, period_month desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        compute='_compute_name',
        store=True,
    )
    
    # Period
    period_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True)
    period_year = fields.Char(string='Year', required=True)
    
    # WPS File Link
    wps_file_id = fields.Many2one(
        'tazweed.wps.file',
        string='WPS File',
    )
    
    # Employee Metrics
    total_employees = fields.Integer(
        string='Total Employees',
        help='Total number of employees in the company',
    )
    employees_paid_wps = fields.Integer(
        string='Employees Paid via WPS',
        help='Number of employees paid through WPS',
    )
    employees_not_paid = fields.Integer(
        string='Employees Not Paid',
        help='Number of employees not paid through WPS',
    )
    employees_exempt = fields.Integer(
        string='Exempt Employees',
        help='Employees exempt from WPS (e.g., domestic workers)',
    )
    
    # Salary Metrics
    total_salary_due = fields.Float(
        string='Total Salary Due',
        digits=(16, 2),
    )
    total_salary_paid = fields.Float(
        string='Total Salary Paid',
        digits=(16, 2),
    )
    salary_variance = fields.Float(
        string='Salary Variance',
        compute='_compute_metrics',
        store=True,
        digits=(16, 2),
    )
    
    # Compliance Metrics
    compliance_rate = fields.Float(
        string='Compliance Rate %',
        compute='_compute_metrics',
        store=True,
    )
    is_compliant = fields.Boolean(
        string='Compliant',
        compute='_compute_metrics',
        store=True,
    )
    compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('partial', 'Partial Compliance'),
        ('non_compliant', 'Non-Compliant'),
    ], string='Compliance Status', compute='_compute_metrics', store=True)
    
    # Dates
    submission_deadline = fields.Date(
        string='Submission Deadline',
        compute='_compute_deadline',
        store=True,
    )
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_deadline',
        store=True,
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    action_items = fields.Text(string='Action Items')
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    @api.depends('period_month', 'period_year')
    def _compute_name(self):
        for rec in self:
            month_name = dict(rec._fields['period_month'].selection).get(rec.period_month, '')
            rec.name = f'WPS Compliance - {month_name} {rec.period_year}'

    @api.depends('total_employees', 'employees_paid_wps', 'employees_exempt',
                 'total_salary_due', 'total_salary_paid')
    def _compute_metrics(self):
        for rec in self:
            # Calculate compliance rate
            eligible_employees = rec.total_employees - rec.employees_exempt
            if eligible_employees > 0:
                rec.compliance_rate = (rec.employees_paid_wps / eligible_employees) * 100
            else:
                rec.compliance_rate = 100
            
            # Salary variance
            rec.salary_variance = rec.total_salary_due - rec.total_salary_paid
            
            # Compliance status
            if rec.compliance_rate >= 100:
                rec.is_compliant = True
                rec.compliance_status = 'compliant'
            elif rec.compliance_rate >= 80:
                rec.is_compliant = False
                rec.compliance_status = 'partial'
            else:
                rec.is_compliant = False
                rec.compliance_status = 'non_compliant'

    @api.depends('period_month', 'period_year')
    def _compute_deadline(self):
        for rec in self:
            if rec.period_month and rec.period_year:
                # WPS deadline is typically 15th of the following month
                month = int(rec.period_month)
                year = int(rec.period_year)
                
                # Next month
                if month == 12:
                    next_month = 1
                    next_year = year + 1
                else:
                    next_month = month + 1
                    next_year = year
                
                rec.submission_deadline = date(next_year, next_month, 15)
                rec.is_overdue = date.today() > rec.submission_deadline
            else:
                rec.submission_deadline = False
                rec.is_overdue = False

    @api.model
    def generate_monthly_report(self, company_id=None, period_month=None, period_year=None):
        """Generate monthly WPS compliance report"""
        company = self.env.company if not company_id else self.env['res.company'].browse(company_id)
        
        if not period_month:
            # Previous month
            today = date.today()
            if today.month == 1:
                period_month = '12'
                period_year = str(today.year - 1)
            else:
                period_month = str(today.month - 1).zfill(2)
                period_year = str(today.year)
        
        # Get WPS files for the period
        wps_files = self.env['tazweed.wps.file'].search([
            ('company_id', '=', company.id),
            ('period_month', '=', period_month),
            ('period_year', '=', period_year),
            ('state', '=', 'processed'),
        ])
        
        # Get total employees
        total_employees = self.env['hr.employee'].search_count([
            ('company_id', '=', company.id),
            ('contract_id', '!=', False),
        ])
        
        # Calculate metrics
        employees_paid = sum(wps_files.mapped('employee_count'))
        total_salary_paid = sum(wps_files.mapped('total_net'))
        
        # Create or update report
        existing = self.search([
            ('company_id', '=', company.id),
            ('period_month', '=', period_month),
            ('period_year', '=', period_year),
        ], limit=1)
        
        vals = {
            'period_month': period_month,
            'period_year': period_year,
            'total_employees': total_employees,
            'employees_paid_wps': employees_paid,
            'employees_not_paid': total_employees - employees_paid,
            'total_salary_due': total_salary_paid,  # Simplified
            'total_salary_paid': total_salary_paid,
            'company_id': company.id,
        }
        
        if existing:
            existing.write(vals)
            return existing
        else:
            return self.create(vals)

    def action_view_wps_file(self):
        """View linked WPS file"""
        self.ensure_one()
        if self.wps_file_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('WPS File'),
                'res_model': 'tazweed.wps.file',
                'res_id': self.wps_file_id.id,
                'view_mode': 'form',
            }
        return False
