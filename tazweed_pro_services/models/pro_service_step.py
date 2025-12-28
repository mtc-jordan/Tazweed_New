# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProServiceStep(models.Model):
    """Steps within a PRO service workflow"""
    _name = 'pro.service.step'
    _description = 'PRO Service Step'
    _order = 'service_id, sequence'

    name = fields.Char(string='Step Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Parent Service
    service_id = fields.Many2one(
        'pro.service',
        string='Service',
        required=True,
        ondelete='cascade'
    )
    
    # Step Details
    description = fields.Text(string='Description')
    instructions = fields.Html(string='Instructions')
    
    # Step Type
    step_type = fields.Selection([
        ('document_collection', 'Document Collection'),
        ('document_verification', 'Document Verification'),
        ('form_filling', 'Form Filling'),
        ('payment', 'Payment'),
        ('submission', 'Government Submission'),
        ('biometric', 'Biometric/Photo'),
        ('medical', 'Medical Test'),
        ('approval_waiting', 'Waiting for Approval'),
        ('collection', 'Document Collection'),
        ('delivery', 'Delivery to Customer'),
        ('other', 'Other'),
    ], string='Step Type', default='other')
    
    # Location
    location = fields.Selection([
        ('office', 'Office'),
        ('government', 'Government Office'),
        ('typing_center', 'Typing Center'),
        ('medical_center', 'Medical Center'),
        ('online', 'Online Portal'),
        ('customer_location', 'Customer Location'),
    ], string='Location', default='office')
    
    # Government Authority for this step
    government_authority_id = fields.Many2one(
        'pro.government.authority',
        string='Government Authority'
    )
    
    # Time Estimates
    estimated_duration = fields.Float(
        string='Estimated Duration (Hours)',
        default=1.0
    )
    waiting_days = fields.Integer(
        string='Waiting Days',
        default=0,
        help='Days to wait after this step (e.g., for government processing)'
    )
    
    # Documents
    required_document_ids = fields.Many2many(
        'pro.document.type',
        'pro_step_required_document_rel',
        'step_id',
        'document_type_id',
        string='Required Documents'
    )
    output_document_ids = fields.Many2many(
        'pro.document.type',
        'pro_step_output_document_rel',
        'step_id',
        'document_type_id',
        string='Output Documents'
    )
    
    # Fees
    government_fee = fields.Float(string='Government Fee', digits=(16, 2))
    service_fee = fields.Float(string='Service Fee', digits=(16, 2))
    
    # Requirements
    requires_customer_presence = fields.Boolean(string='Requires Customer Presence')
    requires_original_documents = fields.Boolean(string='Requires Original Documents')
    
    # Automation
    auto_proceed = fields.Boolean(
        string='Auto Proceed',
        help='Automatically proceed to next step when completed'
    )
    
    # Notes
    notes = fields.Text(string='Internal Notes')
    active = fields.Boolean(string='Active', default=True)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.sequence}. {record.name}"
            result.append((record.id, name))
        return result
