# -*- coding: utf-8 -*-
"""
Employee Self-Onboarding Module
===============================
Digital onboarding workflow with document upload, task tracking,
and automated notifications for new employee onboarding.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class OnboardingTemplate(models.Model):
    """Template for onboarding workflows"""
    _name = 'employee.onboarding.template'
    _description = 'Onboarding Template'
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Template configuration
    department_ids = fields.Many2many(
        'hr.department',
        string='Applicable Departments',
        help='Leave empty to apply to all departments'
    )
    job_ids = fields.Many2many(
        'hr.job',
        string='Applicable Job Positions',
        help='Leave empty to apply to all positions'
    )
    
    # Tasks
    task_ids = fields.One2many(
        'employee.onboarding.template.task',
        'template_id',
        string='Onboarding Tasks'
    )
    
    # Documents required
    required_document_type_ids = fields.Many2many(
        'tazweed.document.type',
        string='Required Documents',
        help='Documents that must be uploaded during onboarding'
    )
    
    # Timeline
    default_duration_days = fields.Integer(
        string='Default Duration (Days)',
        default=30,
        help='Default number of days to complete onboarding'
    )
    
    # Statistics
    onboarding_count = fields.Integer(
        string='Onboarding Count',
        compute='_compute_onboarding_count'
    )
    
    def _compute_onboarding_count(self):
        for template in self:
            template.onboarding_count = self.env['employee.onboarding'].search_count([
                ('template_id', '=', template.id)
            ])
    
    def action_view_onboardings(self):
        """View onboardings using this template"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Onboardings'),
            'res_model': 'employee.onboarding',
            'view_mode': 'tree,form,kanban',
            'domain': [('template_id', '=', self.id)],
            'context': {'default_template_id': self.id},
        }


class OnboardingTemplateTask(models.Model):
    """Tasks within an onboarding template"""
    _name = 'employee.onboarding.template.task'
    _description = 'Onboarding Template Task'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'employee.onboarding.template',
        string='Template',
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(string='Task Name', required=True)
    description = fields.Html(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Task configuration
    task_type = fields.Selection([
        ('document', 'Document Upload'),
        ('form', 'Form Completion'),
        ('training', 'Training/Course'),
        ('meeting', 'Meeting/Introduction'),
        ('it_setup', 'IT Setup'),
        ('access', 'Access/Permissions'),
        ('other', 'Other Task'),
    ], string='Task Type', default='other', required=True)
    
    # Assignment
    assigned_to = fields.Selection([
        ('employee', 'New Employee'),
        ('manager', 'Manager'),
        ('hr', 'HR Department'),
        ('it', 'IT Department'),
        ('admin', 'Administration'),
    ], string='Assigned To', default='employee', required=True)
    
    # Timing
    days_before_start = fields.Integer(
        string='Days Before Start',
        default=0,
        help='Number of days before employee start date to begin this task'
    )
    days_to_complete = fields.Integer(
        string='Days to Complete',
        default=7,
        help='Number of days allowed to complete this task'
    )
    
    # Dependencies
    depends_on_task_ids = fields.Many2many(
        'employee.onboarding.template.task',
        'onboarding_task_dependency_rel',
        'task_id',
        'depends_on_id',
        string='Depends On',
        domain="[('template_id', '=', template_id), ('id', '!=', id)]"
    )
    
    # Document type (if task_type is document)
    document_type_id = fields.Many2one(
        'tazweed.document.type',
        string='Document Type',
        help='Required document type for document upload tasks'
    )
    
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    
    # Instructions
    instructions = fields.Html(string='Instructions')
    help_url = fields.Char(string='Help URL')


class EmployeeOnboarding(models.Model):
    """Employee Onboarding Process"""
    _name = 'employee.onboarding'
    _description = 'Employee Onboarding'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    # Employee information
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Portal User',
        related='employee_id.user_id',
        store=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        related='employee_id.job_id',
        store=True
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        related='employee_id.parent_id',
        store=True
    )
    
    # Template
    template_id = fields.Many2one(
        'employee.onboarding.template',
        string='Onboarding Template',
        tracking=True
    )
    
    # Dates
    start_date = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
        help='Employee start date'
    )
    target_completion_date = fields.Date(
        string='Target Completion',
        compute='_compute_target_completion_date',
        store=True
    )
    actual_completion_date = fields.Date(
        string='Actual Completion',
        readonly=True,
        tracking=True
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Start'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Tasks
    task_ids = fields.One2many(
        'employee.onboarding.task',
        'onboarding_id',
        string='Tasks'
    )
    
    # Progress
    progress = fields.Float(
        string='Progress (%)',
        compute='_compute_progress',
        store=True
    )
    tasks_total = fields.Integer(
        string='Total Tasks',
        compute='_compute_progress',
        store=True
    )
    tasks_completed = fields.Integer(
        string='Completed Tasks',
        compute='_compute_progress',
        store=True
    )
    
    # Documents
    document_ids = fields.One2many(
        'tazweed.employee.document',
        'onboarding_id',
        string='Uploaded Documents'
    )
    documents_required = fields.Integer(
        string='Required Documents',
        compute='_compute_document_progress'
    )
    documents_uploaded = fields.Integer(
        string='Uploaded Documents',
        compute='_compute_document_progress'
    )
    
    # Notes
    notes = fields.Html(string='Notes')
    hr_notes = fields.Html(string='HR Notes')
    
    # Welcome message
    welcome_message = fields.Html(
        string='Welcome Message',
        help='Personalized welcome message for the employee'
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'employee.onboarding'
                ) or _('New')
        return super().create(vals_list)
    
    @api.depends('template_id', 'start_date')
    def _compute_target_completion_date(self):
        for onboarding in self:
            if onboarding.start_date and onboarding.template_id:
                days = onboarding.template_id.default_duration_days
                onboarding.target_completion_date = onboarding.start_date + timedelta(days=days)
            else:
                onboarding.target_completion_date = False
    
    @api.depends('task_ids', 'task_ids.state')
    def _compute_progress(self):
        for onboarding in self:
            tasks = onboarding.task_ids
            total = len(tasks)
            completed = len(tasks.filtered(lambda t: t.state == 'completed'))
            
            onboarding.tasks_total = total
            onboarding.tasks_completed = completed
            onboarding.progress = (completed / total * 100) if total > 0 else 0
    
    def _compute_document_progress(self):
        for onboarding in self:
            if onboarding.template_id:
                required = len(onboarding.template_id.required_document_type_ids)
                uploaded = len(onboarding.document_ids)
                onboarding.documents_required = required
                onboarding.documents_uploaded = uploaded
            else:
                onboarding.documents_required = 0
                onboarding.documents_uploaded = 0
    
    def action_generate_tasks(self):
        """Generate tasks from template"""
        self.ensure_one()
        if not self.template_id:
            raise UserError(_('Please select an onboarding template first.'))
        
        # Clear existing tasks
        self.task_ids.unlink()
        
        # Create tasks from template
        for template_task in self.template_id.task_ids:
            # Calculate due date
            due_date = self.start_date - timedelta(days=template_task.days_before_start)
            due_date = due_date + timedelta(days=template_task.days_to_complete)
            
            self.env['employee.onboarding.task'].create({
                'onboarding_id': self.id,
                'template_task_id': template_task.id,
                'name': template_task.name,
                'description': template_task.description,
                'task_type': template_task.task_type,
                'assigned_to': template_task.assigned_to,
                'due_date': due_date,
                'is_mandatory': template_task.is_mandatory,
                'document_type_id': template_task.document_type_id.id,
                'instructions': template_task.instructions,
                'sequence': template_task.sequence,
            })
        
        self.message_post(body=_('Onboarding tasks generated from template: %s') % self.template_id.name)
        return True
    
    def action_start(self):
        """Start the onboarding process"""
        self.ensure_one()
        if not self.task_ids:
            self.action_generate_tasks()
        
        self.write({'state': 'in_progress'})
        
        # Send welcome email to employee
        self._send_welcome_email()
        
        # Create activities for pending tasks
        self._create_task_activities()
        
        return True
    
    def action_complete(self):
        """Mark onboarding as completed"""
        self.ensure_one()
        
        # Check if all mandatory tasks are completed
        mandatory_incomplete = self.task_ids.filtered(
            lambda t: t.is_mandatory and t.state != 'completed'
        )
        if mandatory_incomplete:
            raise UserError(_(
                'Cannot complete onboarding. The following mandatory tasks are not completed:\n%s'
            ) % '\n'.join(mandatory_incomplete.mapped('name')))
        
        self.write({
            'state': 'completed',
            'actual_completion_date': fields.Date.today(),
        })
        
        # Update employee record
        self.employee_id.write({'onboarding_completed': True})
        
        self.message_post(body=_('Onboarding completed successfully!'))
        return True
    
    def action_cancel(self):
        """Cancel the onboarding process"""
        self.ensure_one()
        self.write({'state': 'cancelled'})
        return True
    
    def action_reset_to_draft(self):
        """Reset to draft state"""
        self.ensure_one()
        self.write({'state': 'draft'})
        return True
    
    def _send_welcome_email(self):
        """Send welcome email to new employee"""
        self.ensure_one()
        template = self.env.ref(
            'tazweed_core.email_template_onboarding_welcome',
            raise_if_not_found=False
        )
        if template and self.employee_id.work_email:
            template.send_mail(self.id, force_send=True)
    
    def _create_task_activities(self):
        """Create activities for pending tasks"""
        self.ensure_one()
        for task in self.task_ids.filtered(lambda t: t.state == 'pending'):
            # Determine responsible user
            if task.assigned_to == 'employee' and self.user_id:
                user = self.user_id
            elif task.assigned_to == 'manager' and self.manager_id.user_id:
                user = self.manager_id.user_id
            else:
                user = self.env.user
            
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=task.due_date,
                summary=task.name,
                note=task.description,
                user_id=user.id,
            )
    
    def action_view_portal(self):
        """Open the onboarding portal view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/my/onboarding/{self.id}',
            'target': 'self',
        }


class EmployeeOnboardingTask(models.Model):
    """Individual task in an onboarding process"""
    _name = 'employee.onboarding.task'
    _description = 'Onboarding Task'
    _order = 'sequence, id'

    onboarding_id = fields.Many2one(
        'employee.onboarding',
        string='Onboarding',
        required=True,
        ondelete='cascade'
    )
    template_task_id = fields.Many2one(
        'employee.onboarding.template.task',
        string='Template Task'
    )
    
    name = fields.Char(string='Task Name', required=True)
    description = fields.Html(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    
    task_type = fields.Selection([
        ('document', 'Document Upload'),
        ('form', 'Form Completion'),
        ('training', 'Training/Course'),
        ('meeting', 'Meeting/Introduction'),
        ('it_setup', 'IT Setup'),
        ('access', 'Access/Permissions'),
        ('other', 'Other Task'),
    ], string='Task Type', default='other', required=True)
    
    assigned_to = fields.Selection([
        ('employee', 'New Employee'),
        ('manager', 'Manager'),
        ('hr', 'HR Department'),
        ('it', 'IT Department'),
        ('admin', 'Administration'),
    ], string='Assigned To', default='employee', required=True)
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
    ], string='Status', default='pending', tracking=True)
    
    # Dates
    due_date = fields.Date(string='Due Date')
    completed_date = fields.Datetime(string='Completed Date', readonly=True)
    completed_by = fields.Many2one('res.users', string='Completed By', readonly=True)
    
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    is_overdue = fields.Boolean(string='Overdue', compute='_compute_is_overdue')
    
    # Document upload
    document_type_id = fields.Many2one('tazweed.document.type', string='Document Type')
    document_id = fields.Many2one('tazweed.employee.document', string='Uploaded Document')
    
    # Instructions
    instructions = fields.Html(string='Instructions')
    
    # Feedback
    notes = fields.Text(string='Notes')
    
    @api.depends('due_date', 'state')
    def _compute_is_overdue(self):
        today = fields.Date.today()
        for task in self:
            task.is_overdue = (
                task.due_date and 
                task.due_date < today and 
                task.state not in ('completed', 'skipped')
            )
    
    def action_start(self):
        """Start working on the task"""
        self.ensure_one()
        self.write({'state': 'in_progress'})
        return True
    
    def action_complete(self):
        """Mark task as completed"""
        self.ensure_one()
        
        # For document tasks, check if document is uploaded
        if self.task_type == 'document' and not self.document_id:
            raise UserError(_('Please upload the required document before completing this task.'))
        
        self.write({
            'state': 'completed',
            'completed_date': fields.Datetime.now(),
            'completed_by': self.env.user.id,
        })
        
        # Check if all tasks are completed
        self.onboarding_id._check_completion()
        
        return True
    
    def action_skip(self):
        """Skip a non-mandatory task"""
        self.ensure_one()
        if self.is_mandatory:
            raise UserError(_('Cannot skip a mandatory task.'))
        
        self.write({'state': 'skipped'})
        return True
    
    def action_upload_document(self):
        """Open document upload wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Upload Document'),
            'res_model': 'tazweed.employee.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.onboarding_id.employee_id.id,
                'default_document_type_id': self.document_type_id.id,
                'default_onboarding_id': self.onboarding_id.id,
                'default_onboarding_task_id': self.id,
            },
        }


class EmployeeDocument(models.Model):
    """Extend employee document for onboarding"""
    _inherit = 'tazweed.employee.document'
    
    onboarding_id = fields.Many2one(
        'employee.onboarding',
        string='Onboarding',
        help='Related onboarding process'
    )
    onboarding_task_id = fields.Many2one(
        'employee.onboarding.task',
        string='Onboarding Task',
        help='Related onboarding task'
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        
        # Link document to onboarding task if applicable
        for record in records:
            if record.onboarding_task_id:
                record.onboarding_task_id.write({
                    'document_id': record.id,
                })
        
        return records


class HrEmployee(models.Model):
    """Extend HR Employee for onboarding"""
    _inherit = 'hr.employee'
    
    onboarding_ids = fields.One2many(
        'employee.onboarding',
        'employee_id',
        string='Onboarding Processes'
    )
    onboarding_completed = fields.Boolean(
        string='Onboarding Completed',
        default=False,
        tracking=True
    )
    current_onboarding_id = fields.Many2one(
        'employee.onboarding',
        string='Current Onboarding',
        compute='_compute_current_onboarding'
    )
    onboarding_progress = fields.Float(
        string='Onboarding Progress',
        compute='_compute_current_onboarding'
    )
    
    def _compute_current_onboarding(self):
        for employee in self:
            onboarding = self.env['employee.onboarding'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['pending', 'in_progress']),
            ], limit=1, order='create_date desc')
            
            employee.current_onboarding_id = onboarding
            employee.onboarding_progress = onboarding.progress if onboarding else 0
    
    def action_start_onboarding(self):
        """Start onboarding for this employee"""
        self.ensure_one()
        
        # Find appropriate template
        template = self.env['employee.onboarding.template'].search([
            '|',
            ('department_ids', '=', False),
            ('department_ids', 'in', self.department_id.ids),
            '|',
            ('job_ids', '=', False),
            ('job_ids', 'in', self.job_id.ids),
        ], limit=1)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Start Onboarding'),
            'res_model': 'employee.onboarding',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_employee_id': self.id,
                'default_template_id': template.id if template else False,
                'default_start_date': fields.Date.today(),
            },
        }
    
    def action_view_onboarding(self):
        """View onboarding processes for this employee"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Onboarding'),
            'res_model': 'employee.onboarding',
            'view_mode': 'tree,form,kanban',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
