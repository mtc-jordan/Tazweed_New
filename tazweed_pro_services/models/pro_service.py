# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProService(models.Model):
    """PRO Service definitions with steps and requirements"""
    _name = 'pro.service'
    _description = 'PRO Service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Service Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Classification
    category_id = fields.Many2one(
        'pro.service.category',
        string='Category',
        required=True,
        tracking=True
    )
    service_type = fields.Selection([
        ('new', 'New Application'),
        ('renewal', 'Renewal'),
        ('amendment', 'Amendment'),
        ('cancellation', 'Cancellation'),
        ('replacement', 'Replacement'),
    ], string='Service Type', default='new', required=True, tracking=True)
    
    # Government Authority
    government_authority_id = fields.Many2one(
        'pro.government.authority',
        string='Government Authority',
        required=True
    )
    # Service Details
    description = fields.Html(string='Description')
    
    # Target
    applicable_to = fields.Selection([
        ('employee', 'Internal Employees Only'),
        ('customer', 'External Customers Only'),
        ('both', 'Both Employees & Customers'),
    ], string='Applicable To', default='both', required=True)
    
    # Pricing
    government_fee = fields.Float(string='Government Fee (AED)', digits=(16, 2), help='Official government fees')
    service_fee = fields.Float(string='Service Fee (AED)', digits=(16, 2), help='PRO service charges')
    total_fee = fields.Float(
        string='Total Fee',
        compute='_compute_total_fee',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # SLA
    processing_days = fields.Integer(
        string='Processing Days',
        default=5,
        help='Expected number of working days to complete'
    )
    urgent_available = fields.Boolean(string='Urgent Processing Available')
    urgent_fee = fields.Float(string='Urgent Processing Fee', digits=(16, 2))
    urgent_days = fields.Integer(string='Urgent Processing Days', default=2)
    
    # Steps
    step_ids = fields.One2many(
        'pro.service.step',
        'service_id',
        string='Service Steps'
    )
    step_count = fields.Integer(
        string='Step Count',
        compute='_compute_step_count'
    )
    
    # Required Documents
    required_document_ids = fields.Many2many(
        'pro.document.type',
        'pro_service_document_rel',
        'service_id',
        'document_type_id',
        string='Required Documents'
    )
    
    # Output Documents
    output_document_ids = fields.Many2many(
        'pro.document.type',
        'pro_service_output_document_rel',
        'service_id',
        'document_type_id',
        string='Output Documents',
        help='Documents produced by this service'
    )
    
    # Prerequisites
    prerequisite_service_ids = fields.Many2many(
        'pro.service',
        'pro_service_prerequisite_rel',
        'service_id',
        'prerequisite_id',
        string='Prerequisite Services'
    )
    
    # Notes
    internal_notes = fields.Text(string='Internal Notes')
    customer_notes = fields.Text(string='Customer Instructions')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    # Statistics
    request_count = fields.Integer(
        string='Request Count',
        compute='_compute_request_count'
    )

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Service code must be unique!'),
    ]

    @api.depends('government_fee', 'service_fee')
    def _compute_total_fee(self):
        for record in self:
            record.total_fee = record.government_fee + record.service_fee

    @api.depends('step_ids')
    def _compute_step_count(self):
        for record in self:
            record.step_count = len(record.step_ids)

    def _compute_request_count(self):
        Request = self.env['pro.service.request']
        for record in self:
            record.request_count = Request.search_count([
                ('service_id', '=', record.id)
            ])

    def action_view_requests(self):
        """View all requests for this service"""
        self.ensure_one()
        return {
            'name': _('Service Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.service.request',
            'view_mode': 'list,form',
            'domain': [('service_id', '=', self.id)],
            'context': {'default_service_id': self.id},
        }

    def action_view_steps(self):
        """View service steps"""
        self.ensure_one()
        return {
            'name': _('Service Steps'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.service.step',
            'view_mode': 'list,form',
            'domain': [('service_id', '=', self.id)],
            'context': {'default_service_id': self.id},
        }

    @api.constrains('urgent_days', 'processing_days')
    def _check_urgent_days(self):
        for record in self:
            if record.urgent_available and record.urgent_days >= record.processing_days:
                raise ValidationError(_(
                    'Urgent processing days must be less than normal processing days.'
                ))
