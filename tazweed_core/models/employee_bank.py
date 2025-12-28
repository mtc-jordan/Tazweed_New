# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeeBank(models.Model):
    """Employee Bank Account"""
    _name = 'tazweed.employee.bank'
    _description = 'Employee Bank Account'
    _order = 'is_primary desc, id desc'

    name = fields.Char(string='Account Name', required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
    )
    bank_id = fields.Many2one('res.bank', string='Bank')
    bank_name = fields.Char(string='Bank Name')
    account_number = fields.Char(string='Account Number', required=True)
    iban = fields.Char(string='IBAN')
    swift_code = fields.Char(string='SWIFT Code')
    branch_name = fields.Char(string='Branch Name')
    branch_code = fields.Char(string='Branch Code')
    
    is_primary = fields.Boolean(string='Primary Account', default=False)
    is_salary_account = fields.Boolean(string='Salary Account', default=True)
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    
    active = fields.Boolean(string='Active', default=True)
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.constrains('is_primary', 'employee_id')
    def _check_primary_account(self):
        for record in self:
            if record.is_primary:
                existing = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('is_primary', '=', True),
                    ('id', '!=', record.id),
                ])
                if existing:
                    raise ValidationError(_('Employee can only have one primary bank account.'))

    @api.model
    def create(self, vals):
        """Set as primary if first account"""
        if vals.get('employee_id'):
            existing = self.search_count([('employee_id', '=', vals['employee_id'])])
            if existing == 0:
                vals['is_primary'] = True
        return super().create(vals)
