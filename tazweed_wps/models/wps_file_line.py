# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class WPSFileLine(models.Model):
    """WPS File Employee Line"""
    _name = 'tazweed.wps.file.line'
    _description = 'WPS File Line'
    _order = 'employee_id'

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
    employee_name = fields.Char(
        string='Employee Name',
        related='employee_id.name',
        store=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
    )
    
    # Employee Identification
    employee_eid = fields.Char(
        string='Emirates ID',
        help='Employee Emirates ID (15 digits)',
    )
    labour_card_no = fields.Char(
        string='Labour Card No.',
        help='Employee Labour Card Number',
    )
    mol_id = fields.Char(
        string='MOL ID',
        help='Ministry of Labour ID',
    )
    
    # Bank Details
    bank_id = fields.Many2one(
        'tazweed.wps.bank',
        string='Bank',
    )
    bank_code = fields.Char(
        string='Bank Routing Code',
    )
    account_number = fields.Char(
        string='Account Number',
    )
    iban = fields.Char(
        string='IBAN',
    )
    
    # Salary Components
    basic_salary = fields.Float(
        string='Basic Salary',
        digits=(16, 2),
    )
    housing_allowance = fields.Float(
        string='Housing Allowance',
        digits=(16, 2),
    )
    transport_allowance = fields.Float(
        string='Transport Allowance',
        digits=(16, 2),
    )
    other_allowance = fields.Float(
        string='Other Allowances',
        digits=(16, 2),
    )
    overtime = fields.Float(
        string='Overtime',
        digits=(16, 2),
    )
    leave_salary = fields.Float(
        string='Leave Salary',
        digits=(16, 2),
    )
    deductions = fields.Float(
        string='Deductions',
        digits=(16, 2),
    )
    
    # Computed
    gross_salary = fields.Float(
        string='Gross Salary',
        compute='_compute_salary',
        store=True,
        digits=(16, 2),
    )
    net_salary = fields.Float(
        string='Net Salary',
        compute='_compute_salary',
        store=True,
        digits=(16, 2),
    )
    
    # Days
    days_worked = fields.Integer(
        string='Days Worked',
        default=30,
    )
    
    # Validation
    is_valid = fields.Boolean(
        string='Valid',
        compute='_compute_validation',
        store=True,
    )
    validation_message = fields.Char(
        string='Validation Message',
        compute='_compute_validation',
        store=True,
    )
    
    # Status
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ], string='Payment Status', default='pending')
    
    # Payslip link (optional, for payroll integration)
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
    )

    @api.depends('basic_salary', 'housing_allowance', 'transport_allowance', 
                 'other_allowance', 'overtime', 'leave_salary', 'deductions')
    def _compute_salary(self):
        for line in self:
            line.gross_salary = (
                line.basic_salary + 
                line.housing_allowance + 
                line.transport_allowance + 
                line.other_allowance + 
                line.overtime + 
                line.leave_salary
            )
            line.net_salary = line.gross_salary - line.deductions

    @api.depends('employee_eid', 'labour_card_no', 'bank_code', 'account_number', 'net_salary')
    def _compute_validation(self):
        for line in self:
            errors = []
            
            # Check employee identification
            if not line.employee_eid and not line.labour_card_no:
                errors.append(_('Missing Emirates ID or Labour Card'))
            
            # Check bank details
            if not line.bank_code:
                errors.append(_('Missing bank routing code'))
            if not line.account_number and not line.iban:
                errors.append(_('Missing bank account number'))
            
            # Check salary
            if line.net_salary <= 0:
                errors.append(_('Net salary must be positive'))
            
            line.is_valid = len(errors) == 0
            line.validation_message = ', '.join(errors) if errors else ''

    @api.onchange('employee_id')
    def _onchange_employee(self):
        """Auto-fill employee details"""
        if self.employee_id:
            emp = self.employee_id
            
            # Employee ID
            self.employee_eid = getattr(emp, 'emirates_id', '') or ''
            self.labour_card_no = getattr(emp, 'labour_card_no', '') or ''
            self.mol_id = getattr(emp, 'mol_id', '') or ''
            
            # Bank details
            if hasattr(emp, 'bank_account_id') and emp.bank_account_id:
                bank_acc = emp.bank_account_id
                self.account_number = bank_acc.acc_number
                self.iban = getattr(bank_acc, 'iban', '') or ''
                
                if bank_acc.bank_id:
                    # Try to find WPS bank
                    wps_bank = self.env['tazweed.wps.bank'].search([
                        ('swift_code', '=', bank_acc.bank_id.bic)
                    ], limit=1)
                    if wps_bank:
                        self.bank_id = wps_bank.id
                        self.bank_code = wps_bank.routing_code
                    else:
                        self.bank_code = bank_acc.bank_id.bic
            
            # Salary from contract
            if emp.contract_id:
                contract = emp.contract_id
                self.basic_salary = contract.wage
                self.housing_allowance = getattr(contract, 'housing_allowance', 0) or 0
                self.transport_allowance = getattr(contract, 'transport_allowance', 0) or 0
                self.other_allowance = getattr(contract, 'other_allowance', 0) or 0

    @api.onchange('bank_id')
    def _onchange_bank(self):
        """Update bank code when bank is selected"""
        if self.bank_id:
            self.bank_code = self.bank_id.routing_code

    def action_mark_paid(self):
        """Mark line as paid"""
        self.write({'payment_status': 'paid'})

    def action_mark_failed(self):
        """Mark line as failed"""
        self.write({'payment_status': 'failed'})
