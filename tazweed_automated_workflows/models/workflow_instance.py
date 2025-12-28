"""
Tazweed Automated Workflows - Workflow Instance Model
Manages individual workflow instances and their execution
"""

from odoo import models, fields, api
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class WorkflowInstance(models.Model):
    """Workflow Instance Model"""
    
    _name = 'tazweed.workflow.instance'
    _description = 'Workflow Instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ============================================================
    # Basic Information
    # ============================================================
    
    name = fields.Char('Instance Name', required=True, tracking=True)
    workflow_id = fields.Many2one(
        'tazweed.workflow.definition',
        string='Workflow',
        required=True,
        tracking=True
    )
    
    reference_model = fields.Char('Reference Model', help='Model this workflow is attached to')
    reference_id = fields.Integer('Reference ID', help='ID of the referenced record')
    
    # ============================================================
    # Workflow State
    # ============================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed')
    ], string='State', default='draft', tracking=True)
    
    current_step = fields.Char('Current Step', readonly=True)
    
    # ============================================================
    # Approvers & Approvals
    # ============================================================
    
    approver_ids = fields.Many2many(
        'res.users',
        string='Approvers'
    )
    
    approval_ids = fields.One2many(
        'tazweed.workflow.approval',
        'workflow_instance_id',
        string='Approvals'
    )
    
    # ============================================================
    # Timeline
    # ============================================================
    
    initiated_by = fields.Many2one('res.users', 'Initiated By', readonly=True, default=lambda self: self.env.user)
    initiated_date = fields.Datetime('Initiated Date', readonly=True, default=fields.Datetime.now)
    
    started_date = fields.Datetime('Started Date', readonly=True)
    completed_date = fields.Datetime('Completed Date', readonly=True)
    
    # ============================================================
    # Execution Details
    # ============================================================
    
    execution_logs = fields.One2many(
        'tazweed.workflow.execution.log',
        'workflow_instance_id',
        string='Execution Logs',
        readonly=True
    )
    
    comments = fields.Text('Comments')
    rejection_reason = fields.Text('Rejection Reason')
    
    # ============================================================
    # Metadata
    # ============================================================
    
    context_data = fields.Json('Context Data', help='Additional context for workflow')
    variables = fields.Json('Variables', help='Workflow variables')
    
    # ============================================================
    # Statistics
    # ============================================================
    
    total_approvals = fields.Integer('Total Approvals', compute='_compute_approval_stats')
    completed_approvals = fields.Integer('Completed Approvals', compute='_compute_approval_stats')
    pending_approvals = fields.Integer('Pending Approvals', compute='_compute_approval_stats')
    
    execution_time = fields.Float('Execution Time (hours)', compute='_compute_execution_time')
    
    # ============================================================
    # Methods
    # ============================================================
    
    @api.model
    def create(self, vals):
        """Create workflow instance"""
        vals['initiated_by'] = self.env.user.id
        instance = super().create(vals)
        
        # Log creation
        self.env['tazweed.workflow.execution.log'].create({
            'workflow_instance_id': instance.id,
            'action': 'created',
            'description': f'Workflow instance created',
            'executed_by': self.env.user.id
        })
        
        return instance
    
    @api.depends('approval_ids')
    def _compute_approval_stats(self):
        """Compute approval statistics"""
        for instance in self:
            approvals = instance.approval_ids
            instance.total_approvals = len(approvals)
            instance.completed_approvals = len(approvals.filtered(lambda x: x.state in ['approved', 'rejected']))
            instance.pending_approvals = len(approvals.filtered(lambda x: x.state == 'pending'))
    
    @api.depends('initiated_date', 'completed_date')
    def _compute_execution_time(self):
        """Compute execution time"""
        for instance in self:
            if instance.completed_date and instance.initiated_date:
                delta = instance.completed_date - instance.initiated_date
                instance.execution_time = delta.total_seconds() / 3600
            else:
                instance.execution_time = 0
    
    def action_start(self):
        """Start workflow"""
        self.write({
            'state': 'in_progress',
            'started_date': datetime.now()
        })
        
        # Create approvals
        self._create_approvals()
        
        # Execute on_start_action
        if self.workflow_id.on_start_action:
            try:
                exec(self.workflow_id.on_start_action)
            except Exception as e:
                _logger.error(f'Error executing on_start_action: {str(e)}')
        
        # Send notifications
        self._send_notifications('start')
        
        # Log action
        self._log_action('started', 'Workflow started')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Workflow started successfully',
                'type': 'success'
            }
        }
    
    def action_approve(self):
        """Approve workflow"""
        if self.state != 'in_progress':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Workflow is not in progress',
                    'type': 'danger'
                }
            }
        
        # Check all approvals completed
        pending_approvals = self.approval_ids.filtered(lambda x: x.state == 'pending')
        if pending_approvals:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'{len(pending_approvals)} approvals still pending',
                    'type': 'danger'
                }
            }
        
        # Check if all approvals are approved
        rejected_approvals = self.approval_ids.filtered(lambda x: x.state == 'rejected')
        if rejected_approvals:
            self.action_reject()
            return
        
        # Execute on_approval_action
        if self.workflow_id.on_approval_action:
            try:
                exec(self.workflow_id.on_approval_action)
            except Exception as e:
                _logger.error(f'Error executing on_approval_action: {str(e)}')
        
        self.write({
            'state': 'approved',
            'completed_date': datetime.now()
        })
        
        # Send notifications
        self._send_notifications('approval')
        
        # Log action
        self._log_action('approved', 'Workflow approved')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Workflow approved successfully',
                'type': 'success'
            }
        }
    
    def action_reject(self):
        """Reject workflow"""
        self.write({
            'state': 'rejected',
            'completed_date': datetime.now()
        })
        
        # Execute on_rejection_action
        if self.workflow_id.on_rejection_action:
            try:
                exec(self.workflow_id.on_rejection_action)
            except Exception as e:
                _logger.error(f'Error executing on_rejection_action: {str(e)}')
        
        # Send notifications
        self._send_notifications('rejection')
        
        # Log action
        self._log_action('rejected', 'Workflow rejected')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Workflow rejected',
                'type': 'warning'
            }
        }
    
    def action_cancel(self):
        """Cancel workflow"""
        if self.state in ['approved', 'rejected', 'cancelled']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Cannot cancel completed workflow',
                    'type': 'danger'
                }
            }
        
        self.write({
            'state': 'cancelled',
            'completed_date': datetime.now()
        })
        
        # Log action
        self._log_action('cancelled', 'Workflow cancelled')
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Workflow cancelled',
                'type': 'warning'
            }
        }
    
    def _create_approvals(self):
        """Create approval records"""
        approval_model = self.env['tazweed.workflow.approval']
        
        for approver in self.approver_ids:
            approval_model.create({
                'workflow_instance_id': self.id,
                'approver_id': approver.id,
                'state': 'pending'
            })
    
    def _send_notifications(self, event_type):
        """Send notifications"""
        notification_model = self.env['tazweed.notification.template']
        
        templates = self.workflow_id.notification_template_ids.filtered(
            lambda x: event_type in x.trigger_event
        )
        
        for template in templates:
            template.send_notification(self)
    
    def _log_action(self, action, description):
        """Log workflow action"""
        self.env['tazweed.workflow.execution.log'].create({
            'workflow_instance_id': self.id,
            'action': action,
            'description': description,
            'executed_by': self.env.user.id
        })


class WorkflowApproval(models.Model):
    """Workflow Approval Model"""
    
    _name = 'tazweed.workflow.approval'
    _description = 'Workflow Approval'
    _order = 'create_date desc'
    
    workflow_instance_id = fields.Many2one(
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
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delegated', 'Delegated')
    ], string='State', default='pending', tracking=True)
    
    comments = fields.Text('Comments')
    
    approved_date = fields.Datetime('Approved Date', readonly=True)
    
    def action_approve(self):
        """Approve"""
        self.write({
            'state': 'approved',
            'approved_date': datetime.now()
        })
        
        # Check if all approvals are done
        pending = self.workflow_instance_id.approval_ids.filtered(lambda x: x.state == 'pending')
        if not pending:
            self.workflow_instance_id.action_approve()
    
    def action_reject(self):
        """Reject"""
        self.write({'state': 'rejected'})
        self.workflow_instance_id.action_reject()
