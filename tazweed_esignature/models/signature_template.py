# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SignatureTemplate(models.Model):
    """Signature Template for reusable document configurations."""
    _name = 'signature.template'
    _description = 'Signature Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Template Name',
        required=True,
        tracking=True
    )
    active = fields.Boolean(
        string='Active',
        default=True
    )
    description = fields.Text(
        string='Description'
    )
    
    # Document Configuration
    document_type = fields.Selection([
        ('contract', 'Employment Contract'),
        ('offer', 'Offer Letter'),
        ('nda', 'Non-Disclosure Agreement'),
        ('policy', 'Policy Acknowledgment'),
        ('termination', 'Termination Letter'),
        ('amendment', 'Contract Amendment'),
        ('other', 'Other Document'),
    ], string='Document Type', default='contract', required=True, tracking=True)
    
    template_file = fields.Binary(
        string='Template Document',
        attachment=True
    )
    template_filename = fields.Char(
        string='Template Filename'
    )
    
    # Signer Configuration
    default_signers = fields.Integer(
        string='Default Number of Signers',
        default=1
    )
    require_sequential = fields.Boolean(
        string='Sequential Signing',
        default=False,
        help='Signers must sign in order'
    )
    
    # Expiry Settings
    default_expiry_days = fields.Integer(
        string='Default Expiry (Days)',
        default=30
    )
    
    # Reminder Settings
    reminder_enabled = fields.Boolean(
        string='Enable Reminders',
        default=True
    )
    reminder_days = fields.Integer(
        string='Reminder After (Days)',
        default=3
    )
    
    # Statistics
    request_count = fields.Integer(
        string='Request Count',
        compute='_compute_request_count'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    def _compute_request_count(self):
        """Compute the number of requests using this template."""
        for template in self:
            template.request_count = self.env['signature.request'].search_count([
                ('template_id', '=', template.id)
            ])

    def action_view_requests(self):
        """View all requests using this template."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature Requests'),
            'res_model': 'signature.request',
            'view_mode': 'kanban,tree,form',
            'domain': [('template_id', '=', self.id)],
            'context': {'default_template_id': self.id},
        }

    def action_create_request(self):
        """Create a new request from this template."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Signature Request'),
            'res_model': 'signature.request',
            'view_mode': 'form',
            'context': {
                'default_template_id': self.id,
                'default_document_type': self.document_type,
            },
        }
