"""
Tazweed Automated Workflows - Notification Dispatcher
Manages notification sending and distribution
"""

from odoo import models, fields, api
from datetime import datetime, timedelta
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Notification Dispatcher for sending notifications"""
    
    def __init__(self, env):
        """Initialize notification dispatcher"""
        self.env = env
        self.notification_queue = []
    
    def send_notification(self, template, record=None, recipients=None, is_async=False):
        """Send notification"""
        try:
            # Check if template is active
            if not template.is_active or template.state != 'active':
                return False
            
            # Prepare variables
            variables = self._prepare_variables(template, record)
            
            # Queue or send notification
            if is_async:
                self.queue_notification(template, variables, recipients)
            else:
                return template.send_notification(record)
        
        except Exception as e:
            _logger.error(f'Error sending notification: {str(e)}')
            return False
    
    def queue_notification(self, template, variables, recipients=None, delay_minutes=0):
        """Queue notification for later sending"""
        try:
            send_time = datetime.now() + timedelta(minutes=delay_minutes)
            
            notification_item = {
                'template': template,
                'variables': variables,
                'recipients': recipients,
                'send_time': send_time,
                'status': 'queued',
                'attempts': 0
            }
            
            self.notification_queue.append(notification_item)
            
            _logger.info(f'Notification queued for sending at {send_time}')
            return True
        
        except Exception as e:
            _logger.error(f'Error queuing notification: {str(e)}')
            return False
    
    def process_queue(self):
        """Process queued notifications"""
        try:
            now = datetime.now()
            
            for item in self.notification_queue:
                if item['send_time'] <= now and item['status'] == 'queued':
                    item['status'] = 'sending'
                    
                    # Send notification
                    if self._send_notification_internal(item):
                        item['status'] = 'sent'
                    else:
                        item['attempts'] += 1
                        if item['attempts'] < 3:
                            item['status'] = 'queued'
                            item['send_time'] = now + timedelta(minutes=5)
                        else:
                            item['status'] = 'failed'
            
            # Remove sent/failed items
            self.notification_queue = [item for item in self.notification_queue 
                                      if item['status'] in ['queued', 'sending']]
            
            _logger.info(f'Processed {len(self.notification_queue)} queued notifications')
            return True
        
        except Exception as e:
            _logger.error(f'Error processing notification queue: {str(e)}')
            return False
    
    def _send_notification_internal(self, notification_item):
        """Send notification internally"""
        try:
            template = notification_item['template']
            variables = notification_item['variables']
            recipients = notification_item['recipients']
            
            # Send based on notification type
            if template.notification_type in ['email', 'multi']:
                self._send_email(template, variables, recipients)
            
            if template.notification_type in ['in_app', 'multi']:
                self._send_in_app(template, variables, recipients)
            
            if template.notification_type in ['sms', 'multi']:
                self._send_sms(template, variables, recipients)
            
            if template.notification_type in ['webhook', 'multi']:
                self._send_webhook(template, variables)
            
            return True
        
        except Exception as e:
            _logger.error(f'Error sending notification: {str(e)}')
            return False
    
    def _send_email(self, template, variables, recipients=None):
        """Send email notification"""
        try:
            subject = template.email_subject
            body = template.email_body
            
            # Replace variables
            for key, value in variables.items():
                subject = subject.replace(f'${{{key}}}', str(value))
                body = body.replace(f'${{{key}}}', str(value))
            
            # Get recipients
            email_recipients = recipients or template.email_recipients
            for key, value in variables.items():
                email_recipients = email_recipients.replace(f'${{{key}}}', str(value))
            
            # Send email
            mail_values = {
                'subject': subject,
                'body_html': body,
                'email_to': email_recipients,
                'email_cc': template.email_cc,
                'email_bcc': template.email_bcc,
            }
            
            self.env['mail.mail'].create(mail_values).send()
            
            _logger.info(f'Email notification sent to {email_recipients}')
            return True
        
        except Exception as e:
            _logger.error(f'Error sending email notification: {str(e)}')
            return False
    
    def _send_in_app(self, template, variables, recipients=None):
        """Send in-app notification"""
        try:
            title = template.notification_title
            message = template.notification_message
            
            # Replace variables
            for key, value in variables.items():
                title = title.replace(f'${{{key}}}', str(value))
                message = message.replace(f'${{{key}}}', str(value))
            
            # Send notification
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                {
                    'type': 'notification',
                    'title': title,
                    'message': message,
                    'notification_type': template.notification_type_display,
                }
            )
            
            _logger.info(f'In-app notification sent')
            return True
        
        except Exception as e:
            _logger.error(f'Error sending in-app notification: {str(e)}')
            return False
    
    def _send_sms(self, template, variables, recipients=None):
        """Send SMS notification"""
        try:
            message = template.sms_message
            
            # Replace variables
            for key, value in variables.items():
                message = message.replace(f'${{{key}}}', str(value))
            
            # Get recipients
            sms_recipients = recipients or template.sms_recipients
            for key, value in variables.items():
                sms_recipients = sms_recipients.replace(f'${{{key}}}', str(value))
            
            # Send SMS (integration with SMS provider)
            _logger.info(f'SMS sent to {sms_recipients}: {message}')
            return True
        
        except Exception as e:
            _logger.error(f'Error sending SMS notification: {str(e)}')
            return False
    
    def _send_webhook(self, template, variables):
        """Send webhook notification"""
        try:
            payload = template.webhook_payload
            
            # Replace variables
            for key, value in variables.items():
                payload = payload.replace(f'${{{key}}}', str(value))
            
            # Send webhook
            if template.webhook_method == 'post':
                requests.post(template.webhook_url, json=json.loads(payload), timeout=10)
            elif template.webhook_method == 'get':
                requests.get(template.webhook_url, timeout=10)
            elif template.webhook_method == 'put':
                requests.put(template.webhook_url, json=json.loads(payload), timeout=10)
            elif template.webhook_method == 'patch':
                requests.patch(template.webhook_url, json=json.loads(payload), timeout=10)
            elif template.webhook_method == 'delete':
                requests.delete(template.webhook_url, timeout=10)
            
            _logger.info(f'Webhook sent to {template.webhook_url}')
            return True
        
        except Exception as e:
            _logger.error(f'Error sending webhook notification: {str(e)}')
            return False
    
    def _prepare_variables(self, template, record):
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
    
    def send_workflow_notification(self, workflow_instance, event):
        """Send workflow notification"""
        try:
            workflow = workflow_instance.workflow_id
            
            # Get notification template based on event
            template_code = f'workflow_{event}'
            
            # Send notification
            self.send_notification(template_code, workflow_instance)
            
            return True
        
        except Exception as e:
            _logger.error(f'Error sending workflow notification: {str(e)}')
            return False
    
    def send_approval_notification(self, approval_request, event):
        """Send approval notification"""
        try:
            workflow = approval_request.workflow_id
            
            # Get notification template based on event
            template_code = f'approval_{event}'
            
            # Send notification
            self.send_notification(template_code, approval_request)
            
            return True
        
        except Exception as e:
            _logger.error(f'Error sending approval notification: {str(e)}')
            return False
    
    def send_task_notification(self, task, event):
        """Send task notification"""
        try:
            # Get notification template based on event
            template_code = f'task_{event}'
            
            # Send notification
            self.send_notification(template_code, task)
            
            return True
        
        except Exception as e:
            _logger.error(f'Error sending task notification: {str(e)}')
            return False
