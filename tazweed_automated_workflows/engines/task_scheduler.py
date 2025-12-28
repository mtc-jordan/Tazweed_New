"""
Tazweed Automated Workflows - Task Scheduler
Manages scheduled task execution
"""

from odoo import models, fields, api
from datetime import datetime, timedelta
import logging
import threading
import croniter

_logger = logging.getLogger(__name__)


class TaskScheduler:
    """Task Scheduler for managing scheduled task execution"""
    
    def __init__(self, env):
        """Initialize task scheduler"""
        self.env = env
        self.tasks = []
        self.running = False
        self.scheduler_thread = None
    
    def load_tasks(self):
        """Load active scheduled tasks"""
        self.tasks = self.env['tazweed.scheduled.task'].search([
            ('is_active', '=', True),
            ('state', '=', 'active')
        ])
        _logger.info(f'Loaded {len(self.tasks)} scheduled tasks')
    
    def is_task_due(self, task):
        """Check if a task is due for execution"""
        try:
            now = datetime.now()
            
            # One-time task
            if task.schedule_type == 'once':
                if task.execution_date and task.execution_date <= now:
                    return True
            
            # Daily task
            elif task.schedule_type == 'daily':
                task_time = now.replace(
                    hour=int(task.execution_time),
                    minute=task.execution_minute,
                    second=0,
                    microsecond=0
                )
                
                if task_time <= now:
                    # Check if last execution was more than 24 hours ago
                    if task.last_execution_date:
                        if (now - task.last_execution_date).days >= 1:
                            return True
                    else:
                        return True
            
            # Weekly task
            elif task.schedule_type == 'weekly':
                if task.day_of_week:
                    target_day = int(task.day_of_week)
                    current_day = now.weekday()
                    
                    if current_day == target_day:
                        task_time = now.replace(
                            hour=int(task.execution_time),
                            minute=task.execution_minute,
                            second=0,
                            microsecond=0
                        )
                        
                        if task_time <= now:
                            if task.last_execution_date:
                                if (now - task.last_execution_date).days >= 7:
                                    return True
                            else:
                                return True
            
            # Monthly task
            elif task.schedule_type == 'monthly':
                target_day = task.day_of_month if task.day_of_month > 0 else 31
                current_day = now.day
                
                if current_day == target_day or (target_day > 28 and current_day == 28):
                    task_time = now.replace(
                        hour=int(task.execution_time),
                        minute=task.execution_minute,
                        second=0,
                        microsecond=0
                    )
                    
                    if task_time <= now:
                        if task.last_execution_date:
                            if (now - task.last_execution_date).days >= 30:
                                return True
                        else:
                            return True
            
            # Quarterly task
            elif task.schedule_type == 'quarterly':
                current_month = now.month
                target_months = [1, 4, 7, 10]
                
                if current_month in target_months:
                    task_time = now.replace(
                        hour=int(task.execution_time),
                        minute=task.execution_minute,
                        second=0,
                        microsecond=0
                    )
                    
                    if task_time <= now:
                        if task.last_execution_date:
                            if (now - task.last_execution_date).days >= 90:
                                return True
                        else:
                            return True
            
            # Yearly task
            elif task.schedule_type == 'yearly':
                task_time = now.replace(
                    hour=int(task.execution_time),
                    minute=task.execution_minute,
                    second=0,
                    microsecond=0
                )
                
                if task_time <= now:
                    if task.last_execution_date:
                        if (now - task.last_execution_date).days >= 365:
                            return True
                    else:
                        return True
            
            # Cron task
            elif task.schedule_type == 'cron':
                if task.cron_expression:
                    try:
                        cron = croniter.croniter(task.cron_expression, now)
                        next_run = cron.get_next(datetime)
                        
                        if next_run <= now:
                            return True
                    except Exception as e:
                        _logger.error(f'Error parsing cron expression: {str(e)}')
            
            return False
        
        except Exception as e:
            _logger.error(f'Error checking if task is due: {str(e)}')
            return False
    
    def execute_task(self, task):
        """Execute a scheduled task"""
        try:
            # Check if task is active
            if not task.is_active or task.state != 'active':
                return False
            
            # Execute task code
            if task.task_code:
                exec(task.task_code)
            
            # Update statistics
            task.execution_count += 1
            task.success_count += 1
            task.last_execution_date = datetime.now()
            task.last_execution_status = 'success'
            
            # Log execution
            self.env['tazweed.task.execution.log'].create({
                'task_id': task.id,
                'status': 'success',
                'description': 'Task executed successfully'
            })
            
            _logger.info(f'Task {task.code} executed successfully')
            return True
        
        except Exception as e:
            _logger.error(f'Error executing task {task.code}: {str(e)}')
            
            # Update statistics
            task.execution_count += 1
            task.error_count += 1
            task.last_execution_date = datetime.now()
            task.last_execution_status = 'error'
            
            # Log error
            self.env['tazweed.task.execution.log'].create({
                'task_id': task.id,
                'status': 'error',
                'description': f'Error: {str(e)}'
            })
            
            return False
    
    def execute_due_tasks(self):
        """Execute all due scheduled tasks"""
        self.load_tasks()
        
        for task in self.tasks:
            if self.is_task_due(task):
                self.execute_task(task)
    
    def get_next_execution_time(self, task):
        """Get next execution time for a task"""
        try:
            now = datetime.now()
            
            if task.schedule_type == 'once':
                return task.execution_date
            
            elif task.schedule_type == 'daily':
                next_time = now.replace(
                    hour=int(task.execution_time),
                    minute=task.execution_minute,
                    second=0,
                    microsecond=0
                )
                
                if next_time <= now:
                    next_time += timedelta(days=1)
                
                return next_time
            
            elif task.schedule_type == 'weekly':
                target_day = int(task.day_of_week)
                current_day = now.weekday()
                days_ahead = target_day - current_day
                
                if days_ahead <= 0:
                    days_ahead += 7
                
                next_time = now + timedelta(days=days_ahead)
                next_time = next_time.replace(
                    hour=int(task.execution_time),
                    minute=task.execution_minute,
                    second=0,
                    microsecond=0
                )
                
                return next_time
            
            elif task.schedule_type == 'monthly':
                target_day = task.day_of_month if task.day_of_month > 0 else 31
                current_day = now.day
                
                if current_day >= target_day:
                    # Next month
                    if now.month == 12:
                        next_time = now.replace(year=now.year + 1, month=1, day=target_day)
                    else:
                        next_time = now.replace(month=now.month + 1, day=target_day)
                else:
                    next_time = now.replace(day=target_day)
                
                next_time = next_time.replace(
                    hour=int(task.execution_time),
                    minute=task.execution_minute,
                    second=0,
                    microsecond=0
                )
                
                return next_time
            
            elif task.schedule_type == 'cron':
                if task.cron_expression:
                    cron = croniter.croniter(task.cron_expression, now)
                    return cron.get_next(datetime)
            
            return None
        
        except Exception as e:
            _logger.error(f'Error getting next execution time: {str(e)}')
            return None
    
    def start(self):
        """Start task scheduler"""
        self.running = True
        self.load_tasks()
        _logger.info('Task scheduler started')
    
    def stop(self):
        """Stop task scheduler"""
        self.running = False
        _logger.info('Task scheduler stopped')
