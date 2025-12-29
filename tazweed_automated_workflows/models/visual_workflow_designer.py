# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import json
import uuid


class VisualWorkflowDesigner(models.Model):
    """Visual Workflow Designer - Drag-drop workflow builder"""
    _name = 'visual.workflow.designer'
    _description = 'Visual Workflow Designer'
    _order = 'name'

    name = fields.Char(string='Designer Name', required=True)
    description = fields.Text(string='Description')
    
    # Canvas Settings
    canvas_width = fields.Integer(string='Canvas Width', default=1200)
    canvas_height = fields.Integer(string='Canvas Height', default=800)
    grid_size = fields.Integer(string='Grid Size', default=20)
    snap_to_grid = fields.Boolean(string='Snap to Grid', default=True)
    show_grid = fields.Boolean(string='Show Grid', default=True)
    zoom_level = fields.Float(string='Zoom Level (%)', default=100.0)
    
    # Design Data (JSON)
    design_data = fields.Text(string='Design Data (JSON)', default='{}')
    nodes_json = fields.Text(string='Nodes JSON', default='[]')
    connections_json = fields.Text(string='Connections JSON', default='[]')
    
    # Related Workflow
    workflow_definition_id = fields.Many2one('tazweed.workflow.definition', string='Workflow Definition')
    
    # Node Elements
    node_ids = fields.One2many('visual.workflow.node', 'designer_id', string='Nodes')
    connection_ids = fields.One2many('visual.workflow.connection', 'designer_id', string='Connections')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('designing', 'Designing'),
        ('validated', 'Validated'),
        ('published', 'Published'),
        ('archived', 'Archived')
    ], string='Status', default='draft', tracking=True)
    
    # Metadata
    active = fields.Boolean(string='Active', default=True)
    last_modified = fields.Datetime(string='Last Modified', readonly=True)
    version = fields.Integer(string='Version', default=1)
    
    # Statistics
    node_count = fields.Integer(string='Node Count', compute='_compute_statistics')
    connection_count = fields.Integer(string='Connection Count', compute='_compute_statistics')
    
    @api.depends('node_ids', 'connection_ids')
    def _compute_statistics(self):
        for record in self:
            record.node_count = len(record.node_ids)
            record.connection_count = len(record.connection_ids)
    
    def action_start_designing(self):
        """Start the design process"""
        self.write({
            'state': 'designing',
            'last_modified': fields.Datetime.now()
        })
    
    def action_validate_design(self):
        """Validate the workflow design"""
        self.ensure_one()
        
        # Check for start node
        start_nodes = self.node_ids.filtered(lambda n: n.node_type == 'start')
        if not start_nodes:
            raise ValidationError("Workflow must have at least one Start node.")
        
        # Check for end node
        end_nodes = self.node_ids.filtered(lambda n: n.node_type == 'end')
        if not end_nodes:
            raise ValidationError("Workflow must have at least one End node.")
        
        # Check all nodes are connected
        for node in self.node_ids:
            if node.node_type not in ['start', 'end']:
                incoming = self.connection_ids.filtered(lambda c: c.target_node_id == node)
                outgoing = self.connection_ids.filtered(lambda c: c.source_node_id == node)
                if not incoming or not outgoing:
                    raise ValidationError(f"Node '{node.name}' is not properly connected.")
        
        self.write({
            'state': 'validated',
            'last_modified': fields.Datetime.now()
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Validation Successful',
                'message': 'Workflow design is valid and ready to publish.',
                'type': 'success',
            }
        }
    
    def action_publish(self):
        """Publish the workflow design"""
        self.ensure_one()
        if self.state != 'validated':
            raise UserError("Please validate the design before publishing.")
        
        # Generate workflow definition from design
        self._generate_workflow_definition()
        
        self.write({
            'state': 'published',
            'version': self.version + 1,
            'last_modified': fields.Datetime.now()
        })
    
    def _generate_workflow_definition(self):
        """Generate workflow definition from visual design"""
        # This would convert the visual design to actual workflow definition
        pass
    
    def action_export_json(self):
        """Export design as JSON"""
        self.ensure_one()
        design = {
            'name': self.name,
            'version': self.version,
            'canvas': {
                'width': self.canvas_width,
                'height': self.canvas_height,
                'grid_size': self.grid_size
            },
            'nodes': [{
                'id': node.node_uuid,
                'type': node.node_type,
                'name': node.name,
                'x': node.position_x,
                'y': node.position_y,
                'config': json.loads(node.config_json or '{}')
            } for node in self.node_ids],
            'connections': [{
                'source': conn.source_node_id.node_uuid,
                'target': conn.target_node_id.node_uuid,
                'condition': conn.condition
            } for conn in self.connection_ids]
        }
        return json.dumps(design, indent=2)
    
    def action_import_json(self, json_data):
        """Import design from JSON"""
        self.ensure_one()
        try:
            design = json.loads(json_data)
            # Import nodes and connections
            # Implementation details...
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format.")


class VisualWorkflowNode(models.Model):
    """Visual Workflow Node - Individual node in the designer"""
    _name = 'visual.workflow.node'
    _description = 'Visual Workflow Node'
    _order = 'sequence'

    designer_id = fields.Many2one('visual.workflow.designer', string='Designer', required=True, ondelete='cascade')
    node_uuid = fields.Char(string='Node UUID', default=lambda self: str(uuid.uuid4()), readonly=True)
    
    name = fields.Char(string='Node Name', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Node Type
    node_type = fields.Selection([
        ('start', 'Start'),
        ('end', 'End'),
        ('action', 'Action'),
        ('decision', 'Decision'),
        ('approval', 'Approval'),
        ('notification', 'Notification'),
        ('delay', 'Delay'),
        ('subprocess', 'Sub-Process'),
        ('parallel', 'Parallel Gateway'),
        ('merge', 'Merge Gateway'),
        ('script', 'Script'),
        ('webhook', 'Webhook'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('assignment', 'Assignment'),
        ('loop', 'Loop'),
    ], string='Node Type', required=True, default='action')
    
    # Position on Canvas
    position_x = fields.Integer(string='X Position', default=100)
    position_y = fields.Integer(string='Y Position', default=100)
    width = fields.Integer(string='Width', default=150)
    height = fields.Integer(string='Height', default=80)
    
    # Visual Properties
    color = fields.Char(string='Color', default='#4A90D9')
    icon = fields.Char(string='Icon', default='fa-cog')
    shape = fields.Selection([
        ('rectangle', 'Rectangle'),
        ('rounded', 'Rounded Rectangle'),
        ('diamond', 'Diamond'),
        ('circle', 'Circle'),
        ('parallelogram', 'Parallelogram'),
    ], string='Shape', default='rounded')
    
    # Configuration
    config_json = fields.Text(string='Configuration (JSON)', default='{}')
    
    # Action Configuration
    action_type = fields.Selection([
        ('create', 'Create Record'),
        ('update', 'Update Record'),
        ('delete', 'Delete Record'),
        ('execute', 'Execute Method'),
        ('api_call', 'API Call'),
        ('custom', 'Custom Action'),
    ], string='Action Type')
    target_model = fields.Char(string='Target Model')
    target_method = fields.Char(string='Target Method')
    
    # Approval Configuration
    approver_type = fields.Selection([
        ('user', 'Specific User'),
        ('group', 'User Group'),
        ('manager', 'Manager'),
        ('role', 'Role-based'),
    ], string='Approver Type')
    approver_user_id = fields.Many2one('res.users', string='Approver User')
    approver_group_id = fields.Many2one('res.groups', string='Approver Group')
    
    # Notification Configuration
    notification_template_id = fields.Many2one('mail.template', string='Email Template')
    
    # Delay Configuration
    delay_type = fields.Selection([
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('business_days', 'Business Days'),
    ], string='Delay Type')
    delay_value = fields.Integer(string='Delay Value', default=1)
    
    # Connections
    incoming_connection_ids = fields.One2many('visual.workflow.connection', 'target_node_id', string='Incoming')
    outgoing_connection_ids = fields.One2many('visual.workflow.connection', 'source_node_id', string='Outgoing')
    
    @api.model
    def get_node_palette(self):
        """Return available node types for the palette"""
        return [
            {'type': 'start', 'name': 'Start', 'icon': 'fa-play-circle', 'color': '#28a745', 'shape': 'circle'},
            {'type': 'end', 'name': 'End', 'icon': 'fa-stop-circle', 'color': '#dc3545', 'shape': 'circle'},
            {'type': 'action', 'name': 'Action', 'icon': 'fa-cog', 'color': '#4A90D9', 'shape': 'rounded'},
            {'type': 'decision', 'name': 'Decision', 'icon': 'fa-code-branch', 'color': '#ffc107', 'shape': 'diamond'},
            {'type': 'approval', 'name': 'Approval', 'icon': 'fa-check-circle', 'color': '#17a2b8', 'shape': 'rounded'},
            {'type': 'notification', 'name': 'Notification', 'icon': 'fa-bell', 'color': '#6f42c1', 'shape': 'rounded'},
            {'type': 'delay', 'name': 'Delay', 'icon': 'fa-clock', 'color': '#fd7e14', 'shape': 'rounded'},
            {'type': 'email', 'name': 'Email', 'icon': 'fa-envelope', 'color': '#20c997', 'shape': 'rounded'},
            {'type': 'webhook', 'name': 'Webhook', 'icon': 'fa-globe', 'color': '#6610f2', 'shape': 'rounded'},
            {'type': 'parallel', 'name': 'Parallel', 'icon': 'fa-code-branch', 'color': '#e83e8c', 'shape': 'diamond'},
        ]


class VisualWorkflowConnection(models.Model):
    """Visual Workflow Connection - Connection between nodes"""
    _name = 'visual.workflow.connection'
    _description = 'Visual Workflow Connection'

    designer_id = fields.Many2one('visual.workflow.designer', string='Designer', required=True, ondelete='cascade')
    connection_uuid = fields.Char(string='Connection UUID', default=lambda self: str(uuid.uuid4()), readonly=True)
    
    name = fields.Char(string='Connection Name')
    source_node_id = fields.Many2one('visual.workflow.node', string='Source Node', required=True, ondelete='cascade')
    target_node_id = fields.Many2one('visual.workflow.node', string='Target Node', required=True, ondelete='cascade')
    
    # Connection Type
    connection_type = fields.Selection([
        ('normal', 'Normal'),
        ('conditional', 'Conditional'),
        ('default', 'Default'),
        ('error', 'Error Handler'),
    ], string='Connection Type', default='normal')
    
    # Condition (for decision nodes)
    condition = fields.Char(string='Condition')
    condition_expression = fields.Text(string='Condition Expression')
    
    # Visual Properties
    line_color = fields.Char(string='Line Color', default='#666666')
    line_style = fields.Selection([
        ('solid', 'Solid'),
        ('dashed', 'Dashed'),
        ('dotted', 'Dotted'),
    ], string='Line Style', default='solid')
    line_width = fields.Integer(string='Line Width', default=2)
    
    # Label
    label = fields.Char(string='Label')
    label_position = fields.Float(string='Label Position', default=0.5)  # 0-1 along the line
    
    @api.constrains('source_node_id', 'target_node_id')
    def _check_connection(self):
        for record in self:
            if record.source_node_id == record.target_node_id:
                raise ValidationError("A node cannot connect to itself.")
