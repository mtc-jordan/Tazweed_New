# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from collections import OrderedDict
import json


class TazweedClientPortal(CustomerPortal):
    """Main Client Portal Controller"""

    def _prepare_home_portal_values(self, counters):
        """Add Tazweed-specific counters to portal home"""
        values = super()._prepare_home_portal_values(counters)
        
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        
        if client:
            if 'job_order_count' in counters:
                values['job_order_count'] = request.env['tazweed.job.order'].search_count([
                    ('client_id', '=', client.id)
                ])
            if 'placement_count' in counters:
                values['placement_count'] = request.env['tazweed.placement'].search_count([
                    ('client_id', '=', client.id)
                ])
            if 'candidate_count' in counters:
                values['candidate_count'] = request.env['tazweed.candidate'].search_count([
                    ('job_order_id.client_id', '=', client.id),
                    ('state', '=', 'pending_approval')
                ])
            if 'invoice_count' in counters:
                values['invoice_count'] = request.env['tazweed.client.invoice'].search_count([
                    ('client_id', '=', client.id)
                ])
            if 'document_count' in counters:
                values['document_count'] = request.env['client.portal.document'].search_count([
                    ('client_id', '=', client.id),
                    ('visibility', '=', 'client')
                ])
            if 'message_count' in counters:
                values['message_count'] = request.env['client.portal.message'].search_count([
                    ('client_id', '=', client.id),
                    ('is_read', '=', False),
                    ('direction', '=', 'outgoing')
                ])
        
        return values
    
    def _get_client_for_partner(self, partner):
        """Get client record for the current partner"""
        # Check if partner is directly a client
        client = request.env['tazweed.client'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1)
        
        if not client and partner.parent_id:
            # Check parent partner
            client = request.env['tazweed.client'].sudo().search([
                ('partner_id', '=', partner.parent_id.id)
            ], limit=1)
        
        return client
    
    def _get_portal_user(self, client):
        """Get portal user record for current user"""
        return request.env['client.portal.user'].sudo().search([
            ('client_id', '=', client.id),
            ('user_id', '=', request.env.user.id),
            ('state', '=', 'active')
        ], limit=1)

    # ==================== DASHBOARD ====================
    
    @http.route(['/my/dashboard'], type='http', auth='user', website=True)
    def portal_dashboard(self, **kw):
        """Client Dashboard with KPIs and Analytics"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        
        if not client:
            return request.redirect('/my')
        
        portal_user = self._get_portal_user(client)
        
        # Get dashboard data
        dashboard_model = request.env['client.portal.dashboard'].sudo()
        dashboard_data = dashboard_model.get_dashboard_data(client.id)
        
        # Get portal settings
        settings = client.portal_settings_id
        
        values = {
            'client': client,
            'portal_user': portal_user,
            'settings': settings,
            'dashboard': dashboard_data,
            'page_name': 'dashboard',
        }
        
        return request.render('tazweed_client_portal.portal_dashboard', values)

    # ==================== JOB ORDERS ====================
    
    @http.route(['/my/job-orders', '/my/job-orders/page/<int:page>'], 
                type='http', auth='user', website=True)
    def portal_job_orders(self, page=1, sortby=None, filterby=None, search=None, **kw):
        """List all job orders for the client"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        
        if not client:
            return request.redirect('/my')
        
        JobOrder = request.env['tazweed.job.order'].sudo()
        
        domain = [('client_id', '=', client.id)]
        
        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Title'), 'order': 'name'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Filtering
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'open': {'label': _('Open'), 'domain': [('state', '=', 'open')]},
            'in_progress': {'label': _('In Progress'), 'domain': [('state', '=', 'in_progress')]},
            'completed': {'label': _('Completed'), 'domain': [('state', '=', 'completed')]},
        }
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        # Search
        if search:
            domain += [('name', 'ilike', search)]
        
        # Pager
        job_order_count = JobOrder.search_count(domain)
        pager = portal_pager(
            url='/my/job-orders',
            url_args={'sortby': sortby, 'filterby': filterby, 'search': search},
            total=job_order_count,
            page=page,
            step=10
        )
        
        job_orders = JobOrder.search(domain, order=order, limit=10, offset=pager['offset'])
        
        values = {
            'job_orders': job_orders,
            'page_name': 'job_orders',
            'pager': pager,
            'default_url': '/my/job-orders',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'search': search,
            'client': client,
        }
        
        return request.render('tazweed_client_portal.portal_job_orders', values)
    
    @http.route(['/my/job-orders/<int:order_id>'], type='http', auth='user', website=True)
    def portal_job_order_detail(self, order_id, **kw):
        """Job order detail view"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        
        job_order = request.env['tazweed.job.order'].sudo().browse(order_id)
        
        if not job_order.exists() or job_order.client_id.id != client.id:
            return request.redirect('/my/job-orders')
        
        # Get candidates for this job order
        candidates = request.env['tazweed.candidate'].sudo().search([
            ('job_order_id', '=', job_order.id)
        ])
        
        values = {
            'job_order': job_order,
            'candidates': candidates,
            'page_name': 'job_order_detail',
            'client': client,
        }
        
        return request.render('tazweed_client_portal.portal_job_order_detail', values)

    # ==================== CANDIDATES ====================
    
    @http.route(['/my/candidates', '/my/candidates/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_candidates(self, page=1, sortby=None, filterby=None, **kw):
        """List candidates pending review"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        
        if not client:
            return request.redirect('/my')
        
        Candidate = request.env['tazweed.candidate'].sudo()
        
        domain = [('job_order_id.client_id', '=', client.id)]
        
        # Filtering
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'pending': {'label': _('Pending Review'), 'domain': [('state', '=', 'pending_approval')]},
            'approved': {'label': _('Approved'), 'domain': [('state', '=', 'approved')]},
            'rejected': {'label': _('Rejected'), 'domain': [('state', '=', 'rejected')]},
        }
        if not filterby:
            filterby = 'pending'
        domain += searchbar_filters[filterby]['domain']
        
        # Pager
        candidate_count = Candidate.search_count(domain)
        pager = portal_pager(
            url='/my/candidates',
            url_args={'filterby': filterby},
            total=candidate_count,
            page=page,
            step=10
        )
        
        candidates = Candidate.search(domain, limit=10, offset=pager['offset'])
        
        values = {
            'candidates': candidates,
            'page_name': 'candidates',
            'pager': pager,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'client': client,
        }
        
        return request.render('tazweed_client_portal.portal_candidates', values)
    
    @http.route(['/my/candidates/<int:candidate_id>/approve'], type='http', auth='user', website=True)
    def portal_approve_candidate(self, candidate_id, **kw):
        """Approve a candidate"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        portal_user = self._get_portal_user(client)
        
        if not portal_user or not portal_user.can_approve_candidates:
            return request.redirect('/my/candidates')
        
        candidate = request.env['tazweed.candidate'].sudo().browse(candidate_id)
        
        if candidate.exists() and candidate.job_order_id.client_id.id == client.id:
            candidate.write({'state': 'approved'})
            
            # Create notification
            request.env['client.portal.notification'].sudo().create({
                'client_id': client.id,
                'title': _('Candidate Approved'),
                'message': _('You approved candidate %s') % candidate.name,
                'notification_type': 'success',
            })
        
        return request.redirect('/my/candidates')
    
    @http.route(['/my/candidates/<int:candidate_id>/reject'], type='http', auth='user', website=True)
    def portal_reject_candidate(self, candidate_id, **kw):
        """Reject a candidate"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        portal_user = self._get_portal_user(client)
        
        if not portal_user or not portal_user.can_approve_candidates:
            return request.redirect('/my/candidates')
        
        candidate = request.env['tazweed.candidate'].sudo().browse(candidate_id)
        
        if candidate.exists() and candidate.job_order_id.client_id.id == client.id:
            candidate.write({'state': 'rejected'})
        
        return request.redirect('/my/candidates')

    # ==================== PLACEMENTS ====================
    
    @http.route(['/my/placements', '/my/placements/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_placements(self, page=1, filterby=None, **kw):
        """List all placements"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        
        if not client:
            return request.redirect('/my')
        
        Placement = request.env['tazweed.placement'].sudo()
        
        domain = [('client_id', '=', client.id)]
        
        # Filtering
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'active': {'label': _('Active'), 'domain': [('state', '=', 'active')]},
            'completed': {'label': _('Completed'), 'domain': [('state', '=', 'completed')]},
        }
        if not filterby:
            filterby = 'active'
        domain += searchbar_filters[filterby]['domain']
        
        # Pager
        placement_count = Placement.search_count(domain)
        pager = portal_pager(
            url='/my/placements',
            url_args={'filterby': filterby},
            total=placement_count,
            page=page,
            step=10
        )
        
        placements = Placement.search(domain, limit=10, offset=pager['offset'])
        
        values = {
            'placements': placements,
            'page_name': 'placements',
            'pager': pager,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'client': client,
        }
        
        return request.render('tazweed_client_portal.portal_placements', values)

    # ==================== INVOICES ====================
    
    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_invoices(self, page=1, filterby=None, **kw):
        """List all invoices"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        
        if not client:
            return request.redirect('/my')
        
        Invoice = request.env['tazweed.client.invoice'].sudo()
        
        domain = [('client_id', '=', client.id)]
        
        # Filtering
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'pending': {'label': _('Pending'), 'domain': [('state', '=', 'sent')]},
            'paid': {'label': _('Paid'), 'domain': [('state', '=', 'paid')]},
        }
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        # Pager
        invoice_count = Invoice.search_count(domain)
        pager = portal_pager(
            url='/my/invoices',
            url_args={'filterby': filterby},
            total=invoice_count,
            page=page,
            step=10
        )
        
        invoices = Invoice.search(domain, order='invoice_date desc', limit=10, offset=pager['offset'])
        
        values = {
            'invoices': invoices,
            'page_name': 'invoices',
            'pager': pager,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'client': client,
        }
        
        return request.render('tazweed_client_portal.portal_invoices', values)

    # ==================== DOCUMENTS ====================
    
    @http.route(['/my/documents', '/my/documents/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_documents(self, page=1, category=None, **kw):
        """List all shared documents"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        
        if not client:
            return request.redirect('/my')
        
        Document = request.env['client.portal.document'].sudo()
        
        domain = [
            ('client_id', '=', client.id),
            ('visibility', '=', 'client'),
            ('is_latest', '=', True),
        ]
        
        # Category filter
        if category:
            domain.append(('category', '=', category))
        
        # Pager
        document_count = Document.search_count(domain)
        pager = portal_pager(
            url='/my/documents',
            url_args={'category': category},
            total=document_count,
            page=page,
            step=12
        )
        
        documents = Document.search(domain, order='create_date desc', limit=12, offset=pager['offset'])
        
        # Get categories for filter
        categories = [
            ('contract', _('Contracts')),
            ('invoice', _('Invoices')),
            ('report', _('Reports')),
            ('compliance', _('Compliance')),
            ('timesheet', _('Timesheets')),
            ('certificate', _('Certificates')),
            ('policy', _('Policies')),
            ('other', _('Other')),
        ]
        
        values = {
            'documents': documents,
            'page_name': 'documents',
            'pager': pager,
            'categories': categories,
            'current_category': category,
            'client': client,
        }
        
        return request.render('tazweed_client_portal.portal_documents', values)
    
    @http.route(['/my/documents/<int:doc_id>/download'], type='http', auth='user', website=True)
    def portal_download_document(self, doc_id, **kw):
        """Download a document"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        portal_user = self._get_portal_user(client)
        
        document = request.env['client.portal.document'].sudo().browse(doc_id)
        
        if not document.exists() or document.client_id.id != client.id:
            return request.redirect('/my/documents')
        
        if portal_user and not portal_user.can_download_documents:
            return request.redirect('/my/documents')
        
        # Log download
        document.with_context(
            remote_ip=request.httprequest.remote_addr
        ).action_download(portal_user.id if portal_user else False)
        
        # Return file
        return request.make_response(
            document.file,
            headers=[
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', f'attachment; filename="{document.file_name}"'),
            ]
        )

    # ==================== MESSAGES ====================
    
    @http.route(['/my/messages', '/my/messages/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_messages(self, page=1, **kw):
        """List all messages"""
        partner = request.env.user.partner_id
        client = self._get_client_for_partner(partner)
        
        if not client:
            return request.redirect('/my')
        
        Message = request.env['client.portal.message'].sudo()
        
        domain = [
            ('client_id', '=', client.id),
            ('is_archived', '=', False),
        ]
        
        # Pager
        message_count = Message.search_count(domain)
        pager = portal_pager(
            url='/my/messages',
            total=message_count,
            page=page,
            step=20
        )
        
        messages = Message.search(domain, order='create_date desc', limit=20, offset=pager['offset'])
        
        values = {
            'messages': messages,
            'page_name': 'messages',
            'pager': pager,
            'client': client,
        }
        
        return request.render('tazweed_client_portal.portal_messages', values)
