# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, timedelta


class IntegrationDashboard(models.Model):
    """Integration Dashboard"""
    _name = 'tazweed.integration.dashboard'
    _description = 'Integration Dashboard'
    _order = 'create_date desc'

    name = fields.Char(string='Dashboard Name', required=True)
    dashboard_type = fields.Selection([
        ('executive', 'Executive Dashboard'),
        ('hr', 'HR Dashboard'),
        ('payroll', 'Payroll Dashboard'),
        ('compliance', 'Compliance Dashboard'),
        ('placement', 'Placement Dashboard'),
    ], string='Dashboard Type', default='executive')
    
    # Period
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    
    # HR Metrics
    total_employees = fields.Integer(string='Total Employees', compute='_compute_hr_metrics')
    new_hires = fields.Integer(string='New Hires', compute='_compute_hr_metrics')
    terminations = fields.Integer(string='Terminations', compute='_compute_hr_metrics')
    
    # Leave Metrics
    pending_leaves = fields.Integer(string='Pending Leaves', compute='_compute_leave_metrics')
    approved_leaves = fields.Integer(string='Approved Leaves', compute='_compute_leave_metrics')
    
    # Payroll Metrics
    total_payroll = fields.Float(string='Total Payroll', compute='_compute_payroll_metrics')
    pending_payslips = fields.Integer(string='Pending Payslips', compute='_compute_payroll_metrics')
    
    # Compliance Metrics
    wps_compliance = fields.Float(string='WPS Compliance %', compute='_compute_compliance_metrics')
    emiratization_rate = fields.Float(string='Emiratization %', compute='_compute_compliance_metrics')
    expiring_documents = fields.Integer(string='Expiring Documents', compute='_compute_compliance_metrics')
    
    # Placement Metrics
    active_placements = fields.Integer(string='Active Placements', compute='_compute_placement_metrics')
    open_job_orders = fields.Integer(string='Open Job Orders', compute='_compute_placement_metrics')
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def _compute_hr_metrics(self):
        for rec in self:
            employees = self.env['hr.employee'].search([
                ('company_id', '=', rec.company_id.id),
            ])
            rec.total_employees = len(employees)
            rec.new_hires = 0  # Would need hire date tracking
            rec.terminations = 0  # Would need termination tracking

    def _compute_leave_metrics(self):
        for rec in self:
            rec.pending_leaves = 0
            rec.approved_leaves = 0
            # Would integrate with leave module if installed

    def _compute_payroll_metrics(self):
        for rec in self:
            rec.total_payroll = 0
            rec.pending_payslips = 0
            # Would integrate with payroll module if installed

    def _compute_compliance_metrics(self):
        for rec in self:
            rec.wps_compliance = 0
            rec.emiratization_rate = 0
            rec.expiring_documents = 0
            # Would integrate with compliance module if installed

    def _compute_placement_metrics(self):
        for rec in self:
            rec.active_placements = 0
            rec.open_job_orders = 0
            # Would integrate with placement module if installed

    def action_refresh(self):
        """Refresh all metrics"""
        self._compute_hr_metrics()
        self._compute_leave_metrics()
        self._compute_payroll_metrics()
        self._compute_compliance_metrics()
        self._compute_placement_metrics()
        return True


class IntegrationLog(models.Model):
    """Integration Log"""
    _name = 'tazweed.integration.log'
    _description = 'Integration Log'
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    
    integration_type = fields.Selection([
        ('payroll_leave', 'Payroll-Leave'),
        ('payroll_attendance', 'Payroll-Attendance'),
        ('payroll_performance', 'Payroll-Performance'),
        ('compliance_wps', 'Compliance-WPS'),
        ('compliance_emiratization', 'Compliance-Emiratization'),
        ('placement_employee', 'Placement-Employee'),
        ('other', 'Other'),
    ], string='Integration Type', required=True)
    
    source_model = fields.Char(string='Source Model')
    source_record_id = fields.Integer(string='Source Record ID')
    target_model = fields.Char(string='Target Model')
    target_record_id = fields.Integer(string='Target Record ID')
    
    state = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')
    
    error_message = fields.Text(string='Error Message')
    
    create_date = fields.Datetime(string='Created', readonly=True)
    write_date = fields.Datetime(string='Updated', readonly=True)
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.integration.log') or _('New')
        return super().create(vals)


class IntegrationConfig(models.Model):
    """Integration Configuration"""
    _name = 'tazweed.integration.config'
    _description = 'Integration Configuration'

    name = fields.Char(string='Configuration Name', required=True)
    
    config_type = fields.Selection([
        ('payroll', 'Payroll Integration'),
        ('compliance', 'Compliance Integration'),
        ('placement', 'Placement Integration'),
        ('analytics', 'Analytics Integration'),
    ], string='Configuration Type', required=True)
    
    is_active = fields.Boolean(string='Active', default=True)
    
    # Payroll Integration Settings
    auto_leave_deduction = fields.Boolean(string='Auto Leave Deduction', default=True)
    auto_attendance_calc = fields.Boolean(string='Auto Attendance Calculation', default=True)
    auto_performance_bonus = fields.Boolean(string='Auto Performance Bonus', default=True)
    auto_loan_deduction = fields.Boolean(string='Auto Loan Deduction', default=True)
    
    # Compliance Integration Settings
    auto_wps_generation = fields.Boolean(string='Auto WPS Generation', default=False)
    auto_document_alerts = fields.Boolean(string='Auto Document Alerts', default=True)
    
    # Placement Integration Settings
    auto_employee_creation = fields.Boolean(string='Auto Employee Creation', default=True)
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
