# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class PlacementClient(models.Model):
    """Client Company for Placement"""
    _name = 'tazweed.client'
    _description = 'Placement Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Company Name', required=True, tracking=True)
    code = fields.Char(
        string='Client Code',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        domain="[('is_company', '=', True)]",
    )
    
    # Company Details
    trade_license = fields.Char(string='Trade License No.')
    trade_license_expiry = fields.Date(string='Trade License Expiry')
    establishment_card = fields.Char(string='Establishment Card No.')
    establishment_card_expiry = fields.Date(string='Establishment Card Expiry')
    
    industry_id = fields.Many2one('res.partner.industry', string='Industry')
    company_size = fields.Selection([
        ('small', 'Small (1-50)'),
        ('medium', 'Medium (51-200)'),
        ('large', 'Large (201-500)'),
        ('enterprise', 'Enterprise (500+)'),
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
    ], string='Emirate')
    
    free_zone = fields.Char(string='Free Zone')
    is_free_zone = fields.Boolean(string='Is Free Zone Company')
    
    # Contacts
    contact_ids = fields.One2many('tazweed.client.contact', 'client_id', string='Contacts')
    primary_contact_id = fields.Many2one('tazweed.client.contact', string='Primary Contact')
    
    # Contract & Billing
    contract_ids = fields.One2many('tazweed.client.contract', 'client_id', string='Contracts')
    active_contract_id = fields.Many2one(
        'tazweed.client.contract',
        string='Active Contract',
        compute='_compute_active_contract',
    )
    
    billing_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('weekly', 'Weekly'),
        ('per_placement', 'Per Placement'),
    ], string='Billing Type', default='monthly')
    
    payment_terms = fields.Integer(string='Payment Terms (Days)', default=30)
    credit_limit = fields.Float(string='Credit Limit')
    
    # Rates
    default_markup_pct = fields.Float(string='Default Markup %', default=15)
    default_commission_pct = fields.Float(string='Default Commission %', default=10)
    
    # Status
    state = fields.Selection([
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('inactive', 'Inactive'),
    ], string='Status', default='prospect', tracking=True)
    
    # Statistics
    job_order_count = fields.Integer(compute='_compute_counts')
    placement_count = fields.Integer(compute='_compute_counts')
    active_placement_count = fields.Integer(compute='_compute_counts')
    total_revenue = fields.Float(compute='_compute_revenue')
    
    # Documents
    document_ids = fields.One2many('tazweed.client.document', 'client_id', string='Documents')
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Client code must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tazweed.client') or _('New')
        return super().create(vals)

    @api.depends('contract_ids', 'contract_ids.state')
    def _compute_active_contract(self):
        for client in self:
            active = client.contract_ids.filtered(lambda c: c.state == 'active')
            client.active_contract_id = active[0] if active else False

    def _compute_counts(self):
        for client in self:
            job_orders = self.env['tazweed.job.order'].search_count([('client_id', '=', client.id)])
            placements = self.env['tazweed.placement'].search([('client_id', '=', client.id)])
            client.job_order_count = job_orders
            client.placement_count = len(placements)
            client.active_placement_count = len(placements.filtered(lambda p: p.state == 'active'))

    def _compute_revenue(self):
        for client in self:
            placements = self.env['tazweed.placement'].search([
                ('client_id', '=', client.id),
                ('state', 'in', ('active', 'completed')),
            ])
            client.total_revenue = sum(p.total_billing for p in placements)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_hold(self):
        self.write({'state': 'on_hold'})

    def action_deactivate(self):
        self.write({'state': 'inactive'})

    def action_view_job_orders(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Job Orders'),
            'res_model': 'tazweed.job.order',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'context': {'default_client_id': self.id},
        }

    def action_view_placements(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Placements'),
            'res_model': 'tazweed.placement',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'context': {'default_client_id': self.id},
        }


class ClientContact(models.Model):
    """Client Contact Person"""
    _name = 'tazweed.client.contact'
    _description = 'Client Contact'
    _order = 'is_primary desc, name'

    client_id = fields.Many2one('tazweed.client', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', domain="[('is_company', '=', False)]")
    
    name = fields.Char(string='Name', required=True)
    designation = fields.Char(string='Designation')
    department = fields.Char(string='Department')
    
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    
    contact_type = fields.Selection([
        ('hr', 'HR Contact'),
        ('hiring', 'Hiring Manager'),
        ('finance', 'Finance Contact'),
        ('operations', 'Operations Contact'),
        ('executive', 'Executive'),
    ], string='Contact Type', default='hr')
    
    is_primary = fields.Boolean(string='Primary Contact')
    is_billing_contact = fields.Boolean(string='Billing Contact')
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)


class ClientContract(models.Model):
    """Client Contract"""
    _name = 'tazweed.client.contract'
    _description = 'Client Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(
        string='Contract Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    client_id = fields.Many2one('tazweed.client', required=True, ondelete='cascade')
    
    contract_type = fields.Selection([
        ('manpower', 'Manpower Supply'),
        ('recruitment', 'Recruitment'),
        ('outsourcing', 'HR Outsourcing'),
        ('payroll', 'Payroll Services'),
        ('combined', 'Combined Services'),
    ], string='Contract Type', required=True, default='manpower')
    
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date')
    duration_months = fields.Integer(string='Duration (Months)')
    
    # Terms
    markup_pct = fields.Float(string='Markup %')
    commission_pct = fields.Float(string='Commission %')
    
    billing_type = fields.Selection([
        ('monthly', 'Monthly'),
        ('bi_weekly', 'Bi-Weekly'),
        ('weekly', 'Weekly'),
        ('per_placement', 'Per Placement'),
    ], string='Billing Type', default='monthly')
    
    payment_terms = fields.Integer(string='Payment Terms (Days)', default=30)
    
    # Rates
    rate_ids = fields.One2many('tazweed.client.rate', 'contract_id', string='Rate Card')
    
    # Documents
    contract_document = fields.Binary(string='Contract Document')
    contract_document_name = fields.Char(string='Document Name')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Terms and Conditions')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.client.contract') or _('New')
        return super().create(vals)

    def action_submit(self):
        self.write({'state': 'pending'})

    def action_approve(self):
        self.write({'state': 'active'})

    def action_expire(self):
        self.write({'state': 'expired'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class ClientRate(models.Model):
    """Client Rate Card"""
    _name = 'tazweed.client.rate'
    _description = 'Client Rate'

    contract_id = fields.Many2one('tazweed.client.contract', required=True, ondelete='cascade')
    
    job_category = fields.Selection([
        ('unskilled', 'Unskilled'),
        ('semi_skilled', 'Semi-Skilled'),
        ('skilled', 'Skilled'),
        ('professional', 'Professional'),
        ('managerial', 'Managerial'),
        ('executive', 'Executive'),
    ], string='Job Category', required=True)
    
    job_id = fields.Many2one('hr.job', string='Specific Position')
    
    rate_type = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
        ('fixed', 'Fixed Fee'),
    ], string='Rate Type', default='monthly')
    
    base_rate = fields.Float(string='Base Rate')
    markup_pct = fields.Float(string='Markup %')
    bill_rate = fields.Float(string='Bill Rate', compute='_compute_bill_rate', store=True)
    
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('base_rate', 'markup_pct')
    def _compute_bill_rate(self):
        for rate in self:
            rate.bill_rate = rate.base_rate * (1 + rate.markup_pct / 100)


class ClientDocument(models.Model):
    """Client Document"""
    _name = 'tazweed.client.document'
    _description = 'Client Document'
    _order = 'create_date desc'

    client_id = fields.Many2one('tazweed.client', required=True, ondelete='cascade')
    
    name = fields.Char(string='Document Name', required=True)
    document_type = fields.Selection([
        ('trade_license', 'Trade License'),
        ('establishment_card', 'Establishment Card'),
        ('contract', 'Contract'),
        ('nda', 'NDA'),
        ('other', 'Other'),
    ], string='Document Type', required=True)
    
    document = fields.Binary(string='Document', required=True)
    document_name = fields.Char(string='File Name')
    
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    
    notes = fields.Text(string='Notes')
