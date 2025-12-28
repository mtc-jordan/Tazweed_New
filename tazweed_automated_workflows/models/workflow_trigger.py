# -*- coding: utf-8 -*-
"""
Tazweed Automated Workflows - Smart Workflow Triggers
Event-based, time-based, and condition-based triggers
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WorkflowTrigger(models.Model):
    """Smart Workflow Trigger"""
    
    _name = 'tazweed.workflow.trigger'
    _description = 'Workflow Trigger'
    _order = 'sequence, name'
    
    name = fields.Char(string='Trigger Name', required=True)
    code = fields.Char(string='Trigger Code')
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    workflow_id = fields.Many2one(
        'tazweed.workflow.definition',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    
    # ============================================================
    # Trigger Type
    # ============================================================
    
    trigger_type = fields.Selection([
        ('record_create', 'Record Created'),
        ('record_update', 'Record Updated'),
        ('field_change', 'Field Changed'),
        ('state_change', 'State Changed'),
        ('schedule', 'Scheduled'),
        ('webhook', 'Webhook'),
        ('manual', 'Manual'),
        ('api', 'API Call'),
        ('relative_date', 'Relative to Date'),
    ], string='Trigger Type', required=True, default='manual')
    
    # ============================================================
    # Model Configuration
    # ============================================================
    
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        help='Model to watch for events'
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        store=True
    )
    trigger_model = fields.Char(
        string='Trigger Model',
        help='Model that triggers workflow (legacy)'
    )
    trigger_field = fields.Char(
        string='Trigger Field',
        help='Field that triggers workflow'
    )
    
    # ============================================================
    # Event Configuration
    # ============================================================
    
    watch_field_ids = fields.Many2many(
        'ir.model.fields',
        string='Watch Fields',
        domain="[('model_id', '=', model_id)]",
        help='Trigger when these fields change'
    )
    
    from_state = fields.Char(
        string='From State',
        help='Trigger when state changes from this value'
    )
    to_state = fields.Char(
        string='To State',
        help='Trigger when state changes to this value'
    )
    
    # ============================================================
    # Time-Based Configuration
    # ============================================================
    
    schedule_type = fields.Selection([
        ('once', 'One Time'),
        ('recurring', 'Recurring'),
        ('relative', 'Relative to Date'),
    ], string='Schedule Type', default='once')
    
    scheduled_date = fields.Datetime(
        string='Scheduled Date',
        help='For one-time triggers'
    )
    
    cron_expression = fields.Char(
        string='Cron Expression',
        help='For recurring triggers'
    )
    
    relative_field_id = fields.Many2one(
        'ir.model.fields',
        string='Relative To Field',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['date', 'datetime'])]"
    )
    relative_days = fields.Integer(
        string='Days Before/After',
        default=0,
        help='Negative for before, positive for after'
    )
    
    # ============================================================
    # Condition Configuration
    # ============================================================
    
    trigger_condition = fields.Text(
        string='Trigger Condition',
        help='Python condition that must be True'
    )
    
    domain_filter = fields.Char(
        string='Domain Filter',
        default='[]',
        help='Odoo domain to filter records'
    )
    
    # ============================================================
    # Employee Filters
    # ============================================================
    
    employee_filter = fields.Selection([
        ('all', 'All Employees'),
        ('department', 'Specific Departments'),
        ('job', 'Specific Job Positions'),
        ('probation', 'On Probation'),
    ], string='Employee Filter', default='all')
    
    department_ids = fields.Many2many(
        'hr.department',
        string='Departments'
    )
    job_ids = fields.Many2many(
        'hr.job',
        string='Job Positions'
    )
    
    # ============================================================
    # Actions
    # ============================================================
    
    auto_start = fields.Boolean(
        string='Auto Start Workflow',
        default=True
    )
    pass_context = fields.Boolean(
        string='Pass Context',
        default=True
    )
    
    action_type = fields.Selection([
        ('create_instance', 'Create Workflow Instance'),
        ('server_action', 'Execute Server Action'),
        ('both', 'Both'),
    ], string='Action', default='create_instance')
    
    server_action_id = fields.Many2one(
        'ir.actions.server',
        string='Server Action'
    )
    
    # ============================================================
    # Instance Configuration
    # ============================================================
    
    set_employee = fields.Boolean(
        string='Set Employee',
        default=True
    )
    employee_field = fields.Char(
        string='Employee Field',
        default='employee_id'
    )
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Instance Priority', default='0')
    
    # ============================================================
    # Status & Statistics
    # ============================================================
    
    is_active = fields.Boolean(string='Active', default=True)
    
    trigger_count = fields.Integer(
        string='Times Triggered',
        default=0,
        readonly=True
    )
    last_triggered = fields.Datetime(
        string='Last Triggered',
        readonly=True
    )
    
    # ============================================================
    # Methods
    # ============================================================
    
    def check_trigger(self, record=None):
        """Check if trigger condition is met"""
        self.ensure_one()
        
        if not self.is_active:
            return False
        
        try:
            # Check domain filter
            if self.domain_filter and self.domain_filter != '[]' and record:
                domain = eval(self.domain_filter)
                if not record.filtered_domain(domain):
                    return False
            
            # Check python condition
            if self.trigger_condition:
                local_dict = {
                    'record': record,
                    'env': self.env,
                    'datetime': datetime,
                    'timedelta': timedelta,
                }
                if not eval(self.trigger_condition, local_dict):
                    return False
            
            # Check employee filter
            if record and self.employee_filter != 'all':
                employee = getattr(record, self.employee_field, None) if self.employee_field else None
                
                if self.employee_filter == 'department' and self.department_ids:
                    if employee and employee.department_id not in self.department_ids:
                        return False
                
                elif self.employee_filter == 'job' and self.job_ids:
                    if employee and employee.job_id not in self.job_ids:
                        return False
                
                elif self.employee_filter == 'probation':
                    if employee:
                        contract = self.env['hr.contract'].search([
                            ('employee_id', '=', employee.id),
                            ('state', '=', 'open'),
                        ], limit=1)
                        if not contract or not contract.trial_date_end:
                            return False
                        if contract.trial_date_end < fields.Date.today():
                            return False
            
            return True
        
        except Exception as e:
            _logger.error(f'Error checking trigger condition: {str(e)}')
            return False
    
    def execute_trigger(self, record=None):
        """Execute trigger"""
        self.ensure_one()
        
        if not self.is_active:
            return False
        
        if self.workflow_id.state != 'active':
            return False
        
        if not self.check_trigger(record):
            return False
        
        result = True
        
        # Create workflow instance
        if self.auto_start and self.action_type in ('create_instance', 'both'):
            instance_vals = {
                'workflow_id': self.workflow_id.id,
                'priority': self.priority,
            }
            
            if record:
                instance_vals.update({
                    'res_model': record._name,
                    'res_id': record.id,
                })
                
                # Set employee
                if self.set_employee and self.employee_field:
                    employee = getattr(record, self.employee_field, None)
                    if employee:
                        instance_vals['employee_id'] = employee.id
            
            if self.pass_context:
                instance_vals['description'] = f'Triggered by: {self.name}'
            
            instance = self.env['tazweed.workflow.instance'].create(instance_vals)
            instance.action_start()
        
        # Execute server action
        if self.action_type in ('server_action', 'both') and self.server_action_id:
            try:
                ctx = {}
                if record:
                    ctx = {
                        'active_model': record._name,
                        'active_id': record.id,
                        'active_ids': [record.id],
                    }
                self.server_action_id.with_context(**ctx).run()
            except Exception as e:
                _logger.error(f'Error executing server action: {e}')
                result = False
        
        # Update statistics
        self.write({
            'trigger_count': self.trigger_count + 1,
            'last_triggered': fields.Datetime.now(),
        })
        
        return result
    
    @api.model
    def process_scheduled_triggers(self):
        """Process all scheduled triggers (called by cron)"""
        now = fields.Datetime.now()
        
        triggers = self.search([
            ('is_active', '=', True),
            ('trigger_type', '=', 'schedule'),
            ('workflow_id.state', '=', 'active'),
        ])
        
        for trigger in triggers:
            try:
                if trigger.schedule_type == 'once':
                    if trigger.scheduled_date and trigger.scheduled_date <= now:
                        trigger.execute_trigger()
                        trigger.is_active = False
                
                elif trigger.schedule_type == 'relative':
                    trigger._process_relative_trigger()
                
            except Exception as e:
                _logger.error(f'Error processing trigger {trigger.name}: {e}')
    
    def _process_relative_trigger(self):
        """Process relative date triggers"""
        self.ensure_one()
        
        if not self.model_id or not self.relative_field_id:
            return
        
        today = fields.Date.today()
        target_date = today + timedelta(days=-self.relative_days)
        
        model_name = self.model_name or self.trigger_model
        if not model_name:
            return
        
        records = self.env[model_name].search([
            (self.relative_field_id.name, '=', target_date),
        ])
        
        for record in records:
            self.execute_trigger(record)
