# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class PayrollLoan(models.Model):
    """Employee Loan Management"""
    _name = 'tazweed.payroll.loan'
    _description = 'Employee Loan'
    _order = 'request_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default='/',
        copy=False,
    )
    
    # Employee
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
    )
    
    # Loan Details
    loan_type = fields.Selection([
        ('personal', 'Personal Loan'),
        ('salary_advance', 'Salary Advance'),
        ('emergency', 'Emergency Loan'),
        ('housing', 'Housing Loan'),
        ('education', 'Education Loan'),
        ('medical', 'Medical Loan'),
        ('other', 'Other'),
    ], string='Loan Type', required=True, default='personal', tracking=True)
    
    loan_amount = fields.Float(
        string='Loan Amount',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True,
    )
    
    interest_rate = fields.Float(
        string='Interest Rate (%)',
        default=0.0,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
    )
    
    # Installments
    installment_count = fields.Integer(
        string='Number of Installments',
        required=True,
        default=12,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    installment_amount = fields.Float(
        string='Installment Amount',
        compute='_compute_installment_amount',
        store=True,
    )
    
    # Dates
    request_date = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.today,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    approval_date = fields.Date(
        string='Approval Date',
        readonly=True,
    )
    disbursement_date = fields.Date(
        string='Disbursement Date',
        readonly=True,
    )
    start_date = fields.Date(
        string='Deduction Start Date',
        readonly=True,
        states={'draft': [('readonly', False)], 'approved': [('readonly', False)]},
    )
    end_date = fields.Date(
        string='Expected End Date',
        compute='_compute_end_date',
        store=True,
    )
    
    # Payment Tracking
    paid_amount = fields.Float(
        string='Paid Amount',
        compute='_compute_paid_amount',
        store=True,
    )
    balance_amount = fields.Float(
        string='Balance Amount',
        compute='_compute_balance_amount',
        store=True,
    )
    
    # Installment Lines
    installment_ids = fields.One2many(
        'tazweed.payroll.loan.installment',
        'loan_id',
        string='Installments',
        readonly=True,
    )
    
    # Approval
    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
    )
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('disbursed', 'Disbursed'),
        ('active', 'Active'),
        ('paid', 'Fully Paid'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Reason
    reason = fields.Text(
        string='Loan Reason',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    
    # Notes
    notes = fields.Text(string='Notes')

    @api.depends('loan_amount', 'interest_rate')
    def _compute_total_amount(self):
        """Compute total amount with interest"""
        for loan in self:
            interest = loan.loan_amount * loan.interest_rate / 100
            loan.total_amount = loan.loan_amount + interest

    @api.depends('total_amount', 'installment_count')
    def _compute_installment_amount(self):
        """Compute monthly installment amount"""
        for loan in self:
            if loan.installment_count:
                loan.installment_amount = loan.total_amount / loan.installment_count
            else:
                loan.installment_amount = 0.0

    @api.depends('start_date', 'installment_count')
    def _compute_end_date(self):
        """Compute expected end date"""
        for loan in self:
            if loan.start_date and loan.installment_count:
                loan.end_date = loan.start_date + relativedelta(months=loan.installment_count)
            else:
                loan.end_date = False

    @api.depends('installment_ids.state')
    def _compute_paid_amount(self):
        """Compute total paid amount"""
        for loan in self:
            paid_installments = loan.installment_ids.filtered(lambda i: i.state == 'paid')
            loan.paid_amount = sum(paid_installments.mapped('amount'))

    @api.depends('total_amount', 'paid_amount')
    def _compute_balance_amount(self):
        """Compute balance amount"""
        for loan in self:
            loan.balance_amount = loan.total_amount - loan.paid_amount

    @api.model
    def create(self, vals):
        """Generate sequence on create"""
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.payroll.loan') or '/'
        return super().create(vals)

    @api.constrains('loan_amount')
    def _check_loan_amount(self):
        """Validate loan amount"""
        for loan in self:
            if loan.loan_amount <= 0:
                raise ValidationError(_('Loan amount must be greater than zero.'))

    @api.constrains('installment_count')
    def _check_installment_count(self):
        """Validate installment count"""
        for loan in self:
            if loan.installment_count <= 0:
                raise ValidationError(_('Number of installments must be greater than zero.'))

    def action_submit(self):
        """Submit loan for approval"""
        self.write({'state': 'submitted'})

    def action_approve(self):
        """Approve loan"""
        self.write({
            'state': 'approved',
            'approval_date': fields.Date.today(),
            'approved_by_id': self.env.user.id,
        })

    def action_reject(self):
        """Open rejection wizard"""
        return {
            'name': _('Reject Loan'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'tazweed.payroll.loan',
                'default_res_id': self.id,
            },
        }

    def action_disburse(self):
        """Disburse loan and generate installments"""
        for loan in self:
            if not loan.start_date:
                loan.start_date = date.today().replace(day=1) + relativedelta(months=1)
            
            # Generate installments
            loan._generate_installments()
            
            loan.write({
                'state': 'disbursed',
                'disbursement_date': fields.Date.today(),
            })

    def action_activate(self):
        """Activate loan (start deductions)"""
        self.write({'state': 'active'})

    def action_cancel(self):
        """Cancel loan"""
        self.write({'state': 'cancelled'})

    def action_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def _generate_installments(self):
        """Generate installment schedule"""
        self.ensure_one()
        
        # Clear existing installments
        self.installment_ids.unlink()
        
        # Generate new installments
        installment_date = self.start_date
        for i in range(self.installment_count):
            self.env['tazweed.payroll.loan.installment'].create({
                'loan_id': self.id,
                'sequence': i + 1,
                'due_date': installment_date,
                'amount': self.installment_amount,
            })
            installment_date = installment_date + relativedelta(months=1)


class PayrollLoanInstallment(models.Model):
    """Loan Installment"""
    _name = 'tazweed.payroll.loan.installment'
    _description = 'Loan Installment'
    _order = 'loan_id, sequence'

    loan_id = fields.Many2one(
        'tazweed.payroll.loan',
        string='Loan',
        required=True,
        ondelete='cascade',
    )
    
    sequence = fields.Integer(
        string='Installment #',
        required=True,
    )
    
    due_date = fields.Date(
        string='Due Date',
        required=True,
    )
    
    amount = fields.Float(
        string='Amount',
        required=True,
    )
    
    paid_date = fields.Date(
        string='Paid Date',
        readonly=True,
    )
    
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        readonly=True,
    )
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending', required=True)

    def action_mark_paid(self):
        """Mark installment as paid"""
        self.write({
            'state': 'paid',
            'paid_date': fields.Date.today(),
        })
        
        # Check if loan is fully paid
        loan = self.loan_id
        pending = loan.installment_ids.filtered(lambda i: i.state == 'pending')
        if not pending:
            loan.write({'state': 'paid'})
