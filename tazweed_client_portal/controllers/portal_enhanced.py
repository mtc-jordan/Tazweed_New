# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import json
from datetime import datetime, timedelta


class ClientPortalEnhanced(CustomerPortal):
    """Enhanced Client Portal Controller"""

    # ==================== Dashboard Routes ====================
    
    @http.route('/my/dashboard/data', type='json', auth='user', website=True)
    def get_dashboard_data(self, **kw):
        """Get comprehensive dashboard data via AJAX"""
        client = self._get_client_for_user()
        if not client:
            return {'error': 'Client not found'}
        
        date_from = kw.get('date_from')
        date_to = kw.get('date_to')
        
        dashboard = request.env['client.portal.dashboard.enhanced'].sudo()
        return dashboard.get_comprehensive_dashboard(client.id, date_from, date_to)
    
    @http.route('/my/dashboard/refresh', type='json', auth='user', website=True)
    def refresh_dashboard(self, **kw):
        """Refresh specific dashboard section"""
        client = self._get_client_for_user()
        if not client:
            return {'error': 'Client not found'}
        
        section = kw.get('section', 'all')
        dashboard = request.env['client.portal.dashboard.enhanced'].sudo()
        
        if section == 'kpis':
            return dashboard._get_summary_kpis(client.id)
        elif section == 'workforce':
            return dashboard._get_workforce_metrics(client.id)
        elif section == 'financial':
            return dashboard._get_financial_summary(client.id, None, None)
        elif section == 'alerts':
            return dashboard._get_alerts(client.id)
        else:
            return dashboard.get_comprehensive_dashboard(client.id)
    
    # ==================== Employee Routes ====================
    
    @http.route('/my/employees', type='http', auth='user', website=True)
    def portal_employees(self, **kw):
        """Employee list page"""
        client = self._get_client_for_user()
        if not client:
            return request.redirect('/my')
        
        filters = {
            'department': kw.get('department'),
            'status': kw.get('status'),
            'search': kw.get('search'),
        }
        
        portal_emp = request.env['client.portal.employee'].sudo()
        employees = portal_emp.get_employees_for_client(client.id, filters)
        departments = portal_emp.get_department_list(client.id)
        
        values = {
            'employees': employees,
            'departments': departments,
            'filters': filters,
            'page_name': 'employees',
        }
        
        return request.render('tazweed_client_portal.portal_employees', values)
    
    @http.route('/my/employees/<int:employee_id>', type='http', auth='user', website=True)
    def portal_employee_detail(self, employee_id, **kw):
        """Employee detail page"""
        client = self._get_client_for_user()
        if not client:
            return request.redirect('/my')
        
        portal_emp = request.env['client.portal.employee'].sudo()
        
        try:
            employee_data = portal_emp.get_employee_details(client.id, employee_id)
        except Exception as e:
            return request.redirect('/my/employees')
        
        values = {
            'employee': employee_data,
            'page_name': 'employee_detail',
        }
        
        return request.render('tazweed_client_portal.portal_employee_detail', values)
    
    @http.route('/my/employees/data', type='json', auth='user', website=True)
    def get_employees_data(self, **kw):
        """Get employees data via AJAX"""
        client = self._get_client_for_user()
        if not client:
            return {'error': 'Client not found'}
        
        filters = {
            'department': kw.get('department'),
            'status': kw.get('status'),
            'search': kw.get('search'),
        }
        
        portal_emp = request.env['client.portal.employee'].sudo()
        return portal_emp.get_employees_for_client(client.id, filters)
    
    # ==================== Document Routes ====================
    
    @http.route('/my/documents/enhanced', type='http', auth='user', website=True)
    def portal_documents_enhanced(self, **kw):
        """Enhanced documents page"""
        client = self._get_client_for_user()
        if not client:
            return request.redirect('/my')
        
        domain = [
            ('client_id', '=', client.id),
            ('visibility', 'in', ['client', 'public']),
            ('state', '=', 'active'),
        ]
        
        # Apply filters
        if kw.get('type'):
            domain.append(('document_type', '=', kw['type']))
        if kw.get('category'):
            domain.append(('category_id', '=', int(kw['category'])))
        if kw.get('search'):
            domain.append(('name', 'ilike', kw['search']))
        
        documents = request.env['client.portal.document.enhanced'].sudo().search(domain)
        categories = request.env['client.portal.document.category'].sudo().search([])
        
        values = {
            'documents': documents,
            'categories': categories,
            'filters': kw,
            'page_name': 'documents_enhanced',
        }
        
        return request.render('tazweed_client_portal.portal_documents_enhanced', values)
    
    @http.route('/my/documents/<int:doc_id>/download', type='http', auth='user', website=True)
    def download_document(self, doc_id, **kw):
        """Download document and track"""
        client = self._get_client_for_user()
        if not client:
            return request.redirect('/my')
        
        document = request.env['client.portal.document.enhanced'].sudo().browse(doc_id)
        
        if not document.exists() or document.client_id.id != client.id:
            return request.redirect('/my/documents/enhanced')
        
        # Track download
        document.action_download()
        
        # Return file
        import base64
        file_content = base64.b64decode(document.file)
        
        return request.make_response(
            file_content,
            headers=[
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', f'attachment; filename="{document.filename}"'),
            ]
        )
    
    # ==================== Request Routes ====================
    
    @http.route('/my/requests/quick-actions', type='json', auth='user', website=True)
    def get_quick_actions(self, **kw):
        """Get available quick actions"""
        client = self._get_client_for_user()
        if not client:
            return {'error': 'Client not found'}
        
        quick_actions = request.env['client.request.quick.action'].sudo()
        return quick_actions.get_quick_actions_for_portal(client.id)
    
    @http.route('/my/requests/create-quick', type='json', auth='user', website=True)
    def create_quick_request(self, **kw):
        """Create request from quick action"""
        client = self._get_client_for_user()
        if not client:
            return {'error': 'Client not found'}
        
        action_id = kw.get('action_id')
        if not action_id:
            return {'error': 'Action ID required'}
        
        quick_action = request.env['client.request.quick.action'].sudo().browse(action_id)
        if not quick_action.exists():
            return {'error': 'Action not found'}
        
        try:
            new_request = quick_action.create_request_from_action(client.id, kw)
            return {'success': True, 'request_id': new_request.id}
        except Exception as e:
            return {'error': str(e)}
    
    @http.route('/my/requests/<int:request_id>/timeline', type='json', auth='user', website=True)
    def get_request_timeline(self, request_id, **kw):
        """Get request timeline"""
        client = self._get_client_for_user()
        if not client:
            return {'error': 'Client not found'}
        
        client_request = request.env['client.request'].sudo().browse(request_id)
        
        if not client_request.exists() or client_request.client_id.id != client.id:
            return {'error': 'Request not found'}
        
        timeline = []
        for entry in client_request.timeline_ids:
            timeline.append({
                'type': entry.entry_type,
                'description': entry.description,
                'user': entry.user_id.name if entry.user_id else 'System',
                'date': entry.create_date.strftime('%b %d, %Y %H:%M'),
            })
        
        return timeline
    
    @http.route('/my/requests/<int:request_id>/feedback', type='json', auth='user', website=True)
    def submit_request_feedback(self, request_id, **kw):
        """Submit feedback for completed request"""
        client = self._get_client_for_user()
        if not client:
            return {'error': 'Client not found'}
        
        client_request = request.env['client.request'].sudo().browse(request_id)
        
        if not client_request.exists() or client_request.client_id.id != client.id:
            return {'error': 'Request not found'}
        
        rating = kw.get('rating')
        comment = kw.get('comment', '')
        
        if not rating or int(rating) < 1 or int(rating) > 5:
            return {'error': 'Invalid rating'}
        
        try:
            client_request.action_submit_feedback(int(rating), comment)
            return {'success': True}
        except Exception as e:
            return {'error': str(e)}
    
    # ==================== Reports Routes ====================
    
    @http.route('/my/reports', type='http', auth='user', website=True)
    def portal_reports(self, **kw):
        """Reports page"""
        client = self._get_client_for_user()
        if not client:
            return request.redirect('/my')
        
        reports = request.env['client.portal.report'].sudo().search([
            ('client_id', '=', client.id)
        ], order='generated_date desc')
        
        values = {
            'reports': reports,
            'page_name': 'reports',
        }
        
        return request.render('tazweed_client_portal.portal_reports', values)
    
    @http.route('/my/reports/generate', type='json', auth='user', website=True)
    def generate_report(self, **kw):
        """Generate a new report"""
        client = self._get_client_for_user()
        if not client:
            return {'error': 'Client not found'}
        
        report_type = kw.get('report_type')
        date_from = kw.get('date_from')
        date_to = kw.get('date_to')
        
        if not all([report_type, date_from, date_to]):
            return {'error': 'Missing required parameters'}
        
        try:
            report = request.env['client.portal.report'].sudo().create({
                'name': f'{report_type.title()} Report',
                'client_id': client.id,
                'report_type': report_type,
                'date_from': date_from,
                'date_to': date_to,
            })
            report.action_generate_report()
            return {'success': True, 'report_id': report.id}
        except Exception as e:
            return {'error': str(e)}
    
    # ==================== Settings Routes ====================
    
    @http.route('/my/settings/notifications', type='http', auth='user', website=True)
    def portal_notification_settings(self, **kw):
        """Notification settings page"""
        client = self._get_client_for_user()
        if not client:
            return request.redirect('/my')
        
        prefs = request.env['client.portal.notification.preference'].sudo().search([
            ('client_id', '=', client.id),
            ('user_id', '=', request.env.user.id),
        ], limit=1)
        
        if not prefs:
            prefs = request.env['client.portal.notification.preference'].sudo().create({
                'client_id': client.id,
                'user_id': request.env.user.id,
            })
        
        values = {
            'preferences': prefs,
            'page_name': 'notification_settings',
        }
        
        return request.render('tazweed_client_portal.portal_notification_settings', values)
    
    @http.route('/my/settings/notifications/save', type='json', auth='user', website=True)
    def save_notification_settings(self, **kw):
        """Save notification settings"""
        client = self._get_client_for_user()
        if not client:
            return {'error': 'Client not found'}
        
        prefs = request.env['client.portal.notification.preference'].sudo().search([
            ('client_id', '=', client.id),
            ('user_id', '=', request.env.user.id),
        ], limit=1)
        
        if not prefs:
            return {'error': 'Preferences not found'}
        
        # Update preferences
        update_vals = {}
        for key, value in kw.items():
            if hasattr(prefs, key):
                update_vals[key] = value
        
        prefs.write(update_vals)
        return {'success': True}
    
    # ==================== Helper Methods ====================
    
    def _get_client_for_user(self):
        """Get the client associated with current portal user"""
        user = request.env.user
        
        # Check portal user mapping
        portal_user = request.env['client.portal.user'].sudo().search([
            ('user_id', '=', user.id),
            ('state', '=', 'active'),
        ], limit=1)
        
        if portal_user:
            return portal_user.client_id
        
        # Fallback: check partner
        if user.partner_id:
            client = request.env['tazweed.client'].sudo().search([
                ('partner_id', '=', user.partner_id.id)
            ], limit=1)
            return client
        
        return None
