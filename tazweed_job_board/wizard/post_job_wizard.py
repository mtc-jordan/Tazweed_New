# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class PostJobWizard(models.TransientModel):
    """Wizard for posting jobs to multiple boards"""
    _name = 'post.job.wizard'
    _description = 'Post Job to Boards Wizard'

    # Step tracking
    current_step = fields.Selection([
        ('job', 'Job Details'),
        ('content', 'Content'),
        ('boards', 'Select Boards'),
        ('schedule', 'Schedule'),
        ('review', 'Review'),
    ], string='Current Step', default='job')
    
    # Job Selection
    hr_job_id = fields.Many2one('hr.job', string='Job Position', required=True)
    template_id = fields.Many2one('job.template', string='Use Template')
    
    # Job Details
    title = fields.Char(string='Job Title', required=True)
    department_id = fields.Many2one('hr.department', string='Department', related='hr_job_id.department_id')
    company_id = fields.Many2one('res.company', string='Company', related='hr_job_id.company_id')
    
    # Location
    location = fields.Char(string='Location', default='Dubai, UAE')
    remote_type = fields.Selection([
        ('onsite', 'On-site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ], string='Work Type', default='onsite')
    
    # Employment Details
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
    
    experience_years = fields.Integer(string='Years of Experience Required')
    
    # Salary
    show_salary = fields.Boolean(string='Show Salary', default=False)
    salary_min = fields.Float(string='Minimum Salary')
    salary_max = fields.Float(string='Maximum Salary')
    salary_currency = fields.Many2one('res.currency', string='Currency', 
        default=lambda self: self.env.company.currency_id)
    salary_period = fields.Selection([
        ('hourly', 'Per Hour'),
        ('daily', 'Per Day'),
        ('monthly', 'Per Month'),
        ('yearly', 'Per Year'),
    ], string='Salary Period', default='monthly')
    
    # Content
    description = fields.Html(string='Job Description', required=True)
    requirements = fields.Html(string='Requirements')
    benefits = fields.Html(string='Benefits')
    
    # Board Selection
    job_board_ids = fields.Many2many('job.board', string='Job Boards',
        domain=[('active', '=', True), ('supports_posting', '=', True)])
    board_line_ids = fields.One2many('post.job.wizard.board', 'wizard_id', string='Board Settings')
    
    # Scheduling
    post_immediately = fields.Boolean(string='Post Immediately', default=True)
    scheduled_date = fields.Datetime(string='Scheduled Date')
    expiry_days = fields.Integer(string='Expiry (Days)', default=30)
    expiry_date = fields.Date(string='Expiry Date', compute='_compute_expiry_date')
    
    # Promotion
    is_featured = fields.Boolean(string='Featured Posting', default=False)
    is_sponsored = fields.Boolean(string='Sponsored', default=False)
    daily_budget = fields.Float(string='Daily Budget (AED)')
    
    # Summary
    total_boards = fields.Integer(string='Total Boards', compute='_compute_summary')
    estimated_cost = fields.Float(string='Estimated Cost', compute='_compute_summary')
    estimated_reach = fields.Char(string='Estimated Reach', compute='_compute_summary')
    
    # Create syndication
    create_syndication = fields.Boolean(string='Create Syndication Group', default=True)
    
    @api.depends('expiry_days')
    def _compute_expiry_date(self):
        for wizard in self:
            wizard.expiry_date = fields.Date.today() + timedelta(days=wizard.expiry_days or 30)
    
    @api.depends('job_board_ids', 'board_line_ids')
    def _compute_summary(self):
        for wizard in self:
            wizard.total_boards = len(wizard.job_board_ids)
            wizard.estimated_cost = sum(wizard.job_board_ids.mapped('cost_per_post'))
            
            # Estimate reach based on board types
            reach_estimate = 0
            for board in wizard.job_board_ids:
                if board.board_type == 'global':
                    reach_estimate += 10000
                elif board.board_type == 'regional':
                    reach_estimate += 5000
                else:
                    reach_estimate += 2000
            
            if reach_estimate >= 1000:
                wizard.estimated_reach = f"{reach_estimate // 1000}K+ potential candidates"
            else:
                wizard.estimated_reach = f"{reach_estimate}+ potential candidates"
    
    @api.onchange('template_id')
    def _onchange_template(self):
        if self.template_id:
            template = self.template_id
            if template.title_template:
                self.title = template.title_template.replace('{position}', self.hr_job_id.name or '')
            if template.description_template:
                self.description = template.description_template
            if template.requirements_template:
                self.requirements = template.requirements_template
            if template.benefits_template:
                self.benefits = template.benefits_template
            if template.default_employment_type:
                self.employment_type = template.default_employment_type
            if template.default_experience_level:
                self.experience_level = template.default_experience_level
            if template.default_remote_type:
                self.remote_type = template.default_remote_type
    
    @api.onchange('hr_job_id')
    def _onchange_hr_job(self):
        if self.hr_job_id:
            job = self.hr_job_id
            self.title = job.name
            if job.description:
                self.description = job.description
            if job.employment_type:
                self.employment_type = job.employment_type
            if job.experience_level:
                self.experience_level = job.experience_level
            if job.remote_type:
                self.remote_type = job.remote_type
            if job.salary_min:
                self.salary_min = job.salary_min
            if job.salary_max:
                self.salary_max = job.salary_max
            self.show_salary = job.show_salary
    
    @api.onchange('job_board_ids')
    def _onchange_job_boards(self):
        """Create board lines for selected boards"""
        lines = []
        for board in self.job_board_ids:
            lines.append((0, 0, {
                'job_board_id': board.id,
                'is_featured': self.is_featured,
                'is_sponsored': self.is_sponsored,
            }))
        self.board_line_ids = [(5, 0, 0)] + lines
    
    def action_next_step(self):
        """Move to next step"""
        self.ensure_one()
        steps = ['job', 'content', 'boards', 'schedule', 'review']
        current_index = steps.index(self.current_step)
        if current_index < len(steps) - 1:
            self.current_step = steps[current_index + 1]
        return self._reopen_wizard()
    
    def action_prev_step(self):
        """Move to previous step"""
        self.ensure_one()
        steps = ['job', 'content', 'boards', 'schedule', 'review']
        current_index = steps.index(self.current_step)
        if current_index > 0:
            self.current_step = steps[current_index - 1]
        return self._reopen_wizard()
    
    def _reopen_wizard(self):
        """Reopen the wizard with current state"""
        return {
            'name': _('Post Job to Boards'),
            'type': 'ir.actions.act_window',
            'res_model': 'post.job.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_post_jobs(self):
        """Create and post jobs to selected boards"""
        self.ensure_one()
        
        if not self.job_board_ids:
            raise UserError(_('Please select at least one job board.'))
        
        # Create syndication if requested
        syndication = None
        if self.create_syndication and len(self.job_board_ids) > 1:
            syndication = self.env['job.syndication'].create({
                'hr_job_id': self.hr_job_id.id,
            })
        
        postings = self.env['job.posting']
        
        for board in self.job_board_ids:
            # Get board-specific settings
            board_line = self.board_line_ids.filtered(lambda l: l.job_board_id == board)
            
            posting_vals = {
                'hr_job_id': self.hr_job_id.id,
                'job_board_id': board.id,
                'title': self.title,
                'description': self.description,
                'requirements': self.requirements,
                'benefits': self.benefits,
                'location': self.location,
                'remote_type': self.remote_type,
                'employment_type': self.employment_type,
                'experience_level': self.experience_level,
                'experience_years': self.experience_years,
                'show_salary': self.show_salary,
                'salary_min': self.salary_min,
                'salary_max': self.salary_max,
                'salary_currency': self.salary_currency.id,
                'salary_period': self.salary_period,
                'expiry_date': self.expiry_date,
                'is_featured': board_line.is_featured if board_line else self.is_featured,
                'is_sponsored': board_line.is_sponsored if board_line else self.is_sponsored,
                'daily_budget': board_line.daily_budget if board_line else self.daily_budget,
                'syndication_id': syndication.id if syndication else False,
                'is_master': board == self.job_board_ids[0] if syndication else False,
            }
            
            if self.post_immediately:
                posting_vals['state'] = 'draft'
            else:
                posting_vals['state'] = 'scheduled'
                posting_vals['scheduled_date'] = self.scheduled_date
            
            posting = self.env['job.posting'].create(posting_vals)
            postings |= posting
            
            # Post immediately if requested
            if self.post_immediately:
                try:
                    posting.action_post()
                except Exception as e:
                    # Log error but continue with other boards
                    posting.error_message = str(e)
                    posting.state = 'failed'
        
        # Show result
        if len(postings) == 1:
            return {
                'name': _('Job Posting'),
                'type': 'ir.actions.act_window',
                'res_model': 'job.posting',
                'res_id': postings.id,
                'view_mode': 'form',
            }
        else:
            return {
                'name': _('Job Postings'),
                'type': 'ir.actions.act_window',
                'res_model': 'job.posting',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', postings.ids)],
            }


class PostJobWizardBoard(models.TransientModel):
    """Board-specific settings in post job wizard"""
    _name = 'post.job.wizard.board'
    _description = 'Post Job Wizard Board Settings'

    wizard_id = fields.Many2one('post.job.wizard', string='Wizard', ondelete='cascade')
    job_board_id = fields.Many2one('job.board', string='Job Board', required=True)
    
    # Board info
    board_name = fields.Char(string='Board', related='job_board_id.name')
    board_logo = fields.Binary(string='Logo', related='job_board_id.logo')
    board_color = fields.Char(string='Color', related='job_board_id.color')
    cost_per_post = fields.Float(string='Cost', related='job_board_id.cost_per_post')
    
    # Settings
    is_featured = fields.Boolean(string='Featured', default=False)
    is_sponsored = fields.Boolean(string='Sponsored', default=False)
    daily_budget = fields.Float(string='Daily Budget')
    
    # Board-specific fields
    custom_title = fields.Char(string='Custom Title')
    custom_category = fields.Char(string='Category')
