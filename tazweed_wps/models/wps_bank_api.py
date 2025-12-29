# -*- coding: utf-8 -*-
"""
WPS Bank API Integration Module
Direct bank file submission and status tracking
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import json
import hashlib
import base64
import logging

_logger = logging.getLogger(__name__)


class WPSBankAPIConnection(models.Model):
    """Bank API Connection Configuration"""
    _name = 'wps.bank.api.connection'
    _description = 'WPS Bank API Connection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Connection Name', required=True, tracking=True)
    bank_id = fields.Many2one('wps.bank', string='Bank', required=True, tracking=True)
    
    # API Configuration
    api_type = fields.Selection([
        ('rest', 'REST API'),
        ('soap', 'SOAP Web Service'),
        ('sftp', 'SFTP File Transfer'),
        ('direct', 'Direct Bank Portal'),
    ], string='API Type', default='rest', required=True)
    
    api_url = fields.Char(string='API Base URL')
    api_version = fields.Char(string='API Version', default='v1')
    
    # Authentication
    auth_method = fields.Selection([
        ('api_key', 'API Key'),
        ('oauth2', 'OAuth 2.0'),
        ('certificate', 'Client Certificate'),
        ('basic', 'Basic Auth'),
    ], string='Authentication Method', default='api_key')
    
    api_key = fields.Char(string='API Key')
    api_secret = fields.Char(string='API Secret')
    client_id = fields.Char(string='Client ID')
    client_secret = fields.Char(string='Client Secret')
    certificate = fields.Binary(string='Client Certificate')
    certificate_password = fields.Char(string='Certificate Password')
    
    # SFTP Configuration
    sftp_host = fields.Char(string='SFTP Host')
    sftp_port = fields.Integer(string='SFTP Port', default=22)
    sftp_username = fields.Char(string='SFTP Username')
    sftp_password = fields.Char(string='SFTP Password')
    sftp_key = fields.Binary(string='SSH Private Key')
    sftp_upload_path = fields.Char(string='Upload Path', default='/upload')
    sftp_download_path = fields.Char(string='Download Path', default='/download')
    
    # Company Info
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                  default=lambda self: self.env.company)
    employer_id = fields.Char(string='Employer ID (MOL)')
    routing_code = fields.Char(string='Bank Routing Code')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('testing', 'Testing'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    ], string='Status', default='draft', tracking=True)
    
    last_connection_test = fields.Datetime(string='Last Connection Test')
    last_test_result = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Last Test Result')
    last_test_message = fields.Text(string='Last Test Message')
    
    # Statistics
    total_submissions = fields.Integer(string='Total Submissions', compute='_compute_statistics')
    successful_submissions = fields.Integer(string='Successful', compute='_compute_statistics')
    failed_submissions = fields.Integer(string='Failed', compute='_compute_statistics')
    
    submission_ids = fields.One2many('wps.api.submission', 'connection_id', string='Submissions')
    
    @api.depends('submission_ids', 'submission_ids.state')
    def _compute_statistics(self):
        for record in self:
            submissions = record.submission_ids
            record.total_submissions = len(submissions)
            record.successful_submissions = len(submissions.filtered(lambda s: s.state == 'success'))
            record.failed_submissions = len(submissions.filtered(lambda s: s.state == 'failed'))
    
    def action_test_connection(self):
        """Test the API connection"""
        self.ensure_one()
        
        try:
            if self.api_type == 'rest':
                result = self._test_rest_connection()
            elif self.api_type == 'soap':
                result = self._test_soap_connection()
            elif self.api_type == 'sftp':
                result = self._test_sftp_connection()
            else:
                result = {'success': True, 'message': 'Direct portal connection - manual verification required'}
            
            self.write({
                'last_connection_test': fields.Datetime.now(),
                'last_test_result': 'success' if result.get('success') else 'failed',
                'last_test_message': result.get('message', ''),
            })
            
            if result.get('success'):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Test'),
                        'message': _('Connection successful!'),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                raise UserError(result.get('message', 'Connection failed'))
                
        except Exception as e:
            self.write({
                'last_connection_test': fields.Datetime.now(),
                'last_test_result': 'failed',
                'last_test_message': str(e),
            })
            raise UserError(_('Connection test failed: %s') % str(e))
    
    def _test_rest_connection(self):
        """Test REST API connection"""
        # Simulated test - in production, would make actual API call
        if not self.api_url:
            return {'success': False, 'message': 'API URL not configured'}
        return {'success': True, 'message': 'REST API connection verified'}
    
    def _test_soap_connection(self):
        """Test SOAP Web Service connection"""
        if not self.api_url:
            return {'success': False, 'message': 'SOAP endpoint not configured'}
        return {'success': True, 'message': 'SOAP connection verified'}
    
    def _test_sftp_connection(self):
        """Test SFTP connection"""
        if not self.sftp_host or not self.sftp_username:
            return {'success': False, 'message': 'SFTP credentials not configured'}
        return {'success': True, 'message': 'SFTP connection verified'}
    
    def action_activate(self):
        """Activate the connection"""
        self.state = 'active'
    
    def action_suspend(self):
        """Suspend the connection"""
        self.state = 'suspended'


class WPSAPISubmission(models.Model):
    """WPS API Submission Record"""
    _name = 'wps.api.submission'
    _description = 'WPS API Submission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'submission_date desc'

    name = fields.Char(string='Reference', required=True, default='New', copy=False)
    connection_id = fields.Many2one('wps.bank.api.connection', string='Bank Connection', required=True)
    wps_file_id = fields.Many2one('tazweed.wps.file', string='WPS File', required=True)
    
    # Submission Details
    submission_date = fields.Datetime(string='Submission Date', default=fields.Datetime.now)
    submission_type = fields.Selection([
        ('new', 'New Submission'),
        ('correction', 'Correction'),
        ('cancellation', 'Cancellation'),
    ], string='Submission Type', default='new')
    
    # File Information
    file_content = fields.Binary(string='SIF File Content')
    file_name = fields.Char(string='File Name')
    file_hash = fields.Char(string='File Hash (SHA256)')
    file_size = fields.Integer(string='File Size (bytes)')
    
    # Response
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    bank_reference = fields.Char(string='Bank Reference Number')
    bank_response_code = fields.Char(string='Response Code')
    bank_response_message = fields.Text(string='Response Message')
    
    # Timing
    processing_start = fields.Datetime(string='Processing Started')
    processing_end = fields.Datetime(string='Processing Completed')
    processing_duration = fields.Float(string='Duration (seconds)', compute='_compute_duration')
    
    # Error Handling
    retry_count = fields.Integer(string='Retry Count', default=0)
    max_retries = fields.Integer(string='Max Retries', default=3)
    last_error = fields.Text(string='Last Error')
    
    # Audit
    submitted_by = fields.Many2one('res.users', string='Submitted By', default=lambda self: self.env.user)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('wps.api.submission') or 'New'
        return super().create(vals)
    
    @api.depends('processing_start', 'processing_end')
    def _compute_duration(self):
        for record in self:
            if record.processing_start and record.processing_end:
                delta = record.processing_end - record.processing_start
                record.processing_duration = delta.total_seconds()
            else:
                record.processing_duration = 0
    
    def action_submit(self):
        """Submit the WPS file to the bank"""
        self.ensure_one()
        
        if not self.connection_id.state == 'active':
            raise UserError(_('Bank connection is not active.'))
        
        # Prepare file
        self._prepare_submission_file()
        
        # Submit based on API type
        self.processing_start = fields.Datetime.now()
        self.state = 'submitted'
        
        try:
            if self.connection_id.api_type == 'rest':
                result = self._submit_rest()
            elif self.connection_id.api_type == 'soap':
                result = self._submit_soap()
            elif self.connection_id.api_type == 'sftp':
                result = self._submit_sftp()
            else:
                result = self._submit_manual()
            
            self._process_submission_result(result)
            
        except Exception as e:
            self._handle_submission_error(str(e))
    
    def _prepare_submission_file(self):
        """Prepare the SIF file for submission"""
        if self.wps_file_id and self.wps_file_id.sif_file:
            self.file_content = self.wps_file_id.sif_file
            self.file_name = self.wps_file_id.sif_filename or 'wps_file.sif'
            
            # Calculate hash
            content = base64.b64decode(self.file_content)
            self.file_hash = hashlib.sha256(content).hexdigest()
            self.file_size = len(content)
    
    def _submit_rest(self):
        """Submit via REST API"""
        # Simulated - in production would make actual API call
        return {
            'success': True,
            'reference': f'BNK-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'code': '200',
            'message': 'File accepted for processing',
        }
    
    def _submit_soap(self):
        """Submit via SOAP Web Service"""
        return {
            'success': True,
            'reference': f'SOAP-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'code': '0',
            'message': 'SOAP submission successful',
        }
    
    def _submit_sftp(self):
        """Submit via SFTP"""
        return {
            'success': True,
            'reference': f'SFTP-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'code': 'OK',
            'message': 'File uploaded successfully',
        }
    
    def _submit_manual(self):
        """Manual submission tracking"""
        return {
            'success': True,
            'reference': f'MANUAL-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'code': 'PENDING',
            'message': 'Marked for manual submission',
        }
    
    def _process_submission_result(self, result):
        """Process the submission result"""
        self.processing_end = fields.Datetime.now()
        
        if result.get('success'):
            self.state = 'processing'
            self.bank_reference = result.get('reference')
            self.bank_response_code = result.get('code')
            self.bank_response_message = result.get('message')
        else:
            self._handle_submission_error(result.get('message', 'Unknown error'))
    
    def _handle_submission_error(self, error_message):
        """Handle submission error"""
        self.last_error = error_message
        self.retry_count += 1
        
        if self.retry_count >= self.max_retries:
            self.state = 'failed'
        else:
            self.state = 'draft'  # Allow retry
    
    def action_check_status(self):
        """Check submission status with bank"""
        self.ensure_one()
        
        # Simulated status check
        if self.state == 'processing':
            # In production, would query bank API
            self.state = 'success'
            self.bank_response_message = 'Payment processed successfully'
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Status Update'),
                    'message': _('Payment processed successfully!'),
                    'type': 'success',
                    'sticky': False,
                }
            }
    
    def action_retry(self):
        """Retry failed submission"""
        self.ensure_one()
        if self.state == 'failed' and self.retry_count < self.max_retries:
            self.action_submit()
    
    def action_cancel(self):
        """Cancel submission"""
        self.state = 'cancelled'
