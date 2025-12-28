# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class HrLeaveAllocation(models.Model):
    """Extended Leave Allocation with UAE-specific features"""
    _inherit = 'hr.leave.allocation'

    # Reference
    reference = fields.Char(
        string='Reference',
        readonly=True,
        copy=False,
        default='/',
    )
    
    # Allocation Type
    allocation_type = fields.Selection([
        ('regular', 'Regular Allocation'),
        ('accrual', 'Accrual'),
        ('carry_forward', 'Carry Forward'),
        ('adjustment', 'Adjustment'),
        ('encashment_reversal', 'Encashment Reversal'),
    ], string='Allocation Type', default='regular', required=True)
    
    # Validity
    validity_start = fields.Date(
        string='Valid From',
        default=lambda self: date.today().replace(month=1, day=1),
    )
    validity_end = fields.Date(
        string='Valid Until',
        default=lambda self: date.today().replace(month=12, day=31),
    )
    
    # Accrual
    is_accrual = fields.Boolean(
        string='Accrual Based',
        related='holiday_status_id.is_accrual',
        store=True,
    )
    accrual_rate = fields.Float(
        string='Accrual Rate',
        related='holiday_status_id.accrual_rate',
        store=True,
    )
    accrued_days = fields.Float(
        string='Accrued Days',
        compute='_compute_accrued_days',
        store=True,
    )
    
    # Balance
    used_days = fields.Float(
        string='Used Days',
        compute='_compute_used_days',
        store=True,
    )
    remaining_days = fields.Float(
        string='Remaining Days',
        compute='_compute_remaining_days',
        store=True,
    )
    
    # Carry Forward
    carried_forward_from_id = fields.Many2one(
        'hr.leave.allocation',
        string='Carried Forward From',
    )
    carry_forward_expiry = fields.Date(
        string='Carry Forward Expiry',
    )
    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_is_expired',
        store=True,
    )
    
    # Encashment
    encashed_days = fields.Float(
        string='Encashed Days',
        default=0,
    )
    encashment_amount = fields.Float(
        string='Encashment Amount',
        default=0,
    )
    
    # Pro-rata
    is_pro_rata = fields.Boolean(
        string='Pro-rata Allocation',
        default=False,
    )
    pro_rata_start_date = fields.Date(
        string='Pro-rata Start Date',
    )
    pro_rata_days = fields.Float(
        string='Pro-rata Days',
        compute='_compute_pro_rata_days',
        store=True,
    )

    @api.model
    def create(self, vals):
        """Generate sequence on create"""
        if vals.get('reference', '/') == '/':
            vals['reference'] = self.env['ir.sequence'].next_by_code('hr.leave.allocation') or '/'
        return super().create(vals)

    @api.depends('employee_id', 'holiday_status_id', 'validity_start')
    def _compute_accrued_days(self):
        """Compute accrued days based on service"""
        for allocation in self:
            if allocation.is_accrual and allocation.employee_id:
                # Calculate months of service
                join_date = allocation.employee_id.joining_date or allocation.employee_id.create_date.date()
                start_date = max(join_date, allocation.validity_start or date.today())
                end_date = min(date.today(), allocation.validity_end or date.today())
                
                if end_date >= start_date:
                    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
                    allocation.accrued_days = months * allocation.accrual_rate
                else:
                    allocation.accrued_days = 0
            else:
                allocation.accrued_days = 0

    @api.depends('employee_id', 'holiday_status_id', 'validity_start', 'validity_end')
    def _compute_used_days(self):
        """Compute used days from approved leaves"""
        for allocation in self:
            if allocation.employee_id and allocation.holiday_status_id:
                domain = [
                    ('employee_id', '=', allocation.employee_id.id),
                    ('holiday_status_id', '=', allocation.holiday_status_id.id),
                    ('state', '=', 'validate'),
                ]
                if allocation.validity_start:
                    domain.append(('date_from', '>=', allocation.validity_start))
                if allocation.validity_end:
                    domain.append(('date_to', '<=', allocation.validity_end))
                
                leaves = self.env['hr.leave'].search(domain)
                allocation.used_days = sum(leaves.mapped('number_of_days'))
            else:
                allocation.used_days = 0

    @api.depends('number_of_days', 'used_days', 'encashed_days')
    def _compute_remaining_days(self):
        """Compute remaining days"""
        for allocation in self:
            allocation.remaining_days = allocation.number_of_days - allocation.used_days - allocation.encashed_days

    @api.depends('carry_forward_expiry')
    def _compute_is_expired(self):
        """Check if carry forward has expired"""
        for allocation in self:
            if allocation.carry_forward_expiry:
                allocation.is_expired = allocation.carry_forward_expiry < date.today()
            else:
                allocation.is_expired = False

    @api.depends('is_pro_rata', 'pro_rata_start_date', 'number_of_days', 'validity_end')
    def _compute_pro_rata_days(self):
        """Compute pro-rata days"""
        for allocation in self:
            if allocation.is_pro_rata and allocation.pro_rata_start_date and allocation.validity_end:
                # Calculate remaining months in the year
                end_date = allocation.validity_end
                start_date = allocation.pro_rata_start_date
                
                if end_date >= start_date:
                    total_months = 12
                    remaining_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
                    allocation.pro_rata_days = allocation.number_of_days * remaining_months / total_months
                else:
                    allocation.pro_rata_days = 0
            else:
                allocation.pro_rata_days = allocation.number_of_days

    def action_carry_forward(self):
        """Create carry forward allocation for next year"""
        self.ensure_one()
        
        leave_type = self.holiday_status_id
        if not leave_type.allow_carry_forward:
            raise ValidationError(_('Carry forward is not allowed for this leave type.'))
        
        # Calculate carry forward days
        carry_forward_days = min(self.remaining_days, leave_type.max_carry_forward_days)
        
        if carry_forward_days <= 0:
            raise ValidationError(_('No days available for carry forward.'))
        
        # Calculate expiry date
        expiry_date = False
        if leave_type.carry_forward_expiry_months > 0:
            expiry_date = date.today() + relativedelta(months=leave_type.carry_forward_expiry_months)
        
        # Create new allocation
        new_allocation = self.copy({
            'allocation_type': 'carry_forward',
            'number_of_days': carry_forward_days,
            'validity_start': date.today().replace(month=1, day=1) + relativedelta(years=1),
            'validity_end': date.today().replace(month=12, day=31) + relativedelta(years=1),
            'carried_forward_from_id': self.id,
            'carry_forward_expiry': expiry_date,
            'state': 'draft',
        })
        
        return {
            'name': _('Carry Forward Allocation'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.allocation',
            'res_id': new_allocation.id,
            'view_mode': 'form',
        }

    def action_encash(self):
        """Open encashment wizard"""
        self.ensure_one()
        
        leave_type = self.holiday_status_id
        if not leave_type.allow_encashment:
            raise ValidationError(_('Encashment is not allowed for this leave type.'))
        
        if self.remaining_days < leave_type.min_balance_for_encashment:
            raise ValidationError(_(
                'Minimum balance of %d days is required for encashment.'
            ) % leave_type.min_balance_for_encashment)
        
        return {
            'name': _('Leave Encashment'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.leave.encashment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_allocation_id': self.id,
                'default_employee_id': self.employee_id.id,
                'default_available_days': self.remaining_days,
            },
        }


class HrLeaveAllocationAccrual(models.Model):
    """Leave Allocation Accrual Plan"""
    _name = 'hr.leave.allocation.accrual'
    _description = 'Leave Allocation Accrual Plan'

    name = fields.Char(string='Name', required=True)
    holiday_status_id = fields.Many2one(
        'hr.leave.type',
        string='Leave Type',
        required=True,
    )
    accrual_rate = fields.Float(
        string='Accrual Rate (Days/Month)',
        required=True,
    )
    max_accrual = fields.Float(
        string='Maximum Accrual',
        help='Maximum days that can be accrued (0 = unlimited)',
    )
    start_after_months = fields.Integer(
        string='Start After (Months)',
        default=0,
    )
    active = fields.Boolean(default=True)
