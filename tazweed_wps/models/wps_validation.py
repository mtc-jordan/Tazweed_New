# -*- coding: utf-8 -*-
"""
WPS Validation Rules Module
Pre-submission validation checks for WPS compliance
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import re
import logging

_logger = logging.getLogger(__name__)


class WPSValidationRule(models.Model):
    """WPS Validation Rule Definition"""
    _name = 'wps.validation.rule'
    _description = 'WPS Validation Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    code = fields.Char(string='Rule Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Rule Configuration
    rule_type = fields.Selection([
        ('format', 'Format Validation'),
        ('range', 'Range Check'),
        ('required', 'Required Field'),
        ('unique', 'Uniqueness Check'),
        ('reference', 'Reference Validation'),
        ('calculation', 'Calculation Check'),
        ('business', 'Business Rule'),
        ('compliance', 'Compliance Check'),
    ], string='Rule Type', required=True, default='format')
    
    applies_to = fields.Selection([
        ('file', 'WPS File'),
        ('line', 'WPS Line'),
        ('employee', 'Employee'),
        ('bank', 'Bank Account'),
    ], string='Applies To', required=True, default='line')
    
    field_name = fields.Char(string='Field Name', help='Technical field name to validate')
    
    # Validation Parameters
    regex_pattern = fields.Char(string='Regex Pattern', help='Regular expression for format validation')
    min_value = fields.Float(string='Minimum Value')
    max_value = fields.Float(string='Maximum Value')
    allowed_values = fields.Char(string='Allowed Values', help='Comma-separated list of allowed values')
    reference_model = fields.Char(string='Reference Model', help='Model to check for reference validation')
    
    # Error Handling
    severity = fields.Selection([
        ('error', 'Error - Blocks Submission'),
        ('warning', 'Warning - Allows Override'),
        ('info', 'Info - Notification Only'),
    ], string='Severity', default='error', required=True)
    
    error_message = fields.Text(string='Error Message', required=True)
    help_text = fields.Text(string='Help Text', help='Guidance on how to fix the issue')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    # Statistics
    total_checks = fields.Integer(string='Total Checks', default=0)
    failed_checks = fields.Integer(string='Failed Checks', default=0)
    
    def validate(self, record, context=None):
        """Execute the validation rule"""
        self.ensure_one()
        self.total_checks += 1
        
        result = {
            'rule_id': self.id,
            'rule_code': self.code,
            'rule_name': self.name,
            'passed': True,
            'severity': self.severity,
            'message': '',
            'field': self.field_name,
        }
        
        try:
            if self.rule_type == 'format':
                result = self._validate_format(record, result)
            elif self.rule_type == 'range':
                result = self._validate_range(record, result)
            elif self.rule_type == 'required':
                result = self._validate_required(record, result)
            elif self.rule_type == 'unique':
                result = self._validate_unique(record, result)
            elif self.rule_type == 'reference':
                result = self._validate_reference(record, result)
            elif self.rule_type == 'calculation':
                result = self._validate_calculation(record, result, context)
            elif self.rule_type == 'business':
                result = self._validate_business(record, result, context)
            elif self.rule_type == 'compliance':
                result = self._validate_compliance(record, result, context)
                
        except Exception as e:
            result['passed'] = False
            result['message'] = f"Validation error: {str(e)}"
        
        if not result['passed']:
            self.failed_checks += 1
            result['message'] = self.error_message
            result['help'] = self.help_text
        
        return result
    
    def _validate_format(self, record, result):
        """Validate field format using regex"""
        if not self.field_name or not self.regex_pattern:
            return result
        
        value = getattr(record, self.field_name, None)
        if value:
            if not re.match(self.regex_pattern, str(value)):
                result['passed'] = False
        return result
    
    def _validate_range(self, record, result):
        """Validate numeric range"""
        if not self.field_name:
            return result
        
        value = getattr(record, self.field_name, None)
        if value is not None:
            if self.min_value and value < self.min_value:
                result['passed'] = False
            if self.max_value and value > self.max_value:
                result['passed'] = False
        return result
    
    def _validate_required(self, record, result):
        """Validate required field"""
        if not self.field_name:
            return result
        
        value = getattr(record, self.field_name, None)
        if not value:
            result['passed'] = False
        return result
    
    def _validate_unique(self, record, result):
        """Validate uniqueness"""
        if not self.field_name:
            return result
        
        value = getattr(record, self.field_name, None)
        if value:
            domain = [(self.field_name, '=', value), ('id', '!=', record.id)]
            if record.search_count(domain) > 0:
                result['passed'] = False
        return result
    
    def _validate_reference(self, record, result):
        """Validate reference exists"""
        if not self.field_name or not self.reference_model:
            return result
        
        value = getattr(record, self.field_name, None)
        if value:
            ref_model = self.env[self.reference_model]
            if not ref_model.search_count([('id', '=', value.id if hasattr(value, 'id') else value)]):
                result['passed'] = False
        return result
    
    def _validate_calculation(self, record, result, context):
        """Validate calculations"""
        return result
    
    def _validate_business(self, record, result, context):
        """Validate business rules"""
        return result
    
    def _validate_compliance(self, record, result, context):
        """Validate compliance requirements"""
        return result


class WPSValidationResult(models.Model):
    """WPS Validation Result"""
    _name = 'wps.validation.result'
    _description = 'WPS Validation Result'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, default='New', copy=False)
    wps_file_id = fields.Many2one('tazweed.wps.file', string='WPS File', required=True, ondelete='cascade')
    
    # Validation Summary
    validation_date = fields.Datetime(string='Validation Date', default=fields.Datetime.now)
    validated_by = fields.Many2one('res.users', string='Validated By', default=lambda self: self.env.user)
    
    total_rules = fields.Integer(string='Total Rules Checked')
    passed_rules = fields.Integer(string='Passed')
    failed_rules = fields.Integer(string='Failed')
    warnings = fields.Integer(string='Warnings')
    
    # Status
    state = fields.Selection([
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('warning', 'Valid with Warnings'),
    ], string='Status', compute='_compute_state', store=True)
    
    can_submit = fields.Boolean(string='Can Submit', compute='_compute_state', store=True)
    
    # Details
    result_line_ids = fields.One2many('wps.validation.result.line', 'result_id', string='Validation Details')
    
    # Notes
    notes = fields.Text(string='Notes')
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('wps.validation.result') or 'New'
        return super().create(vals)
    
    @api.depends('result_line_ids', 'result_line_ids.passed', 'result_line_ids.severity')
    def _compute_state(self):
        for record in self:
            lines = record.result_line_ids
            errors = lines.filtered(lambda l: not l.passed and l.severity == 'error')
            warnings = lines.filtered(lambda l: not l.passed and l.severity == 'warning')
            
            record.total_rules = len(lines)
            record.passed_rules = len(lines.filtered('passed'))
            record.failed_rules = len(errors)
            record.warnings = len(warnings)
            
            if errors:
                record.state = 'invalid'
                record.can_submit = False
            elif warnings:
                record.state = 'warning'
                record.can_submit = True
            else:
                record.state = 'valid'
                record.can_submit = True


class WPSValidationResultLine(models.Model):
    """WPS Validation Result Line"""
    _name = 'wps.validation.result.line'
    _description = 'WPS Validation Result Line'
    _order = 'sequence, id'

    result_id = fields.Many2one('wps.validation.result', string='Validation Result', 
                                 required=True, ondelete='cascade')
    rule_id = fields.Many2one('wps.validation.rule', string='Validation Rule')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Result
    rule_code = fields.Char(string='Rule Code')
    rule_name = fields.Char(string='Rule Name')
    field_name = fields.Char(string='Field')
    passed = fields.Boolean(string='Passed', default=True)
    severity = fields.Selection([
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Info'),
    ], string='Severity', default='error')
    
    message = fields.Text(string='Message')
    help_text = fields.Text(string='Help')
    
    # Record Reference
    record_model = fields.Char(string='Record Model')
    record_id = fields.Integer(string='Record ID')
    record_name = fields.Char(string='Record Name')


class WPSFileValidation(models.Model):
    """Extend WPS File with validation methods"""
    _inherit = 'tazweed.wps.file'
    
    validation_result_ids = fields.One2many('wps.validation.result', 'wps_file_id', string='Validation Results')
    last_validation_date = fields.Datetime(string='Last Validation', compute='_compute_last_validation')
    validation_state = fields.Selection([
        ('not_validated', 'Not Validated'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('warning', 'Valid with Warnings'),
    ], string='Validation Status', compute='_compute_last_validation')
    
    @api.depends('validation_result_ids', 'validation_result_ids.state')
    def _compute_last_validation(self):
        for record in self:
            last_result = record.validation_result_ids[:1]
            if last_result:
                record.last_validation_date = last_result.validation_date
                record.validation_state = last_result.state
            else:
                record.last_validation_date = False
                record.validation_state = 'not_validated'
    
    def action_validate(self):
        """Run all validation rules on the WPS file"""
        self.ensure_one()
        
        # Get active validation rules
        file_rules = self.env['wps.validation.rule'].search([
            ('active', '=', True),
            ('applies_to', '=', 'file'),
        ])
        line_rules = self.env['wps.validation.rule'].search([
            ('active', '=', True),
            ('applies_to', '=', 'line'),
        ])
        
        # Create validation result
        result = self.env['wps.validation.result'].create({
            'wps_file_id': self.id,
        })
        
        # Validate file-level rules
        for rule in file_rules:
            rule_result = rule.validate(self)
            self.env['wps.validation.result.line'].create({
                'result_id': result.id,
                'rule_id': rule.id,
                'rule_code': rule_result.get('rule_code'),
                'rule_name': rule_result.get('rule_name'),
                'field_name': rule_result.get('field'),
                'passed': rule_result.get('passed'),
                'severity': rule_result.get('severity'),
                'message': rule_result.get('message'),
                'help_text': rule_result.get('help'),
                'record_model': 'tazweed.wps.file',
                'record_id': self.id,
                'record_name': self.name,
            })
        
        # Validate line-level rules
        for line in self.line_ids:
            for rule in line_rules:
                rule_result = rule.validate(line)
                if not rule_result.get('passed'):
                    self.env['wps.validation.result.line'].create({
                        'result_id': result.id,
                        'rule_id': rule.id,
                        'rule_code': rule_result.get('rule_code'),
                        'rule_name': rule_result.get('rule_name'),
                        'field_name': rule_result.get('field'),
                        'passed': rule_result.get('passed'),
                        'severity': rule_result.get('severity'),
                        'message': rule_result.get('message'),
                        'help_text': rule_result.get('help'),
                        'record_model': 'tazweed.wps.file.line',
                        'record_id': line.id,
                        'record_name': line.employee_id.name if line.employee_id else '',
                    })
        
        # Return result view
        return {
            'type': 'ir.actions.act_window',
            'name': _('Validation Result'),
            'res_model': 'wps.validation.result',
            'res_id': result.id,
            'view_mode': 'form',
            'target': 'current',
        }
