# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import hashlib
import secrets


class ClientRequestType(models.Model):
    """Client Request Type Configuration"""
    _name = 'client.request.type'
    _description = 'Client Request Type'
    _order = 'category, sequence, name'

    name = fields.Char(string='Request Type', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    category = fields.Selection([
        ('invoice', 'Invoice & Billing'),
        ('worker', 'Worker Management'),
        ('document', 'Documents'),
        ('service', 'Services'),
        ('support', 'Support'),
        ('feedback', 'Feedback'),
    ], string='Category', required=True, default='service')
    
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Processing Configuration
    requires_approval = fields.Boolean(string='Requires Approval', default=True)
    approval_type = fields.Selection([
        ('none', 'No Approval Required'),
        ('account_manager', 'Account Manager Only'),
        ('finance', 'Finance Team Only'),
        ('operations', 'Operations Team Only'),
        ('manager', 'Department Manager'),
        ('both', 'Account Manager + Department'),
    ], string='Approval Type', default='account_manager')
    
    # SLA Configuration
    sla_days = fields.Integer(string='SLA (Days)', default=3, 
                              help='Expected processing time in business days')
    priority_sla_days = fields.Integer(string='Priority SLA (Days)', default=1,
                                       help='SLA for urgent/priority requests')
    
    # Notification Settings
    notify_account_manager = fields.Boolean(string='Notify Account Manager', default=True)
    notify_finance = fields.Boolean(string='Notify Finance Team', default=False)
    notify_operations = fields.Boolean(string='Notify Operations Team', default=False)
    
    # Form Configuration
    requires_attachment = fields.Boolean(string='Requires Attachment', default=False)
    requires_worker_selection = fields.Boolean(string='Requires Worker Selection', default=False)
    requires_invoice_selection = fields.Boolean(string='Requires Invoice Selection', default=False)
    requires_amount = fields.Boolean(string='Requires Amount', default=False)
    requires_date_range = fields.Boolean(string='Requires Date Range', default=False)
    
    # Template
    response_template = fields.Html(string='Response Template',
                                    help='Default response template for this request type')
    
    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Request type code must be unique!')
    ]


class ClientRequest(models.Model):
    """Client Request Management"""
    _name = 'client.request'
    _description = 'Client Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'reference'

    # Basic Information
    reference = fields.Char(string='Reference', required=True, copy=False, 
                           readonly=True, default='New')
    client_id = fields.Many2one('tazweed.client', string='Client', required=True,
                                tracking=True, ondelete='cascade')
    portal_user_id = fields.Many2one('client.portal.user', string='Submitted By',
                                     tracking=True)
    request_type_id = fields.Many2one('client.request.type', string='Request Type',
                                      required=True, tracking=True)
    
    # Request Details
    subject = fields.Char(string='Subject', required=True, tracking=True)
    description = fields.Html(string='Description', required=True)
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal', required=True, tracking=True)
    
    # Category (from request type)
    category = fields.Selection(related='request_type_id.category', store=True)
    
    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('pending_info', 'Pending Information'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Related Records
    worker_ids = fields.Many2many('hr.employee', string='Related Workers',
                                  help='Workers related to this request')
    invoice_id = fields.Many2one('account.move', string='Related Invoice',
                                 domain="[('partner_id', '=', client_id)]")
    placement_ids = fields.Many2many('tazweed.placement', string='Related Placements')
    
    # Financial Information
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    
    # Date Range
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    
    # Attachments
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    attachment_count = fields.Integer(compute='_compute_attachment_count')
    
    # Processing Information
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    assigned_team = fields.Selection([
        ('account', 'Account Management'),
        ('finance', 'Finance'),
        ('operations', 'Operations'),
        ('hr', 'Human Resources'),
        ('support', 'Support'),
    ], string='Assigned Team', tracking=True)
    
    # Dates
    submitted_date = fields.Datetime(string='Submitted Date', readonly=True)
    expected_date = fields.Date(string='Expected Completion', compute='_compute_expected_date', store=True)
    completed_date = fields.Datetime(string='Completed Date', readonly=True)
    
    # Response
    response = fields.Html(string='Response')
    response_attachment_ids = fields.Many2many('ir.attachment', 'client_request_response_attachment_rel',
                                               'request_id', 'attachment_id', string='Response Attachments')
    
    # SLA Tracking
    sla_status = fields.Selection([
        ('on_track', 'On Track'),
        ('at_risk', 'At Risk'),
        ('overdue', 'Overdue'),
    ], string='SLA Status', compute='_compute_sla_status', store=True)
    
    # Feedback
    rating = fields.Selection([
        ('1', '1 - Very Poor'),
        ('2', '2 - Poor'),
        ('3', '3 - Average'),
        ('4', '4 - Good'),
        ('5', '5 - Excellent'),
    ], string='Rating')
    feedback = fields.Text(string='Feedback')
    
    # Internal Notes
    internal_notes = fields.Text(string='Internal Notes')
    
    # Tracking
    access_token = fields.Char(string='Access Token', copy=False)
    
    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for record in self:
            record.attachment_count = len(record.attachment_ids)
    
    def action_view_attachments(self):
        """View all attachments for this request"""
        self.ensure_one()
        return {
            'name': _('Attachments'),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'tree,form',
            'domain': [('res_model', '=', 'client.request'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'client.request', 'default_res_id': self.id},
        }
    
    @api.depends('submitted_date', 'request_type_id', 'priority')
    def _compute_expected_date(self):
        for record in self:
            if record.submitted_date and record.request_type_id:
                if record.priority in ['high', 'urgent']:
                    days = record.request_type_id.priority_sla_days
                else:
                    days = record.request_type_id.sla_days
                record.expected_date = (record.submitted_date + timedelta(days=days)).date()
            else:
                record.expected_date = False
    
    @api.depends('expected_date', 'state')
    def _compute_sla_status(self):
        today = fields.Date.today()
        for record in self:
            if record.state in ['completed', 'rejected', 'cancelled']:
                record.sla_status = False
            elif not record.expected_date:
                record.sla_status = 'on_track'
            elif today > record.expected_date:
                record.sla_status = 'overdue'
            elif today >= record.expected_date - timedelta(days=1):
                record.sla_status = 'at_risk'
            else:
                record.sla_status = 'on_track'
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('client.request') or 'New'
            vals['access_token'] = secrets.token_urlsafe(32)
        return super().create(vals_list)
    
    def action_submit(self):
        """Submit request for processing"""
        self.ensure_one()
        if not self.description:
            raise UserError(_('Please provide a description for your request.'))
        
        self.write({
            'state': 'submitted',
            'submitted_date': fields.Datetime.now(),
        })
        
        # Auto-assign based on request type
        self._auto_assign()
        
        # Send notifications
        self._send_submission_notification()
        
        # Log activity
        self.message_post(
            body=_('Request submitted by client.'),
            message_type='notification',
        )
        return True
    
    def action_review(self):
        """Mark as under review"""
        self.ensure_one()
        self.write({'state': 'under_review'})
        self._notify_client('review')
        return True
    
    def action_request_info(self):
        """Request additional information from client"""
        self.ensure_one()
        self.write({'state': 'pending_info'})
        self._notify_client('info_needed')
        return True
    
    def action_approve(self):
        """Approve the request"""
        self.ensure_one()
        self.write({'state': 'approved'})
        self._notify_client('approved')
        return True
    
    def action_start_processing(self):
        """Start processing the request"""
        self.ensure_one()
        self.write({'state': 'in_progress'})
        return True
    
    def action_complete(self):
        """Complete the request"""
        self.ensure_one()
        self.write({
            'state': 'completed',
            'completed_date': fields.Datetime.now(),
        })
        self._notify_client('completed')
        return True
    
    def action_reject(self):
        """Reject the request"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Request'),
            'res_model': 'client.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }
    
    def action_cancel(self):
        """Cancel the request"""
        self.ensure_one()
        self.write({'state': 'cancelled'})
        return True
    
    def action_reopen(self):
        """Reopen a closed request"""
        self.ensure_one()
        if self.state in ['completed', 'rejected', 'cancelled']:
            self.write({'state': 'submitted'})
        return True
    
    def _auto_assign(self):
        """Auto-assign request based on type and category"""
        self.ensure_one()
        request_type = self.request_type_id
        
        # Determine team based on category
        team_mapping = {
            'invoice': 'finance',
            'worker': 'operations',
            'document': 'account',
            'service': 'operations',
            'support': 'support',
            'feedback': 'account',
        }
        self.assigned_team = team_mapping.get(self.category, 'account')
        
        # Try to find account manager for the client
        if self.client_id.user_id:
            self.assigned_to = self.client_id.user_id
    
    def _send_submission_notification(self):
        """Send notification when request is submitted"""
        self.ensure_one()
        request_type = self.request_type_id
        
        # Notify account manager
        if request_type.notify_account_manager and self.client_id.user_id:
            self._send_internal_notification(
                self.client_id.user_id,
                _('New Client Request: %s') % self.reference,
                _('Client %s has submitted a new request: %s') % (self.client_id.name, self.subject)
            )
    
    def _send_internal_notification(self, user, subject, body):
        """Send internal notification to user"""
        self.message_post(
            partner_ids=[user.partner_id.id],
            subject=subject,
            body=body,
            message_type='notification',
        )
    
    def _notify_client(self, notification_type):
        """Send notification to client"""
        self.ensure_one()
        # Create portal notification
        self.env['client.portal.notification'].create({
            'client_id': self.client_id.id,
            'title': _('Request Update: %s') % self.reference,
            'message': self._get_notification_message(notification_type),
            'notification_type': 'request',
            'reference_model': 'client.request',
            'reference_id': self.id,
        })
    
    def _get_notification_message(self, notification_type):
        """Get notification message based on type"""
        messages = {
            'review': _('Your request is now under review by our team.'),
            'info_needed': _('We need additional information to process your request. Please check and respond.'),
            'approved': _('Your request has been approved and will be processed shortly.'),
            'completed': _('Your request has been completed. Please review and provide feedback.'),
            'rejected': _('Your request has been rejected. Please check the response for details.'),
        }
        return messages.get(notification_type, _('Your request status has been updated.'))


class ClientRequestRejectWizard(models.TransientModel):
    """Wizard for rejecting client requests"""
    _name = 'client.request.reject.wizard'
    _description = 'Reject Client Request Wizard'

    request_id = fields.Many2one('client.request', string='Request', required=True)
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_reject(self):
        """Confirm rejection"""
        self.ensure_one()
        self.request_id.write({
            'state': 'rejected',
            'response': _('<p><strong>Rejection Reason:</strong></p><p>%s</p>') % self.reason,
            'completed_date': fields.Datetime.now(),
        })
        self.request_id._notify_client('rejected')
        return {'type': 'ir.actions.act_window_close'}


class ClientInvoiceRequest(models.Model):
    """Specialized model for invoice-related requests"""
    _name = 'client.invoice.request'
    _description = 'Client Invoice Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    reference = fields.Char(string='Reference', required=True, copy=False,
                           readonly=True, default='New')
    client_id = fields.Many2one('tazweed.client', string='Client', required=True)
    
    request_type = fields.Selection([
        ('copy', 'Invoice Copy'),
        ('correction', 'Invoice Correction'),
        ('credit_note', 'Credit Note Request'),
        ('payment_extension', 'Payment Extension'),
        ('payment_plan', 'Payment Plan'),
        ('statement', 'Account Statement'),
        ('receipt', 'Payment Receipt'),
        ('tax_certificate', 'Tax Certificate'),
    ], string='Request Type', required=True)
    
    invoice_ids = fields.Many2many('account.move', string='Related Invoices')
    
    # For corrections
    correction_details = fields.Html(string='Correction Details')
    
    # For payment extension
    current_due_date = fields.Date(string='Current Due Date')
    requested_due_date = fields.Date(string='Requested Due Date')
    extension_reason = fields.Text(string='Reason for Extension')
    
    # For payment plan
    total_amount = fields.Monetary(string='Total Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    installment_count = fields.Integer(string='Number of Installments')
    
    # For statement
    statement_from = fields.Date(string='Statement From')
    statement_to = fields.Date(string='Statement To')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    
    response = fields.Html(string='Response')
    response_attachment_ids = fields.Many2many('ir.attachment', string='Response Documents')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('client.invoice.request') or 'New'
        return super().create(vals_list)


class ClientWorkerRequest(models.Model):
    """Specialized model for worker-related requests"""
    _name = 'client.worker.request'
    _description = 'Client Worker Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    reference = fields.Char(string='Reference', required=True, copy=False,
                           readonly=True, default='New')
    client_id = fields.Many2one('tazweed.client', string='Client', required=True)
    
    request_type = fields.Selection([
        ('additional', 'Request Additional Workers'),
        ('replacement', 'Request Worker Replacement'),
        ('extension', 'Extend Worker Contract'),
        ('termination', 'Request Worker Termination'),
        ('transfer', 'Request Worker Transfer'),
        ('performance', 'Report Performance Issue'),
        ('attendance', 'Report Attendance Issue'),
        ('conduct', 'Report Conduct Issue'),
        ('appreciation', 'Worker Appreciation'),
    ], string='Request Type', required=True)
    
    # For additional workers
    job_title = fields.Char(string='Job Title')
    quantity = fields.Integer(string='Number of Workers', default=1)
    required_date = fields.Date(string='Required By Date')
    requirements = fields.Html(string='Requirements')
    
    # For specific worker requests
    worker_ids = fields.Many2many('hr.employee', string='Workers')
    placement_id = fields.Many2one('tazweed.placement', string='Placement')
    
    # For replacement
    replacement_reason = fields.Selection([
        ('performance', 'Performance Issues'),
        ('attendance', 'Attendance Issues'),
        ('conduct', 'Conduct Issues'),
        ('skill_mismatch', 'Skill Mismatch'),
        ('personal', 'Personal Reasons'),
        ('other', 'Other'),
    ], string='Replacement Reason')
    
    # For extension
    current_end_date = fields.Date(string='Current End Date')
    requested_end_date = fields.Date(string='Requested End Date')
    
    # For issues
    issue_date = fields.Date(string='Issue Date')
    issue_description = fields.Html(string='Issue Description')
    
    # For appreciation
    appreciation_message = fields.Html(string='Appreciation Message')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    
    priority = fields.Selection([
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    response = fields.Html(string='Response')
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('client.worker.request') or 'New'
        return super().create(vals_list)
