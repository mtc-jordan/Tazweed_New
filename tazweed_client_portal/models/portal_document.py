# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
import hashlib
import base64
from datetime import datetime


class PortalDocument(models.Model):
    """Secure Document Sharing with Audit Trail"""
    _name = 'client.portal.document'
    _description = 'Portal Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Document Name', required=True, tracking=True)
    description = fields.Text(string='Description')
    
    # File Information
    file = fields.Binary(string='File', required=True, attachment=True)
    file_name = fields.Char(string='File Name')
    file_size = fields.Integer(string='File Size (bytes)', compute='_compute_file_info', store=True)
    file_type = fields.Char(string='File Type', compute='_compute_file_info', store=True)
    file_hash = fields.Char(string='File Hash (SHA256)', compute='_compute_file_info', store=True)
    
    # Relationships
    client_id = fields.Many2one(
        'tazweed.client', string='Client', 
        required=True, ondelete='cascade', tracking=True
    )
    uploaded_by_id = fields.Many2one(
        'res.users', string='Uploaded By', 
        default=lambda self: self.env.user, readonly=True
    )
    portal_user_id = fields.Many2one(
        'client.portal.user', string='Portal User',
        help='If uploaded by portal user'
    )
    
    # Related Records
    job_order_id = fields.Many2one('tazweed.job.order', string='Related Job Order')
    placement_id = fields.Many2one('tazweed.placement', string='Related Placement')
    invoice_id = fields.Many2one('tazweed.client.invoice', string='Related Invoice')
    
    # Classification
    category = fields.Selection([
        ('contract', 'Contract'),
        ('invoice', 'Invoice'),
        ('report', 'Report'),
        ('compliance', 'Compliance Document'),
        ('timesheet', 'Timesheet'),
        ('certificate', 'Certificate'),
        ('policy', 'Policy Document'),
        ('other', 'Other'),
    ], string='Category', default='other', tracking=True)
    
    tags = fields.Many2many('client.portal.document.tag', string='Tags')
    
    # Access Control
    visibility = fields.Selection([
        ('private', 'Private (Internal Only)'),
        ('client', 'Client Visible'),
        ('public', 'Public'),
    ], string='Visibility', default='client', tracking=True)
    
    requires_acknowledgment = fields.Boolean(
        string='Requires Acknowledgment', 
        help='Client must acknowledge receipt of this document'
    )
    acknowledged = fields.Boolean(string='Acknowledged', readonly=True)
    acknowledged_by_id = fields.Many2one(
        'client.portal.user', string='Acknowledged By', readonly=True
    )
    acknowledged_date = fields.Datetime(string='Acknowledged Date', readonly=True)
    
    # Version Control
    version = fields.Integer(string='Version', default=1)
    parent_document_id = fields.Many2one(
        'client.portal.document', string='Previous Version'
    )
    child_document_ids = fields.One2many(
        'client.portal.document', 'parent_document_id', 
        string='Newer Versions'
    )
    is_latest = fields.Boolean(string='Is Latest Version', default=True)
    
    # Expiry
    expiry_date = fields.Date(string='Expiry Date')
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    
    # Audit Trail
    download_count = fields.Integer(string='Download Count', default=0, readonly=True)
    last_downloaded = fields.Datetime(string='Last Downloaded', readonly=True)
    access_log_ids = fields.One2many(
        'client.portal.document.access', 'document_id',
        string='Access Log'
    )
    
    @api.depends('file')
    def _compute_file_info(self):
        for doc in self:
            if doc.file:
                file_content = base64.b64decode(doc.file)
                doc.file_size = len(file_content)
                doc.file_hash = hashlib.sha256(file_content).hexdigest()
                
                # Determine file type from extension
                if doc.file_name:
                    ext = doc.file_name.split('.')[-1].lower() if '.' in doc.file_name else ''
                    doc.file_type = ext
                else:
                    doc.file_type = 'unknown'
            else:
                doc.file_size = 0
                doc.file_hash = False
                doc.file_type = False
    
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for doc in self:
            doc.is_expired = doc.expiry_date and doc.expiry_date < today
    
    def action_acknowledge(self, portal_user_id):
        """Mark document as acknowledged by client"""
        self.ensure_one()
        self.write({
            'acknowledged': True,
            'acknowledged_by_id': portal_user_id,
            'acknowledged_date': fields.Datetime.now(),
        })
        self._log_access('acknowledge', portal_user_id)
        return True
    
    def action_download(self, portal_user_id=False):
        """Record document download"""
        self.ensure_one()
        self.write({
            'download_count': self.download_count + 1,
            'last_downloaded': fields.Datetime.now(),
        })
        self._log_access('download', portal_user_id)
        return True
    
    def action_create_new_version(self):
        """Create a new version of this document"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upload New Version'),
            'res_model': 'client.portal.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_name': self.name,
                'default_client_id': self.client_id.id,
                'default_category': self.category,
                'default_parent_document_id': self.id,
                'default_version': self.version + 1,
            }
        }
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # If this is a new version, mark previous as not latest
            if vals.get('parent_document_id'):
                parent = self.browse(vals['parent_document_id'])
                parent.is_latest = False
        
        records = super().create(vals_list)
        
        # Send notification if client visible
        for record in records:
            if record.visibility == 'client':
                record._send_document_notification()
        
        return records
    
    def _send_document_notification(self):
        """Send notification to client about new document"""
        self.ensure_one()
        self.env['client.portal.notification'].create({
            'client_id': self.client_id.id,
            'title': _('New Document Shared'),
            'message': _('A new document "%s" has been shared with you.') % self.name,
            'notification_type': 'document',
            'reference_model': 'client.portal.document',
            'reference_id': self.id,
        })
    
    def _log_access(self, action, portal_user_id=False):
        """Log document access for audit trail"""
        self.ensure_one()
        self.env['client.portal.document.access'].create({
            'document_id': self.id,
            'portal_user_id': portal_user_id,
            'user_id': self.env.user.id,
            'action': action,
            'ip_address': self.env.context.get('remote_ip', 'Unknown'),
        })


class PortalDocumentTag(models.Model):
    """Document Tags for Organization"""
    _name = 'client.portal.document.tag'
    _description = 'Document Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color Index')
    
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Tag name must be unique!')
    ]


class PortalDocumentAccess(models.Model):
    """Document Access Audit Log"""
    _name = 'client.portal.document.access'
    _description = 'Document Access Log'
    _order = 'access_time desc'

    document_id = fields.Many2one(
        'client.portal.document', string='Document',
        required=True, ondelete='cascade'
    )
    portal_user_id = fields.Many2one('client.portal.user', string='Portal User')
    user_id = fields.Many2one('res.users', string='System User')
    action = fields.Selection([
        ('view', 'Viewed'),
        ('download', 'Downloaded'),
        ('acknowledge', 'Acknowledged'),
        ('share', 'Shared'),
    ], string='Action', required=True)
    access_time = fields.Datetime(
        string='Access Time', 
        default=fields.Datetime.now, 
        readonly=True
    )
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')
