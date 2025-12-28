# -*- coding: utf-8 -*-
import base64
import hashlib
import secrets
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SignatureRequest(models.Model):
    """Signature Request - Main document for signature workflow."""
    _name = 'signature.request'
    _description = 'Signature Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # Basic Information
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    document_name = fields.Char(
        string='Document Name',
        required=True,
        tracking=True
    )
    
    # Document Type and Template
    document_type = fields.Selection([
        ('contract', 'Employment Contract'),
        ('offer', 'Offer Letter'),
        ('nda', 'Non-Disclosure Agreement'),
        ('policy', 'Policy Acknowledgment'),
        ('termination', 'Termination Letter'),
        ('amendment', 'Contract Amendment'),
        ('other', 'Other Document'),
    ], string='Document Type', default='contract', required=True, tracking=True)
    
    template_id = fields.Many2one(
        'signature.template',
        string='Template',
        ondelete='set null'
    )
    
    # Document Files
    document_file = fields.Binary(
        string='Document',
        attachment=True,
        required=True
    )
    document_filename = fields.Char(
        string='Document Filename'
    )
    document_hash = fields.Char(
        string='Document Hash',
        readonly=True,
        copy=False
    )
    
    # Signed Document
    signed_document = fields.Binary(
        string='Signed Document',
        attachment=True,
        readonly=True,
        copy=False
    )
    signed_filename = fields.Char(
        string='Signed Filename',
        readonly=True,
        copy=False
    )
    
    # Related Records
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        ondelete='set null',
        tracking=True
    )
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
        ondelete='set null'
    )
    
    # Signers
    signer_ids = fields.One2many(
        'signature.signer',
        'request_id',
        string='Signers',
        copy=True
    )
    signer_count = fields.Integer(
        string='Signer Count',
        compute='_compute_signer_stats',
        store=True
    )
    signed_count = fields.Integer(
        string='Signed Count',
        compute='_compute_signer_stats',
        store=True
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('partially_signed', 'Partially Signed'),
        ('signed', 'Completed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Dates
    sent_date = fields.Datetime(
        string='Sent Date',
        readonly=True,
        copy=False
    )
    expiry_date = fields.Date(
        string='Expiry Date'
    )
    completed_date = fields.Datetime(
        string='Completed Date',
        readonly=True,
        copy=False
    )
    
    # Reminders
    reminder_enabled = fields.Boolean(
        string='Enable Reminders',
        default=True
    )
    reminder_days = fields.Integer(
        string='Reminder After (Days)',
        default=3
    )
    last_reminder_date = fields.Datetime(
        string='Last Reminder',
        readonly=True,
        copy=False
    )
    
    # Security
    access_token = fields.Char(
        string='Access Token',
        readonly=True,
        copy=False
    )
    require_authentication = fields.Boolean(
        string='Require Authentication',
        default=False
    )
    
    # Audit
    audit_log_ids = fields.One2many(
        'signature.audit.log',
        'request_id',
        string='Audit Log',
        readonly=True
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Color for Kanban
    color = fields.Integer(string='Color')

    @api.depends('signer_ids', 'signer_ids.state')
    def _compute_signer_stats(self):
        """Compute signer statistics."""
        for request in self:
            request.signer_count = len(request.signer_ids)
            request.signed_count = len(request.signer_ids.filtered(lambda s: s.state == 'signed'))

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence and access token."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('signature.request') or _('New')
            if not vals.get('access_token'):
                vals['access_token'] = secrets.token_urlsafe(32)
            # Compute document hash
            if vals.get('document_file'):
                doc_bytes = base64.b64decode(vals['document_file'])
                vals['document_hash'] = hashlib.sha256(doc_bytes).hexdigest()
        return super().create(vals_list)

    def write(self, vals):
        """Override write to update document hash if document changes."""
        if vals.get('document_file'):
            doc_bytes = base64.b64decode(vals['document_file'])
            vals['document_hash'] = hashlib.sha256(doc_bytes).hexdigest()
        return super().write(vals)

    def action_send_for_signature(self):
        """Send the document for signature."""
        self.ensure_one()
        if not self.signer_ids:
            raise UserError(_('Please add at least one signer before sending.'))
        if not self.document_file:
            raise UserError(_('Please attach a document before sending.'))
        
        # Generate access tokens for signers
        for signer in self.signer_ids:
            if not signer.access_token:
                signer.access_token = secrets.token_urlsafe(32)
            signer._send_signature_request_email()
        
        self.write({
            'state': 'sent',
            'sent_date': fields.Datetime.now(),
        })
        self._log_audit('sent', _('Document sent for signature'))
        return True

    def action_send_reminder(self):
        """Send reminder to pending signers."""
        self.ensure_one()
        pending_signers = self.signer_ids.filtered(lambda s: s.state in ('pending', 'viewed'))
        for signer in pending_signers:
            signer._send_reminder_email()
        
        self.write({'last_reminder_date': fields.Datetime.now()})
        self._log_audit('reminder', _('Reminder sent to %d signers') % len(pending_signers))
        return True

    def action_cancel(self):
        """Cancel the signature request."""
        self.ensure_one()
        self.write({'state': 'cancelled'})
        self._log_audit('cancelled', _('Signature request cancelled'))
        return True

    def action_reset_to_draft(self):
        """Reset to draft state."""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'sent_date': False,
            'completed_date': False,
        })
        # Reset signer states
        self.signer_ids.write({
            'state': 'pending',
            'signature_data': False,
            'signed_date': False,
        })
        self._log_audit('reset', _('Request reset to draft'))
        return True

    def action_view_signed_document(self):
        """Download the signed document."""
        self.ensure_one()
        if not self.signed_document:
            raise UserError(_('No signed document available.'))
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/signature.request/{self.id}/signed_document/{self.signed_filename}?download=true',
            'target': 'self',
        }

    def _check_all_signed(self):
        """Check if all signers have signed and update status."""
        self.ensure_one()
        if all(signer.state == 'signed' for signer in self.signer_ids):
            self.write({
                'state': 'signed',
                'completed_date': fields.Datetime.now(),
            })
            self._generate_signed_document()
            self._log_audit('completed', _('All signatures collected'))
            self._send_completion_notification()
        elif any(signer.state == 'signed' for signer in self.signer_ids):
            if self.state != 'partially_signed':
                self.write({'state': 'partially_signed'})

    def _generate_signed_document(self):
        """Generate the final signed document with all signatures."""
        self.write({
            'signed_document': self.document_file,
            'signed_filename': f'signed_{self.document_filename}',
        })

    def _send_completion_notification(self):
        """Send notification when all signatures are collected."""
        template = self.env.ref('tazweed_esignature.email_signature_completed', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _log_audit(self, action, description, signer=None):
        """Log an audit entry."""
        self.env['signature.audit.log'].create({
            'request_id': self.id,
            'signer_id': signer.id if signer else False,
            'action': action,
            'description': description,
        })

    @api.model
    def get_dashboard_data(self, date_range='30'):
        """Get dashboard statistics for the OWL component."""
        days = int(date_range)
        date_from = fields.Date.today() - timedelta(days=days)
        
        all_requests = self.search([])
        
        status_counts = {}
        for state in ['draft', 'sent', 'partially_signed', 'signed', 'expired', 'cancelled']:
            status_counts[state] = self.search_count([('state', '=', state)])
        
        total = len(all_requests)
        completed = status_counts.get('signed', 0)
        completion_rate = round((completed / total * 100) if total > 0 else 0, 1)
        
        completed_requests = self.search([
            ('state', '=', 'signed'),
            ('sent_date', '!=', False),
            ('completed_date', '!=', False),
        ])
        avg_completion_time = 0
        if completed_requests:
            total_hours = sum(
                (r.completed_date - r.sent_date).total_seconds() / 3600
                for r in completed_requests
            )
            avg_completion_time = round(total_hours / len(completed_requests), 1)
        
        pending_count = self.search_count([('state', 'in', ('sent', 'partially_signed'))])
        
        recent_activity = []
        audit_logs = self.env['signature.audit.log'].search([], limit=10, order='timestamp desc')
        for log in audit_logs:
            recent_activity.append({
                'id': log.id,
                'action': log.action,
                'description': log.description,
                'timestamp': log.timestamp.isoformat() if log.timestamp else '',
                'request_name': log.request_id.name if log.request_id else '',
            })
        
        trend_data = []
        for i in range(7):
            day = fields.Date.today() - timedelta(days=6-i)
            day_start = fields.Datetime.to_datetime(day)
            day_end = day_start + timedelta(days=1)
            
            sent = self.search_count([
                ('sent_date', '>=', day_start),
                ('sent_date', '<', day_end),
            ])
            completed = self.search_count([
                ('completed_date', '>=', day_start),
                ('completed_date', '<', day_end),
            ])
            
            trend_data.append({
                'date': day.strftime('%b %d'),
                'sent': sent,
                'completed': completed,
            })
        
        return {
            'total_requests': total,
            'pending_signatures': pending_count,
            'completed_today': self.search_count([
                ('completed_date', '>=', fields.Datetime.today()),
                ('state', '=', 'signed'),
            ]),
            'avg_completion_time': avg_completion_time,
            'completion_rate': completion_rate,
            'status_counts': status_counts,
            'recent_activity': recent_activity,
            'trend_data': trend_data,
        }
