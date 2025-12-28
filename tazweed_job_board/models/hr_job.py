# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrJob(models.Model):
    """Extend HR Job with job board integration"""
    _inherit = 'hr.job'

    # Job Board Integration
    posting_ids = fields.One2many('job.posting', 'hr_job_id', string='Job Postings')
    active_posting_count = fields.Integer(string='Active Postings', compute='_compute_posting_stats')
    total_posting_count = fields.Integer(string='Total Postings', compute='_compute_posting_stats')
    
    # Syndication
    syndication_ids = fields.One2many('job.syndication', 'hr_job_id', string='Syndications')
    
    # Sourced Candidates
    sourced_candidate_ids = fields.One2many('candidate.source', 'hr_job_id', string='Sourced Candidates')
    sourced_candidate_count = fields.Integer(string='Sourced Candidates', compute='_compute_candidate_stats')
    
    # Job Board Settings
    default_template_id = fields.Many2one('job.template', string='Default Template')
    auto_post_boards = fields.Many2many('job.board', string='Auto-Post to Boards',
        help='Automatically post to these boards when job is published')
    
    # Job Details for Boards
    remote_type = fields.Selection([
        ('onsite', 'On-site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ], string='Work Type', default='onsite')
    
    employment_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('internship', 'Internship'),
    ], string='Employment Type', default='full_time')
    
    experience_level = fields.Selection([
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior Level'),
        ('executive', 'Executive'),
    ], string='Experience Level', default='mid')
    
    min_experience = fields.Integer(string='Minimum Experience (Years)')
    max_experience = fields.Integer(string='Maximum Experience (Years)')
    
    # Salary Range
    show_salary = fields.Boolean(string='Show Salary on Job Boards', default=False)
    salary_min = fields.Float(string='Minimum Salary')
    salary_max = fields.Float(string='Maximum Salary')
    salary_currency = fields.Many2one('res.currency', string='Salary Currency', 
        default=lambda self: self.env.company.currency_id)
    salary_period = fields.Selection([
        ('hourly', 'Per Hour'),
        ('daily', 'Per Day'),
        ('monthly', 'Per Month'),
        ('yearly', 'Per Year'),
    ], string='Salary Period', default='monthly')
    
    # Keywords & SEO
    keywords = fields.Char(string='Keywords', help='Comma-separated keywords for job board SEO')
    
    # Performance Metrics
    total_views = fields.Integer(string='Total Views', compute='_compute_posting_stats')
    total_applications = fields.Integer(string='Total Applications', compute='_compute_posting_stats')
    total_hires = fields.Integer(string='Total Hires', compute='_compute_posting_stats')
    total_spend = fields.Float(string='Total Spend', compute='_compute_posting_stats')
    avg_cost_per_hire = fields.Float(string='Avg Cost per Hire', compute='_compute_posting_stats')
    
    @api.depends('posting_ids', 'posting_ids.state', 'posting_ids.view_count', 
                 'posting_ids.application_count', 'posting_ids.hired_count', 'posting_ids.cost')
    def _compute_posting_stats(self):
        for job in self:
            postings = job.posting_ids
            job.total_posting_count = len(postings)
            job.active_posting_count = len(postings.filtered(lambda p: p.state == 'active'))
            job.total_views = sum(postings.mapped('view_count'))
            job.total_applications = sum(postings.mapped('application_count'))
            job.total_hires = sum(postings.mapped('hired_count'))
            job.total_spend = sum(postings.mapped('cost'))
            job.avg_cost_per_hire = job.total_spend / job.total_hires if job.total_hires else 0
    
    @api.depends('sourced_candidate_ids')
    def _compute_candidate_stats(self):
        for job in self:
            job.sourced_candidate_count = len(job.sourced_candidate_ids)
    
    def action_post_to_boards(self):
        """Open wizard to post job to multiple boards"""
        self.ensure_one()
        return {
            'name': _('Post Job to Boards'),
            'type': 'ir.actions.act_window',
            'res_model': 'post.job.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_hr_job_id': self.id,
                'default_title': self.name,
                'default_description': self.description,
                'default_employment_type': self.employment_type,
                'default_experience_level': self.experience_level,
                'default_remote_type': self.remote_type,
                'default_salary_min': self.salary_min,
                'default_salary_max': self.salary_max,
                'default_show_salary': self.show_salary,
            },
        }
    
    def action_view_postings(self):
        """View all postings for this job"""
        self.ensure_one()
        return {
            'name': _('Job Postings - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'job.posting',
            'view_mode': 'tree,form,kanban',
            'domain': [('hr_job_id', '=', self.id)],
            'context': {'default_hr_job_id': self.id},
        }
    
    def action_view_sourced_candidates(self):
        """View all sourced candidates for this job"""
        self.ensure_one()
        return {
            'name': _('Sourced Candidates - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'candidate.source',
            'view_mode': 'tree,form,kanban',
            'domain': [('hr_job_id', '=', self.id)],
            'context': {'default_hr_job_id': self.id},
        }
    
    def action_import_candidates(self):
        """Open wizard to import candidates from job boards"""
        self.ensure_one()
        return {
            'name': _('Import Candidates'),
            'type': 'ir.actions.act_window',
            'res_model': 'import.candidates.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_hr_job_id': self.id,
            },
        }
    
    def action_view_analytics(self):
        """View analytics for this job"""
        self.ensure_one()
        return {
            'name': _('Job Analytics - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'job.board.analytics',
            'view_mode': 'tree,pivot,graph',
            'domain': [('hr_job_id', '=', self.id)],
        }
