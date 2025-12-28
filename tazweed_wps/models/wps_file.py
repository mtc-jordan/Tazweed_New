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
    
    # Period
    period_month = fields.Selection([
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True, tracking=True)
    
    period_year = fields.Char(
        string='Year',
        required=True,
        default=lambda self: str(date.today().year),
    )
    
    period_display = fields.Char(
        string='Period',
        compute='_compute_period_display',
        store=True,
    )
    
    # Employer Details
    employer_eid = fields.Char(
        string='Employer Emirates ID',
        required=True,
        help='Employer Emirates ID (15 digits)',
    )
    employer_bank_id = fields.Many2one(
        'tazweed.wps.bank',
        string='Employer Bank',
        help='Select employer bank for WPS',
    )
    employer_bank_code = fields.Char(
        string='Employer Bank Code',
        related='employer_bank_id.routing_code',
        store=True,
        readonly=False,
    )
    employer_account = fields.Char(
        string='Employer Account',
        required=True,
        help='Employer Bank Account Number (IBAN)',
    )
    
    # Salary Date
    salary_date = fields.Date(
        string='Salary Date',
        required=True,
        default=fields.Date.today,
        help='Date when salaries are paid',
    )
    
    # File Type
    file_type = fields.Selection([
        ('sif', 'SIF (Salary Information File)'),
        ('non_sif', 'Non-SIF'),
    ], string='File Type', default='sif', required=True)
    
    # Lines
    line_ids = fields.One2many(
        'tazweed.wps.file.line',
        'wps_file_id',
        string='Employee Lines',
    )
    
    # Counts and Totals
    employee_count = fields.Integer(
        string='Employee Count',
        compute='_compute_totals',
        store=True,
    )
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
        string='Total Leave Salary',
        compute='_compute_totals',
        store=True,
    )
    total_net = fields.Float(
        string='Total Net Salary',
        compute='_compute_totals',
        store=True,
    )
    
    # Generated File
    sif_file = fields.Binary(
        string='SIF File',
        readonly=True,
    )
    sif_filename = fields.Char(
        string='SIF Filename',
        readonly=True,
    )
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('submitted', 'Submitted to Bank'),
        ('processed', 'Processed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Submission Details
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
    rejection_reason = fields.Text(
        string='Rejection Reason',
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    
    notes = fields.Text(string='Notes')

    @api.depends('period_month', 'period_year')
    def _compute_period_display(self):
        for rec in self:
            month_name = dict(rec._fields['period_month'].selection).get(rec.period_month, '')
            rec.period_display = f'{month_name} {rec.period_year}'

    @api.depends('line_ids.basic_salary', 'line_ids.housing_allowance', 
                 'line_ids.transport_allowance', 'line_ids.other_allowance',
                 'line_ids.overtime', 'line_ids.deductions', 'line_ids.leave_salary',
                 'line_ids.net_salary')
    def _compute_totals(self):
        for wps in self:
            wps.employee_count = len(wps.line_ids)
            wps.total_basic = sum(wps.line_ids.mapped('basic_salary'))
            wps.total_housing = sum(wps.line_ids.mapped('housing_allowance'))
            wps.total_transport = sum(wps.line_ids.mapped('transport_allowance'))
            wps.total_other = sum(wps.line_ids.mapped('other_allowance'))
            wps.total_overtime = sum(wps.line_ids.mapped('overtime'))
            wps.total_deductions = sum(wps.line_ids.mapped('deductions'))
            wps.total_leave = sum(wps.line_ids.mapped('leave_salary'))
            wps.total_net = sum(wps.line_ids.mapped('net_salary'))

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.wps.file') or '/'
        return super().create(vals)

    def action_generate_lines(self):
        """Generate WPS lines from employees with contracts"""
        for wps in self:
            # Clear existing lines
            wps.line_ids.unlink()
            
            # Get employees with active contracts
            employees = self.env['hr.employee'].search([
                ('company_id', '=', wps.company_id.id),
                ('contract_id', '!=', False),
                ('contract_id.state', '=', 'open'),
            ])
            
            if not employees:
                raise UserError(_('No employees with active contracts found.'))
            
            lines = []
            for emp in employees:
                # Get bank account
                bank_account = emp.bank_account_id if hasattr(emp, 'bank_account_id') else False
                
                # Get WPS bank
                wps_bank = False
                if bank_account and bank_account.bank_id:
                    wps_bank = self.env['tazweed.wps.bank'].search([
                        ('swift_code', '=', bank_account.bank_id.bic)
                    ], limit=1)
                
                contract = emp.contract_id
                
                lines.append({
                    'wps_file_id': wps.id,
                    'employee_id': emp.id,
                    'employee_eid': getattr(emp, 'emirates_id', '') or '',
                    'labour_card_no': getattr(emp, 'labour_card_no', '') or '',
                    'bank_id': wps_bank.id if wps_bank else False,
                    'bank_code': wps_bank.routing_code if wps_bank else (bank_account.bank_id.bic if bank_account and bank_account.bank_id else ''),
                    'account_number': bank_account.acc_number if bank_account else '',
                    'iban': getattr(bank_account, 'iban', '') if bank_account else '',
                    'basic_salary': contract.wage if contract else 0,
                    'housing_allowance': getattr(contract, 'housing_allowance', 0) or 0,
                    'transport_allowance': getattr(contract, 'transport_allowance', 0) or 0,
                    'other_allowance': getattr(contract, 'other_allowance', 0) or 0,
                    'overtime': 0,
                    'deductions': 0,
                    'leave_salary': 0,
                })
            
            self.env['tazweed.wps.file.line'].create(lines)
        
        return True

    def action_generate_sif(self):
        """Generate SIF file"""
        for wps in self:
            if not wps.line_ids:
                raise UserError(_('Please generate employee lines first.'))
            
            # Validate lines
            invalid_lines = wps.line_ids.filtered(lambda l: not l.is_valid)
            if invalid_lines:
                raise UserError(_('Some employee lines have validation errors. Please fix them before generating SIF.'))
            
            # Generate SIF content
            sif_content = wps._generate_sif_content()
            
            # Encode and save
            wps.sif_file = base64.b64encode(sif_content.encode('utf-8'))
            wps.sif_filename = f'WPS_{wps.employer_eid}_{wps.period_year}{wps.period_month}.SIF'
            wps.state = 'generated'
            
            wps.message_post(body=_('SIF file generated successfully.'))
        
        return True

    def _generate_sif_content(self):
        """Generate SIF file content according to UAE WPS format"""
        self.ensure_one()
        lines = []
        
        # Header Record (EDR - Employer Details Record)
        header = self._generate_header_record()
        lines.append(header)
        
        # Employee Records (SDR - Salary Details Record)
        for line in self.line_ids:
            sdr = self._generate_employee_record(line)
            lines.append(sdr)
        
        return '\n'.join(lines)

    def _generate_header_record(self):
        """Generate EDR (Employer Details Record)"""
        self.ensure_one()
        
        # EDR Format:
        # Field 1: Record Type (3) - "EDR"
        # Field 2: Employer EID (15)
        # Field 3: Employer Bank Routing Code (9)
        # Field 4: Employer Bank Account (34)
        # Field 5: Salary Month (2)
        # Field 6: Salary Year (4)
        # Field 7: Total Records (6)
        # Field 8: Total Salary (15) - in fils (x100)
        # Field 9: Currency (3) - "AED"
        
        edr = 'EDR'
        edr += (self.employer_eid or '').ljust(15)[:15]
        edr += (self.employer_bank_code or '').ljust(9)[:9]
        edr += (self.employer_account or '').ljust(34)[:34]
        edr += self.period_month
        edr += self.period_year[:4]
        edr += str(len(self.line_ids)).zfill(6)
        edr += str(int(self.total_net * 100)).zfill(15)
        edr += 'AED'
        
        return edr

    def _generate_employee_record(self, line):
        """Generate SDR (Salary Details Record)"""
        
        # SDR Format:
        # Field 1: Record Type (3) - "SDR"
        # Field 2: Employee EID (15)
        # Field 3: Employee Bank Routing Code (9)
        # Field 4: Employee Bank Account (34)
        # Field 5: Salary Date (8) - YYYYMMDD
        # Field 6: Salary Frequency (1) - M=Monthly
        # Field 7: Number of Days (2)
        # Field 8: Net Salary (15) - in fils
        # Field 9: Basic Salary (15) - in fils
        # Field 10: Housing Allowance (15) - in fils
        # Field 11: Other Allowance (15) - in fils
        # Field 12: Deductions (15) - in fils
        # Field 13: Currency (3) - "AED"
        
        sdr = 'SDR'
        sdr += (line.employee_eid or line.labour_card_no or '').ljust(15)[:15]
        sdr += (line.bank_code or '').ljust(9)[:9]
        sdr += (line.account_number or line.iban or '').ljust(34)[:34]
        sdr += self.salary_date.strftime('%Y%m%d')
        sdr += 'M'  # Monthly
        sdr += str(line.days_worked or 30).zfill(2)
        sdr += str(int(line.net_salary * 100)).zfill(15)
        sdr += str(int(line.basic_salary * 100)).zfill(15)
        sdr += str(int(line.housing_allowance * 100)).zfill(15)
        sdr += str(int((line.transport_allowance + line.other_allowance + line.overtime + line.leave_salary) * 100)).zfill(15)
        sdr += str(int(line.deductions * 100)).zfill(15)
        sdr += 'AED'
        
        return sdr

    def action_submit(self):
        """Submit WPS file to bank"""
        for wps in self:
            if wps.state != 'generated':
                raise UserError(_('Only generated files can be submitted.'))
            
            wps.write({
                'state': 'submitted',
                'submission_date': date.today(),
            })
            wps.message_post(body=_('WPS file submitted to bank.'))
        
        return True

    def action_process(self):
        """Mark WPS file as processed"""
        for wps in self:
            if wps.state != 'submitted':
                raise UserError(_('Only submitted files can be marked as processed.'))
            
            wps.write({
                'state': 'processed',
                'processing_date': date.today(),
            })
            wps.message_post(body=_('WPS file processed successfully.'))
            
            # Create compliance record
            self.env['tazweed.wps.compliance'].create({
                'period_month': wps.period_month,
                'period_year': wps.period_year,
                'wps_file_id': wps.id,
                'total_employees': wps.employee_count,
                'employees_paid_wps': wps.employee_count,
                'employees_not_paid': 0,
                'total_salary_due': wps.total_net,
                'total_salary_paid': wps.total_net,
                'company_id': wps.company_id.id,
            })
        
        return True

    def action_reject(self):
        """Mark WPS file as rejected"""
        for wps in self:
            if wps.state != 'submitted':
                raise UserError(_('Only submitted files can be rejected.'))
            
            wps.write({'state': 'rejected'})
            wps.message_post(body=_('WPS file rejected by bank.'))
        
        return True

    def action_cancel(self):
        """Cancel WPS file"""
        for wps in self:
            if wps.state == 'processed':
                raise UserError(_('Processed files cannot be cancelled.'))
            
            wps.write({'state': 'cancelled'})
            wps.message_post(body=_('WPS file cancelled.'))
        
        return True

    def action_reset_draft(self):
        """Reset to draft"""
        for wps in self:
            if wps.state not in ['cancelled', 'rejected']:
                raise UserError(_('Only cancelled or rejected files can be reset to draft.'))
            
            wps.write({
                'state': 'draft',
                'sif_file': False,
                'sif_filename': False,
            })
            wps.message_post(body=_('WPS file reset to draft.'))
        
        return True

    def action_download_sif(self):
        """Download SIF file"""
        self.ensure_one()
        if not self.sif_file:
            raise UserError(_('No SIF file generated.'))
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=tazweed.wps.file&id={self.id}&field=sif_file&filename={self.sif_filename}&download=true',
            'target': 'new',
        }
