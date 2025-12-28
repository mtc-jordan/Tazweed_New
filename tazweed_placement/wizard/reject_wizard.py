# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class RejectWizard(models.TransientModel):
    """Wizard to reject candidate from pipeline"""
    _name = 'tazweed.reject.wizard'
    _description = 'Reject Candidate'

    pipeline_id = fields.Many2one('tazweed.recruitment.pipeline', string='Pipeline', required=True)
    
    rejection_reason = fields.Selection([
        ('not_qualified', 'Not Qualified'),
        ('salary_mismatch', 'Salary Mismatch'),
        ('failed_interview', 'Failed Interview'),
        ('no_show', 'No Show'),
        ('client_rejected', 'Client Rejected'),
        ('candidate_declined', 'Candidate Declined'),
        ('position_filled', 'Position Filled'),
        ('other', 'Other'),
    ], string='Rejection Reason', required=True)
    
    rejection_notes = fields.Text(string='Notes')
    
    send_notification = fields.Boolean(string='Send Notification to Candidate', default=True)

    def action_reject(self):
        """Reject the candidate"""
        self.ensure_one()
        
        # Get rejected stage
        rejected_stage = self.env['tazweed.recruitment.stage'].search([('is_rejected', '=', True)], limit=1)
        
        vals = {
            'result': 'rejected',
            'rejection_reason': self.rejection_reason,
            'rejection_notes': self.rejection_notes,
        }
        
        if rejected_stage:
            vals['stage_id'] = rejected_stage.id
        
        self.pipeline_id.write(vals)
        
        # Update candidate state
        self.pipeline_id.candidate_id.write({'state': 'rejected'})
        
        # Send notification if requested
        if self.send_notification:
            self._send_rejection_notification()
        
        return {'type': 'ir.actions.act_window_close'}

    def _send_rejection_notification(self):
        """Send rejection email to candidate"""
        # This would send an email using mail template
        pass
