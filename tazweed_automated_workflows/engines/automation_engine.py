"""
Tazweed Automated Workflows - Automation Engine
Executes automation rules and triggers
"""

from odoo import models, fields, api
from datetime import datetime, timedelta
import logging
import threading

_logger = logging.getLogger(__name__)


class AutomationEngine:
    """Automation Engine for executing automation rules"""
    
    def __init__(self, env):
        """Initialize automation engine"""
        self.env = env
        self.rules = []
        self.execution_queue = []
        self.running = False
    
    def load_rules(self):
        """Load active automation rules"""
        self.rules = self.env['tazweed.automation.rule'].search([
            ('is_active', '=', True),
            ('state', '=', 'active')
        ])
        _logger.info(f'Loaded {len(self.rules)} automation rules')
    
    def execute_rule(self, rule, record=None):
        """Execute a single automation rule"""
        try:
            # Check if rule is active
            if not rule.is_active or rule.state != 'active':
                return False
            
            # Check max executions
            if rule.max_executions > 0 and rule.execution_count >= rule.max_executions:
                _logger.info(f'Rule {rule.code} has reached max executions')
                return False
            
            # Check trigger condition
            if rule.trigger_condition:
                try:
                    if not eval(rule.trigger_condition):
                        return False
                except Exception as e:
                    _logger.error(f'Error evaluating trigger condition: {str(e)}')
                    return False
            
            # Execute action
            if rule.action_code:
                try:
                    exec(rule.action_code)
                except Exception as e:
                    _logger.error(f'Error executing action code: {str(e)}')
                    return False
            
            # Update execution count
            rule.execution_count += 1
            rule.last_execution = datetime.now()
            rule.last_execution_status = 'success'
            
            # Log execution
            self.env['tazweed.automation.execution.log'].create({
                'rule_id': rule.id,
                'status': 'success',
                'description': f'Rule executed successfully'
            })
            
            _logger.info(f'Rule {rule.code} executed successfully')
            return True
        
        except Exception as e:
            _logger.error(f'Error executing rule {rule.code}: {str(e)}')
            
            rule.last_execution = datetime.now()
            rule.last_execution_status = 'error'
            
            # Log error
            self.env['tazweed.automation.execution.log'].create({
                'rule_id': rule.id,
                'status': 'error',
                'description': f'Error: {str(e)}'
            })
            
            return False
    
    def execute_rules_for_model(self, model_name, trigger_event, record=None):
        """Execute all rules for a specific model and trigger event"""
        matching_rules = self.rules.filtered(
            lambda r: r.trigger_model == model_name and r.trigger_event == trigger_event
        )
        
        for rule in matching_rules:
            self.execute_rule(rule, record)
    
    def execute_all_rules(self):
        """Execute all active rules"""
        self.load_rules()
        
        for rule in self.rules:
            self.execute_rule(rule)
    
    def queue_rule_execution(self, rule, record=None, delay_minutes=0):
        """Queue a rule for execution"""
        execution_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        self.execution_queue.append({
            'rule': rule,
            'record': record,
            'execution_time': execution_time,
            'status': 'queued'
        })
        
        _logger.info(f'Rule {rule.code} queued for execution at {execution_time}')
    
    def process_queue(self):
        """Process queued rule executions"""
        now = datetime.now()
        
        for item in self.execution_queue:
            if item['execution_time'] <= now and item['status'] == 'queued':
                item['status'] = 'executing'
                self.execute_rule(item['rule'], item['record'])
                item['status'] = 'completed'
        
        # Remove completed items
        self.execution_queue = [item for item in self.execution_queue if item['status'] != 'completed']
    
    def start(self):
        """Start automation engine"""
        self.running = True
        self.load_rules()
        _logger.info('Automation engine started')
    
    def stop(self):
        """Stop automation engine"""
        self.running = False
        _logger.info('Automation engine stopped')


class WorkflowTriggerEngine:
    """Workflow Trigger Engine for executing workflow triggers"""
    
    def __init__(self, env):
        """Initialize workflow trigger engine"""
        self.env = env
        self.triggers = []
    
    def load_triggers(self):
        """Load active workflow triggers"""
        self.triggers = self.env['tazweed.workflow.trigger'].search([
            ('is_active', '=', True)
        ])
        _logger.info(f'Loaded {len(self.triggers)} workflow triggers')
    
    def execute_trigger(self, trigger, record=None):
        """Execute a workflow trigger"""
        try:
            return trigger.execute_trigger(record)
        except Exception as e:
            _logger.error(f'Error executing trigger {trigger.id}: {str(e)}')
            return False
    
    def execute_triggers_for_model(self, model_name, trigger_type, record=None):
        """Execute all triggers for a specific model and trigger type"""
        matching_triggers = self.triggers.filtered(
            lambda t: t.trigger_model == model_name and t.trigger_type == trigger_type
        )
        
        for trigger in matching_triggers:
            self.execute_trigger(trigger, record)
    
    def execute_all_triggers(self):
        """Execute all active triggers"""
        self.load_triggers()
        
        for trigger in self.triggers:
            self.execute_trigger(trigger)


class ApprovalChainEngine:
    """Approval Chain Engine for processing approval workflows"""
    
    def __init__(self, env):
        """Initialize approval chain engine"""
        self.env = env
    
    def create_approval_request(self, workflow, record=None):
        """Create approval request for a workflow"""
        try:
            approval_request = self.env['tazweed.approval.request'].create({
                'name': f'{workflow.name} - {record.name if record else "Manual"}',
                'workflow_id': workflow.id,
                'reference_model': record._name if record else None,
                'reference_id': record.id if record else None,
                'state': 'draft'
            })
            
            _logger.info(f'Approval request {approval_request.id} created')
            return approval_request
        
        except Exception as e:
            _logger.error(f'Error creating approval request: {str(e)}')
            return None
    
    def submit_for_approval(self, approval_request):
        """Submit approval request for approval"""
        try:
            approval_request.action_submit()
            _logger.info(f'Approval request {approval_request.id} submitted')
            return True
        except Exception as e:
            _logger.error(f'Error submitting approval request: {str(e)}')
            return False
    
    def process_approval(self, approval_line, approved=True, comments=''):
        """Process approval line"""
        try:
            if approved:
                approval_line.action_approve()
            else:
                approval_line.action_reject()
            
            _logger.info(f'Approval line {approval_line.id} processed')
            return True
        except Exception as e:
            _logger.error(f'Error processing approval line: {str(e)}')
            return False
    
    def check_escalation(self, approval_request):
        """Check if approval should be escalated"""
        try:
            workflow = approval_request.workflow_id
            
            if not workflow.escalation_enabled:
                return False
            
            # Check timeout
            if workflow.timeout_days > 0:
                timeout_date = approval_request.requested_date + timedelta(days=workflow.timeout_days)
                if datetime.now() > timeout_date:
                    return True
            
            return False
        except Exception as e:
            _logger.error(f'Error checking escalation: {str(e)}')
            return False
    
    def escalate_approval(self, approval_request):
        """Escalate approval to escalation approver"""
        try:
            workflow = approval_request.workflow_id
            
            if not workflow.escalation_approver_id:
                return False
            
            # Create escalation approval line
            self.env['tazweed.approval.line'].create({
                'request_id': approval_request.id,
                'approver_id': workflow.escalation_approver_id.id,
                'level': approval_request.current_level,
                'state': 'pending'
            })
            
            _logger.info(f'Approval request {approval_request.id} escalated')
            return True
        except Exception as e:
            _logger.error(f'Error escalating approval: {str(e)}')
            return False
