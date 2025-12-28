# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    """Leave Configuration Settings"""
    _inherit = 'res.config.settings'

    # Leave Settings
    leave_grace_period = fields.Integer(
        string='Late Grace Period (Minutes)',
        config_parameter='tazweed_leave.grace_period',
        default=5,
    )
    leave_annual_days = fields.Integer(
        string='Annual Leave Days',
        config_parameter='tazweed_leave.annual_days',
        default=30,
    )
    leave_sick_full_pay_days = fields.Integer(
        string='Sick Leave Full Pay Days',
        config_parameter='tazweed_leave.sick_full_pay_days',
        default=15,
    )
    leave_sick_half_pay_days = fields.Integer(
        string='Sick Leave Half Pay Days',
        config_parameter='tazweed_leave.sick_half_pay_days',
        default=30,
    )
    leave_maternity_days = fields.Integer(
        string='Maternity Leave Days',
        config_parameter='tazweed_leave.maternity_days',
        default=60,
    )
    leave_paternity_days = fields.Integer(
        string='Paternity Leave Days',
        config_parameter='tazweed_leave.paternity_days',
        default=5,
    )
    leave_hajj_days = fields.Integer(
        string='Hajj Leave Days',
        config_parameter='tazweed_leave.hajj_days',
        default=30,
    )
    
    # Attendance Settings
    attendance_auto_checkout = fields.Boolean(
        string='Auto Checkout',
        config_parameter='tazweed_leave.auto_checkout',
        default=False,
    )
    attendance_auto_checkout_time = fields.Float(
        string='Auto Checkout Time',
        config_parameter='tazweed_leave.auto_checkout_time',
        default=23.0,
    )
    attendance_require_location = fields.Boolean(
        string='Require Location',
        config_parameter='tazweed_leave.require_location',
        default=False,
    )
    
    # Overtime Settings
    overtime_multiplier_regular = fields.Float(
        string='Regular Overtime Multiplier',
        config_parameter='tazweed_leave.overtime_regular',
        default=1.25,
    )
    overtime_multiplier_weekend = fields.Float(
        string='Weekend Overtime Multiplier',
        config_parameter='tazweed_leave.overtime_weekend',
        default=1.5,
    )
    overtime_multiplier_holiday = fields.Float(
        string='Holiday Overtime Multiplier',
        config_parameter='tazweed_leave.overtime_holiday',
        default=2.0,
    )
    overtime_requires_approval = fields.Boolean(
        string='Overtime Requires Approval',
        config_parameter='tazweed_leave.overtime_approval',
        default=True,
    )
    
    # Weekend Configuration
    weekend_day_1 = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Weekend Day 1', config_parameter='tazweed_leave.weekend_day_1', default='4')
    weekend_day_2 = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Weekend Day 2', config_parameter='tazweed_leave.weekend_day_2', default='5')
