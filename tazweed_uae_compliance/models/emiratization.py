# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class EmiratizationQuota(models.Model):
    """Emiratization Quota Management"""
    _name = 'tazweed.emiratization.quota'
    _description = 'Emiratization Quota'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    year = fields.Char(string='Year', required=True, default=lambda self: str(date.today().year))
    
    # Company Info
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    industry_category = fields.Selection([
        ('private', 'Private Sector'),
        ('semi_govt', 'Semi-Government'),
        ('free_zone', 'Free Zone'),
    ], string='Industry Category', default='private')
    
    # Quota Requirements
    required_percentage = fields.Float(string='Required %', default=2.0, tracking=True)
    target_count = fields.Integer(string='Target UAE Nationals', compute='_compute_metrics', store=True)
    
    # Current Status
    total_employees = fields.Integer(string='Total Employees', compute='_compute_metrics', store=True)
    uae_nationals = fields.Integer(string='UAE Nationals', compute='_compute_metrics', store=True)
    current_percentage = fields.Float(string='Current %', compute='_compute_metrics', store=True)
    
    # Gap Analysis
    gap_count = fields.Integer(string='Gap (Nationals Needed)', compute='_compute_metrics', store=True)
    is_compliant = fields.Boolean(string='Compliant', compute='_compute_metrics', store=True)
    
    # Penalties
    penalty_per_employee = fields.Float(string='Penalty per Employee (AED)', default=6000)
    estimated_penalty = fields.Float(string='Estimated Penalty', compute='_compute_metrics', store=True)
    
    # Tracking
    national_ids = fields.Many2many('hr.employee', string='UAE Nationals', compute='_compute_nationals')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')

    @api.depends('year', 'company_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f'Emiratization {rec.year} - {rec.company_id.name}'

    @api.depends('company_id', 'required_percentage')
    def _compute_metrics(self):
        for rec in self:
            # Get all employees
            employees = self.env['hr.employee'].search([
                ('company_id', '=', rec.company_id.id),
            ])
            
            # Count UAE nationals (assuming country_id is UAE)
            uae = self.env['res.country'].search([('code', '=', 'AE')], limit=1)
            nationals = employees.filtered(lambda e: e.country_id == uae)
            
            rec.total_employees = len(employees)
            rec.uae_nationals = len(nationals)
            
            if rec.total_employees:
                rec.current_percentage = (rec.uae_nationals / rec.total_employees) * 100
            else:
                rec.current_percentage = 0
            
            rec.target_count = int(rec.total_employees * rec.required_percentage / 100)
            rec.gap_count = max(0, rec.target_count - rec.uae_nationals)
            rec.is_compliant = rec.current_percentage >= rec.required_percentage
            rec.estimated_penalty = rec.gap_count * rec.penalty_per_employee

    def _compute_nationals(self):
        for rec in self:
            uae = self.env['res.country'].search([('code', '=', 'AE')], limit=1)
            rec.national_ids = self.env['hr.employee'].search([
                ('company_id', '=', rec.company_id.id),
                ('country_id', '=', uae.id),
            ])

    def action_activate(self):
        self.write({'state': 'active'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_refresh(self):
        """Refresh metrics"""
        self._compute_metrics()
        return True


class EmiratizationPlan(models.Model):
    """Emiratization Hiring Plan"""
    _name = 'tazweed.emiratization.plan'
    _description = 'Emiratization Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Plan Name', required=True)
    quota_id = fields.Many2one('tazweed.emiratization.quota', string='Quota Reference')
    
    # Timeline
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date', required=True)
    
    # Targets
    target_hires = fields.Integer(string='Target Hires', required=True)
    actual_hires = fields.Integer(string='Actual Hires', compute='_compute_hires')
    
    # Budget
    budget = fields.Float(string='Budget (AED)')
    spent = fields.Float(string='Spent (AED)')
    
    # Lines
    line_ids = fields.One2many('tazweed.emiratization.plan.line', 'plan_id', string='Plan Lines')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _compute_hires(self):
        for rec in self:
            rec.actual_hires = len(rec.line_ids.filtered(lambda l: l.state == 'hired'))

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})


class EmiratizationPlanLine(models.Model):
    """Emiratization Plan Line"""
    _name = 'tazweed.emiratization.plan.line'
    _description = 'Emiratization Plan Line'

    plan_id = fields.Many2one('tazweed.emiratization.plan', required=True, ondelete='cascade')
    
    job_id = fields.Many2one('hr.job', string='Position')
    department_id = fields.Many2one('hr.department', string='Department')
    
    target_count = fields.Integer(string='Target', default=1)
    hired_count = fields.Integer(string='Hired', default=0)
    
    target_date = fields.Date(string='Target Date')
    
    employee_id = fields.Many2one('hr.employee', string='Hired Employee')
    
    state = fields.Selection([
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('hired', 'Hired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='open')
    
    notes = fields.Text(string='Notes')
