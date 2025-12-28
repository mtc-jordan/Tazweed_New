"""
Tazweed Automated Workflows - Scheduled Task Model
Manages scheduled task execution
"""

from odoo import models, fields, api
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class ScheduledTask(models.Model):
    """Scheduled Task Model"""
    
    _name = 'tazweed.scheduled.task'
    _description = 'Scheduled Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'next_execution_date'

    # ============================================================
    # Basic Information
    # ============================================================
    
    name = fields.Char('Task Name', required=True, tracking=True)
    code = fields.Char('Task Code', required=True, unique=True, tracking=True)
    description = fields.Text('Description')
    
    # ============================================================
    # Task Type
    # ============================================================
    
    task_type = fields.Selection([
        ('payroll_processing', 'Payroll Processing'),
        ('leave_accrual', 'Leave Accrual'),
        ('attendance_sync', 'Attendance Sync'),
        ('compliance_check', 'Compliance Check'),
        ('report_generation', 'Report Generation'),
        ('data_cleanup', 'Data Cleanup'),
        ('backup', 'Backup'),
        ('notification_send', 'Send Notifications'),
        ('custom', 'Custom Task')
    ], string='Task Type', required=True, tracking=True)
    
    # ============================================================
    # Schedule Configuration
    # ============================================================
    
    schedule_type = fields.Selection([
        ('once', 'Once'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
        ('cron', 'Cron Expression')
    ], string='Schedule Type', required=True, default='daily')
    
    # One-time execution
    execution_date = fields.Datetime('Execution Date', help='For one-time tasks')
    
    # Recurring execution
    start_date = fields.Date('Start Date', default=fields.Date.today)
    end_date = fields.Date('End Date', help='Leave empty for indefinite')
    
    # Time configuration
    execution_time = fields.Float('Execution Time (24h)', help='Hour of day (0-23)')
    execution_minute = fields.Integer('Execution Minute', default=0)
    
    # Weekly configuration
    day_of_week = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], string='Day of Week')
    
    # Monthly configuration
    day_of_month = fields.Integer('Day of Month', help='1-31, 0 for last day')
    
    # Cron expression
    cron_expression = fields.Char('Cron Expression', help='Standard cron format')
    
    # ============================================================
    # Task Configuration
    # ============================================================
    
    task_code = fields.Text('Task Code', help='Python code to execute')
    
    parameters = fields.Json('Parameters', help='Task parameters')
    
    # ============================================================
    # Execution Configuration
    # ============================================================
    
    max_retries = fields.Integer('Max Retries', default=3)
    retry_delay_minutes = fields.Integer('Retry Delay (minutes)', default=5)
    
    timeout_minutes = fields.Integer('Timeout (minutes)', default=60)
    
    # ============================================================
    # Status & Tracking
    # ============================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('archived', 'Archived')
    ], string='State', default='draft', tracking=True)
    
    is_active = fields.Boolean('Is Active', default=True)
    
    # ============================================================
    # Execution History
    # ============================================================
    
    next_execution_date = fields.Datetime('Next Execution', compute='_compute_next_execution')
    last_execution_date = fields.Datetime('Last Execution', readonly=True)
    last_execution_status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
        ('timeout', 'Timeout')
    ], string='Last Execution Status', readonly=True)
    
    execution_count = fields.Integer('Execution Count', readonly=True, default=0)
    success_count = fields.Integer('Success Count', readonly=True, default=0)
    error_count = fields.Integer('Error Count', readonly=True, default=0)
    
    execution_logs = fields.One2many(
        'tazweed.task.execution.log',
        'task_id',
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
        """Create scheduled task"""
        vals['created_by'] = self.env.user.id
        return super().create(vals)
    
    @api.depends('schedule_type', 'execution_date', 'start_date', 'execution_time')
    def _compute_next_execution(self):
        """Compute next execution date"""
        for task in self:
            if task.schedule_type == 'once':
                task.next_execution_date = task.execution_date
            else:
                # Calculate next execution based on schedule type
                now = datetime.now()
                next_exec = now
                
                if task.schedule_type == 'daily':
                    next_exec = now.replace(hour=int(task.execution_time), minute=task.execution_minute, second=0)
                    if next_exec <= now:
                        next_exec += timedelta(days=1)
                
                elif task.schedule_type == 'weekly':
                    # Calculate next occurrence of specified day
                    pass
                
                elif task.schedule_type == 'monthly':
                    # Calculate next occurrence of specified day
                    pass
                
                task.next_execution_date = next_exec
    
    def action_activate(self):
        """Activate task"""
        self.write({
            'state': 'active',
            'is_active': True
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Task "{self.name}" activated',
                'type': 'success'
            }
        }
    
    def action_pause(self):
        """Pause task"""
        self.write({
            'state': 'paused',
            'is_active': False
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Task "{self.name}" paused',
                'type': 'warning'
            }
        }
    
    def action_execute_now(self):
        """Execute task immediately"""
        try:
            # Execute task code
            if self.task_code:
                exec(self.task_code)
            
            # Update statistics
            self.execution_count += 1
            self.success_count += 1
            self.last_execution_date = datetime.now()
            self.last_execution_status = 'success'
            
            # Log execution
            self.env['tazweed.task.execution.log'].create({
                'task_id': self.id,
                'status': 'success',
                'description': 'Task executed successfully'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Task executed successfully',
                    'type': 'success'
                }
            }
        
        except Exception as e:
            _logger.error(f'Error executing task {self.code}: {str(e)}')
            
            # Update statistics
            self.execution_count += 1
            self.error_count += 1
            self.last_execution_date = datetime.now()
            self.last_execution_status = 'error'
            
            # Log error
            self.env['tazweed.task.execution.log'].create({
                'task_id': self.id,
                'status': 'error',
                'description': f'Error: {str(e)}'
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Task execution failed: {str(e)}',
                    'type': 'danger'
                }
            }
    
    def action_view_logs(self):
        """View execution logs"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.task.execution.log',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
        }
    
    @api.model
    def cron_process_scheduled_tasks(self):
        """Cron job to process due scheduled tasks"""
        from datetime import datetime
        tasks = self.search([
            ('is_active', '=', True),
            ('state', '=', 'scheduled'),
            ('next_run', '<=', datetime.now()),
        ])
        for task in tasks:
            try:
                task.action_execute()
            except Exception as e:
                _logger.error(f'Error executing task {task.name}: {e}')


class TaskExecutionLog(models.Model):
    """Task Execution Log Model"""
    
    _name = 'tazweed.task.execution.log'
    _description = 'Task Execution Log'
    _order = 'create_date desc'
    
    task_id = fields.Many2one(
        'tazweed.scheduled.task',
        string='Task',
        required=True,
        ondelete='cascade'
    )
    
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
        ('timeout', 'Timeout')
    ], string='Status', required=True)
    
    description = fields.Text('Description')
    
    execution_time = fields.Float('Execution Time (ms)', help='Time taken to execute')
    
    executed_date = fields.Datetime('Executed Date', readonly=True, default=fields.Datetime.now)
