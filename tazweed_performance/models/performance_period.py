# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class PerformancePeriod(models.Model):
    """Performance Review Period"""
    _name = 'tazweed.performance.period'
    _description = 'Performance Review Period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(
        string='Period Name',
        required=True,
        tracking=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
    )
    period_type = fields.Selection([
        ('annual', 'Annual'),
        ('semi_annual', 'Semi-Annual'),
        ('quarterly', 'Quarterly'),
        ('monthly', 'Monthly'),
    ], string='Period Type', required=True, default='annual', tracking=True)
    
    date_start = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
    )
    date_end = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
    )
    
    # Review Dates
    self_review_start = fields.Date(string='Self Review Start')
    self_review_end = fields.Date(string='Self Review End')
    manager_review_start = fields.Date(string='Manager Review Start')
    manager_review_end = fields.Date(string='Manager Review End')
    calibration_start = fields.Date(string='Calibration Start')
    calibration_end = fields.Date(string='Calibration End')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('self_review', 'Self Review'),
        ('manager_review', 'Manager Review'),
        ('calibration', 'Calibration'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    review_ids = fields.One2many(
        'tazweed.performance.review',
        'period_id',
        string='Reviews',
    )
    review_count = fields.Integer(
        string='Review Count',
        compute='_compute_review_count',
    )
    
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    @api.depends('review_ids')
    def _compute_review_count(self):
        for period in self:
            period.review_count = len(period.review_ids)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for period in self:
            if period.date_end < period.date_start:
                raise ValidationError(_('End date must be after start date.'))

    def action_open(self):
        """Open the performance period"""
        self.write({'state': 'open'})
        return True

    def action_start_self_review(self):
        """Start self review phase"""
        self.write({'state': 'self_review'})
        # Notify employees
        for review in self.review_ids:
            review.message_post(
                body=_('Self review period has started. Please complete your self-assessment.'),
                partner_ids=[review.employee_id.user_id.partner_id.id] if review.employee_id.user_id else [],
            )
        return True

    def action_start_manager_review(self):
        """Start manager review phase"""
        self.write({'state': 'manager_review'})
        return True

    def action_start_calibration(self):
        """Start calibration phase"""
        self.write({'state': 'calibration'})
        return True

    def action_close(self):
        """Close the performance period"""
        self.write({'state': 'closed'})
        return True

    def action_view_reviews(self):
        """View reviews for this period"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Performance Reviews'),
            'res_model': 'tazweed.performance.review',
            'view_mode': 'tree,form',
            'domain': [('period_id', '=', self.id)],
            'context': {'default_period_id': self.id},
        }


class PerformanceTemplate(models.Model):
    """Performance Review Template"""
    _name = 'tazweed.performance.template'
    _description = 'Performance Review Template'
    _inherit = ['mail.thread']

    name = fields.Char(string='Template Name', required=True)
    description = fields.Text(string='Description')
    
    template_type = fields.Selection([
        ('standard', 'Standard Review'),
        ('probation', 'Probation Review'),
        ('annual', 'Annual Review'),
        ('project', 'Project Review'),
        ('360', '360-Degree Review'),
    ], string='Template Type', default='standard', required=True)
    
    # Sections
    section_ids = fields.One2many(
        'tazweed.performance.template.section',
        'template_id',
        string='Sections',
    )
    
    # Weights
    goal_weight = fields.Float(string='Goals Weight (%)', default=40)
    competency_weight = fields.Float(string='Competency Weight (%)', default=30)
    kpi_weight = fields.Float(string='KPI Weight (%)', default=30)
    
    # Settings
    include_self_assessment = fields.Boolean(string='Include Self Assessment', default=True)
    include_manager_assessment = fields.Boolean(string='Include Manager Assessment', default=True)
    include_peer_feedback = fields.Boolean(string='Include Peer Feedback', default=False)
    include_subordinate_feedback = fields.Boolean(string='Include Subordinate Feedback', default=False)
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.constrains('goal_weight', 'competency_weight', 'kpi_weight')
    def _check_weights(self):
        for template in self:
            total = template.goal_weight + template.competency_weight + template.kpi_weight
            if abs(total - 100) > 0.01:
                raise ValidationError(_('Total weights must equal 100%. Current total: %.2f%%') % total)


class PerformanceTemplateSection(models.Model):
    """Performance Template Section"""
    _name = 'tazweed.performance.template.section'
    _description = 'Performance Template Section'
    _order = 'sequence'

    template_id = fields.Many2one(
        'tazweed.performance.template',
        string='Template',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Section Name', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    section_type = fields.Selection([
        ('goals', 'Goals'),
        ('competencies', 'Competencies'),
        ('kpis', 'KPIs'),
        ('feedback', 'Feedback'),
        ('development', 'Development'),
        ('comments', 'Comments'),
    ], string='Section Type', required=True)
    
    weight = fields.Float(string='Weight (%)', default=0)
    is_required = fields.Boolean(string='Required', default=True)
    
    question_ids = fields.One2many(
        'tazweed.performance.template.question',
        'section_id',
        string='Questions',
    )


class PerformanceTemplateQuestion(models.Model):
    """Performance Template Question"""
    _name = 'tazweed.performance.template.question'
    _description = 'Performance Template Question'
    _order = 'sequence'

    section_id = fields.Many2one(
        'tazweed.performance.template.section',
        string='Section',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Question', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    question_type = fields.Selection([
        ('rating', 'Rating (1-5)'),
        ('rating_10', 'Rating (1-10)'),
        ('text', 'Text'),
        ('yes_no', 'Yes/No'),
        ('multiple_choice', 'Multiple Choice'),
    ], string='Question Type', default='rating', required=True)
    
    options = fields.Text(string='Options (for multiple choice)')
    is_required = fields.Boolean(string='Required', default=True)
    weight = fields.Float(string='Weight', default=1)
