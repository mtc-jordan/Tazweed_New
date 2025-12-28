# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # UAE-specific contract fields
    contract_type_uae = fields.Selection([
        ('limited', 'Limited'),
        ('unlimited', 'Unlimited'),
        ('part_time', 'Part Time'),
        ('temporary', 'Temporary'),
        ('freelance', 'Freelance'),
    ], string='UAE Contract Type', default='unlimited')
    
    probation_period = fields.Integer(string='Probation Period (Days)', default=90)
    probation_end_date = fields.Date(string='Probation End Date')
    
    # Allowances
    housing_allowance = fields.Monetary(string='Housing Allowance')
    transport_allowance = fields.Monetary(string='Transport Allowance')
    food_allowance = fields.Monetary(string='Food Allowance')
    other_allowance = fields.Monetary(string='Other Allowance')
    
    total_package = fields.Monetary(
        string='Total Package',
        compute='_compute_total_package',
        store=True,
    )
    
    # Leave entitlement
    annual_leave_days = fields.Integer(string='Annual Leave Days', default=30)
    sick_leave_days = fields.Integer(string='Sick Leave Days', default=15)
    
    # End of Service
    gratuity_eligible = fields.Boolean(string='Gratuity Eligible', default=True)
    
    @api.depends('wage', 'housing_allowance', 'transport_allowance', 'food_allowance', 'other_allowance')
    def _compute_total_package(self):
        for contract in self:
            contract.total_package = (
                (contract.wage or 0) +
                (contract.housing_allowance or 0) +
                (contract.transport_allowance or 0) +
                (contract.food_allowance or 0) +
                (contract.other_allowance or 0)
            )
