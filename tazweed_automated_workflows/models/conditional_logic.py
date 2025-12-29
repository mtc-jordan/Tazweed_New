# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
import json


class WorkflowConditionGroup(models.Model):
    """Workflow Condition Group - Container for multiple conditions"""
    _name = 'workflow.condition.group'
    _description = 'Workflow Condition Group'
    _order = 'sequence'

    name = fields.Char(string='Group Name', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Parent Reference
    workflow_id = fields.Many2one('tazweed.workflow.definition', string='Workflow')
    node_id = fields.Many2one('visual.workflow.node', string='Node')
    
    # Logic Operator
    logic_operator = fields.Selection([
        ('and', 'AND - All conditions must be true'),
        ('or', 'OR - Any condition must be true'),
        ('not', 'NOT - Negate the result'),
        ('xor', 'XOR - Exactly one must be true'),
    ], string='Logic Operator', default='and', required=True)
    
    # Conditions
    condition_ids = fields.One2many('workflow.condition', 'group_id', string='Conditions')
    
    # Nested Groups
    parent_group_id = fields.Many2one('workflow.condition.group', string='Parent Group')
    child_group_ids = fields.One2many('workflow.condition.group', 'parent_group_id', string='Child Groups')
    
    # Result
    result = fields.Boolean(string='Evaluation Result', compute='_compute_result', store=False)
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('condition_ids', 'child_group_ids', 'logic_operator')
    def _compute_result(self):
        for record in self:
            record.result = False  # Computed at runtime
    
    def evaluate(self, context=None):
        """Evaluate the condition group with given context"""
        self.ensure_one()
        context = context or {}
        
        # Evaluate all conditions
        condition_results = [cond.evaluate(context) for cond in self.condition_ids]
        
        # Evaluate child groups
        child_results = [child.evaluate(context) for child in self.child_group_ids]
        
        all_results = condition_results + child_results
        
        if not all_results:
            return True  # Empty group is always true
        
        if self.logic_operator == 'and':
            return all(all_results)
        elif self.logic_operator == 'or':
            return any(all_results)
        elif self.logic_operator == 'not':
            return not all(all_results)
        elif self.logic_operator == 'xor':
            return sum(all_results) == 1
        
        return False


class WorkflowCondition(models.Model):
    """Workflow Condition - Individual condition rule"""
    _name = 'workflow.condition'
    _description = 'Workflow Condition'
    _order = 'sequence'

    name = fields.Char(string='Condition Name')
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Parent Group
    group_id = fields.Many2one('workflow.condition.group', string='Condition Group', ondelete='cascade')
    
    # Condition Type
    condition_type = fields.Selection([
        ('field', 'Field Comparison'),
        ('expression', 'Python Expression'),
        ('date', 'Date Condition'),
        ('user', 'User Condition'),
        ('record', 'Record Condition'),
        ('custom', 'Custom Function'),
    ], string='Condition Type', required=True, default='field')
    
    # Field Comparison
    model_id = fields.Many2one('ir.model', string='Model')
    field_id = fields.Many2one('ir.model.fields', string='Field', 
                               domain="[('model_id', '=', model_id)]")
    field_name = fields.Char(string='Field Name', related='field_id.name')
    
    # Operator
    operator = fields.Selection([
        ('=', 'Equals'),
        ('!=', 'Not Equals'),
        ('>', 'Greater Than'),
        ('>=', 'Greater Than or Equal'),
        ('<', 'Less Than'),
        ('<=', 'Less Than or Equal'),
        ('in', 'In List'),
        ('not in', 'Not In List'),
        ('like', 'Contains'),
        ('ilike', 'Contains (Case Insensitive)'),
        ('not like', 'Does Not Contain'),
        ('is_set', 'Is Set'),
        ('is_not_set', 'Is Not Set'),
        ('changed', 'Has Changed'),
        ('changed_to', 'Changed To'),
        ('changed_from', 'Changed From'),
    ], string='Operator', default='=')
    
    # Value
    value_type = fields.Selection([
        ('static', 'Static Value'),
        ('field', 'Another Field'),
        ('expression', 'Expression'),
        ('context', 'Context Variable'),
        ('current_user', 'Current User'),
        ('current_date', 'Current Date'),
        ('current_datetime', 'Current DateTime'),
    ], string='Value Type', default='static')
    
    value_static = fields.Char(string='Static Value')
    value_field_id = fields.Many2one('ir.model.fields', string='Compare Field')
    value_expression = fields.Text(string='Value Expression')
    value_context_key = fields.Char(string='Context Key')
    
    # Date Conditions
    date_operator = fields.Selection([
        ('before', 'Before'),
        ('after', 'After'),
        ('between', 'Between'),
        ('today', 'Is Today'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
        ('this_year', 'This Year'),
        ('past_days', 'In Past N Days'),
        ('next_days', 'In Next N Days'),
        ('overdue', 'Is Overdue'),
    ], string='Date Operator')
    date_value = fields.Date(string='Date Value')
    date_value_end = fields.Date(string='Date Value End')
    date_days = fields.Integer(string='Number of Days')
    
    # User Conditions
    user_operator = fields.Selection([
        ('is_current', 'Is Current User'),
        ('is_manager', 'Is Manager Of'),
        ('in_group', 'In Group'),
        ('has_role', 'Has Role'),
        ('is_follower', 'Is Follower'),
        ('is_assignee', 'Is Assignee'),
    ], string='User Operator')
    user_id = fields.Many2one('res.users', string='User')
    group_id_check = fields.Many2one('res.groups', string='Group')
    
    # Record Conditions
    record_operator = fields.Selection([
        ('exists', 'Record Exists'),
        ('not_exists', 'Record Does Not Exist'),
        ('count_gt', 'Count Greater Than'),
        ('count_lt', 'Count Less Than'),
        ('count_eq', 'Count Equals'),
    ], string='Record Operator')
    record_domain = fields.Text(string='Record Domain')
    record_count = fields.Integer(string='Record Count')
    
    # Python Expression
    python_expression = fields.Text(string='Python Expression')
    
    # Custom Function
    custom_function = fields.Char(string='Custom Function Name')
    custom_params = fields.Text(string='Custom Parameters (JSON)')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    def evaluate(self, context=None):
        """Evaluate the condition with given context"""
        self.ensure_one()
        context = context or {}
        
        try:
            if self.condition_type == 'field':
                return self._evaluate_field_condition(context)
            elif self.condition_type == 'expression':
                return self._evaluate_expression(context)
            elif self.condition_type == 'date':
                return self._evaluate_date_condition(context)
            elif self.condition_type == 'user':
                return self._evaluate_user_condition(context)
            elif self.condition_type == 'record':
                return self._evaluate_record_condition(context)
            elif self.condition_type == 'custom':
                return self._evaluate_custom_condition(context)
        except Exception as e:
            # Log error and return False
            return False
        
        return False
    
    def _evaluate_field_condition(self, context):
        """Evaluate field comparison condition"""
        record = context.get('record')
        if not record or not self.field_name:
            return False
        
        field_value = record.get(self.field_name) if isinstance(record, dict) else getattr(record, self.field_name, None)
        compare_value = self._get_compare_value(context)
        
        if self.operator == '=':
            return field_value == compare_value
        elif self.operator == '!=':
            return field_value != compare_value
        elif self.operator == '>':
            return field_value > compare_value
        elif self.operator == '>=':
            return field_value >= compare_value
        elif self.operator == '<':
            return field_value < compare_value
        elif self.operator == '<=':
            return field_value <= compare_value
        elif self.operator == 'in':
            return field_value in (compare_value if isinstance(compare_value, (list, tuple)) else [compare_value])
        elif self.operator == 'not in':
            return field_value not in (compare_value if isinstance(compare_value, (list, tuple)) else [compare_value])
        elif self.operator == 'like':
            return str(compare_value) in str(field_value)
        elif self.operator == 'ilike':
            return str(compare_value).lower() in str(field_value).lower()
        elif self.operator == 'is_set':
            return bool(field_value)
        elif self.operator == 'is_not_set':
            return not bool(field_value)
        
        return False
    
    def _get_compare_value(self, context):
        """Get the comparison value based on value_type"""
        if self.value_type == 'static':
            return self.value_static
        elif self.value_type == 'field':
            record = context.get('record')
            if record and self.value_field_id:
                return getattr(record, self.value_field_id.name, None)
        elif self.value_type == 'expression':
            return safe_eval(self.value_expression or 'False', context)
        elif self.value_type == 'context':
            return context.get(self.value_context_key)
        elif self.value_type == 'current_user':
            return self.env.user.id
        elif self.value_type == 'current_date':
            return fields.Date.today()
        elif self.value_type == 'current_datetime':
            return fields.Datetime.now()
        return None
    
    def _evaluate_expression(self, context):
        """Evaluate Python expression"""
        if not self.python_expression:
            return False
        
        eval_context = {
            'env': self.env,
            'user': self.env.user,
            'date': fields.Date,
            'datetime': fields.Datetime,
            **context
        }
        
        return bool(safe_eval(self.python_expression, eval_context))
    
    def _evaluate_date_condition(self, context):
        """Evaluate date-based condition"""
        from datetime import date, timedelta
        
        record = context.get('record')
        if not record or not self.field_name:
            return False
        
        field_value = record.get(self.field_name) if isinstance(record, dict) else getattr(record, self.field_name, None)
        if not field_value:
            return False
        
        today = date.today()
        
        if self.date_operator == 'today':
            return field_value == today
        elif self.date_operator == 'before':
            return field_value < self.date_value
        elif self.date_operator == 'after':
            return field_value > self.date_value
        elif self.date_operator == 'between':
            return self.date_value <= field_value <= self.date_value_end
        elif self.date_operator == 'past_days':
            return today - timedelta(days=self.date_days) <= field_value <= today
        elif self.date_operator == 'next_days':
            return today <= field_value <= today + timedelta(days=self.date_days)
        elif self.date_operator == 'overdue':
            return field_value < today
        
        return False
    
    def _evaluate_user_condition(self, context):
        """Evaluate user-based condition"""
        current_user = self.env.user
        
        if self.user_operator == 'is_current':
            return context.get('user_id') == current_user.id
        elif self.user_operator == 'in_group':
            return self.group_id_check in current_user.groups_id
        
        return False
    
    def _evaluate_record_condition(self, context):
        """Evaluate record-based condition"""
        if not self.model_id or not self.record_domain:
            return False
        
        domain = safe_eval(self.record_domain or '[]')
        count = self.env[self.model_id.model].search_count(domain)
        
        if self.record_operator == 'exists':
            return count > 0
        elif self.record_operator == 'not_exists':
            return count == 0
        elif self.record_operator == 'count_gt':
            return count > self.record_count
        elif self.record_operator == 'count_lt':
            return count < self.record_count
        elif self.record_operator == 'count_eq':
            return count == self.record_count
        
        return False
    
    def _evaluate_custom_condition(self, context):
        """Evaluate custom function condition"""
        if not self.custom_function:
            return False
        
        # Call custom function if it exists
        if hasattr(self, self.custom_function):
            params = json.loads(self.custom_params or '{}')
            return getattr(self, self.custom_function)(context, **params)
        
        return False


class WorkflowDecisionTable(models.Model):
    """Workflow Decision Table - Decision matrix for complex logic"""
    _name = 'workflow.decision.table'
    _description = 'Workflow Decision Table'

    name = fields.Char(string='Table Name', required=True)
    description = fields.Text(string='Description')
    
    # Reference
    workflow_id = fields.Many2one('tazweed.workflow.definition', string='Workflow')
    
    # Hit Policy
    hit_policy = fields.Selection([
        ('first', 'First Match'),
        ('unique', 'Unique Match'),
        ('any', 'Any Match'),
        ('priority', 'Priority Order'),
        ('collect', 'Collect All'),
        ('sum', 'Sum Results'),
        ('min', 'Minimum Result'),
        ('max', 'Maximum Result'),
    ], string='Hit Policy', default='first', required=True)
    
    # Input/Output Columns
    input_column_ids = fields.One2many('workflow.decision.column', 'table_id', 
                                       string='Input Columns', domain=[('column_type', '=', 'input')])
    output_column_ids = fields.One2many('workflow.decision.column', 'table_id', 
                                        string='Output Columns', domain=[('column_type', '=', 'output')])
    
    # Rules
    rule_ids = fields.One2many('workflow.decision.rule', 'table_id', string='Rules')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    def evaluate(self, inputs):
        """Evaluate the decision table with given inputs"""
        self.ensure_one()
        results = []
        
        for rule in self.rule_ids.sorted('priority'):
            if rule.evaluate(inputs):
                result = rule.get_outputs()
                
                if self.hit_policy == 'first':
                    return result
                elif self.hit_policy == 'unique':
                    if results:
                        raise ValidationError("Multiple rules matched in unique hit policy.")
                    return result
                else:
                    results.append(result)
        
        if self.hit_policy in ['collect', 'any']:
            return results
        elif self.hit_policy == 'sum':
            return sum(r.get('value', 0) for r in results)
        elif self.hit_policy == 'min':
            return min(r.get('value', 0) for r in results) if results else None
        elif self.hit_policy == 'max':
            return max(r.get('value', 0) for r in results) if results else None
        
        return None


class WorkflowDecisionColumn(models.Model):
    """Workflow Decision Column - Column definition for decision table"""
    _name = 'workflow.decision.column'
    _description = 'Workflow Decision Column'
    _order = 'sequence'

    table_id = fields.Many2one('workflow.decision.table', string='Decision Table', required=True, ondelete='cascade')
    name = fields.Char(string='Column Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    column_type = fields.Selection([
        ('input', 'Input'),
        ('output', 'Output'),
    ], string='Column Type', required=True)
    
    data_type = fields.Selection([
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('date', 'Date'),
        ('selection', 'Selection'),
    ], string='Data Type', default='string')
    
    # For selection type
    selection_values = fields.Text(string='Selection Values (JSON)')
    
    # Field reference
    field_id = fields.Many2one('ir.model.fields', string='Field Reference')


class WorkflowDecisionRule(models.Model):
    """Workflow Decision Rule - Individual rule in decision table"""
    _name = 'workflow.decision.rule'
    _description = 'Workflow Decision Rule'
    _order = 'priority'

    table_id = fields.Many2one('workflow.decision.table', string='Decision Table', required=True, ondelete='cascade')
    name = fields.Char(string='Rule Name')
    priority = fields.Integer(string='Priority', default=10)
    
    # Conditions (JSON: {column_id: {operator: value}})
    conditions_json = fields.Text(string='Conditions (JSON)', default='{}')
    
    # Outputs (JSON: {column_id: value})
    outputs_json = fields.Text(string='Outputs (JSON)', default='{}')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    def evaluate(self, inputs):
        """Evaluate if this rule matches the inputs"""
        conditions = json.loads(self.conditions_json or '{}')
        
        for col_id, condition in conditions.items():
            input_value = inputs.get(col_id)
            operator = condition.get('operator', '=')
            expected = condition.get('value')
            
            if operator == '=' and input_value != expected:
                return False
            elif operator == '!=' and input_value == expected:
                return False
            # Add more operators as needed
        
        return True
    
    def get_outputs(self):
        """Get the output values for this rule"""
        return json.loads(self.outputs_json or '{}')
