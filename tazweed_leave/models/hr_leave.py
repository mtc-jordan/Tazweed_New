# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta


class HrLeave(models.Model):
    """Extended Leave Request with UAE-specific features"""
    _inherit = 'hr.leave'

    # Reference
    reference = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default='/',
    )
    
    # UAE Fields
    is_emergency = fields.Boolean(
        string='Emergency Leave',
        default=False,
    )
    return_date = fields.Date(
        string='Expected Return Date',
        compute='_compute_return_date',
        store=True,
    )
    actual_return_date = fields.Date(
        string='Actual Return Date',
    )
    
    # Leave Balance
    leave_balance_before = fields.Float(
        string='Balance Before',
        compute='_compute_leave_balance',
        store=True,
    )
    leave_balance_after = fields.Float(
        string='Balance After',
        compute='_compute_leave_balance',
        store=True,
    )
    
    # Salary Impact
    salary_impact = fields.Selection(
        related='holiday_status_id.salary_impact',
        store=True,
    )
    salary_percentage = fields.Float(
        related='holiday_status_id.salary_percentage',
        store=True,
    )
    salary_deduction = fields.Float(
        string='Salary Deduction',
        compute='_compute_salary_deduction',
        store=True,
    )
    
    # Document
    document_ids = fields.Many2many(
        'ir.attachment',
        string='Supporting Documents',
    )
    document_required = fields.Boolean(
        string='Document Required',
        compute='_compute_document_required',
    )
    
    # Contact During Leave
    contact_address = fields.Text(
        string='Contact Address During Leave',
    )
    contact_phone = fields.Char(
        string='Contact Phone',
    )
    
    # Handover
    handover_to_id = fields.Many2one(
        'hr.employee',
        string='Handover To',
    )
    handover_notes = fields.Text(
        string='Handover Notes',
    )
    
    # Approval
    first_approval_date = fields.Datetime(
        string='First Approval Date',
        readonly=True,
    )
    first_approver_id = fields.Many2one(
        'res.users',
        string='First Approver',
        readonly=True,
    )
    second_approval_date = fields.Datetime(
        string='Second Approval Date',
        readonly=True,
    )
    second_approver_id = fields.Many2one(
        'res.users',
        string='Second Approver',
        readonly=True,
    )
    
    # Cancellation
    cancellation_reason = fields.Text(
        string='Cancellation Reason',
    )
    cancelled_by_id = fields.Many2one(
        'res.users',
        string='Cancelled By',
        readonly=True,
    )
    cancellation_date = fields.Datetime(
        string='Cancellation Date',
        readonly=True,
    )
    
    # Public Holidays
    public_holidays_count = fields.Integer(
        string='Public Holidays',
        compute='_compute_public_holidays',
        store=True,
    )
    weekends_count = fields.Integer(
        string='Weekends',
        compute='_compute_public_holidays',
        store=True,
    )
    working_days = fields.Float(
        string='Working Days',
        compute='_compute_public_holidays',
        store=True,
    )
    
    # Payroll Integration
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        readonly=True,
    )
    processed_in_payroll = fields.Boolean(
        string='Processed in Payroll',
        default=False,
    )

    @api.model
    def create(self, vals):
        """Generate sequence on create"""
        if vals.get('reference', '/') == '/':
            vals['reference'] = self.env['ir.sequence'].next_by_code('hr.leave') or '/'
        return super().create(vals)

    @api.depends('date_to')
    def _compute_return_date(self):
        """Compute expected return date"""
        for leave in self:
            if leave.date_to:
                # Return date is the day after leave ends
                leave.return_date = leave.date_to.date() + timedelta(days=1)
            else:
                leave.return_date = False

    @api.depends('employee_id', 'holiday_status_id', 'number_of_days')
    def _compute_leave_balance(self):
        """Compute leave balance before and after"""
        for leave in self:
            if leave.employee_id and leave.holiday_status_id:
                # Get current balance
                allocations = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', leave.employee_id.id),
                    ('holiday_status_id', '=', leave.holiday_status_id.id),
                    ('state', '=', 'validate'),
                ])
                total_allocated = sum(allocations.mapped('number_of_days'))
                
                # Get used leaves (excluding current)
                used_leaves = self.search([
                    ('employee_id', '=', leave.employee_id.id),
                    ('holiday_status_id', '=', leave.holiday_status_id.id),
                    ('state', '=', 'validate'),
                    ('id', '!=', leave.id),
                ])
                total_used = sum(used_leaves.mapped('number_of_days'))
                
                leave.leave_balance_before = total_allocated - total_used
                leave.leave_balance_after = leave.leave_balance_before - leave.number_of_days
            else:
                leave.leave_balance_before = 0
                leave.leave_balance_after = 0

    @api.depends('number_of_days', 'salary_impact', 'salary_percentage', 'employee_id')
    def _compute_salary_deduction(self):
        """Compute salary deduction amount"""
        for leave in self:
            deduction = 0.0
            if leave.employee_id and leave.employee_id.contract_id:
                daily_wage = leave.employee_id.contract_id.wage / 30
                
                if leave.salary_impact == 'no_pay':
                    deduction = daily_wage * leave.number_of_days
                elif leave.salary_impact == 'half_pay':
                    deduction = daily_wage * leave.number_of_days * 0.5
                elif leave.salary_impact == 'custom':
                    deduction = daily_wage * leave.number_of_days * (100 - leave.salary_percentage) / 100
            
            leave.salary_deduction = deduction

    @api.depends('holiday_status_id', 'number_of_days')
    def _compute_document_required(self):
        """Check if document is required"""
        for leave in self:
            leave_type = leave.holiday_status_id
            if leave_type:
                if leave_type.requires_document:
                    leave.document_required = True
                elif leave_type.document_required_after_days > 0:
                    leave.document_required = leave.number_of_days > leave_type.document_required_after_days
                else:
                    leave.document_required = False
            else:
                leave.document_required = False

    @api.depends('date_from', 'date_to', 'holiday_status_id')
    def _compute_public_holidays(self):
        """Compute public holidays and weekends within leave period"""
        for leave in self:
            if leave.date_from and leave.date_to:
                date_from = leave.date_from.date() if hasattr(leave.date_from, 'date') else leave.date_from
                date_to = leave.date_to.date() if hasattr(leave.date_to, 'date') else leave.date_to
                
                # Count weekends (Friday, Saturday for UAE)
                weekends = 0
                current = date_from
                while current <= date_to:
                    if current.weekday() in [4, 5]:
                        weekends += 1
                    current += timedelta(days=1)
                
                # Count public holidays
                holidays = self.env['tazweed.public.holiday'].search([
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('state', '=', 'confirmed'),
                ])
                
                leave.weekends_count = weekends
                leave.public_holidays_count = len(holidays)
                
                # Calculate working days
                total_days = (date_to - date_from).days + 1
                if leave.holiday_status_id:
                    if leave.holiday_status_id.exclude_weekends:
                        total_days -= weekends
                    if leave.holiday_status_id.exclude_public_holidays:
                        total_days -= len(holidays)
                
                leave.working_days = max(0, total_days)
            else:
                leave.weekends_count = 0
                leave.public_holidays_count = 0
                leave.working_days = 0

    @api.constrains('date_from', 'date_to', 'holiday_status_id')
    def _check_advance_notice(self):
        """Check advance notice requirement"""
        for leave in self:
            if leave.holiday_status_id and leave.holiday_status_id.advance_notice_days > 0:
                if not leave.is_emergency:
                    notice_date = date.today() + timedelta(days=leave.holiday_status_id.advance_notice_days)
                    if leave.date_from.date() < notice_date:
                        raise ValidationError(_(
                            'This leave type requires %d days advance notice.'
                        ) % leave.holiday_status_id.advance_notice_days)

    @api.constrains('number_of_days', 'holiday_status_id')
    def _check_max_consecutive_days(self):
        """Check maximum consecutive days"""
        for leave in self:
            if leave.holiday_status_id and leave.holiday_status_id.max_consecutive_days > 0:
                if leave.number_of_days > leave.holiday_status_id.max_consecutive_days:
                    raise ValidationError(_(
                        'Maximum consecutive days for this leave type is %d days.'
                    ) % leave.holiday_status_id.max_consecutive_days)

    @api.constrains('document_ids', 'document_required')
    def _check_document_required(self):
        """Check if document is attached when required"""
        for leave in self:
            if leave.document_required and not leave.document_ids and leave.state == 'confirm':
                raise ValidationError(_('Supporting document is required for this leave request.'))

    def action_approve(self):
        """Override approve to track approver"""
        res = super().action_approve()
        for leave in self:
            if not leave.first_approval_date:
                leave.write({
                    'first_approval_date': fields.Datetime.now(),
                    'first_approver_id': self.env.user.id,
                })
            else:
                leave.write({
                    'second_approval_date': fields.Datetime.now(),
                    'second_approver_id': self.env.user.id,
                })
        return res

    def action_refuse(self):
        """Override refuse to track cancellation"""
        res = super().action_refuse()
        for leave in self:
            leave.write({
                'cancelled_by_id': self.env.user.id,
                'cancellation_date': fields.Datetime.now(),
            })
        return res

    @api.model
    def get_leave_dashboard_data(self, date_range='month'):
        """Get dashboard data for leave management"""
        today = date.today()
        
        # Calculate date range
        if date_range == 'week':
            start_date = today - timedelta(days=7)
        elif date_range == 'month':
            start_date = today - timedelta(days=30)
        elif date_range == 'quarter':
            start_date = today - timedelta(days=90)
        else:  # year
            start_date = today - timedelta(days=365)
        
        # Get employees
        employees = self.env['hr.employee'].search([('active', '=', True)])
        total_employees = len(employees)
        
        # Get leaves on today
        on_leave_today = self.search_count([
            ('state', '=', 'validate'),
            ('date_from', '<=', today),
            ('date_to', '>=', today),
        ])
        
        # Get pending requests
        pending_requests = self.search_count([
            ('state', '=', 'confirm'),
        ])
        
        # Get approved this period
        approved_this_period = self.search_count([
            ('state', '=', 'validate'),
            ('date_from', '>=', start_date),
        ])
        
        # Calculate average leave days
        approved_leaves = self.search([
            ('state', '=', 'validate'),
            ('date_from', '>=', start_date),
        ])
        avg_leave_days = round(sum(approved_leaves.mapped('number_of_days')) / max(len(approved_leaves), 1), 1)
        
        # Calculate leave utilization (simplified)
        total_allocated = sum(self.env['hr.leave.allocation'].search([
            ('state', '=', 'validate'),
        ]).mapped('number_of_days'))
        total_used = sum(self.search([
            ('state', '=', 'validate'),
        ]).mapped('number_of_days'))
        leave_utilization = round((total_used / max(total_allocated, 1)) * 100, 1)
        
        # Leave by type
        leave_types = self.env['hr.leave.type'].search([])
        leave_by_type = []
        for lt in leave_types[:8]:  # Top 8 types
            count = self.search_count([
                ('holiday_status_id', '=', lt.id),
                ('state', '=', 'validate'),
                ('date_from', '>=', start_date),
            ])
            if count > 0:
                leave_by_type.append({
                    'name': lt.name,
                    'count': count,
                })
        
        # Leave by department
        departments = self.env['hr.department'].search([], limit=10)
        leave_by_department = []
        for dept in departments:
            dept_employees = employees.filtered(lambda e: e.department_id.id == dept.id)
            dept_leaves = self.search([
                ('employee_id', 'in', dept_employees.ids),
                ('state', '=', 'validate'),
                ('date_from', '>=', start_date),
            ])
            total_days = sum(dept_leaves.mapped('number_of_days'))
            if total_days > 0:
                leave_by_department.append({
                    'name': dept.name,
                    'days': total_days,
                })
        
        # Sort by days descending
        leave_by_department.sort(key=lambda x: x['days'], reverse=True)
        leave_by_department = leave_by_department[:8]
        
        # Recent requests
        recent_requests = []
        recent_leaves = self.search([
            ('create_date', '>=', start_date),
        ], order='create_date desc', limit=10)
        for leave in recent_leaves:
            recent_requests.append({
                'id': leave.id,
                'employee_name': leave.employee_id.name if leave.employee_id else 'Unknown',
                'leave_type': leave.holiday_status_id.name if leave.holiday_status_id else 'Unknown',
                'duration': leave.number_of_days,
                'state': leave.state,
            })
        
        # Upcoming leaves
        upcoming_leaves = []
        upcoming = self.search([
            ('state', '=', 'validate'),
            ('date_from', '>=', today),
        ], order='date_from asc', limit=10)
        for leave in upcoming:
            upcoming_leaves.append({
                'id': leave.id,
                'employee_name': leave.employee_id.name if leave.employee_id else 'Unknown',
                'date_from': str(leave.date_from.date()) if leave.date_from else '',
                'date_to': str(leave.date_to.date()) if leave.date_to else '',
                'duration': leave.number_of_days,
            })
        
        # Alerts
        alerts = []
        if pending_requests > 5:
            alerts.append({
                'type': 'warning',
                'icon': 'fa-exclamation-triangle',
                'message': f'{pending_requests} leave requests pending approval',
            })
        
        return {
            'stats': {
                'totalEmployees': total_employees,
                'onLeaveToday': on_leave_today,
                'pendingRequests': pending_requests,
                'approvedThisMonth': approved_this_period,
                'avgLeaveDays': avg_leave_days,
                'leaveUtilization': leave_utilization,
            },
            'leave_by_type': leave_by_type,
            'leave_by_department': leave_by_department,
            'recent_requests': recent_requests,
            'upcoming_leaves': upcoming_leaves,
            'alerts': alerts,
        }
