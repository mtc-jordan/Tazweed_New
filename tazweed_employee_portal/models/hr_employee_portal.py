# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta


class HrEmployeePortal(models.Model):
    """Extend hr.employee for portal functionality"""
    _inherit = 'hr.employee'

    # Portal Settings
    portal_access = fields.Boolean(
        string='Portal Access',
        default=True,
    )
    portal_last_login = fields.Datetime(
        string='Last Portal Login',
        readonly=True,
    )
    portal_notification_email = fields.Boolean(
        string='Email Notifications',
        default=True,
    )
    portal_notification_sms = fields.Boolean(
        string='SMS Notifications',
        default=False,
    )

    # Dashboard Metrics
    pending_leaves = fields.Integer(
        string='Pending Leaves',
        compute='_compute_portal_metrics',
    )
    pending_approvals = fields.Integer(
        string='Pending Approvals',
        compute='_compute_portal_metrics',
    )
    unread_announcements = fields.Integer(
        string='Unread Announcements',
        compute='_compute_portal_metrics',
    )
    expiring_documents = fields.Integer(
        string='Expiring Documents',
        compute='_compute_portal_metrics',
    )

    @api.depends_context('uid')
    def _compute_portal_metrics(self):
        """Compute portal dashboard metrics"""
        for employee in self:
            # Pending leaves
            employee.pending_leaves = self.env['hr.leave'].search_count([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['draft', 'confirm']),
            ])
            
            # Pending approvals (if manager)
            if employee.user_id:
                employee.pending_approvals = self.env['hr.leave'].search_count([
                    ('employee_id.parent_id', '=', employee.id),
                    ('state', '=', 'confirm'),
                ])
            else:
                employee.pending_approvals = 0
            
            # Unread announcements
            employee.unread_announcements = self.env['tazweed.portal.announcement'].search_count([
                ('state', '=', 'published'),
                ('target_employees', 'in', employee.id),
                ('read_by_employees', 'not in', employee.id),
            ])
            
            # Expiring documents
            thirty_days = datetime.now() + timedelta(days=30)
            employee.expiring_documents = self.env['tazweed.employee.document'].search_count([
                ('employee_id', '=', employee.id),
                ('expiry_date', '<=', thirty_days.date()),
                ('expiry_date', '>=', datetime.now().date()),
                ('state', '=', 'active'),
            ])

    def get_portal_dashboard_data(self):
        """Get dashboard data for portal"""
        self.ensure_one()
        
        # Leave balance
        leave_allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.id),
            ('state', '=', 'validate'),
        ])
        
        leave_balance = {}
        for alloc in leave_allocations:
            leave_type = alloc.holiday_status_id.name
            if leave_type not in leave_balance:
                leave_balance[leave_type] = {
                    'allocated': 0,
                    'used': 0,
                    'remaining': 0,
                }
            leave_balance[leave_type]['allocated'] += alloc.number_of_days
            leave_balance[leave_type]['used'] += alloc.used_days
            leave_balance[leave_type]['remaining'] += alloc.remaining_days
        
        # Recent attendance
        recent_attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
        ], limit=5, order='check_in desc')
        
        # Recent payslips (optional - only if payroll module is installed)
        recent_payslips = []
        if 'hr.payslip' in self.env:
            recent_payslips = self.env['hr.payslip'].search([
                ('employee_id', '=', self.id),
                ('state', '=', 'done'),
            ], limit=3, order='date_to desc')
        
        # Pending requests
        pending_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.id),
            ('state', 'in', ['draft', 'confirm']),
        ])
        
        # Announcements
        announcements = self.env['tazweed.portal.announcement'].search([
            ('state', '=', 'published'),
            '|',
            ('target_type', '=', 'all'),
            ('target_employees', 'in', self.id),
        ], limit=5, order='publish_date desc')
        
        return {
            'employee': self,
            'leave_balance': leave_balance,
            'recent_attendance': recent_attendance,
            'recent_payslips': recent_payslips,
            'pending_leaves': pending_leaves,
            'announcements': announcements,
            'pending_approvals': self.pending_approvals,
            'expiring_documents': self.expiring_documents,
        }

    def action_portal_check_in(self):
        """Check in from portal"""
        self.ensure_one()
        return self.env['hr.attendance'].create({
            'employee_id': self.id,
            'check_in': fields.Datetime.now(),
        })

    def action_portal_check_out(self):
        """Check out from portal"""
        self.ensure_one()
        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_out', '=', False),
        ], limit=1)
        if attendance:
            attendance.write({'check_out': fields.Datetime.now()})
        return attendance

    def get_current_attendance_state(self):
        """Get current attendance state"""
        self.ensure_one()
        attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', self.id),
            ('check_out', '=', False),
        ], limit=1)
        return 'checked_in' if attendance else 'checked_out'


    @api.model
    def get_employee_dashboard_data(self):
        """Get dashboard data for OWL employee dashboard"""
        employee = self.env.user.employee_id
        if not employee:
            return {
                'employee': None,
                'stats': {},
                'leave_balances': [],
                'recent_activities': [],
                'upcoming_events': [],
                'quick_links': [],
                'announcements': [],
                'team_members': [],
            }
        
        today = datetime.now().date()
        
        # Employee info
        employee_data = {
            'id': employee.id,
            'name': employee.name,
            'job_title': employee.job_id.name if employee.job_id else '',
            'department': employee.department_id.name if employee.department_id else '',
        }
        
        # Leave balance
        leave_balances = []
        leave_allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
        ])
        
        leave_by_type = {}
        for alloc in leave_allocations:
            leave_type = alloc.holiday_status_id.name
            if leave_type not in leave_by_type:
                leave_by_type[leave_type] = 0
            leave_by_type[leave_type] += alloc.number_of_days - alloc.leaves_taken
        
        for leave_type, balance in leave_by_type.items():
            leave_balances.append({
                'name': leave_type,
                'balance': balance,
            })
        
        total_leave_balance = sum(lb['balance'] for lb in leave_balances)
        
        # Pending requests
        pending_requests = self.env['hr.leave'].search_count([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['draft', 'confirm']),
        ])
        
        # Attendance rate (last 30 days)
        thirty_days_ago = today - timedelta(days=30)
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', str(thirty_days_ago)),
        ])
        working_days = 22  # Approximate working days in a month
        attendance_rate = min(100, round((len(attendances) / working_days) * 100))
        
        # Performance rating
        performance_rating = 0.0
        PerformanceReview = self.env.get('tazweed.performance.review')
        if PerformanceReview:
            latest_review = PerformanceReview.search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'completed'),
            ], limit=1, order='completion_date desc')
            if latest_review:
                performance_rating = latest_review.final_rating or 0.0
        
        # Training hours
        training_hours = 0
        
        # Documents expiring
        thirty_days_later = today + timedelta(days=30)
        EmployeeDocument = self.env.get('tazweed.employee.document')
        documents_expiring = 0
        if EmployeeDocument:
            documents_expiring = EmployeeDocument.search_count([
                ('employee_id', '=', employee.id),
                ('expiry_date', '<=', str(thirty_days_later)),
                ('expiry_date', '>=', str(today)),
                ('state', '=', 'active'),
            ])
        
        # Stats
        stats = {
            'leaveBalance': total_leave_balance,
            'pendingRequests': pending_requests,
            'attendanceRate': attendance_rate,
            'performanceRating': performance_rating,
            'trainingHours': training_hours,
            'documentsExpiring': documents_expiring,
            'upcomingHolidays': 0,
            'announcements': 0,
        }
        
        # Recent activities
        recent_activities = []
        
        # Recent leaves
        recent_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
        ], limit=3, order='create_date desc')
        for leave in recent_leaves:
            recent_activities.append({
                'id': f'leave_{leave.id}',
                'type': 'leave',
                'title': f'{leave.holiday_status_id.name} - {leave.state}',
                'date': str(leave.create_date.date()) if leave.create_date else '',
            })
        
        # Recent attendance
        recent_attendance = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
        ], limit=3, order='check_in desc')
        for att in recent_attendance:
            recent_activities.append({
                'id': f'att_{att.id}',
                'type': 'attendance',
                'title': f'Check-in at {att.check_in.strftime("%H:%M")}' if att.check_in else 'Attendance',
                'date': str(att.check_in.date()) if att.check_in else '',
            })
        
        # Sort by date
        recent_activities = sorted(recent_activities, key=lambda x: x['date'], reverse=True)[:5]
        
        # Upcoming events
        upcoming_events = []
        
        # Upcoming leaves
        upcoming_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('date_from', '>=', str(today)),
            ('state', '=', 'validate'),
        ], limit=3, order='date_from')
        for leave in upcoming_leaves:
            leave_date = leave.date_from.date() if leave.date_from else today
            upcoming_events.append({
                'id': f'leave_{leave.id}',
                'day': leave_date.day,
                'month': leave_date.strftime('%b'),
                'title': leave.holiday_status_id.name,
                'type': 'Leave',
            })
        
        # Announcements
        announcements = []
        Announcement = self.env.get('tazweed.portal.announcement')
        if Announcement:
            portal_announcements = Announcement.search([
                ('state', '=', 'published'),
            ], limit=3, order='publish_date desc')
            for ann in portal_announcements:
                announcements.append({
                    'id': ann.id,
                    'title': ann.title,
                    'content': ann.content[:150] + '...' if ann.content and len(ann.content) > 150 else ann.content,
                    'date': str(ann.publish_date) if ann.publish_date else '',
                })
        
        # Team members
        team_members = []
        if employee.department_id:
            team = self.search([
                ('department_id', '=', employee.department_id.id),
                ('id', '!=', employee.id),
            ], limit=6)
            for member in team:
                team_members.append({
                    'id': member.id,
                    'name': member.name,
                    'job_title': member.job_id.name if member.job_id else '',
                })
        
        return {
            'employee': employee_data,
            'stats': stats,
            'leave_balances': leave_balances,
            'recent_activities': recent_activities,
            'upcoming_events': upcoming_events,
            'quick_links': [],
            'announcements': announcements,
            'team_members': team_members,
        }
