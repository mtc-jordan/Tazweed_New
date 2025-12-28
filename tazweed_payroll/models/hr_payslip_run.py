# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class HrPayslipRun(models.Model):
    """Payslip Batch - Enterprise Feature"""
    _name = 'hr.payslip.run'
    _description = 'Payslip Batch'
    _order = 'date_start desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True,
    )
    
    # Reference
    reference = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
    )
    
    # Period
    date_start = fields.Date(
        string='Date From',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: date.today().replace(day=1),
    )
    date_end = fields.Date(
        string='Date To',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        default=lambda self: (date.today().replace(day=1) + relativedelta(months=1, days=-1)),
    )
    
    # Structure
    struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Salary Structure',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    
    # Department
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    
    # Payslips
    slip_ids = fields.One2many(
        'hr.payslip',
        'payslip_run_id',
        string='Payslips',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    
    # Counts
    payslip_count = fields.Integer(
        string='Payslip Count',
        compute='_compute_payslip_count',
        store=True,
    )
    
    # Amounts
    total_basic = fields.Float(
        string='Total Basic',
        compute='_compute_amounts',
        store=True,
    )
    total_gross = fields.Float(
        string='Total Gross',
        compute='_compute_amounts',
        store=True,
    )
    total_net = fields.Float(
        string='Total Net',
        compute='_compute_amounts',
        store=True,
    )
    total_deductions = fields.Float(
        string='Total Deductions',
        compute='_compute_amounts',
        store=True,
    )
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Waiting'),
        ('confirm', 'Confirmed'),
        ('done', 'Done'),
        ('paid', 'Paid'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # WPS
    wps_file_id = fields.Many2one(
        'tazweed.wps.file',
        string='WPS File',
        readonly=True,
    )
    wps_generated = fields.Boolean(
        string='WPS Generated',
        default=False,
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    
    # Notes
    note = fields.Html(string='Notes')

    @api.depends('slip_ids')
    def _compute_payslip_count(self):
        """Compute payslip count"""
        for batch in self:
            batch.payslip_count = len(batch.slip_ids)

    @api.depends('slip_ids.basic_wage', 'slip_ids.gross_wage', 'slip_ids.net_wage', 'slip_ids.total_deductions')
    def _compute_amounts(self):
        """Compute total amounts"""
        for batch in self:
            batch.total_basic = sum(batch.slip_ids.mapped('basic_wage'))
            batch.total_gross = sum(batch.slip_ids.mapped('gross_wage'))
            batch.total_net = sum(batch.slip_ids.mapped('net_wage'))
            batch.total_deductions = sum(batch.slip_ids.mapped('total_deductions'))

    @api.model
    def create(self, vals):
        """Generate reference on create"""
        if not vals.get('reference'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('hr.payslip.run') or '/'
        return super().create(vals)

    def action_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def action_verify(self):
        """Move to verify state"""
        self.write({'state': 'verify'})

    def action_confirm(self):
        """Confirm batch"""
        for batch in self:
            if not batch.slip_ids:
                raise UserError(_('Please generate payslips before confirming.'))
            
            # Compute all payslips
            batch.slip_ids.compute_sheet()
        
        self.write({'state': 'confirm'})

    def action_done(self):
        """Mark as done"""
        for batch in self:
            # Confirm all payslips
            for slip in batch.slip_ids.filtered(lambda s: s.state == 'draft'):
                slip.action_payslip_done()
        
        self.write({'state': 'done'})

    def action_paid(self):
        """Mark as paid"""
        for batch in self:
            # Mark all payslips as paid
            batch.slip_ids.action_payslip_paid()
        
        self.write({'state': 'paid'})

    def action_cancel(self):
        """Cancel batch"""
        for batch in self:
            # Cancel all payslips
            for slip in batch.slip_ids:
                slip.action_payslip_cancel()
        
        self.write({'state': 'cancel'})

    def action_generate_payslips(self):
        """Open wizard to generate payslips"""
        return {
            'name': _('Generate Payslips'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.payslip.generation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payslip_run_id': self.id,
                'default_date_start': self.date_start,
                'default_date_end': self.date_end,
                'default_struct_id': self.struct_id.id,
                'default_department_id': self.department_id.id,
            },
        }

    def action_compute_payslips(self):
        """Compute all payslips in batch"""
        for batch in self:
            batch.slip_ids.compute_sheet()
        return True

    def action_generate_wps(self):
        """Open wizard to generate WPS file"""
        return {
            'name': _('Generate WPS File'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.wps.generation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payslip_run_id': self.id,
            },
        }

    def action_view_payslips(self):
        """View payslips in batch"""
        return {
            'name': _('Payslips'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'tree,form',
            'domain': [('payslip_run_id', '=', self.id)],
            'context': {'default_payslip_run_id': self.id},
        }
