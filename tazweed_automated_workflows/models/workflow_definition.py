"""
Tazweed Automated Workflows - Workflow Definition Model
Defines workflow templates and configurations
"""

from odoo import models, fields, api
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class WorkflowDefinition(models.Model):
    """Workflow Definition Model"""
    
    _name = 'tazweed.workflow.definition'
    _description = 'Workflow Definition'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ============================================================
    # Basic Information
    # ============================================================
    
    name = fields.Char('Workflow Name', required=True, tracking=True)
    code = fields.Char('Workflow Code', required=True, unique=True, tracking=True)
    description = fields.Text('Description')
    
    # ============================================================
    # Workflow Type
    # ============================================================
    
    workflow_type = fields.Selection([
        ('leave_request', 'Leave Request'),
        ('expense_claim', 'Expense Claim'),
        ('salary_adjustment', 'Salary Adjustment'),
        ('promotion', 'Promotion'),
        ('transfer', 'Transfer'),
        ('resignation', 'Resignation'),
        ('payroll', 'Payroll Processing'),
        ('compliance', 'Compliance Check'),
        ('performance', 'Performance Review'),
        ('custom', 'Custom Workflow')
    ], string='Workflow Type', required=True, tracking=True)
    
    # ============================================================
    # Workflow Configuration
    # ============================================================
    
    start_state = fields.Char('Start State', default='draft', help='Initial state of workflow')
    end_states = fields.Char('End States', default='approved,rejected', help='Comma-separated end states')
    
    # ============================================================
    # Steps & Transitions
    # ============================================================
    
    workflow_steps = fields.One2many(
        'tazweed.workflow.step',
        'workflow_id',
        string='Workflow Steps'
    )
    
    workflow_transitions = fields.One2many(
        'tazweed.workflow.transition',
        'workflow_id',
        string='Workflow Transitions'
    )
    
    # ============================================================
    # Approval Configuration
    # ============================================================
    
    require_approval = fields.Boolean('Require Approval', default=True)
    approval_levels = fields.Integer('Number of Approval Levels', default=1)
    parallel_approval = fields.Boolean('Parallel Approval', default=False, help='All approvers at same level')
    sequential_approval = fields.Boolean('Sequential Approval', default=True, help='Approvers in order')
    
    # ============================================================
    # Notifications
    # ============================================================
    
    notify_on_start = fields.Boolean('Notify on Start', default=True)
    notify_on_approval = fields.Boolean('Notify on Approval', default=True)
    notify_on_rejection = fields.Boolean('Notify on Rejection', default=True)
    notify_on_completion = fields.Boolean('Notify on Completion', default=True)
    
    notification_template_ids = fields.Many2many(
        'tazweed.notification.template',
        string='Notification Templates'
    )
    
    # ============================================================
    # Triggers & Conditions
    # ============================================================
    
    auto_trigger = fields.Boolean('Auto Trigger', default=False)
    trigger_condition = fields.Text('Trigger Condition', help='JSON condition for auto-trigger')
    
    trigger_ids = fields.One2many(
        'tazweed.workflow.trigger',
        'workflow_id',
        string='Workflow Triggers'
    )
    
    # ============================================================
    # Actions
    # ============================================================
    
    on_start_action = fields.Text('On Start Action', help='Python code to execute on workflow start')
    on_approval_action = fields.Text('On Approval Action', help='Python code to execute on approval')
    on_rejection_action = fields.Text('On Rejection Action', help='Python code to execute on rejection')
    on_completion_action = fields.Text('On Completion Action', help='Python code to execute on completion')
    
    # ============================================================
    # Configuration
    # ============================================================
    
    timeout_days = fields.Integer('Timeout Days', default=0, help='0 = no timeout')
    auto_approve_after_days = fields.Integer('Auto Approve After Days', default=0)
    allow_rejection = fields.Boolean('Allow Rejection', default=True)
    allow_cancellation = fields.Boolean('Allow Cancellation', default=True)
    
    # ============================================================
    # Status & Tracking
    # ============================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived')
    ], string='State', default='draft', tracking=True)
    
    is_active = fields.Boolean('Is Active', default=True)
    version = fields.Integer('Version', default=1, readonly=True)
    
    # ============================================================
    # Statistics
    # ============================================================
    
    total_instances = fields.Integer('Total Instances', compute='_compute_statistics', readonly=True)
    active_instances = fields.Integer('Active Instances', compute='_compute_statistics', readonly=True)
    completed_instances = fields.Integer('Completed Instances', compute='_compute_statistics', readonly=True)
    rejected_instances = fields.Integer('Rejected Instances', compute='_compute_statistics', readonly=True)
    
    # ============================================================
    # Audit Trail
    # ============================================================
    
    created_by = fields.Many2one('res.users', 'Created By', readonly=True, default=lambda self: self.env.user)
    created_date = fields.Datetime('Created Date', readonly=True, default=fields.Datetime.now)
    modified_date = fields.Datetime('Modified Date', readonly=True)
    
    # ============================================================
    # Methods
    # ============================================================
    
    @api.model
    def create(self, vals):
        """Create workflow definition"""
        vals['created_by'] = self.env.user.id
        return super().create(vals)
    
    def write(self, vals):
        """Update workflow definition"""
        vals['modified_date'] = fields.Datetime.now()
        return super().write(vals)
    
    @api.depends('workflow_steps')
    def _compute_statistics(self):
        """Compute workflow statistics"""
        for workflow in self:
            instances = self.env['tazweed.workflow.instance'].search([
                ('workflow_id', '=', workflow.id)
            ])
            
            workflow.total_instances = len(instances)
            workflow.active_instances = len(instances.filtered(lambda x: x.state in ['draft', 'pending']))
            workflow.completed_instances = len(instances.filtered(lambda x: x.state == 'approved'))
            workflow.rejected_instances = len(instances.filtered(lambda x: x.state == 'rejected'))
    
    def action_activate(self):
        """Activate workflow"""
        self.write({
            'state': 'active',
            'is_active': True
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Workflow "{self.name}" activated',
                'type': 'success'
            }
        }
    
    def action_deactivate(self):
        """Deactivate workflow"""
        self.write({
            'state': 'inactive',
            'is_active': False
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Workflow "{self.name}" deactivated',
                'type': 'success'
            }
        }
    
    def action_archive(self):
        """Archive workflow"""
        self.write({'state': 'archived'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Workflow "{self.name}" archived',
                'type': 'success'
            }
        }
    
    def action_duplicate(self):
        """Duplicate workflow"""
        new_workflow = self.copy()
        new_workflow.write({
            'name': f'{self.name} (Copy)',
            'code': f'{self.code}_copy_{datetime.now().timestamp()}',
            'state': 'draft'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': new_workflow.id,
            'view_mode': 'form',
        }
    
    def action_view_instances(self):
        """View workflow instances"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.workflow.instance',
            'view_mode': 'tree,form',
            'domain': [('workflow_id', '=', self.id)],
            'context': {'default_workflow_id': self.id}
        }
    
    def action_export_workflow(self):
        """Export workflow definition"""
        workflow_data = {
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'workflow_type': self.workflow_type,
            'start_state': self.start_state,
            'end_states': self.end_states,
            'require_approval': self.require_approval,
            'approval_levels': self.approval_levels,
            'parallel_approval': self.parallel_approval,
            'sequential_approval': self.sequential_approval,
            'notify_on_start': self.notify_on_start,
            'notify_on_approval': self.notify_on_approval,
            'notify_on_rejection': self.notify_on_rejection,
            'notify_on_completion': self.notify_on_completion,
            'auto_trigger': self.auto_trigger,
            'trigger_condition': self.trigger_condition,
            'timeout_days': self.timeout_days,
            'auto_approve_after_days': self.auto_approve_after_days,
            'allow_rejection': self.allow_rejection,
            'allow_cancellation': self.allow_cancellation,
        }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Workflow exported: {json.dumps(workflow_data)}',
                'type': 'success'
            }
        }


class WorkflowStep(models.Model):
    """Workflow Step Model"""
    
    _name = 'tazweed.workflow.step'
    _description = 'Workflow Step'
    _order = 'sequence'
    
    workflow_id = fields.Many2one(
        'tazweed.workflow.definition',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char('Step Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    state = fields.Char('State', required=True, help='State identifier')
    
    step_type = fields.Selection([
        ('start', 'Start'),
        ('approval', 'Approval'),
        ('action', 'Action'),
        ('condition', 'Condition'),
        ('end', 'End'),
        ('notification', 'Notification')
    ], string='Step Type', required=True)
    
    description = fields.Text('Description')
    
    # Approval step fields
    approver_ids = fields.Many2many(
        'res.users',
        string='Approvers'
    )
    
    # Action step fields
    action_code = fields.Text('Action Code', help='Python code to execute')
    
    # Condition step fields
    condition_code = fields.Text('Condition Code', help='Python condition code')
    
    # Notification step fields
    notification_template_id = fields.Many2one(
        'tazweed.notification.template',
        string='Notification Template'
    )


class WorkflowTransition(models.Model):
    """Workflow Transition Model"""
    
    _name = 'tazweed.workflow.transition'
    _description = 'Workflow Transition'
    
    workflow_id = fields.Many2one(
        'tazweed.workflow.definition',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    
    from_state = fields.Char('From State', required=True)
    to_state = fields.Char('To State', required=True)
    
    transition_type = fields.Selection([
        ('auto', 'Automatic'),
        ('manual', 'Manual'),
        ('conditional', 'Conditional')
    ], string='Transition Type', default='manual')
    
    condition = fields.Text('Condition', help='Python condition for conditional transitions')
    
    action_code = fields.Text('Action Code', help='Python code to execute on transition')
    
    name = fields.Char('Transition Name', compute='_compute_name')
    
    @api.depends('from_state', 'to_state')
    def _compute_name(self):
        """Compute transition name"""
        for transition in self:
            transition.name = f'{transition.from_state} → {transition.to_state}'
