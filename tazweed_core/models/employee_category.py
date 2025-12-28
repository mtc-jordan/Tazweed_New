# -*- coding: utf-8 -*-
from odoo import models, fields, api


class EmployeeCategory(models.Model):
    """Employee Category for classification"""
    _name = 'tazweed.employee.category'
    _description = 'Employee Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Category name must be unique!'),
    ]
