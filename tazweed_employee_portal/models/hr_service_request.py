# -*- coding: utf-8 -*-
"""
HR Service Request Model
Allows employees to request various HR documents and services
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import hashlib
import secrets


class HRServiceRequestType(models.Model):
    """HR Service Request Type - Defines types of requests employees can make"""
    _name = 'hr.service.request.type'
    _description = 'HR Service Request Type'
    _order = 'sequence, name'

    name = fields.Char(string='Request Type', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Category
    category = fields.Selection([
        ('certificate', 'Certificates & Letters'),
        ('document', 'Document Requests'),
        ('service', 'HR Services'),
        ('financial', 'Financial Requests'),
        ('other', 'Other Requests'),
    ], string='Category', default='certificate', required=True)
    
    # Processing Configuration
    requires_approval = fields.Boolean(string='Requires Approval', default=True)
    approval_type = fields.Selection([
        ('hr', 'HR Only'),
        ('manager', 'Manager Only'),
        ('manager_hr', 'Manager then HR'),
        ('hr_manager', 'HR then Manager'),
    ], string='Approval Type', default='hr')
    
    auto_generate = fields.Boolean(
        string='Auto-Generate Document',
        help='If enabled, document will be auto-generated upon approval'
    )
    template_id = fields.Many2one(
        'mail.template',
        string='Document Template',
        help='Email template used to generate the document'
    )
    
    # SLA Configuration
    sla_days = fields.Integer(
        string='SLA (Days)',
        default=3,
        help='Expected processing time in business days'
    )
    priority_sla_days = fields.Integer(
        string='Priority SLA (Days)',
        default=1,
        help='Processing time for priority requests'
    )
    
    # Fees (if applicable)
    has_fee = fields.Boolean(string='Has Processing Fee')
    fee_amount = fields.Float(string='Fee Amount')
    fee_currency_id = fields.Many2one('res.currency', string='Currency')
    
    # Requirements
    required_fields = fields.Text(
        string='Required Information',
        help='JSON list of required fields for this request type'
    )
    instructions = fields.Html(string='Instructions for Employee')
    
    # Statistics
    request_count = fields.Integer(
        string='Total Requests',
        compute='_compute_request_count'
    )
    avg_processing_time = fields.Float(
        string='Avg Processing Time (Days)',
        compute='_compute_request_count'
    )
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Request type code must be unique!')
    ]
    
    @api.depends('code')
    def _compute_request_count(self):
        for record in self:
            requests = self.env['hr.service.request'].search([
                ('request_type_id', '=', record.id)
            ])
            record.request_count = len(requests)
            
            # Calculate average processing time
            completed = requests.filtered(lambda r: r.state == 'completed' and r.completed_date)
            if completed:
                total_days = sum([
                    (r.completed_date - r.request_date).days 
                    for r in completed if r.completed_date and r.request_date
                ])
                record.avg_processing_time = total_days / len(completed)
            else:
                record.avg_processing_time = 0


class HRServiceRequest(models.Model):
    """HR Service Request - Employee requests for HR documents and services"""
    _name = 'hr.service.request'
    _description = 'HR Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'reference'

    # Basic Information
    reference = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        related='employee_id.user_id',
        store=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        related='employee_id.parent_id',
        store=True
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        related='employee_id.job_id',
        store=True
    )
    
    # Request Details
    request_type_id = fields.Many2one(
        'hr.service.request.type',
        string='Request Type',
        required=True,
        tracking=True
    )
    category = fields.Selection(
        related='request_type_id.category',
        store=True
    )
    
    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.today,
        required=True,
        tracking=True
    )
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal', tracking=True)
    
    # Request Reason and Details
    reason = fields.Text(string='Reason for Request', required=True)
    additional_info = fields.Text(string='Additional Information')
    
    # For specific request types
    addressed_to = fields.Char(
        string='Addressed To',
        help='Name of organization/person the document is addressed to'
    )
    purpose = fields.Selection([
        ('visa', 'Visa Application'),
        ('bank', 'Bank/Financial Institution'),
        ('embassy', 'Embassy/Consulate'),
        ('government', 'Government Authority'),
        ('education', 'Educational Institution'),
        ('employment', 'New Employment'),
        ('personal', 'Personal Use'),
        ('other', 'Other'),
    ], string='Purpose')
    purpose_other = fields.Char(string='Other Purpose')
    
    # Date range for some requests (e.g., salary certificate for specific period)
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    
    # Language preference
    language = fields.Selection([
        ('en', 'English'),
        ('ar', 'Arabic'),
        ('both', 'Both (English & Arabic)'),
    ], string='Document Language', default='en')
    
    # Copies needed
    copies_needed = fields.Integer(string='Number of Copies', default=1)
    
    # State and Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('manager_approval', 'Pending Manager Approval'),
        ('hr_approval', 'Pending HR Approval'),
        ('processing', 'Processing'),
        ('ready', 'Ready for Collection'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # SLA Tracking
    expected_date = fields.Date(
        string='Expected Completion',
        compute='_compute_expected_date',
        store=True
    )
    sla_status = fields.Selection([
        ('on_track', 'On Track'),
        ('at_risk', 'At Risk'),
        ('overdue', 'Overdue'),
    ], string='SLA Status', compute='_compute_sla_status', store=True)
    
    # Approval Information
    manager_approved = fields.Boolean(string='Manager Approved')
    manager_approved_by = fields.Many2one('hr.employee', string='Manager Approved By')
    manager_approved_date = fields.Datetime(string='Manager Approval Date')
    manager_comments = fields.Text(string='Manager Comments')
    
    hr_approved = fields.Boolean(string='HR Approved')
    hr_approved_by = fields.Many2one('hr.employee', string='HR Approved By')
    hr_approved_date = fields.Datetime(string='HR Approval Date')
    hr_comments = fields.Text(string='HR Comments')
    
    # Rejection
    rejection_reason = fields.Text(string='Rejection Reason')
    rejected_by = fields.Many2one('hr.employee', string='Rejected By')
    rejected_date = fields.Datetime(string='Rejection Date')
    
    # Processing
    assigned_to = fields.Many2one(
        'hr.employee',
        string='Assigned To',
        tracking=True,
        domain="[('department_id.name', 'ilike', 'HR')]"
    )
    processing_notes = fields.Text(string='Processing Notes')
    
    # Completion
    completed_date = fields.Date(string='Completed Date')
    collected = fields.Boolean(string='Collected by Employee')
    collected_date = fields.Datetime(string='Collection Date')
    
    # Generated Document
    document_attachment_ids = fields.Many2many(
        'ir.attachment',
        'hr_service_request_attachment_rel',
        'request_id',
        'attachment_id',
        string='Generated Documents'
    )
    
    # Fees
    fee_applicable = fields.Boolean(
        string='Fee Applicable',
        related='request_type_id.has_fee'
    )
    fee_amount = fields.Float(
        string='Fee Amount',
        related='request_type_id.fee_amount'
    )
    fee_paid = fields.Boolean(string='Fee Paid')
    fee_paid_date = fields.Date(string='Fee Payment Date')
    
    # Access Token for Portal
    access_token = fields.Char(string='Access Token', copy=False)
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    @api.model
    def create(self, vals):
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('hr.service.request') or _('New')
        vals['access_token'] = secrets.token_urlsafe(32)
        return super().create(vals)
    
    @api.depends('request_type_id', 'priority', 'request_date')
    def _compute_expected_date(self):
        for record in self:
            if record.request_type_id and record.request_date:
                if record.priority in ['high', 'urgent']:
                    days = record.request_type_id.priority_sla_days
                else:
                    days = record.request_type_id.sla_days
                record.expected_date = record.request_date + timedelta(days=days)
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
    
    def action_submit(self):
        """Submit request for approval"""
        self.ensure_one()
        if not self.reason:
            raise UserError(_('Please provide a reason for this request.'))
        
        approval_type = self.request_type_id.approval_type
        
        if not self.request_type_id.requires_approval:
            self.state = 'processing'
            self._notify_hr_assigned()
        elif approval_type == 'manager':
            self.state = 'manager_approval'
            self._notify_manager()
        elif approval_type == 'manager_hr':
            self.state = 'manager_approval'
            self._notify_manager()
        elif approval_type in ['hr', 'hr_manager']:
            self.state = 'hr_approval'
            self._notify_hr()
        else:
            self.state = 'hr_approval'
            self._notify_hr()
        
        return True
    
    def action_manager_approve(self):
        """Manager approves the request"""
        self.ensure_one()
        self.write({
            'manager_approved': True,
            'manager_approved_by': self.env.user.employee_id.id,
            'manager_approved_date': fields.Datetime.now(),
        })
        
        approval_type = self.request_type_id.approval_type
        if approval_type == 'manager':
            self.state = 'processing'
            self._notify_hr_assigned()
        elif approval_type == 'manager_hr':
            self.state = 'hr_approval'
            self._notify_hr()
        else:
            self.state = 'processing'
            self._notify_hr_assigned()
        
        return True
    
    def action_hr_approve(self):
        """HR approves the request"""
        self.ensure_one()
        self.write({
            'hr_approved': True,
            'hr_approved_by': self.env.user.employee_id.id,
            'hr_approved_date': fields.Datetime.now(),
        })
        
        approval_type = self.request_type_id.approval_type
        if approval_type == 'hr_manager' and not self.manager_approved:
            self.state = 'manager_approval'
            self._notify_manager()
        else:
            self.state = 'processing'
            self._auto_assign()
        
        return True
    
    def action_reject(self):
        """Open rejection wizard"""
        return {
            'name': _('Reject Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.service.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }
    
    def action_start_processing(self):
        """Start processing the request"""
        self.ensure_one()
        if not self.assigned_to:
            self.assigned_to = self.env.user.employee_id
        self.state = 'processing'
        return True
    
    def action_mark_ready(self):
        """Mark document as ready for collection"""
        self.ensure_one()
        self.state = 'ready'
        self._notify_employee_ready()
        return True
    
    def action_complete(self):
        """Complete the request"""
        self.ensure_one()
        self.write({
            'state': 'completed',
            'completed_date': fields.Date.today(),
        })
        self._notify_employee_completed()
        return True
    
    def action_mark_collected(self):
        """Mark as collected by employee"""
        self.ensure_one()
        self.write({
            'collected': True,
            'collected_date': fields.Datetime.now(),
            'state': 'completed',
            'completed_date': fields.Date.today(),
        })
        return True
    
    def action_cancel(self):
        """Cancel the request"""
        self.ensure_one()
        if self.state in ['completed', 'rejected']:
            raise UserError(_('Cannot cancel a completed or rejected request.'))
        self.state = 'cancelled'
        return True
    
    def action_reset_to_draft(self):
        """Reset to draft"""
        self.ensure_one()
        if self.state not in ['cancelled', 'rejected']:
            raise UserError(_('Only cancelled or rejected requests can be reset.'))
        self.write({
            'state': 'draft',
            'manager_approved': False,
            'manager_approved_by': False,
            'manager_approved_date': False,
            'manager_comments': False,
            'hr_approved': False,
            'hr_approved_by': False,
            'hr_approved_date': False,
            'hr_comments': False,
            'rejection_reason': False,
            'rejected_by': False,
            'rejected_date': False,
        })
        return True
    
    def _auto_assign(self):
        """Auto-assign to HR staff"""
        # Find HR employees with least workload
        hr_dept = self.env['hr.department'].search([
            ('name', 'ilike', 'HR')
        ], limit=1)
        if hr_dept:
            hr_employees = self.env['hr.employee'].search([
                ('department_id', '=', hr_dept.id),
                ('active', '=', True)
            ])
            if hr_employees:
                # Simple round-robin or least workload assignment
                pending_counts = {}
                for emp in hr_employees:
                    count = self.search_count([
                        ('assigned_to', '=', emp.id),
                        ('state', 'in', ['processing'])
                    ])
                    pending_counts[emp.id] = count
                
                if pending_counts:
                    min_emp = min(pending_counts, key=pending_counts.get)
                    self.assigned_to = min_emp
    
    def _notify_manager(self):
        """Send notification to manager"""
        if self.manager_id and self.manager_id.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.manager_id.user_id.id,
                summary=_('HR Service Request Approval Required'),
                note=_('Employee %s has submitted a request for %s. Please review and approve.') % (
                    self.employee_id.name, self.request_type_id.name
                )
            )
    
    def _notify_hr(self):
        """Send notification to HR"""
        hr_group = self.env.ref('hr.group_hr_user', raise_if_not_found=False)
        if hr_group:
            for user in hr_group.users[:3]:  # Notify first 3 HR users
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=_('HR Service Request Approval Required'),
                    note=_('Employee %s has submitted a request for %s. Please review and approve.') % (
                        self.employee_id.name, self.request_type_id.name
                    )
                )
    
    def _notify_hr_assigned(self):
        """Notify HR that request needs processing"""
        self._auto_assign()
        if self.assigned_to and self.assigned_to.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.assigned_to.user_id.id,
                summary=_('HR Service Request to Process'),
                note=_('Request %s from %s needs processing.') % (
                    self.reference, self.employee_id.name
                )
            )
    
    def _notify_employee_ready(self):
        """Notify employee that document is ready"""
        if self.employee_id.user_id:
            self.message_post(
                body=_('Your requested document (%s) is ready for collection.') % self.request_type_id.name,
                partner_ids=[self.employee_id.user_id.partner_id.id],
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
    
    def _notify_employee_completed(self):
        """Notify employee that request is completed"""
        if self.employee_id.user_id:
            self.message_post(
                body=_('Your HR service request (%s) has been completed.') % self.request_type_id.name,
                partner_ids=[self.employee_id.user_id.partner_id.id],
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )


class HRServiceRequestRejectWizard(models.TransientModel):
    """Wizard for rejecting HR service requests"""
    _name = 'hr.service.request.reject.wizard'
    _description = 'Reject HR Service Request'

    request_id = fields.Many2one('hr.service.request', string='Request', required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)

    def action_reject(self):
        """Reject the request with reason"""
        self.ensure_one()
        self.request_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'rejected_by': self.env.user.employee_id.id,
            'rejected_date': fields.Datetime.now(),
        })
        
        # Notify employee
        if self.request_id.employee_id.user_id:
            self.request_id.message_post(
                body=_('Your HR service request has been rejected. Reason: %s') % self.rejection_reason,
                partner_ids=[self.request_id.employee_id.user_id.partner_id.id],
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
        
        return {'type': 'ir.actions.act_window_close'}
