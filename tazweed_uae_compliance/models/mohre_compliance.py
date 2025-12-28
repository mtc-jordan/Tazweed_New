# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, timedelta


class MOHREEstablishment(models.Model):
    """MOHRE Establishment Registration"""
    _name = 'tazweed.mohre.establishment'
    _description = 'MOHRE Establishment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Establishment Name', required=True)
    
    # Registration
    establishment_id = fields.Char(string='Establishment ID', required=True)
    mol_id = fields.Char(string='MOL ID')
    
    # License
    trade_license = fields.Char(string='Trade License No.')
    trade_license_expiry = fields.Date(string='Trade License Expiry')
    
    # Classification
    activity_type = fields.Selection([
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('professional', 'Professional'),
        ('services', 'Services'),
    ], string='Activity Type')
    
    company_size = fields.Selection([
        ('micro', 'Micro (1-9)'),
        ('small', 'Small (10-49)'),
        ('medium', 'Medium (50-249)'),
        ('large', 'Large (250+)'),
    ], string='Company Size')
    
    # Location
    emirate = fields.Selection([
        ('abu_dhabi', 'Abu Dhabi'),
        ('dubai', 'Dubai'),
        ('sharjah', 'Sharjah'),
        ('ajman', 'Ajman'),
        ('umm_al_quwain', 'Umm Al Quwain'),
        ('ras_al_khaimah', 'Ras Al Khaimah'),
        ('fujairah', 'Fujairah'),
    ], string='Emirate', required=True)
    
    is_free_zone = fields.Boolean(string='Free Zone')
    free_zone_name = fields.Char(string='Free Zone Name')
    
    # Contacts
    authorized_signatory = fields.Char(string='Authorized Signatory')
    contact_person = fields.Char(string='Contact Person')
    contact_email = fields.Char(string='Contact Email')
    contact_phone = fields.Char(string='Contact Phone')
    
    # Status
    state = fields.Selection([
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='active', tracking=True)
    
    # Related
    work_permit_ids = fields.One2many('tazweed.work.permit', 'establishment_id', string='Work Permits')
    labour_contract_ids = fields.One2many('tazweed.labour.contract', 'establishment_id', string='Labour Contracts')
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)


class WorkPermit(models.Model):
    """Work Permit Management"""
    _name = 'tazweed.work.permit'
    _description = 'Work Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'

    name = fields.Char(string='Permit No.', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    establishment_id = fields.Many2one('tazweed.mohre.establishment', string='Establishment')
    
    # Permit Details
    permit_type = fields.Selection([
        ('new', 'New'),
        ('renewal', 'Renewal'),
        ('transfer', 'Transfer'),
        ('mission', 'Mission'),
    ], string='Permit Type', default='new')
    
    job_title = fields.Char(string='Job Title')
    job_code = fields.Char(string='MOL Job Code')
    
    # Dates
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    
    days_to_expiry = fields.Integer(string='Days to Expiry', compute='_compute_expiry')
    is_expired = fields.Boolean(string='Expired', compute='_compute_expiry')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('applied', 'Applied'),
        ('approved', 'Approved'),
        ('issued', 'Issued'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Fees
    permit_fee = fields.Float(string='Permit Fee')
    medical_fee = fields.Float(string='Medical Fee')
    total_fee = fields.Float(string='Total Fee', compute='_compute_fees')
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('expiry_date')
    def _compute_expiry(self):
        today = date.today()
        for rec in self:
            if rec.expiry_date:
                delta = rec.expiry_date - today
                rec.days_to_expiry = delta.days
                rec.is_expired = delta.days < 0
            else:
                rec.days_to_expiry = 0
                rec.is_expired = False

    @api.depends('permit_fee', 'medical_fee')
    def _compute_fees(self):
        for rec in self:
            rec.total_fee = rec.permit_fee + rec.medical_fee

    def action_apply(self):
        self.write({'state': 'applied'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_issue(self):
        self.write({'state': 'issued', 'issue_date': date.today()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class LabourContract(models.Model):
    """MOHRE Labour Contract"""
    _name = 'tazweed.labour.contract'
    _description = 'Labour Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Contract No.', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    establishment_id = fields.Many2one('tazweed.mohre.establishment', string='Establishment')
    
    # Contract Details
    contract_type = fields.Selection([
        ('limited', 'Limited'),
        ('unlimited', 'Unlimited'),
    ], string='Contract Type', default='limited')
    
    job_title = fields.Char(string='Job Title', required=True)
    
    # Dates
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date')
    duration_months = fields.Integer(string='Duration (Months)')
    
    # Salary
    basic_salary = fields.Float(string='Basic Salary', required=True)
    housing_allowance = fields.Float(string='Housing Allowance')
    transport_allowance = fields.Float(string='Transport Allowance')
    other_allowances = fields.Float(string='Other Allowances')
    total_salary = fields.Float(string='Total Salary', compute='_compute_total')
    
    # Working Hours
    working_hours = fields.Float(string='Working Hours/Day', default=8)
    working_days = fields.Integer(string='Working Days/Week', default=6)
    
    # Probation
    probation_period = fields.Integer(string='Probation Period (Days)', default=90)
    
    # Notice
    notice_period = fields.Integer(string='Notice Period (Days)', default=30)
    
    # Registration
    mol_registration_no = fields.Char(string='MOL Registration No.')
    registration_date = fields.Date(string='Registration Date')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('registered', 'Registered'),
        ('active', 'Active'),
        ('terminated', 'Terminated'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.labour.contract') or _('New')
        return super().create(vals)

    @api.depends('basic_salary', 'housing_allowance', 'transport_allowance', 'other_allowances')
    def _compute_total(self):
        for rec in self:
            rec.total_salary = rec.basic_salary + rec.housing_allowance + rec.transport_allowance + rec.other_allowances

    def action_register(self):
        self.write({'state': 'registered', 'registration_date': date.today()})

    def action_activate(self):
        self.write({'state': 'active'})

    def action_terminate(self):
        self.write({'state': 'terminated'})
