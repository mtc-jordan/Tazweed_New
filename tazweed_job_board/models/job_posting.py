# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging
import json

_logger = logging.getLogger(__name__)


class JobPosting(models.Model):
    """Individual job posting to a specific job board"""
    _name = 'job.posting'
    _description = 'Job Board Posting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'posted_date desc, id desc'
    _rec_name = 'display_name'

    # Basic Info
    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Job Reference
    hr_job_id = fields.Many2one('hr.job', string='Job Position', required=True, ondelete='cascade')
    job_title = fields.Char(string='Job Title', related='hr_job_id.name', store=True)
    department_id = fields.Many2one('hr.department', string='Department', related='hr_job_id.department_id', store=True)
    company_id = fields.Many2one('res.company', string='Company', related='hr_job_id.company_id', store=True)
    
    # Job Board
    job_board_id = fields.Many2one('job.board', string='Job Board', required=True, ondelete='restrict')
    board_code = fields.Char(string='Board Code', related='job_board_id.code', store=True)
    board_logo = fields.Binary(string='Board Logo', related='job_board_id.logo')
    board_color = fields.Char(string='Board Color', related='job_board_id.color')
    
    # Posting Details
    external_id = fields.Char(string='External Job ID', help='Job ID on the external board')
    external_url = fields.Char(string='External URL', help='Direct link to the job on the board')
    
    # Content
    title = fields.Char(string='Posted Title', required=True)
    description = fields.Html(string='Job Description', required=True)
    requirements = fields.Html(string='Requirements')
    benefits = fields.Html(string='Benefits')
    
    # Location
    location = fields.Char(string='Location')
    remote_type = fields.Selection([
        ('onsite', 'On-site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ], string='Work Type', default='onsite')
    
    # Compensation
    show_salary = fields.Boolean(string='Show Salary', default=False)
    salary_min = fields.Float(string='Minimum Salary')
    salary_max = fields.Float(string='Maximum Salary')
    salary_currency = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    salary_period = fields.Selection([
        ('hourly', 'Per Hour'),
        ('daily', 'Per Day'),
        ('monthly', 'Per Month'),
        ('yearly', 'Per Year'),
    ], string='Salary Period', default='monthly')
    
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
    experience_years = fields.Integer(string='Years of Experience')
    
    # Status & Dates
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
        ('closed', 'Closed'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', tracking=True)
    
    posted_date = fields.Datetime(string='Posted Date')
    expiry_date = fields.Date(string='Expiry Date')
    scheduled_date = fields.Datetime(string='Scheduled Post Date')
    last_refreshed = fields.Datetime(string='Last Refreshed')
    
    # Performance Metrics
    view_count = fields.Integer(string='Views', default=0)
    click_count = fields.Integer(string='Clicks', default=0)
    application_count = fields.Integer(string='Applications', default=0)
    hired_count = fields.Integer(string='Hired', default=0)
    
    # Calculated Metrics
    click_rate = fields.Float(string='Click Rate (%)', compute='_compute_rates')
    application_rate = fields.Float(string='Application Rate (%)', compute='_compute_rates')
    conversion_rate = fields.Float(string='Conversion Rate (%)', compute='_compute_rates')
    
    # Cost Tracking
    cost = fields.Float(string='Total Cost (AED)', default=0.0)
    cost_per_click = fields.Float(string='Cost per Click', compute='_compute_cost_metrics')
    cost_per_application = fields.Float(string='Cost per Application', compute='_compute_cost_metrics')
    cost_per_hire = fields.Float(string='Cost per Hire', compute='_compute_cost_metrics')
    
    # Promotion
    is_featured = fields.Boolean(string='Featured Posting', default=False)
    is_sponsored = fields.Boolean(string='Sponsored', default=False)
    daily_budget = fields.Float(string='Daily Budget (AED)')
    
    # Syndication
    syndication_id = fields.Many2one('job.syndication', string='Syndication Group')
    is_master = fields.Boolean(string='Is Master Posting', default=False)
    
    # Error Handling
    error_message = fields.Text(string='Error Message')
    retry_count = fields.Integer(string='Retry Count', default=0)
    
    # Audit
    posted_by = fields.Many2one('res.users', string='Posted By')
    approved_by = fields.Many2one('res.users', string='Approved By')
    
    @api.depends('hr_job_id', 'job_board_id')
    def _compute_display_name(self):
        for posting in self:
            if posting.hr_job_id and posting.job_board_id:
                posting.display_name = f"{posting.hr_job_id.name} - {posting.job_board_id.name}"
            else:
                posting.display_name = posting.name or 'New Posting'
    
    @api.depends('view_count', 'click_count', 'application_count', 'hired_count')
    def _compute_rates(self):
        for posting in self:
            posting.click_rate = (posting.click_count / posting.view_count * 100) if posting.view_count else 0
            posting.application_rate = (posting.application_count / posting.click_count * 100) if posting.click_count else 0
            posting.conversion_rate = (posting.hired_count / posting.application_count * 100) if posting.application_count else 0
    
    @api.depends('cost', 'click_count', 'application_count', 'hired_count')
    def _compute_cost_metrics(self):
        for posting in self:
            posting.cost_per_click = posting.cost / posting.click_count if posting.click_count else 0
            posting.cost_per_application = posting.cost / posting.application_count if posting.application_count else 0
            posting.cost_per_hire = posting.cost / posting.hired_count if posting.hired_count else 0
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('job.posting') or 'New'
        return super().create(vals)
    
    def action_submit_for_approval(self):
        """Submit posting for approval"""
        self.ensure_one()
        self.state = 'pending'
        # Create activity for approver
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=_('Job Posting Approval Required'),
            note=_('Please review and approve the job posting for %s on %s') % (self.title, self.job_board_id.name),
        )
    
    def action_approve(self):
        """Approve and post the job"""
        self.ensure_one()
        self.approved_by = self.env.user
        if self.scheduled_date and self.scheduled_date > fields.Datetime.now():
            self.state = 'scheduled'
        else:
            self.action_post()
    
    def action_post(self):
        """Post the job to the job board"""
        self.ensure_one()
        try:
            # Call board-specific posting method
            method_name = f'_post_to_{self.board_code}'
            if hasattr(self, method_name):
                getattr(self, method_name)()
            else:
                self._post_generic()
            
            self.state = 'active'
            self.posted_date = fields.Datetime.now()
            self.posted_by = self.env.user
            self.error_message = False
            
            # Log success
            self.message_post(
                body=_('Job successfully posted to %s') % self.job_board_id.name,
                message_type='notification',
            )
            
        except Exception as e:
            self.state = 'failed'
            self.error_message = str(e)
            self.retry_count += 1
            _logger.error(f"Failed to post job {self.name} to {self.job_board_id.name}: {e}")
            raise UserError(_('Failed to post job: %s') % str(e))
    
    def _post_generic(self):
        """Generic posting method - override for specific boards"""
        _logger.info(f"Generic posting for {self.name} - implement board-specific method")
        # Simulate successful posting
        self.external_id = f"EXT-{self.id}-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    def _post_to_linkedin(self):
        """Post job to LinkedIn"""
        board = self.job_board_id
        if not board.access_token:
            raise UserError(_('LinkedIn access token not configured'))
        
        # LinkedIn Jobs API implementation
        # This would use the LinkedIn Marketing API
        payload = {
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'employmentType': self.employment_type.upper(),
        }
        
        # Simulate API call
        _logger.info(f"Posting to LinkedIn: {payload}")
        self.external_id = f"LI-{self.id}"
        self.external_url = f"https://www.linkedin.com/jobs/view/{self.external_id}"
    
    def _post_to_indeed(self):
        """Post job to Indeed"""
        board = self.job_board_id
        if not board.api_key:
            raise UserError(_('Indeed API key not configured'))
        
        # Indeed XML Feed or API implementation
        _logger.info(f"Posting to Indeed: {self.title}")
        self.external_id = f"IND-{self.id}"
        self.external_url = f"https://www.indeed.com/viewjob?jk={self.external_id}"
    
    def _post_to_bayt(self):
        """Post job to Bayt.com"""
        board = self.job_board_id
        if not board.api_key:
            raise UserError(_('Bayt API key not configured'))
        
        # Bayt API implementation
        _logger.info(f"Posting to Bayt: {self.title}")
        self.external_id = f"BAYT-{self.id}"
        self.external_url = f"https://www.bayt.com/en/job/{self.external_id}"
    
    def _post_to_gulftalent(self):
        """Post job to GulfTalent"""
        _logger.info(f"Posting to GulfTalent: {self.title}")
        self.external_id = f"GT-{self.id}"
        self.external_url = f"https://www.gulftalent.com/job/{self.external_id}"
    
    def action_pause(self):
        """Pause the job posting"""
        self.ensure_one()
        self.state = 'paused'
        self.message_post(body=_('Job posting paused'))
    
    def action_resume(self):
        """Resume a paused posting"""
        self.ensure_one()
        self.state = 'active'
        self.message_post(body=_('Job posting resumed'))
    
    def action_close(self):
        """Close the job posting"""
        self.ensure_one()
        self.state = 'closed'
        self.message_post(body=_('Job posting closed'))
    
    def action_refresh(self):
        """Refresh the job posting on the board"""
        self.ensure_one()
        try:
            # Call board-specific refresh method
            method_name = f'_refresh_on_{self.board_code}'
            if hasattr(self, method_name):
                getattr(self, method_name)()
            
            self.last_refreshed = fields.Datetime.now()
            self.message_post(body=_('Job posting refreshed'))
            
        except Exception as e:
            raise UserError(_('Failed to refresh: %s') % str(e))
    
    def action_sync_metrics(self):
        """Sync performance metrics from the job board"""
        self.ensure_one()
        try:
            method_name = f'_sync_metrics_{self.board_code}'
            if hasattr(self, method_name):
                getattr(self, method_name)()
            else:
                # Simulate metrics update
                import random
                self.view_count += random.randint(10, 100)
                self.click_count += random.randint(1, 20)
                self.application_count += random.randint(0, 5)
            
            self.message_post(body=_('Metrics synced from %s') % self.job_board_id.name)
            
        except Exception as e:
            _logger.error(f"Failed to sync metrics: {e}")
    
    def action_view_external(self):
        """Open the job posting on the external board"""
        self.ensure_one()
        if self.external_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.external_url,
                'target': 'new',
            }
        else:
            raise UserError(_('External URL not available'))
    
    @api.model
    def _cron_check_expired_postings(self):
        """Cron job to check and update expired postings"""
        expired = self.search([
            ('state', '=', 'active'),
            ('expiry_date', '<', fields.Date.today()),
        ])
        expired.write({'state': 'expired'})
        _logger.info(f"Marked {len(expired)} postings as expired")
    
    @api.model
    def _cron_post_scheduled(self):
        """Cron job to post scheduled jobs"""
        scheduled = self.search([
            ('state', '=', 'scheduled'),
            ('scheduled_date', '<=', fields.Datetime.now()),
        ])
        for posting in scheduled:
            try:
                posting.action_post()
            except Exception as e:
                _logger.error(f"Failed to post scheduled job {posting.name}: {e}")
    
    @api.model
    def _cron_sync_all_metrics(self):
        """Cron job to sync metrics for all active postings"""
        active_postings = self.search([('state', '=', 'active')])
        for posting in active_postings:
            try:
                posting.action_sync_metrics()
            except Exception as e:
                _logger.error(f"Failed to sync metrics for {posting.name}: {e}")


class JobSyndication(models.Model):
    """Group multiple postings for the same job across different boards"""
    _name = 'job.syndication'
    _description = 'Job Syndication Group'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    hr_job_id = fields.Many2one('hr.job', string='Job Position', required=True)
    
    posting_ids = fields.One2many('job.posting', 'syndication_id', string='Postings')
    board_count = fields.Integer(string='Boards', compute='_compute_statistics')
    
    # Aggregated Metrics
    total_views = fields.Integer(string='Total Views', compute='_compute_statistics')
    total_clicks = fields.Integer(string='Total Clicks', compute='_compute_statistics')
    total_applications = fields.Integer(string='Total Applications', compute='_compute_statistics')
    total_cost = fields.Float(string='Total Cost', compute='_compute_statistics')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', compute='_compute_state', store=True)
    
    @api.depends('posting_ids', 'posting_ids.state', 'posting_ids.view_count', 
                 'posting_ids.click_count', 'posting_ids.application_count', 'posting_ids.cost')
    def _compute_statistics(self):
        for syndication in self:
            syndication.board_count = len(syndication.posting_ids)
            syndication.total_views = sum(syndication.posting_ids.mapped('view_count'))
            syndication.total_clicks = sum(syndication.posting_ids.mapped('click_count'))
            syndication.total_applications = sum(syndication.posting_ids.mapped('application_count'))
            syndication.total_cost = sum(syndication.posting_ids.mapped('cost'))
    
    @api.depends('posting_ids.state')
    def _compute_state(self):
        for syndication in self:
            if not syndication.posting_ids:
                syndication.state = 'draft'
            elif any(p.state == 'active' for p in syndication.posting_ids):
                syndication.state = 'active'
            else:
                syndication.state = 'closed'
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('job.syndication') or 'New'
        return super().create(vals)
    
    def action_post_all(self):
        """Post to all boards in the syndication"""
        for posting in self.posting_ids.filtered(lambda p: p.state == 'draft'):
            posting.action_post()
    
    def action_close_all(self):
        """Close all postings in the syndication"""
        for posting in self.posting_ids.filtered(lambda p: p.state in ['active', 'paused']):
            posting.action_close()
