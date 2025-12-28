# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


class HrSalaryRule(models.Model):
    """Salary Rule - Standalone Model"""
    _name = 'hr.salary.rule'
    _description = 'Salary Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', required=True, default=100)
    active = fields.Boolean(string='Active', default=True)
    
    # Structure
    struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Salary Structure',
        required=True,
    )
    
    # Category
    category_id = fields.Many2one(
        'hr.salary.rule.category',
        string='Category',
        required=True,
    )
    
    # Condition
    condition_select = fields.Selection([
        ('none', 'Always True'),
        ('range', 'Range'),
        ('python', 'Python Expression'),
    ], string='Condition Based on', default='none', required=True)
    
    condition_range = fields.Char(
        string='Range Based on',
        default='contract.wage',
    )
    condition_range_min = fields.Float(
        string='Minimum Range',
        default=0.0,
    )
    condition_range_max = fields.Float(
        string='Maximum Range',
        default=0.0,
    )
    condition_python = fields.Text(
        string='Python Condition',
        default='result = True',
    )
    
    # Computation
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ], string='Amount Type', default='fix', required=True)
    
    amount_fix = fields.Float(string='Fixed Amount')
    amount_percentage = fields.Float(string='Percentage (%)')
    amount_percentage_base = fields.Char(string='Percentage Based on')
    amount_python_compute = fields.Text(
        string='Python Code',
        default='result = 0',
    )
    
    # Quantity
    quantity = fields.Char(string='Quantity', default='1.0')
    
    # Partner for contributions
    partner_id = fields.Many2one('res.partner', string='Partner')
    
    # Appearance
    appears_on_payslip = fields.Boolean(string='Appears on Payslip', default=True)
    
    # UAE Specific
    is_uae_rule = fields.Boolean(string='UAE Rule', default=True)
    wps_include = fields.Boolean(string='Include in WPS', default=True)
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
    
    gratuity_include = fields.Boolean(string='Include in Gratuity', default=False)
    
    note = fields.Html(string='Description')

    _sql_constraints = [
        ('code_struct_uniq', 'unique(code, struct_id)', 'Rule code must be unique per structure!'),
    ]

    @api.constrains('condition_python', 'amount_python_compute')
    def _check_python_code(self):
        """Validate Python code syntax"""
        for rule in self:
            if rule.condition_select == 'python' and rule.condition_python:
                try:
                    compile(rule.condition_python, '<string>', 'exec')
                except SyntaxError as e:
                    raise ValidationError(_('Invalid Python code in condition: %s') % str(e))
            
            if rule.amount_select == 'code' and rule.amount_python_compute:
                try:
                    compile(rule.amount_python_compute, '<string>', 'exec')
                except SyntaxError as e:
                    raise ValidationError(_('Invalid Python code in computation: %s') % str(e))

    def _compute_rule(self, localdict):
        """Compute the rule amount. Returns: (amount, qty, rate)"""
        self.ensure_one()
        
        if not self._satisfy_condition(localdict):
            return (0.0, 0.0, 0.0)
        
        if self.amount_select == 'fix':
            amount = self.amount_fix
            qty = 1.0
            rate = 100.0
        elif self.amount_select == 'percentage':
            try:
                base = safe_eval(self.amount_percentage_base or '0', localdict)
            except Exception:
                base = 0.0
            amount = base * self.amount_percentage / 100
            qty = 1.0
            rate = 100.0
        else:  # code
            try:
                localdict['result'] = 0.0
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100.0
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                amount = localdict.get('result', 0.0)
                qty = localdict.get('result_qty', 1.0)
                rate = localdict.get('result_rate', 100.0)
            except Exception as e:
                raise ValidationError(_('Error computing rule %s: %s') % (self.name, str(e)))
        
        try:
            qty = safe_eval(self.quantity or '1.0', localdict)
        except Exception:
            qty = 1.0
        
        return (amount, qty, rate)

    def _satisfy_condition(self, localdict):
        """Check if rule condition is satisfied"""
        self.ensure_one()
        
        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = safe_eval(self.condition_range or '0', localdict)
                return self.condition_range_min <= result <= self.condition_range_max
            except Exception:
                return False
        else:  # python
            try:
                localdict['result'] = False
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return localdict.get('result', False)
            except Exception:
                return False
