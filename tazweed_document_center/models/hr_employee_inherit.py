# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _


class HrEmployeeDocumentCenter(models.Model):
    """Extend HR Employee with document center features."""
    _inherit = 'hr.employee'

    # Document statistics
    document_compliance_score = fields.Float(
        string='Compliance Score',
        compute='_compute_document_compliance',
        store=True
    )
    
    document_compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('warning', 'Warning'),
        ('non_compliant', 'Non-Compliant'),
    ], string='Compliance Status', compute='_compute_document_compliance', store=True)
    
    critical_documents_count = fields.Integer(
        string='Critical Documents',
        compute='_compute_critical_documents',
        store=True
    )
    
    pending_renewals_count = fields.Integer(
        string='Pending Renewals',
        compute='_compute_pending_renewals'
    )
    
    active_alerts_count = fields.Integer(
        string='Active Alerts',
        compute='_compute_active_alerts'
    )

    @api.depends('document_ids', 'document_ids.expiry_date', 'document_ids.state')
    def _compute_document_compliance(self):
        """Compute document compliance score and status."""
        today = fields.Date.today()
        warning_date = today + timedelta(days=30)
        
        for employee in self:
            docs = employee.document_ids
            total = len(docs)
            
            if total == 0:
                employee.document_compliance_score = 0
                employee.document_compliance_status = 'non_compliant'
                continue
            
            expired = len(docs.filtered(lambda d: d.expiry_date and d.expiry_date < today))
            expiring = len(docs.filtered(
                lambda d: d.expiry_date and today <= d.expiry_date <= warning_date
            ))
            valid = total - expired - expiring
            
            # Calculate score
            employee.document_compliance_score = (valid / total) * 100 if total > 0 else 0
            
            # Determine status
            if expired > 0:
                employee.document_compliance_status = 'non_compliant'
            elif expiring > 0:
                employee.document_compliance_status = 'warning'
            else:
                employee.document_compliance_status = 'compliant'

    @api.depends('document_ids', 'document_ids.expiry_date')
    def _compute_critical_documents(self):
        """Count critical (expired or expiring in 7 days) documents."""
        today = fields.Date.today()
        critical_date = today + timedelta(days=7)
        
        for employee in self:
            employee.critical_documents_count = len(employee.document_ids.filtered(
                lambda d: d.expiry_date and d.expiry_date <= critical_date
            ))

    def _compute_pending_renewals(self):
        """Count pending renewal requests."""
        for employee in self:
            employee.pending_renewals_count = self.env['document.renewal.request'].search_count([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['draft', 'pending', 'approved', 'in_progress', 'submitted'])
            ])

    def _compute_active_alerts(self):
        """Count active document alerts."""
        for employee in self:
            employee.active_alerts_count = self.env['document.alert'].search_count([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['pending', 'sent', 'acknowledged'])
            ])

    def action_view_document_dashboard(self):
        """Open document dashboard for this employee."""
        self.ensure_one()
        return {
            'name': _('Document Dashboard - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'view_mode': 'tree,form,kanban',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
                'search_default_group_by_type': 1,
            },
        }

    def action_view_document_alerts(self):
        """View document alerts for this employee."""
        self.ensure_one()
        return {
            'name': _('Document Alerts - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'document.alert',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }

    def action_view_renewal_requests(self):
        """View renewal requests for this employee."""
        self.ensure_one()
        return {
            'name': _('Renewal Requests - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'document.renewal.request',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }

    def action_create_bulk_renewal(self):
        """Create renewal requests for all expiring documents."""
        self.ensure_one()
        today = fields.Date.today()
        warning_date = today + timedelta(days=30)
        
        docs_to_renew = self.document_ids.filtered(
            lambda d: d.expiry_date and d.expiry_date <= warning_date and d.state != 'renewed'
        )
        
        if not docs_to_renew:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Documents'),
                    'message': _('No documents need renewal at this time.'),
                    'type': 'info',
                }
            }
        
        created = 0
        for doc in docs_to_renew:
            # Check if renewal already exists
            existing = self.env['document.renewal.request'].search([
                ('document_id', '=', doc.id),
                ('state', 'not in', ['completed', 'cancelled', 'rejected'])
            ], limit=1)
            
            if not existing:
                self.env['document.renewal.request'].create({
                    'document_id': doc.id,
                    'reason': _('Document expiring soon - bulk renewal request'),
                    'priority': 'high' if doc.expiry_date < today else 'normal',
                })
                created += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Renewal Requests Created'),
                'message': _('%d renewal requests have been created.') % created,
                'type': 'success',
            }
        }

    def action_send_document_reminder(self):
        """Send document reminder to employee."""
        self.ensure_one()
        template = self.env.ref('tazweed_document_center.email_template_employee_document_reminder', raise_if_not_found=False)
        
        if template and self.work_email:
            template.send_mail(self.id, force_send=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Reminder Sent'),
                    'message': _('Document reminder sent to %s.') % self.name,
                    'type': 'success',
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Error'),
                'message': _('Could not send reminder. Employee email not configured.'),
                'type': 'warning',
            }
        }
