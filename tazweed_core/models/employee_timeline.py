# -*- coding: utf-8 -*-
"""
Employee Timeline Module
========================
Visual history of employee events and milestones including
promotions, transfers, achievements, and key dates.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class EmployeeTimelineEvent(models.Model):
    """Timeline events for employees"""
    _name = 'employee.timeline.event'
    _description = 'Employee Timeline Event'
    _order = 'event_date desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(string='Event Title', required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    # Event details
    event_type = fields.Selection([
        ('hire', 'Hired'),
        ('promotion', 'Promotion'),
        ('transfer', 'Transfer'),
        ('salary_change', 'Salary Change'),
        ('contract', 'Contract Change'),
        ('achievement', 'Achievement'),
        ('certification', 'Certification'),
        ('training', 'Training Completed'),
        ('award', 'Award/Recognition'),
        ('milestone', 'Work Anniversary'),
        ('leave', 'Extended Leave'),
        ('return', 'Return from Leave'),
        ('warning', 'Warning/Disciplinary'),
        ('probation', 'Probation Status'),
        ('termination', 'Termination'),
        ('resignation', 'Resignation'),
        ('other', 'Other'),
    ], string='Event Type', required=True, default='other')
    
    event_date = fields.Date(
        string='Event Date',
        required=True,
        default=fields.Date.today
    )
    
    # Event categorization
    category = fields.Selection([
        ('career', 'Career'),
        ('compensation', 'Compensation'),
        ('development', 'Development'),
        ('recognition', 'Recognition'),
        ('administrative', 'Administrative'),
        ('compliance', 'Compliance'),
    ], string='Category', compute='_compute_category', store=True)
    
    is_positive = fields.Boolean(
        string='Positive Event',
        compute='_compute_is_positive',
        store=True
    )
    
    # Details
    description = fields.Html(string='Description')
    
    # Related records
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string='Job Position')
    contract_id = fields.Many2one('hr.contract', string='Contract')
    
    # For transfers
    from_department_id = fields.Many2one(
        'hr.department',
        string='From Department'
    )
    to_department_id = fields.Many2one(
        'hr.department',
        string='To Department'
    )
    from_job_id = fields.Many2one('hr.job', string='From Position')
    to_job_id = fields.Many2one('hr.job', string='To Position')
    
    # For salary changes
    previous_salary = fields.Monetary(
        string='Previous Salary',
        currency_field='currency_id'
    )
    new_salary = fields.Monetary(
        string='New Salary',
        currency_field='currency_id'
    )
    salary_change_percentage = fields.Float(
        string='Change %',
        compute='_compute_salary_change'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # For achievements/awards
    achievement_type = fields.Selection([
        ('performance', 'Performance Excellence'),
        ('innovation', 'Innovation'),
        ('leadership', 'Leadership'),
        ('teamwork', 'Teamwork'),
        ('customer', 'Customer Service'),
        ('sales', 'Sales Achievement'),
        ('tenure', 'Long Service'),
        ('other', 'Other'),
    ], string='Achievement Type')
    award_name = fields.Char(string='Award Name')
    
    # For certifications/training
    certification_name = fields.Char(string='Certification/Training Name')
    certification_provider = fields.Char(string='Provider')
    certification_expiry = fields.Date(string='Expiry Date')
    
    # Visibility
    is_public = fields.Boolean(
        string='Public',
        default=True,
        help='Visible to the employee'
    )
    is_featured = fields.Boolean(
        string='Featured',
        default=False,
        help='Highlight this event'
    )
    
    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments'
    )
    
    # Created by
    created_by_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    # Icon and color for display
    icon = fields.Char(
        string='Icon',
        compute='_compute_display_properties'
    )
    color = fields.Char(
        string='Color',
        compute='_compute_display_properties'
    )
    
    @api.depends('event_type')
    def _compute_category(self):
        category_map = {
            'hire': 'career',
            'promotion': 'career',
            'transfer': 'career',
            'salary_change': 'compensation',
            'contract': 'compensation',
            'achievement': 'recognition',
            'certification': 'development',
            'training': 'development',
            'award': 'recognition',
            'milestone': 'recognition',
            'leave': 'administrative',
            'return': 'administrative',
            'warning': 'compliance',
            'probation': 'administrative',
            'termination': 'administrative',
            'resignation': 'administrative',
            'other': 'administrative',
        }
        for event in self:
            event.category = category_map.get(event.event_type, 'administrative')
    
    @api.depends('event_type')
    def _compute_is_positive(self):
        positive_types = ['hire', 'promotion', 'achievement', 'certification', 
                         'training', 'award', 'milestone', 'return']
        for event in self:
            event.is_positive = event.event_type in positive_types
    
    @api.depends('previous_salary', 'new_salary')
    def _compute_salary_change(self):
        for event in self:
            if event.previous_salary and event.new_salary:
                event.salary_change_percentage = (
                    (event.new_salary - event.previous_salary) / event.previous_salary * 100
                )
            else:
                event.salary_change_percentage = 0
    
    @api.depends('event_type')
    def _compute_display_properties(self):
        icon_map = {
            'hire': ('fa-user-plus', '#28a745'),
            'promotion': ('fa-arrow-up', '#17a2b8'),
            'transfer': ('fa-exchange-alt', '#6c757d'),
            'salary_change': ('fa-dollar-sign', '#28a745'),
            'contract': ('fa-file-contract', '#6c757d'),
            'achievement': ('fa-trophy', '#ffc107'),
            'certification': ('fa-certificate', '#17a2b8'),
            'training': ('fa-graduation-cap', '#17a2b8'),
            'award': ('fa-medal', '#ffc107'),
            'milestone': ('fa-star', '#ffc107'),
            'leave': ('fa-plane', '#6c757d'),
            'return': ('fa-undo', '#28a745'),
            'warning': ('fa-exclamation-triangle', '#dc3545'),
            'probation': ('fa-clock', '#ffc107'),
            'termination': ('fa-user-times', '#dc3545'),
            'resignation': ('fa-sign-out-alt', '#6c757d'),
            'other': ('fa-circle', '#6c757d'),
        }
        for event in self:
            icon, color = icon_map.get(event.event_type, ('fa-circle', '#6c757d'))
            event.icon = icon
            event.color = color
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            # Post message to employee
            if record.is_public and record.employee_id:
                record.employee_id.message_post(
                    body=_('Timeline event: %s') % record.name,
                    subject=record.name,
                )
        return records


class EmployeeTimelineTemplate(models.Model):
    """Templates for automatic timeline events"""
    _name = 'employee.timeline.template'
    _description = 'Timeline Event Template'
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Trigger
    trigger_type = fields.Selection([
        ('hire', 'On Hire'),
        ('anniversary', 'Work Anniversary'),
        ('contract_start', 'Contract Start'),
        ('contract_end', 'Contract End'),
        ('promotion', 'On Promotion'),
        ('transfer', 'On Transfer'),
        ('manual', 'Manual'),
    ], string='Trigger', required=True, default='manual')
    
    # For anniversaries
    anniversary_years = fields.Integer(
        string='Years',
        help='Create event on this work anniversary'
    )
    
    # Event template
    event_type = fields.Selection([
        ('hire', 'Hired'),
        ('promotion', 'Promotion'),
        ('transfer', 'Transfer'),
        ('milestone', 'Work Anniversary'),
        ('contract', 'Contract Change'),
        ('other', 'Other'),
    ], string='Event Type', required=True)
    
    event_title_template = fields.Char(
        string='Title Template',
        help='Use {employee_name}, {years}, {department} as placeholders'
    )
    event_description_template = fields.Html(
        string='Description Template'
    )
    
    is_public = fields.Boolean(string='Public', default=True)
    is_featured = fields.Boolean(string='Featured', default=False)


class HrEmployee(models.Model):
    """Extend HR Employee for timeline"""
    _inherit = 'hr.employee'
    
    timeline_event_ids = fields.One2many(
        'employee.timeline.event',
        'employee_id',
        string='Timeline Events'
    )
    timeline_event_count = fields.Integer(
        string='Timeline Events',
        compute='_compute_timeline_count'
    )
    
    # Key dates for timeline
    hire_date = fields.Date(
        string='Hire Date',
        help='Original hire date'
    )
    years_of_service = fields.Float(
        string='Years of Service',
        compute='_compute_years_of_service'
    )
    next_anniversary = fields.Date(
        string='Next Anniversary',
        compute='_compute_next_anniversary'
    )
    
    # Career progression
    promotion_count = fields.Integer(
        string='Promotions',
        compute='_compute_career_stats'
    )
    transfer_count = fields.Integer(
        string='Transfers',
        compute='_compute_career_stats'
    )
    achievement_count = fields.Integer(
        string='Achievements',
        compute='_compute_career_stats'
    )
    
    def _compute_timeline_count(self):
        for employee in self:
            employee.timeline_event_count = len(employee.timeline_event_ids)
    
    def _compute_years_of_service(self):
        today = fields.Date.today()
        for employee in self:
            if employee.hire_date:
                delta = today - employee.hire_date
                employee.years_of_service = delta.days / 365.25
            else:
                employee.years_of_service = 0
    
    def _compute_next_anniversary(self):
        today = fields.Date.today()
        for employee in self:
            if employee.hire_date:
                # Calculate next anniversary
                this_year_anniversary = employee.hire_date.replace(year=today.year)
                if this_year_anniversary < today:
                    employee.next_anniversary = this_year_anniversary.replace(
                        year=today.year + 1
                    )
                else:
                    employee.next_anniversary = this_year_anniversary
            else:
                employee.next_anniversary = False
    
    def _compute_career_stats(self):
        for employee in self:
            events = employee.timeline_event_ids
            employee.promotion_count = len(events.filtered(
                lambda e: e.event_type == 'promotion'
            ))
            employee.transfer_count = len(events.filtered(
                lambda e: e.event_type == 'transfer'
            ))
            employee.achievement_count = len(events.filtered(
                lambda e: e.event_type in ('achievement', 'award', 'certification')
            ))
    
    def action_view_timeline(self):
        """View employee timeline"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timeline - %s') % self.name,
            'res_model': 'employee.timeline.event',
            'view_mode': 'tree,form,kanban',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
                'search_default_group_by_category': 1,
            },
        }
    
    def action_add_timeline_event(self):
        """Add a new timeline event"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Timeline Event'),
            'res_model': 'employee.timeline.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
            },
        }
    
    def _create_hire_event(self):
        """Create hire event when employee is created"""
        for employee in self:
            if employee.hire_date:
                self.env['employee.timeline.event'].create({
                    'employee_id': employee.id,
                    'name': _('Joined %s') % (employee.company_id.name or 'Company'),
                    'event_type': 'hire',
                    'event_date': employee.hire_date,
                    'department_id': employee.department_id.id,
                    'job_id': employee.job_id.id,
                    'description': _(
                        '<p>%s joined as <strong>%s</strong> in the <strong>%s</strong> department.</p>'
                    ) % (
                        employee.name,
                        employee.job_id.name if employee.job_id else 'Employee',
                        employee.department_id.name if employee.department_id else 'Company',
                    ),
                    'is_featured': True,
                })
    
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.hire_date:
                record._create_hire_event()
        return records
    
    def write(self, vals):
        # Track changes for timeline
        for employee in self:
            # Promotion detection
            if 'job_id' in vals and vals['job_id'] != employee.job_id.id:
                old_job = employee.job_id
                new_job = self.env['hr.job'].browse(vals['job_id'])
                self.env['employee.timeline.event'].create({
                    'employee_id': employee.id,
                    'name': _('Promoted to %s') % new_job.name,
                    'event_type': 'promotion',
                    'event_date': fields.Date.today(),
                    'from_job_id': old_job.id,
                    'to_job_id': new_job.id,
                    'description': _(
                        '<p>Promoted from <strong>%s</strong> to <strong>%s</strong>.</p>'
                    ) % (old_job.name or 'Previous Position', new_job.name),
                })
            
            # Transfer detection
            if 'department_id' in vals and vals['department_id'] != employee.department_id.id:
                old_dept = employee.department_id
                new_dept = self.env['hr.department'].browse(vals['department_id'])
                self.env['employee.timeline.event'].create({
                    'employee_id': employee.id,
                    'name': _('Transferred to %s') % new_dept.name,
                    'event_type': 'transfer',
                    'event_date': fields.Date.today(),
                    'from_department_id': old_dept.id,
                    'to_department_id': new_dept.id,
                    'description': _(
                        '<p>Transferred from <strong>%s</strong> to <strong>%s</strong>.</p>'
                    ) % (old_dept.name or 'Previous Department', new_dept.name),
                })
        
        return super().write(vals)
    
    @api.model
    def _cron_check_anniversaries(self):
        """Cron job to create anniversary events"""
        today = fields.Date.today()
        
        employees = self.search([
            ('hire_date', '!=', False),
        ])
        
        for employee in employees:
            # Check if today is anniversary
            if (employee.hire_date.month == today.month and 
                employee.hire_date.day == today.day):
                
                years = today.year - employee.hire_date.year
                if years > 0:
                    # Check if event already exists
                    existing = self.env['employee.timeline.event'].search([
                        ('employee_id', '=', employee.id),
                        ('event_type', '=', 'milestone'),
                        ('event_date', '=', today),
                    ])
                    
                    if not existing:
                        self.env['employee.timeline.event'].create({
                            'employee_id': employee.id,
                            'name': _('%d Year Work Anniversary') % years,
                            'event_type': 'milestone',
                            'event_date': today,
                            'description': _(
                                '<p>Celebrating <strong>%d years</strong> of service!</p>'
                            ) % years,
                            'is_featured': True,
                        })


class EmployeeTimelineReport(models.AbstractModel):
    """Timeline report for employees"""
    _name = 'report.tazweed_core.employee_timeline_report'
    _description = 'Employee Timeline Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        employees = self.env['hr.employee'].browse(docids)
        
        return {
            'doc_ids': docids,
            'doc_model': 'hr.employee',
            'docs': employees,
            'data': data,
        }
