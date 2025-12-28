# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentAlert(models.Model):
    """Document expiry alerts with multi-level notification system."""
    _name = 'document.alert'
    _description = 'Document Expiry Alert'
    _order = 'priority desc, expiry_date asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Alert Reference', required=True, copy=False,
                       readonly=True, default=lambda self: _('New'))
    
    document_id = fields.Many2one(
        'tazweed.employee.document',
        string='Document',
        required=True,
        ondelete='cascade'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='document_id.employee_id',
        store=True
    )
    
    document_type_id = fields.Many2one(
        'tazweed.document.type',
        string='Document Type',
        related='document_id.document_type_id',
        store=True
    )
    
    expiry_date = fields.Date(
        string='Expiry Date',
        related='document_id.expiry_date',
        store=True
    )
    
    days_to_expiry = fields.Integer(
        string='Days to Expiry',
        compute='_compute_days_to_expiry',
        store=True
    )
    
    alert_level = fields.Selection([
        ('90', '90 Days'),
        ('60', '60 Days'),
        ('30', '30 Days'),
        ('15', '15 Days'),
        ('7', '7 Days'),
        ('1', '1 Day'),
        ('0', 'Expired'),
    ], string='Alert Level', compute='_compute_alert_level', store=True)
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority', compute='_compute_priority', store=True)
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
    ], string='Status', default='pending', tracking=True)
    
    # Notification tracking
    notification_count = fields.Integer(string='Notifications Sent', default=0)
    last_notification_date = fields.Datetime(string='Last Notification')
    next_notification_date = fields.Datetime(string='Next Notification')
    
    # Recipients
    notify_employee = fields.Boolean(string='Notify Employee', default=True)
    notify_manager = fields.Boolean(string='Notify Manager', default=True)
    notify_hr = fields.Boolean(string='Notify HR', default=True)
    
    # Response tracking
    acknowledged_by = fields.Many2one('res.users', string='Acknowledged By')
    acknowledged_date = fields.Datetime(string='Acknowledged Date')
    resolved_by = fields.Many2one('res.users', string='Resolved By')
    resolved_date = fields.Datetime(string='Resolved Date')
    resolution_notes = fields.Text(string='Resolution Notes')
    
    # Linked renewal request
    renewal_request_id = fields.Many2one(
        'document.renewal.request',
        string='Renewal Request'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='document_id.company_id',
        store=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('document.alert') or _('New')
        return super().create(vals_list)

    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        today = fields.Date.today()
        for alert in self:
            if alert.expiry_date:
                alert.days_to_expiry = (alert.expiry_date - today).days
            else:
                alert.days_to_expiry = 999

    @api.depends('days_to_expiry')
    def _compute_alert_level(self):
        for alert in self:
            days = alert.days_to_expiry
            if days <= 0:
                alert.alert_level = '0'
            elif days <= 1:
                alert.alert_level = '1'
            elif days <= 7:
                alert.alert_level = '7'
            elif days <= 15:
                alert.alert_level = '15'
            elif days <= 30:
                alert.alert_level = '30'
            elif days <= 60:
                alert.alert_level = '60'
            else:
                alert.alert_level = '90'

    @api.depends('alert_level')
    def _compute_priority(self):
        for alert in self:
            if alert.alert_level in ('0', '1'):
                alert.priority = '3'  # Critical
            elif alert.alert_level == '7':
                alert.priority = '2'  # High
            elif alert.alert_level in ('15', '30'):
                alert.priority = '1'  # Normal
            else:
                alert.priority = '0'  # Low

    def action_send_notification(self):
        """Send notification for this alert."""
        self.ensure_one()
        self._send_alert_email()
        self.write({
            'state': 'sent',
            'notification_count': self.notification_count + 1,
            'last_notification_date': fields.Datetime.now(),
        })
        return True

    def action_acknowledge(self):
        """Mark alert as acknowledged."""
        self.ensure_one()
        self.write({
            'state': 'acknowledged',
            'acknowledged_by': self.env.user.id,
            'acknowledged_date': fields.Datetime.now(),
        })
        return True

    def action_resolve(self):
        """Mark alert as resolved."""
        self.ensure_one()
        return {
            'name': _('Resolve Alert'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.alert.resolve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_alert_id': self.id},
        }

    def action_escalate(self):
        """Escalate alert to higher management."""
        self.ensure_one()
        self.write({'state': 'escalated'})
        self._send_escalation_email()
        return True

    def action_view_document(self):
        """View the related document."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'res_id': self.document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_renewal(self):
        """Create renewal request from alert."""
        self.ensure_one()
        
        if self.renewal_request_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'document.renewal.request',
                'res_id': self.renewal_request_id.id,
                'view_mode': 'form',
            }
        
        renewal = self.env['document.renewal.request'].create({
            'document_id': self.document_id.id,
            'alert_id': self.id,
            'requested_by': self.env.user.id,
        })
        
        self.renewal_request_id = renewal.id
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'document.renewal.request',
            'res_id': renewal.id,
            'view_mode': 'form',
        }

    def _send_alert_email(self):
        """Send alert notification email."""
        self.ensure_one()
        template = self.env.ref('tazweed_document_center.email_template_document_alert', raise_if_not_found=False)
        
        if template:
            recipients = []
            
            if self.notify_employee and self.employee_id.work_email:
                recipients.append(self.employee_id.work_email)
            
            if self.notify_manager and self.employee_id.parent_id and self.employee_id.parent_id.work_email:
                recipients.append(self.employee_id.parent_id.work_email)
            
            if self.notify_hr:
                hr_users = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
                if hr_users:
                    for user in hr_users.users:
                        if user.email:
                            recipients.append(user.email)
            
            for email in set(recipients):
                template.with_context(recipient_email=email).send_mail(self.id, force_send=True)

    def _send_escalation_email(self):
        """Send escalation notification."""
        self.ensure_one()
        template = self.env.ref('tazweed_document_center.email_template_document_escalation', raise_if_not_found=False)
        
        if template:
            template.send_mail(self.id, force_send=True)

    @api.model
    def _cron_send_expiry_alerts(self):
        """Cron job to check documents and send alerts."""
        today = fields.Date.today()
        Document = self.env['tazweed.employee.document'].sudo()
        
        # Alert thresholds in days
        thresholds = [90, 60, 30, 15, 7, 1, 0]
        
        for threshold in thresholds:
            if threshold == 0:
                # Expired documents
                docs = Document.search([
                    ('expiry_date', '<', today),
                    ('state', '!=', 'expired')
                ])
            else:
                # Documents expiring at this threshold
                target_date = today + timedelta(days=threshold)
                docs = Document.search([
                    ('expiry_date', '=', target_date)
                ])
            
            for doc in docs:
                # Check if alert already exists
                existing_alert = self.search([
                    ('document_id', '=', doc.id),
                    ('alert_level', '=', str(threshold)),
                    ('state', 'not in', ['resolved'])
                ], limit=1)
                
                if not existing_alert:
                    # Create new alert
                    alert = self.create({
                        'document_id': doc.id,
                    })
                    alert.action_send_notification()

    @api.model
    def _cron_send_reminder_notifications(self):
        """Send reminder notifications for unresolved alerts."""
        # Get alerts that need reminder
        alerts = self.search([
            ('state', 'in', ['sent', 'acknowledged']),
            ('priority', 'in', ['2', '3']),  # High and Critical only
        ])
        
        for alert in alerts:
            # Check if enough time has passed since last notification
            if alert.last_notification_date:
                hours_since = (fields.Datetime.now() - alert.last_notification_date).total_seconds() / 3600
                
                # Send reminder based on priority
                if alert.priority == '3' and hours_since >= 24:  # Critical: daily
                    alert.action_send_notification()
                elif alert.priority == '2' and hours_since >= 72:  # High: every 3 days
                    alert.action_send_notification()


class DocumentAlertResolveWizard(models.TransientModel):
    """Wizard to resolve document alerts."""
    _name = 'document.alert.resolve.wizard'
    _description = 'Resolve Document Alert'

    alert_id = fields.Many2one('document.alert', string='Alert', required=True)
    resolution_notes = fields.Text(string='Resolution Notes', required=True)
    
    def action_resolve(self):
        """Resolve the alert."""
        self.ensure_one()
        self.alert_id.write({
            'state': 'resolved',
            'resolved_by': self.env.user.id,
            'resolved_date': fields.Datetime.now(),
            'resolution_notes': self.resolution_notes,
        })
        return {'type': 'ir.actions.act_window_close'}
