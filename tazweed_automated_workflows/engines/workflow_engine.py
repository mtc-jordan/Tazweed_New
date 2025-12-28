"""
Tazweed Automated Workflows - Workflow Engine
Executes workflows and manages workflow state transitions
"""

from odoo import models, fields, api
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Workflow Engine for executing workflows"""
    
    def __init__(self, env):
        """Initialize workflow engine"""
        self.env = env
        self.workflows = []
    
    def load_workflows(self):
        """Load active workflows"""
        self.workflows = self.env['tazweed.workflow.definition'].search([
            ('is_active', '=', True),
            ('state', '=', 'active')
        ])
        _logger.info(f'Loaded {len(self.workflows)} workflows')
    
    def create_workflow_instance(self, workflow, record=None, context_data=None):
        """Create a workflow instance"""
        try:
            instance = self.env['tazweed.workflow.instance'].create({
                'name': f'{workflow.name} - {record.name if record else "Manual"}',
                'workflow_id': workflow.id,
                'reference_model': record._name if record else None,
                'reference_id': record.id if record else None,
                'state': 'draft',
                'initiated_by': self.env.user.id,
                'initiated_date': datetime.now(),
                'context_data': context_data or {}
            })
            
            _logger.info(f'Workflow instance {instance.id} created')
            return instance
        
        except Exception as e:
            _logger.error(f'Error creating workflow instance: {str(e)}')
            return None
    
    def start_workflow(self, instance):
        """Start a workflow instance"""
        try:
            # Check if workflow is in draft state
            if instance.state != 'draft':
                return False
            
            # Update state
            instance.state = 'pending'
            instance.started_date = datetime.now()
            
            # Execute on_start_action
            workflow = instance.workflow_id
            if workflow.on_start_action:
                try:
                    exec(workflow.on_start_action)
                except Exception as e:
                    _logger.error(f'Error executing on_start_action: {str(e)}')
            
            # Create approval lines if approval is required
            if workflow.require_approval:
                self._create_approval_lines(instance)
            
            # Log execution
            self.env['tazweed.workflow.execution.log'].create({
                'workflow_instance_id': instance.id,
                'action': 'started',
                'description': 'Workflow started'
            })
            
            _logger.info(f'Workflow instance {instance.id} started')
            return True
        
        except Exception as e:
            _logger.error(f'Error starting workflow: {str(e)}')
            return False
    
    def _create_approval_lines(self, instance):
        """Create approval lines for workflow instance"""
        try:
            workflow = instance.workflow_id
            
            # Get approval levels
            approval_levels = workflow.approval_levels.sorted(lambda x: x.sequence)
            
            for level in approval_levels:
                for approver in level.approver_ids:
                    self.env['tazweed.workflow.approval'].create({
                        'instance_id': instance.id,
                        'approver_id': approver.id,
                        'level': level.sequence,
                        'state': 'pending'
                    })
            
            instance.total_approvals = len(self.env['tazweed.workflow.approval'].search([
                ('instance_id', '=', instance.id)
            ]))
            
            _logger.info(f'Approval lines created for workflow instance {instance.id}')
        
        except Exception as e:
            _logger.error(f'Error creating approval lines: {str(e)}')
    
    def approve_workflow(self, instance, approver=None, comments=''):
        """Approve a workflow instance"""
        try:
            # Update state
            instance.state = 'approved'
            instance.completed_date = datetime.now()
            instance.completed_approvals += 1
            
            # Execute on_approval_action
            workflow = instance.workflow_id
            if workflow.on_approval_action:
                try:
                    exec(workflow.on_approval_action)
                except Exception as e:
                    _logger.error(f'Error executing on_approval_action: {str(e)}')
            
            # Log execution
            self.env['tazweed.workflow.execution.log'].create({
                'workflow_instance_id': instance.id,
                'action': 'approved',
                'description': f'Workflow approved by {approver.name if approver else "System"}'
            })
            
            _logger.info(f'Workflow instance {instance.id} approved')
            return True
        
        except Exception as e:
            _logger.error(f'Error approving workflow: {str(e)}')
            return False
    
    def reject_workflow(self, instance, reason='', approver=None):
        """Reject a workflow instance"""
        try:
            # Update state
            instance.state = 'rejected'
            instance.completed_date = datetime.now()
            instance.rejection_reason = reason
            
            # Execute on_rejection_action
            workflow = instance.workflow_id
            if workflow.on_rejection_action:
                try:
                    exec(workflow.on_rejection_action)
                except Exception as e:
                    _logger.error(f'Error executing on_rejection_action: {str(e)}')
            
            # Log execution
            self.env['tazweed.workflow.execution.log'].create({
                'workflow_instance_id': instance.id,
                'action': 'rejected',
                'description': f'Workflow rejected by {approver.name if approver else "System"}: {reason}'
            })
            
            _logger.info(f'Workflow instance {instance.id} rejected')
            return True
        
        except Exception as e:
            _logger.error(f'Error rejecting workflow: {str(e)}')
            return False
    
    def cancel_workflow(self, instance, reason=''):
        """Cancel a workflow instance"""
        try:
            # Update state
            instance.state = 'cancelled'
            instance.completed_date = datetime.now()
            
            # Log execution
            self.env['tazweed.workflow.execution.log'].create({
                'workflow_instance_id': instance.id,
                'action': 'cancelled',
                'description': f'Workflow cancelled: {reason}'
            })
            
            _logger.info(f'Workflow instance {instance.id} cancelled')
            return True
        
        except Exception as e:
            _logger.error(f'Error cancelling workflow: {str(e)}')
            return False
    
    def check_workflow_timeout(self, instance):
        """Check if workflow has timed out"""
        try:
            workflow = instance.workflow_id
            
            if workflow.timeout_days <= 0:
                return False
            
            timeout_date = instance.initiated_date + timedelta(days=workflow.timeout_days)
            
            if datetime.now() > timeout_date:
                return True
            
            return False
        
        except Exception as e:
            _logger.error(f'Error checking workflow timeout: {str(e)}')
            return False
    
    def auto_approve_workflow(self, instance):
        """Auto-approve workflow after timeout"""
        try:
            workflow = instance.workflow_id
            
            if workflow.auto_approve_after_days <= 0:
                return False
            
            auto_approve_date = instance.initiated_date + timedelta(days=workflow.auto_approve_after_days)
            
            if datetime.now() > auto_approve_date:
                self.approve_workflow(instance)
                return True
            
            return False
        
        except Exception as e:
            _logger.error(f'Error auto-approving workflow: {str(e)}')
            return False
    
    def get_workflow_status(self, instance):
        """Get workflow status"""
        try:
            status = {
                'id': instance.id,
                'name': instance.name,
                'state': instance.state,
                'workflow': instance.workflow_id.name,
                'initiated_by': instance.initiated_by.name,
                'initiated_date': instance.initiated_date,
                'started_date': instance.started_date,
                'completed_date': instance.completed_date,
                'total_approvals': instance.total_approvals,
                'completed_approvals': instance.completed_approvals,
                'pending_approvals': instance.pending_approvals,
                'execution_time': instance.execution_time,
                'approvers': [approver.name for approver in instance.approver_ids],
                'comments': instance.comments,
                'rejection_reason': instance.rejection_reason if instance.state == 'rejected' else None
            }
            
            return status
        
        except Exception as e:
            _logger.error(f'Error getting workflow status: {str(e)}')
            return None


class WorkflowApproval(models.Model):
    """Workflow Approval Model"""
    
    _name = 'tazweed.workflow.approval'
    _description = 'Workflow Approval'
    
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
    
    level = fields.Integer('Level', required=True)
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delegated', 'Delegated')
    ], string='State', default='pending')
    
    comments = fields.Text('Comments')
    
    approved_date = fields.Datetime('Approved Date', readonly=True)
