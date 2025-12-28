# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date


class DevelopmentPlan(models.Model):
    """Individual Development Plan"""
    _name = 'tazweed.development.plan'
    _description = 'Development Plan'
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
        tracking=True,
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        related='employee_id.parent_id',
        store=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
    )
    
    # Plan Details
    plan_type = fields.Selection([
        ('performance', 'Performance Improvement'),
        ('career', 'Career Development'),
        ('skill', 'Skill Development'),
        ('leadership', 'Leadership Development'),
        ('succession', 'Succession Planning'),
    ], string='Plan Type', default='career', required=True)
    
    date_start = fields.Date(string='Start Date', default=fields.Date.today)
    date_end = fields.Date(string='End Date')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Goals & Objectives
    career_goal = fields.Text(string='Career Goal')
    short_term_objectives = fields.Text(string='Short-term Objectives (6 months)')
    long_term_objectives = fields.Text(string='Long-term Objectives (1-3 years)')
    
    # Development Activities
    development_activity_ids = fields.One2many(
        'tazweed.development.activity',
        'plan_id',
        string='Development Activities',
    )
    development_activity_count = fields.Integer(compute='_compute_counts')
    
    # Training
    training_ids = fields.One2many(
        'tazweed.development.training',
        'plan_id',
        string='Training Programs',
    )
    training_count = fields.Integer(compute='_compute_counts')
    
    # Competency Gaps
    competency_gap_ids = fields.One2many(
        'tazweed.development.competency.gap',
        'plan_id',
        string='Competency Gaps',
    )
    
    # Progress
    progress = fields.Float(string='Progress (%)', compute='_compute_progress', store=True)
    
    # Review
    review_id = fields.Many2one(
        'tazweed.performance.review',
        string='Related Review',
    )
    
    # Comments
    employee_comments = fields.Text(string='Employee Comments')
    manager_comments = fields.Text(string='Manager Comments')
    hr_comments = fields.Text(string='HR Comments')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.development.plan') or _('New')
        return super().create(vals)

    @api.depends('development_activity_ids', 'training_ids')
    def _compute_counts(self):
        for plan in self:
            plan.development_activity_count = len(plan.development_activity_ids)
            plan.training_count = len(plan.training_ids)

    @api.depends('development_activity_ids.progress', 'training_ids.state')
    def _compute_progress(self):
        for plan in self:
            total_items = len(plan.development_activity_ids) + len(plan.training_ids)
            if not total_items:
                plan.progress = 0
                continue
            
            activity_progress = sum(a.progress for a in plan.development_activity_ids)
            training_completed = sum(1 for t in plan.training_ids if t.state == 'completed') * 100
            
            plan.progress = (activity_progress + training_completed) / total_items

    def action_activate(self):
        """Activate the plan"""
        self.write({'state': 'active'})
        return True

    def action_complete(self):
        """Complete the plan"""
        self.write({'state': 'completed'})
        return True

    def action_cancel(self):
        """Cancel the plan"""
        self.write({'state': 'cancelled'})
        return True


class DevelopmentActivity(models.Model):
    """Development Activity"""
    _name = 'tazweed.development.activity'
    _description = 'Development Activity'
    _order = 'sequence, date_deadline'

    plan_id = fields.Many2one(
        'tazweed.development.plan',
        string='Development Plan',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Activity', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    activity_type = fields.Selection([
        ('training', 'Training'),
        ('coaching', 'Coaching'),
        ('mentoring', 'Mentoring'),
        ('project', 'Project Assignment'),
        ('job_rotation', 'Job Rotation'),
        ('self_study', 'Self Study'),
        ('certification', 'Certification'),
        ('workshop', 'Workshop'),
        ('conference', 'Conference'),
        ('other', 'Other'),
    ], string='Activity Type', default='training')
    
    date_start = fields.Date(string='Start Date')
    date_deadline = fields.Date(string='Deadline')
    date_completed = fields.Date(string='Completion Date')
    
    progress = fields.Float(string='Progress (%)', default=0)
    
    state = fields.Selection([
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planned')
    
    # Resources
    resource_type = fields.Selection([
        ('internal', 'Internal'),
        ('external', 'External'),
    ], string='Resource Type', default='internal')
    
    provider = fields.Char(string='Provider')
    estimated_cost = fields.Float(string='Estimated Cost')
    actual_cost = fields.Float(string='Actual Cost')
    
    # Outcome
    expected_outcome = fields.Text(string='Expected Outcome')
    actual_outcome = fields.Text(string='Actual Outcome')
    
    notes = fields.Text(string='Notes')

    def action_start(self):
        """Start activity"""
        self.write({
            'state': 'in_progress',
            'date_start': date.today(),
        })
        return True

    def action_complete(self):
        """Complete activity"""
        self.write({
            'state': 'completed',
            'date_completed': date.today(),
            'progress': 100,
        })
        return True


class DevelopmentTraining(models.Model):
    """Development Training"""
    _name = 'tazweed.development.training'
    _description = 'Development Training'

    plan_id = fields.Many2one(
        'tazweed.development.plan',
        string='Development Plan',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Training Name', required=True)
    description = fields.Text(string='Description')
    
    training_type = fields.Selection([
        ('internal', 'Internal Training'),
        ('external', 'External Training'),
        ('online', 'Online Course'),
        ('certification', 'Certification'),
        ('workshop', 'Workshop'),
    ], string='Training Type', default='internal')
    
    provider = fields.Char(string='Provider')
    
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    duration_hours = fields.Float(string='Duration (Hours)')
    
    state = fields.Selection([
        ('planned', 'Planned'),
        ('enrolled', 'Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='planned')
    
    estimated_cost = fields.Float(string='Estimated Cost')
    actual_cost = fields.Float(string='Actual Cost')
    
    # Outcome
    score = fields.Float(string='Score')
    certificate = fields.Binary(string='Certificate')
    certificate_name = fields.Char(string='Certificate Filename')
    
    notes = fields.Text(string='Notes')


class DevelopmentCompetencyGap(models.Model):
    """Development Competency Gap"""
    _name = 'tazweed.development.competency.gap'
    _description = 'Development Competency Gap'

    plan_id = fields.Many2one(
        'tazweed.development.plan',
        string='Development Plan',
        required=True,
        ondelete='cascade',
    )
    competency_id = fields.Many2one(
        'tazweed.competency',
        string='Competency',
        required=True,
    )
    
    current_level = fields.Selection([
        ('1', 'Basic'),
        ('2', 'Developing'),
        ('3', 'Proficient'),
        ('4', 'Advanced'),
        ('5', 'Expert'),
    ], string='Current Level')
    
    target_level = fields.Selection([
        ('1', 'Basic'),
        ('2', 'Developing'),
        ('3', 'Proficient'),
        ('4', 'Advanced'),
        ('5', 'Expert'),
    ], string='Target Level')
    
    gap = fields.Float(string='Gap', compute='_compute_gap', store=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Priority', default='medium')
    
    development_actions = fields.Text(string='Development Actions')
    target_date = fields.Date(string='Target Date')
    
    notes = fields.Text(string='Notes')

    @api.depends('current_level', 'target_level')
    def _compute_gap(self):
        for gap in self:
            current = float(gap.current_level or 0)
            target = float(gap.target_level or 0)
            gap.gap = target - current
