# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval
import logging

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    """Payslip - Standalone Model"""
    _name = 'hr.payslip'
    _description = 'Payslip'
    _order = 'date_from desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Payslip Name', required=True)
    number = fields.Char(string='Reference', readonly=True, copy=False, default='/')
    
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        domain="[('contract_ids.state', 'in', ['open', 'pending'])]"
    )
    department_id = fields.Many2one(
        'hr.department', string='Department',
        related='employee_id.department_id', store=True, readonly=True
    )
    job_id = fields.Many2one(
        'hr.job', string='Job Position',
        related='employee_id.job_id', store=True, readonly=True
    )
    
    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    
    # Batch
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Batch', readonly=True, copy=False, ondelete='cascade')
    
    # Contract & Structure
    contract_id = fields.Many2one('hr.contract', string='Contract', required=True)
    struct_id = fields.Many2one('hr.payroll.structure', string='Structure', required=True)
    
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Lines
    worked_days_line_ids = fields.One2many('hr.payslip.worked_days', 'payslip_id', string='Worked Days', copy=True)
    input_line_ids = fields.One2many('hr.payslip.input', 'payslip_id', string='Other Inputs', copy=True)
    line_ids = fields.One2many('hr.payslip.line', 'slip_id', string='Salary Lines', copy=True)
    
    # Computed Amounts
    basic_wage = fields.Float(string='Basic Wage', compute='_compute_amounts', store=True)
    gross_wage = fields.Float(string='Gross Wage', compute='_compute_amounts', store=True)
    net_wage = fields.Float(string='Net Wage', compute='_compute_amounts', store=True)
    total_deductions = fields.Float(string='Total Deductions', compute='_compute_amounts', store=True)
    
    # UAE Specific
    housing_allowance = fields.Float(string='Housing Allowance', compute='_compute_amounts', store=True)
    transport_allowance = fields.Float(string='Transport Allowance', compute='_compute_amounts', store=True)
    other_allowances = fields.Float(string='Other Allowances', compute='_compute_amounts', store=True)
    overtime_amount = fields.Float(string='Overtime Amount', compute='_compute_amounts', store=True)
    
    # WPS
    wps_file_id = fields.Many2one('tazweed.wps.file', string='WPS File', readonly=True)
    wps_status = fields.Selection([
        ('pending', 'Pending'),
        ('included', 'Included in WPS'),
        ('transferred', 'Transferred'),
        ('failed', 'Failed'),
    ], string='WPS Status', default='pending', tracking=True)
    
    # Bank Transfer
    bank_account_id = fields.Many2one('tazweed.employee.bank', string='Bank Account', compute='_compute_bank_account', store=True)
    
    # Payment
    payment_date = fields.Date(string='Payment Date')
    payment_method = fields.Selection([
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ], string='Payment Method', default='bank')
    
    note = fields.Html(string='Internal Note')
    credit_note = fields.Boolean(string='Credit Note', default=False, help='Indicates this payslip has a refund of another')
    paid = fields.Boolean(string='Made Payment Order', readonly=True, copy=False)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('done', 'Done'),
        ('paid', 'Paid'),
        ('cancel', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('line_ids.total')
    def _compute_amounts(self):
        """Compute payslip amounts from salary lines"""
        for payslip in self:
            basic = gross = net = deductions = housing = transport = other_allow = overtime = 0.0
            
            for line in payslip.line_ids:
                cat_code = line.category_id.code if line.category_id else ''
                if cat_code == 'BASIC':
                    basic += line.total
                elif cat_code == 'GROSS':
                    gross = line.total
                elif cat_code == 'NET':
                    net = line.total
                elif cat_code == 'DED':
                    deductions += abs(line.total)
                elif line.code == 'HRA':
                    housing = line.total
                elif line.code == 'TRA':
                    transport = line.total
                elif line.code == 'OT':
                    overtime = line.total
                elif cat_code == 'ALW':
                    other_allow += line.total
            
            payslip.basic_wage = basic
            payslip.gross_wage = gross if gross else basic + housing + transport + other_allow + overtime
            payslip.net_wage = net if net else payslip.gross_wage - deductions
            payslip.total_deductions = deductions
            payslip.housing_allowance = housing
            payslip.transport_allowance = transport
            payslip.other_allowances = other_allow
            payslip.overtime_amount = overtime

    @api.depends('employee_id')
    def _compute_bank_account(self):
        """Get employee's primary bank account"""
        for payslip in self:
            bank = payslip.employee_id.bank_account_ids.filtered(lambda b: b.is_primary and b.is_wps_enabled)[:1]
            payslip.bank_account_id = bank if bank else False

    @api.onchange('employee_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        if self.employee_id and self.date_from and self.date_to:
            contract = self.employee_id.contract_ids.filtered(
                lambda c: c.state in ['open', 'pending'] and 
                c.date_start <= self.date_from and 
                (not c.date_end or c.date_end >= self.date_to)
            )[:1]
            if contract:
                self.contract_id = contract
                self.struct_id = contract.structure_type_id.default_struct_id if contract.structure_type_id else False
            
            self.name = _('Salary Slip of %s for %s') % (
                self.employee_id.name,
                self.date_from.strftime('%B %Y') if self.date_from else ''
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number', '/') == '/':
                vals['number'] = self.env['ir.sequence'].next_by_code('hr.payslip') or '/'
        return super().create(vals_list)

    def action_payslip_draft(self):
        return self.write({'state': 'draft'})

    def action_payslip_verify(self):
        return self.write({'state': 'verify'})

    def action_payslip_done(self):
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        return self.write({'state': 'cancel'})

    def action_payslip_paid(self):
        return self.write({'state': 'paid', 'payment_date': fields.Date.today()})

    def compute_sheet(self):
        """Compute payslip salary lines"""
        for payslip in self:
            # Clear existing lines
            payslip.line_ids.unlink()
            
            # Get structure rules
            if not payslip.struct_id:
                continue
            
            rules = payslip.struct_id.get_all_rules()
            
            # Build local dictionary for rule computation
            localdict = payslip._get_localdict()
            
            # Compute each rule
            lines = []
            for rule in rules.sorted(key=lambda r: r.sequence):
                amount, qty, rate = rule._compute_rule(localdict)
                if amount or rule.appears_on_payslip:
                    total = amount * qty * rate / 100
                    lines.append({
                        'slip_id': payslip.id,
                        'salary_rule_id': rule.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'amount': amount,
                        'quantity': qty,
                        'rate': rate,
                        'total': total,
                    })
                    # Update localdict with computed value
                    localdict['categories'][rule.category_id.code] = localdict['categories'].get(rule.category_id.code, 0) + total
                    localdict['rules'][rule.code] = total
            
            self.env['hr.payslip.line'].create(lines)
        
        return True

    def _get_localdict(self):
        """Build local dictionary for rule computation"""
        self.ensure_one()
        
        # Build worked_days dict
        worked_days = {}
        for wd in self.worked_days_line_ids:
            worked_days[wd.code] = {
                'number_of_days': wd.number_of_days,
                'number_of_hours': wd.number_of_hours,
                'amount': wd.amount,
            }
        
        # Build inputs dict
        inputs = {}
        for inp in self.input_line_ids:
            inputs[inp.code] = {
                'amount': inp.amount,
                'quantity': inp.quantity,
            }
        
        return {
            'payslip': self,
            'employee': self.employee_id,
            'contract': self.contract_id,
            'categories': {},
            'rules': {},
            'worked_days': worked_days,
            'inputs': inputs,
            'result': 0.0,
            'result_qty': 1.0,
            'result_rate': 100.0,
        }


class HrPayslipWorkedDays(models.Model):
    """Payslip Worked Days"""
    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'sequence, id'

    payslip_id = fields.Many2one('hr.payslip', string='Payslip', required=True, ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    number_of_days = fields.Float(string='Number of Days')
    number_of_hours = fields.Float(string='Number of Hours')
    amount = fields.Float(string='Amount')


class HrPayslipInput(models.Model):
    """Payslip Input"""
    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'sequence, id'

    payslip_id = fields.Many2one('hr.payslip', string='Payslip', required=True, ondelete='cascade')
    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    amount = fields.Float(string='Amount')
    quantity = fields.Float(string='Quantity', default=1.0)
    contract_id = fields.Many2one('hr.contract', string='Contract')


class HrPayslipLine(models.Model):
    """Payslip Line"""
    _name = 'hr.payslip.line'
    _description = 'Payslip Line'
    _order = 'sequence, id'

    slip_id = fields.Many2one('hr.payslip', string='Payslip', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Rule')
    employee_id = fields.Many2one('hr.employee', related='slip_id.employee_id', store=True)
    contract_id = fields.Many2one('hr.contract', related='slip_id.contract_id', store=True)
    
    name = fields.Char(string='Description', required=True)
    code = fields.Char(string='Code', required=True)
    category_id = fields.Many2one('hr.salary.rule.category', string='Category')
    sequence = fields.Integer(string='Sequence', default=10)
    
    amount = fields.Float(string='Amount')
    quantity = fields.Float(string='Quantity', default=1.0)
    rate = fields.Float(string='Rate (%)', default=100.0)
    total = fields.Float(string='Total', compute='_compute_total', store=True)

    @api.depends('amount', 'quantity', 'rate')
    def _compute_total(self):
        for line in self:
            line.total = line.amount * line.quantity * line.rate / 100


    @api.model
    def get_payroll_dashboard_data(self, period='current'):
        """Get dashboard data for payroll management"""
        today = date.today()
        
        # Calculate date range based on period
        if period == 'current':
            start_date = today.replace(day=1)
            end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)
        elif period == 'previous':
            end_date = today.replace(day=1) - relativedelta(days=1)
            start_date = end_date.replace(day=1)
        elif period == 'quarter':
            quarter = (today.month - 1) // 3
            start_date = date(today.year, quarter * 3 + 1, 1)
            end_date = (start_date + relativedelta(months=3)) - relativedelta(days=1)
        else:  # year
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        
        # Get payslips in the period
        payslips = self.search([
            ('date_from', '>=', start_date),
            ('date_to', '<=', end_date),
        ])
        
        done_payslips = payslips.filtered(lambda p: p.state in ['done', 'paid'])
        pending_payslips = payslips.filtered(lambda p: p.state in ['draft', 'verify'])
        
        # Calculate stats
        total_payroll = sum(done_payslips.mapped('net_wage'))
        employees_paid = len(done_payslips.mapped('employee_id'))
        pending_count = len(pending_payslips)
        avg_salary = total_payroll / max(employees_paid, 1)
        total_deductions = sum(done_payslips.mapped('total_deductions'))
        total_allowances = sum(done_payslips.mapped('housing_allowance')) + \
                          sum(done_payslips.mapped('transport_allowance')) + \
                          sum(done_payslips.mapped('other_allowances'))
        
        # WPS files generated
        wps_count = self.env['tazweed.wps.file'].search_count([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date),
        ]) if 'tazweed.wps.file' in self.env else 0
        
        # Outstanding loans
        loans_outstanding = 0
        if 'payroll.loan' in self.env:
            active_loans = self.env['payroll.loan'].search([('state', '=', 'approved')])
            loans_outstanding = sum(active_loans.mapped('balance_amount'))
        
        # Payroll by department
        departments = self.env['hr.department'].search([], limit=10)
        payroll_by_department = []
        for dept in departments:
            dept_payslips = done_payslips.filtered(lambda p: p.department_id.id == dept.id)
            total = sum(dept_payslips.mapped('net_wage'))
            if total > 0:
                payroll_by_department.append({
                    'name': dept.name[:15],
                    'amount': total,
                })
        payroll_by_department.sort(key=lambda x: x['amount'], reverse=True)
        payroll_by_department = payroll_by_department[:8]
        
        # Salary distribution
        salary_ranges = [
            ('0-5K', 0, 5000),
            ('5K-10K', 5000, 10000),
            ('10K-15K', 10000, 15000),
            ('15K-20K', 15000, 20000),
            ('20K-30K', 20000, 30000),
            ('30K+', 30000, float('inf')),
        ]
        salary_distribution = []
        for label, min_sal, max_sal in salary_ranges:
            count = len(done_payslips.filtered(
                lambda p: min_sal <= p.net_wage < max_sal
            ))
            if count > 0:
                salary_distribution.append({
                    'range': label,
                    'count': count,
                })
        
        # Recent payslips
        recent_payslips = []
        recent = self.search([], order='create_date desc', limit=10)
        for payslip in recent:
            recent_payslips.append({
                'id': payslip.id,
                'employee_name': payslip.employee_id.name if payslip.employee_id else 'Unknown',
                'period': payslip.date_from.strftime('%b %Y') if payslip.date_from else '',
                'net_salary': payslip.net_wage,
                'state': payslip.state,
            })
        
        # Pending loans
        pending_loans = []
        if 'payroll.loan' in self.env:
            loans = self.env['payroll.loan'].search([('state', '=', 'approved')], limit=10)
            for loan in loans:
                pending_loans.append({
                    'id': loan.id,
                    'employee_name': loan.employee_id.name if loan.employee_id else 'Unknown',
                    'amount': loan.loan_amount,
                    'balance': loan.balance_amount,
                    'monthly_deduction': loan.installment_amount,
                })
        
        # Alerts
        alerts = []
        if pending_count > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'fa-exclamation-triangle',
                'message': f'{pending_count} payslips pending processing',
            })
        
        return {
            'stats': {
                'totalPayroll': round(total_payroll, 2),
                'employeesPaid': employees_paid,
                'pendingPayslips': pending_count,
                'avgSalary': round(avg_salary, 2),
                'totalDeductions': round(total_deductions, 2),
                'totalAllowances': round(total_allowances, 2),
                'wpsGenerated': wps_count,
                'loansOutstanding': round(loans_outstanding, 2),
            },
            'payroll_by_department': payroll_by_department,
            'salary_distribution': salary_distribution,
            'monthly_trend': [],
            'recent_payslips': recent_payslips,
            'pending_loans': pending_loans,
            'alerts': alerts,
        }
