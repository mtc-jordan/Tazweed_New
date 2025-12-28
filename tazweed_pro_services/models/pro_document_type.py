# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProDocumentType(models.Model):
    """Document types required for PRO services"""
    _name = 'pro.document.type'
    _description = 'PRO Document Type'
    _order = 'sequence, name'

    name = fields.Char(string='Document Name', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Document Classification
    category = fields.Selection([
        ('identity', 'Identity Documents'),
        ('employment', 'Employment Documents'),
        ('education', 'Education Documents'),
        ('medical', 'Medical Documents'),
        ('legal', 'Legal Documents'),
        ('financial', 'Financial Documents'),
        ('company', 'Company Documents'),
        ('property', 'Property Documents'),
        ('other', 'Other'),
    ], string='Category', default='identity')
    
    # Document Details
    description = fields.Text(string='Description')
    validity_period = fields.Integer(string='Validity Period (Days)', help='0 means no expiry')
    
    # Requirements
    requires_attestation = fields.Boolean(string='Requires Attestation')
    requires_translation = fields.Boolean(string='Requires Translation')
    original_required = fields.Boolean(string='Original Required', default=True)
    copies_required = fields.Integer(string='Copies Required', default=1)
    
    # Mapping to Employee Documents
    employee_document_type_id = fields.Many2one(
        'tazweed.document.type',
        string='Employee Document Type',
        help='Map to employee document type for auto-attachment'
    )
    
    # Notes
    notes = fields.Text(string='Notes/Instructions')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Document type code must be unique!'),
    ]
