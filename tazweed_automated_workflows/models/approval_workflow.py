"""
Tazweed Automated Workflows - Approval Workflow Model
Manages approval chains and multi-level approvals
"""

from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class ApprovalWorkflow(models.Model):
    """Approval Workflow Model"""
    
    _name = 'tazweed.approval.workflow'
    _description = 'Approval Workflow'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ============================================================
    # Basic Information
    # ============================================================
    
    name = fields.Char('Approval Workflow Name', required=True, tracking=True)
    code = fields.Char('Workflow Code', required=True, unique=True, tracking=True)
    description = fields.Text('Description')
    
    # ============================================================
    # Approval Type
    # ============================================================
    
    approval_type = fields.Selection([
        ('leave_request', 'Leave Request'),
        ('expense_claim', 'Expense Claim'),
        ('salary_adjustment', 'Salary Adjustment'),
        ('promotion', 'Promotion'),
        ('transfer', 'Transfer'),
        ('resignation', 'Resignation'),
        ('purchase_order', 'Purchase Order'),
        ('custom', 'Custom')
    ], string='Approval Type', required=True, tracking=True)
    
    # ============================================================
    # Approval Levels
    # ============================================================
    
    approval_levels = fields.One2many(
        'tazweed.approval.level',
        'workflow_id',
        string='Approval Levels'
    )
    
    total_levels = fields.Integer('Total Levels', compute='_compute_total_levels')
    
    # ============================================================
    # Approval Configuration
    # ============================================================
    
    parallel_approval = fields.Boolean('Parallel Approval', default=False, help='All approvers at same level')
    sequential_approval = fields.Boolean('Sequential Approval', default=True, help='Approvers in order')
    
    allow_delegation = fields.Boolean('Allow Delegation', default=True)
    allow_rejection = fields.Boolean('Allow Rejection', default=True)
    allow_comments = fields.Boolean('Allow Comments', default=True)
    
    # ============================================================
    # Timeout Configuration
    # ============================================================
    
    timeout_days = fields.Integer('Timeout Days', default=0, help='0 = no timeout')
    escalation_enabled = fields.Boolean('Enable Escalation', default=False)
    escalation_days = fields.Integer('Escalation Days', default=3)
    escalation_approver_id = fields.Many2one(
        'res.users',
        string='Escalation Approver'
    )
    
    # ============================================================
    # Notifications
    # ============================================================
    
    notify_on_submit = fields.Boolean('Notify on Submit', default=True)
    notify_on_approval = fields.Boolean('Notify on Approval', default=True)
    notify_on_rejection = fields.Boolean('Notify on Rejection', default=True)
    notify_on_escalation = fields.Boolean('Notify on Escalation', default=True)
    
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
    
    # ============================================================
    # Statistics
    # ============================================================
    
    total_approvals = fields.Integer('Total Approvals', compute='_compute_statistics')
    pending_approvals = fields.Integer('Pending Approvals', compute='_compute_statistics')
    approved_count = fields.Integer('Approved', compute='_compute_statistics')
    rejected_count = fields.Integer('Rejected', compute='_compute_statistics')
    
    # ============================================================
    # Audit Trail
    # ============================================================
    
    created_by = fields.Many2one('res.users', 'Created By', readonly=True, default=lambda self: self.env.user)
    created_date = fields.Datetime('Created Date', readonly=True, default=fields.Datetime.now)
    
    # ============================================================
    # Methods
    # ============================================================
    
    @api.model
    def create(self, vals):
        """Create approval workflow"""
        vals['created_by'] = self.env.user.id
        return super().create(vals)
    
    @api.depends('approval_levels')
    def _compute_total_levels(self):
        """Compute total approval levels"""
        for workflow in self:
            workflow.total_levels = len(workflow.approval_levels)
    
    def _compute_statistics(self):
        """Compute approval statistics"""
        for workflow in self:
            approvals = self.env['tazweed.approval.request'].search([
                ('workflow_id', '=', workflow.id)
            ])
            
            workflow.total_approvals = len(approvals)
            workflow.pending_approvals = len(approvals.filtered(lambda x: x.state == 'pending'))
            workflow.approved_count = len(approvals.filtered(lambda x: x.state == 'approved'))
            workflow.rejected_count = len(approvals.filtered(lambda x: x.state == 'rejected'))
    
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
                'message': f'Approval workflow "{self.name}" activated',
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
                'message': f'Approval workflow "{self.name}" deactivated',
                'type': 'success'
            }
        }


class ApprovalLevel(models.Model):
    """Approval Level Model"""
    
    _name = 'tazweed.approval.level'
    _description = 'Approval Level'
    _order = 'sequence'
    
    workflow_id = fields.Many2one(
        'tazweed.approval.workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char('Level Name', required=True)
    sequence = fields.Integer('Sequence', default=10)
    
    approver_ids = fields.Many2many(
        'res.users',
        string='Approvers'
    )
    
    approval_type = fields.Selection([
        ('any', 'Any Approver'),
        ('all', 'All Approvers'),
        ('majority', 'Majority')
    ], string='Approval Type', default='any')
    
    description = fields.Text('Description')


class ApprovalRequest(models.Model):
    """Approval Request Model"""
    
    _name = 'tazweed.approval.request'
    _description = 'Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    
    # ============================================================
    # Basic Information
    # ============================================================
    
    name = fields.Char('Request Name', required=True, tracking=True)
    workflow_id = fields.Many2one(
        'tazweed.approval.workflow',
        string='Workflow',
        required=True,
        tracking=True
    )
    
    reference_model = fields.Char('Reference Model')
    reference_id = fields.Integer('Reference ID')
    
    # ============================================================
    # Request Details
    # ============================================================
    
    requested_by = fields.Many2one('res.users', 'Requested By', default=lambda self: self.env.user)
    requested_date = fields.Datetime('Requested Date', default=fields.Datetime.now)
    
    description = fields.Text('Description')
    
    # ============================================================
    # Approval Status
    # ============================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='State', default='draft', tracking=True)
    
    current_level = fields.Integer('Current Level', default=1)
    
    # ============================================================
    # Approvals
    # ============================================================
    
    approval_line_ids = fields.One2many(
        'tazweed.approval.line',
        'request_id',
        string='Approval Lines'
    )
    
    # ============================================================
    # Timeline
    # ============================================================
    
    approved_date = fields.Datetime('Approved Date', readonly=True)
    rejected_date = fields.Datetime('Rejected Date', readonly=True)
    rejection_reason = fields.Text('Rejection Reason')
    
    # ============================================================
    # Methods
    # ============================================================
    
    def action_submit(self):
        """Submit for approval"""
        self.write({
            'state': 'pending',
            'current_level': 1
        })
        
        # Create approval lines
        self._create_approval_lines()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Request submitted for approval',
                'type': 'success'
            }
        }
    
    def _create_approval_lines(self):
        """Create approval lines for current level"""
        level = self.workflow_id.approval_levels.filtered(lambda x: x.sequence == self.current_level * 10)
        
        if level:
            for approver in level.approver_ids:
                self.env['tazweed.approval.line'].create({
                    'request_id': self.id,
                    'approver_id': approver.id,
                    'level': self.current_level,
                    'state': 'pending'
                })


class ApprovalLine(models.Model):
    """Approval Line Model"""
    
    _name = 'tazweed.approval.line'
    _description = 'Approval Line'
    
    request_id = fields.Many2one(
        'tazweed.approval.request',
        string='Request',
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
    ], string='State', default='pending', tracking=True)
    
    comments = fields.Text('Comments')
    
    approved_date = fields.Datetime('Approved Date', readonly=True)
    
    def action_approve(self):
        """Approve request"""
        self.write({
            'state': 'approved',
            'approved_date': datetime.now()
        })
        
        # Check if all approvals at this level are done
        pending = self.request_id.approval_line_ids.filtered(
            lambda x: x.level == self.level and x.state == 'pending'
        )
        
        if not pending:
            # Move to next level
            next_level = self.level + 1
            if next_level <= self.request_id.workflow_id.total_levels:
                self.request_id.current_level = next_level
                self.request_id._create_approval_lines()
            else:
                # All approvals done
                self.request_id.write({
                    'state': 'approved',
                    'approved_date': datetime.now()
                })
    
    def action_reject(self):
        """Reject request"""
        self.write({'state': 'rejected'})
        self.request_id.write({
            'state': 'rejected',
            'rejected_date': datetime.now()
        })
