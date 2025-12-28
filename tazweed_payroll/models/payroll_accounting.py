# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class HrPayslipAccounting(models.Model):
    """Extend Payslip with Accounting Integration"""
    _inherit = 'hr.payslip'

    # Accounting Fields
    move_id = fields.Many2one(
        'account.move',
        string='Accounting Entry',
        readonly=True,
        copy=False,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Salary Journal',
    )
    
    def action_payslip_done(self):
        """Override to create accounting entry when payslip is confirmed"""
        res = super().action_payslip_done()
        
        # Create accounting entries for confirmed payslips
        for payslip in self:
            if payslip.journal_id and not payslip.move_id:
                payslip._create_accounting_entry()
        
        return res

    def action_payslip_cancel(self):
        """Override to cancel accounting entry when payslip is cancelled"""
        for payslip in self:
            if payslip.move_id:
                if payslip.move_id.state == 'posted':
                    payslip.move_id.button_draft()
                payslip.move_id.button_cancel()
        
        return super().action_payslip_cancel()

    def _create_accounting_entry(self):
        """Create journal entry for payslip"""
        self.ensure_one()
        
        if not self.journal_id:
            return
        
        if 'account.move' not in self.env:
            return
        
        # Get accounts from configuration
        config = self.env['ir.config_parameter'].sudo()
        salary_expense_account = config.get_param('tazweed_payroll.salary_expense_account')
        salary_payable_account = config.get_param('tazweed_payroll.salary_payable_account')
        
        if not salary_expense_account or not salary_payable_account:
            # Try to get default accounts
            expense_account = self.env['account.account'].search([
                ('account_type', '=', 'expense'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            payable_account = self.env['account.account'].search([
                ('account_type', '=', 'liability_payable'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            
            if not expense_account or not payable_account:
                return
            
            salary_expense_account = expense_account.id
            salary_payable_account = payable_account.id
        
        # Build journal entry lines
        move_lines = []
        
        # Debit: Salary Expense (Gross)
        if self.gross_wage:
            move_lines.append((0, 0, {
                'name': f'Salary - {self.employee_id.name}',
                'account_id': int(salary_expense_account),
                'debit': self.gross_wage,
                'credit': 0.0,
                'partner_id': self.employee_id.address_home_id.id if self.employee_id.address_home_id else False,
            }))
        
        # Credit: Salary Payable (Net)
        if self.net_wage:
            move_lines.append((0, 0, {
                'name': f'Net Salary Payable - {self.employee_id.name}',
                'account_id': int(salary_payable_account),
                'debit': 0.0,
                'credit': self.net_wage,
                'partner_id': self.employee_id.address_home_id.id if self.employee_id.address_home_id else False,
            }))
        
        # Credit: Deductions (if any)
        if self.total_deductions:
            # Get deduction account
            deduction_account = config.get_param('tazweed_payroll.deduction_account')
            if not deduction_account:
                deduction_account = salary_payable_account
            
            move_lines.append((0, 0, {
                'name': f'Deductions - {self.employee_id.name}',
                'account_id': int(deduction_account),
                'debit': 0.0,
                'credit': self.total_deductions,
            }))
        
        if not move_lines:
            return
        
        # Create the journal entry
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date_to,
            'ref': self.number,
            'line_ids': move_lines,
        }
        
        move = self.env['account.move'].create(move_vals)
        self.move_id = move
        
        return move

    def action_view_accounting_entry(self):
        """View linked accounting entry"""
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('No accounting entry linked to this payslip.'))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }


class HrPayslipRunAccounting(models.Model):
    """Extend Payslip Batch with Accounting Integration"""
    _inherit = 'hr.payslip.run'

    # Accounting Fields
    journal_id = fields.Many2one(
        'account.journal',
        string='Salary Journal',
    )
    move_id = fields.Many2one(
        'account.move',
        string='Batch Accounting Entry',
        readonly=True,
        copy=False,
    )
    create_single_entry = fields.Boolean(
        string='Create Single Entry',
        default=True,
        help='Create a single journal entry for the entire batch instead of individual entries per payslip',
    )

    def action_validate(self):
        """Override to create batch accounting entry"""
        res = super().action_validate()
        
        for batch in self:
            if batch.journal_id and batch.create_single_entry and not batch.move_id:
                batch._create_batch_accounting_entry()
            elif batch.journal_id and not batch.create_single_entry:
                # Set journal on individual payslips
                for payslip in batch.slip_ids:
                    if not payslip.journal_id:
                        payslip.journal_id = batch.journal_id
        
        return res

    def _create_batch_accounting_entry(self):
        """Create single journal entry for entire batch"""
        self.ensure_one()
        
        if not self.journal_id:
            return
        
        if 'account.move' not in self.env:
            return
        
        # Get accounts from configuration
        config = self.env['ir.config_parameter'].sudo()
        salary_expense_account = config.get_param('tazweed_payroll.salary_expense_account')
        salary_payable_account = config.get_param('tazweed_payroll.salary_payable_account')
        
        if not salary_expense_account or not salary_payable_account:
            # Try to get default accounts
            expense_account = self.env['account.account'].search([
                ('account_type', '=', 'expense'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            payable_account = self.env['account.account'].search([
                ('account_type', '=', 'liability_payable'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            
            if not expense_account or not payable_account:
                return
            
            salary_expense_account = expense_account.id
            salary_payable_account = payable_account.id
        
        # Calculate totals
        total_gross = sum(slip.gross_wage for slip in self.slip_ids)
        total_net = sum(slip.net_wage for slip in self.slip_ids)
        total_deductions = sum(slip.total_deductions for slip in self.slip_ids)
        
        # Build journal entry lines
        move_lines = []
        
        # Debit: Salary Expense (Total Gross)
        if total_gross:
            move_lines.append((0, 0, {
                'name': f'Salary Expense - {self.name}',
                'account_id': int(salary_expense_account),
                'debit': total_gross,
                'credit': 0.0,
            }))
        
        # Credit: Salary Payable (Total Net)
        if total_net:
            move_lines.append((0, 0, {
                'name': f'Net Salary Payable - {self.name}',
                'account_id': int(salary_payable_account),
                'debit': 0.0,
                'credit': total_net,
            }))
        
        # Credit: Deductions
        if total_deductions:
            deduction_account = config.get_param('tazweed_payroll.deduction_account')
            if not deduction_account:
                deduction_account = salary_payable_account
            
            move_lines.append((0, 0, {
                'name': f'Deductions - {self.name}',
                'account_id': int(deduction_account),
                'debit': 0.0,
                'credit': total_deductions,
            }))
        
        if not move_lines:
            return
        
        # Create the journal entry
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.date_end,
            'ref': self.name,
            'line_ids': move_lines,
        }
        
        move = self.env['account.move'].create(move_vals)
        self.move_id = move
        
        return move

    def action_view_accounting_entry(self):
        """View linked accounting entry"""
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('No accounting entry linked to this batch.'))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }


class PayrollAccountingConfig(models.TransientModel):
    """Payroll Accounting Configuration"""
    _inherit = 'res.config.settings'

    payroll_salary_expense_account = fields.Many2one(
        'account.account',
        string='Salary Expense Account',
        domain="[('account_type', '=', 'expense')]",
        config_parameter='tazweed_payroll.salary_expense_account',
    )
    payroll_salary_payable_account = fields.Many2one(
        'account.account',
        string='Salary Payable Account',
        domain="[('account_type', '=', 'liability_payable')]",
        config_parameter='tazweed_payroll.salary_payable_account',
    )
    payroll_deduction_account = fields.Many2one(
        'account.account',
        string='Deduction Account',
        domain="[('account_type', 'in', ['liability_payable', 'liability_current'])]",
        config_parameter='tazweed_payroll.deduction_account',
    )
    payroll_default_journal = fields.Many2one(
        'account.journal',
        string='Default Salary Journal',
        config_parameter='tazweed_payroll.default_journal',
    )
