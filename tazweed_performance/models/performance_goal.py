# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class PerformanceGoal(models.Model):
    """Performance Goal"""
    _name = 'tazweed.performance.goal'
    _description = 'Performance Goal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, date_deadline'

    name = fields.Char(
        string='Goal Title',
        required=True,
        tracking=True,
    )
    description = fields.Html(string='Description')
    
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
    
    review_id = fields.Many2one(
        'tazweed.performance.review',
        string='Performance Review',
    )
    period_id = fields.Many2one(
        'tazweed.performance.period',
        string='Period',
    )
    
    goal_type = fields.Selection([
        ('individual', 'Individual'),
        ('team', 'Team'),
        ('department', 'Department'),
        ('company', 'Company'),
    ], string='Goal Type', default='individual', required=True)
    
    category = fields.Selection([
        ('performance', 'Performance'),
        ('development', 'Development'),
        ('project', 'Project'),
        ('operational', 'Operational'),
        ('strategic', 'Strategic'),
    ], string='Category', default='performance')
    
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority', default='1')
    
    # SMART Goal Components
    is_specific = fields.Boolean(string='Specific')
    is_measurable = fields.Boolean(string='Measurable')
    is_achievable = fields.Boolean(string='Achievable')
    is_relevant = fields.Boolean(string='Relevant')
    is_time_bound = fields.Boolean(string='Time-bound')
    smart_score = fields.Integer(string='SMART Score', compute='_compute_smart_score')
    
    # Dates
    date_start = fields.Date(string='Start Date', default=fields.Date.today)
    date_deadline = fields.Date(string='Deadline', required=True)
    date_completed = fields.Date(string='Completion Date')
    
    # Progress
    progress = fields.Float(string='Progress (%)', default=0, tracking=True)
    progress_notes = fields.Text(string='Progress Notes')
    
    # Measurement
    measurement_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('yes_no', 'Yes/No'),
        ('rating', 'Rating'),
    ], string='Measurement Type', default='percentage')
    
    target_value = fields.Float(string='Target Value')
    actual_value = fields.Float(string='Actual Value')
    unit = fields.Char(string='Unit')
    
    # Scoring
    weight = fields.Float(string='Weight (%)', default=100)
    self_score = fields.Float(string='Self Score', digits=(3, 2))
    manager_score = fields.Float(string='Manager Score', digits=(3, 2))
    achievement_score = fields.Float(string='Achievement Score', compute='_compute_achievement_score', store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Milestones
    milestone_ids = fields.One2many(
        'tazweed.goal.milestone',
        'goal_id',
        string='Milestones',
    )
    milestone_count = fields.Integer(compute='_compute_milestone_count')
    
    # Alignment
    parent_goal_id = fields.Many2one(
        'tazweed.performance.goal',
        string='Parent Goal',
    )
    child_goal_ids = fields.One2many(
        'tazweed.performance.goal',
        'parent_goal_id',
        string='Sub-Goals',
    )
    
    # Comments
    employee_comments = fields.Text(string='Employee Comments')
    manager_comments = fields.Text(string='Manager Comments')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('is_specific', 'is_measurable', 'is_achievable', 'is_relevant', 'is_time_bound')
    def _compute_smart_score(self):
        for goal in self:
            score = sum([
                goal.is_specific,
                goal.is_measurable,
                goal.is_achievable,
                goal.is_relevant,
                goal.is_time_bound,
            ])
            goal.smart_score = score

    @api.depends('progress', 'target_value', 'actual_value', 'measurement_type', 'manager_score')
    def _compute_achievement_score(self):
        for goal in self:
            if goal.manager_score:
                goal.achievement_score = goal.manager_score
            elif goal.measurement_type == 'percentage':
                goal.achievement_score = min(goal.progress / 20, 5)  # Convert to 5-point scale
            elif goal.target_value and goal.actual_value:
                achievement_pct = (goal.actual_value / goal.target_value) * 100
                goal.achievement_score = min(achievement_pct / 20, 5)
            else:
                goal.achievement_score = 0

    @api.depends('milestone_ids')
    def _compute_milestone_count(self):
        for goal in self:
            goal.milestone_count = len(goal.milestone_ids)

    @api.onchange('milestone_ids')
    def _onchange_milestones(self):
        """Update progress based on milestones"""
        if self.milestone_ids:
            completed = sum(1 for m in self.milestone_ids if m.is_completed)
            self.progress = (completed / len(self.milestone_ids)) * 100

    def action_submit(self):
        """Submit for approval"""
        self.write({'state': 'pending'})
        return True

    def action_approve(self):
        """Approve the goal"""
        self.write({'state': 'approved'})
        return True

    def action_start(self):
        """Start working on goal"""
        self.write({'state': 'in_progress'})
        return True

    def action_complete(self):
        """Mark as completed"""
        self.write({
            'state': 'completed',
            'date_completed': date.today(),
            'progress': 100,
        })
        return True

    def action_cancel(self):
        """Cancel the goal"""
        self.write({'state': 'cancelled'})
        return True

    def action_reset_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
        return True


class GoalMilestone(models.Model):
    """Goal Milestone"""
    _name = 'tazweed.goal.milestone'
    _description = 'Goal Milestone'
    _order = 'sequence, date_deadline'

    goal_id = fields.Many2one(
        'tazweed.performance.goal',
        string='Goal',
        required=True,
        ondelete='cascade',
    )
    name = fields.Char(string='Milestone', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    date_deadline = fields.Date(string='Deadline')
    date_completed = fields.Date(string='Completion Date')
    is_completed = fields.Boolean(string='Completed')
    
    weight = fields.Float(string='Weight (%)', default=0)
    notes = fields.Text(string='Notes')

    def action_complete(self):
        """Mark milestone as completed"""
        self.write({
            'is_completed': True,
            'date_completed': date.today(),
        })
        return True
