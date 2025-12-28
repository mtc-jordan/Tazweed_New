# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class Placement(models.Model):
    """Placement Record - When candidate is placed with client"""
    _name = 'tazweed.placement'
    _description = 'Placement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Placement Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Core Relations
    candidate_id = fields.Many2one('tazweed.candidate', string='Candidate', required=True, tracking=True)
    client_id = fields.Many2one('tazweed.client', string='Client', required=True, tracking=True)
    job_order_id = fields.Many2one('tazweed.job.order', string='Job Order', required=True)
    pipeline_id = fields.Many2one('tazweed.recruitment.pipeline', string='Pipeline Record')
    
    # Employee Link
    employee_id = fields.Many2one('hr.employee', string='Employee Record')
    
    # Job Details
    job_title = fields.Char(string='Job Title', required=True)
    department = fields.Char(string='Department')
    work_location = fields.Char(string='Work Location')
    
    # Placement Type
    placement_type = fields.Selection([
        ('permanent', 'Permanent Placement'),
        ('contract', 'Contract'),
        ('temp_to_perm', 'Temp to Perm'),
        ('outsourcing', 'Outsourcing'),
    ], string='Placement Type', required=True, default='contract', tracking=True)
    
    # Dates
    date_placed = fields.Date(string='Placement Date', default=fields.Date.today, required=True)
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date')
    
    contract_duration = fields.Integer(string='Contract Duration (Months)')
    probation_period = fields.Integer(string='Probation Period (Days)', default=90)
    probation_end_date = fields.Date(string='Probation End Date', compute='_compute_probation_end')
    
    # Compensation - Candidate
    salary = fields.Float(string='Salary', required=True)
    salary_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('annual', 'Annual'),
    ], string='Salary Type', default='monthly')
    
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    housing_allowance = fields.Float(string='Housing Allowance')
    transport_allowance = fields.Float(string='Transport Allowance')
    other_allowances = fields.Float(string='Other Allowances')
    total_package = fields.Float(string='Total Package', compute='_compute_total_package', store=True)
    
    # Billing - Client
    bill_rate = fields.Float(string='Bill Rate')
    bill_rate_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
    ], string='Bill Rate Type', default='monthly')
    
    markup_pct = fields.Float(string='Markup %')
    margin = fields.Float(string='Margin', compute='_compute_margin', store=True)
    margin_pct = fields.Float(string='Margin %', compute='_compute_margin', store=True)
    
    # Fees
    placement_fee = fields.Float(string='Placement Fee')
    placement_fee_pct = fields.Float(string='Placement Fee %')
    fee_paid = fields.Boolean(string='Fee Paid')
    fee_paid_date = fields.Date(string='Fee Paid Date')
    
    # Invoicing
    invoice_ids = fields.One2many('tazweed.placement.invoice', 'placement_id', string='Invoices')
    total_invoiced = fields.Float(string='Total Invoiced', compute='_compute_invoiced')
    total_paid = fields.Float(string='Total Paid', compute='_compute_invoiced')
    total_billing = fields.Float(string='Total Billing', compute='_compute_total_billing')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Start'),
        ('probation', 'Probation'),
        ('active', 'Active'),
        ('extended', 'Extended'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Termination
    termination_date = fields.Date(string='Termination Date')
    termination_reason = fields.Selection([
        ('contract_end', 'Contract End'),
        ('resignation', 'Resignation'),
        ('termination', 'Termination'),
        ('client_request', 'Client Request'),
        ('performance', 'Performance Issues'),
        ('other', 'Other'),
    ], string='Termination Reason')
    termination_notes = fields.Text(string='Termination Notes')
    
    # Replacement
    replacement_required = fields.Boolean(string='Replacement Required')
    replacement_deadline = fields.Date(string='Replacement Deadline')
    replacement_pipeline_id = fields.Many2one('tazweed.recruitment.pipeline', string='Replacement Pipeline')
    
    # Documents
    offer_letter = fields.Binary(string='Offer Letter')
    offer_letter_name = fields.Char(string='Offer Letter Filename')
    contract_document = fields.Binary(string='Contract Document')
    contract_document_name = fields.Char(string='Contract Filename')
    
    # Assignment
    account_manager_id = fields.Many2one('res.users', string='Account Manager')
    recruiter_id = fields.Many2one('res.users', string='Recruiter')
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Placement reference must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.placement') or _('New')
        
        result = super().create(vals)
        
        # Update candidate state
        result.candidate_id.write({'state': 'placed'})
        
        # Update pipeline if linked
        if result.pipeline_id:
            result.pipeline_id.write({
                'result': 'hired',
                'placement_id': result.id,
            })
        
        return result

    @api.depends('date_start', 'probation_period')
    def _compute_probation_end(self):
        for placement in self:
            if placement.date_start and placement.probation_period:
                placement.probation_end_date = placement.date_start + relativedelta(days=placement.probation_period)
            else:
                placement.probation_end_date = False

    @api.depends('salary', 'housing_allowance', 'transport_allowance', 'other_allowances')
    def _compute_total_package(self):
        for placement in self:
            placement.total_package = (
                placement.salary +
                placement.housing_allowance +
                placement.transport_allowance +
                placement.other_allowances
            )

    @api.depends('bill_rate', 'total_package')
    def _compute_margin(self):
        for placement in self:
            if placement.bill_rate and placement.total_package:
                placement.margin = placement.bill_rate - placement.total_package
                placement.margin_pct = (placement.margin / placement.bill_rate) * 100 if placement.bill_rate else 0
            else:
                placement.margin = 0
                placement.margin_pct = 0

    def _compute_invoiced(self):
        for placement in self:
            invoices = placement.invoice_ids
            placement.total_invoiced = sum(inv.amount for inv in invoices)
            placement.total_paid = sum(inv.amount for inv in invoices.filtered(lambda i: i.state == 'paid'))

    @api.depends('date_start', 'date_end', 'bill_rate', 'state')
    def _compute_total_billing(self):
        """Calculate total billing based on duration and rate"""
        for placement in self:
            if placement.bill_rate and placement.date_start:
                end_date = placement.date_end or date.today()
                if placement.state in ('active', 'completed', 'extended'):
                    months = relativedelta(end_date, placement.date_start).months + 1
                    placement.total_billing = placement.bill_rate * months
                else:
                    placement.total_billing = 0
            else:
                placement.total_billing = 0

    def action_confirm(self):
        """Confirm placement and move to pending start"""
        self.write({'state': 'pending'})

    def action_start(self):
        """Start placement - candidate begins work"""
        self.write({'state': 'probation'})

    def action_pass_probation(self):
        """Pass probation period"""
        self.write({'state': 'active'})

    def action_extend(self):
        """Extend contract"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Extend Contract'),
            'res_model': 'tazweed.extend.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_placement_id': self.id},
        }

    def action_complete(self):
        """Complete placement (contract ended normally)"""
        self.write({
            'state': 'completed',
            'termination_date': fields.Date.today(),
            'termination_reason': 'contract_end',
        })

    def action_terminate(self):
        """Terminate placement early"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Terminate Placement'),
            'res_model': 'tazweed.terminate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_placement_id': self.id},
        }

    def action_cancel(self):
        """Cancel placement before start"""
        self.write({'state': 'cancelled'})

    def action_create_employee(self):
        """Create employee record from placement"""
        self.ensure_one()
        
        employee_vals = {
            'name': self.candidate_id.name,
            'job_title': self.job_title,
            'department_id': False,  # Would need to map
            'work_email': self.candidate_id.email,
            'mobile_phone': self.candidate_id.mobile,
            'gender': self.candidate_id.gender,
            'birthday': self.candidate_id.date_of_birth,
            'country_id': self.candidate_id.nationality_id.id,
            'marital': self.candidate_id.marital_status,
        }
        
        employee = self.env['hr.employee'].create(employee_vals)
        self.write({'employee_id': employee.id})
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee'),
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': employee.id,
        }

    def action_view_invoices(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoices'),
            'res_model': 'tazweed.placement.invoice',
            'view_mode': 'tree,form',
            'domain': [('placement_id', '=', self.id)],
            'context': {'default_placement_id': self.id},
        }

    def action_create_invoice(self):
        """Create new invoice for this placement"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Invoice'),
            'res_model': 'tazweed.placement.invoice',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_placement_id': self.id,
                'default_client_id': self.client_id.id,
            },
        }
