# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentDashboard(models.Model):
    """Central dashboard for document management and monitoring."""
    _name = 'document.dashboard'
    _description = 'Document Management Dashboard'
    _order = 'create_date desc'

    name = fields.Char(string='Dashboard Name', required=True, default='Document Dashboard')
    
    # Summary Statistics (Computed)
    total_documents = fields.Integer(string='Total Documents', compute='_compute_statistics')
    total_employees = fields.Integer(string='Total Employees', compute='_compute_statistics')
    
    # Expiry Statistics
    expired_count = fields.Integer(string='Expired', compute='_compute_statistics')
    expiring_7_days = fields.Integer(string='Expiring in 7 Days', compute='_compute_statistics')
    expiring_15_days = fields.Integer(string='Expiring in 15 Days', compute='_compute_statistics')
    expiring_30_days = fields.Integer(string='Expiring in 30 Days', compute='_compute_statistics')
    expiring_60_days = fields.Integer(string='Expiring in 60 Days', compute='_compute_statistics')
    expiring_90_days = fields.Integer(string='Expiring in 90 Days', compute='_compute_statistics')
    valid_count = fields.Integer(string='Valid Documents', compute='_compute_statistics')
    
    # Compliance Statistics
    compliance_rate = fields.Float(string='Compliance Rate (%)', compute='_compute_statistics')
    missing_mandatory = fields.Integer(string='Missing Mandatory', compute='_compute_statistics')
    pending_renewal = fields.Integer(string='Pending Renewal', compute='_compute_statistics')
    
    # Filters
    department_id = fields.Many2one('hr.department', string='Department')
    document_type_id = fields.Many2one('tazweed.document.type', string='Document Type')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)

    @api.depends('department_id', 'document_type_id', 'date_from', 'date_to')
    def _compute_statistics(self):
        """Compute all dashboard statistics."""
        Document = self.env['tazweed.employee.document'].sudo()
        Employee = self.env['hr.employee'].sudo()
        today = fields.Date.today()
        
        for dashboard in self:
            # Base domain
            domain = [('company_id', '=', dashboard.company_id.id)]
            emp_domain = [('company_id', '=', dashboard.company_id.id), ('active', '=', True)]
            
            if dashboard.department_id:
                emp_domain.append(('department_id', '=', dashboard.department_id.id))
                domain.append(('employee_id.department_id', '=', dashboard.department_id.id))
            
            if dashboard.document_type_id:
                domain.append(('document_type_id', '=', dashboard.document_type_id.id))
            
            # Get all documents
            all_docs = Document.search(domain)
            employees = Employee.search(emp_domain)
            
            dashboard.total_documents = len(all_docs)
            dashboard.total_employees = len(employees)
            
            # Expiry counts
            dashboard.expired_count = len(all_docs.filtered(
                lambda d: d.expiry_date and d.expiry_date < today
            ))
            
            dashboard.expiring_7_days = len(all_docs.filtered(
                lambda d: d.expiry_date and today <= d.expiry_date <= today + timedelta(days=7)
            ))
            
            dashboard.expiring_15_days = len(all_docs.filtered(
                lambda d: d.expiry_date and today <= d.expiry_date <= today + timedelta(days=15)
            ))
            
            dashboard.expiring_30_days = len(all_docs.filtered(
                lambda d: d.expiry_date and today <= d.expiry_date <= today + timedelta(days=30)
            ))
            
            dashboard.expiring_60_days = len(all_docs.filtered(
                lambda d: d.expiry_date and today <= d.expiry_date <= today + timedelta(days=60)
            ))
            
            dashboard.expiring_90_days = len(all_docs.filtered(
                lambda d: d.expiry_date and today <= d.expiry_date <= today + timedelta(days=90)
            ))
            
            dashboard.valid_count = len(all_docs.filtered(
                lambda d: not d.expiry_date or d.expiry_date > today + timedelta(days=90)
            ))
            
            # Compliance rate
            if dashboard.total_documents > 0:
                valid_docs = dashboard.total_documents - dashboard.expired_count
                dashboard.compliance_rate = (valid_docs / dashboard.total_documents) * 100
            else:
                dashboard.compliance_rate = 100.0
            
            # Missing mandatory documents
            dashboard.missing_mandatory = dashboard._count_missing_mandatory(employees)
            
            # Pending renewal requests
            dashboard.pending_renewal = self.env['document.renewal.request'].sudo().search_count([
                ('state', '=', 'pending'),
                ('company_id', '=', dashboard.company_id.id)
            ])

    def _count_missing_mandatory(self, employees):
        """Count missing mandatory documents across employees."""
        DocumentType = self.env['tazweed.document.type'].sudo()
        mandatory_types = DocumentType.search([('is_mandatory', '=', True)])
        
        missing_count = 0
        for employee in employees:
            employee_doc_types = employee.document_ids.mapped('document_type_id')
            for mandatory in mandatory_types:
                if mandatory not in employee_doc_types:
                    missing_count += 1
        
        return missing_count

    def action_view_expired(self):
        """View expired documents."""
        return self._get_document_action(
            'Expired Documents',
            [('expiry_date', '<', fields.Date.today())]
        )

    def action_view_expiring_7(self):
        """View documents expiring in 7 days."""
        today = fields.Date.today()
        return self._get_document_action(
            'Expiring in 7 Days',
            [('expiry_date', '>=', today), ('expiry_date', '<=', today + timedelta(days=7))]
        )

    def action_view_expiring_15(self):
        """View documents expiring in 15 days."""
        today = fields.Date.today()
        return self._get_document_action(
            'Expiring in 15 Days',
            [('expiry_date', '>=', today), ('expiry_date', '<=', today + timedelta(days=15))]
        )

    def action_view_expiring_30(self):
        """View documents expiring in 30 days."""
        today = fields.Date.today()
        return self._get_document_action(
            'Expiring in 30 Days',
            [('expiry_date', '>=', today), ('expiry_date', '<=', today + timedelta(days=30))]
        )

    def action_view_expiring_60(self):
        """View documents expiring in 60 days."""
        today = fields.Date.today()
        return self._get_document_action(
            'Expiring in 60 Days',
            [('expiry_date', '>=', today), ('expiry_date', '<=', today + timedelta(days=60))]
        )

    def action_view_expiring_90(self):
        """View documents expiring in 90 days."""
        today = fields.Date.today()
        return self._get_document_action(
            'Expiring in 90 Days',
            [('expiry_date', '>=', today), ('expiry_date', '<=', today + timedelta(days=90))]
        )

    def action_view_valid(self):
        """View valid documents."""
        today = fields.Date.today()
        return self._get_document_action(
            'Valid Documents',
            ['|', ('expiry_date', '=', False), ('expiry_date', '>', today + timedelta(days=90))]
        )

    def action_view_missing_mandatory(self):
        """View employees with missing mandatory documents."""
        return {
            'name': _('Missing Mandatory Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.compliance.report',
            'view_mode': 'tree,form',
            'domain': [('missing_count', '>', 0)],
            'context': {'default_company_id': self.company_id.id},
        }

    def action_view_pending_renewal(self):
        """View pending renewal requests."""
        return {
            'name': _('Pending Renewals'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.renewal.request',
            'view_mode': 'tree,form',
            'domain': [('state', '=', 'pending')],
        }

    def _get_document_action(self, name, domain):
        """Helper to create document action."""
        base_domain = [('company_id', '=', self.company_id.id)]
        
        if self.department_id:
            base_domain.append(('employee_id.department_id', '=', self.department_id.id))
        
        if self.document_type_id:
            base_domain.append(('document_type_id', '=', self.document_type_id.id))
        
        return {
            'name': _(name),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'view_mode': 'tree,form',
            'domain': base_domain + domain,
            'context': {'search_default_group_by_employee': 1},
        }

    def action_refresh(self):
        """Refresh dashboard statistics."""
        self._compute_statistics()
        return True

    def action_send_alerts(self):
        """Manually trigger alert sending."""
        self.env['document.alert']._cron_send_expiry_alerts()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Alerts Sent'),
                'message': _('Document expiry alerts have been sent.'),
                'type': 'success',
            }
        }

    def action_generate_report(self):
        """Generate compliance report."""
        return {
            'name': _('Document Compliance Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.compliance.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_department_id': self.department_id.id,
                'default_document_type_id': self.document_type_id.id,
            },
        }

    @api.model
    def get_dashboard_data(self):
        """Get dashboard data for JavaScript widget."""
        dashboard = self.search([], limit=1)
        if not dashboard:
            dashboard = self.create({'name': 'Main Dashboard'})
        
        today = fields.Date.today()
        Document = self.env['tazweed.employee.document'].sudo()
        
        # Get documents by type
        docs_by_type = {}
        doc_types = self.env['tazweed.document.type'].search([])
        for doc_type in doc_types:
            docs = Document.search([('document_type_id', '=', doc_type.id)])
            expired = len(docs.filtered(lambda d: d.expiry_date and d.expiry_date < today))
            expiring = len(docs.filtered(
                lambda d: d.expiry_date and today <= d.expiry_date <= today + timedelta(days=30)
            ))
            valid = len(docs) - expired - expiring
            
            docs_by_type[doc_type.name] = {
                'total': len(docs),
                'expired': expired,
                'expiring': expiring,
                'valid': valid,
            }
        
        # Get documents by department
        docs_by_dept = {}
        departments = self.env['hr.department'].search([])
        for dept in departments:
            docs = Document.search([('employee_id.department_id', '=', dept.id)])
            expired = len(docs.filtered(lambda d: d.expiry_date and d.expiry_date < today))
            expiring = len(docs.filtered(
                lambda d: d.expiry_date and today <= d.expiry_date <= today + timedelta(days=30)
            ))
            
            docs_by_dept[dept.name] = {
                'total': len(docs),
                'expired': expired,
                'expiring': expiring,
            }
        
        # Get expiry timeline
        timeline = []
        for i in range(12):
            month_start = today.replace(day=1) + relativedelta(months=i)
            month_end = month_start + relativedelta(months=1, days=-1)
            count = Document.search_count([
                ('expiry_date', '>=', month_start),
                ('expiry_date', '<=', month_end)
            ])
            timeline.append({
                'month': month_start.strftime('%b %Y'),
                'count': count,
            })
        
        # Recent alerts
        alerts = self.env['document.alert'].search([
            ('state', 'in', ['pending', 'sent'])
        ], limit=10, order='create_date desc')
        
        recent_alerts = [{
            'id': alert.id,
            'document': alert.document_id.name,
            'employee': alert.employee_id.name,
            'expiry_date': alert.expiry_date.strftime('%Y-%m-%d') if alert.expiry_date else '',
            'days_left': alert.days_to_expiry,
            'priority': alert.priority,
            'state': alert.state,
        } for alert in alerts]
        
        return {
            'summary': {
                'total_documents': dashboard.total_documents,
                'total_employees': dashboard.total_employees,
                'expired': dashboard.expired_count,
                'expiring_7': dashboard.expiring_7_days,
                'expiring_30': dashboard.expiring_30_days,
                'expiring_90': dashboard.expiring_90_days,
                'valid': dashboard.valid_count,
                'compliance_rate': dashboard.compliance_rate,
                'missing_mandatory': dashboard.missing_mandatory,
                'pending_renewal': dashboard.pending_renewal,
            },
            'by_type': docs_by_type,
            'by_department': docs_by_dept,
            'timeline': timeline,
            'recent_alerts': recent_alerts,
        }
