# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TerminateWizard(models.TransientModel):
    """Wizard to terminate placement"""
    _name = 'tazweed.terminate.wizard'
    _description = 'Terminate Placement'

    placement_id = fields.Many2one('tazweed.placement', string='Placement', required=True)
    
    termination_date = fields.Date(string='Termination Date', required=True, default=fields.Date.today)
    
    termination_reason = fields.Selection([
        ('resignation', 'Resignation'),
        ('termination', 'Termination'),
        ('client_request', 'Client Request'),
        ('performance', 'Performance Issues'),
        ('misconduct', 'Misconduct'),
        ('redundancy', 'Redundancy'),
        ('other', 'Other'),
    ], string='Reason', required=True)
    
    termination_notes = fields.Text(string='Notes')
    
    replacement_required = fields.Boolean(string='Replacement Required')
    replacement_deadline = fields.Date(string='Replacement Deadline')
    
    final_settlement = fields.Float(string='Final Settlement Amount')
    settlement_notes = fields.Text(string='Settlement Notes')

    def action_terminate(self):
        """Terminate the placement"""
        self.ensure_one()
        
        vals = {
            'state': 'terminated',
            'termination_date': self.termination_date,
            'termination_reason': self.termination_reason,
            'termination_notes': self.termination_notes,
            'replacement_required': self.replacement_required,
        }
        
        if self.replacement_required and self.replacement_deadline:
            vals['replacement_deadline'] = self.replacement_deadline
        
        self.placement_id.write(vals)
        
        # Update candidate state back to qualified
        self.placement_id.candidate_id.write({'state': 'qualified'})
        
        # Log termination
        self.placement_id.message_post(
            body=_(
                'Placement terminated on %s. Reason: %s\n%s',
                self.termination_date.strftime('%Y-%m-%d'),
                dict(self._fields['termination_reason'].selection).get(self.termination_reason),
                self.termination_notes or ''
            )
        )
        
        return {'type': 'ir.actions.act_window_close'}
