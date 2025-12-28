# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import datetime, timedelta
import json


class TazweedAttendancePortal(CustomerPortal):
    """Attendance Portal Controller"""

    def _get_current_employee(self):
        """Get current user's employee record"""
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
        ], limit=1)
        return employee

    @http.route(['/my/attendance', '/my/attendance/page/<int:page>'], type='http', auth='user', website=True)
    def portal_attendance(self, page=1, date_from=None, date_to=None, **kw):
        """Attendance List"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        Attendance = request.env['hr.attendance'].sudo()
        
        domain = [('employee_id', '=', employee.id)]
        
        # Date filter
        if date_from:
            domain.append(('check_in', '>=', date_from))
        if date_to:
            domain.append(('check_in', '<=', date_to))
        
        attendance_count = Attendance.search_count(domain)
        
        pager = portal_pager(
            url='/my/attendance',
            url_args={'date_from': date_from, 'date_to': date_to},
            total=attendance_count,
            page=page,
            step=15,
        )
        
        attendances = Attendance.search(
            domain,
            order='check_in desc',
            limit=15,
            offset=pager['offset'],
        )
        
        # Get current state
        current_state = employee.get_current_attendance_state()
        
        values = {
            'page_name': 'attendance',
            'attendances': attendances,
            'pager': pager,
            'employee': employee,
            'current_state': current_state,
            'date_from': date_from,
            'date_to': date_to,
        }
        
        return request.render('tazweed_employee_portal.portal_attendance', values)

    @http.route(['/my/attendance/check-in'], type='http', auth='user', website=True, methods=['POST'])
    def portal_check_in(self, **post):
        """Check In"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        # Check if already checked in
        current_state = employee.get_current_attendance_state()
        if current_state == 'checked_in':
            return request.redirect('/my/attendance')
        
        # Create attendance record
        attendance_vals = {
            'employee_id': employee.id,
            'check_in': fields.Datetime.now(),
        }
        
        # Add location if provided
        if post.get('latitude') and post.get('longitude'):
            attendance_vals.update({
                'check_in_latitude': float(post.get('latitude')),
                'check_in_longitude': float(post.get('longitude')),
            })
        
        request.env['hr.attendance'].sudo().create(attendance_vals)
        
        return request.redirect('/my/attendance')

    @http.route(['/my/attendance/check-out'], type='http', auth='user', website=True, methods=['POST'])
    def portal_check_out(self, **post):
        """Check Out"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        # Find open attendance
        attendance = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_out', '=', False),
        ], limit=1)
        
        if attendance:
            update_vals = {
                'check_out': fields.Datetime.now(),
            }
            
            # Add location if provided
            if post.get('latitude') and post.get('longitude'):
                update_vals.update({
                    'check_out_latitude': float(post.get('latitude')),
                    'check_out_longitude': float(post.get('longitude')),
                })
            
            attendance.write(update_vals)
        
        return request.redirect('/my/attendance')

    @http.route(['/my/attendance/status'], type='json', auth='user')
    def portal_attendance_status(self, **kw):
        """Get current attendance status (AJAX)"""
        employee = self._get_current_employee()
        if not employee:
            return {'error': 'Employee not found'}
        
        current_state = employee.get_current_attendance_state()
        
        # Get current attendance if checked in
        current_attendance = None
        if current_state == 'checked_in':
            attendance = request.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False),
            ], limit=1)
            if attendance:
                current_attendance = {
                    'check_in': attendance.check_in.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': attendance.worked_hours,
                }
        
        return {
            'state': current_state,
            'current_attendance': current_attendance,
        }

    @http.route(['/my/attendance/summary'], type='http', auth='user', website=True)
    def portal_attendance_summary(self, month=None, year=None, **kw):
        """Attendance Summary"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        # Default to current month
        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year
        
        month = int(month)
        year = int(year)
        
        # Get attendance for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        attendances = request.env['hr.attendance'].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_date),
            ('check_in', '<=', end_date),
        ])
        
        # Calculate summary
        total_hours = sum(att.worked_hours for att in attendances)
        total_days = len(set(att.check_in.date() for att in attendances))
        late_count = len([att for att in attendances if getattr(att, 'is_late', False)])
        overtime_hours = sum(getattr(att, 'overtime_hours', 0) for att in attendances)
        
        # Generate month options
        months = [
            {'value': i, 'name': datetime(2000, i, 1).strftime('%B')}
            for i in range(1, 13)
        ]
        
        years = list(range(datetime.now().year - 2, datetime.now().year + 1))
        
        values = {
            'page_name': 'attendance_summary',
            'employee': employee,
            'attendances': attendances,
            'month': month,
            'year': year,
            'months': months,
            'years': years,
            'summary': {
                'total_hours': total_hours,
                'total_days': total_days,
                'late_count': late_count,
                'overtime_hours': overtime_hours,
            },
        }
        
        return request.render('tazweed_employee_portal.portal_attendance_summary', values)

    @http.route(['/my/attendance/<int:attendance_id>'], type='http', auth='user', website=True)
    def portal_attendance_detail(self, attendance_id, **kw):
        """Attendance Detail"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        attendance = request.env['hr.attendance'].sudo().browse(attendance_id)
        if not attendance.exists() or attendance.employee_id.id != employee.id:
            return request.redirect('/my/attendance')
        
        values = {
            'page_name': 'attendance_detail',
            'attendance': attendance,
            'employee': employee,
        }
        
        return request.render('tazweed_employee_portal.portal_attendance_detail', values)
