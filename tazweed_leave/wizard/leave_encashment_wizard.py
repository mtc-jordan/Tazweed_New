# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LeaveEncashmentWizard(models.TransientModel):
    """Leave Encashment Wizard"""
    _name = 'tazweed.leave.encashment.wizard'
    _description = 'Leave Encashment Wizard'

    allocation_id = fields.Many2one(
        'hr.leave.allocation',
        string='Allocation',
        required=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
    )
    available_days = fields.Float(
        string='Available Days',
        readonly=True,
    )
    encash_days = fields.Float(
        string='Days to Encash',
        required=True,
    )
    daily_rate = fields.Float(
        string='Daily Rate',
        compute='_compute_daily_rate',
    )
    encashment_rate = fields.Float(
        string='Encashment Rate',
        related='allocation_id.holiday_status_id.encashment_rate',
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
    )
    notes = fields.Text(string='Notes')

    @api.depends('employee_id')
    def _compute_daily_rate(self):
        """Compute daily rate from contract"""
        for wizard in self:
            if wizard.employee_id and wizard.employee_id.contract_id:
                wizard.daily_rate = wizard.employee_id.contract_id.wage / 30
            else:
                wizard.daily_rate = 0

    @api.depends('encash_days', 'daily_rate', 'encashment_rate')
    def _compute_total_amount(self):
        """Compute total encashment amount"""
        for wizard in self:
            wizard.total_amount = wizard.encash_days * wizard.daily_rate * wizard.encashment_rate

    @api.constrains('encash_days', 'available_days')
    def _check_encash_days(self):
        """Validate encash days"""
        for wizard in self:
            if wizard.encash_days <= 0:
                raise ValidationError(_('Days to encash must be greater than 0.'))
            if wizard.encash_days > wizard.available_days:
                raise ValidationError(_('Cannot encash more days than available.'))

    def action_encash(self):
        """Process encashment"""
        self.ensure_one()
        
        # Update allocation
        self.allocation_id.write({
            'encashed_days': self.allocation_id.encashed_days + self.encash_days,
            'encashment_amount': self.allocation_id.encashment_amount + self.total_amount,
        })
        
        # Create encashment record (could be linked to payroll)
        # This can be extended to create a payroll input
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Leave Encashment'),
                'message': _('Successfully encashed %s days for %s') % (self.encash_days, self.total_amount),
                'type': 'success',
            }
        }


class LeaveAllocationWizard(models.TransientModel):
    """Bulk Leave Allocation Wizard"""
    _name = 'tazweed.leave.allocation.wizard'
    _description = 'Bulk Leave Allocation Wizard'

    holiday_status_id = fields.Many2one(
        'hr.leave.type',
        string='Leave Type',
        required=True,
    )
    allocation_type = fields.Selection([
        ('regular', 'Regular Allocation'),
        ('accrual', 'Accrual'),
    ], string='Allocation Type', default='regular', required=True)
    number_of_days = fields.Float(
        string='Number of Days',
        required=True,
    )
    validity_start = fields.Date(
        string='Valid From',
        required=True,
    )
    validity_end = fields.Date(
        string='Valid Until',
        required=True,
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        required=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
    )
    notes = fields.Text(string='Notes')

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Filter employees by department"""
        if self.department_id:
            employees = self.env['hr.employee'].search([
                ('department_id', '=', self.department_id.id),
            ])
            self.employee_ids = employees

    def action_allocate(self):
        """Create allocations for selected employees"""
        self.ensure_one()
        
        allocations = self.env['hr.leave.allocation']
        
        for employee in self.employee_ids:
            allocation = self.env['hr.leave.allocation'].create({
                'name': f'{self.holiday_status_id.name} - {employee.name}',
                'holiday_status_id': self.holiday_status_id.id,
                'employee_id': employee.id,
                'allocation_type': self.allocation_type,
                'number_of_days': self.number_of_days,
                'validity_start': self.validity_start,
                'validity_end': self.validity_end,
                'notes': self.notes,
            })
            allocations |= allocation
        
        return {
            'name': _('Created Allocations'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.allocation',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', allocations.ids)],
        }


class AttendanceSummaryWizard(models.TransientModel):
    """Attendance Summary Generation Wizard"""
    _name = 'tazweed.attendance.summary.wizard'
    _description = 'Attendance Summary Wizard'

    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'),
        ('4', 'April'), ('5', 'May'), ('6', 'June'),
        ('7', 'July'), ('8', 'August'), ('9', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], string='Month', required=True)
    year = fields.Integer(
        string='Year',
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
    )
    regenerate = fields.Boolean(
        string='Regenerate Existing',
        default=False,
    )

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Filter employees by department"""
        if self.department_id:
            employees = self.env['hr.employee'].search([
                ('department_id', '=', self.department_id.id),
            ])
            self.employee_ids = employees

    def action_generate(self):
        """Generate attendance summaries"""
        self.ensure_one()
        
        employees = self.employee_ids or self.env['hr.employee'].search([])
        summaries = self.env['hr.attendance.summary']
        
        for employee in employees:
            # Check if summary exists
            existing = self.env['hr.attendance.summary'].search([
                ('employee_id', '=', employee.id),
                ('month', '=', self.month),
                ('year', '=', self.year),
            ], limit=1)
            
            if existing and not self.regenerate:
                continue
            
            if existing and self.regenerate:
                existing.unlink()
            
            # Calculate summary data
            # This is a simplified version - actual implementation would calculate from attendance records
            summary = self.env['hr.attendance.summary'].create({
                'employee_id': employee.id,
                'month': self.month,
                'year': self.year,
                'working_days': 22,  # Placeholder
                'present_days': 20,  # Placeholder
                'absent_days': 2,  # Placeholder
            })
            summaries |= summary
        
        return {
            'name': _('Attendance Summaries'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.summary',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', summaries.ids)],
        }
