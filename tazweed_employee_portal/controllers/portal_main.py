# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import datetime, timedelta


class TazweedEmployeePortal(CustomerPortal):
    """Main Employee Portal Controller"""

    def _prepare_home_portal_values(self, counters):
        """Prepare portal home values"""
        values = super()._prepare_home_portal_values(counters)
        
        employee = self._get_current_employee()
        if not employee:
            return values
        
        if 'leave_count' in counters:
            values['leave_count'] = request.env['hr.leave'].search_count([
                ('employee_id', '=', employee.id),
            ])
        
        if 'payslip_count' in counters:
            # Only count payslips if payroll module is installed
            if 'hr.payslip' in request.env:
                values['payslip_count'] = request.env['hr.payslip'].search_count([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'done'),
                ])
            else:
                values['payslip_count'] = 0
        
        if 'document_count' in counters:
            values['document_count'] = request.env['tazweed.employee.document'].search_count([
                ('employee_id', '=', employee.id),
            ])
        
        if 'announcement_count' in counters:
            values['announcement_count'] = request.env['tazweed.portal.announcement'].search_count([
                ('state', '=', 'published'),
            ])
        
        return values

    def _get_current_employee(self):
        """Get current user's employee record"""
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
        ], limit=1)
        return employee

    @http.route(['/my/dashboard'], type='http', auth='user', website=True)
    def portal_dashboard(self, **kw):
        """Employee Dashboard"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        dashboard_data = employee.get_portal_dashboard_data()
        
        values = {
            'page_name': 'dashboard',
            'employee': employee,
            'dashboard_data': dashboard_data,
        }
        
        return request.render('tazweed_employee_portal.portal_dashboard', values)

    @http.route(['/my/profile'], type='http', auth='user', website=True)
    def portal_profile(self, **kw):
        """Employee Profile"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        values = {
            'page_name': 'profile',
            'employee': employee,
        }
        
        return request.render('tazweed_employee_portal.portal_profile', values)

    @http.route(['/my/profile/edit'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_profile_edit(self, **post):
        """Edit Employee Profile"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        if request.httprequest.method == 'POST':
            # Update allowed fields
            allowed_fields = ['mobile_phone', 'private_email', 'emergency_contact', 'emergency_phone']
            update_vals = {}
            for field in allowed_fields:
                if field in post:
                    update_vals[field] = post[field]
            
            if update_vals:
                employee.sudo().write(update_vals)
            
            return request.redirect('/my/profile')
        
        values = {
            'page_name': 'profile_edit',
            'employee': employee,
        }
        
        return request.render('tazweed_employee_portal.portal_profile_edit', values)

    @http.route(['/my/announcements'], type='http', auth='user', website=True)
    def portal_announcements(self, page=1, **kw):
        """Announcements List"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        Announcement = request.env['tazweed.portal.announcement'].sudo()
        
        domain = [
            ('state', '=', 'published'),
            '|',
            ('target_type', '=', 'all'),
            '|',
            ('target_employees', 'in', employee.id),
            ('target_department_ids', 'in', employee.department_id.id if employee.department_id else []),
        ]
        
        announcement_count = Announcement.search_count(domain)
        
        pager = portal_pager(
            url='/my/announcements',
            total=announcement_count,
            page=page,
            step=10,
        )
        
        announcements = Announcement.search(
            domain,
            order='publish_date desc',
            limit=10,
            offset=pager['offset'],
        )
        
        values = {
            'page_name': 'announcements',
            'announcements': announcements,
            'pager': pager,
            'employee': employee,
        }
        
        return request.render('tazweed_employee_portal.portal_announcements', values)

    @http.route(['/my/announcements/<int:announcement_id>'], type='http', auth='user', website=True)
    def portal_announcement_detail(self, announcement_id, **kw):
        """Announcement Detail"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        announcement = request.env['tazweed.portal.announcement'].sudo().browse(announcement_id)
        if not announcement.exists():
            return request.redirect('/my/announcements')
        
        # Mark as read
        announcement.mark_as_read(employee.id)
        
        values = {
            'page_name': 'announcement_detail',
            'announcement': announcement,
            'employee': employee,
        }
        
        return request.render('tazweed_employee_portal.portal_announcement_detail', values)

    @http.route(['/my/team'], type='http', auth='user', website=True)
    def portal_team(self, **kw):
        """Team View (for managers)"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        # Get team members
        team_members = request.env['hr.employee'].sudo().search([
            ('parent_id', '=', employee.id),
        ])
        
        values = {
            'page_name': 'team',
            'employee': employee,
            'team_members': team_members,
        }
        
        return request.render('tazweed_employee_portal.portal_team', values)

    @http.route(['/my/calendar'], type='http', auth='user', website=True)
    def portal_calendar(self, **kw):
        """Team Calendar"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        # Get team leaves
        department_id = employee.department_id.id if employee.department_id else False
        
        leaves = request.env['hr.leave'].sudo().search([
            ('employee_id.department_id', '=', department_id),
            ('state', '=', 'validate'),
            ('date_from', '>=', datetime.now() - timedelta(days=30)),
            ('date_to', '<=', datetime.now() + timedelta(days=60)),
        ])
        
        # Get public holidays
        holidays = request.env['tazweed.public.holiday'].sudo().search([
            ('state', '=', 'confirmed'),
            ('date', '>=', datetime.now().date() - timedelta(days=30)),
            ('date', '<=', datetime.now().date() + timedelta(days=60)),
        ])
        
        values = {
            'page_name': 'calendar',
            'employee': employee,
            'leaves': leaves,
            'holidays': holidays,
        }
        
        return request.render('tazweed_employee_portal.portal_calendar', values)
