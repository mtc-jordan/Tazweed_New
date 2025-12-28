# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
import base64
import logging

_logger = logging.getLogger(__name__)


class WPSFile(models.Model):
    """WPS (Wage Protection System) File Generation"""
    _name = 'tazweed.wps.file'
    _description = 'WPS File'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default='/',
        copy=False,
    )
    
    # Period - using same field names as tazweed_uae_compliance for consistency
    period_month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Month', required=True, tracking=True)
    
    period_year = fields.Char(
        string='Year',
        required=True,
        default=lambda self: str(date.today().year),
    )
    
    # Batch
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        tracking=True,
    )
    
    # Employer Details
    employer_eid = fields.Char(
        string='Employer EID',
        help='Employer Emirates ID (15 digits)',
    )
    employer_bank_code = fields.Char(
        string='Employer Bank Code',
        help='Employer Bank Routing Code',
    )
    employer_account = fields.Char(
        string='Employer Account',
        help='Employer Bank Account Number',
    )
    
    # File Details
    file_type = fields.Selection([
        ('sif', 'SIF (Salary Information File)'),
        ('non_sif', 'Non-SIF'),
    ], string='File Type', default='sif', required=True)
    
    # Lines
    line_ids = fields.One2many(
        'tazweed.wps.file.line',
        'wps_file_id',
        string='WPS Lines',
    )
    
    # Counts
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_totals',
        store=True,
    )
    
    # Amounts
    total_basic = fields.Float(
        string='Total Basic',
        compute='_compute_totals',
        store=True,
    )
    total_housing = fields.Float(
        string='Total Housing',
        compute='_compute_totals',
        store=True,
    )
    total_transport = fields.Float(
        string='Total Transport',
        compute='_compute_totals',
        store=True,
    )
    total_other = fields.Float(
        string='Total Other Allowances',
        compute='_compute_totals',
        store=True,
    )
    total_overtime = fields.Float(
        string='Total Overtime',
        compute='_compute_totals',
        store=True,
    )
    total_deductions = fields.Float(
        string='Total Deductions',
        compute='_compute_totals',
        store=True,
    )
    total_leave = fields.Float(
        string='Total Leave',
        compute='_compute_totals',
        store=True,
    )
    total_net = fields.Float(
        string='Total Net',
        compute='_compute_totals',
        store=True,
    )
    
    # File
    file_data = fields.Binary(
        string='WPS File',
        readonly=True,
    )
    file_name = fields.Char(
        string='File Name',
        readonly=True,
    )
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('submitted', 'Submitted to Bank'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Submission
    submission_date = fields.Date(
        string='Submission Date',
        readonly=True,
    )
    processing_date = fields.Date(
        string='Processing Date',
        readonly=True,
    )
    
    # Bank Response
    bank_reference = fields.Char(
        string='Bank Reference',
        readonly=True,
    )
    bank_response = fields.Text(
        string='Bank Response',
        readonly=True,
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    
    # Salary Date - for compatibility with tazweed_uae_compliance
    salary_date = fields.Date(
        string='Salary Date',
        help='Date when salaries are paid',
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    
    # Compatibility fields with tazweed_uae_compliance
    total_employees = fields.Integer(
        string='Total Employees',
        compute='_compute_totals',
        store=True,
    )
    total_salary = fields.Float(
        string='Total Salary',
        compute='_compute_totals',
        store=True,
    )
    employer_bank_account = fields.Char(
        string='Employer Bank Account',
        related='employer_account',
        store=False,
    )
    sif_file = fields.Binary(
        string='SIF File',
        related='file_data',
        store=False,
    )
    sif_filename = fields.Char(
        string='SIF Filename',
        related='file_name',
        store=False,
    )
    rejection_reason = fields.Text(string='Rejection Reason')

    @api.depends('line_ids.basic_salary', 'line_ids.housing_allowance', 
                 'line_ids.transport_allowance', 'line_ids.other_allowance',
                 'line_ids.overtime', 'line_ids.deductions', 'line_ids.leave_salary',
                 'line_ids.net_salary')
    def _compute_totals(self):
        """Compute totals from lines"""
        for wps in self:
            wps.employee_count = len(wps.line_ids)
            wps.total_employees = len(wps.line_ids)  # Alias for compatibility
            wps.total_basic = sum(wps.line_ids.mapped('basic_salary'))
            wps.total_housing = sum(wps.line_ids.mapped('housing_allowance'))
            wps.total_transport = sum(wps.line_ids.mapped('transport_allowance'))
            wps.total_other = sum(wps.line_ids.mapped('other_allowance'))
            wps.total_overtime = sum(wps.line_ids.mapped('overtime'))
            wps.total_deductions = sum(wps.line_ids.mapped('deductions'))
            wps.total_leave = sum(wps.line_ids.mapped('leave_salary'))
            wps.total_net = sum(wps.line_ids.mapped('net_salary'))
            wps.total_salary = wps.total_net  # Alias for compatibility

    @api.model
    def create(self, vals):
        """Generate sequence on create"""
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.wps.file') or '/'
        return super().create(vals)

    def action_generate_lines(self):
        """Generate WPS lines from payslip batch"""
        for wps in self:
            if not wps.payslip_run_id:
                raise UserError(_('Please select a payslip batch.'))
            
            # Clear existing lines
            wps.line_ids.unlink()
            
            # Generate lines from payslips
            for payslip in wps.payslip_run_id.slip_ids.filtered(lambda p: p.state in ['done', 'paid']):
                employee = payslip.employee_id
                bank = payslip.bank_account_id
                
                if not bank:
                    _logger.warning('No bank account for employee %s', employee.name)
                    continue
                
                self.env['tazweed.wps.file.line'].create({
                    'wps_file_id': wps.id,
                    'employee_id': employee.id,
                    'payslip_id': payslip.id,
                    'employee_eid': getattr(employee, 'emirates_id', '') or '',
                    'labour_card_no': getattr(employee, 'labour_card_no', '') or '',
                    'bank_code': bank.bank_id.bic if bank.bank_id else '',
                    'account_number': bank.account_number or '',
                    'iban': bank.iban or '',
                    'basic_salary': payslip.basic_wage,
                    'housing_allowance': payslip.housing_allowance,
                    'transport_allowance': payslip.transport_allowance,
                    'other_allowance': payslip.other_allowances,
                    'overtime': payslip.overtime_amount,
                    'deductions': payslip.total_deductions,
                    'leave_salary': 0.0,  # Calculate if applicable
                    'net_salary': payslip.net_wage,
                })
        
        return True

    def action_generate_file(self):
        """Generate WPS SIF file"""
        for wps in self:
            if not wps.line_ids:
                raise UserError(_('Please generate WPS lines first.'))
            
            # Generate SIF content
            sif_content = wps._generate_sif_content()
            
            # Encode and save
            file_data = base64.b64encode(sif_content.encode('utf-8'))
            file_name = f"WPS_{wps.company_id.name}_{wps.period_month}_{wps.period_year}.SIF"
            
            wps.write({
                'file_data': file_data,
                'file_name': file_name,
                'state': 'generated',
            })
            
            # Update payslips
            wps.line_ids.mapped('payslip_id').write({
                'wps_file_id': wps.id,
                'wps_status': 'included',
            })
        
        return True

    def _generate_sif_content(self):
        """Generate SIF file content"""
        self.ensure_one()
        
        lines = []
        
        # Header Record (EDR - Employer Details Record)
        header = self._generate_header_record()
        lines.append(header)
        
        # Employee Records (SCR - Salary Credit Records)
        for line in self.line_ids:
            employee_record = self._generate_employee_record(line)
            lines.append(employee_record)
        
        return '\n'.join(lines)

    def _generate_header_record(self):
        """Generate EDR (Employer Details Record)"""
        # Format: EDR,EID,Bank Code,Account,Month,Year,Total Records,Total Amount
        return ','.join([
            'EDR',
            self.employer_eid or '',
            self.employer_bank_code or '',
            self.employer_account or '',
            self.period_month,
            self.period_year,
            str(self.employee_count),
            f'{self.total_net:.2f}',
        ])

    def _generate_employee_record(self, line):
        """Generate SCR (Salary Credit Record)"""
        # Format: SCR,EID,Labour Card,Bank Code,Account,IBAN,Basic,Housing,Transport,Other,OT,Deductions,Leave,Net
        return ','.join([
            'SCR',
            line.employee_eid or '',
            line.labour_card_no or '',
            line.bank_code or '',
            line.account_number or '',
            line.iban or '',
            f'{line.basic_salary:.2f}',
            f'{line.housing_allowance:.2f}',
            f'{line.transport_allowance:.2f}',
            f'{line.other_allowance:.2f}',
            f'{line.overtime:.2f}',
            f'{line.deductions:.2f}',
            f'{line.leave_salary:.2f}',
            f'{line.net_salary:.2f}',
        ])

    def action_submit(self):
        """Mark as submitted to bank"""
        self.write({
            'state': 'submitted',
            'submission_date': fields.Date.today(),
        })

    def action_mark_processed(self):
        """Mark as processed"""
        for wps in self:
            wps.line_ids.mapped('payslip_id').write({'wps_status': 'transferred'})
        
        self.write({
            'state': 'processed',
            'processing_date': fields.Date.today(),
        })

    def action_mark_failed(self):
        """Mark as failed"""
        for wps in self:
            wps.line_ids.mapped('payslip_id').write({'wps_status': 'failed'})
        
        self.write({'state': 'failed'})

    def action_cancel(self):
        """Cancel WPS file"""
        for wps in self:
            wps.line_ids.mapped('payslip_id').write({
                'wps_file_id': False,
                'wps_status': 'pending',
            })
        
        self.write({'state': 'cancelled'})


class WPSFileLine(models.Model):
    """WPS File Line"""
    _name = 'tazweed.wps.file.line'
    _description = 'WPS File Line'
    _order = 'wps_file_id, id'

    wps_file_id = fields.Many2one(
        'tazweed.wps.file',
        string='WPS File',
        required=True,
        ondelete='cascade',
    )
    
    # Employee
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
    )
    
    # Employee Details
    employee_eid = fields.Char(string='Emirates ID')
    labour_card_no = fields.Char(string='Labour Card No')
    
    # Bank Details
    bank_code = fields.Char(string='Bank Code')
    account_number = fields.Char(string='Account Number')
    bank_account = fields.Char(string='Bank Account', related='account_number', store=False)  # Alias for compatibility
    iban = fields.Char(string='IBAN')
    
    # Salary Components
    basic_salary = fields.Float(string='Basic Salary')
    housing_allowance = fields.Float(string='Housing Allowance')
    transport_allowance = fields.Float(string='Transport Allowance')
    other_allowance = fields.Float(string='Other Allowances')
    other_allowances = fields.Float(string='Other Allowances', related='other_allowance', store=False)  # Alias for compatibility
    overtime = fields.Float(string='Overtime')
    deductions = fields.Float(string='Deductions')
    leave_salary = fields.Float(string='Leave Salary')
    net_salary = fields.Float(string='Net Salary')
    
    # Days
    days_worked = fields.Integer(string='Days Worked', default=30)
    
    # Status
    status = fields.Selection([
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')
    
    error_message = fields.Text(string='Error Message')
    
    # Compatibility fields with tazweed_uae_compliance
    is_valid = fields.Boolean(string='Valid', default=True)
    validation_message = fields.Char(string='Validation Message')
    salary_date = fields.Date(string='Salary Date')
    period_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month')
    period_year = fields.Char(string='Year')
    total_employees = fields.Integer(string='Total Employees')
    employees_paid_wps = fields.Integer(string='Employees Paid via WPS')
    employees_not_paid = fields.Integer(string='Employees Not Paid')
    compliance_rate = fields.Float(string='Compliance Rate %')
    total_salary_due = fields.Float(string='Total Salary Due')
    total_salary_paid = fields.Float(string='Total Salary Paid')
    is_compliant = fields.Boolean(string='Compliant')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    name = fields.Char(string='Reference')
