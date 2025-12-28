# -*- coding: utf-8 -*-
"""
Tazweed Automated Workflows - Workflow Instance Model
Runtime instances of workflow definitions with SLA and escalation
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WorkflowInstance(models.Model):
    """Workflow Instance - Runtime execution of a workflow"""
    
    _name = 'tazweed.workflow.instance'
    _description = 'Workflow Instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    # ============================================================
    # Basic Information
    # ============================================================
    
    name = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    workflow_id = fields.Many2one(
        'tazweed.workflow.definition',
        string='Workflow',
        required=True,
        ondelete='restrict',
        tracking=True
    )
    workflow_type = fields.Selection(
        related='workflow_id.workflow_type',
        store=True
    )
    
    # ============================================================
    # Source Record
    # ============================================================
    
    res_model = fields.Char(string='Related Model')
    res_id = fields.Integer(string='Related Record ID')
    res_name = fields.Char(
        string='Related Record',
        compute='_compute_res_name'
    )
    
    # ============================================================
    # Employee/Requester
    # ============================================================
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        tracking=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True
    )
    requester_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    # ============================================================
    # Current State
    # ============================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('escalated', 'Escalated'),
        ('on_hold', 'On Hold'),
    ], string='Status', default='draft', tracking=True, index=True)
    
    current_step_id = fields.Many2one(
        'tazweed.workflow.step',
        string='Current Step',
        tracking=True
    )
    current_approval_level = fields.Integer(
        string='Current Approval Level',
        default=0
    )
    
    # ============================================================
    # Dates & Timing
    # ============================================================
    
    start_date = fields.Datetime(string='Start Date', tracking=True)
    completion_date = fields.Datetime(string='Completion Date', tracking=True)
    due_date = fields.Datetime(
        string='Due Date',
        compute='_compute_due_date',
        store=True
    )
    
    # ============================================================
    # SLA Tracking
    # ============================================================
    
    sla_status = fields.Selection([
        ('not_applicable', 'N/A'),
        ('compliant', 'Compliant'),
        ('at_risk', 'At Risk'),
        ('breached', 'Breached'),
    ], string='SLA Status', default='not_applicable', compute='_compute_sla_status', store=True)
    
    response_time_hours = fields.Float(
        string='Response Time (Hours)',
        compute='_compute_response_time',
        store=True
    )
    resolution_time_hours = fields.Float(
        string='Resolution Time (Hours)',
        compute='_compute_resolution_time',
        store=True
    )
    first_response_date = fields.Datetime(string='First Response')
    
    # ============================================================
    # Approvals
    # ============================================================
    
    approval_ids = fields.One2many(
        'tazweed.workflow.approval',
        'instance_id',
        string='Approvals'
    )
    pending_approver_ids = fields.Many2many(
        'res.users',
        'workflow_instance_pending_approvers',
        'instance_id',
        'user_id',
        string='Pending Approvers',
        compute='_compute_pending_approvers'
    )
    current_approver_ids = fields.Many2many(
        'res.users',
        'workflow_instance_current_approvers',
        'instance_id',
        'user_id',
        string='Current Approvers'
    )
    
    # ============================================================
    # Escalation
    # ============================================================
    
    is_escalated = fields.Boolean(string='Escalated', default=False)
    escalation_level = fields.Integer(string='Escalation Level', default=0)
    escalated_to_ids = fields.Many2many(
        'res.users',
        'workflow_instance_escalated_to',
        'instance_id',
        'user_id',
        string='Escalated To'
    )
    escalation_date = fields.Datetime(string='Escalation Date')
    
    # ============================================================
    # Comments & Notes
    # ============================================================
    
    description = fields.Text(string='Description')
    rejection_reason = fields.Text(string='Rejection Reason')
    cancellation_reason = fields.Text(string='Cancellation Reason')
    
    # ============================================================
    # Execution Log
    # ============================================================
    
    log_ids = fields.One2many(
        'tazweed.workflow.execution.log',
        'instance_id',
        string='Execution Log'
    )
    
    # ============================================================
    # Priority
    # ============================================================
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='0', tracking=True)
    
    # ============================================================
    # Statistics
    # ============================================================
    
    total_approvals = fields.Integer(
        string='Total Approvals',
        compute='_compute_approval_stats'
    )
    completed_approvals = fields.Integer(
        string='Completed Approvals',
        compute='_compute_approval_stats'
    )
    pending_approval_count = fields.Integer(
        string='Pending Approvals',
        compute='_compute_approval_stats'
    )
    
    # ============================================================
    # Computed Fields
    # ============================================================
    
    can_approve = fields.Boolean(
        string='Can Approve',
        compute='_compute_can_approve'
    )
    can_reject = fields.Boolean(
        string='Can Reject',
        compute='_compute_can_reject'
    )
    
    # ============================================================
    # Compute Methods
    # ============================================================
    
    def _compute_res_name(self):
        for record in self:
            if record.res_model and record.res_id:
                try:
                    related = self.env[record.res_model].browse(record.res_id)
                    record.res_name = related.display_name if related.exists() else ''
                except:
                    record.res_name = ''
            else:
                record.res_name = ''
    
    @api.depends('workflow_id', 'create_date')
    def _compute_due_date(self):
        for record in self:
            if record.workflow_id and record.workflow_id.resolution_time_hours:
                if record.create_date:
                    record.due_date = record.create_date + timedelta(
                        hours=record.workflow_id.resolution_time_hours
                    )
                else:
                    record.due_date = False
            else:
                record.due_date = False
    
    @api.depends('state', 'create_date', 'due_date', 'workflow_id.sla_enabled')
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for record in self:
            if not record.workflow_id or not record.workflow_id.sla_enabled:
                record.sla_status = 'not_applicable'
            elif record.state in ('approved', 'rejected', 'cancelled'):
                if record.completion_date and record.due_date:
                    if record.completion_date <= record.due_date:
                        record.sla_status = 'compliant'
                    else:
                        record.sla_status = 'breached'
                else:
                    record.sla_status = 'compliant'
            elif record.due_date:
                if now > record.due_date:
                    record.sla_status = 'breached'
                elif record.workflow_id.response_time_hours and now > record.due_date - timedelta(hours=record.workflow_id.response_time_hours / 2):
                    record.sla_status = 'at_risk'
                else:
                    record.sla_status = 'compliant'
            else:
                record.sla_status = 'not_applicable'
    
    @api.depends('first_response_date', 'create_date')
    def _compute_response_time(self):
        for record in self:
            if record.first_response_date and record.create_date:
                delta = record.first_response_date - record.create_date
                record.response_time_hours = delta.total_seconds() / 3600
            else:
                record.response_time_hours = 0
    
    @api.depends('completion_date', 'create_date')
    def _compute_resolution_time(self):
        for record in self:
            if record.completion_date and record.create_date:
                delta = record.completion_date - record.create_date
                record.resolution_time_hours = delta.total_seconds() / 3600
            else:
                record.resolution_time_hours = 0
    
    def _compute_pending_approvers(self):
        for record in self:
            pending = record.approval_ids.filtered(
                lambda a: a.state == 'pending'
            ).mapped('approver_id')
            record.pending_approver_ids = pending
    
    @api.depends('approval_ids')
    def _compute_approval_stats(self):
        for record in self:
            approvals = record.approval_ids
            record.total_approvals = len(approvals)
            record.completed_approvals = len(approvals.filtered(
                lambda a: a.state in ('approved', 'rejected')
            ))
            record.pending_approval_count = len(approvals.filtered(
                lambda a: a.state == 'pending'
            ))
    
    def _compute_can_approve(self):
        user = self.env.user
        for record in self:
            record.can_approve = (
                record.state == 'pending' and
                user in record.current_approver_ids
            )
    
    def _compute_can_reject(self):
        user = self.env.user
        for record in self:
            record.can_reject = (
                record.state == 'pending' and
                user in record.current_approver_ids and
                record.workflow_id.allow_rejection
            )
    
    # ============================================================
    # CRUD Methods
    # ============================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'tazweed.workflow.instance'
                ) or _('New')
        records = super().create(vals_list)
        for record in records:
            record._log_action('created', 'Workflow instance created')
        return records
    
    # ============================================================
    # Action Methods
    # ============================================================
    
    def action_start(self):
        """Start the workflow"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft workflows can be started.'))
            
            record.write({
                'state': 'pending',
                'start_date': fields.Datetime.now(),
            })
            
            # Set first step
            first_step = record.workflow_id.step_ids.filtered(
                lambda s: s.is_start or s.step_type == 'start'
            )[:1]
            if first_step:
                record.current_step_id = first_step
            
            # Create approval requests
            record._create_approval_requests()
            
            # Send notifications
            if record.workflow_id.notify_on_start:
                record._send_notification('start')
            
            record._log_action('started', 'Workflow started')
        
        return True
    
    def action_approve(self, comment=None):
        """Approve the current step"""
        self.ensure_one()
        user = self.env.user
        
        if not self.can_approve:
            raise UserError(_('You are not authorized to approve this workflow.'))
        
        if self.workflow_id.require_comments and not comment:
            raise UserError(_('Please provide a comment for approval.'))
        
        # Record first response
        if not self.first_response_date:
            self.first_response_date = fields.Datetime.now()
        
        # Update approval record
        approval = self.approval_ids.filtered(
            lambda a: a.approver_id == user and a.state == 'pending'
        )[:1]
        if approval:
            approval.write({
                'state': 'approved',
                'action_date': fields.Datetime.now(),
                'comment': comment,
            })
        
        # Check if all approvals at current level are complete
        if self._check_approval_complete():
            if self._has_next_approval_level():
                self.current_approval_level += 1
                self._create_approval_requests()
            else:
                self._complete_workflow('approved')
        
        if self.workflow_id.notify_on_approval:
            self._send_notification('approval')
        
        self._log_action('approved', f'Approved by {user.name}', comment)
        
        return True
    
    def action_reject(self, reason=None):
        """Reject the workflow"""
        self.ensure_one()
        user = self.env.user
        
        if not self.can_reject:
            raise UserError(_('You are not authorized to reject this workflow.'))
        
        if self.workflow_id.require_comments and not reason:
            raise UserError(_('Please provide a reason for rejection.'))
        
        if not self.first_response_date:
            self.first_response_date = fields.Datetime.now()
        
        approval = self.approval_ids.filtered(
            lambda a: a.approver_id == user and a.state == 'pending'
        )[:1]
        if approval:
            approval.write({
                'state': 'rejected',
                'action_date': fields.Datetime.now(),
                'comment': reason,
            })
        
        self._complete_workflow('rejected', reason)
        
        if self.workflow_id.notify_on_rejection:
            self._send_notification('rejection')
        
        self._log_action('rejected', f'Rejected by {user.name}', reason)
        
        return True
    
    def action_cancel(self, reason=None):
        """Cancel the workflow"""
        self.ensure_one()
        
        if not self.workflow_id.allow_cancellation:
            raise UserError(_('Cancellation is not allowed for this workflow.'))
        
        if self.state in ('approved', 'rejected', 'cancelled'):
            raise UserError(_('Cannot cancel a completed workflow.'))
        
        self.write({
            'state': 'cancelled',
            'cancellation_reason': reason,
            'completion_date': fields.Datetime.now(),
        })
        
        self.approval_ids.filtered(
            lambda a: a.state == 'pending'
        ).write({'state': 'cancelled'})
        
        self._log_action('cancelled', 'Workflow cancelled', reason)
        
        return True
    
    def action_hold(self):
        """Put workflow on hold"""
        self.ensure_one()
        
        if self.state not in ('pending', 'in_progress'):
            raise UserError(_('Only active workflows can be put on hold.'))
        
        self.write({'state': 'on_hold'})
        self._log_action('on_hold', 'Workflow put on hold')
        
        return True
    
    def action_resume(self):
        """Resume workflow from hold"""
        self.ensure_one()
        
        if self.state != 'on_hold':
            raise UserError(_('Only held workflows can be resumed.'))
        
        self.write({'state': 'pending'})
        self._log_action('resumed', 'Workflow resumed')
        
        return True
    
    def action_escalate(self):
        """Escalate the workflow"""
        self.ensure_one()
        
        if not self.workflow_id.escalation_enabled:
            raise UserError(_('Escalation is not enabled for this workflow.'))
        
        self.escalation_level += 1
        self.is_escalated = True
        self.escalation_date = fields.Datetime.now()
        self.state = 'escalated'
        
        rule = self.workflow_id.escalation_rule_ids.filtered(
            lambda r: r.level == self.escalation_level
        )[:1]
        
        if rule:
            self.escalated_to_ids = rule.escalate_to_ids
            
            for user in rule.escalate_to_ids:
                self.env['tazweed.workflow.approval'].create({
                    'instance_id': self.id,
                    'approver_id': user.id,
                    'level': self.current_approval_level,
                    'is_escalation': True,
                })
        
        if self.workflow_id.notify_on_escalation:
            self._send_notification('escalation')
        
        self._log_action('escalated', f'Escalated to level {self.escalation_level}')
        
        return True
    
    # ============================================================
    # Helper Methods
    # ============================================================
    
    def _create_approval_requests(self):
        """Create approval requests for current level"""
        self.ensure_one()
        
        approvers = self.workflow_id.get_next_approvers(self, self.current_approval_level)
        
        for approver in approvers:
            self.env['tazweed.workflow.approval'].create({
                'instance_id': self.id,
                'approver_id': approver.id,
                'level': self.current_approval_level,
            })
        
        self.current_approver_ids = approvers
    
    def _check_approval_complete(self):
        """Check if current approval level is complete"""
        self.ensure_one()
        
        current_approvals = self.approval_ids.filtered(
            lambda a: a.level == self.current_approval_level
        )
        
        approval_type = self.workflow_id.approval_type
        
        if approval_type == 'sequential':
            return all(a.state == 'approved' for a in current_approvals)
        elif approval_type == 'parallel':
            return all(a.state == 'approved' for a in current_approvals)
        elif approval_type == 'any':
            return any(a.state == 'approved' for a in current_approvals)
        elif approval_type == 'majority':
            approved = len(current_approvals.filtered(lambda a: a.state == 'approved'))
            return approved > len(current_approvals) / 2
        elif approval_type == 'unanimous':
            return all(a.state == 'approved' for a in current_approvals)
        
        return False
    
    def _has_next_approval_level(self):
        """Check if there are more approval levels"""
        self.ensure_one()
        
        levels = self.workflow_id.approval_level_ids
        return self.current_approval_level < len(levels) - 1
    
    def _complete_workflow(self, final_state, reason=None):
        """Complete the workflow"""
        self.ensure_one()
        
        vals = {
            'state': final_state,
            'completion_date': fields.Datetime.now(),
        }
        
        if final_state == 'rejected' and reason:
            vals['rejection_reason'] = reason
        
        self.write(vals)
        
        if self.workflow_id.notify_on_completion:
            self._send_notification('completion')
    
    def _send_notification(self, event_type):
        """Send notification for workflow event"""
        self.ensure_one()
        
        template = self.workflow_id.notification_template_ids.filtered(
            lambda t: t.event_type == event_type
        )[:1]
        
        if template:
            template.send_notification(self)
    
    def _log_action(self, action, description, comment=None):
        """Log workflow action"""
        self.ensure_one()
        
        log_vals = {
            'instance_id': self.id,
            'action': action,
            'description': description,
            'executed_by': self.env.user.id,
        }
        if comment:
            log_vals['additional_data'] = {'comment': comment}
        
        self.env['tazweed.workflow.execution.log'].create(log_vals)
    
    # ============================================================
    # CRON METHODS
    # ============================================================
    
    @api.model
    def cron_check_sla_status(self):
        """Cron job to check and update SLA status for active instances"""
        instances = self.search([
            ('state', 'in', ['pending', 'in_progress', 'escalated']),
        ])
        for instance in instances:
            instance._compute_sla_status()
    
    @api.model
    def cron_process_escalations(self):
        """Cron job to process escalations"""
        instances = self.search([
            ('state', 'in', ['pending', 'in_progress']),
            ('is_escalated', '=', False),
        ])
        for instance in instances:
            if instance.sla_status == 'breached':
                instance.action_escalate()
    
    @api.model
    def cron_auto_approve_timeout(self):
        """Cron job to auto-approve workflows that have exceeded timeout"""
        from datetime import datetime
        instances = self.search([
            ('state', '=', 'pending'),
        ])
        now = datetime.now()
        for instance in instances:
            if instance.workflow_id.auto_approve_days and instance.create_date:
                days_elapsed = (now - instance.create_date).days
                if days_elapsed >= instance.workflow_id.auto_approve_days:
                    instance.sudo()._complete_workflow('approved')
    
    @api.model
    def cron_cancel_timeout(self):
        """Cron job to cancel workflows that have exceeded timeout"""
        from datetime import datetime
        instances = self.search([
            ('state', 'in', ['draft', 'pending', 'in_progress']),
        ])
        now = datetime.now()
        for instance in instances:
            if instance.workflow_id.timeout_days and instance.create_date:
                days_elapsed = (now - instance.create_date).days
                if days_elapsed >= instance.workflow_id.timeout_days:
                    instance.sudo().action_cancel('Auto-cancelled due to timeout')


class WorkflowApproval(models.Model):
    """Workflow Approval Record"""
    
    _name = 'tazweed.workflow.approval'
    _description = 'Workflow Approval'
    _order = 'level, create_date'
    
    instance_id = fields.Many2one(
        'tazweed.workflow.instance',
        string='Workflow Instance',
        required=True,
        ondelete='cascade'
    )
    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        required=True
    )
    level = fields.Integer(string='Approval Level', default=0)
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delegated', 'Delegated'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending')
    
    action_date = fields.Datetime(string='Action Date')
    comment = fields.Text(string='Comment')
    
    delegated_to_id = fields.Many2one(
        'res.users',
        string='Delegated To'
    )
    is_escalation = fields.Boolean(string='Is Escalation', default=False)
    
    def action_approve(self):
        """Approve"""
        self.ensure_one()
        self.instance_id.action_approve()
        return True
    
    def action_reject(self):
        """Reject"""
        self.ensure_one()
        self.instance_id.action_reject()
        return True
    
    def action_delegate(self, delegate_to):
        """Delegate approval to another user"""
        self.ensure_one()
        
        if self.state != 'pending':
            raise UserError(_('Only pending approvals can be delegated.'))
        
        self.write({
            'state': 'delegated',
            'delegated_to_id': delegate_to.id,
            'action_date': fields.Datetime.now(),
        })
        
        self.env['tazweed.workflow.approval'].create({
            'instance_id': self.instance_id.id,
            'approver_id': delegate_to.id,
            'level': self.level,
        })
        
        return True
