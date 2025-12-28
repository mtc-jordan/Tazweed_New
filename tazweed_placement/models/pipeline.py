# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class RecruitmentPipeline(models.Model):
    """Recruitment Pipeline - Tracks candidate progress through stages"""
    _name = 'tazweed.recruitment.pipeline'
    _description = 'Recruitment Pipeline'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'stage_id, priority desc, create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Core Relations
    candidate_id = fields.Many2one('tazweed.candidate', string='Candidate', required=True, tracking=True)
    job_order_id = fields.Many2one('tazweed.job.order', string='Job Order', required=True, tracking=True)
    client_id = fields.Many2one('tazweed.client', related='job_order_id.client_id', store=True)
    
    # Stage
    stage_id = fields.Many2one(
        'tazweed.recruitment.stage',
        string='Stage',
        required=True,
        tracking=True,
        group_expand='_read_group_stage_ids',
    )
    
    # Candidate Info (for kanban display)
    candidate_name = fields.Char(related='candidate_id.name', store=True)
    candidate_email = fields.Char(related='candidate_id.email')
    candidate_mobile = fields.Char(related='candidate_id.mobile')
    candidate_image = fields.Image(related='candidate_id.image_128')
    
    # Job Info
    job_title = fields.Char(related='job_order_id.job_title', store=True)
    
    # Scoring
    match_score = fields.Float(string='Match Score', compute='_compute_match_score', store=True)
    recruiter_rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Below Average'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Recruiter Rating')
    
    # Status
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High'),
    ], string='Priority', default='0')
    
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red'),
    ], string='Kanban State', default='normal')
    
    # Dates
    date_applied = fields.Date(string='Date Applied', default=fields.Date.today)
    date_last_stage_change = fields.Datetime(string='Last Stage Change')
    days_in_stage = fields.Integer(string='Days in Stage', compute='_compute_days_in_stage')
    
    # Assignment
    recruiter_id = fields.Many2one('res.users', string='Recruiter', default=lambda self: self.env.user)
    
    # Interviews
    interview_ids = fields.One2many('tazweed.interview', 'pipeline_id', string='Interviews')
    interview_count = fields.Integer(compute='_compute_interview_count', store=True)
    next_interview_date = fields.Datetime(string='Next Interview', compute='_compute_next_interview')
    
    # Outcome
    result = fields.Selection([
        ('pending', 'Pending'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('on_hold', 'On Hold'),
    ], string='Result', default='pending', tracking=True)
    
    rejection_reason = fields.Selection([
        ('not_qualified', 'Not Qualified'),
        ('salary_mismatch', 'Salary Mismatch'),
        ('failed_interview', 'Failed Interview'),
        ('no_show', 'No Show'),
        ('client_rejected', 'Client Rejected'),
        ('candidate_declined', 'Candidate Declined'),
        ('position_filled', 'Position Filled'),
        ('other', 'Other'),
    ], string='Rejection Reason')
    
    rejection_notes = fields.Text(string='Rejection Notes')
    
    # Placement
    placement_id = fields.Many2one('tazweed.placement', string='Placement')
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('candidate_job_uniq', 'unique(candidate_id, job_order_id)', 
         'Candidate is already in pipeline for this job order!'),
    ]

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """Return all stages for kanban view"""
        return self.env['tazweed.recruitment.stage'].search([])

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.recruitment.pipeline') or _('New')
        
        # Set initial stage if not provided
        if not vals.get('stage_id'):
            initial_stage = self.env['tazweed.recruitment.stage'].search([('is_initial', '=', True)], limit=1)
            if initial_stage:
                vals['stage_id'] = initial_stage.id
        
        result = super().create(vals)
        
        # Update candidate state
        result.candidate_id.write({'state': 'in_process'})
        
        return result

    def write(self, vals):
        if 'stage_id' in vals:
            vals['date_last_stage_change'] = fields.Datetime.now()
            
            # Check if moving to hired stage
            new_stage = self.env['tazweed.recruitment.stage'].browse(vals['stage_id'])
            if new_stage.is_hired:
                vals['result'] = 'hired'
            elif new_stage.is_rejected:
                vals['result'] = 'rejected'
        
        return super().write(vals)

    @api.depends('job_order_id', 'candidate_id')
    def _compute_match_score(self):
        for pipeline in self:
            if pipeline.job_order_id and pipeline.candidate_id:
                pipeline.match_score = pipeline.job_order_id._calculate_match_score(pipeline.candidate_id)
            else:
                pipeline.match_score = 0

    @api.depends('date_last_stage_change')
    def _compute_days_in_stage(self):
        now = fields.Datetime.now()
        for pipeline in self:
            if pipeline.date_last_stage_change:
                delta = now - pipeline.date_last_stage_change
                pipeline.days_in_stage = delta.days
            else:
                pipeline.days_in_stage = 0

    @api.depends('interview_ids')
    def _compute_interview_count(self):
        for pipeline in self:
            pipeline.interview_count = len(pipeline.interview_ids)

    @api.depends('interview_ids', 'interview_ids.scheduled_date', 'interview_ids.state')
    def _compute_next_interview(self):
        for pipeline in self:
            upcoming = pipeline.interview_ids.filtered(
                lambda i: i.state == 'scheduled' and i.scheduled_date
            ).sorted('scheduled_date')
            pipeline.next_interview_date = upcoming[0].scheduled_date if upcoming else False

    def action_schedule_interview(self):
        """Open wizard to schedule interview"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Interview'),
            'res_model': 'tazweed.interview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_pipeline_id': self.id,
                'default_candidate_id': self.candidate_id.id,
                'default_job_order_id': self.job_order_id.id,
            },
        }

    def action_hire(self):
        """Mark as hired and create placement"""
        hired_stage = self.env['tazweed.recruitment.stage'].search([('is_hired', '=', True)], limit=1)
        if hired_stage:
            self.write({
                'stage_id': hired_stage.id,
                'result': 'hired',
            })
        
        # Create placement
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Placement'),
            'res_model': 'tazweed.placement',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_pipeline_id': self.id,
                'default_candidate_id': self.candidate_id.id,
                'default_job_order_id': self.job_order_id.id,
                'default_client_id': self.client_id.id,
            },
        }

    def action_reject(self):
        """Open rejection wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Candidate'),
            'res_model': 'tazweed.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_pipeline_id': self.id},
        }

    def action_view_interviews(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Interviews'),
            'res_model': 'tazweed.interview',
            'view_mode': 'tree,form,calendar',
            'domain': [('pipeline_id', '=', self.id)],
            'context': {
                'default_pipeline_id': self.id,
                'default_candidate_id': self.candidate_id.id,
                'default_job_order_id': self.job_order_id.id,
            },
        }
