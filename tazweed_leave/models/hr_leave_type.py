# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrLeaveType(models.Model):
    """Extended Leave Type with UAE-specific features"""
    _inherit = 'hr.leave.type'

    # UAE Leave Type
    uae_leave_type = fields.Selection([
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('hajj', 'Hajj Leave'),
        ('bereavement', 'Bereavement Leave'),
        ('study', 'Study Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('compassionate', 'Compassionate Leave'),
        ('emergency', 'Emergency Leave'),
        ('other', 'Other'),
    ], string='UAE Leave Type', default='other')
    
    # Entitlement Rules
    is_uae_statutory = fields.Boolean(
        string='UAE Statutory Leave',
        default=False,
        help='This leave type is mandated by UAE Labour Law',
    )
    min_service_months = fields.Integer(
        string='Minimum Service (Months)',
        default=0,
        help='Minimum months of service required to be eligible',
    )
    max_days_per_year = fields.Float(
        string='Maximum Days/Year',
        default=0,
        help='Maximum days allowed per year (0 = unlimited)',
    )
    
    # Carry Forward
    allow_carry_forward = fields.Boolean(
        string='Allow Carry Forward',
        default=False,
    )
    max_carry_forward_days = fields.Float(
        string='Max Carry Forward Days',
        default=0,
    )
    carry_forward_expiry_months = fields.Integer(
        string='Carry Forward Expiry (Months)',
        default=0,
        help='Number of months after which carried forward leave expires (0 = never)',
    )
    
    # Encashment
    allow_encashment = fields.Boolean(
        string='Allow Encashment',
        default=False,
    )
    encashment_rate = fields.Float(
        string='Encashment Rate',
        default=1.0,
        help='Rate for encashment calculation (1.0 = 100% of daily wage)',
    )
    min_balance_for_encashment = fields.Float(
        string='Min Balance for Encashment',
        default=0,
        help='Minimum leave balance required to request encashment',
    )
    
    # Accrual
    is_accrual = fields.Boolean(
        string='Accrual Based',
        default=False,
    )
    accrual_rate = fields.Float(
        string='Accrual Rate (Days/Month)',
        default=0,
    )
    accrual_start_after_months = fields.Integer(
        string='Accrual Starts After (Months)',
        default=0,
    )
    
    # Approval
    requires_document = fields.Boolean(
        string='Requires Document',
        default=False,
        help='Document attachment is required for this leave type',
    )
    document_required_after_days = fields.Integer(
        string='Document Required After (Days)',
        default=0,
        help='Document required if leave is more than these days',
    )
    max_consecutive_days = fields.Integer(
        string='Max Consecutive Days',
        default=0,
        help='Maximum consecutive days allowed (0 = unlimited)',
    )
    
    # Salary Impact
    salary_impact = fields.Selection([
        ('full_pay', 'Full Pay'),
        ('half_pay', 'Half Pay'),
        ('no_pay', 'No Pay'),
        ('custom', 'Custom'),
    ], string='Salary Impact', default='full_pay')
    salary_percentage = fields.Float(
        string='Salary Percentage',
        default=100.0,
        help='Percentage of salary to pay during this leave',
    )
    
    # Sick Leave Specific (UAE Law)
    sick_leave_full_pay_days = fields.Integer(
        string='Full Pay Days',
        default=15,
        help='Number of days with full pay (UAE: 15 days)',
    )
    sick_leave_half_pay_days = fields.Integer(
        string='Half Pay Days',
        default=30,
        help='Number of days with half pay (UAE: 30 days)',
    )
    sick_leave_no_pay_days = fields.Integer(
        string='No Pay Days',
        default=45,
        help='Number of days with no pay (UAE: 45 days)',
    )
    
    # Gender Restriction
    gender_restriction = fields.Selection([
        ('all', 'All'),
        ('male', 'Male Only'),
        ('female', 'Female Only'),
    ], string='Gender Restriction', default='all')
    
    # Probation
    allowed_during_probation = fields.Boolean(
        string='Allowed During Probation',
        default=False,
    )
    
    # Public Holidays
    exclude_public_holidays = fields.Boolean(
        string='Exclude Public Holidays',
        default=True,
        help='Public holidays within leave period are not counted',
    )
    exclude_weekends = fields.Boolean(
        string='Exclude Weekends',
        default=True,
        help='Weekends within leave period are not counted',
    )
    
    # Notification
    notify_manager = fields.Boolean(
        string='Notify Manager',
        default=True,
    )
    notify_hr = fields.Boolean(
        string='Notify HR',
        default=True,
    )
    advance_notice_days = fields.Integer(
        string='Advance Notice (Days)',
        default=0,
        help='Minimum days in advance to request this leave',
    )

    @api.constrains('salary_percentage')
    def _check_salary_percentage(self):
        """Validate salary percentage"""
        for leave_type in self:
            if leave_type.salary_percentage < 0 or leave_type.salary_percentage > 100:
                raise ValidationError(_('Salary percentage must be between 0 and 100.'))

    def get_leave_days_for_employee(self, employee_id, date_from, date_to):
        """Calculate leave days considering exclusions"""
        self.ensure_one()
        
        total_days = (date_to - date_from).days + 1
        
        if self.exclude_weekends:
            # Count weekends
            weekends = 0
            current = date_from
            while current <= date_to:
                if current.weekday() in [4, 5]:  # Friday, Saturday (UAE weekend)
                    weekends += 1
                current += timedelta(days=1)
            total_days -= weekends
        
        if self.exclude_public_holidays:
            # Count public holidays
            holidays = self.env['tazweed.public.holiday'].search([
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('state', '=', 'confirmed'),
            ])
            total_days -= len(holidays)
        
        return max(0, total_days)
