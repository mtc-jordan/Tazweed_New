"""
Tazweed Automated Workflows - Workflow Execution Log Model
Logs all workflow executions and actions
"""

from odoo import models, fields, api
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class WorkflowExecutionLog(models.Model):
    """Workflow Execution Log Model"""
    
    _name = 'tazweed.workflow.execution.log'
    _description = 'Workflow Execution Log'
    _order = 'create_date desc'

    # ============================================================
    # Basic Information
    # ============================================================
    
    instance_id = fields.Many2one(
        'tazweed.workflow.instance',
        string='Workflow Instance',
        required=True,
        ondelete='cascade'
    )
    
    # ============================================================
    # Action Details
    # ============================================================
    
    action = fields.Selection([
        ('created', 'Created'),
        ('started', 'Started'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('step_executed', 'Step Executed'),
        ('notification_sent', 'Notification Sent'),
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Info')
    ], string='Action', required=True)
    
    description = fields.Text('Description')
    
    # ============================================================
    # Execution Details
    # ============================================================
    
    executed_by = fields.Many2one(
        'res.users',
        'Executed By',
        readonly=True,
        default=lambda self: self.env.user
    )
    
    executed_date = fields.Datetime(
        'Executed Date',
        readonly=True,
        default=fields.Datetime.now
    )
    
    # ============================================================
    # Additional Data
    # ============================================================
    
    additional_data = fields.Json('Additional Data', help='Extra information about the action')
    
    # ============================================================
    # Methods
    # ============================================================
    
    @api.model
    def create(self, vals):
        """Create execution log"""
        vals['executed_by'] = self.env.user.id
        return super().create(vals)
