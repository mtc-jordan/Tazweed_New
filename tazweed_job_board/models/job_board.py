# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class JobBoard(models.Model):
    """Job Board Configuration - Stores connection details for each job board"""
    _name = 'job.board'
    _description = 'Job Board Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Board Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True, help='Unique identifier for the job board')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    
    # Board Type
    board_type = fields.Selection([
        ('global', 'Global'),
        ('regional', 'Regional (MENA/GCC)'),
        ('local', 'Local (UAE)'),
        ('niche', 'Niche/Industry'),
        ('social', 'Social Media'),
    ], string='Board Type', default='global', required=True)
    
    # Connection Details
    api_endpoint = fields.Char(string='API Endpoint')
    api_key = fields.Char(string='API Key', groups='base.group_system')
    api_secret = fields.Char(string='API Secret', groups='base.group_system')
    client_id = fields.Char(string='Client ID', groups='base.group_system')
    access_token = fields.Text(string='Access Token', groups='base.group_system')
    token_expiry = fields.Datetime(string='Token Expiry')
    
    # Board Settings
    website_url = fields.Char(string='Website URL')
    logo = fields.Binary(string='Logo')
    color = fields.Char(string='Brand Color', default='#007bff')
    
    # Posting Settings
    supports_posting = fields.Boolean(string='Supports Job Posting', default=True)
    supports_sourcing = fields.Boolean(string='Supports Candidate Sourcing', default=True)
    supports_analytics = fields.Boolean(string='Supports Analytics', default=False)
    max_job_length = fields.Integer(string='Max Job Description Length', default=5000)
    requires_salary = fields.Boolean(string='Requires Salary Info', default=False)
    
    # Pricing
    cost_per_post = fields.Float(string='Cost per Post (AED)', default=0.0)
    cost_per_click = fields.Float(string='Cost per Click (AED)', default=0.0)
    monthly_budget = fields.Float(string='Monthly Budget (AED)', default=0.0)
    budget_spent = fields.Float(string='Budget Spent (AED)', compute='_compute_budget_spent')
    
    # Statistics
    total_postings = fields.Integer(string='Total Postings', compute='_compute_statistics')
    active_postings = fields.Integer(string='Active Postings', compute='_compute_statistics')
    total_applications = fields.Integer(string='Total Applications', compute='_compute_statistics')
    avg_cost_per_hire = fields.Float(string='Avg Cost per Hire', compute='_compute_statistics')
    
    # Connection Status
    connection_status = fields.Selection([
        ('not_configured', 'Not Configured'),
        ('connected', 'Connected'),
        ('error', 'Connection Error'),
        ('expired', 'Token Expired'),
    ], string='Connection Status', default='not_configured', compute='_compute_connection_status')
    last_sync = fields.Datetime(string='Last Sync')
    last_error = fields.Text(string='Last Error')
    
    # Related Records
    posting_ids = fields.One2many('job.posting', 'job_board_id', string='Job Postings')
    candidate_ids = fields.One2many('candidate.source', 'job_board_id', string='Sourced Candidates')
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Job board code must be unique!'),
    ]
    
    @api.depends('api_key', 'access_token', 'token_expiry')
    def _compute_connection_status(self):
        for board in self:
            if not board.api_key and not board.access_token:
                board.connection_status = 'not_configured'
            elif board.token_expiry and board.token_expiry < fields.Datetime.now():
                board.connection_status = 'expired'
            elif board.last_error:
                board.connection_status = 'error'
            else:
                board.connection_status = 'connected'
    
    @api.depends('posting_ids', 'posting_ids.cost')
    def _compute_budget_spent(self):
        for board in self:
            current_month_start = fields.Date.today().replace(day=1)
            postings = board.posting_ids.filtered(
                lambda p: p.posted_date and p.posted_date >= current_month_start
            )
            board.budget_spent = sum(postings.mapped('cost'))
    
    @api.depends('posting_ids', 'candidate_ids')
    def _compute_statistics(self):
        for board in self:
            board.total_postings = len(board.posting_ids)
            board.active_postings = len(board.posting_ids.filtered(lambda p: p.state == 'active'))
            board.total_applications = sum(board.posting_ids.mapped('application_count'))
            
            # Calculate avg cost per hire
            hired_postings = board.posting_ids.filtered(lambda p: p.hired_count > 0)
            if hired_postings:
                total_cost = sum(hired_postings.mapped('cost'))
                total_hired = sum(hired_postings.mapped('hired_count'))
                board.avg_cost_per_hire = total_cost / total_hired if total_hired else 0
            else:
                board.avg_cost_per_hire = 0
    
    def action_test_connection(self):
        """Test the connection to the job board API"""
        self.ensure_one()
        try:
            # Implement board-specific connection test
            if self.code == 'linkedin':
                self._test_linkedin_connection()
            elif self.code == 'indeed':
                self._test_indeed_connection()
            elif self.code == 'bayt':
                self._test_bayt_connection()
            else:
                # Generic test
                if self.api_endpoint:
                    response = requests.get(self.api_endpoint, timeout=10)
                    if response.status_code == 200:
                        self.last_error = False
                        self.last_sync = fields.Datetime.now()
                    else:
                        raise UserError(f"Connection failed with status {response.status_code}")
            
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
        except Exception as e:
            self.last_error = str(e)
            raise UserError(_('Connection failed: %s') % str(e))
    
    def _test_linkedin_connection(self):
        """Test LinkedIn API connection"""
        # LinkedIn uses OAuth 2.0
        if not self.access_token:
            raise UserError(_('LinkedIn access token not configured'))
        # Add LinkedIn-specific test logic
        pass
    
    def _test_indeed_connection(self):
        """Test Indeed API connection"""
        if not self.api_key:
            raise UserError(_('Indeed API key not configured'))
        # Add Indeed-specific test logic
        pass
    
    def _test_bayt_connection(self):
        """Test Bayt.com API connection"""
        if not self.api_key:
            raise UserError(_('Bayt API key not configured'))
        # Add Bayt-specific test logic
        pass
    
    def action_refresh_token(self):
        """Refresh OAuth token for boards that require it"""
        self.ensure_one()
        if self.code == 'linkedin':
            self._refresh_linkedin_token()
        return True
    
    def _refresh_linkedin_token(self):
        """Refresh LinkedIn OAuth token"""
        # Implement LinkedIn token refresh
        pass
    
    def action_view_postings(self):
        """View all postings for this board"""
        self.ensure_one()
        return {
            'name': _('Job Postings - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'job.posting',
            'view_mode': 'tree,form',
            'domain': [('job_board_id', '=', self.id)],
            'context': {'default_job_board_id': self.id},
        }
    
    def action_view_candidates(self):
        """View all sourced candidates from this board"""
        self.ensure_one()
        return {
            'name': _('Sourced Candidates - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'candidate.source',
            'view_mode': 'tree,form',
            'domain': [('job_board_id', '=', self.id)],
            'context': {'default_job_board_id': self.id},
        }


class JobBoardCredential(models.Model):
    """Store multiple credentials for different accounts on same board"""
    _name = 'job.board.credential'
    _description = 'Job Board Credential'
    
    name = fields.Char(string='Account Name', required=True)
    job_board_id = fields.Many2one('job.board', string='Job Board', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    username = fields.Char(string='Username')
    password = fields.Char(string='Password', groups='base.group_system')
    api_key = fields.Char(string='API Key', groups='base.group_system')
    employer_id = fields.Char(string='Employer ID')
    
    is_default = fields.Boolean(string='Default Account', default=False)
    active = fields.Boolean(string='Active', default=True)
    
    @api.constrains('is_default', 'job_board_id', 'company_id')
    def _check_default_unique(self):
        for record in self:
            if record.is_default:
                existing = self.search([
                    ('job_board_id', '=', record.job_board_id.id),
                    ('company_id', '=', record.company_id.id),
                    ('is_default', '=', True),
                    ('id', '!=', record.id),
                ])
                if existing:
                    raise ValidationError(_('Only one default account per job board per company is allowed.'))
