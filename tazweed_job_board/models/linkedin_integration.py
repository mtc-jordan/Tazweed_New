# -*- coding: utf-8 -*-
"""
LinkedIn Integration for Tazweed Job Board
Post jobs directly to LinkedIn and import candidates
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import json
from datetime import datetime, timedelta
import hashlib
import base64

_logger = logging.getLogger(__name__)


class LinkedInIntegration(models.Model):
    """LinkedIn API Integration Configuration"""
    _name = 'linkedin.integration'
    _description = 'LinkedIn Integration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Integration Name', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company, required=True)
    
    # API Credentials
    client_id = fields.Char(string='Client ID', required=True)
    client_secret = fields.Char(string='Client Secret', required=True)
    access_token = fields.Text(string='Access Token')
    refresh_token = fields.Text(string='Refresh Token')
    token_expiry = fields.Datetime(string='Token Expiry')
    
    # LinkedIn Organization
    organization_id = fields.Char(string='LinkedIn Organization ID')
    organization_name = fields.Char(string='Organization Name')
    organization_logo = fields.Binary(string='Organization Logo')
    
    # Configuration
    auto_post = fields.Boolean(string='Auto Post Jobs', default=False,
                               help='Automatically post new jobs to LinkedIn')
    auto_import_candidates = fields.Boolean(string='Auto Import Candidates', default=False,
                                            help='Automatically import candidate applications')
    sync_interval = fields.Selection([
        ('hourly', 'Every Hour'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], string='Sync Interval', default='daily')
    
    # Status
    state = fields.Selection([
        ('draft', 'Not Connected'),
        ('connected', 'Connected'),
        ('expired', 'Token Expired'),
        ('error', 'Error'),
    ], string='Status', default='draft', tracking=True)
    
    last_sync = fields.Datetime(string='Last Sync')
    error_message = fields.Text(string='Error Message')
    
    # Statistics
    total_jobs_posted = fields.Integer(string='Total Jobs Posted', compute='_compute_statistics')
    total_applications = fields.Integer(string='Total Applications', compute='_compute_statistics')
    active_postings = fields.Integer(string='Active Postings', compute='_compute_statistics')
    
    # Related records
    posting_ids = fields.One2many('linkedin.job.posting', 'integration_id', string='Job Postings')
    application_ids = fields.One2many('linkedin.application', 'integration_id', string='Applications')

    @api.depends('posting_ids', 'application_ids')
    def _compute_statistics(self):
        for rec in self:
            rec.total_jobs_posted = len(rec.posting_ids)
            rec.total_applications = len(rec.application_ids)
            rec.active_postings = len(rec.posting_ids.filtered(lambda p: p.state == 'active'))

    def action_connect(self):
        """Initiate OAuth connection to LinkedIn"""
        self.ensure_one()
        # In production, this would redirect to LinkedIn OAuth
        # For demo, we simulate a successful connection
        self.write({
            'state': 'connected',
            'access_token': self._generate_demo_token(),
            'token_expiry': datetime.now() + timedelta(days=60),
            'last_sync': datetime.now(),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('LinkedIn Connected'),
                'message': _('Successfully connected to LinkedIn API'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_disconnect(self):
        """Disconnect from LinkedIn"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'access_token': False,
            'refresh_token': False,
            'token_expiry': False,
        })

    def action_refresh_token(self):
        """Refresh the access token"""
        self.ensure_one()
        if self.state != 'connected':
            raise UserError(_('Integration is not connected'))
        
        self.write({
            'access_token': self._generate_demo_token(),
            'token_expiry': datetime.now() + timedelta(days=60),
        })

    def action_sync_now(self):
        """Manually trigger sync"""
        self.ensure_one()
        self._sync_linkedin_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Complete'),
                'message': _('LinkedIn data synchronized successfully'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _sync_linkedin_data(self):
        """Sync data with LinkedIn"""
        self.ensure_one()
        # In production, this would call LinkedIn API
        self.write({'last_sync': datetime.now()})

    def _generate_demo_token(self):
        """Generate a demo token for testing"""
        return hashlib.sha256(f'{self.client_id}{datetime.now()}'.encode()).hexdigest()

    @api.model
    def _cron_sync_linkedin(self):
        """Cron job to sync LinkedIn data"""
        integrations = self.search([('state', '=', 'connected')])
        for integration in integrations:
            try:
                integration._sync_linkedin_data()
            except Exception as e:
                _logger.error(f'LinkedIn sync error: {e}')
                integration.write({
                    'state': 'error',
                    'error_message': str(e),
                })


class LinkedInJobPosting(models.Model):
    """LinkedIn Job Posting"""
    _name = 'linkedin.job.posting'
    _description = 'LinkedIn Job Posting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Job Title', required=True, tracking=True)
    integration_id = fields.Many2one('linkedin.integration', string='LinkedIn Integration',
                                      required=True, ondelete='cascade')
    job_posting_id = fields.Many2one('job.posting', string='Job Board Posting',
                                      help='Link to internal job posting')
    
    # LinkedIn IDs
    linkedin_job_id = fields.Char(string='LinkedIn Job ID')
    linkedin_url = fields.Char(string='LinkedIn URL')
    
    # Job Details
    description = fields.Html(string='Job Description', required=True)
    location = fields.Char(string='Location')
    employment_type = fields.Selection([
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('internship', 'Internship'),
    ], string='Employment Type', default='full_time')
    
    experience_level = fields.Selection([
        ('entry', 'Entry Level'),
        ('associate', 'Associate'),
        ('mid_senior', 'Mid-Senior Level'),
        ('director', 'Director'),
        ('executive', 'Executive'),
    ], string='Experience Level')
    
    industry = fields.Char(string='Industry')
    function = fields.Char(string='Job Function')
    
    # Salary
    salary_min = fields.Float(string='Minimum Salary')
    salary_max = fields.Float(string='Maximum Salary')
    salary_currency = fields.Many2one('res.currency', string='Currency',
                                       default=lambda self: self.env.company.currency_id)
    show_salary = fields.Boolean(string='Show Salary', default=True)
    
    # Skills
    required_skills = fields.Text(string='Required Skills')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('closed', 'Closed'),
        ('expired', 'Expired'),
    ], string='Status', default='draft', tracking=True)
    
    # Dates
    posted_date = fields.Datetime(string='Posted Date')
    expiry_date = fields.Date(string='Expiry Date')
    
    # Statistics
    views = fields.Integer(string='Views', default=0)
    clicks = fields.Integer(string='Clicks', default=0)
    applications = fields.Integer(string='Applications', compute='_compute_applications')
    
    application_ids = fields.One2many('linkedin.application', 'posting_id', string='Applications')

    @api.depends('application_ids')
    def _compute_applications(self):
        for rec in self:
            rec.applications = len(rec.application_ids)

    def action_post_to_linkedin(self):
        """Post job to LinkedIn"""
        self.ensure_one()
        if self.integration_id.state != 'connected':
            raise UserError(_('LinkedIn integration is not connected'))
        
        # In production, this would call LinkedIn API
        self.write({
            'state': 'active',
            'posted_date': datetime.now(),
            'linkedin_job_id': f'LI-{self.id}-{datetime.now().strftime("%Y%m%d")}',
            'linkedin_url': f'https://www.linkedin.com/jobs/view/{self.id}',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Job Posted'),
                'message': _('Job successfully posted to LinkedIn'),
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


class LinkedInApplication(models.Model):
    """LinkedIn Job Application"""
    _name = 'linkedin.application'
    _description = 'LinkedIn Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Applicant Name', required=True)
    integration_id = fields.Many2one('linkedin.integration', string='LinkedIn Integration',
                                      required=True, ondelete='cascade')
    posting_id = fields.Many2one('linkedin.job.posting', string='Job Posting',
                                  required=True, ondelete='cascade')
    
    # LinkedIn Profile
    linkedin_profile_id = fields.Char(string='LinkedIn Profile ID')
    linkedin_url = fields.Char(string='LinkedIn Profile URL')
    profile_picture = fields.Binary(string='Profile Picture')
    
    # Contact Info
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    
    # Professional Info
    headline = fields.Char(string='Professional Headline')
    current_company = fields.Char(string='Current Company')
    current_position = fields.Char(string='Current Position')
    location = fields.Char(string='Location')
    
    # Experience & Education
    total_experience = fields.Float(string='Total Experience (Years)')
    education = fields.Text(string='Education')
    skills = fields.Text(string='Skills')
    
    # Resume
    resume = fields.Binary(string='Resume')
    resume_filename = fields.Char(string='Resume Filename')
    cover_letter = fields.Text(string='Cover Letter')
    
    # Application Details
    applied_date = fields.Datetime(string='Applied Date', default=fields.Datetime.now)
    source = fields.Selection([
        ('linkedin_easy_apply', 'LinkedIn Easy Apply'),
        ('linkedin_apply', 'LinkedIn Apply'),
        ('imported', 'Imported'),
    ], string='Source', default='linkedin_easy_apply')
    
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
    ai_score = fields.Float(string='AI Match Score', help='AI-calculated match score 0-100')
    ai_recommendation = fields.Selection([
        ('strong_match', 'Strong Match'),
        ('good_match', 'Good Match'),
        ('moderate_match', 'Moderate Match'),
        ('weak_match', 'Weak Match'),
    ], string='AI Recommendation')
    
    # Linked Candidate
    candidate_id = fields.Many2one('tazweed.candidate', string='Linked Candidate',
                                    help='Link to internal candidate record')
    
    # Notes
    notes = fields.Text(string='Notes')

    def action_import_to_candidates(self):
        """Import LinkedIn application as internal candidate"""
        self.ensure_one()
        if self.candidate_id:
            raise UserError(_('This application is already linked to a candidate'))
        
        # Create candidate from LinkedIn application
        candidate = self.env['tazweed.candidate'].create({
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'linkedin_url': self.linkedin_url,
            'source': 'linkedin',
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

    def action_shortlist(self):
        """Shortlist the application"""
        self.write({'state': 'shortlisted'})

    def action_reject(self):
        """Reject the application"""
        self.write({'state': 'rejected'})
