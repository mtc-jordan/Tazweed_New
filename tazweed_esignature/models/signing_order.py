# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class SigningOrderWorkflow(models.Model):
    """Signing Order Workflow - Advanced signing order management"""
    _name = 'signing.order.workflow'
    _description = 'Signing Order Workflow'
    _order = 'name'

    name = fields.Char(string='Workflow Name', required=True)
    description = fields.Text(string='Description')
    
    # Workflow Type
    workflow_type = fields.Selection([
        ('sequential', 'Sequential (One by One)'),
        ('parallel', 'Parallel (All at Once)'),
        ('hybrid', 'Hybrid (Groups in Sequence)'),
        ('conditional', 'Conditional (Based on Rules)'),
    ], string='Workflow Type', required=True, default='sequential')
    
    # Steps
    step_ids = fields.One2many(
        'signing.order.step',
        'workflow_id',
        string='Workflow Steps'
    )
    
    # Document Types this workflow applies to
    document_type_ids = fields.Many2many(
        'signature.document.type',
        'signing_workflow_doctype_rel',
        'workflow_id',
        'doctype_id',
        string='Document Types'
    )
    
    # Default for document types
    is_default = fields.Boolean(
        string='Default Workflow',
        help='Use this workflow as default for selected document types'
    )
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.constrains('is_default', 'document_type_ids')
    def _check_default_workflow(self):
        """Ensure only one default workflow per document type"""
        for workflow in self:
            if workflow.is_default:
                for doc_type in workflow.document_type_ids:
                    existing = self.search([
                        ('id', '!=', workflow.id),
                        ('is_default', '=', True),
                        ('document_type_ids', 'in', doc_type.id)
                    ])
                    if existing:
                        raise ValidationError(
                            _('Document type "%s" already has a default workflow: %s') % 
                            (doc_type.name, existing[0].name)
                        )

    def apply_to_request(self, request):
        """Apply this workflow to a signature request"""
        self.ensure_one()
        
        # Clear existing signers
        request.signer_ids.unlink()
        
        # Create signers based on workflow steps
        for step in self.step_ids.sorted('sequence'):
            signer_vals = step._get_signer_values(request)
            if signer_vals:
                for vals in signer_vals:
                    vals['request_id'] = request.id
                    self.env['signature.signer'].create(vals)
        
        # Set signing order on request
        if self.workflow_type == 'sequential':
            request.signing_order = 'sequential'
        elif self.workflow_type == 'parallel':
            request.signing_order = 'parallel'
        else:
            request.signing_order = 'sequential'  # Hybrid uses sequential with groups


class SigningOrderStep(models.Model):
    """Signing Order Step - Individual step in signing workflow"""
    _name = 'signing.order.step'
    _description = 'Signing Order Step'
    _order = 'sequence'

    workflow_id = fields.Many2one(
        'signing.order.workflow',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Step Name', required=True)
    
    # Step Type
    step_type = fields.Selection([
        ('single', 'Single Signer'),
        ('group', 'Group (Any One)'),
        ('all', 'All Must Sign'),
        ('conditional', 'Conditional'),
    ], string='Step Type', required=True, default='single')
    
    # Signer Source
    signer_source = fields.Selection([
        ('fixed_user', 'Fixed User'),
        ('fixed_role', 'Fixed Role'),
        ('employee', 'Document Employee'),
        ('employee_manager', 'Employee Manager'),
        ('department_head', 'Department Head'),
        ('hr_manager', 'HR Manager'),
        ('ceo', 'CEO/Director'),
        ('custom_field', 'Custom Field'),
        ('dynamic', 'Dynamic (Runtime)'),
    ], string='Signer Source', required=True, default='fixed_user')
    
    # Fixed User/Role
    user_id = fields.Many2one(
        'res.users',
        string='User',
        help='Fixed user for this step'
    )
    group_id = fields.Many2one(
        'res.groups',
        string='User Group',
        help='Any user from this group can sign'
    )
    
    # Custom Field (for custom_field source)
    custom_field_name = fields.Char(
        string='Custom Field Name',
        help='Field name on the employee/document to get signer'
    )
    
    # Role
    signer_role = fields.Selection([
        ('signer', 'Signer'),
        ('approver', 'Approver'),
        ('witness', 'Witness'),
        ('reviewer', 'Reviewer'),
        ('cc', 'CC (Receive Copy)'),
    ], string='Signer Role', default='signer')
    
    # Signing Requirements
    is_required = fields.Boolean(string='Required', default=True)
    can_delegate = fields.Boolean(
        string='Can Delegate',
        default=False,
        help='Allow this signer to delegate to another person'
    )
    
    # Time Constraints
    deadline_days = fields.Integer(
        string='Deadline (Days)',
        default=0,
        help='Days to complete this step (0 = no deadline)'
    )
    reminder_days = fields.Integer(
        string='Reminder After (Days)',
        default=2
    )
    
    # Escalation
    escalation_enabled = fields.Boolean(
        string='Enable Escalation',
        default=False
    )
    escalation_after_days = fields.Integer(
        string='Escalate After (Days)',
        default=3
    )
    escalation_to = fields.Selection([
        ('manager', 'Manager'),
        ('hr', 'HR'),
        ('admin', 'Administrator'),
        ('custom', 'Custom User'),
    ], string='Escalate To')
    escalation_user_id = fields.Many2one(
        'res.users',
        string='Escalation User'
    )
    
    # Conditional Logic
    condition_type = fields.Selection([
        ('always', 'Always'),
        ('field_value', 'Based on Field Value'),
        ('amount', 'Based on Amount'),
        ('department', 'Based on Department'),
        ('custom', 'Custom Condition'),
    ], string='Condition Type', default='always')
    
    condition_field = fields.Char(string='Condition Field')
    condition_operator = fields.Selection([
        ('=', 'Equals'),
        ('!=', 'Not Equals'),
        ('>', 'Greater Than'),
        ('<', 'Less Than'),
        ('>=', 'Greater or Equal'),
        ('<=', 'Less or Equal'),
        ('in', 'In List'),
        ('not in', 'Not In List'),
    ], string='Condition Operator', default='=')
    condition_value = fields.Char(string='Condition Value')
    
    # Notifications
    notify_on_assign = fields.Boolean(
        string='Notify on Assignment',
        default=True
    )
    notify_on_complete = fields.Boolean(
        string='Notify on Completion',
        default=True
    )
    
    # Custom Message
    custom_message = fields.Text(
        string='Custom Message',
        help='Custom message to include in the signing request email'
    )

    def _get_signer_values(self, request):
        """Get signer values for this step based on the request"""
        self.ensure_one()
        
        # Check condition
        if not self._check_condition(request):
            return []
        
        signers = []
        
        if self.signer_source == 'fixed_user' and self.user_id:
            signers.append({
                'name': self.user_id.name,
                'email': self.user_id.email,
                'user_id': self.user_id.id,
                'role': self.signer_role,
                'sequence': self.sequence,
                'is_required': self.is_required,
                'can_delegate': self.can_delegate,
            })
        
        elif self.signer_source == 'fixed_role' and self.group_id:
            # For group, we'll add all users (for 'all' type) or mark as group (for 'group' type)
            users = self.group_id.users
            if self.step_type == 'all':
                for user in users:
                    signers.append({
                        'name': user.name,
                        'email': user.email,
                        'user_id': user.id,
                        'role': self.signer_role,
                        'sequence': self.sequence,
                        'is_required': self.is_required,
                    })
            else:
                # For 'group' type, add first user but mark as group
                if users:
                    signers.append({
                        'name': f"Any from {self.group_id.name}",
                        'email': users[0].email,
                        'group_id': self.group_id.id,
                        'role': self.signer_role,
                        'sequence': self.sequence,
                        'is_required': self.is_required,
                    })
        
        elif self.signer_source == 'employee' and request.employee_id:
            employee = request.employee_id
            signers.append({
                'name': employee.name,
                'email': employee.work_email,
                'employee_id': employee.id,
                'role': self.signer_role,
                'sequence': self.sequence,
                'is_required': self.is_required,
            })
        
        elif self.signer_source == 'employee_manager' and request.employee_id:
            manager = request.employee_id.parent_id
            if manager:
                signers.append({
                    'name': manager.name,
                    'email': manager.work_email,
                    'employee_id': manager.id,
                    'role': self.signer_role,
                    'sequence': self.sequence,
                    'is_required': self.is_required,
                })
        
        elif self.signer_source == 'department_head' and request.employee_id:
            dept = request.employee_id.department_id
            if dept and dept.manager_id:
                manager = dept.manager_id
                signers.append({
                    'name': manager.name,
                    'email': manager.work_email,
                    'employee_id': manager.id,
                    'role': self.signer_role,
                    'sequence': self.sequence,
                    'is_required': self.is_required,
                })
        
        elif self.signer_source == 'hr_manager':
            # Find HR manager
            hr_group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
            if hr_group and hr_group.users:
                hr_user = hr_group.users[0]
                signers.append({
                    'name': hr_user.name,
                    'email': hr_user.email,
                    'user_id': hr_user.id,
                    'role': self.signer_role,
                    'sequence': self.sequence,
                    'is_required': self.is_required,
                })
        
        return signers

    def _check_condition(self, request):
        """Check if this step's condition is met"""
        self.ensure_one()
        
        if self.condition_type == 'always':
            return True
        
        if self.condition_type == 'field_value' and self.condition_field:
            field_value = getattr(request, self.condition_field, None)
            if field_value is None:
                return False
            
            compare_value = self.condition_value
            
            if self.condition_operator == '=':
                return str(field_value) == compare_value
            elif self.condition_operator == '!=':
                return str(field_value) != compare_value
            elif self.condition_operator == '>':
                return float(field_value) > float(compare_value)
            elif self.condition_operator == '<':
                return float(field_value) < float(compare_value)
            elif self.condition_operator == '>=':
                return float(field_value) >= float(compare_value)
            elif self.condition_operator == '<=':
                return float(field_value) <= float(compare_value)
            elif self.condition_operator == 'in':
                return str(field_value) in compare_value.split(',')
            elif self.condition_operator == 'not in':
                return str(field_value) not in compare_value.split(',')
        
        return True


class SigningOrderGroup(models.Model):
    """Signing Order Group - Group signers for hybrid workflows"""
    _name = 'signing.order.group'
    _description = 'Signing Order Group'
    _order = 'sequence'

    name = fields.Char(string='Group Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Parent Request
    request_id = fields.Many2one(
        'signature.request',
        string='Signature Request',
        ondelete='cascade'
    )
    
    # Group Type
    group_type = fields.Selection([
        ('all', 'All Must Sign'),
        ('any', 'Any One Can Sign'),
        ('majority', 'Majority Must Sign'),
        ('threshold', 'Minimum Threshold'),
    ], string='Group Type', required=True, default='all')
    
    # Threshold (for threshold type)
    threshold_count = fields.Integer(
        string='Minimum Signatures',
        default=1,
        help='Minimum number of signatures required'
    )
    
    # Signers in this group
    signer_ids = fields.One2many(
        'signature.signer',
        'group_id',
        string='Signers'
    )
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending')
    
    # Statistics
    total_signers = fields.Integer(
        string='Total Signers',
        compute='_compute_stats'
    )
    signed_count = fields.Integer(
        string='Signed Count',
        compute='_compute_stats'
    )
    is_complete = fields.Boolean(
        string='Is Complete',
        compute='_compute_stats'
    )

    @api.depends('signer_ids', 'signer_ids.state')
    def _compute_stats(self):
        """Compute group statistics"""
        for group in self:
            group.total_signers = len(group.signer_ids)
            group.signed_count = len(group.signer_ids.filtered(lambda s: s.state == 'signed'))
            
            # Check completion based on group type
            if group.group_type == 'all':
                group.is_complete = group.signed_count == group.total_signers
            elif group.group_type == 'any':
                group.is_complete = group.signed_count >= 1
            elif group.group_type == 'majority':
                group.is_complete = group.signed_count > group.total_signers / 2
            elif group.group_type == 'threshold':
                group.is_complete = group.signed_count >= group.threshold_count
            else:
                group.is_complete = False

    def check_and_advance(self):
        """Check if group is complete and advance to next group"""
        self.ensure_one()
        
        if self.is_complete and self.state == 'active':
            self.write({'state': 'completed'})
            
            # Find and activate next group
            next_group = self.search([
                ('request_id', '=', self.request_id.id),
                ('sequence', '>', self.sequence),
                ('state', '=', 'pending')
            ], limit=1, order='sequence')
            
            if next_group:
                next_group.activate()
            else:
                # All groups complete, check if request is fully signed
                self.request_id._check_completion()

    def activate(self):
        """Activate this group and notify signers"""
        self.ensure_one()
        self.write({'state': 'active'})
        
        # Send notifications to signers in this group
        for signer in self.signer_ids:
            signer._send_signing_notification()


class SignerDelegation(models.Model):
    """Signer Delegation - Allow signers to delegate to others"""
    _name = 'signer.delegation'
    _description = 'Signer Delegation'
    _order = 'create_date desc'

    # Original Signer
    original_signer_id = fields.Many2one(
        'signature.signer',
        string='Original Signer',
        required=True,
        ondelete='cascade'
    )
    
    # Delegated To
    delegated_to_name = fields.Char(string='Delegated To Name', required=True)
    delegated_to_email = fields.Char(string='Delegated To Email', required=True)
    delegated_to_user_id = fields.Many2one(
        'res.users',
        string='Delegated To User'
    )
    
    # Reason
    reason = fields.Text(string='Delegation Reason')
    
    # Validity
    valid_from = fields.Datetime(
        string='Valid From',
        default=fields.Datetime.now
    )
    valid_until = fields.Datetime(
        string='Valid Until'
    )
    
    # Status
    state = fields.Selection([
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ], string='Status', default='active')
    
    # Audit
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    used_date = fields.Datetime(string='Used Date', readonly=True)

    @api.constrains('original_signer_id')
    def _check_can_delegate(self):
        """Check if original signer can delegate"""
        for delegation in self:
            if not delegation.original_signer_id.can_delegate:
                raise ValidationError(
                    _('This signer is not allowed to delegate.')
                )

    def action_revoke(self):
        """Revoke the delegation"""
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_('Only active delegations can be revoked.'))
        self.write({'state': 'revoked'})

    def use_delegation(self):
        """Mark delegation as used"""
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_('This delegation is not active.'))
        
        # Check validity
        now = fields.Datetime.now()
        if self.valid_until and now > self.valid_until:
            self.write({'state': 'expired'})
            raise UserError(_('This delegation has expired.'))
        
        self.write({
            'state': 'used',
            'used_date': now
        })
