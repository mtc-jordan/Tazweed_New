# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class Placement(models.Model):
    """Placement Record"""
    _name = 'tazweed.placement'
    _description = 'Placement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Placement No.',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Links
    client_id = fields.Many2one('tazweed.client', string='Client', required=True, tracking=True)
    candidate_id = fields.Many2one('tazweed.candidate', string='Candidate', required=True, tracking=True)
    job_order_id = fields.Many2one('tazweed.job.order', string='Job Order')
    employee_id = fields.Many2one('hr.employee', string='Employee Record')
    
    # Position
    job_title = fields.Char(string='Job Title', required=True)
    department = fields.Char(string='Department')
    work_location = fields.Char(string='Work Location')
    
    # Contract
    date_start = fields.Date(string='Start Date', required=True, tracking=True)
    date_end = fields.Date(string='End Date')
    contract_duration = fields.Integer(string='Duration (Months)')
    
    contract_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary'),
        ('contract', 'Contract'),
        ('project', 'Project Based'),
    ], string='Contract Type', default='permanent')
    
    # Compensation
    basic_salary = fields.Float(string='Basic Salary', tracking=True)
    housing_allowance = fields.Float(string='Housing Allowance')
    transport_allowance = fields.Float(string='Transport Allowance')
    food_allowance = fields.Float(string='Food Allowance')
    other_allowances = fields.Float(string='Other Allowances')
    total_salary = fields.Float(string='Total Salary', compute='_compute_totals', store=True)
    
    # Billing
    bill_rate = fields.Float(string='Bill Rate')
    markup_pct = fields.Float(string='Markup %')
    total_billing = fields.Float(string='Total Billing', compute='_compute_totals', store=True)
    
    # Commission
    commission_pct = fields.Float(string='Commission %')
    commission_amount = fields.Float(string='Commission Amount', compute='_compute_totals', store=True)
    
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    # Deployment
    deployment_ids = fields.One2many('tazweed.deployment', 'placement_id', string='Deployments')
    current_deployment_id = fields.Many2one('tazweed.deployment', string='Current Deployment', compute='_compute_deployment')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    termination_reason = fields.Selection([
        ('contract_end', 'Contract End'),
        ('resignation', 'Resignation'),
        ('client_request', 'Client Request'),
        ('performance', 'Performance Issues'),
        ('absconding', 'Absconding'),
        ('other', 'Other'),
    ], string='Termination Reason')
    
    termination_date = fields.Date(string='Termination Date')
    termination_notes = fields.Text(string='Termination Notes')
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.placement') or _('New')
        return super().create(vals)

    @api.depends('basic_salary', 'housing_allowance', 'transport_allowance', 'food_allowance', 
                 'other_allowances', 'bill_rate', 'markup_pct', 'commission_pct')
    def _compute_totals(self):
        for rec in self:
            rec.total_salary = (rec.basic_salary + rec.housing_allowance + 
                               rec.transport_allowance + rec.food_allowance + rec.other_allowances)
            if rec.bill_rate:
                rec.total_billing = rec.bill_rate
            else:
                rec.total_billing = rec.total_salary * (1 + rec.markup_pct / 100)
            rec.commission_amount = rec.total_billing * rec.commission_pct / 100

    def _compute_deployment(self):
        for rec in self:
            active = rec.deployment_ids.filtered(lambda d: d.state == 'active')
            rec.current_deployment_id = active[0] if active else False

    def action_submit(self):
        self.write({'state': 'pending'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_activate(self):
        self.write({'state': 'active'})
        # Update candidate status
        self.candidate_id.write({'state': 'placed'})

    def action_complete(self):
        self.write({'state': 'completed', 'termination_reason': 'contract_end', 'termination_date': date.today()})

    def action_terminate(self):
        self.write({'state': 'terminated', 'termination_date': date.today()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_create_employee(self):
        """Create employee record from placement"""
        self.ensure_one()
        if self.employee_id:
            raise ValidationError(_('Employee already exists for this placement.'))
        
        employee = self.env['hr.employee'].create({
            'name': self.candidate_id.name,
            'gender': self.candidate_id.gender,
            'birthday': self.candidate_id.date_of_birth,
            'country_id': self.candidate_id.nationality_id.id,
            'work_email': self.candidate_id.email,
            'work_phone': self.candidate_id.phone,
            'mobile_phone': self.candidate_id.mobile,
            'job_title': self.job_title,
        })
        self.employee_id = employee
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'res_id': employee.id,
            'view_mode': 'form',
        }


class Deployment(models.Model):
    """Worker Deployment"""
    _name = 'tazweed.deployment'
    _description = 'Deployment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(string='Deployment No.', copy=False, readonly=True, default=lambda self: _('New'))
    
    placement_id = fields.Many2one('tazweed.placement', string='Placement', required=True, ondelete='cascade')
    client_id = fields.Many2one(related='placement_id.client_id', store=True)
    candidate_id = fields.Many2one(related='placement_id.candidate_id', store=True)
    
    # Site
    site_name = fields.Char(string='Site Name')
    site_location = fields.Char(string='Site Location')
    site_supervisor = fields.Char(string='Site Supervisor')
    site_contact = fields.Char(string='Site Contact')
    
    # Duration
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date')
    
    # Schedule
    work_schedule = fields.Selection([
        ('regular', 'Regular (8 hours)'),
        ('shift', 'Shift Work'),
        ('rotational', 'Rotational'),
    ], string='Work Schedule', default='regular')
    
    shift_pattern = fields.Char(string='Shift Pattern')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.deployment') or _('New')
        return super().create(vals)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_complete(self):
        self.write({'state': 'completed', 'date_end': date.today()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
