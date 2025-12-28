"""
Tazweed Automated Workflows - Notification Template Model
Manages notification templates and sending
"""

from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class NotificationTemplate(models.Model):
    """Notification Template Model"""
    
    _name = 'tazweed.notification.template'
    _description = 'Notification Template'
    _inherit = ['mail.thread']

    # ============================================================
    # Basic Information
    # ============================================================
    
    name = fields.Char('Template Name', required=True, tracking=True)
    code = fields.Char('Template Code', required=True, unique=True, tracking=True)
    description = fields.Text('Description')
    
    # ============================================================
    # Trigger Configuration
    # ============================================================
    
    trigger_event = fields.Selection([
        ('workflow_start', 'Workflow Start'),
        ('workflow_approval', 'Workflow Approval'),
        ('workflow_rejection', 'Workflow Rejection'),
        ('workflow_completion', 'Workflow Completion'),
        ('task_execution', 'Task Execution'),
        ('task_failure', 'Task Failure'),
        ('approval_request', 'Approval Request'),
        ('approval_approved', 'Approval Approved'),
        ('approval_rejected', 'Approval Rejected'),
        ('custom', 'Custom Event')
    ], string='Trigger Event', required=True)
    
    # ============================================================
    # Notification Type
    # ============================================================
    
    notification_type = fields.Selection([
        ('email', 'Email'),
        ('in_app', 'In-App Notification'),
        ('sms', 'SMS'),
        ('webhook', 'Webhook'),
        ('multi', 'Multiple Channels')
    ], string='Notification Type', required=True, default='email')
    
    # ============================================================
    # Email Configuration
    # ============================================================
    
    email_subject = fields.Char('Email Subject')
    email_body = fields.Html('Email Body')
    email_recipients = fields.Char('Email Recipients', help='Comma-separated or dynamic: ${approver_email}')
    email_cc = fields.Char('CC')
    email_bcc = fields.Char('BCC')
    
    # ============================================================
    # In-App Notification
    # ============================================================
    
    notification_title = fields.Char('Notification Title')
    notification_message = fields.Text('Notification Message')
    notification_type_display = fields.Selection([
        ('info', 'Info'),
        ('success', 'Success'),
        ('warning', 'Warning'),
        ('danger', 'Danger')
    ], string='Display Type', default='info')
    
    # ============================================================
    # SMS Configuration
    # ============================================================
    
    sms_message = fields.Text('SMS Message', help='Max 160 characters')
    sms_recipients = fields.Char('SMS Recipients', help='Phone numbers')
    
    # ============================================================
    # Webhook Configuration
    # ============================================================
    
    webhook_url = fields.Char('Webhook URL')
    webhook_method = fields.Selection([
        ('post', 'POST'),
        ('get', 'GET'),
        ('put', 'PUT'),
        ('patch', 'PATCH'),
        ('delete', 'DELETE')
    ], string='HTTP Method', default='post')
    
    webhook_payload = fields.Text('Webhook Payload', help='JSON payload template')
    
    # ============================================================
    # Variables & Templating
    # ============================================================
    
    available_variables = fields.Text('Available Variables', readonly=True, help='Variables available for this template')
    
    # ============================================================
    # Scheduling
    # ============================================================
    
    send_immediately = fields.Boolean('Send Immediately', default=True)
    schedule_delay_minutes = fields.Integer('Delay (minutes)', default=0)
    
    # ============================================================
    # Status & Tracking
    # ============================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived')
    ], string='State', default='draft', tracking=True)
    
    is_active = fields.Boolean('Is Active', default=True)
    
    # ============================================================
    # Statistics
    # ============================================================
    
    total_sent = fields.Integer('Total Sent', readonly=True, default=0)
    total_failed = fields.Integer('Total Failed', readonly=True, default=0)
    
    notification_logs = fields.One2many(
        'tazweed.notification.log',
        'template_id',
        string='Notification Logs',
        readonly=True
    )
    
    # ============================================================
    # Audit Trail
    # ============================================================
    
    created_by = fields.Many2one('res.users', 'Created By', readonly=True, default=lambda self: self.env.user)
    created_date = fields.Datetime('Created Date', readonly=True, default=fields.Datetime.now)
    
    # ============================================================
    # Methods
    # ============================================================
    
    @api.model
    def create(self, vals):
        """Create notification template"""
        vals['created_by'] = self.env.user.id
        return super().create(vals)
    
    def action_activate(self):
        """Activate template"""
        self.write({
            'state': 'active',
            'is_active': True
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Template "{self.name}" activated',
                'type': 'success'
            }
        }
    
    def action_deactivate(self):
        """Deactivate template"""
        self.write({
            'state': 'inactive',
            'is_active': False
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Template "{self.name}" deactivated',
                'type': 'success'
            }
        }
    
    def action_test_notification(self):
        """Test notification sending"""
        try:
            # Send test notification
            self.send_notification(record=None, is_test=True)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Test notification sent',
                    'type': 'success'
                }
            }
        
        except Exception as e:
            _logger.error(f'Error sending test notification: {str(e)}')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to send test notification: {str(e)}',
                    'type': 'danger'
                }
            }
    
    def send_notification(self, record=None, is_test=False):
        """Send notification"""
        try:
            # Check if template is active
            if not self.is_active and not is_test:
                return False
            
            # Prepare variables
            variables = self._prepare_variables(record)
            
            # Send based on notification type
            if self.notification_type in ['email', 'multi']:
                self._send_email(variables, is_test)
            
            if self.notification_type in ['in_app', 'multi']:
                self._send_in_app(variables, is_test)
            
            if self.notification_type in ['sms', 'multi']:
                self._send_sms(variables, is_test)
            
            if self.notification_type in ['webhook', 'multi']:
                self._send_webhook(variables, is_test)
            
            # Update statistics
            if not is_test:
                self.total_sent += 1
                
                # Log notification
                self.env['tazweed.notification.log'].create({
                    'template_id': self.id,
                    'status': 'sent',
                    'description': 'Notification sent successfully'
                })
            
            return True
        
        except Exception as e:
            _logger.error(f'Error sending notification: {str(e)}')
            
            if not is_test:
                self.total_failed += 1
                
                # Log error
                self.env['tazweed.notification.log'].create({
                    'template_id': self.id,
                    'status': 'failed',
                    'description': f'Error: {str(e)}'
                })
            
            return False
    
    def _prepare_variables(self, record):
        """Prepare template variables"""
        variables = {
            'current_date': datetime.now().strftime('%Y-%m-%d'),
            'current_time': datetime.now().strftime('%H:%M:%S'),
            'current_user': self.env.user.name,
        }
        
        if record:
            variables.update({
                'record_name': record.name if hasattr(record, 'name') else str(record),
                'record_id': record.id,
            })
        
        return variables
    
    def _send_email(self, variables, is_test=False):
        """Send email notification"""
        subject = self.email_subject
        body = self.email_body
        
        # Replace variables
        for key, value in variables.items():
            subject = subject.replace(f'${{{key}}}', str(value))
            body = body.replace(f'${{{key}}}', str(value))
        
        # Get recipients
        recipients = self.email_recipients
        for key, value in variables.items():
            recipients = recipients.replace(f'${{{key}}}', str(value))
        
        if is_test:
            recipients = self.env.user.email
        
        # Send email
        mail_values = {
            'subject': subject,
            'body_html': body,
            'email_to': recipients,
            'email_cc': self.email_cc,
            'email_bcc': self.email_bcc,
        }
        
        self.env['mail.mail'].create(mail_values).send()
    
    def _send_in_app(self, variables, is_test=False):
        """Send in-app notification"""
        title = self.notification_title
        message = self.notification_message
        
        # Replace variables
        for key, value in variables.items():
            title = title.replace(f'${{{key}}}', str(value))
            message = message.replace(f'${{{key}}}', str(value))
        
        # Create notification
        self.env['bus.bus'].sendone(
            (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
            {
                'type': 'notification',
                'title': title,
                'message': message,
                'notification_type': self.notification_type_display,
            }
        )
    
    def _send_sms(self, variables, is_test=False):
        """Send SMS notification"""
        message = self.sms_message
        
        # Replace variables
        for key, value in variables.items():
            message = message.replace(f'${{{key}}}', str(value))
        
        # Get recipients
        recipients = self.sms_recipients
        for key, value in variables.items():
            recipients = recipients.replace(f'${{{key}}}', str(value))
        
        # Send SMS (integration with SMS provider)
        _logger.info(f'SMS sent to {recipients}: {message}')
    
    def _send_webhook(self, variables, is_test=False):
        """Send webhook notification"""
        import requests
        import json
        
        payload = self.webhook_payload
        
        # Replace variables
        for key, value in variables.items():
            payload = payload.replace(f'${{{key}}}', str(value))
        
        # Send webhook
        try:
            if self.webhook_method == 'post':
                requests.post(self.webhook_url, json=json.loads(payload))
            elif self.webhook_method == 'get':
                requests.get(self.webhook_url)
            elif self.webhook_method == 'put':
                requests.put(self.webhook_url, json=json.loads(payload))
            elif self.webhook_method == 'patch':
                requests.patch(self.webhook_url, json=json.loads(payload))
            elif self.webhook_method == 'delete':
                requests.delete(self.webhook_url)
        
        except Exception as e:
            _logger.error(f'Error sending webhook: {str(e)}')


class NotificationLog(models.Model):
    """Notification Log Model"""
    
    _name = 'tazweed.notification.log'
    _description = 'Notification Log'
    _order = 'create_date desc'
    
    template_id = fields.Many2one(
        'tazweed.notification.template',
        string='Template',
        required=True,
        ondelete='cascade'
    )
    
    status = fields.Selection([
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('pending', 'Pending')
    ], string='Status', required=True)
    
    description = fields.Text('Description')
    
    sent_date = fields.Datetime('Sent Date', readonly=True, default=fields.Datetime.now)
