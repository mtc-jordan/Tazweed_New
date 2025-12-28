"""
Tazweed Automated Workflows - Workflow Trigger Model
Manages workflow triggers and conditions
"""

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class WorkflowTrigger(models.Model):
    """Workflow Trigger Model"""
    
    _name = 'tazweed.workflow.trigger'
    _description = 'Workflow Trigger'

    # ============================================================
    # Basic Information
    # ============================================================
    
    workflow_id = fields.Many2one(
        'tazweed.workflow.definition',
        string='Workflow',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char('Trigger Name', required=True)
    description = fields.Text('Description')
    
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
        ('api', 'API Call')
    ], string='Trigger Type', required=True)
    
    # ============================================================
    # Trigger Configuration
    # ============================================================
    
    trigger_model = fields.Char('Trigger Model', help='Model that triggers workflow')
    trigger_field = fields.Char('Trigger Field', help='Field that triggers workflow')
    trigger_condition = fields.Text('Trigger Condition', help='Python condition')
    
    # ============================================================
    # Workflow Configuration
    # ============================================================
    
    auto_start = fields.Boolean('Auto Start Workflow', default=True)
    pass_context = fields.Boolean('Pass Context', default=True)
    
    # ============================================================
    # Status
    # ============================================================
    
    is_active = fields.Boolean('Is Active', default=True)
    
    # ============================================================
    # Methods
    # ============================================================
    
    def check_trigger(self, record=None):
        """Check if trigger condition is met"""
        try:
            if self.trigger_condition:
                return eval(self.trigger_condition)
            return True
        
        except Exception as e:
            _logger.error(f'Error checking trigger condition: {str(e)}')
            return False
    
    def execute_trigger(self, record=None):
        """Execute trigger"""
        if not self.is_active:
            return False
        
        if not self.check_trigger(record):
            return False
        
        # Create workflow instance
        if self.auto_start:
            workflow_instance = self.env['tazweed.workflow.instance'].create({
                'name': f'{self.workflow_id.name} - {record.name if record else "Manual"}',
                'workflow_id': self.workflow_id.id,
                'reference_model': record._name if record else None,
                'reference_id': record.id if record else None,
                'context_data': {
                    'trigger_id': self.id,
                    'trigger_type': self.trigger_type
                } if self.pass_context else None
            })
            
            # Start workflow
            workflow_instance.action_start()
            
            return True
        
        return False
