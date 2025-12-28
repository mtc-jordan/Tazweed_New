# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrPayrollStructureType(models.Model):
    """Payroll Structure Type - Enterprise Feature"""
    _name = 'hr.payroll.structure.type'
    _description = 'Payroll Structure Type'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env.ref('base.ae', raise_if_not_found=False),
    )
    
    default_struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Default Structure',
    )
    default_resource_calendar_id = fields.Many2one(
        'resource.calendar',
        string='Default Working Hours',
    )
    
    wage_type = fields.Selection([
        ('monthly', 'Monthly Fixed Wage'),
        ('hourly', 'Hourly Wage'),
        ('daily', 'Daily Wage'),
    ], string='Wage Type', default='monthly', required=True)
    
    struct_ids = fields.One2many(
        'hr.payroll.structure',
        'type_id',
        string='Structures',
    )
    
    # UAE Specific
    is_uae_structure = fields.Boolean(
        string='UAE Structure',
        default=True,
    )
    include_gratuity = fields.Boolean(
        string='Include Gratuity',
        default=True,
    )
    wps_enabled = fields.Boolean(
        string='WPS Enabled',
        default=True,
    )
    
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Structure type code must be unique!'),
    ]


class HrPayrollStructure(models.Model):
    """Payroll Structure - Standalone Model"""
    _name = 'hr.payroll.structure'
    _description = 'Payroll Structure'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    type_id = fields.Many2one(
        'hr.payroll.structure.type',
        string='Structure Type',
    )
    
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env.ref('base.ae', raise_if_not_found=False),
    )
    
    # Parent Structure
    parent_id = fields.Many2one(
        'hr.payroll.structure',
        string='Parent Structure',
    )
    children_ids = fields.One2many(
        'hr.payroll.structure',
        'parent_id',
        string='Child Structures',
    )
    
    # Salary Rules
    rule_ids = fields.One2many(
        'hr.salary.rule',
        'struct_id',
        string='Salary Rules',
    )
    
    # Schedule Pay
    schedule_pay = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annually', 'Semi-annually'),
        ('annually', 'Annually'),
        ('weekly', 'Weekly'),
        ('bi-weekly', 'Bi-weekly'),
        ('bi-monthly', 'Bi-monthly'),
    ], string='Scheduled Pay', default='monthly', required=True)
    
    # Input Line Types
    input_line_type_ids = fields.Many2many(
        'hr.payslip.input.type',
        'hr_structure_input_type_rel',
        'structure_id',
        'input_type_id',
        string='Other Input Types',
    )
    
    # UAE Specific
    is_uae_structure = fields.Boolean(
        string='UAE Structure',
        default=True,
    )
    include_housing = fields.Boolean(
        string='Include Housing Allowance',
        default=True,
    )
    include_transport = fields.Boolean(
        string='Include Transport Allowance',
        default=True,
    )
    include_overtime = fields.Boolean(
        string='Include Overtime',
        default=True,
    )
    include_gratuity = fields.Boolean(
        string='Include Gratuity Provision',
        default=True,
    )
    
    use_worked_day_lines = fields.Boolean(
        string='Use Worked Day Lines',
        default=True,
    )
    
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'Structure code must be unique per company!'),
    ]

    def get_all_rules(self):
        """Get all rules including parent rules"""
        self.ensure_one()
        rules = self.rule_ids
        if self.parent_id:
            rules |= self.parent_id.get_all_rules()
        return rules


class HrSalaryRuleCategory(models.Model):
    """Salary Rule Category"""
    _name = 'hr.salary.rule.category'
    _description = 'Salary Rule Category'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    parent_id = fields.Many2one(
        'hr.salary.rule.category',
        string='Parent Category',
    )
    children_ids = fields.One2many(
        'hr.salary.rule.category',
        'parent_id',
        string='Child Categories',
    )
    
    notes = fields.Text(string='Notes')
    
    # Category Type
    category_type = fields.Selection([
        ('basic', 'Basic'),
        ('allowance', 'Allowance'),
        ('deduction', 'Deduction'),
        ('gross', 'Gross'),
        ('net', 'Net'),
        ('contribution', 'Contribution'),
        ('other', 'Other'),
    ], string='Category Type', default='other')
    
    # WPS Category
    wps_category = fields.Selection([
        ('basic', 'Basic Salary'),
        ('housing', 'Housing Allowance'),
        ('transport', 'Transport Allowance'),
        ('other_allowance', 'Other Allowance'),
        ('deduction', 'Deduction'),
        ('leave', 'Leave Salary'),
        ('overtime', 'Overtime'),
        ('commission', 'Commission'),
        ('other', 'Other'),
    ], string='WPS Category', default='other')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Category code must be unique!'),
    ]


class HrPayslipInputType(models.Model):
    """Payslip Input Types"""
    _name = 'hr.payslip.input.type'
    _description = 'Payslip Input Type'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env.ref('base.ae', raise_if_not_found=False),
    )
    
    struct_ids = fields.Many2many(
        'hr.payroll.structure',
        'hr_structure_input_type_rel',
        'input_type_id',
        'structure_id',
        string='Structures',
    )
    
    # Input Configuration
    input_type = fields.Selection([
        ('amount', 'Fixed Amount'),
        ('percentage', 'Percentage'),
        ('quantity', 'Quantity'),
    ], string='Input Type', default='amount', required=True)
    
    is_deduction = fields.Boolean(
        string='Is Deduction',
        default=False,
    )
    
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Input type code must be unique!'),
    ]
