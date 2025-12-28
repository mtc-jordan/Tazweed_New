# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime
import base64


class WPSFile(models.Model):
    """WPS SIF File Generation"""
    _name = 'tazweed.wps.file'
    _description = 'WPS File'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    
    # Period
    period_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True)
    period_year = fields.Char(string='Year', required=True, default=lambda self: str(date.today().year))
    
    # Company Info
    employer_eid = fields.Char(string='Employer Emirates ID', required=True)
    employer_bank_code = fields.Char(string='Employer Bank Code', required=True)
    employer_bank_account = fields.Char(string='Employer Bank Account', required=True)
    
    # File Details
    salary_date = fields.Date(string='Salary Date', required=True)
    total_employees = fields.Integer(string='Total Employees', compute='_compute_totals', store=True)
    total_salary = fields.Float(string='Total Salary', compute='_compute_totals', store=True)
    
    # Lines
    line_ids = fields.One2many('tazweed.wps.file.line', 'wps_file_id', string='Employee Lines')
    
    # Generated File
    sif_file = fields.Binary(string='SIF File', readonly=True)
    sif_filename = fields.Char(string='SIF Filename')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('submitted', 'Submitted'),
        ('processed', 'Processed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    
    submission_date = fields.Date(string='Submission Date')
    processing_date = fields.Date(string='Processing Date')
    rejection_reason = fields.Text(string='Rejection Reason')
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.wps.file') or _('New')
        return super().create(vals)

    @api.depends('line_ids', 'line_ids.net_salary')
    def _compute_totals(self):
        for rec in self:
            rec.total_employees = len(rec.line_ids)
            rec.total_salary = sum(rec.line_ids.mapped('net_salary'))

    def action_generate_lines(self):
        """Generate WPS lines from payslips"""
        self.ensure_one()
        # Clear existing lines
        self.line_ids.unlink()
        
        # Get employees with bank accounts
        employees = self.env['hr.employee'].search([
            ('company_id', '=', self.company_id.id),
            ('contract_id', '!=', False),
        ])
        
        lines = []
        for emp in employees:
            # Get bank account
            bank = emp.bank_account_id if hasattr(emp, 'bank_account_id') else False
            
            lines.append((0, 0, {
                'employee_id': emp.id,
                'labour_card_no': getattr(emp, 'labour_card_no', '') or '',
                'bank_code': bank.bank_id.bic if bank and bank.bank_id else '',
                'bank_account': bank.acc_number if bank else '',
                'basic_salary': emp.contract_id.wage if emp.contract_id else 0,
                'housing_allowance': 0,
                'transport_allowance': 0,
                'other_allowances': 0,
                'deductions': 0,
            }))
        
        self.line_ids = lines
        return True

    def action_generate_sif(self):
        """Generate SIF file"""
        self.ensure_one()
        if not self.line_ids:
            raise ValidationError(_('No employee lines to generate SIF file.'))
        
        # Generate SIF content
        sif_content = self._generate_sif_content()
        
        # Encode and save
        self.sif_file = base64.b64encode(sif_content.encode('utf-8'))
        self.sif_filename = f'WPS_{self.employer_eid}_{self.period_year}{self.period_month}.SIF'
        self.state = 'generated'
        
        return True

    def _generate_sif_content(self):
        """Generate SIF file content according to UAE WPS format"""
        lines = []
        
        # Header Record (EDR)
        header = 'EDR'
        header += self.employer_eid.ljust(15)[:15]
        header += self.employer_bank_code.ljust(20)[:20]
        header += self.salary_date.strftime('%Y-%m-%d')
        header += self.salary_date.strftime('%H%M')
        header += str(len(self.line_ids)).zfill(6)
        header += str(int(self.total_salary * 100)).zfill(15)
        header += 'AED'
        lines.append(header)
        
        # Employee Records (SDR)
        for line in self.line_ids:
            sdr = 'SDR'
            sdr += (line.labour_card_no or '').ljust(15)[:15]
            sdr += (line.bank_code or '').ljust(20)[:20]
            sdr += (line.bank_account or '').ljust(34)[:34]
            sdr += line.salary_date.strftime('%Y-%m-%d') if line.salary_date else self.salary_date.strftime('%Y-%m-%d')
            sdr += str(int(line.net_salary * 100)).zfill(15)
            sdr += 'AED'
            sdr += str(int(line.basic_salary * 100)).zfill(15)
            sdr += str(int(line.housing_allowance * 100)).zfill(15)
            sdr += str(int(line.other_allowances * 100)).zfill(15)
            sdr += str(int(line.deductions * 100)).zfill(15)
            sdr += (line.employee_id.name or '').ljust(50)[:50]
            lines.append(sdr)
        
        return '\n'.join(lines)

    def action_submit(self):
        self.write({'state': 'submitted', 'submission_date': date.today()})

    def action_process(self):
        self.write({'state': 'processed', 'processing_date': date.today()})

    def action_reject(self):
        self.write({'state': 'rejected'})


class WPSFileLine(models.Model):
    """WPS File Line"""
    _name = 'tazweed.wps.file.line'
    _description = 'WPS File Line'

    wps_file_id = fields.Many2one('tazweed.wps.file', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    
    # Employee Details
    labour_card_no = fields.Char(string='Labour Card No.')
    bank_code = fields.Char(string='Bank Code')
    bank_account = fields.Char(string='Bank Account')
    
    # Salary Components
    basic_salary = fields.Float(string='Basic Salary')
    housing_allowance = fields.Float(string='Housing Allowance')
    transport_allowance = fields.Float(string='Transport Allowance')
    other_allowances = fields.Float(string='Other Allowances')
    deductions = fields.Float(string='Deductions')
    
    net_salary = fields.Float(string='Net Salary', compute='_compute_net', store=True)
    
    salary_date = fields.Date(string='Salary Date')
    
    # Status
    is_valid = fields.Boolean(string='Valid', default=True)
    validation_message = fields.Char(string='Validation Message')

    @api.depends('basic_salary', 'housing_allowance', 'transport_allowance', 'other_allowances', 'deductions')
    def _compute_net(self):
        for line in self:
            line.net_salary = (line.basic_salary + line.housing_allowance + 
                              line.transport_allowance + line.other_allowances - line.deductions)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            emp = self.employee_id
            self.labour_card_no = getattr(emp, 'labour_card_no', '') or ''
            if hasattr(emp, 'bank_account_id') and emp.bank_account_id:
                self.bank_code = emp.bank_account_id.bank_id.bic if emp.bank_account_id.bank_id else ''
                self.bank_account = emp.bank_account_id.acc_number
            if emp.contract_id:
                self.basic_salary = emp.contract_id.wage


class WPSComplianceReport(models.Model):
    """WPS Compliance Report"""
    _name = 'tazweed.wps.compliance'
    _description = 'WPS Compliance Report'
    _order = 'period_year desc, period_month desc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    period_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True)
    period_year = fields.Char(string='Year', required=True)
    
    # Metrics
    total_employees = fields.Integer(string='Total Employees')
    employees_paid_wps = fields.Integer(string='Employees Paid via WPS')
    employees_not_paid = fields.Integer(string='Employees Not Paid')
    
    compliance_rate = fields.Float(string='Compliance Rate %', compute='_compute_compliance', store=True)
    
    total_salary_due = fields.Float(string='Total Salary Due')
    total_salary_paid = fields.Float(string='Total Salary Paid')
    
    # Status
    is_compliant = fields.Boolean(string='Compliant', compute='_compute_compliance', store=True)
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('period_month', 'period_year')
    def _compute_name(self):
        for rec in self:
            month_name = dict(rec._fields['period_month'].selection).get(rec.period_month, '')
            rec.name = f'WPS Compliance - {month_name} {rec.period_year}'

    @api.depends('total_employees', 'employees_paid_wps')
    def _compute_compliance(self):
        for rec in self:
            if rec.total_employees:
                rec.compliance_rate = (rec.employees_paid_wps / rec.total_employees) * 100
            else:
                rec.compliance_rate = 0
            rec.is_compliant = rec.compliance_rate >= 100
