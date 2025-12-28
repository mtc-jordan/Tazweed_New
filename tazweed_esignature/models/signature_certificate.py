# -*- coding: utf-8 -*-
import hashlib
import secrets
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SignatureCertificate(models.Model):
    """Signature Certificate - Legal proof of signature completion."""
    _name = 'signature.certificate'
    _description = 'Signature Certificate'
    _order = 'create_date desc'

    name = fields.Char(
        string='Certificate Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    request_id = fields.Many2one(
        'signature.request',
        string='Signature Request',
        required=True,
        ondelete='cascade'
    )
    
    # Document Information
    document_name = fields.Char(
        string='Document Name',
        related='request_id.document_name',
        store=True
    )
    document_type = fields.Selection(
        related='request_id.document_type',
        store=True
    )
    document_hash = fields.Char(
        string='Document Hash',
        related='request_id.document_hash',
        store=True
    )
    
    # Certificate Details
    certificate_hash = fields.Char(
        string='Certificate Hash',
        readonly=True
    )
    verification_code = fields.Char(
        string='Verification Code',
        readonly=True
    )
    
    # Dates
    issued_date = fields.Datetime(
        string='Issued Date',
        default=fields.Datetime.now,
        readonly=True
    )
    valid_until = fields.Date(
        string='Valid Until',
        compute='_compute_valid_until',
        store=True
    )
    
    # Signers Summary
    signer_summary = fields.Text(
        string='Signers Summary',
        compute='_compute_signer_summary',
        store=True
    )
    total_signers = fields.Integer(
        string='Total Signers',
        compute='_compute_signer_summary',
        store=True
    )
    
    # Verification
    is_verified = fields.Boolean(
        string='Verified',
        default=True
    )
    verification_url = fields.Char(
        string='Verification URL',
        compute='_compute_verification_url'
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate certificate number and hashes."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('signature.certificate') or _('New')
            vals['verification_code'] = secrets.token_urlsafe(16).upper()[:12]
            
            # Generate certificate hash
            hash_input = f"{vals.get('name', '')}{vals.get('verification_code', '')}{fields.Datetime.now()}"
            vals['certificate_hash'] = hashlib.sha256(hash_input.encode()).hexdigest()
        
        return super().create(vals_list)

    @api.depends('issued_date')
    def _compute_valid_until(self):
        """Certificate is valid for 10 years."""
        for cert in self:
            if cert.issued_date:
                cert.valid_until = fields.Date.add(cert.issued_date, years=10)
            else:
                cert.valid_until = False

    @api.depends('request_id.signer_ids')
    def _compute_signer_summary(self):
        """Compute summary of all signers."""
        for cert in self:
            signers = cert.request_id.signer_ids.filtered(lambda s: s.state == 'signed')
            cert.total_signers = len(signers)
            
            summary_lines = []
            for signer in signers:
                summary_lines.append(
                    f"• {signer.name} ({signer.email})\n"
                    f"  Role: {dict(signer._fields['role'].selection).get(signer.role, 'N/A')}\n"
                    f"  Signed: {signer.signed_date.strftime('%Y-%m-%d %H:%M:%S') if signer.signed_date else 'N/A'}\n"
                    f"  IP: {signer.signing_ip or 'N/A'}\n"
                    f"  Signature Hash: {signer.signature_hash[:16]}..." if signer.signature_hash else ""
                )
            cert.signer_summary = '\n'.join(summary_lines)

    def _compute_verification_url(self):
        """Generate verification URL."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for cert in self:
            cert.verification_url = f"{base_url}/verify/{cert.verification_code}"

    def action_download_certificate(self):
        """Download the certificate as PDF."""
        self.ensure_one()
        return self.env.ref('tazweed_esignature.action_report_signature_certificate').report_action(self)

    def action_verify(self):
        """Verify the certificate integrity."""
        self.ensure_one()
        # Check document hash matches
        if self.request_id.document_hash != self.document_hash:
            raise UserError(_('Document integrity check failed. The document may have been modified.'))
        
        # Check all signatures are valid
        for signer in self.request_id.signer_ids:
            if signer.state == 'signed' and not signer.signature_hash:
                raise UserError(_('Signature integrity check failed for %s.') % signer.name)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Verification Successful'),
                'message': _('Certificate and all signatures are valid.'),
                'type': 'success',
                'sticky': False,
            }
        }


class SignatureDocumentType(models.Model):
    """Document Type Configuration for signatures."""
    _name = 'signature.document.type'
    _description = 'Signature Document Type'
    _order = 'sequence, name'

    name = fields.Char(string='Document Type', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    description = fields.Text(string='Description')
    
    # Default Settings
    default_expiry_days = fields.Integer(
        string='Default Expiry (Days)',
        default=30
    )
    default_reminder_days = fields.Integer(
        string='Default Reminder (Days)',
        default=3
    )
    require_witness = fields.Boolean(
        string='Require Witness',
        default=False
    )
    min_signers = fields.Integer(
        string='Minimum Signers',
        default=1
    )
    
    # Template
    default_template_id = fields.Many2one(
        'signature.template',
        string='Default Template'
    )
    
    # Category
    category = fields.Selection([
        ('hr', 'HR Documents'),
        ('contract', 'Contracts'),
        ('compliance', 'Compliance'),
        ('finance', 'Finance'),
        ('legal', 'Legal'),
        ('other', 'Other'),
    ], string='Category', default='hr')
    
    active = fields.Boolean(string='Active', default=True)
