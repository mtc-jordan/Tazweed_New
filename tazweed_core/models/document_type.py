# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DocumentType(models.Model):
    """Document Type Configuration"""
    _name = 'tazweed.document.type'
    _description = 'Document Type'
    _order = 'sequence, name'

    name = fields.Char(string='Document Type', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    is_mandatory = fields.Boolean(string='Mandatory', default=False)
    has_expiry = fields.Boolean(string='Has Expiry Date', default=True)
    alert_days = fields.Integer(string='Alert Days Before Expiry', default=30)
    
    category = fields.Selection([
        ('identification', 'Identification'),
        ('visa', 'Visa & Immigration'),
        ('employment', 'Employment'),
        ('education', 'Education'),
        ('medical', 'Medical'),
        ('other', 'Other'),
    ], string='Category', default='other')
    
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Document type name must be unique!'),
    ]
