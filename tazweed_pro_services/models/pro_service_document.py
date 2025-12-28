# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProServiceDocument(models.Model):
    """Required documents for PRO services"""
    _name = 'pro.service.document'
    _description = 'PRO Service Required Document'
    _order = 'service_id, sequence'

    service_id = fields.Many2one(
        'pro.service',
        string='Service',
        required=True,
        ondelete='cascade'
    )
    document_type_id = fields.Many2one(
        'pro.document.type',
        string='Document Type',
        required=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    is_required = fields.Boolean(string='Required', default=True)
    notes = fields.Text(string='Notes')
    
    # Auto-fetch settings
    auto_fetch = fields.Boolean(
        string='Auto Fetch',
        default=True,
        help='Automatically fetch this document from employee records if available'
    )
    employee_document_field = fields.Char(
        string='Employee Document Field',
        help='Field name in employee record to fetch document from'
    )
