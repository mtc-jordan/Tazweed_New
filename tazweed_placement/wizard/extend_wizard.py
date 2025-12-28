# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class ExtendWizard(models.TransientModel):
    """Wizard to extend placement contract"""
    _name = 'tazweed.extend.wizard'
    _description = 'Extend Contract'

    placement_id = fields.Many2one('tazweed.placement', string='Placement', required=True)
    
    # Current Info
    current_end_date = fields.Date(related='placement_id.date_end', string='Current End Date')
    current_salary = fields.Float(related='placement_id.salary', string='Current Salary')
    current_bill_rate = fields.Float(related='placement_id.bill_rate', string='Current Bill Rate')
    
    # Extension Details
    extension_type = fields.Selection([
        ('months', 'Months'),
        ('date', 'Specific Date'),
    ], string='Extension Type', default='months', required=True)
    
    extension_months = fields.Integer(string='Extension (Months)', default=3)
    new_end_date = fields.Date(string='New End Date')
    
    # Rate Changes
    new_salary = fields.Float(string='New Salary')
    new_bill_rate = fields.Float(string='New Bill Rate')
    
    notes = fields.Text(string='Notes')

    @api.onchange('extension_type', 'extension_months', 'placement_id')
    def _onchange_extension(self):
        if self.extension_type == 'months' and self.placement_id.date_end:
            self.new_end_date = self.placement_id.date_end + relativedelta(months=self.extension_months)

    @api.onchange('placement_id')
    def _onchange_placement(self):
        if self.placement_id:
            self.new_salary = self.placement_id.salary
            self.new_bill_rate = self.placement_id.bill_rate

    def action_extend(self):
        """Extend the contract"""
        self.ensure_one()
        
        if self.extension_type == 'months':
            new_end = self.placement_id.date_end + relativedelta(months=self.extension_months)
        else:
            new_end = self.new_end_date
        
        if not new_end or new_end <= self.placement_id.date_end:
            raise ValidationError(_('New end date must be after current end date.'))
        
        vals = {
            'date_end': new_end,
            'state': 'extended',
        }
        
        if self.new_salary:
            vals['salary'] = self.new_salary
        if self.new_bill_rate:
            vals['bill_rate'] = self.new_bill_rate
        
        self.placement_id.write(vals)
        
        # Log the extension
        self.placement_id.message_post(
            body=_(
                'Contract extended until %s. %s',
                new_end.strftime('%Y-%m-%d'),
                self.notes or ''
            )
        )
        
        return {'type': 'ir.actions.act_window_close'}
