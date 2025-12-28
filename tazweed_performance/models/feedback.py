# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date


class PerformanceFeedback(models.Model):
    """Performance Feedback"""
    _name = 'tazweed.performance.feedback'
    _description = 'Performance Feedback'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Participants
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        help='Employee receiving feedback',
    )
    provider_id = fields.Many2one(
        'hr.employee',
        string='Feedback Provider',
        default=lambda self: self.env.user.employee_id,
        tracking=True,
    )
    
    review_id = fields.Many2one(
        'tazweed.performance.review',
        string='Performance Review',
    )
    
    feedback_type = fields.Selection([
        ('recognition', 'Recognition'),
        ('constructive', 'Constructive Feedback'),
        ('coaching', 'Coaching'),
        ('peer', 'Peer Feedback'),
        ('manager', 'Manager Feedback'),
        ('subordinate', 'Subordinate Feedback'),
        ('360', '360-Degree Feedback'),
    ], string='Feedback Type', default='recognition', required=True)
    
    category = fields.Selection([
        ('performance', 'Performance'),
        ('behavior', 'Behavior'),
        ('skills', 'Skills'),
        ('teamwork', 'Teamwork'),
        ('communication', 'Communication'),
        ('leadership', 'Leadership'),
        ('innovation', 'Innovation'),
        ('other', 'Other'),
    ], string='Category', default='performance')
    
    # Feedback Content
    subject = fields.Char(string='Subject')
    feedback = fields.Html(string='Feedback', required=True)
    
    # Rating
    rating = fields.Selection([
        ('1', '1 - Needs Improvement'),
        ('2', '2 - Below Expectations'),
        ('3', '3 - Meets Expectations'),
        ('4', '4 - Exceeds Expectations'),
        ('5', '5 - Outstanding'),
    ], string='Rating')
    
    # Visibility
    is_anonymous = fields.Boolean(string='Anonymous', default=False)
    is_private = fields.Boolean(string='Private', default=False)
    visibility = fields.Selection([
        ('employee', 'Employee Only'),
        ('manager', 'Manager Only'),
        ('hr', 'HR Only'),
        ('all', 'All'),
    ], string='Visibility', default='all')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('acknowledged', 'Acknowledged'),
    ], string='Status', default='draft', tracking=True)
    
    # Acknowledgement
    acknowledged_date = fields.Datetime(string='Acknowledged Date')
    employee_response = fields.Text(string='Employee Response')
    
    # Tags
    tag_ids = fields.Many2many(
        'tazweed.feedback.tag',
        string='Tags',
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.performance.feedback') or _('New')
        return super().create(vals)

    def action_submit(self):
        """Submit feedback"""
        self.write({'state': 'submitted'})
        # Notify employee
        if self.employee_id.user_id and not self.is_anonymous:
            self.message_post(
                body=_('You have received new feedback from %s.') % self.provider_id.name,
                partner_ids=[self.employee_id.user_id.partner_id.id],
            )
        return True

    def action_acknowledge(self):
        """Acknowledge feedback"""
        self.write({
            'state': 'acknowledged',
            'acknowledged_date': fields.Datetime.now(),
        })
        return True


class FeedbackTag(models.Model):
    """Feedback Tag"""
    _name = 'tazweed.feedback.tag'
    _description = 'Feedback Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color')
    
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Tag name must be unique!'),
    ]


class FeedbackRequest(models.Model):
    """Feedback Request"""
    _name = 'tazweed.feedback.request'
    _description = 'Feedback Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        help='Employee requesting feedback about',
    )
    requester_id = fields.Many2one(
        'hr.employee',
        string='Requester',
        default=lambda self: self.env.user.employee_id,
    )
    
    provider_ids = fields.Many2many(
        'hr.employee',
        string='Feedback Providers',
        required=True,
    )
    
    review_id = fields.Many2one(
        'tazweed.performance.review',
        string='Performance Review',
    )
    
    request_type = fields.Selection([
        ('peer', 'Peer Feedback'),
        ('subordinate', 'Subordinate Feedback'),
        ('360', '360-Degree Feedback'),
        ('project', 'Project Feedback'),
    ], string='Request Type', default='peer')
    
    deadline = fields.Date(string='Deadline')
    
    questions = fields.Text(string='Questions/Guidelines')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    feedback_ids = fields.One2many(
        'tazweed.performance.feedback',
        'review_id',
        string='Received Feedback',
    )
    feedback_count = fields.Integer(compute='_compute_feedback_count')
    completion_rate = fields.Float(compute='_compute_completion_rate')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.feedback.request') or _('New')
        return super().create(vals)

    @api.depends('feedback_ids')
    def _compute_feedback_count(self):
        for request in self:
            request.feedback_count = len(request.feedback_ids)

    @api.depends('provider_ids', 'feedback_ids')
    def _compute_completion_rate(self):
        for request in self:
            if request.provider_ids:
                request.completion_rate = (len(request.feedback_ids) / len(request.provider_ids)) * 100
            else:
                request.completion_rate = 0

    def action_send(self):
        """Send feedback request"""
        self.write({'state': 'sent'})
        # Notify providers
        for provider in self.provider_ids:
            if provider.user_id:
                self.message_post(
                    body=_('You have been requested to provide feedback for %s.') % self.employee_id.name,
                    partner_ids=[provider.user_id.partner_id.id],
                )
        return True

    def action_complete(self):
        """Mark as completed"""
        self.write({'state': 'completed'})
        return True

    def action_cancel(self):
        """Cancel request"""
        self.write({'state': 'cancelled'})
        return True


class Recognition(models.Model):
    """Employee Recognition"""
    _name = 'tazweed.recognition'
    _description = 'Employee Recognition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True)
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )
    recognizer_id = fields.Many2one(
        'hr.employee',
        string='Recognized By',
        default=lambda self: self.env.user.employee_id,
    )
    
    recognition_type = fields.Selection([
        ('achievement', 'Achievement'),
        ('innovation', 'Innovation'),
        ('teamwork', 'Teamwork'),
        ('customer_service', 'Customer Service'),
        ('leadership', 'Leadership'),
        ('milestone', 'Milestone'),
        ('other', 'Other'),
    ], string='Recognition Type', default='achievement')
    
    description = fields.Html(string='Description')
    
    # Award
    award_type = fields.Selection([
        ('certificate', 'Certificate'),
        ('bonus', 'Bonus'),
        ('gift', 'Gift'),
        ('time_off', 'Time Off'),
        ('promotion', 'Promotion'),
        ('other', 'Other'),
    ], string='Award Type')
    
    award_value = fields.Float(string='Award Value')
    
    # Visibility
    is_public = fields.Boolean(string='Public Recognition', default=True)
    
    date = fields.Date(string='Date', default=fields.Date.today)
    
    # Likes/Comments
    like_count = fields.Integer(string='Likes', default=0)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    def action_like(self):
        """Like recognition"""
        self.like_count += 1
        return True
