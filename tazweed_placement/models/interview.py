# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class Interview(models.Model):
    """Interview Management"""
    _name = 'tazweed.interview'
    _description = 'Interview'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Relations
    pipeline_id = fields.Many2one('tazweed.recruitment.pipeline', string='Pipeline', ondelete='cascade')
    candidate_id = fields.Many2one('tazweed.candidate', string='Candidate', required=True)
    job_order_id = fields.Many2one('tazweed.job.order', string='Job Order', required=True)
    client_id = fields.Many2one('tazweed.client', related='job_order_id.client_id', store=True)
    
    # Interview Details
    interview_type = fields.Selection([
        ('phone', 'Phone Screening'),
        ('video', 'Video Interview'),
        ('in_person', 'In-Person Interview'),
        ('technical', 'Technical Interview'),
        ('panel', 'Panel Interview'),
        ('final', 'Final Interview'),
        ('client', 'Client Interview'),
    ], string='Interview Type', required=True, default='phone', tracking=True)
    
    interview_round = fields.Integer(string='Round', default=1)
    
    # Schedule
    scheduled_date = fields.Datetime(string='Scheduled Date/Time', required=True, tracking=True)
    duration = fields.Float(string='Duration (Hours)', default=1.0)
    end_datetime = fields.Datetime(string='End Time', compute='_compute_end_datetime', store=True)
    
    # Location
    location_type = fields.Selection([
        ('office', 'Office'),
        ('client_site', 'Client Site'),
        ('remote', 'Remote/Online'),
        ('other', 'Other'),
    ], string='Location Type', default='office')
    
    location = fields.Char(string='Location/Address')
    meeting_link = fields.Char(string='Meeting Link')
    
    # Interviewers
    interviewer_ids = fields.Many2many('res.users', string='Interviewers')
    external_interviewer = fields.Char(string='External Interviewer')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ], string='Status', default='draft', tracking=True)
    
    # Candidate Confirmation
    candidate_confirmed = fields.Boolean(string='Candidate Confirmed')
    confirmation_date = fields.Datetime(string='Confirmation Date')
    
    # Feedback
    feedback_ids = fields.One2many('tazweed.interview.feedback', 'interview_id', string='Feedback')
    
    overall_rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Overall Rating', compute='_compute_overall_rating', store=True)
    
    recommendation = fields.Selection([
        ('strong_hire', 'Strong Hire'),
        ('hire', 'Hire'),
        ('maybe', 'Maybe'),
        ('no_hire', 'No Hire'),
        ('strong_no_hire', 'Strong No Hire'),
    ], string='Recommendation', compute='_compute_recommendation', store=True)
    
    # Outcome
    result = fields.Selection([
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('on_hold', 'On Hold'),
    ], string='Result', default='pending', tracking=True)
    
    # Notifications
    reminder_sent = fields.Boolean(string='Reminder Sent')
    
    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')
    
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.interview') or _('New')
        return super().create(vals)

    @api.depends('scheduled_date', 'duration')
    def _compute_end_datetime(self):
        for interview in self:
            if interview.scheduled_date and interview.duration:
                interview.end_datetime = interview.scheduled_date + timedelta(hours=interview.duration)
            else:
                interview.end_datetime = False

    @api.depends('feedback_ids', 'feedback_ids.overall_rating')
    def _compute_overall_rating(self):
        for interview in self:
            ratings = interview.feedback_ids.filtered(lambda f: f.overall_rating).mapped('overall_rating')
            if ratings:
                avg = sum(int(r) for r in ratings) / len(ratings)
                interview.overall_rating = str(round(avg))
            else:
                interview.overall_rating = False

    @api.depends('feedback_ids', 'feedback_ids.recommendation')
    def _compute_recommendation(self):
        recommendation_order = ['strong_no_hire', 'no_hire', 'maybe', 'hire', 'strong_hire']
        for interview in self:
            recommendations = interview.feedback_ids.filtered(lambda f: f.recommendation).mapped('recommendation')
            if recommendations:
                # Get most common recommendation
                from collections import Counter
                most_common = Counter(recommendations).most_common(1)[0][0]
                interview.recommendation = most_common
            else:
                interview.recommendation = False

    def action_schedule(self):
        self.write({'state': 'scheduled'})
        # Send calendar invite
        self._send_calendar_invite()

    def action_confirm(self):
        self.write({
            'state': 'confirmed',
            'candidate_confirmed': True,
            'confirmation_date': fields.Datetime.now(),
        })

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_no_show(self):
        self.write({
            'state': 'no_show',
            'result': 'failed',
        })

    def action_reschedule(self):
        """Open reschedule wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reschedule Interview'),
            'res_model': 'tazweed.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_interview_id': self.id},
        }

    def action_add_feedback(self):
        """Open feedback form"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Feedback'),
            'res_model': 'tazweed.interview.feedback',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_interview_id': self.id,
                'default_interviewer_id': self.env.user.id,
            },
        }

    def action_pass(self):
        self.write({'result': 'passed'})

    def action_fail(self):
        self.write({'result': 'failed'})

    def _send_calendar_invite(self):
        """Send calendar invite to candidate and interviewers"""
        # This would integrate with calendar/email
        pass

    def _send_reminder(self):
        """Send reminder before interview"""
        # This would send email/SMS reminder
        self.write({'reminder_sent': True})


class InterviewFeedback(models.Model):
    """Interview Feedback from Interviewer"""
    _name = 'tazweed.interview.feedback'
    _description = 'Interview Feedback'
    _order = 'create_date desc'

    interview_id = fields.Many2one('tazweed.interview', required=True, ondelete='cascade')
    interviewer_id = fields.Many2one('res.users', string='Interviewer', required=True)
    
    # Ratings
    technical_skills = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Technical Skills')
    
    communication = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Communication')
    
    problem_solving = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Problem Solving')
    
    cultural_fit = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Cultural Fit')
    
    leadership = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Leadership')
    
    overall_rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Overall Rating', required=True)
    
    # Recommendation
    recommendation = fields.Selection([
        ('strong_hire', 'Strong Hire'),
        ('hire', 'Hire'),
        ('maybe', 'Maybe'),
        ('no_hire', 'No Hire'),
        ('strong_no_hire', 'Strong No Hire'),
    ], string='Recommendation', required=True)
    
    # Comments
    strengths = fields.Text(string='Strengths')
    weaknesses = fields.Text(string='Areas for Improvement')
    comments = fields.Text(string='Additional Comments')
    
    # Questions Asked
    questions_asked = fields.Text(string='Questions Asked')
    
    create_date = fields.Datetime(string='Submitted On', readonly=True)
