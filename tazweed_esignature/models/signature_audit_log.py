# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SignatureAuditLog(models.Model):
    """Audit Log for signature activities."""
    _name = 'signature.audit.log'
    _description = 'Signature Audit Log'
    _order = 'timestamp desc'

    request_id = fields.Many2one(
        'signature.request',
        string='Signature Request',
        ondelete='cascade',
        required=True,
        index=True
    )
    signer_id = fields.Many2one(
        'signature.signer',
        string='Signer',
        ondelete='set null'
    )
    
    timestamp = fields.Datetime(
        string='Timestamp',
        default=fields.Datetime.now,
        required=True
    )
    
    action = fields.Selection([
        ('created', 'Created'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('signed', 'Signed'),
        ('declined', 'Declined'),
        ('reminder', 'Reminder Sent'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('reset', 'Reset to Draft'),
    ], string='Action', required=True)
    
    description = fields.Text(string='Description')
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user
    )
