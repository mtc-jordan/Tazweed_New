# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta, time


class HrAttendance(models.Model):
    """Extended Attendance with UAE-specific features"""
    _inherit = 'hr.attendance'

    # Reference
    reference = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
    )
    
    # Work Schedule
    scheduled_check_in = fields.Datetime(
        string='Scheduled Check In',
        compute='_compute_scheduled_times',
        store=True,
    )
    scheduled_check_out = fields.Datetime(
        string='Scheduled Check Out',
        compute='_compute_scheduled_times',
        store=True,
    )
    scheduled_hours = fields.Float(
        string='Scheduled Hours',
        compute='_compute_scheduled_times',
        store=True,
    )
    
    # Variance
    late_minutes = fields.Integer(
        string='Late (Minutes)',
        compute='_compute_variance',
        store=True,
    )
    early_leave_minutes = fields.Integer(
        string='Early Leave (Minutes)',
        compute='_compute_variance',
        store=True,
    )
    is_late = fields.Boolean(
        string='Is Late',
        compute='_compute_variance',
        store=True,
    )
    is_early_leave = fields.Boolean(
        string='Is Early Leave',
        compute='_compute_variance',
        store=True,
    )
    
    # Overtime
    overtime_hours = fields.Float(
        string='Overtime Hours',
        compute='_compute_overtime',
        store=True,
    )
    overtime_type = fields.Selection([
        ('none', 'None'),
        ('regular', 'Regular Overtime'),
        ('weekend', 'Weekend Overtime'),
        ('holiday', 'Holiday Overtime'),
    ], string='Overtime Type', compute='_compute_overtime', store=True)
    overtime_approved = fields.Boolean(
        string='Overtime Approved',
        default=False,
    )
    overtime_approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
    )
    
    # Location
    check_in_latitude = fields.Float(string='Check In Latitude')
    check_in_longitude = fields.Float(string='Check In Longitude')
    check_out_latitude = fields.Float(string='Check Out Latitude')
    check_out_longitude = fields.Float(string='Check Out Longitude')
    check_in_address = fields.Char(string='Check In Address')
    check_out_address = fields.Char(string='Check Out Address')
    
    # Device
    check_in_device = fields.Char(string='Check In Device')
    check_out_device = fields.Char(string='Check Out Device')
    check_in_method = fields.Selection([
        ('manual', 'Manual'),
        ('biometric', 'Biometric'),
        ('mobile', 'Mobile App'),
        ('web', 'Web Portal'),
        ('kiosk', 'Kiosk'),
    ], string='Check In Method', default='manual')
    check_out_method = fields.Selection([
        ('manual', 'Manual'),
        ('biometric', 'Biometric'),
        ('mobile', 'Mobile App'),
        ('web', 'Web Portal'),
        ('kiosk', 'Kiosk'),
    ], string='Check Out Method', default='manual')
    
    # Status
    attendance_status = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
        ('holiday', 'Holiday'),
        ('weekend', 'Weekend'),
    ], string='Status', compute='_compute_attendance_status', store=True)
    
    # Break
    break_start = fields.Datetime(string='Break Start')
    break_end = fields.Datetime(string='Break End')
    break_duration = fields.Float(
        string='Break Duration',
        compute='_compute_break_duration',
        store=True,
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    manager_notes = fields.Text(string='Manager Notes')
    
    # Approval
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
    ], string='State', default='draft')
    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
    )
    approval_date = fields.Datetime(string='Approval Date')

    @api.model
    def create(self, vals):
        """Generate sequence on create"""
        vals['reference'] = self.env['ir.sequence'].next_by_code('hr.attendance') or '/'
        return super().create(vals)

    @api.depends('employee_id', 'check_in')
    def _compute_scheduled_times(self):
        """Compute scheduled work times from resource calendar"""
        for attendance in self:
            if attendance.employee_id and attendance.check_in:
                # Get employee's work schedule
                calendar = attendance.employee_id.resource_calendar_id
                if calendar:
                    check_in_date = attendance.check_in.date()
                    day_of_week = check_in_date.weekday()
                    
                    # Find work hours for this day
                    work_hours = calendar.attendance_ids.filtered(
                        lambda a: int(a.dayofweek) == day_of_week
                    )
                    
                    if work_hours:
                        # Get first and last work hour
                        start_hour = min(work_hours.mapped('hour_from'))
                        end_hour = max(work_hours.mapped('hour_to'))
                        
                        attendance.scheduled_check_in = datetime.combine(
                            check_in_date,
                            time(int(start_hour), int((start_hour % 1) * 60))
                        )
                        attendance.scheduled_check_out = datetime.combine(
                            check_in_date,
                            time(int(end_hour), int((end_hour % 1) * 60))
                        )
                        attendance.scheduled_hours = end_hour - start_hour
                    else:
                        attendance.scheduled_check_in = False
                        attendance.scheduled_check_out = False
                        attendance.scheduled_hours = 0
                else:
                    attendance.scheduled_check_in = False
                    attendance.scheduled_check_out = False
                    attendance.scheduled_hours = 0
            else:
                attendance.scheduled_check_in = False
                attendance.scheduled_check_out = False
                attendance.scheduled_hours = 0

    @api.depends('check_in', 'check_out', 'scheduled_check_in', 'scheduled_check_out')
    def _compute_variance(self):
        """Compute late arrival and early leave"""
        for attendance in self:
            attendance.late_minutes = 0
            attendance.early_leave_minutes = 0
            attendance.is_late = False
            attendance.is_early_leave = False
            
            if attendance.check_in and attendance.scheduled_check_in:
                # Calculate late minutes
                if attendance.check_in > attendance.scheduled_check_in:
                    diff = attendance.check_in - attendance.scheduled_check_in
                    attendance.late_minutes = int(diff.total_seconds() / 60)
                    attendance.is_late = attendance.late_minutes > 5  # 5 min grace period
            
            if attendance.check_out and attendance.scheduled_check_out:
                # Calculate early leave minutes
                if attendance.check_out < attendance.scheduled_check_out:
                    diff = attendance.scheduled_check_out - attendance.check_out
                    attendance.early_leave_minutes = int(diff.total_seconds() / 60)
                    attendance.is_early_leave = attendance.early_leave_minutes > 5

    @api.depends('check_in', 'check_out', 'scheduled_hours', 'worked_hours')
    def _compute_overtime(self):
        """Compute overtime hours"""
        for attendance in self:
            attendance.overtime_hours = 0
            attendance.overtime_type = 'none'
            
            if attendance.worked_hours and attendance.scheduled_hours:
                if attendance.worked_hours > attendance.scheduled_hours:
                    attendance.overtime_hours = attendance.worked_hours - attendance.scheduled_hours
                    
                    # Determine overtime type
                    if attendance.check_in:
                        day_of_week = attendance.check_in.weekday()
                        
                        # Check if it's a public holiday
                        holiday = self.env['tazweed.public.holiday'].search([
                            ('date', '=', attendance.check_in.date()),
                            ('state', '=', 'confirmed'),
                        ], limit=1)
                        
                        if holiday:
                            attendance.overtime_type = 'holiday'
                        elif day_of_week in [4, 5]:  # Friday, Saturday (UAE weekend)
                            attendance.overtime_type = 'weekend'
                        else:
                            attendance.overtime_type = 'regular'

    @api.depends('worked_hours', 'scheduled_hours')
    def _compute_attendance_status(self):
        """Compute attendance status"""
        for attendance in self:
            if not attendance.check_in:
                attendance.attendance_status = 'absent'
            elif attendance.worked_hours >= attendance.scheduled_hours * 0.9:
                attendance.attendance_status = 'present'
            elif attendance.worked_hours >= attendance.scheduled_hours * 0.5:
                attendance.attendance_status = 'half_day'
            else:
                attendance.attendance_status = 'absent'

    @api.depends('break_start', 'break_end')
    def _compute_break_duration(self):
        """Compute break duration"""
        for attendance in self:
            if attendance.break_start and attendance.break_end:
                diff = attendance.break_end - attendance.break_start
                attendance.break_duration = diff.total_seconds() / 3600
            else:
                attendance.break_duration = 0

    def action_approve_overtime(self):
        """Approve overtime"""
        for attendance in self:
            attendance.write({
                'overtime_approved': True,
                'overtime_approved_by_id': self.env.user.id,
            })

    def action_confirm(self):
        """Confirm attendance"""
        self.write({'state': 'confirmed'})

    def action_approve(self):
        """Approve attendance"""
        self.write({
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })


class HrAttendanceSummary(models.Model):
    """Monthly Attendance Summary"""
    _name = 'hr.attendance.summary'
    _description = 'Monthly Attendance Summary'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True)
    year = fields.Integer(string='Year', required=True)
    
    # Days
    working_days = fields.Integer(string='Working Days')
    present_days = fields.Integer(string='Present Days')
    absent_days = fields.Integer(string='Absent Days')
    half_days = fields.Integer(string='Half Days')
    leave_days = fields.Integer(string='Leave Days')
    holiday_days = fields.Integer(string='Holiday Days')
    weekend_days = fields.Integer(string='Weekend Days')
    
    # Hours
    scheduled_hours = fields.Float(string='Scheduled Hours')
    worked_hours = fields.Float(string='Worked Hours')
    overtime_hours = fields.Float(string='Overtime Hours')
    
    # Late/Early
    late_count = fields.Integer(string='Late Count')
    early_leave_count = fields.Integer(string='Early Leave Count')
    total_late_minutes = fields.Integer(string='Total Late Minutes')
    total_early_leave_minutes = fields.Integer(string='Total Early Leave Minutes')
    
    # Computed
    attendance_percentage = fields.Float(
        string='Attendance %',
        compute='_compute_attendance_percentage',
        store=True,
    )

    @api.depends('working_days', 'present_days', 'half_days')
    def _compute_attendance_percentage(self):
        """Compute attendance percentage"""
        for summary in self:
            if summary.working_days > 0:
                effective_days = summary.present_days + (summary.half_days * 0.5)
                summary.attendance_percentage = (effective_days / summary.working_days) * 100
            else:
                summary.attendance_percentage = 0
