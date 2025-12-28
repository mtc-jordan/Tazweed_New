# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class HrPayslipAccounting(models.Model):
    """Extend Payslip with Accounting Integration (Optional)"""
    _inherit = 'hr.payslip'

    # Accounting Fields - only if account module is installed
    # These fields are defined conditionally to avoid errors
    
    def _check_account_module(self):
        """Check if account module is installed"""
        return 'account.move' in self.env

    def action_create_accounting_entry(self):
        """Create accounting entry for payslip (if account module installed)"""
        if not self._check_account_module():
            raise UserError(_('Accounting module is not installed.'))
        
        for payslip in self:
            payslip._create_accounting_entry()
        
        return True

    def _create_accounting_entry(self):
        """Create journal entry for payslip"""
        self.ensure_one()
        
        if not self._check_account_module():
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
        
        # Get default journal
        journal_id = config.get_param('tazweed_payroll.default_journal')
        if not journal_id:
            journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if not journal:
                return
            journal_id = journal.id
        
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
            'journal_id': int(journal_id),
            'date': self.date_to,
            'ref': self.number,
            'line_ids': move_lines,
        }
        
        move = self.env['account.move'].create(move_vals)
        
        return move


class HrPayslipRunAccounting(models.Model):
    """Extend Payslip Batch with Accounting Integration (Optional)"""
    _inherit = 'hr.payslip.run'

    create_single_entry = fields.Boolean(
        string='Create Single Entry',
        default=True,
        help='Create a single journal entry for the entire batch instead of individual entries per payslip',
    )

    def _check_account_module(self):
        """Check if account module is installed"""
        return 'account.move' in self.env

    def action_create_batch_accounting_entry(self):
        """Create batch accounting entry (if account module installed)"""
        if not self._check_account_module():
            raise UserError(_('Accounting module is not installed.'))
        
        for batch in self:
            batch._create_batch_accounting_entry()
        
        return True

    def _create_batch_accounting_entry(self):
        """Create single journal entry for entire batch"""
        self.ensure_one()
        
        if not self._check_account_module():
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
        
        # Get default journal
        journal_id = config.get_param('tazweed_payroll.default_journal')
        if not journal_id:
            journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if not journal:
                return
            journal_id = journal.id
        
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
            'journal_id': int(journal_id),
            'date': self.date_end,
            'ref': self.name,
            'line_ids': move_lines,
        }
        
        move = self.env['account.move'].create(move_vals)
        
        return move
