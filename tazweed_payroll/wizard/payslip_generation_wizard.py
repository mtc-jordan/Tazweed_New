# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class PayslipGenerationWizard(models.TransientModel):
    """Wizard to generate payslips for multiple employees"""
    _name = 'tazweed.payslip.generation.wizard'
    _description = 'Payslip Generation Wizard'

    # Batch
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
    )
    
    # Period
    date_start = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_end = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: (date.today().replace(day=1) + relativedelta(months=1, days=-1)),
    )
    
    # Structure
    struct_id = fields.Many2one(
        'hr.payroll.structure',
        string='Salary Structure',
    )
    
    # Filters
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
    )
    
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
    )
    
    # Options
    create_batch = fields.Boolean(
        string='Create New Batch',
        default=False,
    )
    batch_name = fields.Char(
        string='Batch Name',
    )
    
    skip_existing = fields.Boolean(
        string='Skip Existing Payslips',
        default=True,
        help='Skip employees who already have a payslip for this period',
    )
    
    auto_compute = fields.Boolean(
        string='Auto Compute',
        default=True,
        help='Automatically compute payslips after generation',
    )

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Filter employees by department"""
        domain = [('contract_id', '!=', False)]
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        
        employees = self.env['hr.employee'].search(domain)
        self.employee_ids = employees

    def action_generate(self):
        """Generate payslips"""
        self.ensure_one()
        
        # Get or create batch
        if self.create_batch:
            batch = self.env['hr.payslip.run'].create({
                'name': self.batch_name or f'Payroll {self.date_start.strftime("%B %Y")}',
                'date_start': self.date_start,
                'date_end': self.date_end,
                'struct_id': self.struct_id.id if self.struct_id else False,
                'department_id': self.department_id.id if self.department_id else False,
            })
        else:
            batch = self.payslip_run_id
        
        # Get employees
        if self.employee_ids:
            employees = self.employee_ids
        elif self.department_id:
            employees = self.env['hr.employee'].search([
                ('department_id', '=', self.department_id.id),
                ('contract_id', '!=', False),
            ])
        else:
            employees = self.env['hr.employee'].search([
                ('contract_id', '!=', False),
            ])
        
        # Generate payslips
        payslips = self.env['hr.payslip']
        for employee in employees:
            # Check for existing payslip
            if self.skip_existing:
                existing = self.env['hr.payslip'].search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '<=', self.date_end),
                    ('date_to', '>=', self.date_start),
                    ('state', '!=', 'cancel'),
                ])
                if existing:
                    continue
            
            # Get contract
            contract = employee.contract_id
            if not contract:
                continue
            
            # Get structure
            struct = self.struct_id or contract.struct_id
            if not struct:
                continue
            
            # Create payslip
            payslip = self.env['hr.payslip'].create({
                'employee_id': employee.id,
                'contract_id': contract.id,
                'struct_id': struct.id,
                'date_from': self.date_start,
                'date_to': self.date_end,
                'payslip_run_id': batch.id if batch else False,
                'name': f'{employee.name} - {self.date_start.strftime("%B %Y")}',
            })
            payslips |= payslip
        
        # Auto compute
        if self.auto_compute and payslips:
            payslips.compute_sheet()
        
        # Return action
        if batch:
            return {
                'name': _('Payslip Batch'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip.run',
                'res_id': batch.id,
                'view_mode': 'form',
            }
        else:
            return {
                'name': _('Generated Payslips'),
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payslips.ids)],
            }
