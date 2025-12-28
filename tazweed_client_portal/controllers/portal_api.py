# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import json


class TazweedPortalAPI(http.Controller):
    """REST API for Client Portal AJAX Requests"""

    def _get_client(self):
        """Get client for current user"""
        partner = request.env.user.partner_id
        client = request.env['tazweed.client'].sudo().search([
            '|',
            ('partner_id', '=', partner.id),
            ('partner_id', '=', partner.parent_id.id),
        ], limit=1)
        return client

    # ==================== DASHBOARD API ====================
    
    @http.route('/api/portal/dashboard', type='json', auth='user')
    def api_dashboard_data(self):
        """Get dashboard data for client"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        dashboard = request.env['client.portal.dashboard'].sudo()
        return dashboard.get_dashboard_data(client.id)

    # ==================== NOTIFICATIONS API ====================
    
    @http.route('/api/portal/notifications', type='json', auth='user')
    def api_get_notifications(self, limit=20):
        """Get notifications for client"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        notifications = request.env['client.portal.notification'].sudo().search([
            ('client_id', '=', client.id),
            ('is_dismissed', '=', False),
            '|',
            ('is_expired', '=', False),
            ('expiry_date', '=', False),
        ], order='create_date desc', limit=limit)
        
        return {
            'notifications': [{
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'icon': n.icon,
                'color': n.color,
                'is_read': n.is_read,
                'action_url': n.action_url,
                'date': n.create_date.isoformat(),
            } for n in notifications],
            'unread_count': request.env['client.portal.notification'].sudo().get_unread_count(client.id),
        }
    
    @http.route('/api/portal/notifications/mark-read', type='json', auth='user')
    def api_mark_notification_read(self, notification_id):
        """Mark notification as read"""
        notification = request.env['client.portal.notification'].sudo().browse(notification_id)
        if notification.exists():
            notification.action_mark_read()
            return {'success': True}
        return {'error': 'Notification not found'}
    
    @http.route('/api/portal/notifications/dismiss', type='json', auth='user')
    def api_dismiss_notification(self, notification_id):
        """Dismiss notification"""
        notification = request.env['client.portal.notification'].sudo().browse(notification_id)
        if notification.exists():
            notification.action_dismiss()
            return {'success': True}
        return {'error': 'Notification not found'}
    
    @http.route('/api/portal/notifications/mark-all-read', type='json', auth='user')
    def api_mark_all_read(self):
        """Mark all notifications as read"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        notifications = request.env['client.portal.notification'].sudo().search([
            ('client_id', '=', client.id),
            ('is_read', '=', False),
        ])
        notifications.action_mark_read()
        return {'success': True, 'count': len(notifications)}

    # ==================== MESSAGES API ====================
    
    @http.route('/api/portal/messages/send', type='json', auth='user')
    def api_send_message(self, subject, body, category='general', job_order_id=None, placement_id=None):
        """Send a new message"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        portal_user = request.env['client.portal.user'].sudo().search([
            ('client_id', '=', client.id),
            ('user_id', '=', request.env.user.id),
        ], limit=1)
        
        message = request.env['client.portal.message'].sudo().create({
            'client_id': client.id,
            'portal_user_id': portal_user.id if portal_user else False,
            'subject': subject,
            'body': body,
            'direction': 'incoming',
            'category': category,
            'job_order_id': job_order_id,
            'placement_id': placement_id,
        })
        
        return {
            'success': True,
            'message_id': message.id,
        }
    
    @http.route('/api/portal/messages/unread-count', type='json', auth='user')
    def api_unread_messages(self):
        """Get unread message count"""
        client = self._get_client()
        if not client:
            return {'count': 0}
        
        count = request.env['client.portal.message'].sudo().search_count([
            ('client_id', '=', client.id),
            ('is_read', '=', False),
            ('direction', '=', 'outgoing'),
        ])
        return {'count': count}

    # ==================== JOB ORDERS API ====================
    
    @http.route('/api/portal/job-orders/create', type='json', auth='user')
    def api_create_job_order(self, title, description, positions_required, 
                             department=None, location=None, skills=None):
        """Create a new job order"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        portal_user = request.env['client.portal.user'].sudo().search([
            ('client_id', '=', client.id),
            ('user_id', '=', request.env.user.id),
        ], limit=1)
        
        if portal_user and not portal_user.can_create_job_orders:
            return {'error': 'Permission denied'}
        
        job_order = request.env['tazweed.job.order'].sudo().create({
            'client_id': client.id,
            'name': title,
            'description': description,
            'positions_required': positions_required,
            'department': department,
            'location': location,
            'required_skills': skills,
            'state': 'draft',
        })
        
        return {
            'success': True,
            'job_order_id': job_order.id,
            'reference': job_order.name,
        }

    # ==================== CANDIDATES API ====================
    
    @http.route('/api/portal/candidates/approve', type='json', auth='user')
    def api_approve_candidate(self, candidate_id, notes=None):
        """Approve a candidate"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        portal_user = request.env['client.portal.user'].sudo().search([
            ('client_id', '=', client.id),
            ('user_id', '=', request.env.user.id),
        ], limit=1)
        
        if portal_user and not portal_user.can_approve_candidates:
            return {'error': 'Permission denied'}
        
        candidate = request.env['tazweed.candidate'].sudo().browse(candidate_id)
        
        if not candidate.exists() or candidate.job_order_id.client_id.id != client.id:
            return {'error': 'Candidate not found'}
        
        candidate.write({
            'state': 'approved',
            'approval_notes': notes,
        })
        
        return {'success': True}
    
    @http.route('/api/portal/candidates/reject', type='json', auth='user')
    def api_reject_candidate(self, candidate_id, reason=None):
        """Reject a candidate"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        portal_user = request.env['client.portal.user'].sudo().search([
            ('client_id', '=', client.id),
            ('user_id', '=', request.env.user.id),
        ], limit=1)
        
        if portal_user and not portal_user.can_approve_candidates:
            return {'error': 'Permission denied'}
        
        candidate = request.env['tazweed.candidate'].sudo().browse(candidate_id)
        
        if not candidate.exists() or candidate.job_order_id.client_id.id != client.id:
            return {'error': 'Candidate not found'}
        
        candidate.write({
            'state': 'rejected',
            'rejection_reason': reason,
        })
        
        return {'success': True}

    # ==================== DOCUMENTS API ====================
    
    @http.route('/api/portal/documents/acknowledge', type='json', auth='user')
    def api_acknowledge_document(self, document_id):
        """Acknowledge receipt of a document"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        portal_user = request.env['client.portal.user'].sudo().search([
            ('client_id', '=', client.id),
            ('user_id', '=', request.env.user.id),
        ], limit=1)
        
        document = request.env['client.portal.document'].sudo().browse(document_id)
        
        if not document.exists() or document.client_id.id != client.id:
            return {'error': 'Document not found'}
        
        document.action_acknowledge(portal_user.id if portal_user else False)
        
        return {'success': True}

    # ==================== ANALYTICS API ====================
    
    @http.route('/api/portal/analytics/placements', type='json', auth='user')
    def api_placement_analytics(self, period='month'):
        """Get placement analytics"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        # Get placement data grouped by month
        query = """
            SELECT 
                DATE_TRUNC('month', start_date) as month,
                COUNT(*) as count,
                SUM(CASE WHEN state = 'active' THEN 1 ELSE 0 END) as active_count
            FROM tazweed_placement
            WHERE client_id = %s
            AND start_date >= NOW() - INTERVAL '12 months'
            GROUP BY DATE_TRUNC('month', start_date)
            ORDER BY month
        """
        request.env.cr.execute(query, (client.id,))
        results = request.env.cr.dictfetchall()
        
        return {
            'data': [{
                'month': r['month'].strftime('%b %Y') if r['month'] else '',
                'count': r['count'],
                'active_count': r['active_count'],
            } for r in results]
        }
    
    @http.route('/api/portal/analytics/invoices', type='json', auth='user')
    def api_invoice_analytics(self, period='month'):
        """Get invoice analytics"""
        client = self._get_client()
        if not client:
            return {'error': 'Client not found'}
        
        # Get invoice data grouped by month
        query = """
            SELECT 
                DATE_TRUNC('month', invoice_date) as month,
                COUNT(*) as count,
                SUM(total_amount) as total,
                SUM(CASE WHEN state = 'paid' THEN total_amount ELSE 0 END) as paid_total
            FROM tazweed_client_invoice
            WHERE client_id = %s
            AND invoice_date >= NOW() - INTERVAL '12 months'
            GROUP BY DATE_TRUNC('month', invoice_date)
            ORDER BY month
        """
        request.env.cr.execute(query, (client.id,))
        results = request.env.cr.dictfetchall()
        
        return {
            'data': [{
                'month': r['month'].strftime('%b %Y') if r['month'] else '',
                'count': r['count'],
                'total': float(r['total'] or 0),
                'paid_total': float(r['paid_total'] or 0),
            } for r in results]
        }
