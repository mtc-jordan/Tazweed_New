# -*- coding: utf-8 -*-
"""
WPS File Extension for Payroll Module
=====================================
This module extends the tazweed.wps.file model from tazweed_wps
to add payroll-specific functionality like payslip batch integration.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime
import base64
import logging

_logger = logging.getLogger(__name__)


class WPSFilePayrollExtension(models.Model):
    """Extend WPS File with Payroll-specific functionality"""
    _inherit = 'tazweed.wps.file'

    # Payroll-specific fields
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        tracking=True,
        help='Link to payroll batch for automatic line generation',
    )
    
    # Compatibility fields for payroll
    file_data = fields.Binary(
        string='WPS File Data',
        related='sif_file',
        store=False,
        readonly=False,
    )
    file_name = fields.Char(
        string='File Name',
        related='sif_filename',
        store=False,
        readonly=False,
    )
    total_employees = fields.Integer(
        string='Total Employees',
        compute='_compute_payroll_totals',
        store=True,
    )
    total_salary = fields.Float(
        string='Total Salary',
        compute='_compute_payroll_totals',
        store=True,
    )
    employer_bank_account = fields.Char(
        string='Employer Bank Account',
        related='employer_account',
        store=False,
    )

    @api.depends('employee_count', 'total_net')
    def _compute_payroll_totals(self):
        """Compute payroll-specific totals"""
        for wps in self:
            wps.total_employees = wps.employee_count
            wps.total_salary = wps.total_net

    def action_generate_lines_from_payslips(self):
        """Generate WPS lines from payslip batch"""
        for wps in self:
            if not wps.payslip_run_id:
                raise UserError(_('Please select a payslip batch.'))
            
            # Clear existing lines
            wps.line_ids.unlink()
            
            # Generate lines from payslips
            for payslip in wps.payslip_run_id.slip_ids.filtered(lambda p: p.state in ['done', 'paid']):
                employee = payslip.employee_id
                bank = getattr(payslip, 'bank_account_id', None)
                
                if not bank:
                    _logger.warning('No bank account for employee %s', employee.name)
                    continue
                
                # Get bank info
                bank_code = ''
                if hasattr(bank, 'bank_id') and bank.bank_id:
                    bank_code = bank.bank_id.bic or ''
                
                self.env['tazweed.wps.file.line'].create({
                    'wps_file_id': wps.id,
                    'employee_id': employee.id,
                    'employee_eid': getattr(employee, 'emirates_id', '') or '',
                    'labour_card_no': getattr(employee, 'labour_card_no', '') or '',
                    'bank_id': wps.employer_bank_id.id if wps.employer_bank_id else False,
                    'bank_code': bank_code,
                    'account_number': bank.acc_number or getattr(bank, 'account_number', '') or '',
                    'iban': getattr(bank, 'iban', '') or '',
                    'basic_salary': getattr(payslip, 'basic_wage', 0.0),
                    'housing_allowance': getattr(payslip, 'housing_allowance', 0.0),
                    'transport_allowance': getattr(payslip, 'transport_allowance', 0.0),
                    'other_allowance': getattr(payslip, 'other_allowances', 0.0),
                    'overtime': getattr(payslip, 'overtime_amount', 0.0),
                    'deductions': getattr(payslip, 'total_deductions', 0.0),
                    'leave_salary': 0.0,
                    'net_salary': getattr(payslip, 'net_wage', 0.0),
                })
        
        return True

    def action_generate_payroll_sif(self):
        """Generate WPS SIF file from payroll data"""
        for wps in self:
            if not wps.line_ids:
                raise UserError(_('Please generate WPS lines first.'))
            
            # Generate SIF content
            sif_content = wps._generate_payroll_sif_content()
            
            # Encode and save
            file_data = base64.b64encode(sif_content.encode('utf-8'))
            file_name = f"WPS_{wps.company_id.name}_{wps.period_month}_{wps.period_year}.SIF"
            
            wps.write({
                'sif_file': file_data,
                'sif_filename': file_name,
                'state': 'generated',
            })
        
        return True

    def _generate_payroll_sif_content(self):
        """Generate SIF file content for payroll"""
        self.ensure_one()
        
        lines = []
        
        # Header Record (EDR - Employer Details Record)
        header = self._generate_payroll_header_record()
        lines.append(header)
        
        # Employee Records (SCR - Salary Credit Records)
        for line in self.line_ids:
            employee_record = self._generate_payroll_employee_record(line)
            lines.append(employee_record)
        
        return '\n'.join(lines)

    def _generate_payroll_header_record(self):
        """Generate EDR (Employer Details Record) for payroll"""
        return ','.join([
            'EDR',
            self.employer_eid or '',
            self.employer_bank_code or '',
            self.employer_account or '',
            self.period_month,
            self.period_year,
            str(self.employee_count),
            f'{self.total_net:.2f}',
        ])

    def _generate_payroll_employee_record(self, line):
        """Generate SCR (Salary Credit Record) for payroll"""
        return ','.join([
            'SCR',
            line.employee_eid or '',
            line.labour_card_no or '',
            line.bank_code or '',
            line.account_number or '',
            line.iban or '',
            f'{line.basic_salary:.2f}',
            f'{line.housing_allowance:.2f}',
            f'{line.transport_allowance:.2f}',
            f'{line.other_allowance:.2f}',
            f'{line.overtime:.2f}',
            f'{line.deductions:.2f}',
            f'{line.leave_salary:.2f}',
            f'{line.net_salary:.2f}',
        ])

    def action_submit(self):
        """Mark as submitted to bank"""
        self.write({
            'state': 'submitted',
            'submission_date': fields.Date.today(),
        })

    def action_mark_processed(self):
        """Mark as processed"""
        self.write({
            'state': 'processed',
            'processing_date': fields.Date.today(),
        })

    def action_mark_failed(self):
        """Mark as failed/rejected"""
        self.write({'state': 'rejected'})

    def action_cancel(self):
        """Cancel WPS file"""
        self.write({'state': 'cancelled'})


class WPSFileLinePayrollExtension(models.Model):
    """Extend WPS File Line with Payroll-specific fields"""
    _inherit = 'tazweed.wps.file.line'

    # Payroll-specific fields
    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Payslip',
        help='Link to source payslip',
    )
    
    # Compatibility aliases
    bank_account = fields.Char(
        string='Bank Account',
        related='account_number',
        store=False,
    )
    other_allowances = fields.Float(
        string='Other Allowances Alt',
        related='other_allowance',
        store=False,
    )
