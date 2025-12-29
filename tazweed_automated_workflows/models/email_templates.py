# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import json
import re


class WorkflowEmailTemplate(models.Model):
    """Workflow Email Template - Advanced email templates for workflows"""
    _name = 'workflow.email.template'
    _description = 'Workflow Email Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Template Name', required=True, tracking=True)
    description = fields.Text(string='Description')
    
    # Template Type
    template_type = fields.Selection([
        ('notification', 'Notification'),
        ('approval_request', 'Approval Request'),
        ('reminder', 'Reminder'),
        ('escalation', 'Escalation'),
        ('completion', 'Task Completion'),
        ('rejection', 'Rejection Notice'),
        ('welcome', 'Welcome Email'),
        ('confirmation', 'Confirmation'),
        ('alert', 'Alert'),
        ('report', 'Report'),
        ('custom', 'Custom'),
    ], string='Template Type', default='notification', required=True, tracking=True)
    
    # Email Content
    subject = fields.Char(string='Subject', required=True)
    body_html = fields.Html(string='Body (HTML)', sanitize_style=True)
    body_text = fields.Text(string='Body (Plain Text)')
    
    # Dynamic Content
    use_dynamic_content = fields.Boolean(string='Use Dynamic Content', default=True)
    dynamic_fields = fields.Text(string='Available Fields (JSON)', compute='_compute_dynamic_fields')
    
    # Model Reference
    model_id = fields.Many2one('ir.model', string='Related Model')
    model_name = fields.Char(string='Model Name', related='model_id.model')
    
    # Sender Configuration
    email_from = fields.Char(string='From Email', default='${object.company_id.email or "noreply@company.com"}')
    reply_to = fields.Char(string='Reply To')
    
    # Recipients
    recipient_type = fields.Selection([
        ('static', 'Static Email'),
        ('field', 'Field Value'),
        ('expression', 'Expression'),
        ('followers', 'Followers'),
        ('group', 'User Group'),
        ('role', 'Role-based'),
    ], string='Recipient Type', default='field')
    
    recipient_email = fields.Char(string='Recipient Email')
    recipient_field = fields.Char(string='Recipient Field', default='email')
    recipient_expression = fields.Text(string='Recipient Expression')
    recipient_group_id = fields.Many2one('res.groups', string='Recipient Group')
    
    # CC/BCC
    cc_emails = fields.Char(string='CC Emails')
    bcc_emails = fields.Char(string='BCC Emails')
    
    # Attachments
    attachment_ids = fields.Many2many('ir.attachment', string='Static Attachments')
    dynamic_attachment_field = fields.Char(string='Dynamic Attachment Field')
    include_report = fields.Boolean(string='Include Report')
    report_template_id = fields.Many2one('ir.actions.report', string='Report Template')
    
    # Scheduling
    send_immediately = fields.Boolean(string='Send Immediately', default=True)
    delay_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
    ], string='Delay Type')
    delay_value = fields.Integer(string='Delay Value')
    
    # Conditions
    condition_ids = fields.One2many('workflow.email.condition', 'template_id', string='Send Conditions')
    
    # Personalization
    personalization_ids = fields.One2many('workflow.email.personalization', 'template_id', string='Personalizations')
    
    # A/B Testing
    enable_ab_testing = fields.Boolean(string='Enable A/B Testing')
    variant_ids = fields.One2many('workflow.email.variant', 'template_id', string='Variants')
    
    # Tracking
    track_opens = fields.Boolean(string='Track Opens', default=True)
    track_clicks = fields.Boolean(string='Track Clicks', default=True)
    
    # Statistics
    sent_count = fields.Integer(string='Sent Count', readonly=True)
    open_count = fields.Integer(string='Open Count', readonly=True)
    click_count = fields.Integer(string='Click Count', readonly=True)
    open_rate = fields.Float(string='Open Rate (%)', compute='_compute_rates')
    click_rate = fields.Float(string='Click Rate (%)', compute='_compute_rates')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('model_id')
    def _compute_dynamic_fields(self):
        for record in self:
            if record.model_id:
                model = self.env[record.model_id.model]
                fields_info = []
                for field_name, field_obj in model._fields.items():
                    fields_info.append({
                        'name': field_name,
                        'string': field_obj.string,
                        'type': field_obj.type,
                        'placeholder': '${object.' + field_name + '}'
                    })
                record.dynamic_fields = json.dumps(fields_info[:50])  # Limit to 50 fields
            else:
                record.dynamic_fields = '[]'
    
    @api.depends('sent_count', 'open_count', 'click_count')
    def _compute_rates(self):
        for record in self:
            record.open_rate = (record.open_count / record.sent_count * 100) if record.sent_count > 0 else 0
            record.click_rate = (record.click_count / record.sent_count * 100) if record.sent_count > 0 else 0
    
    def action_activate(self):
        """Activate the template"""
        self.write({'state': 'active'})
    
    def action_pause(self):
        """Pause the template"""
        self.write({'state': 'paused'})
    
    def action_archive(self):
        """Archive the template"""
        self.write({'state': 'archived', 'active': False})
    
    def render_template(self, record):
        """Render the template for a specific record"""
        self.ensure_one()
        
        # Create evaluation context
        context = {
            'object': record,
            'user': self.env.user,
            'company': self.env.company,
            'date': fields.Date.today(),
            'datetime': fields.Datetime.now(),
        }
        
        # Render subject
        subject = self._render_string(self.subject, context)
        
        # Render body
        body_html = self._render_string(self.body_html or '', context)
        body_text = self._render_string(self.body_text or '', context)
        
        # Get recipients
        recipients = self._get_recipients(record)
        
        return {
            'subject': subject,
            'body_html': body_html,
            'body_text': body_text,
            'email_from': self._render_string(self.email_from, context),
            'email_to': recipients,
            'email_cc': self.cc_emails,
            'email_bcc': self.bcc_emails,
        }
    
    def _render_string(self, template_string, context):
        """Render a string with dynamic placeholders"""
        if not template_string:
            return ''
        
        # Simple placeholder replacement ${object.field}
        def replace_placeholder(match):
            expression = match.group(1)
            try:
                parts = expression.split('.')
                value = context
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = getattr(value, part, '')
                return str(value) if value else ''
            except:
                return ''
        
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_placeholder, template_string)
    
    def _get_recipients(self, record):
        """Get recipient emails based on configuration"""
        self.ensure_one()
        
        if self.recipient_type == 'static':
            return self.recipient_email
        elif self.recipient_type == 'field':
            return getattr(record, self.recipient_field, '') if hasattr(record, self.recipient_field) else ''
        elif self.recipient_type == 'followers':
            followers = record.message_follower_ids.mapped('partner_id.email')
            return ','.join(filter(None, followers))
        elif self.recipient_type == 'group':
            users = self.recipient_group_id.users
            return ','.join(filter(None, users.mapped('email')))
        
        return ''
    
    def send_email(self, record):
        """Send email for a specific record"""
        self.ensure_one()
        
        if self.state != 'active':
            raise UserError("Template is not active.")
        
        # Check conditions
        if not self._check_conditions(record):
            return False
        
        # Render template
        email_data = self.render_template(record)
        
        # Create and send email
        mail = self.env['mail.mail'].create({
            'subject': email_data['subject'],
            'body_html': email_data['body_html'],
            'email_from': email_data['email_from'],
            'email_to': email_data['email_to'],
            'email_cc': email_data['email_cc'],
            'attachment_ids': [(6, 0, self.attachment_ids.ids)],
        })
        
        mail.send()
        
        # Update statistics
        self.sudo().write({'sent_count': self.sent_count + 1})
        
        return True
    
    def _check_conditions(self, record):
        """Check if all conditions are met"""
        for condition in self.condition_ids:
            if not condition.evaluate(record):
                return False
        return True
    
    def action_preview(self):
        """Preview the email template"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Email Preview',
            'res_model': 'workflow.email.preview',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_template_id': self.id}
        }
    
    def action_send_test(self):
        """Send a test email"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send Test Email',
            'res_model': 'workflow.email.test.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_template_id': self.id}
        }


class WorkflowEmailCondition(models.Model):
    """Workflow Email Condition - Conditions for sending emails"""
    _name = 'workflow.email.condition'
    _description = 'Workflow Email Condition'
    _order = 'sequence'

    template_id = fields.Many2one('workflow.email.template', string='Template', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    field_name = fields.Char(string='Field Name', required=True)
    operator = fields.Selection([
        ('=', 'Equals'),
        ('!=', 'Not Equals'),
        ('>', 'Greater Than'),
        ('<', 'Less Than'),
        ('in', 'In'),
        ('not in', 'Not In'),
        ('set', 'Is Set'),
        ('not_set', 'Is Not Set'),
    ], string='Operator', default='=', required=True)
    value = fields.Char(string='Value')
    
    def evaluate(self, record):
        """Evaluate the condition against a record"""
        self.ensure_one()
        
        field_value = getattr(record, self.field_name, None) if hasattr(record, self.field_name) else None
        
        if self.operator == '=':
            return str(field_value) == self.value
        elif self.operator == '!=':
            return str(field_value) != self.value
        elif self.operator == 'set':
            return bool(field_value)
        elif self.operator == 'not_set':
            return not bool(field_value)
        
        return True


class WorkflowEmailPersonalization(models.Model):
    """Workflow Email Personalization - Dynamic content blocks"""
    _name = 'workflow.email.personalization'
    _description = 'Workflow Email Personalization'
    _order = 'sequence'

    template_id = fields.Many2one('workflow.email.template', string='Template', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    name = fields.Char(string='Block Name', required=True)
    placeholder = fields.Char(string='Placeholder', required=True)
    
    content_type = fields.Selection([
        ('text', 'Text'),
        ('html', 'HTML'),
        ('image', 'Image'),
        ('button', 'Button'),
    ], string='Content Type', default='text')
    
    default_content = fields.Text(string='Default Content')
    
    # Conditional Content
    condition_field = fields.Char(string='Condition Field')
    condition_value = fields.Char(string='Condition Value')
    conditional_content = fields.Text(string='Conditional Content')


class WorkflowEmailVariant(models.Model):
    """Workflow Email Variant - A/B Testing variants"""
    _name = 'workflow.email.variant'
    _description = 'Workflow Email Variant'

    template_id = fields.Many2one('workflow.email.template', string='Template', required=True, ondelete='cascade')
    name = fields.Char(string='Variant Name', required=True)
    
    subject = fields.Char(string='Subject')
    body_html = fields.Html(string='Body (HTML)')
    
    weight = fields.Integer(string='Weight (%)', default=50)
    
    # Statistics
    sent_count = fields.Integer(string='Sent Count', readonly=True)
    open_count = fields.Integer(string='Open Count', readonly=True)
    click_count = fields.Integer(string='Click Count', readonly=True)


class WorkflowEmailLog(models.Model):
    """Workflow Email Log - Track sent emails"""
    _name = 'workflow.email.log'
    _description = 'Workflow Email Log'
    _order = 'sent_date desc'

    template_id = fields.Many2one('workflow.email.template', string='Template', required=True)
    variant_id = fields.Many2one('workflow.email.variant', string='Variant')
    
    # Record Reference
    model = fields.Char(string='Model')
    res_id = fields.Integer(string='Record ID')
    
    # Email Details
    email_from = fields.Char(string='From')
    email_to = fields.Char(string='To')
    subject = fields.Char(string='Subject')
    
    # Status
    state = fields.Selection([
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
    ], string='Status', default='sent')
    
    # Timestamps
    sent_date = fields.Datetime(string='Sent Date', default=fields.Datetime.now)
    opened_date = fields.Datetime(string='Opened Date')
    clicked_date = fields.Datetime(string='Clicked Date')
    
    # Tracking
    tracking_id = fields.Char(string='Tracking ID')
    user_agent = fields.Char(string='User Agent')
    ip_address = fields.Char(string='IP Address')
