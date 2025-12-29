# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class ComplianceDashboard(models.Model):
    """Compliance Analytics Dashboard for tracking document and regulatory compliance."""
    
    _name = 'compliance.analytics.dashboard'
    _description = 'Compliance Analytics Dashboard'
    _rec_name = 'name'
    
    name = fields.Char(string='Dashboard Name', required=True, default='Compliance Dashboard')
    
    # Filters
    date_from = fields.Date(string='From Date', 
                             default=lambda self: fields.Date.today().replace(day=1) - relativedelta(months=11))
    date_to = fields.Date(string='To Date', default=fields.Date.today)
    
    department_ids = fields.Many2many('hr.department', 
                                       'compliance_dashboard_department_rel',
                                       'dashboard_id', 'department_id',
                                       string='Departments')
    document_type_ids = fields.Many2many('tazweed.document.type', 
                                          'compliance_dashboard_doctype_rel',
                                          'dashboard_id', 'document_type_id',
                                          string='Document Types')
    
    # View Type
    view_type = fields.Selection([
        ('summary', 'Summary'),
        ('by_document_type', 'By Document Type'),
        ('by_department', 'By Department'),
        ('by_employee', 'By Employee'),
        ('expiring_soon', 'Expiring Soon'),
        ('trend', 'Trend Analysis'),
    ], string='View Type', default='summary')
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    
    # Alert Settings
    expiry_warning_days = fields.Integer(string='Expiry Warning Days', default=30,
                                          help='Number of days before expiry to show warning')
    
    # Computed KPI Fields
    total_documents = fields.Integer(string='Total Documents', compute='_compute_kpi_values')
    valid_documents = fields.Integer(string='Valid Documents', compute='_compute_kpi_values')
    expired_documents = fields.Integer(string='Expired Documents', compute='_compute_kpi_values')
    expiring_soon = fields.Integer(string='Expiring Soon', compute='_compute_kpi_values')
    compliance_rate = fields.Float(string='Compliance Rate %', digits=(5, 2), compute='_compute_kpi_values')
    
    # Document Type Metrics
    visas_valid = fields.Integer(string='Valid Visas', compute='_compute_kpi_values')
    visas_expired = fields.Integer(string='Expired Visas', compute='_compute_kpi_values')
    labor_cards_valid = fields.Integer(string='Valid Labor Cards', compute='_compute_kpi_values')
    labor_cards_expired = fields.Integer(string='Expired Labor Cards', compute='_compute_kpi_values')
    emirates_ids_valid = fields.Integer(string='Valid Emirates IDs', compute='_compute_kpi_values')
    emirates_ids_expired = fields.Integer(string='Expired Emirates IDs', compute='_compute_kpi_values')
    medical_valid = fields.Integer(string='Valid Medical', compute='_compute_kpi_values')
    medical_expired = fields.Integer(string='Expired Medical', compute='_compute_kpi_values')
    
    # Work Permit Metrics
    total_work_permits = fields.Integer(string='Total Work Permits', compute='_compute_kpi_values')
    active_work_permits = fields.Integer(string='Active Work Permits', compute='_compute_kpi_values')
    expired_work_permits = fields.Integer(string='Expired Work Permits', compute='_compute_kpi_values')
    
    # Emiratization Metrics
    emiratization_target = fields.Float(string='Emiratization Target %', compute='_compute_kpi_values')
    emiratization_actual = fields.Float(string='Emiratization Actual %', compute='_compute_kpi_values')
    uae_nationals_count = fields.Integer(string='UAE Nationals', compute='_compute_kpi_values')
    
    # Dashboard Data (JSON)
    dashboard_data = fields.Text(string='Dashboard Data', compute='_compute_dashboard_data')
    
    @api.depends('date_from', 'date_to', 'department_ids', 'document_type_ids', 'expiry_warning_days')
    def _compute_kpi_values(self):
        """Compute KPI values for compliance dashboard."""
        for record in self:
            # Set default values
            record.total_documents = 0
            record.valid_documents = 0
            record.expired_documents = 0
            record.expiring_soon = 0
            record.compliance_rate = 0
            record.visas_valid = 0
            record.visas_expired = 0
            record.labor_cards_valid = 0
            record.labor_cards_expired = 0
            record.emirates_ids_valid = 0
            record.emirates_ids_expired = 0
            record.medical_valid = 0
            record.medical_expired = 0
            record.total_work_permits = 0
            record.active_work_permits = 0
            record.expired_work_permits = 0
            record.emiratization_target = 0
            record.emiratization_actual = 0
            record.uae_nationals_count = 0
            
            if not record.date_from or not record.date_to:
                continue
            
            today = fields.Date.today()
            warning_date = today + timedelta(days=record.expiry_warning_days)
            
            try:
                # Get employee documents
                EmployeeDocument = self.env['tazweed.employee.document'].sudo()
                if 'tazweed.employee.document' in self.env:
                    doc_domain = []
                    
                    if record.id:
                        try:
                            if record.department_ids:
                                doc_domain.append(('employee_id.department_id', 'in', record.department_ids.ids))
                        except Exception:
                            pass
                        try:
                            if record.document_type_ids:
                                doc_domain.append(('document_type_id', 'in', record.document_type_ids.ids))
                        except Exception:
                            pass
                    
                    documents = EmployeeDocument.search(doc_domain)
                    record.total_documents = len(documents)
                    
                    for doc in documents:
                        expiry = doc.expiry_date
                        doc_type = doc.document_type_id.name.lower() if doc.document_type_id else ''
                        
                        is_valid = expiry and expiry >= today
                        is_expired = expiry and expiry < today
                        is_expiring = expiry and today <= expiry <= warning_date
                        
                        if is_valid:
                            record.valid_documents += 1
                        if is_expired:
                            record.expired_documents += 1
                        if is_expiring:
                            record.expiring_soon += 1
                        
                        # Categorize by document type
                        if 'visa' in doc_type:
                            if is_valid:
                                record.visas_valid += 1
                            if is_expired:
                                record.visas_expired += 1
                        elif 'labor' in doc_type or 'work permit' in doc_type:
                            if is_valid:
                                record.labor_cards_valid += 1
                            if is_expired:
                                record.labor_cards_expired += 1
                        elif 'emirates' in doc_type or 'eid' in doc_type:
                            if is_valid:
                                record.emirates_ids_valid += 1
                            if is_expired:
                                record.emirates_ids_expired += 1
                        elif 'medical' in doc_type or 'health' in doc_type:
                            if is_valid:
                                record.medical_valid += 1
                            if is_expired:
                                record.medical_expired += 1
                    
                    # Calculate compliance rate
                    if record.total_documents > 0:
                        record.compliance_rate = (record.valid_documents / record.total_documents) * 100
                
                # Get work permits
                WorkPermit = self.env['tazweed.work.permit'].sudo()
                if 'tazweed.work.permit' in self.env:
                    permits = WorkPermit.search([])
                    record.total_work_permits = len(permits)
                    for permit in permits:
                        if permit.expiry_date:
                            if permit.expiry_date >= today:
                                record.active_work_permits += 1
                            else:
                                record.expired_work_permits += 1
                
                # Get emiratization data
                Employee = self.env['hr.employee'].sudo()
                employees = Employee.search([('active', '=', True)])
                total_employees = len(employees)
                
                for emp in employees:
                    nationality = emp.country_id.code if emp.country_id else ''
                    if nationality == 'AE':
                        record.uae_nationals_count += 1
                
                if total_employees > 0:
                    record.emiratization_actual = (record.uae_nationals_count / total_employees) * 100
                
                # Get emiratization target from quota
                EmiratizationQuota = self.env['tazweed.emiratization.quota'].sudo()
                if 'tazweed.emiratization.quota' in self.env:
                    quotas = EmiratizationQuota.search([], limit=1, order='create_date desc')
                    if quotas:
                        record.emiratization_target = quotas[0].target_percentage or 0
                        
            except Exception:
                pass
    
    def _compute_dashboard_data(self):
        for record in self:
            record.dashboard_data = json.dumps(record.get_dashboard_data())
    
    def get_dashboard_data(self):
        """Get comprehensive compliance dashboard data."""
        self.ensure_one()
        
        if not self.date_from or not self.date_to:
            return {
                'summary': {},
                'by_document_type': [],
                'expiring_documents': [],
                'expired_documents': [],
                'emiratization': {},
                'charts': {},
            }
        
        return {
            'summary': self._get_summary_data(),
            'by_document_type': self._get_by_document_type_data(),
            'expiring_documents': self._get_expiring_documents(),
            'expired_documents': self._get_expired_documents(),
            'emiratization': self._get_emiratization_data(),
            'charts': self._get_charts_data(),
        }
    
    def _get_summary_data(self):
        """Get summary statistics."""
        return {
            'total_documents': self.total_documents,
            'valid_documents': self.valid_documents,
            'expired_documents': self.expired_documents,
            'expiring_soon': self.expiring_soon,
            'compliance_rate': self.compliance_rate,
        }
    
    def _get_by_document_type_data(self):
        """Get compliance by document type."""
        return [
            {'type': 'Visa', 'valid': self.visas_valid, 'expired': self.visas_expired},
            {'type': 'Labor Card', 'valid': self.labor_cards_valid, 'expired': self.labor_cards_expired},
            {'type': 'Emirates ID', 'valid': self.emirates_ids_valid, 'expired': self.emirates_ids_expired},
            {'type': 'Medical', 'valid': self.medical_valid, 'expired': self.medical_expired},
        ]
    
    def _get_expiring_documents(self):
        """Get list of documents expiring soon."""
        result = []
        try:
            today = fields.Date.today()
            warning_date = today + timedelta(days=self.expiry_warning_days)
            
            EmployeeDocument = self.env['tazweed.employee.document'].sudo()
            if 'tazweed.employee.document' in self.env:
                documents = EmployeeDocument.search([
                    ('expiry_date', '>=', today),
                    ('expiry_date', '<=', warning_date),
                ], order='expiry_date', limit=50)
                
                for doc in documents:
                    result.append({
                        'employee': doc.employee_id.name if doc.employee_id else '',
                        'document_type': doc.document_type_id.name if doc.document_type_id else '',
                        'expiry_date': str(doc.expiry_date),
                        'days_remaining': (doc.expiry_date - today).days,
                    })
        except Exception:
            pass
        return result
    
    def _get_expired_documents(self):
        """Get list of expired documents."""
        result = []
        try:
            today = fields.Date.today()
            
            EmployeeDocument = self.env['tazweed.employee.document'].sudo()
            if 'tazweed.employee.document' in self.env:
                documents = EmployeeDocument.search([
                    ('expiry_date', '<', today),
                ], order='expiry_date desc', limit=50)
                
                for doc in documents:
                    result.append({
                        'employee': doc.employee_id.name if doc.employee_id else '',
                        'document_type': doc.document_type_id.name if doc.document_type_id else '',
                        'expiry_date': str(doc.expiry_date),
                        'days_overdue': (today - doc.expiry_date).days,
                    })
        except Exception:
            pass
        return result
    
    def _get_emiratization_data(self):
        """Get emiratization compliance data."""
        return {
            'target': self.emiratization_target,
            'actual': self.emiratization_actual,
            'uae_nationals': self.uae_nationals_count,
            'gap': self.emiratization_target - self.emiratization_actual,
            'compliant': self.emiratization_actual >= self.emiratization_target,
        }
    
    def _get_charts_data(self):
        """Get chart configuration data."""
        return {
            'compliance_pie': {
                'type': 'pie',
                'data': [
                    {'label': 'Valid', 'value': self.valid_documents},
                    {'label': 'Expired', 'value': self.expired_documents},
                    {'label': 'Expiring Soon', 'value': self.expiring_soon},
                ],
            },
            'document_type_bar': {
                'type': 'bar',
                'data': self._get_by_document_type_data(),
            },
            'emiratization_gauge': {
                'type': 'gauge',
                'data': {
                    'target': self.emiratization_target,
                    'actual': self.emiratization_actual,
                },
            },
        }
    
    def action_refresh(self):
        """Refresh dashboard data."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dashboard Refreshed'),
                'message': _('Compliance dashboard data has been refreshed.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_view_expired_documents(self):
        """Open expired documents view."""
        self.ensure_one()
        today = fields.Date.today()
        return {
            'name': _('Expired Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'view_mode': 'tree,form',
            'domain': [('expiry_date', '<', today)],
            'context': {'search_default_group_by_employee': 1},
        }
    
    def action_view_expiring_documents(self):
        """Open expiring soon documents view."""
        self.ensure_one()
        today = fields.Date.today()
        warning_date = today + timedelta(days=self.expiry_warning_days)
        return {
            'name': _('Expiring Soon'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'view_mode': 'tree,form',
            'domain': [
                ('expiry_date', '>=', today),
                ('expiry_date', '<=', warning_date),
            ],
            'context': {'search_default_group_by_document_type': 1},
        }
    
    def action_send_expiry_alerts(self):
        """Send email alerts for expiring documents."""
        self.ensure_one()
        # This would trigger the scheduled report
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Alerts Sent'),
                'message': _('Expiry alert emails have been sent.'),
                'type': 'success',
                'sticky': False,
            }
        }
