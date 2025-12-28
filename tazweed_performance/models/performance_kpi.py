# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PerformanceKPI(models.Model):
    """Key Performance Indicator Definition"""
    _name = 'tazweed.performance.kpi'
    _description = 'Key Performance Indicator'
    _inherit = ['mail.thread']
    _order = 'category, name'

    name = fields.Char(string='KPI Name', required=True, tracking=True)
    code = fields.Char(string='Code', required=True)
    description = fields.Text(string='Description')
    
    category = fields.Selection([
        ('financial', 'Financial'),
        ('operational', 'Operational'),
        ('customer', 'Customer'),
        ('employee', 'Employee'),
        ('quality', 'Quality'),
        ('productivity', 'Productivity'),
        ('compliance', 'Compliance'),
    ], string='Category', required=True, default='operational')
    
    kpi_type = fields.Selection([
        ('individual', 'Individual'),
        ('team', 'Team'),
        ('department', 'Department'),
        ('company', 'Company'),
    ], string='KPI Type', default='individual')
    
    measurement_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('ratio', 'Ratio'),
        ('rating', 'Rating'),
        ('time', 'Time'),
    ], string='Measurement Type', default='number', required=True)
    
    unit = fields.Char(string='Unit')
    
    # Target Settings
    target_type = fields.Selection([
        ('higher_better', 'Higher is Better'),
        ('lower_better', 'Lower is Better'),
        ('target_range', 'Target Range'),
        ('exact', 'Exact Value'),
    ], string='Target Type', default='higher_better')
    
    default_target = fields.Float(string='Default Target')
    min_threshold = fields.Float(string='Minimum Threshold')
    max_threshold = fields.Float(string='Maximum Threshold')
    
    # Scoring
    weight = fields.Float(string='Default Weight (%)', default=100)
    
    # Calculation
    calculation_method = fields.Selection([
        ('manual', 'Manual Entry'),
        ('formula', 'Formula'),
        ('automatic', 'Automatic'),
    ], string='Calculation Method', default='manual')
    
    formula = fields.Text(string='Formula')
    data_source = fields.Char(string='Data Source')
    
    # Frequency
    measurement_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Measurement Frequency', default='monthly')
    
    # Applicability
    department_ids = fields.Many2many(
        'hr.department',
        string='Applicable Departments',
    )
    job_ids = fields.Many2many(
        'hr.job',
        string='Applicable Job Positions',
    )
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'KPI code must be unique per company!'),
    ]


class PerformanceKPILine(models.Model):
    """KPI Line for Performance Review"""
    _name = 'tazweed.performance.kpi.line'
    _description = 'Performance KPI Line'

    review_id = fields.Many2one(
        'tazweed.performance.review',
        string='Review',
        required=True,
        ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='review_id.employee_id',
        store=True,
    )
    kpi_id = fields.Many2one(
        'tazweed.performance.kpi',
        string='KPI',
        required=True,
    )
    
    # Target
    target_value = fields.Float(string='Target')
    actual_value = fields.Float(string='Actual')
    unit = fields.Char(string='Unit', related='kpi_id.unit')
    
    # Achievement
    achievement_pct = fields.Float(
        string='Achievement %',
        compute='_compute_achievement',
        store=True,
    )
    score = fields.Float(
        string='Score',
        compute='_compute_score',
        store=True,
    )
    
    weight = fields.Float(string='Weight (%)', default=100)
    
    # Comments
    comments = fields.Text(string='Comments')
    
    period_id = fields.Many2one(
        'tazweed.performance.period',
        string='Period',
        related='review_id.period_id',
        store=True,
    )

    @api.depends('target_value', 'actual_value', 'kpi_id.target_type')
    def _compute_achievement(self):
        for line in self:
            if not line.target_value:
                line.achievement_pct = 0
                continue
            
            if line.kpi_id.target_type == 'higher_better':
                line.achievement_pct = (line.actual_value / line.target_value) * 100
            elif line.kpi_id.target_type == 'lower_better':
                if line.actual_value:
                    line.achievement_pct = (line.target_value / line.actual_value) * 100
                else:
                    line.achievement_pct = 100
            else:
                line.achievement_pct = (line.actual_value / line.target_value) * 100

    @api.depends('achievement_pct')
    def _compute_score(self):
        for line in self:
            # Convert achievement percentage to 5-point scale
            pct = min(line.achievement_pct, 150)  # Cap at 150%
            line.score = (pct / 100) * 5


class PerformanceKPITracking(models.Model):
    """KPI Tracking History"""
    _name = 'tazweed.kpi.tracking'
    _description = 'KPI Tracking'
    _order = 'date desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )
    kpi_id = fields.Many2one(
        'tazweed.performance.kpi',
        string='KPI',
        required=True,
    )
    
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    period = fields.Char(string='Period')
    
    target_value = fields.Float(string='Target')
    actual_value = fields.Float(string='Actual')
    achievement_pct = fields.Float(string='Achievement %')
    
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
