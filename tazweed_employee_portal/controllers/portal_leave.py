# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import datetime


class TazweedLeavePortal(CustomerPortal):
    """Leave Portal Controller"""

    def _get_current_employee(self):
        """Get current user's employee record"""
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
        ], limit=1)
        return employee

    @http.route(['/my/leaves', '/my/leaves/page/<int:page>'], type='http', auth='user', website=True)
    def portal_leaves(self, page=1, sortby=None, filterby=None, **kw):
        """Leave Requests List"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        Leave = request.env['hr.leave'].sudo()
        
        # Sorting
        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'date_from desc'},
            'name': {'label': _('Leave Type'), 'order': 'holiday_status_id'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        # Filtering
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'pending': {'label': _('Pending'), 'domain': [('state', 'in', ['draft', 'confirm'])]},
            'approved': {'label': _('Approved'), 'domain': [('state', '=', 'validate')]},
            'refused': {'label': _('Refused'), 'domain': [('state', '=', 'refuse')]},
        }
        if not filterby:
            filterby = 'all'
        
        domain = [('employee_id', '=', employee.id)] + searchbar_filters[filterby]['domain']
        
        leave_count = Leave.search_count(domain)
        
        pager = portal_pager(
            url='/my/leaves',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=leave_count,
            page=page,
            step=10,
        )
        
        leaves = Leave.search(
            domain,
            order=order,
            limit=10,
            offset=pager['offset'],
        )
        
        values = {
            'page_name': 'leaves',
            'leaves': leaves,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'employee': employee,
        }
        
        return request.render('tazweed_employee_portal.portal_leaves', values)

    @http.route(['/my/leaves/<int:leave_id>'], type='http', auth='user', website=True)
    def portal_leave_detail(self, leave_id, **kw):
        """Leave Request Detail"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        if not leave.exists() or leave.employee_id.id != employee.id:
            return request.redirect('/my/leaves')
        
        values = {
            'page_name': 'leave_detail',
            'leave': leave,
            'employee': employee,
        }
        
        return request.render('tazweed_employee_portal.portal_leave_detail', values)

    @http.route(['/my/leaves/new'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_leave_new(self, **post):
        """Create New Leave Request"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        if request.httprequest.method == 'POST':
            # Create leave request
            try:
                leave_vals = {
                    'employee_id': employee.id,
                    'holiday_status_id': int(post.get('leave_type')),
                    'date_from': post.get('date_from'),
                    'date_to': post.get('date_to'),
                    'name': post.get('reason', ''),
                }
                
                leave = request.env['hr.leave'].sudo().create(leave_vals)
                
                # Submit for approval
                if post.get('submit'):
                    leave.action_confirm()
                
                return request.redirect(f'/my/leaves/{leave.id}')
            except Exception as e:
                values = {
                    'page_name': 'leave_new',
                    'employee': employee,
                    'leave_types': request.env['hr.leave.type'].sudo().search([]),
                    'error': str(e),
                }
                return request.render('tazweed_employee_portal.portal_leave_new', values)
        
        # Get leave types
        leave_types = request.env['hr.leave.type'].sudo().search([])
        
        values = {
            'page_name': 'leave_new',
            'employee': employee,
            'leave_types': leave_types,
        }
        
        return request.render('tazweed_employee_portal.portal_leave_new', values)

    @http.route(['/my/leaves/<int:leave_id>/cancel'], type='http', auth='user', website=True)
    def portal_leave_cancel(self, leave_id, **kw):
        """Cancel Leave Request"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        if leave.exists() and leave.employee_id.id == employee.id and leave.state in ['draft', 'confirm']:
            leave.action_refuse()
        
        return request.redirect('/my/leaves')

    @http.route(['/my/leave-balance'], type='http', auth='user', website=True)
    def portal_leave_balance(self, **kw):
        """Leave Balance"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        # Get allocations
        allocations = request.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
        ])
        
        # Group by leave type
        balance_data = {}
        for alloc in allocations:
            leave_type = alloc.holiday_status_id
            if leave_type.id not in balance_data:
                balance_data[leave_type.id] = {
                    'leave_type': leave_type,
                    'allocated': 0,
                    'used': 0,
                    'remaining': 0,
                }
            balance_data[leave_type.id]['allocated'] += alloc.number_of_days
            balance_data[leave_type.id]['used'] += alloc.used_days
            balance_data[leave_type.id]['remaining'] += alloc.remaining_days
        
        values = {
            'page_name': 'leave_balance',
            'employee': employee,
            'balance_data': balance_data.values(),
        }
        
        return request.render('tazweed_employee_portal.portal_leave_balance', values)

    @http.route(['/my/approvals'], type='http', auth='user', website=True)
    def portal_approvals(self, page=1, **kw):
        """Pending Approvals (for managers)"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        Leave = request.env['hr.leave'].sudo()
        
        # Get pending approvals for team members
        domain = [
            ('employee_id.parent_id', '=', employee.id),
            ('state', '=', 'confirm'),
        ]
        
        approval_count = Leave.search_count(domain)
        
        pager = portal_pager(
            url='/my/approvals',
            total=approval_count,
            page=page,
            step=10,
        )
        
        approvals = Leave.search(
            domain,
            order='date_from asc',
            limit=10,
            offset=pager['offset'],
        )
        
        values = {
            'page_name': 'approvals',
            'approvals': approvals,
            'pager': pager,
            'employee': employee,
        }
        
        return request.render('tazweed_employee_portal.portal_approvals', values)

    @http.route(['/my/approvals/<int:leave_id>/approve'], type='http', auth='user', website=True)
    def portal_approve_leave(self, leave_id, **kw):
        """Approve Leave Request"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        if leave.exists() and leave.employee_id.parent_id.id == employee.id and leave.state == 'confirm':
            leave.action_validate()
        
        return request.redirect('/my/approvals')

    @http.route(['/my/approvals/<int:leave_id>/refuse'], type='http', auth='user', website=True)
    def portal_refuse_leave(self, leave_id, **kw):
        """Refuse Leave Request"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        leave = request.env['hr.leave'].sudo().browse(leave_id)
        if leave.exists() and leave.employee_id.parent_id.id == employee.id and leave.state == 'confirm':
            leave.action_refuse()
        
        return request.redirect('/my/approvals')
