# -*- coding: utf-8 -*-
import base64
import hashlib
import secrets
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SignatureSigner(models.Model):
    """Document Signer - Simplified model without problematic onchange."""
    _name = 'signature.signer'
    _description = 'Document Signer'
    _order = 'sequence, id'

    # Parent Request
    request_id = fields.Many2one(
        'signature.request',
        string='Signature Request',
        ondelete='cascade',
        index=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Signer Information - Using simple fields
    name = fields.Char(string='Name', required=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Phone')
    role = fields.Selection([
        ('employee', 'Employee'),
        ('manager', 'Manager'),
        ('hr', 'HR Representative'),
        ('client', 'Client'),
        ('witness', 'Witness'),
        ('other', 'Other'),
    ], string='Role', default='employee')
    
    # Signature
    signature_type = fields.Selection([
        ('draw', 'Draw Signature'),
        ('type', 'Type Signature'),
        ('upload', 'Upload Signature'),
    ], string='Signature Type')
    
    signature_data = fields.Binary(string='Signature', attachment=True)
    signature_hash = fields.Char(string='Signature Hash', readonly=True)
    typed_signature = fields.Char(string='Typed Signature')
    signature_font = fields.Selection([
        ('dancing', 'Dancing Script'),
        ('allura', 'Allura'),
        ('pacifico', 'Pacifico'),
        ('sacramento', 'Sacramento'),
    ], string='Signature Font', default='dancing')
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('viewed', 'Viewed'),
        ('signed', 'Signed'),
        ('declined', 'Declined'),
    ], string='Status', default='pending')
    
    # Dates
    sent_date = fields.Datetime(string='Sent Date')
    viewed_date = fields.Datetime(string='First Viewed')
    signed_date = fields.Datetime(string='Signed Date')
    
    # Security
    access_token = fields.Char(string='Access Token', readonly=True, copy=False)
    
    # Audit Information
    signing_ip = fields.Char(string='Signing IP Address')
    signing_user_agent = fields.Char(string='Signing Device')
    
    # Decline
    decline_reason = fields.Text(string='Decline Reason')

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate access token."""
        for vals in vals_list:
            if not vals.get('access_token'):
                vals['access_token'] = secrets.token_urlsafe(32)
        return super().create(vals_list)

    def _send_signature_request_email(self):
        """Send signature request email to the signer."""
        self.ensure_one()
        template = self.env.ref('tazweed_esignature.email_signature_request', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        self.write({'sent_date': fields.Datetime.now()})
        if self.request_id:
            self.request_id._log_audit('sent', f'Signature request sent to {self.name}', self)

    def _send_reminder_email(self):
        """Send reminder email to the signer."""
        self.ensure_one()
        template = self.env.ref('tazweed_esignature.email_signature_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_mark_viewed(self, ip_address=None, user_agent=None):
        """Mark the document as viewed by the signer."""
        self.ensure_one()
        if self.state == 'pending':
            self.write({
                'state': 'viewed',
                'viewed_date': fields.Datetime.now(),
            })
            if self.request_id:
                self.request_id._log_audit('viewed', f'Document viewed by {self.name}', self)

    def action_sign(self, signature_data, signature_type='draw', ip_address=None, user_agent=None):
        """Record the signature from the signer."""
        self.ensure_one()
        
        if self.state == 'signed':
            raise UserError(_('This document has already been signed.'))
        if self.state == 'declined':
            raise UserError(_('This signature request was declined.'))
        
        signature_hash = None
        if signature_data:
            sig_bytes = base64.b64decode(signature_data) if isinstance(signature_data, str) else signature_data
            signature_hash = hashlib.sha256(sig_bytes).hexdigest()
        
        self.write({
            'state': 'signed',
            'signature_data': signature_data,
            'signature_type': signature_type,
            'signature_hash': signature_hash,
            'signed_date': fields.Datetime.now(),
            'signing_ip': ip_address,
            'signing_user_agent': user_agent,
        })
        
        if self.request_id:
            self.request_id._log_audit('signed', f'Document signed by {self.name}', self)
            self.request_id._check_all_signed()
        
        return True

    def action_decline(self, reason=None):
        """Decline to sign the document."""
        self.ensure_one()
        self.write({
            'state': 'declined',
            'decline_reason': reason,
        })
        if self.request_id:
            self.request_id._log_audit('declined', f'Signature declined by {self.name}: {reason}', self)
        return True

    def action_resend(self):
        """Resend the signature request email."""
        self.ensure_one()
        if self.state in ['signed', 'declined']:
            raise UserError(_('Cannot resend to a signer who has already signed or declined.'))
        self._send_signature_request_email()
        return True

    def get_signing_url(self):
        """Get the URL for signing the document."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f'{base_url}/sign/{self.request_id.access_token}/{self.access_token}'
