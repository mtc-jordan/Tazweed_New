# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProCustomer(models.Model):
    """External customers for PRO services"""
    _name = 'pro.customer'
    _description = 'PRO Customer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Customer Name', required=True, tracking=True)
    reference = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    
    # Customer Type
    customer_type = fields.Selection([
        ('individual', 'Individual'),
        ('company', 'Company'),
    ], string='Customer Type', default='individual', required=True, tracking=True)
    
    # Contact Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        help='Link to contact record'
    )
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile')
    
    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    emirate = fields.Selection([
        ('dubai', 'Dubai'),
        ('abu_dhabi', 'Abu Dhabi'),
        ('sharjah', 'Sharjah'),
        ('ajman', 'Ajman'),
        ('ras_al_khaimah', 'Ras Al Khaimah'),
        ('fujairah', 'Fujairah'),
        ('umm_al_quwain', 'Umm Al Quwain'),
    ], string='Emirate', default='dubai')
    country_id = fields.Many2one('res.country', string='Country')
    
    # Individual Details
    nationality_id = fields.Many2one('res.country', string='Nationality')
    passport_number = fields.Char(string='Passport Number')
    passport_expiry = fields.Date(string='Passport Expiry')
    emirates_id = fields.Char(string='Emirates ID')
    emirates_id_expiry = fields.Date(string='Emirates ID Expiry')
    date_of_birth = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender')
    
    # Company Details
    trade_license_number = fields.Char(string='Trade License Number')
    trade_license_expiry = fields.Date(string='Trade License Expiry')
    company_type = fields.Selection([
        ('mainland', 'Mainland'),
        ('free_zone', 'Free Zone'),
        ('offshore', 'Offshore'),
    ], string='Company Type')
    free_zone_id = fields.Char(string='Free Zone')
    
    # Documents
    document_ids = fields.One2many(
        'pro.customer.document',
        'customer_id',
        string='Documents'
    )
    document_count = fields.Integer(
        string='Document Count',
        compute='_compute_document_count'
    )
    
    # Service Requests
    request_ids = fields.One2many(
        'pro.service.request',
        'customer_id',
        string='Service Requests'
    )
    request_count = fields.Integer(
        string='Request Count',
        compute='_compute_request_count'
    )
    
    # Billing
    total_billed = fields.Float(
        string='Total Billed',
        compute='_compute_billing'
    )
    total_paid = fields.Float(
        string='Total Paid',
        compute='_compute_billing'
    )
    balance_due = fields.Float(
        string='Balance Due',
        compute='_compute_billing'
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'pro.customer'
                ) or _('New')
        return super().create(vals_list)

    @api.depends('document_ids')
    def _compute_document_count(self):
        for record in self:
            record.document_count = len(record.document_ids)

    @api.depends('request_ids')
    def _compute_request_count(self):
        for record in self:
            record.request_count = len(record.request_ids)

    def _compute_billing(self):
        for record in self:
            billings = self.env['pro.billing'].search([
                ('customer_id', '=', record.id)
            ])
            record.total_billed = sum(billings.mapped('total_amount'))
            record.total_paid = sum(billings.filtered(
                lambda b: b.payment_status == 'paid'
            ).mapped('total_amount'))
            record.balance_due = record.total_billed - record.total_paid

    def action_view_requests(self):
        """View customer's service requests"""
        self.ensure_one()
        return {
            'name': _('Service Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.service.request',
            'view_mode': 'list,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }

    def action_view_documents(self):
        """View customer's documents"""
        self.ensure_one()
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.customer.document',
            'view_mode': 'list,form',
            'domain': [('customer_id', '=', self.id)],
            'context': {'default_customer_id': self.id},
        }


class ProCustomerDocument(models.Model):
    """Documents uploaded by/for PRO customers"""
    _name = 'pro.customer.document'
    _description = 'PRO Customer Document'
    _order = 'create_date desc'

    name = fields.Char(string='Document Name', required=True)
    customer_id = fields.Many2one(
        'pro.customer',
        string='Customer',
        required=True,
        ondelete='cascade'
    )
    document_type_id = fields.Many2one(
        'pro.document.type',
        string='Document Type',
        required=True
    )
    
    # File
    file = fields.Binary(string='File', required=True, attachment=True)
    file_name = fields.Char(string='File Name')
    
    # Details
    document_number = fields.Char(string='Document Number')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    issuing_authority = fields.Char(string='Issuing Authority')
    
    # Status
    status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Status', compute='_compute_status', store=True)
    
    notes = fields.Text(string='Notes')

    @api.depends('expiry_date')
    def _compute_status(self):
        today = fields.Date.today()
        for record in self:
            if not record.expiry_date:
                record.status = 'valid'
            elif record.expiry_date < today:
                record.status = 'expired'
            elif (record.expiry_date - today).days <= 30:
                record.status = 'expiring_soon'
            else:
                record.status = 'valid'
