# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class PortalNotification(models.Model):
    """Real-time Notifications for Client Portal"""
    _name = 'client.portal.notification'
    _description = 'Portal Notification'
    _order = 'create_date desc'

    # Content
    title = fields.Char(string='Title', required=True)
    message = fields.Text(string='Message', required=True)
    
    # Recipient
    client_id = fields.Many2one(
        'tazweed.client', string='Client',
        required=True, ondelete='cascade'
    )
    portal_user_id = fields.Many2one(
        'client.portal.user', string='Specific User',
        help='Leave empty to notify all client users'
    )
    
    # Type & Category
    notification_type = fields.Selection([
        ('info', 'Information'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('message', 'New Message'),
        ('document', 'Document Shared'),
        ('candidate', 'Candidate Update'),
        ('placement', 'Placement Update'),
        ('invoice', 'Invoice'),
        ('job_order', 'Job Order Update'),
    ], string='Type', default='info', required=True)
    
    icon = fields.Char(string='Icon', compute='_compute_icon')
    color = fields.Char(string='Color', compute='_compute_color')
    
    # Reference
    reference_model = fields.Char(string='Reference Model')
    reference_id = fields.Integer(string='Reference ID')
    action_url = fields.Char(string='Action URL', compute='_compute_action_url')
    
    # Status
    is_read = fields.Boolean(string='Read', default=False)
    read_date = fields.Datetime(string='Read Date')
    is_dismissed = fields.Boolean(string='Dismissed', default=False)
    
    # Delivery
    send_email = fields.Boolean(string='Send Email', default=True)
    email_sent = fields.Boolean(string='Email Sent', readonly=True)
    send_sms = fields.Boolean(string='Send SMS', default=False)
    sms_sent = fields.Boolean(string='SMS Sent', readonly=True)
    
    # Expiry
    expiry_date = fields.Datetime(string='Expiry Date')
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired')
    
    @api.depends('notification_type')
    def _compute_icon(self):
        icon_map = {
            'info': 'fa-info-circle',
            'success': 'fa-check-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-times-circle',
            'message': 'fa-envelope',
            'document': 'fa-file',
            'candidate': 'fa-user',
            'placement': 'fa-user-plus',
            'invoice': 'fa-file-invoice-dollar',
            'job_order': 'fa-briefcase',
        }
        for notif in self:
            notif.icon = icon_map.get(notif.notification_type, 'fa-bell')
    
    @api.depends('notification_type')
    def _compute_color(self):
        color_map = {
            'info': '#2196F3',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'message': '#9C27B0',
            'document': '#607D8B',
            'candidate': '#00BCD4',
            'placement': '#8BC34A',
            'invoice': '#FF5722',
            'job_order': '#3F51B5',
        }
        for notif in self:
            notif.color = color_map.get(notif.notification_type, '#757575')
    
    @api.depends('reference_model', 'reference_id')
    def _compute_action_url(self):
        for notif in self:
            if notif.reference_model and notif.reference_id:
                # Map model to portal URL
                url_map = {
                    'client.portal.message': f'/my/messages/{notif.reference_id}',
                    'client.portal.document': f'/my/documents/{notif.reference_id}',
                    'tazweed.candidate': f'/my/candidates/{notif.reference_id}',
                    'tazweed.placement': f'/my/placements/{notif.reference_id}',
                    'tazweed.client.invoice': f'/my/invoices/{notif.reference_id}',
                    'tazweed.job.order': f'/my/job-orders/{notif.reference_id}',
                }
                notif.action_url = url_map.get(notif.reference_model, '/my')
            else:
                notif.action_url = '/my'
    
    @api.depends('expiry_date')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for notif in self:
            notif.is_expired = notif.expiry_date and notif.expiry_date < now
    
    def action_mark_read(self):
        """Mark notification as read"""
        self.write({
            'is_read': True,
            'read_date': fields.Datetime.now(),
        })
        return True
    
    def action_dismiss(self):
        """Dismiss notification"""
        self.write({
            'is_dismissed': True,
            'is_read': True,
        })
        return True
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        for record in records:
            # Send email notification if enabled
            if record.send_email:
                record._send_email_notification()
            
            # Send SMS if enabled
            if record.send_sms:
                record._send_sms_notification()
        
        return records
    
    def _send_email_notification(self):
        """Send email notification"""
        self.ensure_one()
        template = self.env.ref(
            'tazweed_client_portal.email_template_portal_notification',
            raise_if_not_found=False
        )
        if template:
            # Get recipients
            if self.portal_user_id:
                recipients = self.portal_user_id
            else:
                recipients = self.client_id.portal_user_ids.filtered(
                    lambda u: u.state == 'active' and u.notify_email
                )
            
            for recipient in recipients:
                template.with_context(recipient=recipient).send_mail(
                    self.id, force_send=False
                )
            
            self.email_sent = True
    
    def _send_sms_notification(self):
        """Send SMS notification (placeholder for SMS gateway integration)"""
        self.ensure_one()
        # TODO: Integrate with SMS gateway (Twilio, etc.)
        self.sms_sent = True
    
    @api.model
    def cleanup_old_notifications(self, days=30):
        """Cleanup old read/dismissed notifications"""
        cutoff_date = datetime.now() - timedelta(days=days)
        old_notifications = self.search([
            '|',
            ('is_read', '=', True),
            ('is_dismissed', '=', True),
            ('create_date', '<', cutoff_date),
        ])
        old_notifications.unlink()
        return True
    
    @api.model
    def get_unread_count(self, client_id, portal_user_id=False):
        """Get unread notification count for client/user"""
        domain = [
            ('client_id', '=', client_id),
            ('is_read', '=', False),
            ('is_dismissed', '=', False),
            '|',
            ('is_expired', '=', False),
            ('expiry_date', '=', False),
        ]
        if portal_user_id:
            domain.extend([
                '|',
                ('portal_user_id', '=', False),
                ('portal_user_id', '=', portal_user_id),
            ])
        return self.search_count(domain)
