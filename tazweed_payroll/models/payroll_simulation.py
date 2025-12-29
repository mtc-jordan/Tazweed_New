# -*- coding: utf-8 -*-
"""
Payroll Simulation Module
Preview payroll before processing with what-if scenarios
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class PayrollSimulation(models.Model):
    """Payroll Simulation - Preview payroll before processing"""
    _name = 'payroll.simulation'
    _description = 'Payroll Simulation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Simulation Name',
        required=True,
        tracking=True,
        default=lambda self: _('New Simulation')
    )
    
    # Period Information
    date_from = fields.Date(
        string='Period Start',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Period End',
        required=True,
        default=lambda self: (fields.Date.today().replace(day=1) + relativedelta(months=1) - timedelta(days=1))
    )
    
    # Selection Criteria
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    department_ids = fields.Many2many(
        'hr.department',
        'payroll_simulation_department_rel',
        'simulation_id',
        'department_id',
        string='Departments'
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'payroll_simulation_employee_rel',
        'simulation_id',
        'employee_id',
        string='Employees'
    )
    structure_id = fields.Many2one(
        'hr.payroll.structure',
        string='Salary Structure'
    )
    
    # Simulation Parameters
    simulation_type = fields.Selection([
        ('standard', 'Standard Payroll'),
        ('salary_increase', 'Salary Increase Scenario'),
        ('bonus', 'Bonus Distribution'),
        ('overtime', 'Overtime Projection'),
        ('deduction', 'Deduction Impact'),
        ('custom', 'Custom Scenario')
    ], string='Simulation Type', default='standard', required=True)
    
    # Scenario Parameters
    increase_percentage = fields.Float(
        string='Increase %',
        help='Percentage increase for salary increase scenario'
    )
    bonus_amount = fields.Float(
        string='Bonus Amount',
        help='Fixed bonus amount per employee'
    )
    bonus_percentage = fields.Float(
        string='Bonus % of Basic',
        help='Bonus as percentage of basic salary'
    )
    overtime_hours = fields.Float(
        string='Projected Overtime Hours',
        help='Estimated overtime hours per employee'
    )
    additional_deduction = fields.Float(
        string='Additional Deduction',
        help='Additional deduction amount'
    )
    deduction_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Gross')
    ], string='Deduction Type', default='fixed')
    
    # Custom Adjustments
    custom_adjustments = fields.Text(
        string='Custom Adjustments (JSON)',
        help='JSON format: {"employee_id": {"basic": 1000, "allowance": 500}}'
    )
    
    # Results
    state = fields.Selection([
        ('draft', 'Draft'),
        ('simulating', 'Simulating'),
        ('completed', 'Completed'),
        ('compared', 'Compared'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    simulation_line_ids = fields.One2many(
        'payroll.simulation.line',
        'simulation_id',
        string='Simulation Lines'
    )
    
    # Summary Statistics
    total_employees = fields.Integer(
        string='Total Employees',
        compute='_compute_summary',
        store=True
    )
    total_gross = fields.Float(
        string='Total Gross',
        compute='_compute_summary',
        store=True
    )
    total_deductions = fields.Float(
        string='Total Deductions',
        compute='_compute_summary',
        store=True
    )
    total_net = fields.Float(
        string='Total Net',
        compute='_compute_summary',
        store=True
    )
    total_employer_cost = fields.Float(
        string='Total Employer Cost',
        compute='_compute_summary',
        store=True
    )
    
    # Comparison with Previous
    previous_total_net = fields.Float(string='Previous Total Net')
    net_difference = fields.Float(
        string='Net Difference',
        compute='_compute_difference'
    )
    net_difference_percent = fields.Float(
        string='Net Difference %',
        compute='_compute_difference'
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    
    @api.depends('simulation_line_ids', 'simulation_line_ids.gross_salary',
                 'simulation_line_ids.total_deductions', 'simulation_line_ids.net_salary',
                 'simulation_line_ids.employer_cost')
    def _compute_summary(self):
        for record in self:
            lines = record.simulation_line_ids
            record.total_employees = len(lines)
            record.total_gross = sum(lines.mapped('gross_salary'))
            record.total_deductions = sum(lines.mapped('total_deductions'))
            record.total_net = sum(lines.mapped('net_salary'))
            record.total_employer_cost = sum(lines.mapped('employer_cost'))
    
    @api.depends('total_net', 'previous_total_net')
    def _compute_difference(self):
        for record in self:
            record.net_difference = record.total_net - record.previous_total_net
            if record.previous_total_net:
                record.net_difference_percent = (record.net_difference / record.previous_total_net) * 100
            else:
                record.net_difference_percent = 0
    
    def action_run_simulation(self):
        """Run the payroll simulation"""
        self.ensure_one()
        self.state = 'simulating'
        
        # Clear existing lines
        self.simulation_line_ids.unlink()
        
        # Get employees to simulate
        domain = [('company_id', '=', self.company_id.id)]
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        if self.employee_ids:
            domain.append(('id', 'in', self.employee_ids.ids))
        
        employees = self.env['hr.employee'].search(domain)
        
        if not employees:
            raise UserError(_('No employees found matching the criteria.'))
        
        # Parse custom adjustments if any
        custom_adj = {}
        if self.custom_adjustments:
            try:
                custom_adj = json.loads(self.custom_adjustments)
            except json.JSONDecodeError:
                raise ValidationError(_('Invalid JSON format for custom adjustments.'))
        
        # Create simulation lines
        for employee in employees:
            self._create_simulation_line(employee, custom_adj.get(str(employee.id), {}))
        
        self.state = 'completed'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Simulation Complete'),
                'message': _('Payroll simulation completed for %d employees.') % len(employees),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _create_simulation_line(self, employee, custom_adj):
        """Create a simulation line for an employee"""
        # Get contract
        contract = employee.contract_id
        if not contract:
            return
        
        # Base salary components
        basic_salary = contract.wage or 0
        housing_allowance = getattr(contract, 'housing_allowance', 0) or basic_salary * 0.25
        transport_allowance = getattr(contract, 'transport_allowance', 0) or basic_salary * 0.10
        other_allowances = getattr(contract, 'other_allowances', 0) or 0
        
        # Apply scenario adjustments
        if self.simulation_type == 'salary_increase':
            increase_factor = 1 + (self.increase_percentage / 100)
            basic_salary *= increase_factor
            housing_allowance *= increase_factor
            transport_allowance *= increase_factor
        
        # Calculate gross
        gross_salary = basic_salary + housing_allowance + transport_allowance + other_allowances
        
        # Add bonus if applicable
        bonus = 0
        if self.simulation_type == 'bonus':
            if self.bonus_amount:
                bonus = self.bonus_amount
            elif self.bonus_percentage:
                bonus = basic_salary * (self.bonus_percentage / 100)
            gross_salary += bonus
        
        # Add overtime if applicable
        overtime_pay = 0
        if self.simulation_type == 'overtime' and self.overtime_hours:
            hourly_rate = basic_salary / 30 / 8  # Assuming 30 days, 8 hours
            overtime_rate = hourly_rate * 1.5  # 150% for overtime
            overtime_pay = self.overtime_hours * overtime_rate
            gross_salary += overtime_pay
        
        # Apply custom adjustments
        if custom_adj:
            if 'basic' in custom_adj:
                basic_salary = custom_adj['basic']
            if 'allowance' in custom_adj:
                other_allowances = custom_adj['allowance']
            if 'gross' in custom_adj:
                gross_salary = custom_adj['gross']
        
        # Calculate deductions
        # Social insurance (employee share - typically 5% in UAE for nationals)
        social_insurance = 0
        if getattr(employee, 'is_uae_national', False):
            social_insurance = gross_salary * 0.05
        
        # Loan deduction
        loan_deduction = self._get_loan_deduction(employee)
        
        # Additional deduction from scenario
        additional_ded = 0
        if self.simulation_type == 'deduction':
            if self.deduction_type == 'fixed':
                additional_ded = self.additional_deduction
            else:
                additional_ded = gross_salary * (self.additional_deduction / 100)
        
        total_deductions = social_insurance + loan_deduction + additional_ded
        net_salary = gross_salary - total_deductions
        
        # Employer costs
        employer_social = 0
        if getattr(employee, 'is_uae_national', False):
            employer_social = gross_salary * 0.125  # 12.5% employer share
        
        employer_cost = gross_salary + employer_social
        
        # Create line
        self.env['payroll.simulation.line'].create({
            'simulation_id': self.id,
            'employee_id': employee.id,
            'department_id': employee.department_id.id,
            'job_id': employee.job_id.id,
            'basic_salary': basic_salary,
            'housing_allowance': housing_allowance,
            'transport_allowance': transport_allowance,
            'other_allowances': other_allowances,
            'bonus': bonus,
            'overtime_pay': overtime_pay,
            'gross_salary': gross_salary,
            'social_insurance': social_insurance,
            'loan_deduction': loan_deduction,
            'other_deductions': additional_ded,
            'total_deductions': total_deductions,
            'net_salary': net_salary,
            'employer_contribution': employer_social,
            'employer_cost': employer_cost,
        })
    
    def _get_loan_deduction(self, employee):
        """Get active loan deduction for employee"""
        # Try different loan model names
        loan_model = None
        for model_name in ['tazweed.payroll.loan', 'hr.loan', 'tazweed.loan']:
            if model_name in self.env:
                loan_model = self.env[model_name].sudo()
                break
        
        if not loan_model:
            return 0
        
        try:
            loans = loan_model.search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'approved'),
            ])
            # Try different field names for remaining amount and installment
            total = 0
            for loan in loans:
                if hasattr(loan, 'remaining_amount') and loan.remaining_amount > 0:
                    if hasattr(loan, 'monthly_installment'):
                        total += loan.monthly_installment
                    elif hasattr(loan, 'installment_amount'):
                        total += loan.installment_amount
            return total
        except Exception:
            return 0
    
    def action_compare_previous(self):
        """Compare with previous period"""
        self.ensure_one()
        
        # Find previous simulation or actual payroll
        previous_date_from = self.date_from - relativedelta(months=1)
        previous_date_to = self.date_to - relativedelta(months=1)
        
        # Try to find previous simulation
        previous = self.search([
            ('company_id', '=', self.company_id.id),
            ('date_from', '=', previous_date_from),
            ('state', '=', 'completed'),
            ('id', '!=', self.id)
        ], limit=1)
        
        if previous:
            self.previous_total_net = previous.total_net
        else:
            # Try to get from actual payslips
            payslips = self.env['hr.payslip'].search([
                ('company_id', '=', self.company_id.id),
                ('date_from', '>=', previous_date_from),
                ('date_to', '<=', previous_date_to),
                ('state', '=', 'done')
            ])
            self.previous_total_net = sum(payslips.mapped('net_wage'))
        
        self.state = 'compared'
        
        return True
    
    def action_export_report(self):
        """Export simulation report"""
        self.ensure_one()
        return {
            'type': 'ir.actions.report',
            'report_name': 'tazweed_payroll.report_payroll_simulation',
            'report_type': 'qweb-pdf',
            'data': {'simulation_id': self.id},
        }
    
    def action_create_payslips(self):
        """Create actual payslips from simulation"""
        self.ensure_one()
        
        if self.state != 'completed':
            raise UserError(_('Simulation must be completed before creating payslips.'))
        
        # Create payslip batch
        batch = self.env['hr.payslip.run'].create({
            'name': _('Payroll from Simulation: %s') % self.name,
            'date_start': self.date_from,
            'date_end': self.date_to,
        })
        
        for line in self.simulation_line_ids:
            if not line.employee_id.contract_id:
                continue
            
            self.env['hr.payslip'].create({
                'employee_id': line.employee_id.id,
                'contract_id': line.employee_id.contract_id.id,
                'struct_id': self.structure_id.id or line.employee_id.contract_id.struct_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'payslip_run_id': batch.id,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslip Batch'),
            'res_model': 'hr.payslip.run',
            'res_id': batch.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_simulation_lines(self):
        """View simulation lines"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Simulation Details'),
            'res_model': 'payroll.simulation.line',
            'view_mode': 'tree',
            'domain': [('simulation_id', '=', self.id)],
            'context': {'default_simulation_id': self.id},
        }
    
    def action_cancel(self):
        """Cancel the simulation"""
        self.state = 'cancelled'
    
    def action_reset_draft(self):
        """Reset to draft"""
        self.state = 'draft'
        self.simulation_line_ids.unlink()


class PayrollSimulationLine(models.Model):
    """Payroll Simulation Line - Individual employee simulation"""
    _name = 'payroll.simulation.line'
    _description = 'Payroll Simulation Line'
    _order = 'employee_id'

    simulation_id = fields.Many2one(
        'payroll.simulation',
        string='Simulation',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department'
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position'
    )
    
    # Earnings
    basic_salary = fields.Float(string='Basic Salary')
    housing_allowance = fields.Float(string='Housing Allowance')
    transport_allowance = fields.Float(string='Transport Allowance')
    other_allowances = fields.Float(string='Other Allowances')
    bonus = fields.Float(string='Bonus')
    overtime_pay = fields.Float(string='Overtime Pay')
    gross_salary = fields.Float(string='Gross Salary')
    
    # Deductions
    social_insurance = fields.Float(string='Social Insurance')
    loan_deduction = fields.Float(string='Loan Deduction')
    other_deductions = fields.Float(string='Other Deductions')
    total_deductions = fields.Float(string='Total Deductions')
    
    # Net
    net_salary = fields.Float(string='Net Salary')
    
    # Employer Cost
    employer_contribution = fields.Float(string='Employer Contribution')
    employer_cost = fields.Float(string='Total Employer Cost')
    
    # Comparison
    previous_net = fields.Float(string='Previous Net')
    variance = fields.Float(
        string='Variance',
        compute='_compute_variance'
    )
    variance_percent = fields.Float(
        string='Variance %',
        compute='_compute_variance'
    )
    
    @api.depends('net_salary', 'previous_net')
    def _compute_variance(self):
        for record in self:
            record.variance = record.net_salary - record.previous_net
            if record.previous_net:
                record.variance_percent = (record.variance / record.previous_net) * 100
            else:
                record.variance_percent = 0


class PayrollSimulationWizard(models.TransientModel):
    """Wizard for quick payroll simulation"""
    _name = 'payroll.simulation.wizard'
    _description = 'Payroll Simulation Wizard'

    name = fields.Char(
        string='Simulation Name',
        required=True,
        default=lambda self: _('Quick Simulation - %s') % fields.Date.today().strftime('%B %Y')
    )
    date_from = fields.Date(
        string='Period Start',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Period End',
        required=True,
        default=lambda self: (fields.Date.today().replace(day=1) + relativedelta(months=1) - timedelta(days=1))
    )
    simulation_type = fields.Selection([
        ('standard', 'Standard Payroll'),
        ('salary_increase', 'Salary Increase Scenario'),
        ('bonus', 'Bonus Distribution'),
        ('overtime', 'Overtime Projection'),
    ], string='Simulation Type', default='standard', required=True)
    
    increase_percentage = fields.Float(string='Increase %')
    bonus_percentage = fields.Float(string='Bonus % of Basic')
    overtime_hours = fields.Float(string='Overtime Hours')
    
    def action_create_simulation(self):
        """Create and run simulation"""
        simulation = self.env['payroll.simulation'].create({
            'name': self.name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'simulation_type': self.simulation_type,
            'increase_percentage': self.increase_percentage,
            'bonus_percentage': self.bonus_percentage,
            'overtime_hours': self.overtime_hours,
        })
        
        simulation.action_run_simulation()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Payroll Simulation'),
            'res_model': 'payroll.simulation',
            'res_id': simulation.id,
            'view_mode': 'form',
            'target': 'current',
        }
