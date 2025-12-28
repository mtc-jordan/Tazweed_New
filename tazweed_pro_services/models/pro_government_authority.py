# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProGovernmentAuthority(models.Model):
    """Government authorities that PRO services interact with"""
    _name = 'pro.government.authority'
    _description = 'Government Authority'
    _order = 'sequence, name'

    name = fields.Char(string='Authority Name', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Authority Details
    authority_type = fields.Selection([
        ('federal', 'Federal'),
        ('local', 'Local/Emirate'),
        ('free_zone', 'Free Zone'),
    ], string='Authority Type', default='federal')
    
    emirate = fields.Selection([
        ('dubai', 'Dubai'),
        ('abu_dhabi', 'Abu Dhabi'),
        ('sharjah', 'Sharjah'),
        ('ajman', 'Ajman'),
        ('ras_al_khaimah', 'Ras Al Khaimah'),
        ('fujairah', 'Fujairah'),
        ('umm_al_quwain', 'Umm Al Quwain'),
        ('federal', 'Federal (All Emirates)'),
    ], string='Emirate', default='dubai')
    
    # Contact Information
    website = fields.Char(string='Website')
    portal_url = fields.Char(string='Portal URL')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    
    # Working Hours
    working_days = fields.Char(string='Working Days', default='Sunday - Thursday')
    working_hours = fields.Char(string='Working Hours', default='8:00 AM - 3:00 PM')
    
    # Notes
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True)
    
    # Related Services
    service_ids = fields.One2many(
        'pro.service',
        'government_authority_id',
        string='Services'
    )
    service_count = fields.Integer(
        string='Service Count',
        compute='_compute_service_count'
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Authority code must be unique!'),
    ]

    @api.depends('service_ids')
    def _compute_service_count(self):
        for record in self:
            record.service_count = len(record.service_ids)
