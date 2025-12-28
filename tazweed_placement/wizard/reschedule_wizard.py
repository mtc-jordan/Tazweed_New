# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RescheduleWizard(models.TransientModel):
    """Wizard to reschedule interview"""
    _name = 'tazweed.reschedule.wizard'
    _description = 'Reschedule Interview'

    interview_id = fields.Many2one('tazweed.interview', string='Interview', required=True)
    
    # Current Schedule
    current_date = fields.Datetime(related='interview_id.scheduled_date', string='Current Date')
    
    # New Schedule
    new_date = fields.Datetime(string='New Date/Time', required=True)
    new_duration = fields.Float(string='Duration (Hours)', default=1.0)
    
    reschedule_reason = fields.Selection([
        ('candidate_request', 'Candidate Request'),
        ('interviewer_unavailable', 'Interviewer Unavailable'),
        ('client_request', 'Client Request'),
        ('scheduling_conflict', 'Scheduling Conflict'),
        ('other', 'Other'),
    ], string='Reason', required=True)
    
    notes = fields.Text(string='Notes')
    
    notify_candidate = fields.Boolean(string='Notify Candidate', default=True)
    notify_interviewers = fields.Boolean(string='Notify Interviewers', default=True)

    @api.constrains('new_date')
    def _check_new_date(self):
        for wizard in self:
            if wizard.new_date and wizard.new_date <= fields.Datetime.now():
                raise ValidationError(_('New date must be in the future.'))

    def action_reschedule(self):
        """Reschedule the interview"""
        self.ensure_one()
        
        # Update interview
        self.interview_id.write({
            'scheduled_date': self.new_date,
            'duration': self.new_duration,
            'state': 'scheduled',
            'notes': (self.interview_id.notes or '') + f'\n\nRescheduled: {self.reschedule_reason}\n{self.notes or ""}',
        })
        
        # Send notifications
        if self.notify_candidate:
            self._notify_candidate()
        if self.notify_interviewers:
            self._notify_interviewers()
        
        return {'type': 'ir.actions.act_window_close'}

    def _notify_candidate(self):
        """Send reschedule notification to candidate"""
        pass

    def _notify_interviewers(self):
        """Send reschedule notification to interviewers"""
        pass
