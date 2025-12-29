# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import json
import hashlib
import hmac
import requests
import logging

_logger = logging.getLogger(__name__)


class WorkflowWebhook(models.Model):
    """Workflow Webhook - Outgoing webhook configuration"""
    _name = 'workflow.webhook'
    _description = 'Workflow Webhook'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Webhook Name', required=True, tracking=True)
    description = fields.Text(string='Description')
    
    # Webhook Type
    webhook_type = fields.Selection([
        ('outgoing', 'Outgoing (Send Data)'),
        ('incoming', 'Incoming (Receive Data)'),
    ], string='Webhook Type', default='outgoing', required=True)
    
    # URL Configuration
    url = fields.Char(string='Webhook URL', required=True)
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ], string='HTTP Method', default='POST', required=True)
    
    # Authentication
    auth_type = fields.Selection([
        ('none', 'No Authentication'),
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
        ('api_key', 'API Key'),
        ('oauth2', 'OAuth 2.0'),
        ('hmac', 'HMAC Signature'),
    ], string='Authentication Type', default='none')
    
    auth_username = fields.Char(string='Username')
    auth_password = fields.Char(string='Password')
    auth_token = fields.Char(string='Bearer Token')
    api_key_name = fields.Char(string='API Key Name', default='X-API-Key')
    api_key_value = fields.Char(string='API Key Value')
    api_key_location = fields.Selection([
        ('header', 'Header'),
        ('query', 'Query Parameter'),
    ], string='API Key Location', default='header')
    
    # HMAC Configuration
    hmac_secret = fields.Char(string='HMAC Secret')
    hmac_algorithm = fields.Selection([
        ('sha1', 'SHA-1'),
        ('sha256', 'SHA-256'),
        ('sha512', 'SHA-512'),
    ], string='HMAC Algorithm', default='sha256')
    hmac_header = fields.Char(string='HMAC Header Name', default='X-Signature')
    
    # Headers
    header_ids = fields.One2many('workflow.webhook.header', 'webhook_id', string='Custom Headers')
    content_type = fields.Selection([
        ('application/json', 'JSON'),
        ('application/x-www-form-urlencoded', 'Form URL Encoded'),
        ('multipart/form-data', 'Multipart Form Data'),
        ('text/xml', 'XML'),
        ('text/plain', 'Plain Text'),
    ], string='Content Type', default='application/json')
    
    # Payload Configuration
    payload_type = fields.Selection([
        ('full_record', 'Full Record'),
        ('selected_fields', 'Selected Fields'),
        ('custom', 'Custom Payload'),
        ('template', 'Template'),
    ], string='Payload Type', default='full_record')
    
    model_id = fields.Many2one('ir.model', string='Source Model')
    model_name = fields.Char(string='Model Name', related='model_id.model')
    
    selected_field_ids = fields.Many2many('ir.model.fields', string='Selected Fields',
                                          domain="[('model_id', '=', model_id)]")
    custom_payload = fields.Text(string='Custom Payload (JSON)')
    payload_template = fields.Text(string='Payload Template')
    
    # Trigger Configuration
    trigger_type = fields.Selection([
        ('manual', 'Manual'),
        ('create', 'On Create'),
        ('write', 'On Update'),
        ('unlink', 'On Delete'),
        ('workflow', 'Workflow Action'),
        ('scheduled', 'Scheduled'),
    ], string='Trigger Type', default='manual')
    
    trigger_field_ids = fields.Many2many('ir.model.fields', 'webhook_trigger_fields_rel',
                                         string='Trigger on Field Change',
                                         domain="[('model_id', '=', model_id)]")
    
    # Retry Configuration
    retry_enabled = fields.Boolean(string='Enable Retry', default=True)
    max_retries = fields.Integer(string='Max Retries', default=3)
    retry_delay = fields.Integer(string='Retry Delay (seconds)', default=60)
    retry_backoff = fields.Selection([
        ('linear', 'Linear'),
        ('exponential', 'Exponential'),
    ], string='Retry Backoff', default='exponential')
    
    # Timeout
    timeout = fields.Integer(string='Timeout (seconds)', default=30)
    
    # Response Handling
    expected_status_codes = fields.Char(string='Expected Status Codes', default='200,201,202')
    response_handling = fields.Selection([
        ('ignore', 'Ignore Response'),
        ('log', 'Log Response'),
        ('process', 'Process Response'),
    ], string='Response Handling', default='log')
    
    response_field_mapping = fields.Text(string='Response Field Mapping (JSON)')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('error', 'Error'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    
    active = fields.Boolean(string='Active', default=True)
    
    # Statistics
    total_calls = fields.Integer(string='Total Calls', readonly=True)
    successful_calls = fields.Integer(string='Successful Calls', readonly=True)
    failed_calls = fields.Integer(string='Failed Calls', readonly=True)
    success_rate = fields.Float(string='Success Rate (%)', compute='_compute_success_rate')
    last_call_date = fields.Datetime(string='Last Call Date', readonly=True)
    last_status_code = fields.Integer(string='Last Status Code', readonly=True)
    
    # Logs
    log_ids = fields.One2many('workflow.webhook.log', 'webhook_id', string='Logs')
    
    @api.depends('total_calls', 'successful_calls')
    def _compute_success_rate(self):
        for record in self:
            record.success_rate = (record.successful_calls / record.total_calls * 100) if record.total_calls > 0 else 0
    
    def action_activate(self):
        """Activate the webhook"""
        self.write({'state': 'active'})
    
    def action_pause(self):
        """Pause the webhook"""
        self.write({'state': 'paused'})
    
    def action_test(self):
        """Test the webhook with sample data"""
        self.ensure_one()
        
        # Create test payload
        test_payload = {'test': True, 'message': 'Webhook test from Tazweed'}
        
        try:
            response = self._send_request(test_payload)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Webhook Test',
                    'message': f'Test successful! Status: {response.status_code}',
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Webhook Test Failed',
                    'message': str(e),
                    'type': 'danger',
                }
            }
    
    def execute(self, record=None, context=None):
        """Execute the webhook"""
        self.ensure_one()
        
        if self.state != 'active':
            _logger.warning(f"Webhook {self.name} is not active")
            return False
        
        # Build payload
        payload = self._build_payload(record, context)
        
        # Send request
        try:
            response = self._send_request(payload)
            self._log_call(payload, response, 'success')
            
            # Process response if needed
            if self.response_handling == 'process':
                self._process_response(response, record)
            
            return True
        except Exception as e:
            self._log_call(payload, None, 'error', str(e))
            
            if self.retry_enabled:
                self._schedule_retry(payload, 1)
            
            return False
    
    def _build_payload(self, record, context=None):
        """Build the webhook payload"""
        context = context or {}
        
        if self.payload_type == 'full_record' and record:
            return record.read()[0] if hasattr(record, 'read') else {}
        elif self.payload_type == 'selected_fields' and record:
            field_names = self.selected_field_ids.mapped('name')
            return record.read(field_names)[0] if hasattr(record, 'read') else {}
        elif self.payload_type == 'custom':
            return json.loads(self.custom_payload or '{}')
        elif self.payload_type == 'template':
            return self._render_template(record, context)
        
        return {}
    
    def _render_template(self, record, context):
        """Render payload template"""
        if not self.payload_template:
            return {}
        
        # Simple template rendering
        template = self.payload_template
        if record:
            for field_name in dir(record):
                if not field_name.startswith('_'):
                    try:
                        value = getattr(record, field_name)
                        if not callable(value):
                            template = template.replace(f'${{{field_name}}}', str(value))
                    except:
                        pass
        
        return json.loads(template)
    
    def _send_request(self, payload):
        """Send the HTTP request"""
        headers = self._build_headers(payload)
        auth = self._build_auth()
        
        # Prepare payload
        if self.content_type == 'application/json':
            data = None
            json_data = payload
        else:
            data = payload
            json_data = None
        
        response = requests.request(
            method=self.method,
            url=self.url,
            headers=headers,
            auth=auth,
            json=json_data,
            data=data,
            timeout=self.timeout
        )
        
        # Check status code
        expected_codes = [int(c.strip()) for c in self.expected_status_codes.split(',')]
        if response.status_code not in expected_codes:
            raise Exception(f"Unexpected status code: {response.status_code}")
        
        # Update statistics
        self.sudo().write({
            'total_calls': self.total_calls + 1,
            'successful_calls': self.successful_calls + 1,
            'last_call_date': fields.Datetime.now(),
            'last_status_code': response.status_code,
        })
        
        return response
    
    def _build_headers(self, payload):
        """Build request headers"""
        headers = {
            'Content-Type': self.content_type,
        }
        
        # Add custom headers
        for header in self.header_ids:
            headers[header.name] = header.value
        
        # Add API key header
        if self.auth_type == 'api_key' and self.api_key_location == 'header':
            headers[self.api_key_name] = self.api_key_value
        
        # Add HMAC signature
        if self.auth_type == 'hmac':
            signature = self._generate_hmac_signature(json.dumps(payload))
            headers[self.hmac_header] = signature
        
        return headers
    
    def _build_auth(self):
        """Build authentication"""
        if self.auth_type == 'basic':
            return (self.auth_username, self.auth_password)
        return None
    
    def _generate_hmac_signature(self, payload):
        """Generate HMAC signature"""
        if self.hmac_algorithm == 'sha1':
            algo = hashlib.sha1
        elif self.hmac_algorithm == 'sha256':
            algo = hashlib.sha256
        else:
            algo = hashlib.sha512
        
        signature = hmac.new(
            self.hmac_secret.encode(),
            payload.encode(),
            algo
        ).hexdigest()
        
        return signature
    
    def _process_response(self, response, record):
        """Process webhook response"""
        if not self.response_field_mapping or not record:
            return
        
        try:
            response_data = response.json()
            mapping = json.loads(self.response_field_mapping)
            
            update_vals = {}
            for response_field, record_field in mapping.items():
                if response_field in response_data:
                    update_vals[record_field] = response_data[response_field]
            
            if update_vals:
                record.write(update_vals)
        except:
            pass
    
    def _log_call(self, payload, response, status, error_message=None):
        """Log the webhook call"""
        self.env['workflow.webhook.log'].create({
            'webhook_id': self.id,
            'request_payload': json.dumps(payload, default=str),
            'response_body': response.text if response else None,
            'status_code': response.status_code if response else None,
            'status': status,
            'error_message': error_message,
        })
    
    def _schedule_retry(self, payload, attempt):
        """Schedule a retry"""
        if attempt > self.max_retries:
            return
        
        delay = self.retry_delay
        if self.retry_backoff == 'exponential':
            delay = self.retry_delay * (2 ** (attempt - 1))
        
        # Schedule retry using ir.cron or queue job
        # Implementation depends on available job queue system


class WorkflowWebhookHeader(models.Model):
    """Workflow Webhook Header - Custom headers for webhooks"""
    _name = 'workflow.webhook.header'
    _description = 'Workflow Webhook Header'
    _order = 'sequence'

    webhook_id = fields.Many2one('workflow.webhook', string='Webhook', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    name = fields.Char(string='Header Name', required=True)
    value = fields.Char(string='Header Value', required=True)


class WorkflowWebhookLog(models.Model):
    """Workflow Webhook Log - Log of webhook calls"""
    _name = 'workflow.webhook.log'
    _description = 'Workflow Webhook Log'
    _order = 'call_date desc'

    webhook_id = fields.Many2one('workflow.webhook', string='Webhook', required=True, ondelete='cascade')
    
    # Request Details
    request_payload = fields.Text(string='Request Payload')
    request_headers = fields.Text(string='Request Headers')
    
    # Response Details
    response_body = fields.Text(string='Response Body')
    response_headers = fields.Text(string='Response Headers')
    status_code = fields.Integer(string='Status Code')
    
    # Status
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('retry', 'Retry'),
    ], string='Status')
    
    error_message = fields.Text(string='Error Message')
    
    # Timing
    call_date = fields.Datetime(string='Call Date', default=fields.Datetime.now)
    response_time = fields.Float(string='Response Time (ms)')
    
    # Retry Info
    retry_attempt = fields.Integer(string='Retry Attempt', default=0)


class WorkflowIncomingWebhook(models.Model):
    """Workflow Incoming Webhook - Receive external webhook calls"""
    _name = 'workflow.incoming.webhook'
    _description = 'Workflow Incoming Webhook'
    _order = 'name'

    name = fields.Char(string='Webhook Name', required=True)
    description = fields.Text(string='Description')
    
    # Endpoint Configuration
    endpoint_token = fields.Char(string='Endpoint Token', readonly=True, 
                                  default=lambda self: self._generate_token())
    endpoint_url = fields.Char(string='Endpoint URL', compute='_compute_endpoint_url')
    
    # Security
    require_signature = fields.Boolean(string='Require Signature')
    signature_secret = fields.Char(string='Signature Secret')
    signature_header = fields.Char(string='Signature Header', default='X-Signature')
    
    allowed_ips = fields.Text(string='Allowed IPs (one per line)')
    
    # Processing
    target_model_id = fields.Many2one('ir.model', string='Target Model')
    action_type = fields.Selection([
        ('create', 'Create Record'),
        ('update', 'Update Record'),
        ('method', 'Call Method'),
        ('workflow', 'Trigger Workflow'),
    ], string='Action Type', default='create')
    
    field_mapping = fields.Text(string='Field Mapping (JSON)')
    target_method = fields.Char(string='Target Method')
    workflow_id = fields.Many2one('tazweed.workflow.definition', string='Workflow')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
    ], string='Status', default='draft')
    
    active = fields.Boolean(string='Active', default=True)
    
    # Statistics
    total_received = fields.Integer(string='Total Received', readonly=True)
    successful_processed = fields.Integer(string='Successfully Processed', readonly=True)
    failed_processed = fields.Integer(string='Failed', readonly=True)
    
    def _generate_token(self):
        """Generate a unique endpoint token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @api.depends('endpoint_token')
    def _compute_endpoint_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            record.endpoint_url = f"{base_url}/api/webhook/{record.endpoint_token}"
    
    def process_incoming(self, payload, headers=None):
        """Process incoming webhook payload"""
        self.ensure_one()
        
        if self.state != 'active':
            raise ValidationError("Webhook endpoint is not active")
        
        # Verify signature if required
        if self.require_signature:
            signature = headers.get(self.signature_header) if headers else None
            if not self._verify_signature(payload, signature):
                raise ValidationError("Invalid signature")
        
        # Process based on action type
        try:
            if self.action_type == 'create':
                return self._create_record(payload)
            elif self.action_type == 'update':
                return self._update_record(payload)
            elif self.action_type == 'method':
                return self._call_method(payload)
            elif self.action_type == 'workflow':
                return self._trigger_workflow(payload)
        except Exception as e:
            self.sudo().write({'failed_processed': self.failed_processed + 1})
            raise
        
        self.sudo().write({
            'total_received': self.total_received + 1,
            'successful_processed': self.successful_processed + 1,
        })
    
    def _verify_signature(self, payload, signature):
        """Verify the webhook signature"""
        if not signature or not self.signature_secret:
            return False
        
        expected = hmac.new(
            self.signature_secret.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
    
    def _create_record(self, payload):
        """Create a new record from payload"""
        if not self.target_model_id:
            raise ValidationError("Target model not configured")
        
        mapping = json.loads(self.field_mapping or '{}')
        values = {}
        
        for payload_field, model_field in mapping.items():
            if payload_field in payload:
                values[model_field] = payload[payload_field]
        
        return self.env[self.target_model_id.model].create(values)
    
    def _update_record(self, payload):
        """Update existing record from payload"""
        # Implementation for update
        pass
    
    def _call_method(self, payload):
        """Call a method on the target model"""
        if not self.target_model_id or not self.target_method:
            raise ValidationError("Target model or method not configured")
        
        model = self.env[self.target_model_id.model]
        if hasattr(model, self.target_method):
            return getattr(model, self.target_method)(payload)
        
        raise ValidationError(f"Method {self.target_method} not found")
    
    def _trigger_workflow(self, payload):
        """Trigger a workflow"""
        if not self.workflow_id:
            raise ValidationError("Workflow not configured")
        
        # Trigger workflow execution
        return self.workflow_id.execute(payload)
