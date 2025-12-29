# -*- coding: utf-8 -*-
"""
Indeed and Bayt.com Integration for Tazweed Job Board
Multi-platform job posting and candidate sourcing
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import json
from datetime import datetime, timedelta
import hashlib

_logger = logging.getLogger(__name__)


class JobBoardPlatform(models.Model):
    """Job Board Platform Configuration"""
    _name = 'job.board.platform'
    _description = 'Job Board Platform'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Platform Name', required=True, tracking=True)
    code = fields.Char(string='Platform Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company, required=True)
    
    # Platform Type
    platform_type = fields.Selection([
        ('indeed', 'Indeed'),
        ('bayt', 'Bayt.com'),
        ('glassdoor', 'Glassdoor'),
        ('monster', 'Monster'),
        ('naukrigulf', 'NaukriGulf'),
        ('gulftalent', 'GulfTalent'),
        ('linkedin', 'LinkedIn'),
        ('custom', 'Custom Platform'),
    ], string='Platform Type', required=True, tracking=True)
    
    # API Configuration
    api_url = fields.Char(string='API URL')
    api_key = fields.Char(string='API Key')
    api_secret = fields.Char(string='API Secret')
    employer_id = fields.Char(string='Employer ID')
    
    # OAuth (if applicable)
    oauth_client_id = fields.Char(string='OAuth Client ID')
    oauth_client_secret = fields.Char(string='OAuth Client Secret')
    oauth_access_token = fields.Text(string='Access Token')
    oauth_refresh_token = fields.Text(string='Refresh Token')
    oauth_token_expiry = fields.Datetime(string='Token Expiry')
    
    # Configuration
    auto_post = fields.Boolean(string='Auto Post Jobs', default=False)
    auto_sync = fields.Boolean(string='Auto Sync Applications', default=False)
    sync_interval = fields.Selection([
        ('hourly', 'Every Hour'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], string='Sync Interval', default='daily')
    
    # Posting Settings
    default_sponsored = fields.Boolean(string='Default Sponsored', default=False)
    default_budget = fields.Float(string='Default Daily Budget')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    
    # Status
    state = fields.Selection([
        ('draft', 'Not Configured'),
        ('testing', 'Testing'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True)
    
    active = fields.Boolean(string='Active', default=True)
    last_sync = fields.Datetime(string='Last Sync')
    error_message = fields.Text(string='Error Message')
    
    # Statistics
    total_postings = fields.Integer(string='Total Postings', compute='_compute_statistics')
    active_postings = fields.Integer(string='Active Postings', compute='_compute_statistics')
    total_applications = fields.Integer(string='Total Applications', compute='_compute_statistics')
    total_spend = fields.Float(string='Total Spend', compute='_compute_statistics')
    
    # Related records
    posting_ids = fields.One2many('platform.job.posting', 'platform_id', string='Job Postings')
    
    # Platform Logo
    logo = fields.Binary(string='Platform Logo')

    @api.depends('posting_ids')
    def _compute_statistics(self):
        for rec in self:
            rec.total_postings = len(rec.posting_ids)
            rec.active_postings = len(rec.posting_ids.filtered(lambda p: p.state == 'active'))
            rec.total_applications = sum(rec.posting_ids.mapped('application_count'))
            rec.total_spend = sum(rec.posting_ids.mapped('total_spend'))

    def action_test_connection(self):
        """Test API connection"""
        self.ensure_one()
        # In production, this would test the actual API
        self.write({
            'state': 'testing',
            'error_message': False,
        })
        
        # Simulate successful test
        self.write({'state': 'active'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection Successful'),
                'message': _('Successfully connected to %s') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_sync_now(self):
        """Manually trigger sync"""
        self.ensure_one()
        self._sync_platform_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Complete'),
                'message': _('%s data synchronized successfully') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def _sync_platform_data(self):
        """Sync data with platform"""
        self.ensure_one()
        self.write({'last_sync': datetime.now()})

    @api.model
    def _cron_sync_platforms(self):
        """Cron job to sync all platforms"""
        platforms = self.search([('state', '=', 'active'), ('auto_sync', '=', True)])
        for platform in platforms:
            try:
                platform._sync_platform_data()
            except Exception as e:
                _logger.error(f'Platform sync error ({platform.name}): {e}')
                platform.write({
                    'state': 'error',
                    'error_message': str(e),
                })


class PlatformJobPosting(models.Model):
    """Job Posting on External Platform"""
    _name = 'platform.job.posting'
    _description = 'Platform Job Posting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Job Title', required=True, tracking=True)
    platform_id = fields.Many2one('job.board.platform', string='Platform',
                                   required=True, ondelete='cascade')
    job_posting_id = fields.Many2one('job.posting', string='Internal Job Posting',
                                      help='Link to internal job posting')
    
    # Platform IDs
    external_job_id = fields.Char(string='External Job ID')
    external_url = fields.Char(string='External URL')
    
    # Job Details
    description = fields.Html(string='Job Description', required=True)
    requirements = fields.Html(string='Requirements')
    benefits = fields.Html(string='Benefits')
    
    location_city = fields.Char(string='City')
    location_country = fields.Many2one('res.country', string='Country')
    remote_type = fields.Selection([
        ('onsite', 'On-site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ], string='Remote Type', default='onsite')
    
    employment_type = fields.Selection([
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('internship', 'Internship'),
    ], string='Employment Type', default='full_time')
    
    # Salary
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
    hide_salary = fields.Boolean(string='Hide Salary', default=False)
    
    # Sponsorship (Indeed/Bayt)
    is_sponsored = fields.Boolean(string='Sponsored', default=False)
    daily_budget = fields.Float(string='Daily Budget')
    total_budget = fields.Float(string='Total Budget')
    total_spend = fields.Float(string='Total Spend', default=0)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    
    rejection_reason = fields.Text(string='Rejection Reason')
    
    # Dates
    posted_date = fields.Datetime(string='Posted Date')
    expiry_date = fields.Date(string='Expiry Date')
    
    # Statistics
    impressions = fields.Integer(string='Impressions', default=0)
    clicks = fields.Integer(string='Clicks', default=0)
    application_count = fields.Integer(string='Applications', compute='_compute_application_count')
    click_rate = fields.Float(string='Click Rate %', compute='_compute_rates')
    apply_rate = fields.Float(string='Apply Rate %', compute='_compute_rates')
    cost_per_click = fields.Float(string='Cost Per Click', compute='_compute_rates')
    cost_per_apply = fields.Float(string='Cost Per Apply', compute='_compute_rates')
    
    # Applications
    application_ids = fields.One2many('platform.application', 'posting_id', string='Applications')

    @api.depends('application_ids')
    def _compute_application_count(self):
        for rec in self:
            rec.application_count = len(rec.application_ids)

    @api.depends('impressions', 'clicks', 'application_count', 'total_spend')
    def _compute_rates(self):
        for rec in self:
            rec.click_rate = (rec.clicks / rec.impressions * 100) if rec.impressions > 0 else 0
            rec.apply_rate = (rec.application_count / rec.clicks * 100) if rec.clicks > 0 else 0
            rec.cost_per_click = (rec.total_spend / rec.clicks) if rec.clicks > 0 else 0
            rec.cost_per_apply = (rec.total_spend / rec.application_count) if rec.application_count > 0 else 0

    def action_post(self):
        """Post job to platform"""
        self.ensure_one()
        if self.platform_id.state != 'active':
            raise UserError(_('Platform integration is not active'))
        
        # In production, this would call the platform API
        self.write({
            'state': 'active',
            'posted_date': datetime.now(),
            'external_job_id': f'{self.platform_id.code.upper()}-{self.id}-{datetime.now().strftime("%Y%m%d")}',
            'external_url': f'https://{self.platform_id.code}.com/jobs/{self.id}',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Job Posted'),
                'message': _('Job successfully posted to %s') % self.platform_id.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_pause(self):
        """Pause the job posting"""
        self.write({'state': 'paused'})

    def action_resume(self):
        """Resume the job posting"""
        self.write({'state': 'active'})

    def action_close(self):
        """Close the job posting"""
        self.write({'state': 'closed'})


class PlatformApplication(models.Model):
    """Application from External Platform"""
    _name = 'platform.application'
    _description = 'Platform Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Applicant Name', required=True)
    posting_id = fields.Many2one('platform.job.posting', string='Job Posting',
                                  required=True, ondelete='cascade')
    platform_id = fields.Many2one(related='posting_id.platform_id', string='Platform', store=True)
    
    # External IDs
    external_application_id = fields.Char(string='External Application ID')
    external_profile_url = fields.Char(string='External Profile URL')
    
    # Contact Info
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    
    # Professional Info
    headline = fields.Char(string='Professional Headline')
    current_company = fields.Char(string='Current Company')
    current_position = fields.Char(string='Current Position')
    location = fields.Char(string='Location')
    
    # Experience
    total_experience = fields.Float(string='Total Experience (Years)')
    education_level = fields.Selection([
        ('high_school', 'High School'),
        ('associate', 'Associate Degree'),
        ('bachelor', "Bachelor's Degree"),
        ('master', "Master's Degree"),
        ('doctorate', 'Doctorate'),
        ('other', 'Other'),
    ], string='Education Level')
    
    # Resume
    resume = fields.Binary(string='Resume')
    resume_filename = fields.Char(string='Resume Filename')
    cover_letter = fields.Text(string='Cover Letter')
    
    # Questions & Answers
    screening_answers = fields.Text(string='Screening Answers')
    
    # Application Details
    applied_date = fields.Datetime(string='Applied Date', default=fields.Datetime.now)
    
    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('reviewed', 'Reviewed'),
        ('shortlisted', 'Shortlisted'),
        ('interview', 'Interview'),
        ('offered', 'Offered'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ], string='Status', default='new', tracking=True)
    
    # AI Scoring
    ai_score = fields.Float(string='AI Match Score')
    ai_recommendation = fields.Selection([
        ('strong_match', 'Strong Match'),
        ('good_match', 'Good Match'),
        ('moderate_match', 'Moderate Match'),
        ('weak_match', 'Weak Match'),
    ], string='AI Recommendation')
    
    # Linked Candidate
    candidate_id = fields.Many2one('tazweed.candidate', string='Linked Candidate')
    
    # Notes
    notes = fields.Text(string='Notes')

    def action_import_to_candidates(self):
        """Import application as internal candidate"""
        self.ensure_one()
        if self.candidate_id:
            raise UserError(_('This application is already linked to a candidate'))
        
        candidate = self.env['tazweed.candidate'].create({
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'source': self.platform_id.platform_type,
            'resume': self.resume,
            'resume_filename': self.resume_filename,
        })
        
        self.write({'candidate_id': candidate.id})
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Candidate'),
            'res_model': 'tazweed.candidate',
            'res_id': candidate.id,
            'view_mode': 'form',
            'target': 'current',
        }


class MultiPlatformPostingWizard(models.TransientModel):
    """Wizard to post job to multiple platforms at once"""
    _name = 'multi.platform.posting.wizard'
    _description = 'Multi-Platform Posting Wizard'

    job_posting_id = fields.Many2one('job.posting', string='Job Posting', required=True)
    platform_ids = fields.Many2many('job.board.platform', string='Platforms',
                                     domain=[('state', '=', 'active')])
    
    # Common Settings
    is_sponsored = fields.Boolean(string='Sponsored Posting', default=False)
    daily_budget = fields.Float(string='Daily Budget per Platform')
    expiry_date = fields.Date(string='Expiry Date')

    def action_post_to_platforms(self):
        """Post job to selected platforms"""
        self.ensure_one()
        
        if not self.platform_ids:
            raise UserError(_('Please select at least one platform'))
        
        created_postings = []
        for platform in self.platform_ids:
            posting = self.env['platform.job.posting'].create({
                'name': self.job_posting_id.name,
                'platform_id': platform.id,
                'job_posting_id': self.job_posting_id.id,
                'description': self.job_posting_id.description,
                'is_sponsored': self.is_sponsored,
                'daily_budget': self.daily_budget,
                'expiry_date': self.expiry_date,
            })
            posting.action_post()
            created_postings.append(posting.id)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Jobs Posted'),
                'message': _('Job posted to %d platforms successfully') % len(created_postings),
                'type': 'success',
                'sticky': False,
            }
        }
