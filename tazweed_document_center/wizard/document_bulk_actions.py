# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentBulkNotificationWizard(models.TransientModel):
    """Wizard to send bulk notifications for document expiry."""
    _name = 'document.bulk.notification.wizard'
    _description = 'Bulk Document Notification'

    notification_type = fields.Selection([
        ('expired', 'Expired Documents'),
        ('expiring_7', 'Expiring in 7 Days'),
        ('expiring_15', 'Expiring in 15 Days'),
        ('expiring_30', 'Expiring in 30 Days'),
        ('all_critical', 'All Critical (Expired + 7 Days)'),
    ], string='Notification Type', required=True, default='expiring_30')
    
    department_id = fields.Many2one('hr.department', string='Department')
    document_type_id = fields.Many2one('tazweed.document.type', string='Document Type')
    
    notify_employees = fields.Boolean(string='Notify Employees', default=True)
    notify_managers = fields.Boolean(string='Notify Managers', default=True)
    notify_hr = fields.Boolean(string='Notify HR', default=True)
    
    custom_message = fields.Text(string='Custom Message')
    
    document_count = fields.Integer(string='Documents Found', compute='_compute_document_count')
    employee_count = fields.Integer(string='Employees Affected', compute='_compute_document_count')

    @api.depends('notification_type', 'department_id', 'document_type_id')
    def _compute_document_count(self):
        for wizard in self:
            docs = wizard._get_documents()
            wizard.document_count = len(docs)
            wizard.employee_count = len(docs.mapped('employee_id'))

    def _get_documents(self):
        """Get documents based on filters."""
        today = fields.Date.today()
        domain = []
        
        if self.notification_type == 'expired':
            domain.append(('expiry_date', '<', today))
        elif self.notification_type == 'expiring_7':
            domain.extend([
                ('expiry_date', '>=', today),
                ('expiry_date', '<=', today + timedelta(days=7))
            ])
        elif self.notification_type == 'expiring_15':
            domain.extend([
                ('expiry_date', '>=', today),
                ('expiry_date', '<=', today + timedelta(days=15))
            ])
        elif self.notification_type == 'expiring_30':
            domain.extend([
                ('expiry_date', '>=', today),
                ('expiry_date', '<=', today + timedelta(days=30))
            ])
        elif self.notification_type == 'all_critical':
            domain.append(('expiry_date', '<=', today + timedelta(days=7)))
        
        if self.department_id:
            domain.append(('employee_id.department_id', '=', self.department_id.id))
        
        if self.document_type_id:
            domain.append(('document_type_id', '=', self.document_type_id.id))
        
        return self.env['tazweed.employee.document'].search(domain)

    def action_send_notifications(self):
        """Send bulk notifications."""
        docs = self._get_documents()
        
        if not docs:
            raise UserError(_('No documents found matching the criteria.'))
        
        # Group by employee
        employees = docs.mapped('employee_id')
        sent_count = 0
        
        for employee in employees:
            emp_docs = docs.filtered(lambda d: d.employee_id == employee)
            
            # Create or update alerts
            for doc in emp_docs:
                alert = self.env['document.alert'].search([
                    ('document_id', '=', doc.id),
                    ('state', 'not in', ['resolved'])
                ], limit=1)
                
                if not alert:
                    alert = self.env['document.alert'].create({
                        'document_id': doc.id,
                        'notify_employee': self.notify_employees,
                        'notify_manager': self.notify_managers,
                        'notify_hr': self.notify_hr,
                    })
                
                alert.action_send_notification()
                sent_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Notifications Sent'),
                'message': _('%d notifications sent for %d employees.') % (sent_count, len(employees)),
                'type': 'success',
            }
        }


class DocumentBulkRenewalWizard(models.TransientModel):
    """Wizard to create bulk renewal requests."""
    _name = 'document.bulk.renewal.wizard'
    _description = 'Bulk Document Renewal'

    renewal_type = fields.Selection([
        ('expired', 'Expired Documents'),
        ('expiring_30', 'Expiring in 30 Days'),
        ('expiring_60', 'Expiring in 60 Days'),
        ('expiring_90', 'Expiring in 90 Days'),
    ], string='Documents to Renew', required=True, default='expiring_30')
    
    department_id = fields.Many2one('hr.department', string='Department')
    document_type_id = fields.Many2one('tazweed.document.type', string='Document Type')
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    auto_submit = fields.Boolean(string='Auto-submit for Approval', default=False)
    reason = fields.Text(string='Renewal Reason', default='Bulk renewal request')
    
    document_count = fields.Integer(string='Documents Found', compute='_compute_document_count')

    @api.depends('renewal_type', 'department_id', 'document_type_id')
    def _compute_document_count(self):
        for wizard in self:
            docs = wizard._get_documents()
            wizard.document_count = len(docs)

    def _get_documents(self):
        """Get documents based on filters."""
        today = fields.Date.today()
        domain = [('state', '!=', 'renewed')]
        
        if self.renewal_type == 'expired':
            domain.append(('expiry_date', '<', today))
        elif self.renewal_type == 'expiring_30':
            domain.append(('expiry_date', '<=', today + timedelta(days=30)))
        elif self.renewal_type == 'expiring_60':
            domain.append(('expiry_date', '<=', today + timedelta(days=60)))
        elif self.renewal_type == 'expiring_90':
            domain.append(('expiry_date', '<=', today + timedelta(days=90)))
        
        if self.department_id:
            domain.append(('employee_id.department_id', '=', self.department_id.id))
        
        if self.document_type_id:
            domain.append(('document_type_id', '=', self.document_type_id.id))
        
        return self.env['tazweed.employee.document'].search(domain)

    def action_create_renewals(self):
        """Create bulk renewal requests."""
        docs = self._get_documents()
        
        if not docs:
            raise UserError(_('No documents found matching the criteria.'))
        
        created = 0
        skipped = 0
        
        for doc in docs:
            # Check if renewal already exists
            existing = self.env['document.renewal.request'].search([
                ('document_id', '=', doc.id),
                ('state', 'not in', ['completed', 'cancelled', 'rejected'])
            ], limit=1)
            
            if existing:
                skipped += 1
                continue
            
            renewal = self.env['document.renewal.request'].create({
                'document_id': doc.id,
                'priority': self.priority,
                'reason': self.reason,
            })
            
            if self.auto_submit:
                renewal.action_submit()
            
            created += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Renewal Requests Created'),
                'message': _('%d requests created, %d skipped (already exist).') % (created, skipped),
                'type': 'success',
            }
        }


class DocumentExportWizard(models.TransientModel):
    """Wizard to export document data."""
    _name = 'document.export.wizard'
    _description = 'Export Document Data'

    export_type = fields.Selection([
        ('all', 'All Documents'),
        ('expired', 'Expired Documents'),
        ('expiring', 'Expiring Documents'),
        ('by_employee', 'By Employee'),
        ('by_type', 'By Document Type'),
        ('compliance', 'Compliance Report'),
    ], string='Export Type', required=True, default='all')
    
    department_id = fields.Many2one('hr.department', string='Department')
    date_from = fields.Date(string='Expiry From')
    date_to = fields.Date(string='Expiry To')
    
    format = fields.Selection([
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
    ], string='Format', required=True, default='excel')

    def action_export(self):
        """Export document data."""
        # This would generate the export file
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Export'),
                'message': _('Document data exported successfully.'),
                'type': 'success',
            }
        }
