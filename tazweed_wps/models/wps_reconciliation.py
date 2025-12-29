# -*- coding: utf-8 -*-
"""
WPS Payment Reconciliation Module
Auto-reconcile WPS payments with bank statements
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class WPSReconciliation(models.Model):
    """WPS Payment Reconciliation"""
    _name = 'wps.reconciliation'
    _description = 'WPS Payment Reconciliation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'reconciliation_date desc'

    name = fields.Char(string='Reference', required=True, default='New', copy=False)
    
    # Period
    reconciliation_date = fields.Date(string='Reconciliation Date', default=fields.Date.today, required=True)
    period_from = fields.Date(string='Period From', required=True)
    period_to = fields.Date(string='Period To', required=True)
    
    # Source Documents
    wps_file_ids = fields.Many2many('tazweed.wps.file', 'wps_reconciliation_file_rel', 
                                     'reconciliation_id', 'file_id', string='WPS Files')
    bank_statement_ids = fields.Many2many('account.bank.statement', 'wps_reconciliation_statement_rel',
                                           'reconciliation_id', 'statement_id', string='Bank Statements')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                  default=lambda self: self.env.company)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('reconciled', 'Reconciled'),
        ('partial', 'Partially Reconciled'),
        ('discrepancy', 'Discrepancy Found'),
    ], string='Status', default='draft', tracking=True)
    
    # Summary
    total_wps_amount = fields.Float(string='Total WPS Amount', compute='_compute_summary', store=True)
    total_bank_amount = fields.Float(string='Total Bank Amount', compute='_compute_summary', store=True)
    difference = fields.Float(string='Difference', compute='_compute_summary', store=True)
    
    total_employees = fields.Integer(string='Total Employees', compute='_compute_summary', store=True)
    matched_employees = fields.Integer(string='Matched', compute='_compute_summary', store=True)
    unmatched_employees = fields.Integer(string='Unmatched', compute='_compute_summary', store=True)
    
    match_percentage = fields.Float(string='Match %', compute='_compute_summary', store=True)
    
    # Lines
    line_ids = fields.One2many('wps.reconciliation.line', 'reconciliation_id', string='Reconciliation Lines')
    
    # Notes
    notes = fields.Text(string='Notes')
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('wps.reconciliation') or 'New'
        return super().create(vals)
    
    @api.depends('line_ids', 'line_ids.wps_amount', 'line_ids.bank_amount', 'line_ids.state')
    def _compute_summary(self):
        for record in self:
            lines = record.line_ids
            record.total_wps_amount = sum(lines.mapped('wps_amount'))
            record.total_bank_amount = sum(lines.mapped('bank_amount'))
            record.difference = record.total_wps_amount - record.total_bank_amount
            
            record.total_employees = len(lines)
            record.matched_employees = len(lines.filtered(lambda l: l.state == 'matched'))
            record.unmatched_employees = len(lines.filtered(lambda l: l.state != 'matched'))
            
            if record.total_employees:
                record.match_percentage = (record.matched_employees / record.total_employees) * 100
            else:
                record.match_percentage = 0
    
    def action_start_reconciliation(self):
        """Start the reconciliation process"""
        self.ensure_one()
        self.state = 'in_progress'
        
        # Clear existing lines
        self.line_ids.unlink()
        
        # Get WPS file lines
        wps_lines = self.env['tazweed.wps.file.line'].search([
            ('wps_file_id', 'in', self.wps_file_ids.ids),
        ])
        
        # Create reconciliation lines from WPS data
        for wps_line in wps_lines:
            self.env['wps.reconciliation.line'].create({
                'reconciliation_id': self.id,
                'employee_id': wps_line.employee_id.id,
                'wps_file_line_id': wps_line.id,
                'wps_amount': wps_line.net_salary,
                'bank_account': wps_line.iban or wps_line.account_number,
            })
        
        # Auto-match with bank statements
        self._auto_match_payments()
        
        # Update state based on results
        self._update_reconciliation_state()
        
        return True
    
    def _auto_match_payments(self):
        """Auto-match WPS payments with bank statement lines"""
        # Get bank statement lines for the period
        bank_lines = []
        if 'account.bank.statement.line' in self.env:
            bank_lines = self.env['account.bank.statement.line'].search([
                ('statement_id', 'in', self.bank_statement_ids.ids),
            ])
        
        for rec_line in self.line_ids:
            # Try to find matching bank transaction
            matched = False
            
            for bank_line in bank_lines:
                # Match by amount and reference
                if abs(bank_line.amount) == abs(rec_line.wps_amount):
                    # Check if reference contains employee info
                    ref = (bank_line.ref or '').lower()
                    emp_name = (rec_line.employee_id.name or '').lower()
                    
                    if emp_name in ref or str(rec_line.bank_account) in ref:
                        rec_line.write({
                            'bank_statement_line_id': bank_line.id,
                            'bank_amount': abs(bank_line.amount),
                            'bank_reference': bank_line.ref,
                            'bank_date': bank_line.date,
                            'state': 'matched',
                        })
                        matched = True
                        break
            
            if not matched:
                # Try fuzzy matching by amount only (within tolerance)
                tolerance = 0.01  # 1% tolerance
                for bank_line in bank_lines:
                    if abs(abs(bank_line.amount) - rec_line.wps_amount) <= rec_line.wps_amount * tolerance:
                        rec_line.write({
                            'bank_statement_line_id': bank_line.id,
                            'bank_amount': abs(bank_line.amount),
                            'bank_reference': bank_line.ref,
                            'bank_date': bank_line.date,
                            'state': 'partial',
                            'difference_reason': 'Amount mismatch within tolerance',
                        })
                        break
    
    def _update_reconciliation_state(self):
        """Update reconciliation state based on line states"""
        if not self.line_ids:
            self.state = 'draft'
        elif all(line.state == 'matched' for line in self.line_ids):
            self.state = 'reconciled'
        elif any(line.state == 'matched' for line in self.line_ids):
            self.state = 'partial'
        else:
            self.state = 'discrepancy'
    
    def action_complete_reconciliation(self):
        """Complete the reconciliation"""
        self.ensure_one()
        
        # Check if all critical items are reconciled
        unmatched = self.line_ids.filtered(lambda l: l.state == 'unmatched')
        if unmatched:
            raise UserError(_('%d employees have unmatched payments. Please resolve before completing.') % len(unmatched))
        
        self.state = 'reconciled'
    
    def action_export_report(self):
        """Export reconciliation report"""
        self.ensure_one()
        return {
            'type': 'ir.actions.report',
            'report_name': 'tazweed_wps.report_wps_reconciliation',
            'report_type': 'qweb-pdf',
            'data': {'reconciliation_id': self.id},
        }


class WPSReconciliationLine(models.Model):
    """WPS Reconciliation Line"""
    _name = 'wps.reconciliation.line'
    _description = 'WPS Reconciliation Line'
    _order = 'employee_id'

    reconciliation_id = fields.Many2one('wps.reconciliation', string='Reconciliation', 
                                         required=True, ondelete='cascade')
    
    # Employee Info
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    employee_number = fields.Char(related='employee_id.identification_id', string='Employee Number')
    
    # WPS Data
    wps_file_line_id = fields.Many2one('tazweed.wps.file.line', string='WPS Line')
    wps_amount = fields.Float(string='WPS Amount')
    bank_account = fields.Char(string='Bank Account/IBAN')
    
    # Bank Data
    bank_statement_line_id = fields.Many2one('account.bank.statement.line', string='Bank Statement Line')
    bank_amount = fields.Float(string='Bank Amount')
    bank_reference = fields.Char(string='Bank Reference')
    bank_date = fields.Date(string='Bank Date')
    
    # Matching
    state = fields.Selection([
        ('unmatched', 'Unmatched'),
        ('matched', 'Matched'),
        ('partial', 'Partial Match'),
        ('discrepancy', 'Discrepancy'),
        ('manual', 'Manually Matched'),
    ], string='Status', default='unmatched')
    
    difference = fields.Float(string='Difference', compute='_compute_difference', store=True)
    difference_reason = fields.Char(string='Difference Reason')
    
    # Manual Override
    manually_matched = fields.Boolean(string='Manually Matched')
    matched_by = fields.Many2one('res.users', string='Matched By')
    match_notes = fields.Text(string='Match Notes')
    
    @api.depends('wps_amount', 'bank_amount')
    def _compute_difference(self):
        for record in self:
            record.difference = record.wps_amount - record.bank_amount
    
    def action_manual_match(self):
        """Manually match the payment"""
        self.ensure_one()
        self.write({
            'state': 'manual',
            'manually_matched': True,
            'matched_by': self.env.user.id,
        })
    
    def action_mark_discrepancy(self):
        """Mark as discrepancy"""
        self.ensure_one()
        self.state = 'discrepancy'


class WPSReconciliationWizard(models.TransientModel):
    """Wizard for creating reconciliation"""
    _name = 'wps.reconciliation.wizard'
    _description = 'WPS Reconciliation Wizard'

    period_from = fields.Date(string='Period From', required=True, 
                               default=lambda self: fields.Date.today().replace(day=1))
    period_to = fields.Date(string='Period To', required=True,
                             default=fields.Date.today)
    
    wps_file_ids = fields.Many2many('tazweed.wps.file', string='WPS Files', required=True)
    bank_statement_ids = fields.Many2many('account.bank.statement', string='Bank Statements')
    
    auto_match = fields.Boolean(string='Auto-Match Payments', default=True)
    
    def action_create_reconciliation(self):
        """Create reconciliation record"""
        self.ensure_one()
        
        reconciliation = self.env['wps.reconciliation'].create({
            'period_from': self.period_from,
            'period_to': self.period_to,
            'wps_file_ids': [(6, 0, self.wps_file_ids.ids)],
            'bank_statement_ids': [(6, 0, self.bank_statement_ids.ids)] if self.bank_statement_ids else False,
        })
        
        if self.auto_match:
            reconciliation.action_start_reconciliation()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('WPS Reconciliation'),
            'res_model': 'wps.reconciliation',
            'res_id': reconciliation.id,
            'view_mode': 'form',
            'target': 'current',
        }
