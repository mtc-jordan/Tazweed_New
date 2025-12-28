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
    description = fields.Text(string='Description')
    
    # Document Type and Template
    document_type = fields.Selection([
        ('contract', 'Employment Contract'),
        ('offer', 'Offer Letter'),
        ('nda', 'Non-Disclosure Agreement'),
        ('policy', 'Policy Acknowledgment'),
        ('termination', 'Termination Letter'),
        ('amendment', 'Contract Amendment'),
        ('warning', 'Warning Letter'),
        ('promotion', 'Promotion Letter'),
        ('salary_cert', 'Salary Certificate'),
        ('experience_cert', 'Experience Certificate'),
        ('visa_doc', 'Visa Document'),
        ('labor_card', 'Labor Card Document'),
        ('eos', 'End of Service Settlement'),
        ('gratuity', 'Gratuity Settlement'),
        ('leave_form', 'Leave Application'),
        ('loan_agreement', 'Loan Agreement'),
        ('training_agreement', 'Training Agreement'),
        ('probation_confirm', 'Probation Confirmation'),
        ('other', 'Other Document'),
    ], string='Document Type', default='contract', required=True, tracking=True)
    
    document_type_id = fields.Many2one(
        'signature.document.type',
        string='Document Category',
        ondelete='set null'
    )
    
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
        copy=False,
        help='SHA-256 hash of the original document for integrity verification'
    )
    document_size = fields.Integer(
        string='Document Size (bytes)',
        readonly=True
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
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True
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
    pending_count = fields.Integer(
        string='Pending Count',
        compute='_compute_signer_stats',
        store=True
    )
    
    # Signing Order
    signing_order = fields.Selection([
        ('parallel', 'All at Once'),
        ('sequential', 'In Order'),
    ], string='Signing Order', default='parallel', required=True)
    current_signer_sequence = fields.Integer(
        string='Current Signer Sequence',
        default=1
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
    
    # Priority
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='0')
    
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
    max_reminders = fields.Integer(
        string='Max Reminders',
        default=3
    )
    reminder_count = fields.Integer(
        string='Reminders Sent',
        default=0,
        readonly=True
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
        default=False,
        help='Require signers to log in before signing'
    )
    require_otp = fields.Boolean(
        string='Require OTP Verification',
        default=False,
        help='Send OTP to signer email/phone before signing'
    )
    
    # Certificate
    certificate_id = fields.Many2one(
        'signature.certificate',
        string='Signature Certificate',
        readonly=True,
        copy=False
    )
    certificate_generated = fields.Boolean(
        string='Certificate Generated',
        compute='_compute_certificate_generated'
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
    
    # Requestor
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    # Color for Kanban
    color = fields.Integer(string='Color')
    
    # Progress
    progress = fields.Float(
        string='Progress',
        compute='_compute_progress',
        store=True
    )

    @api.depends('signer_ids', 'signer_ids.state')
    def _compute_signer_stats(self):
        """Compute signer statistics."""
        for request in self:
            request.signer_count = len(request.signer_ids)
            request.signed_count = len(request.signer_ids.filtered(lambda s: s.state == 'signed'))
            request.pending_count = len(request.signer_ids.filtered(lambda s: s.state in ('pending', 'viewed')))

    @api.depends('signer_count', 'signed_count')
    def _compute_progress(self):
        """Compute signing progress percentage."""
        for request in self:
            if request.signer_count > 0:
                request.progress = (request.signed_count / request.signer_count) * 100
            else:
                request.progress = 0

    def _compute_certificate_generated(self):
        """Check if certificate has been generated."""
        for request in self:
            request.certificate_generated = bool(request.certificate_id)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence and access token."""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('signature.request') or _('New')
            if not vals.get('access_token'):
                vals['access_token'] = secrets.token_urlsafe(32)
            # Compute document hash and size
            if vals.get('document_file'):
                doc_bytes = base64.b64decode(vals['document_file'])
                vals['document_hash'] = hashlib.sha256(doc_bytes).hexdigest()
                vals['document_size'] = len(doc_bytes)
        return super().create(vals_list)

    def write(self, vals):
        """Override write to update document hash if document changes."""
        if vals.get('document_file'):
            doc_bytes = base64.b64decode(vals['document_file'])
            vals['document_hash'] = hashlib.sha256(doc_bytes).hexdigest()
            vals['document_size'] = len(doc_bytes)
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
        
        # Send emails based on signing order
        if self.signing_order == 'parallel':
            # Send to all signers at once
            for signer in self.signer_ids:
                signer._send_signature_request_email()
        else:
            # Send to first signer only
            first_signer = self.signer_ids.filtered(lambda s: s.sequence == 1)
            if first_signer:
                first_signer._send_signature_request_email()
            else:
                # If no sequence 1, send to first in list
                self.signer_ids[0]._send_signature_request_email()
        
        self.write({
            'state': 'sent',
            'sent_date': fields.Datetime.now(),
            'current_signer_sequence': 1,
        })
        self._log_audit('sent', _('Document sent for signature'))
        return True

    def action_send_reminder(self):
        """Send reminder to pending signers."""
        self.ensure_one()
        if self.reminder_count >= self.max_reminders:
            raise UserError(_('Maximum number of reminders (%d) already sent.') % self.max_reminders)
        
        pending_signers = self.signer_ids.filtered(lambda s: s.state in ('pending', 'viewed'))
        
        # For sequential signing, only remind current signer
        if self.signing_order == 'sequential':
            pending_signers = pending_signers.filtered(
                lambda s: s.sequence == self.current_signer_sequence
            )
        
        for signer in pending_signers:
            signer._send_reminder_email()
        
        self.write({
            'last_reminder_date': fields.Datetime.now(),
            'reminder_count': self.reminder_count + 1,
        })
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
            'reminder_count': 0,
            'current_signer_sequence': 1,
        })
        # Reset signer states
        self.signer_ids.write({
            'state': 'pending',
            'signature_data': False,
            'signed_date': False,
            'viewed_date': False,
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

    def action_generate_certificate(self):
        """Generate signature certificate."""
        self.ensure_one()
        if self.state != 'signed':
            raise UserError(_('Certificate can only be generated for completed signatures.'))
        if self.certificate_id:
            raise UserError(_('Certificate has already been generated.'))
        
        certificate = self.env['signature.certificate'].create({
            'request_id': self.id,
        })
        self.certificate_id = certificate.id
        self._log_audit('certificate', _('Signature certificate generated'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'signature.certificate',
            'res_id': certificate.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_certificate(self):
        """View the signature certificate."""
        self.ensure_one()
        if not self.certificate_id:
            raise UserError(_('No certificate available. Please generate one first.'))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'signature.certificate',
            'res_id': self.certificate_id.id,
            'view_mode': 'form',
            'target': 'current',
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
            
            # For sequential signing, notify next signer
            if self.signing_order == 'sequential':
                self._notify_next_signer()

    def _notify_next_signer(self):
        """Notify the next signer in sequential signing."""
        self.ensure_one()
        next_sequence = self.current_signer_sequence + 1
        next_signer = self.signer_ids.filtered(
            lambda s: s.sequence == next_sequence and s.state == 'pending'
        )
        if next_signer:
            next_signer._send_signature_request_email()
            self.current_signer_sequence = next_sequence

    def _generate_signed_document(self):
        """Generate the final signed document with all signatures."""
        # In a real implementation, this would merge signatures into the PDF
        # For now, we just copy the original document
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

    # ============================================================
    # CRON METHODS
    # ============================================================

    @api.model
    def cron_check_expiry(self):
        """Check and mark expired signature requests."""
        today = fields.Date.today()
        expired_requests = self.search([
            ('state', 'in', ['sent', 'partially_signed']),
            ('expiry_date', '<', today),
        ])
        for request in expired_requests:
            request.write({'state': 'expired'})
            request._log_audit('expired', _('Signature request expired'))

    @api.model
    def cron_send_reminders(self):
        """Send automatic reminders for pending signatures."""
        today = fields.Datetime.now()
        
        requests = self.search([
            ('state', 'in', ['sent', 'partially_signed']),
            ('reminder_enabled', '=', True),
        ])
        
        for request in requests:
            if request.reminder_count >= request.max_reminders:
                continue
            
            # Calculate if reminder is due
            last_action = request.last_reminder_date or request.sent_date
            if last_action:
                days_since = (today - last_action).days
                if days_since >= request.reminder_days:
                    try:
                        request.action_send_reminder()
                    except Exception:
                        pass  # Skip if reminder fails

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
        
        # Document type breakdown
        type_counts = {}
        for doc_type in ['contract', 'offer', 'nda', 'policy', 'termination', 'other']:
            type_counts[doc_type] = self.search_count([('document_type', '=', doc_type)])
        
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
            'type_counts': type_counts,
            'recent_activity': recent_activity,
            'trend_data': trend_data,
        }
