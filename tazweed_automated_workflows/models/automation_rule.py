"""
Tazweed Automated Workflows - Automation Rule Model
Defines automated actions and rules
"""

from odoo import models, fields, api
from datetime import datetime
import json
import logging

_logger = logging.getLogger(__name__)


class AutomationRule(models.Model):
    """Automation Rule Model"""
    
    _name = 'tazweed.automation.rule'
    _description = 'Automation Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ============================================================
    # Basic Information
    # ============================================================
    
    name = fields.Char('Rule Name', required=True, tracking=True)
    code = fields.Char('Rule Code', required=True, unique=True, tracking=True)
    description = fields.Text('Description')
    
    # ============================================================
    # Rule Type
    # ============================================================
    
    rule_type = fields.Selection([
        ('leave_auto_approve', 'Auto Approve Leave'),
        ('leave_auto_reject', 'Auto Reject Leave'),
        ('salary_auto_process', 'Auto Process Salary'),
        ('attendance_auto_mark', 'Auto Mark Attendance'),
        ('compliance_auto_check', 'Auto Check Compliance'),
        ('performance_auto_update', 'Auto Update Performance'),
        ('notification_auto_send', 'Auto Send Notification'),
        ('report_auto_generate', 'Auto Generate Report'),
        ('custom', 'Custom Rule')
    ], string='Rule Type', required=True, tracking=True)
    
    # ============================================================
    # Trigger Configuration
    # ============================================================
    
    trigger_model = fields.Char('Trigger Model', help='Model that triggers this rule')
    trigger_event = fields.Selection([
        ('create', 'Create'),
        ('write', 'Update'),
        ('delete', 'Delete'),
        ('state_change', 'State Change'),
        ('schedule', 'Scheduled'),
        ('webhook', 'Webhook'),
        ('manual', 'Manual')
    ], string='Trigger Event', required=True)
    
    trigger_condition = fields.Text('Trigger Condition', help='Python condition to check')
    
    # ============================================================
    # Action Configuration
    # ============================================================
    
    action_type = fields.Selection([
        ('create_record', 'Create Record'),
        ('update_record', 'Update Record'),
        ('delete_record', 'Delete Record'),
        ('send_email', 'Send Email'),
        ('send_notification', 'Send Notification'),
        ('execute_code', 'Execute Code'),
        ('trigger_workflow', 'Trigger Workflow'),
        ('create_task', 'Create Task'),
        ('generate_report', 'Generate Report')
    ], string='Action Type', required=True)
    
    action_code = fields.Text('Action Code', help='Python code to execute')
    
    # ============================================================
    # Execution Configuration
    # ============================================================
    
    execute_immediately = fields.Boolean('Execute Immediately', default=True)
    delay_minutes = fields.Integer('Delay (minutes)', default=0)
    
    max_executions = fields.Integer('Max Executions', default=0, help='0 = unlimited')
    execution_count = fields.Integer('Execution Count', readonly=True, default=0)
    
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
    # Execution History
    # ============================================================
    
    last_execution = fields.Datetime('Last Execution', readonly=True)
    last_execution_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('skipped', 'Skipped')
    ], string='Last Execution Status', readonly=True)
    
    execution_logs = fields.One2many(
        'tazweed.automation.execution.log',
        'rule_id',
        string='Execution Logs',
        readonly=True
    )
    
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
        """Create automation rule"""
        vals['created_by'] = self.env.user.id
        return super().create(vals)
    
    def action_activate(self):
        """Activate rule"""
        self.write({
            'state': 'active',
            'is_active': True
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Rule "{self.name}" activated',
                'type': 'success'
            }
        }
    
    def action_deactivate(self):
        """Deactivate rule"""
        self.write({
            'state': 'inactive',
            'is_active': False
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Rule "{self.name}" deactivated',
                'type': 'success'
            }
        }
    
    def action_test_rule(self):
        """Test rule execution"""
        try:
            # Execute action code
            if self.action_code:
                exec(self.action_code)
            
            # Log execution
            self.env['tazweed.automation.execution.log'].create({
                'rule_id': self.id,
                'status': 'success',
                'description': 'Test execution successful'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Rule test executed successfully',
                    'type': 'success'
                }
            }
        
        except Exception as e:
            # Log error
            self.env['tazweed.automation.execution.log'].create({
                'rule_id': self.id,
                'status': 'error',
                'description': f'Test execution failed: {str(e)}'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Rule test failed: {str(e)}',
                    'type': 'danger'
                }
            }
    
    def execute_rule(self, record=None):
        """Execute automation rule"""
        try:
            # Check if rule is active
            if not self.is_active or self.state != 'active':
                return False
            
            # Check max executions
            if self.max_executions > 0 and self.execution_count >= self.max_executions:
                return False
            
            # Check trigger condition
            if self.trigger_condition:
                if not eval(self.trigger_condition):
                    return False
            
            # Execute action
            if self.action_code:
                exec(self.action_code)
            
            # Update execution count
            self.execution_count += 1
            self.last_execution = datetime.now()
            self.last_execution_status = 'success'
            
            # Log execution
            self.env['tazweed.automation.execution.log'].create({
                'rule_id': self.id,
                'status': 'success',
                'description': f'Rule executed successfully'
            })
            
            return True
        
        except Exception as e:
            _logger.error(f'Error executing automation rule {self.code}: {str(e)}')
            
            self.last_execution = datetime.now()
            self.last_execution_status = 'error'
            
            # Log error
            self.env['tazweed.automation.execution.log'].create({
                'rule_id': self.id,
                'status': 'error',
                'description': f'Error: {str(e)}'
            })
            
            return False


class AutomationExecutionLog(models.Model):
    """Automation Execution Log Model"""
    
    _name = 'tazweed.automation.execution.log'
    _description = 'Automation Execution Log'
    _order = 'create_date desc'
    
    rule_id = fields.Many2one(
        'tazweed.automation.rule',
        string='Rule',
        required=True,
        ondelete='cascade'
    )
    
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('skipped', 'Skipped')
    ], string='Status', required=True)
    
    description = fields.Text('Description')
    
    executed_by = fields.Many2one('res.users', 'Executed By', readonly=True, default=lambda self: self.env.user)
    executed_date = fields.Datetime('Executed Date', readonly=True, default=fields.Datetime.now)
    
    execution_time = fields.Float('Execution Time (ms)', help='Time taken to execute')
