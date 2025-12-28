# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


class PortalMessage(models.Model):
    """Integrated Messaging System for Client Portal"""
    _name = 'client.portal.message'
    _description = 'Portal Message'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    # Message Content
    subject = fields.Char(string='Subject', required=True)
    body = fields.Html(string='Message Body', required=True)
    
    # Relationships
    client_id = fields.Many2one(
        'tazweed.client', string='Client',
        required=True, ondelete='cascade'
    )
    
    # Sender/Receiver
    direction = fields.Selection([
        ('incoming', 'From Client'),
        ('outgoing', 'To Client'),
    ], string='Direction', required=True)
    
    portal_user_id = fields.Many2one(
        'client.portal.user', string='Portal User',
        help='Client portal user who sent/received the message'
    )
    internal_user_id = fields.Many2one(
        'res.users', string='Internal User',
        help='Tazweed staff member'
    )
    
    # Thread/Conversation
    parent_id = fields.Many2one(
        'client.portal.message', string='Parent Message',
        ondelete='cascade'
    )
    child_ids = fields.One2many(
        'client.portal.message', 'parent_id',
        string='Replies'
    )
    thread_id = fields.Many2one(
        'client.portal.message.thread', string='Thread'
    )
    
    # Related Records
    job_order_id = fields.Many2one('tazweed.job.order', string='Related Job Order')
    placement_id = fields.Many2one('tazweed.placement', string='Related Placement')
    candidate_id = fields.Many2one('tazweed.candidate', string='Related Candidate')
    
    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Attachments'
    )
    attachment_count = fields.Integer(
        string='Attachment Count',
        compute='_compute_attachment_count'
    )
    
    # Status
    is_read = fields.Boolean(string='Read', default=False)
    read_date = fields.Datetime(string='Read Date')
    is_starred = fields.Boolean(string='Starred', default=False)
    is_archived = fields.Boolean(string='Archived', default=False)
    
    # Priority
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    # Category
    category = fields.Selection([
        ('general', 'General Inquiry'),
        ('job_order', 'Job Order Related'),
        ('candidate', 'Candidate Related'),
        ('placement', 'Placement Related'),
        ('invoice', 'Invoice/Billing'),
        ('support', 'Support Request'),
        ('feedback', 'Feedback'),
    ], string='Category', default='general')
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for message in self:
            message.attachment_count = len(message.attachment_ids)
    
    def action_mark_read(self):
        """Mark message as read"""
        self.write({
            'is_read': True,
            'read_date': fields.Datetime.now(),
        })
        return True
    
    def action_mark_unread(self):
        """Mark message as unread"""
        self.write({
            'is_read': False,
            'read_date': False,
        })
        return True
    
    def action_toggle_star(self):
        """Toggle starred status"""
        for message in self:
            message.is_starred = not message.is_starred
        return True
    
    def action_archive(self):
        """Archive message"""
        self.write({'is_archived': True})
        return True
    
    def action_unarchive(self):
        """Unarchive message"""
        self.write({'is_archived': False})
        return True
    
    def action_reply(self):
        """Open reply form"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reply'),
            'res_model': 'client.portal.message',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_client_id': self.client_id.id,
                'default_parent_id': self.id,
                'default_thread_id': self.thread_id.id if self.thread_id else False,
                'default_subject': f'Re: {self.subject}',
                'default_direction': 'outgoing' if self.direction == 'incoming' else 'incoming',
                'default_portal_user_id': self.portal_user_id.id,
                'default_category': self.category,
            }
        }
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        for record in records:
            # Create notification for recipient
            if record.direction == 'outgoing':
                # Notify client
                self.env['client.portal.notification'].create({
                    'client_id': record.client_id.id,
                    'portal_user_id': record.portal_user_id.id if record.portal_user_id else False,
                    'title': _('New Message'),
                    'message': record.subject,
                    'notification_type': 'message',
                    'reference_model': 'client.portal.message',
                    'reference_id': record.id,
                })
            else:
                # Notify internal team
                record.message_post(
                    body=_('New message from client: %s') % record.subject,
                    message_type='notification',
                )
        
        return records


class PortalMessageThread(models.Model):
    """Message Thread/Conversation"""
    _name = 'client.portal.message.thread'
    _description = 'Message Thread'
    _order = 'last_message_date desc'

    name = fields.Char(string='Thread Subject', required=True)
    client_id = fields.Many2one(
        'tazweed.client', string='Client',
        required=True, ondelete='cascade'
    )
    message_ids = fields.One2many(
        'client.portal.message', 'thread_id',
        string='Messages'
    )
    message_count = fields.Integer(
        string='Message Count',
        compute='_compute_message_count'
    )
    last_message_date = fields.Datetime(
        string='Last Message',
        compute='_compute_last_message'
    )
    last_message_preview = fields.Char(
        string='Last Message Preview',
        compute='_compute_last_message'
    )
    
    # Participants
    portal_user_ids = fields.Many2many(
        'client.portal.user', string='Client Participants'
    )
    internal_user_ids = fields.Many2many(
        'res.users', string='Internal Participants'
    )
    
    # Status
    state = fields.Selection([
        ('open', 'Open'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ], string='Status', default='open')
    
    @api.depends('message_ids')
    def _compute_message_count(self):
        for thread in self:
            thread.message_count = len(thread.message_ids)
    
    @api.depends('message_ids', 'message_ids.create_date')
    def _compute_last_message(self):
        for thread in self:
            if thread.message_ids:
                last_msg = thread.message_ids.sorted('create_date', reverse=True)[0]
                thread.last_message_date = last_msg.create_date
                # Strip HTML and truncate
                import re
                plain_text = re.sub('<[^<]+?>', '', last_msg.body or '')
                thread.last_message_preview = plain_text[:100] + '...' if len(plain_text) > 100 else plain_text
            else:
                thread.last_message_date = False
                thread.last_message_preview = ''
