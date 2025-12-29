# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class PayrollDashboard(models.Model):
    """Payroll Analytics Dashboard for comprehensive payroll metrics and analysis."""
    
    _name = 'payroll.analytics.dashboard'
    _description = 'Payroll Analytics Dashboard'
    _rec_name = 'name'
    
    name = fields.Char(string='Dashboard Name', required=True, default='Payroll Dashboard')
    
    # Filters
    date_from = fields.Date(string='From Date', 
                             default=lambda self: fields.Date.today().replace(day=1) - relativedelta(months=11))
    date_to = fields.Date(string='To Date', default=fields.Date.today)
    
    department_ids = fields.Many2many('hr.department', 
                                       'payroll_dashboard_department_rel',
                                       'dashboard_id', 'department_id',
                                       string='Departments')
    structure_ids = fields.Many2many('hr.payroll.structure', 
                                      'payroll_dashboard_structure_rel',
                                      'dashboard_id', 'structure_id',
                                      string='Salary Structures')
    
    # View Type
    view_type = fields.Selection([
        ('summary', 'Summary'),
        ('by_department', 'By Department'),
        ('by_structure', 'By Structure'),
        ('by_employee', 'By Employee'),
        ('deductions', 'Deductions Analysis'),
        ('trend', 'Trend Analysis'),
    ], string='View Type', default='summary')
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    
    # Computed KPI Fields - Payroll Totals
    total_payslips = fields.Integer(string='Total Payslips', compute='_compute_kpi_values')
    total_gross_salary = fields.Float(string='Total Gross Salary', digits=(16, 2), compute='_compute_kpi_values')
    total_net_salary = fields.Float(string='Total Net Salary', digits=(16, 2), compute='_compute_kpi_values')
    total_deductions = fields.Float(string='Total Deductions', digits=(16, 2), compute='_compute_kpi_values')
    total_allowances = fields.Float(string='Total Allowances', digits=(16, 2), compute='_compute_kpi_values')
    avg_salary = fields.Float(string='Average Salary', digits=(16, 2), compute='_compute_kpi_values')
    
    # Deduction Breakdown
    total_pension = fields.Float(string='Total Pension', digits=(16, 2), compute='_compute_kpi_values')
    total_loans = fields.Float(string='Total Loan Deductions', digits=(16, 2), compute='_compute_kpi_values')
    total_absences = fields.Float(string='Total Absence Deductions', digits=(16, 2), compute='_compute_kpi_values')
    total_other_deductions = fields.Float(string='Other Deductions', digits=(16, 2), compute='_compute_kpi_values')
    
    # Allowance Breakdown
    total_housing = fields.Float(string='Total Housing Allowance', digits=(16, 2), compute='_compute_kpi_values')
    total_transport = fields.Float(string='Total Transport Allowance', digits=(16, 2), compute='_compute_kpi_values')
    total_food = fields.Float(string='Total Food Allowance', digits=(16, 2), compute='_compute_kpi_values')
    total_other_allowances = fields.Float(string='Other Allowances', digits=(16, 2), compute='_compute_kpi_values')
    
    # Payslip Status
    draft_payslips = fields.Integer(string='Draft Payslips', compute='_compute_kpi_values')
    confirmed_payslips = fields.Integer(string='Confirmed Payslips', compute='_compute_kpi_values')
    paid_payslips = fields.Integer(string='Paid Payslips', compute='_compute_kpi_values')
    
    # WPS Metrics
    wps_files_count = fields.Integer(string='WPS Files', compute='_compute_kpi_values')
    wps_total_amount = fields.Float(string='WPS Total Amount', digits=(16, 2), compute='_compute_kpi_values')
    
    # Loan Metrics
    active_loans = fields.Integer(string='Active Loans', compute='_compute_kpi_values')
    total_loan_balance = fields.Float(string='Total Loan Balance', digits=(16, 2), compute='_compute_kpi_values')
    
    # Gratuity Metrics
    total_gratuity_provision = fields.Float(string='Total Gratuity Provision', digits=(16, 2), compute='_compute_kpi_values')
    
    # Dashboard Data (JSON)
    dashboard_data = fields.Text(string='Dashboard Data', compute='_compute_dashboard_data')
    
    @api.depends('date_from', 'date_to', 'department_ids', 'structure_ids')
    def _compute_kpi_values(self):
        """Compute KPI values for payroll dashboard."""
        for record in self:
            # Set default values
            record.total_payslips = 0
            record.total_gross_salary = 0
            record.total_net_salary = 0
            record.total_deductions = 0
            record.total_allowances = 0
            record.avg_salary = 0
            record.total_pension = 0
            record.total_loans = 0
            record.total_absences = 0
            record.total_other_deductions = 0
            record.total_housing = 0
            record.total_transport = 0
            record.total_food = 0
            record.total_other_allowances = 0
            record.draft_payslips = 0
            record.confirmed_payslips = 0
            record.paid_payslips = 0
            record.wps_files_count = 0
            record.wps_total_amount = 0
            record.active_loans = 0
            record.total_loan_balance = 0
            record.total_gratuity_provision = 0
            
            if not record.date_from or not record.date_to:
                continue
            
            try:
                # Build domain for payslips
                payslip_domain = [
                    ('date_from', '>=', record.date_from),
                    ('date_to', '<=', record.date_to),
                ]
                
                if record.id:
                    try:
                        if record.department_ids:
                            payslip_domain.append(('employee_id.department_id', 'in', record.department_ids.ids))
                    except Exception:
                        pass
                    try:
                        if record.structure_ids:
                            payslip_domain.append(('struct_id', 'in', record.structure_ids.ids))
                    except Exception:
                        pass
                
                # Get payslips
                Payslip = self.env['hr.payslip'].sudo()
                if 'hr.payslip' in self.env:
                    payslips = Payslip.search(payslip_domain)
                    record.total_payslips = len(payslips)
                    
                    for slip in payslips:
                        # Get payslip lines
                        for line in slip.line_ids:
                            code = line.code.upper() if line.code else ''
                            amount = line.total or 0
                            
                            # Categorize by rule code
                            if code in ['GROSS', 'BASIC']:
                                record.total_gross_salary += amount
                            elif code == 'NET':
                                record.total_net_salary += amount
                            elif 'PENSION' in code or 'GPSSA' in code:
                                record.total_pension += amount
                                record.total_deductions += amount
                            elif 'LOAN' in code:
                                record.total_loans += amount
                                record.total_deductions += amount
                            elif 'ABSENCE' in code or 'UNPAID' in code:
                                record.total_absences += amount
                                record.total_deductions += amount
                            elif 'HOUSING' in code or 'HRA' in code:
                                record.total_housing += amount
                                record.total_allowances += amount
                            elif 'TRANSPORT' in code or 'TRA' in code:
                                record.total_transport += amount
                                record.total_allowances += amount
                            elif 'FOOD' in code or 'MEAL' in code:
                                record.total_food += amount
                                record.total_allowances += amount
                            elif line.category_id:
                                cat_code = line.category_id.code.upper() if line.category_id.code else ''
                                if cat_code == 'DED':
                                    record.total_other_deductions += amount
                                    record.total_deductions += amount
                                elif cat_code == 'ALW':
                                    record.total_other_allowances += amount
                                    record.total_allowances += amount
                        
                        # Count by status
                        if slip.state == 'draft':
                            record.draft_payslips += 1
                        elif slip.state == 'verify':
                            record.confirmed_payslips += 1
                        elif slip.state == 'done':
                            record.paid_payslips += 1
                    
                    # Calculate average
                    if record.total_payslips > 0:
                        record.avg_salary = record.total_net_salary / record.total_payslips
                
                # Get WPS files
                WPSFile = self.env['tazweed.wps.file'].sudo()
                if 'tazweed.wps.file' in self.env:
                    wps_domain = [
                        ('create_date', '>=', record.date_from),
                        ('create_date', '<=', record.date_to),
                    ]
                    wps_files = WPSFile.search(wps_domain)
                    record.wps_files_count = len(wps_files)
                    record.wps_total_amount = sum(wps_files.mapped('total_amount'))
                
                # Get active loans
                Loan = self.env['tazweed.payroll.loan'].sudo()
                if 'tazweed.payroll.loan' in self.env:
                    loans = Loan.search([('state', '=', 'approved')])
                    record.active_loans = len(loans)
                    record.total_loan_balance = sum(loans.mapped('balance'))
                
                # Get gratuity provisions
                Gratuity = self.env['tazweed.employee.gratuity'].sudo()
                if 'tazweed.employee.gratuity' in self.env:
                    gratuities = Gratuity.search([])
                    record.total_gratuity_provision = sum(gratuities.mapped('provision_amount'))
                    
            except Exception:
                pass
    
    def _compute_dashboard_data(self):
        for record in self:
            record.dashboard_data = json.dumps(record.get_dashboard_data())
    
    def get_dashboard_data(self):
        """Get comprehensive payroll dashboard data."""
        self.ensure_one()
        
        if not self.date_from or not self.date_to:
            return {
                'summary': {},
                'by_department': [],
                'deductions': {},
                'allowances': {},
                'trend': [],
                'charts': {},
            }
        
        return {
            'summary': self._get_summary_data(),
            'by_department': self._get_by_department_data(),
            'deductions': self._get_deductions_data(),
            'allowances': self._get_allowances_data(),
            'trend': self._get_trend_data(),
            'charts': self._get_charts_data(),
        }
    
    def _get_summary_data(self):
        """Get summary statistics."""
        return {
            'total_payslips': self.total_payslips,
            'total_gross_salary': self.total_gross_salary,
            'total_net_salary': self.total_net_salary,
            'total_deductions': self.total_deductions,
            'total_allowances': self.total_allowances,
            'avg_salary': self.avg_salary,
            'draft_payslips': self.draft_payslips,
            'confirmed_payslips': self.confirmed_payslips,
            'paid_payslips': self.paid_payslips,
        }
    
    def _get_by_department_data(self):
        """Get payroll by department."""
        result = []
        try:
            Payslip = self.env['hr.payslip'].sudo()
            if 'hr.payslip' in self.env:
                payslips = Payslip.search([
                    ('date_from', '>=', self.date_from),
                    ('date_to', '<=', self.date_to),
                ])
                
                dept_data = {}
                for slip in payslips:
                    dept = slip.employee_id.department_id.name if slip.employee_id.department_id else 'Unassigned'
                    if dept not in dept_data:
                        dept_data[dept] = {'count': 0, 'gross': 0, 'net': 0}
                    
                    dept_data[dept]['count'] += 1
                    for line in slip.line_ids:
                        if line.code == 'GROSS':
                            dept_data[dept]['gross'] += line.total or 0
                        elif line.code == 'NET':
                            dept_data[dept]['net'] += line.total or 0
                
                for dept, data in dept_data.items():
                    result.append({
                        'department': dept,
                        'payslips': data['count'],
                        'gross_salary': data['gross'],
                        'net_salary': data['net'],
                    })
        except Exception:
            pass
        return result
    
    def _get_deductions_data(self):
        """Get deductions breakdown."""
        return {
            'pension': self.total_pension,
            'loans': self.total_loans,
            'absences': self.total_absences,
            'other': self.total_other_deductions,
            'total': self.total_deductions,
        }
    
    def _get_allowances_data(self):
        """Get allowances breakdown."""
        return {
            'housing': self.total_housing,
            'transport': self.total_transport,
            'food': self.total_food,
            'other': self.total_other_allowances,
            'total': self.total_allowances,
        }
    
    def _get_trend_data(self):
        """Get monthly payroll trend."""
        result = []
        try:
            Payslip = self.env['hr.payslip'].sudo()
            if 'hr.payslip' in self.env:
                current = self.date_from
                while current <= self.date_to:
                    month_end = current + relativedelta(months=1, days=-1)
                    if month_end > self.date_to:
                        month_end = self.date_to
                    
                    payslips = Payslip.search([
                        ('date_from', '>=', current),
                        ('date_to', '<=', month_end),
                    ])
                    
                    gross = 0
                    net = 0
                    for slip in payslips:
                        for line in slip.line_ids:
                            if line.code == 'GROSS':
                                gross += line.total or 0
                            elif line.code == 'NET':
                                net += line.total or 0
                    
                    result.append({
                        'month': current.strftime('%Y-%m'),
                        'payslips': len(payslips),
                        'gross_salary': gross,
                        'net_salary': net,
                    })
                    
                    current = current + relativedelta(months=1)
        except Exception:
            pass
        return result
    
    def _get_charts_data(self):
        """Get chart configuration data."""
        return {
            'salary_pie': {
                'type': 'pie',
                'data': [
                    {'label': 'Net Salary', 'value': self.total_net_salary},
                    {'label': 'Deductions', 'value': self.total_deductions},
                ],
            },
            'deductions_bar': {
                'type': 'bar',
                'data': [
                    {'label': 'Pension', 'value': self.total_pension},
                    {'label': 'Loans', 'value': self.total_loans},
                    {'label': 'Absences', 'value': self.total_absences},
                    {'label': 'Other', 'value': self.total_other_deductions},
                ],
            },
            'trend_line': {
                'type': 'line',
                'data': self._get_trend_data(),
            },
        }
    
    def action_refresh(self):
        """Refresh dashboard data."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dashboard Refreshed'),
                'message': _('Payroll dashboard data has been refreshed.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_view_payslips(self):
        """Open payslips view."""
        self.ensure_one()
        return {
            'name': _('Payslips'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to),
            ],
            'context': {'search_default_group_by_state': 1},
        }
    
    def action_view_draft_payslips(self):
        """Open draft payslips view."""
        self.ensure_one()
        return {
            'name': _('Draft Payslips'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to),
                ('state', '=', 'draft'),
            ],
        }
    
    def action_view_loans(self):
        """Open loans view."""
        self.ensure_one()
        return {
            'name': _('Active Loans'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.payroll.loan',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'approved')],
        }
    
    def action_generate_wps(self):
        """Generate WPS file."""
        self.ensure_one()
        return {
            'name': _('Generate WPS File'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.wps.file',
            'view_mode': 'form',
            'target': 'new',
        }
