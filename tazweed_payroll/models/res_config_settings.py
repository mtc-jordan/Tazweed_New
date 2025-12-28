# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    """Payroll Configuration Settings"""
    _inherit = 'res.config.settings'

    # WPS Settings
    wps_employer_eid = fields.Char(
        string='Employer Emirates ID',
        config_parameter='tazweed_payroll.wps_employer_eid',
    )
    wps_employer_bank_code = fields.Char(
        string='Employer Bank Code',
        config_parameter='tazweed_payroll.wps_employer_bank_code',
    )
    wps_employer_account = fields.Char(
        string='Employer Bank Account',
        config_parameter='tazweed_payroll.wps_employer_account',
    )
    wps_auto_generate = fields.Boolean(
        string='Auto Generate WPS',
        config_parameter='tazweed_payroll.wps_auto_generate',
        default=False,
    )
    
    # Gratuity Settings
    gratuity_calculation_method = fields.Selection([
        ('basic_only', 'Basic Salary Only'),
        ('basic_housing', 'Basic + Housing'),
        ('basic_housing_transport', 'Basic + Housing + Transport'),
        ('total_salary', 'Total Salary'),
    ], string='Gratuity Calculation Base',
       config_parameter='tazweed_payroll.gratuity_calculation_method',
       default='basic_only',
    )
    gratuity_max_years = fields.Integer(
        string='Maximum Gratuity Years',
        config_parameter='tazweed_payroll.gratuity_max_years',
        default=0,
        help='Maximum years for gratuity calculation (0 = no limit)',
    )
    
    # Overtime Settings
    overtime_rate_normal = fields.Float(
        string='Normal Overtime Rate',
        config_parameter='tazweed_payroll.overtime_rate_normal',
        default=1.25,
        help='Multiplier for normal overtime (e.g., 1.25 = 125%)',
    )
    overtime_rate_weekend = fields.Float(
        string='Weekend Overtime Rate',
        config_parameter='tazweed_payroll.overtime_rate_weekend',
        default=1.5,
        help='Multiplier for weekend overtime (e.g., 1.5 = 150%)',
    )
    overtime_rate_holiday = fields.Float(
        string='Holiday Overtime Rate',
        config_parameter='tazweed_payroll.overtime_rate_holiday',
        default=2.0,
        help='Multiplier for holiday overtime (e.g., 2.0 = 200%)',
    )
    
    # Loan Settings
    loan_max_amount = fields.Float(
        string='Maximum Loan Amount',
        config_parameter='tazweed_payroll.loan_max_amount',
        default=50000.0,
    )
    loan_max_installments = fields.Integer(
        string='Maximum Installments',
        config_parameter='tazweed_payroll.loan_max_installments',
        default=24,
    )
    loan_max_deduction_percentage = fields.Float(
        string='Max Deduction % of Salary',
        config_parameter='tazweed_payroll.loan_max_deduction_percentage',
        default=50.0,
        help='Maximum percentage of salary that can be deducted for loans',
    )
    
    # Payslip Settings
    payslip_auto_compute = fields.Boolean(
        string='Auto Compute Payslips',
        config_parameter='tazweed_payroll.payslip_auto_compute',
        default=True,
    )
    payslip_include_leave = fields.Boolean(
        string='Include Leave in Payslip',
        config_parameter='tazweed_payroll.payslip_include_leave',
        default=True,
    )
    payslip_include_attendance = fields.Boolean(
        string='Include Attendance in Payslip',
        config_parameter='tazweed_payroll.payslip_include_attendance',
        default=True,
    )
    
    # Default Structure
    default_structure_id = fields.Many2one(
        'hr.payroll.structure',
        string='Default Salary Structure',
        config_parameter='tazweed_payroll.default_structure_id',
    )
    
    # Currency
    payroll_currency_id = fields.Many2one(
        'res.currency',
        string='Payroll Currency',
        config_parameter='tazweed_payroll.payroll_currency_id',
        default=lambda self: self.env.ref('base.AED', raise_if_not_found=False),
    )
