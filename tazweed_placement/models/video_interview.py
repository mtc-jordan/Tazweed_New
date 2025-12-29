# -*- coding: utf-8 -*-
"""
Video Interview Integration Module
Schedule and conduct video interviews with candidates
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import uuid
import logging

_logger = logging.getLogger(__name__)


class VideoInterview(models.Model):
    """Video Interview Management"""
    _name = 'video.interview'
    _description = 'Video Interview'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc, create_date desc'
    _rec_name = 'display_name'

    # Core Fields
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )
    
    # Interview Details
    candidate_id = fields.Many2one(
        'tazweed.candidate',
        string='Candidate',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    job_order_id = fields.Many2one(
        'tazweed.job.order',
        string='Job Order',
        ondelete='set null',
        tracking=True,
    )
    interview_type = fields.Selection([
        ('screening', 'Initial Screening'),
        ('technical', 'Technical Interview'),
        ('hr', 'HR Interview'),
        ('final', 'Final Interview'),
        ('panel', 'Panel Interview'),
    ], string='Interview Type', default='screening', required=True, tracking=True)
    
    # Scheduling
    scheduled_date = fields.Datetime(
        string='Scheduled Date/Time',
        required=True,
        tracking=True,
    )
    duration = fields.Integer(
        string='Duration (minutes)',
        default=30,
        required=True,
    )
    end_time = fields.Datetime(
        string='End Time',
        compute='_compute_end_time',
        store=True,
    )
    timezone = fields.Selection(
        '_get_timezones',
        string='Timezone',
        default='Asia/Dubai',
    )
    
    # Video Platform
    platform = fields.Selection([
        ('zoom', 'Zoom'),
        ('teams', 'Microsoft Teams'),
        ('meet', 'Google Meet'),
        ('webex', 'Cisco Webex'),
        ('custom', 'Custom Link'),
    ], string='Platform', default='zoom', required=True)
    
    meeting_link = fields.Char(
        string='Meeting Link',
        help='Auto-generated or custom meeting link',
    )
    meeting_id = fields.Char(
        string='Meeting ID',
    )
    meeting_password = fields.Char(
        string='Meeting Password',
    )
    
    # Participants
    interviewer_ids = fields.Many2many(
        'res.users',
        'video_interview_interviewer_rel',
        'interview_id',
        'user_id',
        string='Interviewers',
    )
    client_participant_ids = fields.Many2many(
        'res.partner',
        'video_interview_client_rel',
        'interview_id',
        'partner_id',
        string='Client Participants',
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('reminder_sent', 'Reminder Sent'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ], string='Status', default='draft', tracking=True)
    
    # Recording
    is_recorded = fields.Boolean(
        string='Record Interview',
        default=True,
    )
    recording_url = fields.Char(
        string='Recording URL',
    )
    recording_consent = fields.Boolean(
        string='Recording Consent',
        help='Candidate has consented to recording',
    )
    
    # Evaluation
    overall_rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Overall Rating', tracking=True)
    
    technical_score = fields.Integer(
        string='Technical Score',
        help='Score out of 100',
    )
    communication_score = fields.Integer(
        string='Communication Score',
        help='Score out of 100',
    )
    cultural_fit_score = fields.Integer(
        string='Cultural Fit Score',
        help='Score out of 100',
    )
    
    evaluation_notes = fields.Html(
        string='Evaluation Notes',
    )
    strengths = fields.Text(
        string='Strengths',
    )
    weaknesses = fields.Text(
        string='Areas for Improvement',
    )
    recommendation = fields.Selection([
        ('hire', 'Recommend to Hire'),
        ('next_round', 'Proceed to Next Round'),
        ('hold', 'On Hold'),
        ('reject', 'Do Not Proceed'),
    ], string='Recommendation', tracking=True)
    
    # Questions
    question_ids = fields.One2many(
        'video.interview.question',
        'interview_id',
        string='Interview Questions',
    )
    
    # Related Fields
    candidate_name = fields.Char(
        related='candidate_id.name',
        string='Candidate Name',
        store=True,
    )
    candidate_email = fields.Char(
        related='candidate_id.email',
        string='Candidate Email',
    )
    job_title = fields.Char(
        related='job_order_id.job_title',
        string='Job Title',
        store=True,
    )
    client_id = fields.Many2one(
        related='job_order_id.client_id',
        string='Client',
        store=True,
    )
    
    # Reminders
    reminder_sent = fields.Boolean(
        string='Reminder Sent',
        default=False,
    )
    reminder_date = fields.Datetime(
        string='Reminder Sent Date',
    )

    @api.model
    def _get_timezones(self):
        """Get list of timezones"""
        return [
            ('Asia/Dubai', 'Dubai (GMT+4)'),
            ('Asia/Riyadh', 'Riyadh (GMT+3)'),
            ('Europe/London', 'London (GMT)'),
            ('America/New_York', 'New York (GMT-5)'),
            ('Asia/Kolkata', 'India (GMT+5:30)'),
            ('Asia/Manila', 'Manila (GMT+8)'),
        ]

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('video.interview') or _('New')
        return super().create(vals)

    @api.depends('candidate_id', 'job_order_id', 'interview_type')
    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.candidate_id:
                parts.append(record.candidate_id.name)
            if record.job_order_id:
                parts.append(record.job_order_id.job_title)
            if record.interview_type:
                parts.append(dict(self._fields['interview_type'].selection).get(record.interview_type, ''))
            record.display_name = ' - '.join(parts) if parts else record.name

    @api.depends('scheduled_date', 'duration')
    def _compute_end_time(self):
        for record in self:
            if record.scheduled_date and record.duration:
                record.end_time = record.scheduled_date + timedelta(minutes=record.duration)
            else:
                record.end_time = False

    @api.constrains('scheduled_date')
    def _check_scheduled_date(self):
        for record in self:
            if record.scheduled_date and record.scheduled_date < fields.Datetime.now():
                if record.state == 'draft':
                    raise ValidationError(_('Cannot schedule interview in the past.'))

    def action_schedule(self):
        """Schedule the interview and generate meeting link"""
        self.ensure_one()
        
        # Generate meeting link based on platform
        if not self.meeting_link:
            self.meeting_link = self._generate_meeting_link()
        
        self.state = 'scheduled'
        
        # Send invitations
        self._send_interview_invitations()
        
        return True

    def _generate_meeting_link(self):
        """Generate a meeting link based on the platform"""
        unique_id = str(uuid.uuid4())[:8]
        
        if self.platform == 'zoom':
            # In production, integrate with Zoom API
            return f"https://zoom.us/j/{unique_id}"
        elif self.platform == 'teams':
            return f"https://teams.microsoft.com/l/meetup-join/{unique_id}"
        elif self.platform == 'meet':
            return f"https://meet.google.com/{unique_id}"
        elif self.platform == 'webex':
            return f"https://webex.com/meet/{unique_id}"
        else:
            return self.meeting_link or ''

    def _send_interview_invitations(self):
        """Send interview invitations to all participants"""
        template = self.env.ref('tazweed_placement.email_template_video_interview_invitation', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        
        # Log the activity
        self.message_post(
            body=_('Interview scheduled for %s. Meeting link: %s') % (
                self.scheduled_date.strftime('%Y-%m-%d %H:%M'),
                self.meeting_link,
            ),
            subject=_('Interview Scheduled'),
        )

    def action_send_reminder(self):
        """Send reminder to participants"""
        self.ensure_one()
        
        template = self.env.ref('tazweed_placement.email_template_video_interview_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        
        self.write({
            'reminder_sent': True,
            'reminder_date': fields.Datetime.now(),
            'state': 'reminder_sent',
        })
        
        return True

    def action_start_interview(self):
        """Mark interview as in progress"""
        self.state = 'in_progress'
        return True

    def action_complete(self):
        """Mark interview as completed"""
        self.state = 'completed'
        return True

    def action_cancel(self):
        """Cancel the interview"""
        self.state = 'cancelled'
        self._send_cancellation_notice()
        return True

    def action_mark_no_show(self):
        """Mark as no-show"""
        self.state = 'no_show'
        return True

    def action_reschedule(self):
        """Open reschedule wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reschedule Interview'),
            'res_model': 'video.interview.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_interview_id': self.id,
            },
        }

    def _send_cancellation_notice(self):
        """Send cancellation notice"""
        self.message_post(
            body=_('Interview has been cancelled.'),
            subject=_('Interview Cancelled'),
        )

    def action_join_meeting(self):
        """Open the meeting link"""
        if not self.meeting_link:
            raise UserError(_('No meeting link available.'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.meeting_link,
            'target': 'new',
        }

    def action_view_recording(self):
        """View the interview recording"""
        if not self.recording_url:
            raise UserError(_('No recording available.'))
        return {
            'type': 'ir.actions.act_url',
            'url': self.recording_url,
            'target': 'new',
        }

    @api.model
    def _cron_send_reminders(self):
        """Cron job to send interview reminders"""
        # Find interviews scheduled in the next 24 hours that haven't received reminders
        tomorrow = fields.Datetime.now() + timedelta(hours=24)
        interviews = self.search([
            ('state', '=', 'scheduled'),
            ('reminder_sent', '=', False),
            ('scheduled_date', '<=', tomorrow),
            ('scheduled_date', '>=', fields.Datetime.now()),
        ])
        
        for interview in interviews:
            try:
                interview.action_send_reminder()
            except Exception as e:
                _logger.error("Failed to send reminder for interview %s: %s", interview.id, str(e))


class VideoInterviewQuestion(models.Model):
    """Interview Questions"""
    _name = 'video.interview.question'
    _description = 'Video Interview Question'
    _order = 'sequence, id'

    interview_id = fields.Many2one(
        'video.interview',
        string='Interview',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    question = fields.Text(
        string='Question',
        required=True,
    )
    question_type = fields.Selection([
        ('behavioral', 'Behavioral'),
        ('technical', 'Technical'),
        ('situational', 'Situational'),
        ('competency', 'Competency-based'),
        ('general', 'General'),
    ], string='Question Type', default='general')
    
    expected_answer = fields.Text(
        string='Expected Answer/Guidelines',
    )
    candidate_answer = fields.Text(
        string='Candidate Answer',
    )
    rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Rating')
    notes = fields.Text(string='Notes')


class VideoInterviewTemplate(models.Model):
    """Interview Question Templates"""
    _name = 'video.interview.template'
    _description = 'Video Interview Template'
    _order = 'name'

    name = fields.Char(
        string='Template Name',
        required=True,
    )
    interview_type = fields.Selection([
        ('screening', 'Initial Screening'),
        ('technical', 'Technical Interview'),
        ('hr', 'HR Interview'),
        ('final', 'Final Interview'),
        ('panel', 'Panel Interview'),
    ], string='Interview Type', required=True)
    
    description = fields.Text(string='Description')
    duration = fields.Integer(
        string='Default Duration (minutes)',
        default=30,
    )
    question_ids = fields.One2many(
        'video.interview.template.question',
        'template_id',
        string='Questions',
    )
    active = fields.Boolean(default=True)

    def action_use_template(self, interview_id):
        """Apply template questions to an interview"""
        interview = self.env['video.interview'].browse(interview_id)
        for question in self.question_ids:
            self.env['video.interview.question'].create({
                'interview_id': interview.id,
                'sequence': question.sequence,
                'question': question.question,
                'question_type': question.question_type,
                'expected_answer': question.expected_answer,
            })
        return True


class VideoInterviewTemplateQuestion(models.Model):
    """Template Questions"""
    _name = 'video.interview.template.question'
    _description = 'Video Interview Template Question'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'video.interview.template',
        string='Template',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    question = fields.Text(
        string='Question',
        required=True,
    )
    question_type = fields.Selection([
        ('behavioral', 'Behavioral'),
        ('technical', 'Technical'),
        ('situational', 'Situational'),
        ('competency', 'Competency-based'),
        ('general', 'General'),
    ], string='Question Type', default='general')
    expected_answer = fields.Text(
        string='Expected Answer/Guidelines',
    )
