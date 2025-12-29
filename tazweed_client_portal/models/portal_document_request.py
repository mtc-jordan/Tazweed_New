# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class ClientPortalDocumentEnhanced(models.Model):
    """Enhanced Document Management for Client Portal"""
    _name = 'client.portal.document.enhanced'
    _description = 'Enhanced Client Portal Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Document Name', required=True, tracking=True)
    client_id = fields.Many2one('tazweed.client', string='Client', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    
    document_type = fields.Selection([
        ('contract', 'Contract'),
        ('invoice', 'Invoice'),
        ('report', 'Report'),
        ('certificate', 'Certificate'),
        ('policy', 'Policy Document'),
        ('compliance', 'Compliance Document'),
        ('employee_doc', 'Employee Document'),
        ('other', 'Other'),
    ], string='Document Type', required=True, tracking=True)
    
    category_id = fields.Many2one('client.portal.document.category', string='Category')
    
    file = fields.Binary(string='File', required=True, attachment=True)
    filename = fields.Char(string='Filename')
    file_size = fields.Integer(string='File Size', compute='_compute_file_size', store=True)
    file_type = fields.Char(string='File Type', compute='_compute_file_type', store=True)
    
    description = fields.Text(string='Description')
    
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_expiry_status', store=True)
    days_to_expiry = fields.Integer(string='Days to Expiry', compute='_compute_expiry_status', store=True)
    
    visibility = fields.Selection([
        ('private', 'Private'),
        ('client', 'Client Visible'),
        ('employee', 'Employee Visible'),
        ('public', 'Public'),
    ], string='Visibility', default='client', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='active', tracking=True)
    
    shared_by = fields.Many2one('res.users', string='Shared By', default=lambda self: self.env.user)
    share_date = fields.Datetime(string='Share Date', default=fields.Datetime.now)
    
    download_count = fields.Integer(string='Download Count', default=0)
    last_downloaded = fields.Datetime(string='Last Downloaded')
    
    tags = fields.Many2many('client.portal.document.tag', string='Tags')
    
    @api.depends('file')
    def _compute_file_size(self):
        for record in self:
            if record.file:
                import base64
                record.file_size = len(base64.b64decode(record.file))
            else:
                record.file_size = 0
    
    @api.depends('filename')
    def _compute_file_type(self):
        for record in self:
            if record.filename:
                record.file_type = record.filename.split('.')[-1].upper() if '.' in record.filename else 'Unknown'
            else:
                record.file_type = 'Unknown'
    
    @api.depends('expiry_date')
    def _compute_expiry_status(self):
        today = fields.Date.today()
        for record in self:
            if record.expiry_date:
                record.days_to_expiry = (record.expiry_date - today).days
                record.is_expired = record.expiry_date < today
            else:
                record.days_to_expiry = 999
                record.is_expired = False
    
    def action_download(self):
        """Track document download"""
        self.ensure_one()
        self.download_count += 1
        self.last_downloaded = fields.Datetime.now()
        return True
    
    def action_archive(self):
        """Archive document"""
        self.write({'state': 'archived'})
    
    def action_restore(self):
        """Restore archived document"""
        self.write({'state': 'active'})


class ClientPortalDocumentCategory(models.Model):
    """Document Category for Organization"""
    _name = 'client.portal.document.category'
    _description = 'Document Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    parent_id = fields.Many2one('client.portal.document.category', string='Parent Category')
    child_ids = fields.One2many('client.portal.document.category', 'parent_id', string='Sub Categories')
    document_count = fields.Integer(string='Document Count', compute='_compute_document_count')
    
    @api.depends()
    def _compute_document_count(self):
        for record in self:
            record.document_count = self.env['client.portal.document.enhanced'].search_count([
                ('category_id', '=', record.id)
            ])


class ClientPortalDocumentTag(models.Model):
    """Document Tags for Filtering"""
    _name = 'client.portal.document.tag'
    _description = 'Document Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color Index')


class ClientRequestEnhanced(models.Model):
    """Enhanced Client Request Management"""
    _inherit = 'client.request'

    # Additional fields for enhanced functionality
    priority_level = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority Level', default='normal', tracking=True)
    
    estimated_completion = fields.Datetime(string='Estimated Completion')
    actual_completion = fields.Datetime(string='Actual Completion')
    
    related_employee_ids = fields.Many2many('hr.employee', 'quick_action_employee_rel', 'action_id', 'employee_id', string='Related Employees')
    related_document_ids = fields.Many2many('client.portal.document.enhanced', string='Related Documents')
    
    feedback_rating = fields.Selection([
        ('1', '1 - Very Poor'),
        ('2', '2 - Poor'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Feedback Rating')
    feedback_comment = fields.Text(string='Feedback Comment')
    feedback_date = fields.Datetime(string='Feedback Date')
    
    timeline_ids = fields.One2many('client.request.timeline', 'request_id', string='Timeline')
    
    @api.model
    def create(self, vals):
        """Override create to add timeline entry"""
        record = super().create(vals)
        record._add_timeline_entry('created', 'Request created')
        return record
    
    def write(self, vals):
        """Override write to track state changes"""
        old_states = {r.id: r.state for r in self}
        result = super().write(vals)
        
        if 'state' in vals:
            for record in self:
                old_state = old_states.get(record.id)
                if old_state != vals['state']:
                    record._add_timeline_entry(
                        'state_change',
                        f'Status changed from {old_state} to {vals["state"]}'
                    )
        
        return result
    
    def _add_timeline_entry(self, entry_type, description):
        """Add a timeline entry"""
        self.env['client.request.timeline'].create({
            'request_id': self.id,
            'entry_type': entry_type,
            'description': description,
            'user_id': self.env.user.id,
        })
    
    def action_submit_feedback(self, rating, comment):
        """Submit feedback for completed request"""
        self.ensure_one()
        if self.state != 'completed':
            raise UserError(_('Feedback can only be submitted for completed requests'))
        
        self.write({
            'feedback_rating': str(rating),
            'feedback_comment': comment,
            'feedback_date': fields.Datetime.now(),
        })
        
        self._add_timeline_entry('feedback', f'Feedback submitted: {rating}/5')
        return True


class ClientRequestTimeline(models.Model):
    """Request Timeline for Tracking Progress"""
    _name = 'client.request.timeline'
    _description = 'Client Request Timeline'
    _order = 'create_date desc'

    request_id = fields.Many2one('client.request', string='Request', required=True, ondelete='cascade')
    entry_type = fields.Selection([
        ('created', 'Created'),
        ('state_change', 'Status Change'),
        ('comment', 'Comment'),
        ('document', 'Document Added'),
        ('assignment', 'Assignment'),
        ('feedback', 'Feedback'),
        ('other', 'Other'),
    ], string='Entry Type', required=True)
    
    description = fields.Text(string='Description', required=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    create_date = fields.Datetime(string='Date', default=fields.Datetime.now)


class ClientRequestQuickAction(models.Model):
    """Quick Actions for Common Requests"""
    _name = 'client.request.quick.action'
    _description = 'Quick Request Action'
    _order = 'sequence, name'

    name = fields.Char(string='Action Name', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    request_type = fields.Selection([
        ('employee', 'Employee Related'),
        ('document', 'Document Related'),
        ('payroll', 'Payroll Related'),
        ('visa', 'Visa/Immigration'),
        ('general', 'General'),
    ], string='Request Type', required=True)
    
    default_subject = fields.Char(string='Default Subject')
    default_description = fields.Text(string='Default Description')
    default_priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Default Priority', default='normal')
    
    requires_employee = fields.Boolean(string='Requires Employee Selection')
    requires_document = fields.Boolean(string='Requires Document Upload')
    requires_date = fields.Boolean(string='Requires Date Selection')
    
    icon = fields.Char(string='Icon Class', default='fa-ticket')
    color = fields.Char(string='Color', default='primary')
    
    active = fields.Boolean(string='Active', default=True)
    
    @api.model
    def get_quick_actions_for_portal(self, client_id):
        """Get available quick actions for client portal"""
        actions = self.search([('active', '=', True)])
        return [{
            'id': a.id,
            'name': a.name,
            'code': a.code,
            'type': a.request_type,
            'icon': a.icon,
            'color': a.color,
            'requires_employee': a.requires_employee,
            'requires_document': a.requires_document,
            'requires_date': a.requires_date,
        } for a in actions]
    
    def create_request_from_action(self, client_id, data):
        """Create a request from quick action"""
        self.ensure_one()
        
        vals = {
            'client_id': client_id,
            'subject': data.get('subject', self.default_subject),
            'description': data.get('description', self.default_description),
            'priority_level': data.get('priority', self.default_priority),
            'request_type': data.get('request_type_id'),
        }
        
        if self.requires_employee and data.get('employee_id'):
            vals['related_employee_ids'] = [(4, data['employee_id'])]
        
        return self.env['client.request'].create(vals)


class ClientPortalNotificationPreference(models.Model):
    """Client Notification Preferences"""
    _name = 'client.portal.notification.preference'
    _description = 'Client Notification Preferences'

    client_id = fields.Many2one('tazweed.client', string='Client', required=True)
    user_id = fields.Many2one('res.users', string='Portal User', required=True)
    
    # Email notifications
    email_new_invoice = fields.Boolean(string='New Invoice', default=True)
    email_invoice_due = fields.Boolean(string='Invoice Due Reminder', default=True)
    email_candidate_submitted = fields.Boolean(string='Candidate Submitted', default=True)
    email_placement_update = fields.Boolean(string='Placement Updates', default=True)
    email_document_shared = fields.Boolean(string='Document Shared', default=True)
    email_request_update = fields.Boolean(string='Request Updates', default=True)
    email_document_expiry = fields.Boolean(string='Document Expiry Alerts', default=True)
    
    # Email digest
    email_digest_enabled = fields.Boolean(string='Enable Email Digest', default=False)
    email_digest_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Digest Frequency', default='weekly')
    
    # Portal notifications
    portal_show_alerts = fields.Boolean(string='Show Portal Alerts', default=True)
    portal_show_activity = fields.Boolean(string='Show Activity Feed', default=True)
    
    _sql_constraints = [
        ('unique_client_user', 'unique(client_id, user_id)', 
         'Notification preferences already exist for this client and user')
    ]
