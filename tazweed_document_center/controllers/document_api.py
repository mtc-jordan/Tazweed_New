# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json


class DocumentDashboardAPI(http.Controller):
    """API endpoints for document dashboard."""

    @http.route('/document/dashboard/data', type='json', auth='user')
    def get_dashboard_data(self):
        """Get dashboard data for JavaScript widget."""
        return request.env['document.dashboard'].get_dashboard_data()

    @http.route('/document/alerts/count', type='json', auth='user')
    def get_alerts_count(self):
        """Get count of active alerts."""
        Alert = request.env['document.alert'].sudo()
        return {
            'critical': Alert.search_count([('priority', '=', '3'), ('state', '!=', 'resolved')]),
            'high': Alert.search_count([('priority', '=', '2'), ('state', '!=', 'resolved')]),
            'normal': Alert.search_count([('priority', '=', '1'), ('state', '!=', 'resolved')]),
            'low': Alert.search_count([('priority', '=', '0'), ('state', '!=', 'resolved')]),
            'total': Alert.search_count([('state', '!=', 'resolved')]),
        }

    @http.route('/document/expiry/calendar', type='json', auth='user')
    def get_expiry_calendar(self, start_date=None, end_date=None):
        """Get document expiry dates for calendar view."""
        Document = request.env['tazweed.employee.document'].sudo()
        
        domain = [('expiry_date', '!=', False)]
        if start_date:
            domain.append(('expiry_date', '>=', start_date))
        if end_date:
            domain.append(('expiry_date', '<=', end_date))
        
        docs = Document.search(domain)
        
        events = []
        for doc in docs:
            events.append({
                'id': doc.id,
                'title': f"{doc.employee_id.name} - {doc.document_type_id.name}",
                'start': doc.expiry_date.isoformat(),
                'allDay': True,
                'color': '#dc3545' if doc.days_to_expiry < 0 else 
                         '#ffc107' if doc.days_to_expiry <= 30 else '#28a745',
            })
        
        return events

    @http.route('/document/compliance/summary', type='json', auth='user')
    def get_compliance_summary(self, department_id=None):
        """Get compliance summary statistics."""
        Employee = request.env['hr.employee'].sudo()
        
        domain = [('active', '=', True)]
        if department_id:
            domain.append(('department_id', '=', int(department_id)))
        
        employees = Employee.search(domain)
        
        compliant = len(employees.filtered(lambda e: e.document_compliance_status == 'compliant'))
        warning = len(employees.filtered(lambda e: e.document_compliance_status == 'warning'))
        non_compliant = len(employees.filtered(lambda e: e.document_compliance_status == 'non_compliant'))
        
        return {
            'total': len(employees),
            'compliant': compliant,
            'warning': warning,
            'non_compliant': non_compliant,
            'compliance_rate': (compliant / len(employees) * 100) if employees else 0,
        }
