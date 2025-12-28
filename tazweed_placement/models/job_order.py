# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class JobOrder(models.Model):
    """Job Order / Requisition from Client"""
    _name = 'tazweed.job.order'
    _description = 'Job Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Job Order No.',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    client_id = fields.Many2one(
        'tazweed.client',
        string='Client',
        required=True,
        tracking=True,
    )
    
    # Position Details
    job_title = fields.Char(string='Job Title', required=True, tracking=True)
    job_id = fields.Many2one('hr.job', string='Position Template')
    department = fields.Char(string='Department')
    
    job_category = fields.Selection([
        ('unskilled', 'Unskilled'),
        ('semi_skilled', 'Semi-Skilled'),
        ('skilled', 'Skilled'),
        ('professional', 'Professional'),
        ('managerial', 'Managerial'),
    ], string='Job Category', required=True)
    
    employment_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary'),
        ('contract', 'Contract'),
    ], string='Employment Type', default='permanent')
    
    # Requirements
    positions_required = fields.Integer(string='Positions Required', default=1)
    positions_filled = fields.Integer(string='Positions Filled', compute='_compute_positions')
    
    education_level = fields.Selection([
        ('none', 'No Requirement'),
        ('high_school', 'High School'),
        ('diploma', 'Diploma'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
    ], string='Education Level', default='none')
    
    experience_years = fields.Integer(string='Experience (Years)')
    
    # Compensation
    salary_min = fields.Float(string='Salary Min')
    salary_max = fields.Float(string='Salary Max')
    
    # Timeline
    date_required = fields.Date(string='Required By', tracking=True)
    date_received = fields.Date(string='Date Received', default=fields.Date.today)
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    recruiter_id = fields.Many2one('res.users', string='Assigned Recruiter')
    
    job_description = fields.Html(string='Job Description')
    
    # Placements
    placement_ids = fields.One2many('tazweed.placement', 'job_order_id', string='Placements')
    placement_count = fields.Integer(compute='_compute_positions')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.job.order') or _('New')
        return super().create(vals)

    @api.depends('placement_ids', 'placement_ids.state', 'positions_required')
    def _compute_positions(self):
        for order in self:
            filled = len(order.placement_ids.filtered(lambda p: p.state in ('active', 'completed')))
            order.positions_filled = filled
            order.placement_count = len(order.placement_ids)

    def action_open(self):
        self.write({'state': 'open'})

    def action_fill(self):
        self.write({'state': 'filled'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
