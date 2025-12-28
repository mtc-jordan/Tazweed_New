# -*- coding: utf-8 -*-
"""
Tazweed Automated Workflows - SLA Configuration
Service Level Agreement management for workflows
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SLAConfiguration(models.Model):
    """SLA Configuration for Workflows"""
    
    _name = 'tazweed.sla.configuration'
    _description = 'SLA Configuration'
    _order = 'priority desc, name'
    
    name = fields.Char(string='SLA Name', required=True)
    code = fields.Char(string='SLA Code', required=True)
    description = fields.Text(string='Description')
    
    # Target
    workflow_type = fields.Selection([
        ('all', 'All Workflows'),
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
        ('custom', 'Custom Workflow'),
    ], string='Workflow Type', default='all')
    
    workflow_ids = fields.Many2many(
        'tazweed.workflow.definition',
        string='Specific Workflows',
        help='Leave empty to apply to all workflows of selected type'
    )
    
    # SLA Metrics
    response_time_hours = fields.Float(
        string='Response Time (Hours)',
        default=4,
        help='Maximum time for first response'
    )
    resolution_time_hours = fields.Float(
        string='Resolution Time (Hours)',
        default=24,
        help='Maximum time for complete resolution'
    )
    
    # Priority-based SLA
    priority_based = fields.Boolean(
        string='Priority Based',
        default=True,
        help='Different SLA times based on priority'
    )
    
    urgent_response_hours = fields.Float(string='Urgent Response (Hours)', default=1)
    urgent_resolution_hours = fields.Float(string='Urgent Resolution (Hours)', default=4)
    high_response_hours = fields.Float(string='High Response (Hours)', default=2)
    high_resolution_hours = fields.Float(string='High Resolution (Hours)', default=8)
    normal_response_hours = fields.Float(string='Normal Response (Hours)', default=4)
    normal_resolution_hours = fields.Float(string='Normal Resolution (Hours)', default=24)
    low_response_hours = fields.Float(string='Low Response (Hours)', default=8)
    low_resolution_hours = fields.Float(string='Low Resolution (Hours)', default=48)
    
    # Business Hours
    use_business_hours = fields.Boolean(
        string='Use Business Hours',
        default=True,
        help='Calculate SLA based on business hours only'
    )
    business_start_hour = fields.Float(string='Business Start', default=8.0)
    business_end_hour = fields.Float(string='Business End', default=17.0)
    exclude_weekends = fields.Boolean(string='Exclude Weekends', default=True)
    exclude_holidays = fields.Boolean(string='Exclude Holidays', default=True)
    
    # Notifications
    notify_at_risk = fields.Boolean(string='Notify At Risk', default=True)
    at_risk_threshold_percent = fields.Float(
        string='At Risk Threshold %',
        default=75,
        help='Notify when this percentage of SLA time has elapsed'
    )
    notify_on_breach = fields.Boolean(string='Notify On Breach', default=True)
    
    # Status
    is_active = fields.Boolean(string='Active', default=True)
    priority = fields.Integer(
        string='Priority',
        default=10,
        help='Higher priority SLAs are applied first'
    )
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'SLA code must be unique!'),
    ]
    
    def get_sla_times(self, priority='0'):
        """Get SLA times based on priority"""
        self.ensure_one()
        
        if not self.priority_based:
            return {
                'response': self.response_time_hours,
                'resolution': self.resolution_time_hours,
            }
        
        priority_map = {
            '3': ('urgent_response_hours', 'urgent_resolution_hours'),
            '2': ('high_response_hours', 'high_resolution_hours'),
            '0': ('normal_response_hours', 'normal_resolution_hours'),
            '1': ('low_response_hours', 'low_resolution_hours'),
        }
        
        response_field, resolution_field = priority_map.get(
            priority, ('normal_response_hours', 'normal_resolution_hours')
        )
        
        return {
            'response': getattr(self, response_field),
            'resolution': getattr(self, resolution_field),
        }
    
    def calculate_due_date(self, start_date, priority='0'):
        """Calculate due date considering business hours"""
        self.ensure_one()
        
        sla_times = self.get_sla_times(priority)
        hours = sla_times['resolution']
        
        if not self.use_business_hours:
            return start_date + timedelta(hours=hours)
        
        # Calculate with business hours
        current = start_date
        remaining_hours = hours
        
        while remaining_hours > 0:
            # Check if current day is a working day
            if self.exclude_weekends and current.weekday() >= 5:
                current = current + timedelta(days=1)
                current = current.replace(
                    hour=int(self.business_start_hour),
                    minute=0,
                    second=0
                )
                continue
            
            # Calculate hours available today
            day_start = current.replace(
                hour=int(self.business_start_hour),
                minute=0,
                second=0
            )
            day_end = current.replace(
                hour=int(self.business_end_hour),
                minute=0,
                second=0
            )
            
            if current < day_start:
                current = day_start
            
            if current >= day_end:
                current = current + timedelta(days=1)
                current = current.replace(
                    hour=int(self.business_start_hour),
                    minute=0,
                    second=0
                )
                continue
            
            available_hours = (day_end - current).total_seconds() / 3600
            
            if remaining_hours <= available_hours:
                return current + timedelta(hours=remaining_hours)
            else:
                remaining_hours -= available_hours
                current = current + timedelta(days=1)
                current = current.replace(
                    hour=int(self.business_start_hour),
                    minute=0,
                    second=0
                )
        
        return current


class EscalationRule(models.Model):
    """Escalation Rule for Workflows"""
    
    _name = 'tazweed.escalation.rule'
    _description = 'Escalation Rule'
    _order = 'level, sequence'
    
    name = fields.Char(string='Rule Name', required=True)
    workflow_id = fields.Many2one(
        'tazweed.workflow.definition',
        string='Workflow',
        ondelete='cascade'
    )
    
    level = fields.Integer(
        string='Escalation Level',
        default=1,
        required=True
    )
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Trigger Conditions
    trigger_type = fields.Selection([
        ('time', 'Time Based'),
        ('sla_breach', 'SLA Breach'),
        ('no_response', 'No Response'),
        ('manual', 'Manual Only'),
    ], string='Trigger Type', default='time', required=True)
    
    hours_after_creation = fields.Float(
        string='Hours After Creation',
        default=24,
        help='Escalate after this many hours'
    )
    hours_after_last_action = fields.Float(
        string='Hours After Last Action',
        default=8,
        help='Escalate if no action for this many hours'
    )
    
    # Escalation Target
    escalate_to_type = fields.Selection([
        ('users', 'Specific Users'),
        ('manager', 'Manager'),
        ('department_head', 'Department Head'),
        ('hr_manager', 'HR Manager'),
        ('ceo', 'CEO/MD'),
        ('group', 'User Group'),
    ], string='Escalate To', default='manager', required=True)
    
    escalate_to_ids = fields.Many2many(
        'res.users',
        string='Escalate To Users'
    )
    escalate_to_group_id = fields.Many2one(
        'res.groups',
        string='Escalate To Group'
    )
    
    # Notifications
    notify_requester = fields.Boolean(string='Notify Requester', default=True)
    notify_current_approvers = fields.Boolean(
        string='Notify Current Approvers',
        default=True
    )
    notification_template_id = fields.Many2one(
        'tazweed.notification.template',
        string='Notification Template'
    )
    
    # Actions
    action_id = fields.Many2one(
        'ir.actions.server',
        string='Server Action',
        help='Additional action to execute on escalation'
    )
    
    is_active = fields.Boolean(string='Active', default=True)
    
    def check_escalation(self, instance):
        """Check if escalation should be triggered"""
        self.ensure_one()
        
        if not self.is_active:
            return False
        
        now = fields.Datetime.now()
        
        if self.trigger_type == 'time':
            if instance.create_date:
                hours_elapsed = (now - instance.create_date).total_seconds() / 3600
                return hours_elapsed >= self.hours_after_creation
        
        elif self.trigger_type == 'sla_breach':
            return instance.sla_status == 'breached'
        
        elif self.trigger_type == 'no_response':
            if instance.log_ids:
                last_action = instance.log_ids.sorted('create_date', reverse=True)[0]
                hours_since = (now - last_action.create_date).total_seconds() / 3600
                return hours_since >= self.hours_after_last_action
            else:
                hours_elapsed = (now - instance.create_date).total_seconds() / 3600
                return hours_elapsed >= self.hours_after_last_action
        
        return False
    
    def get_escalation_users(self, instance):
        """Get users to escalate to"""
        self.ensure_one()
        
        if self.escalate_to_type == 'users':
            return self.escalate_to_ids
        
        elif self.escalate_to_type == 'manager':
            if instance.employee_id and instance.employee_id.parent_id:
                return instance.employee_id.parent_id.user_id
        
        elif self.escalate_to_type == 'department_head':
            if instance.employee_id and instance.employee_id.department_id:
                manager = instance.employee_id.department_id.manager_id
                if manager:
                    return manager.user_id
        
        elif self.escalate_to_type == 'hr_manager':
            hr_manager_group = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
            if hr_manager_group:
                return self.env['res.users'].search([
                    ('groups_id', 'in', hr_manager_group.id)
                ], limit=1)
        
        elif self.escalate_to_type == 'group':
            if self.escalate_to_group_id:
                return self.env['res.users'].search([
                    ('groups_id', 'in', self.escalate_to_group_id.id)
                ])
        
        return self.env['res.users']
