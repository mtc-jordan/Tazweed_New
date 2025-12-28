# -*- coding: utf-8 -*-
"""
Tazweed Automated Workflows - Enhanced Workflow Definition Model
World-class workflow engine with smart features and best practices
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class WorkflowDefinition(models.Model):
    """Enhanced Workflow Definition with Smart Features"""
    
    _name = 'tazweed.workflow.definition'
    _description = 'Workflow Definition'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # ============================================================
    # Basic Information
    # ============================================================
    
    name = fields.Char(
        string='Workflow Name',
        required=True,
        tracking=True,
        help='Descriptive name for the workflow'
    )
    code = fields.Char(
        string='Workflow Code',
        required=True,
        copy=False,
        tracking=True,
        help='Unique identifier for the workflow'
    )
    description = fields.Html(
        string='Description',
        help='Detailed description of the workflow purpose and process'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order'
    )
    
    # ============================================================
    # Workflow Type & Category
    # ============================================================
    
    workflow_type = fields.Selection([
        ('hr_onboarding', 'Employee Onboarding'),
        ('hr_offboarding', 'Employee Offboarding'),
        ('leave_request', 'Leave Request'),
        ('expense_claim', 'Expense Claim'),
        ('salary_adjustment', 'Salary Adjustment'),
        ('promotion', 'Promotion'),
        ('transfer', 'Transfer'),
        ('resignation', 'Resignation'),
        ('probation_review', 'Probation Review'),
        ('contract_renewal', 'Contract Renewal'),
        ('performance_review', 'Performance Review'),
        ('training_request', 'Training Request'),
        ('document_approval', 'Document Approval'),
        ('payroll_processing', 'Payroll Processing'),
        ('compliance_check', 'Compliance Check'),
        ('custom', 'Custom Workflow'),
    ], string='Workflow Type', required=True, default='custom', tracking=True)
    
    category = fields.Selection([
        ('hr', 'Human Resources'),
        ('payroll', 'Payroll'),
        ('leave', 'Leave Management'),
        ('performance', 'Performance'),
        ('compliance', 'Compliance'),
        ('finance', 'Finance'),
        ('operations', 'Operations'),
        ('general', 'General'),
    ], string='Category', default='hr', tracking=True)
    
    # ============================================================
    # Target Model Configuration
    # ============================================================
    
    model_id = fields.Many2one(
        'ir.model',
        string='Target Model',
        ondelete='cascade',
        help='The model this workflow applies to'
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        store=True
    )
    
    # ============================================================
    # State Configuration
    # ============================================================
    
    start_state = fields.Char(
        string='Start State',
        default='draft',
        required=True,
        help='Initial state when workflow starts'
    )
    end_states = fields.Char(
        string='End States',
        default='approved,rejected,cancelled',
        help='Comma-separated list of terminal states'
    )
    
    # ============================================================
    # Steps & Transitions
    # ============================================================
    
    step_ids = fields.One2many(
        'tazweed.workflow.step',
        'workflow_id',
        string='Workflow Steps',
        copy=True
    )
    transition_ids = fields.One2many(
        'tazweed.workflow.transition',
        'workflow_id',
        string='Transitions',
        copy=True
    )
    step_count = fields.Integer(
        string='Steps',
        compute='_compute_counts'
    )
    
    # ============================================================
    # Approval Configuration
    # ============================================================
    
    require_approval = fields.Boolean(
        string='Require Approval',
        default=True,
        tracking=True
    )
    approval_type = fields.Selection([
        ('sequential', 'Sequential (One after another)'),
        ('parallel', 'Parallel (All at once)'),
        ('any', 'Any (First approval wins)'),
        ('majority', 'Majority (More than 50%)'),
        ('unanimous', 'Unanimous (All must approve)'),
    ], string='Approval Type', default='sequential')
    
    approval_level_ids = fields.One2many(
        'tazweed.approval.level',
        'workflow_id',
        string='Approval Levels',
        copy=True
    )
    
    # ============================================================
    # SLA Configuration
    # ============================================================
    
    sla_enabled = fields.Boolean(
        string='Enable SLA',
        default=True,
        help='Enable Service Level Agreement tracking'
    )
    response_time_hours = fields.Float(
        string='Response Time (Hours)',
        default=24,
        help='Expected time for first response'
    )
    resolution_time_hours = fields.Float(
        string='Resolution Time (Hours)',
        default=72,
        help='Expected time for complete resolution'
    )
    
    # ============================================================
    # Escalation Configuration
    # ============================================================
    
    escalation_enabled = fields.Boolean(
        string='Enable Escalation',
        default=True
    )
    escalation_rule_ids = fields.One2many(
        'tazweed.escalation.rule',
        'workflow_id',
        string='Escalation Rules',
        copy=True
    )
    
    # ============================================================
    # Notification Configuration
    # ============================================================
    
    notify_on_start = fields.Boolean('Notify on Start', default=True)
    notify_on_approval = fields.Boolean('Notify on Approval', default=True)
    notify_on_rejection = fields.Boolean('Notify on Rejection', default=True)
    notify_on_completion = fields.Boolean('Notify on Completion', default=True)
    notify_on_escalation = fields.Boolean('Notify on Escalation', default=True)
    notify_on_sla_breach = fields.Boolean('Notify on SLA Breach', default=True)
    
    notification_template_ids = fields.Many2many(
        'tazweed.notification.template',
        string='Notification Templates'
    )
    
    # ============================================================
    # Trigger Configuration
    # ============================================================
    
    auto_trigger = fields.Boolean(
        string='Auto Trigger',
        default=False,
        help='Automatically start workflow based on triggers'
    )
    trigger_ids = fields.One2many(
        'tazweed.workflow.trigger',
        'workflow_id',
        string='Triggers'
    )
    
    # ============================================================
    # Actions (Server Actions)
    # ============================================================
    
    on_start_action_id = fields.Many2one(
        'ir.actions.server',
        string='On Start Action',
        help='Server action to execute when workflow starts'
    )
    on_approval_action_id = fields.Many2one(
        'ir.actions.server',
        string='On Approval Action'
    )
    on_rejection_action_id = fields.Many2one(
        'ir.actions.server',
        string='On Rejection Action'
    )
    on_completion_action_id = fields.Many2one(
        'ir.actions.server',
        string='On Completion Action'
    )
    
    # ============================================================
    # Advanced Configuration
    # ============================================================
    
    timeout_days = fields.Integer(
        string='Timeout (Days)',
        default=0,
        help='Auto-cancel after days (0 = no timeout)'
    )
    auto_approve_days = fields.Integer(
        string='Auto Approve (Days)',
        default=0,
        help='Auto-approve if no action after days (0 = disabled)'
    )
    allow_rejection = fields.Boolean('Allow Rejection', default=True)
    allow_cancellation = fields.Boolean('Allow Cancellation', default=True)
    allow_delegation = fields.Boolean('Allow Delegation', default=True)
    allow_reassignment = fields.Boolean('Allow Reassignment', default=True)
    require_comments = fields.Boolean(
        string='Require Comments',
        default=False,
        help='Require comments for approval/rejection'
    )
    
    # ============================================================
    # Status
    # ============================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    
    is_active = fields.Boolean(
        string='Active',
        compute='_compute_is_active',
        store=True
    )
    version = fields.Integer(
        string='Version',
        default=1,
        readonly=True
    )
    is_template = fields.Boolean(
        string='Is Template',
        default=False,
        help='Mark as template for reuse'
    )
    
    # ============================================================
    # Statistics
    # ============================================================
    
    instance_count = fields.Integer(
        string='Total Instances',
        compute='_compute_statistics'
    )
    active_instance_count = fields.Integer(
        string='Active Instances',
        compute='_compute_statistics'
    )
    completed_instance_count = fields.Integer(
        string='Completed',
        compute='_compute_statistics'
    )
    rejected_instance_count = fields.Integer(
        string='Rejected',
        compute='_compute_statistics'
    )
    avg_completion_hours = fields.Float(
        string='Avg. Completion (Hours)',
        compute='_compute_statistics'
    )
    sla_compliance_rate = fields.Float(
        string='SLA Compliance %',
        compute='_compute_statistics'
    )
    
    # ============================================================
    # Audit Fields
    # ============================================================
    
    created_by_id = fields.Many2one(
        'res.users',
        string='Created By',
        readonly=True,
        default=lambda self: self.env.user
    )
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Workflow code must be unique!'),
    ]
    
    # ============================================================
    # Compute Methods
    # ============================================================
    
    @api.depends('step_ids')
    def _compute_counts(self):
        for record in self:
            record.step_count = len(record.step_ids)
    
    @api.depends('state')
    def _compute_is_active(self):
        for record in self:
            record.is_active = record.state == 'active'
    
    def _compute_statistics(self):
        for record in self:
            instances = self.env['tazweed.workflow.instance'].search([
                ('workflow_id', '=', record.id)
            ])
            
            record.instance_count = len(instances)
            record.active_instance_count = len(instances.filtered(
                lambda i: i.state in ('draft', 'pending', 'in_progress')
            ))
            record.completed_instance_count = len(instances.filtered(
                lambda i: i.state == 'approved'
            ))
            record.rejected_instance_count = len(instances.filtered(
                lambda i: i.state == 'rejected'
            ))
            
            # Calculate average completion time
            completed = instances.filtered(
                lambda i: i.state == 'approved' and i.completion_date
            )
            if completed:
                total_hours = sum([
                    (i.completion_date - i.create_date).total_seconds() / 3600
                    for i in completed if i.completion_date and i.create_date
                ])
                record.avg_completion_hours = total_hours / len(completed)
            else:
                record.avg_completion_hours = 0
            
            # Calculate SLA compliance
            if record.sla_enabled and instances:
                compliant = len(instances.filtered(lambda i: i.sla_status == 'compliant'))
                record.sla_compliance_rate = (compliant / len(instances)) * 100
            else:
                record.sla_compliance_rate = 100
    
    # ============================================================
    # CRUD Methods
    # ============================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code(
                    'tazweed.workflow.definition'
                ) or 'WF-NEW'
        return super().create(vals_list)
    
    def write(self, vals):
        if 'state' not in vals:
            # Increment version on significant changes
            significant_fields = ['step_ids', 'transition_ids', 'approval_level_ids']
            if any(f in vals for f in significant_fields):
                vals['version'] = self.version + 1
        return super().write(vals)
    
    def copy(self, default=None):
        default = dict(default or {})
        default.update({
            'name': _('%s (Copy)') % self.name,
            'code': self.env['ir.sequence'].next_by_code('tazweed.workflow.definition'),
            'state': 'draft',
            'version': 1,
        })
        return super().copy(default)
    
    # ============================================================
    # Action Methods
    # ============================================================
    
    def action_activate(self):
        """Activate the workflow"""
        for record in self:
            if not record.step_ids:
                raise UserError(_('Cannot activate workflow without steps.'))
            record.state = 'active'
        return True
    
    def action_deactivate(self):
        """Deactivate the workflow"""
        self.write({'state': 'inactive'})
        return True
    
    def action_archive(self):
        """Archive the workflow"""
        self.write({'state': 'archived'})
        return True
    
    def action_reset_to_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
        return True
    
    def action_view_instances(self):
        """View workflow instances"""
        self.ensure_one()
        return {
            'name': _('Workflow Instances'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.workflow.instance',
            'view_mode': 'tree,form,kanban',
            'domain': [('workflow_id', '=', self.id)],
            'context': {'default_workflow_id': self.id},
        }
    
    def action_create_instance(self):
        """Create a new workflow instance"""
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_('Cannot create instance for inactive workflow.'))
        
        instance = self.env['tazweed.workflow.instance'].create({
            'workflow_id': self.id,
        })
        
        return {
            'name': _('Workflow Instance'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.workflow.instance',
            'view_mode': 'form',
            'res_id': instance.id,
        }
    
    def action_duplicate_as_template(self):
        """Create a template from this workflow"""
        self.ensure_one()
        new_workflow = self.copy({
            'name': _('%s (Template)') % self.name,
            'is_template': True,
        })
        return {
            'name': _('Workflow Template'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.workflow.definition',
            'view_mode': 'form',
            'res_id': new_workflow.id,
        }
    
    # ============================================================
    # Business Logic
    # ============================================================
    
    def get_next_approvers(self, instance, current_level=0):
        """Get next approvers based on approval configuration"""
        self.ensure_one()
        
        if not self.require_approval:
            return []
        
        levels = self.approval_level_ids.sorted('sequence')
        if current_level >= len(levels):
            return []
        
        level = levels[current_level]
        approvers = []
        
        if level.approver_type == 'user':
            approvers = level.user_ids
        elif level.approver_type == 'role':
            approvers = self.env['res.users'].search([
                ('groups_id', 'in', level.group_ids.ids)
            ])
        elif level.approver_type == 'manager':
            if instance.employee_id and instance.employee_id.parent_id:
                approvers = instance.employee_id.parent_id.user_id
        elif level.approver_type == 'department_manager':
            if instance.employee_id and instance.employee_id.department_id:
                manager = instance.employee_id.department_id.manager_id
                if manager:
                    approvers = manager.user_id
        
        return approvers
    
    def check_sla_status(self, instance):
        """Check SLA status for an instance"""
        self.ensure_one()
        
        if not self.sla_enabled:
            return 'not_applicable'
        
        now = fields.Datetime.now()
        created = instance.create_date
        
        hours_elapsed = (now - created).total_seconds() / 3600
        
        if hours_elapsed > self.resolution_time_hours:
            return 'breached'
        elif hours_elapsed > self.response_time_hours:
            return 'at_risk'
        else:
            return 'compliant'


class WorkflowStep(models.Model):
    """Workflow Step Definition"""
    
    _name = 'tazweed.workflow.step'
    _description = 'Workflow Step'
    _order = 'sequence, id'
    
    name = fields.Char(string='Step Name', required=True)
    code = fields.Char(string='Step Code', required=True)
    workflow_id = fields.Many2one(
        'tazweed.workflow.definition',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Text(string='Description')
    
    step_type = fields.Selection([
        ('start', 'Start'),
        ('action', 'Action'),
        ('approval', 'Approval'),
        ('notification', 'Notification'),
        ('condition', 'Condition'),
        ('wait', 'Wait'),
        ('end', 'End'),
    ], string='Step Type', default='action', required=True)
    
    # For approval steps
    approval_level_id = fields.Many2one(
        'tazweed.approval.level',
        string='Approval Level'
    )
    
    # For condition steps
    condition_code = fields.Text(
        string='Condition',
        help='Python expression that evaluates to True/False'
    )
    true_step_id = fields.Many2one(
        'tazweed.workflow.step',
        string='If True, Go To'
    )
    false_step_id = fields.Many2one(
        'tazweed.workflow.step',
        string='If False, Go To'
    )
    
    # For wait steps
    wait_hours = fields.Float(string='Wait Hours', default=0)
    
    # Actions
    action_id = fields.Many2one(
        'ir.actions.server',
        string='Server Action'
    )
    
    is_start = fields.Boolean(string='Is Start Step')
    is_end = fields.Boolean(string='Is End Step')
    
    _sql_constraints = [
        ('code_workflow_unique', 'UNIQUE(code, workflow_id)', 
         'Step code must be unique within workflow!'),
    ]


class WorkflowTransition(models.Model):
    """Workflow Transition Definition"""
    
    _name = 'tazweed.workflow.transition'
    _description = 'Workflow Transition'
    
    name = fields.Char(string='Transition Name', required=True)
    workflow_id = fields.Many2one(
        'tazweed.workflow.definition',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    
    from_step_id = fields.Many2one(
        'tazweed.workflow.step',
        string='From Step',
        required=True,
        domain="[('workflow_id', '=', workflow_id)]"
    )
    to_step_id = fields.Many2one(
        'tazweed.workflow.step',
        string='To Step',
        required=True,
        domain="[('workflow_id', '=', workflow_id)]"
    )
    
    trigger_type = fields.Selection([
        ('auto', 'Automatic'),
        ('manual', 'Manual'),
        ('approval', 'On Approval'),
        ('rejection', 'On Rejection'),
        ('condition', 'Condition Based'),
        ('timeout', 'On Timeout'),
    ], string='Trigger Type', default='auto', required=True)
    
    condition = fields.Text(
        string='Condition',
        help='Python expression for condition-based transitions'
    )
    
    sequence = fields.Integer(string='Sequence', default=10)


