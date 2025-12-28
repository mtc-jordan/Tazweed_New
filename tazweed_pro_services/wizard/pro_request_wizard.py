# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProRequestWizard(models.TransientModel):
    """Wizard for creating PRO service requests"""
    _name = 'pro.request.wizard'
    _description = 'PRO Service Request Wizard'

    # Request Type
    request_type = fields.Selection([
        ('internal', 'Internal (Employee)'),
        ('external', 'External (Customer)'),
    ], string='Request Type', required=True, default='internal')
    
    # Beneficiary
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee'
    )
    customer_id = fields.Many2one(
        'pro.customer',
        string='Customer'
    )
    
    # Service Selection
    category_id = fields.Many2one(
        'pro.service.category',
        string='Service Category'
    )
    service_id = fields.Many2one(
        'pro.service',
        string='Service',
        required=True,
        domain="[('category_id', '=', category_id)]"
    )
    
    # Options
    is_urgent = fields.Boolean(string='Urgent Processing')
    urgent_available = fields.Boolean(
        related='service_id.urgent_available',
        string='Urgent Available'
    )
    
    # Fees Display
    government_fee = fields.Float(
        related='service_id.government_fee',
        string='Government Fee'
    )
    service_fee = fields.Float(
        related='service_id.service_fee',
        string='Service Fee'
    )
    urgent_fee = fields.Float(
        related='service_id.urgent_fee',
        string='Urgent Fee'
    )
    total_fee = fields.Float(
        string='Total Fee',
        compute='_compute_total_fee'
    )
    
    # Required Documents
    required_document_ids = fields.Many2many(
        related='service_id.required_document_ids',
        string='Required Documents'
    )
    
    # Processing Time
    processing_days = fields.Integer(
        related='service_id.processing_days',
        string='Processing Days'
    )
    urgent_days = fields.Integer(
        related='service_id.urgent_days',
        string='Urgent Days'
    )
    
    # Notes
    description = fields.Text(string='Description/Notes')

    @api.depends('service_id', 'is_urgent')
    def _compute_total_fee(self):
        for record in self:
            if record.service_id:
                total = record.service_id.total_fee
                if record.is_urgent and record.service_id.urgent_available:
                    total += record.service_id.urgent_fee
                record.total_fee = total
            else:
                record.total_fee = 0

    @api.onchange('request_type')
    def _onchange_request_type(self):
        if self.request_type == 'internal':
            self.customer_id = False
        else:
            self.employee_id = False

    @api.onchange('category_id')
    def _onchange_category_id(self):
        self.service_id = False

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id and not self.service_id.urgent_available:
            self.is_urgent = False

    def action_create_request(self):
        """Create the service request"""
        self.ensure_one()
        
        # Validate
        if self.request_type == 'internal' and not self.employee_id:
            raise UserError(_('Please select an employee.'))
        if self.request_type == 'external' and not self.customer_id:
            raise UserError(_('Please select a customer.'))
        
        # Create request
        vals = {
            'request_type': self.request_type,
            'service_id': self.service_id.id,
            'is_urgent': self.is_urgent,
            'description': self.description,
        }
        
        if self.request_type == 'internal':
            vals['employee_id'] = self.employee_id.id
            vals['department_id'] = self.employee_id.department_id.id
        else:
            vals['customer_id'] = self.customer_id.id
        
        request = self.env['pro.service.request'].create(vals)
        
        return {
            'name': _('Service Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.service.request',
            'view_mode': 'form',
            'res_id': request.id,
        }


class ProPaymentWizard(models.TransientModel):
    """Wizard for registering payments"""
    _name = 'pro.payment.wizard'
    _description = 'PRO Payment Wizard'

    billing_id = fields.Many2one(
        'pro.billing',
        string='Billing',
        required=True
    )
    amount = fields.Float(string='Amount', required=True)
    payment_date = fields.Date(
        string='Payment Date',
        default=fields.Date.today,
        required=True
    )
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ], string='Payment Method', required=True, default='cash')
    payment_reference = fields.Char(string='Payment Reference')
    notes = fields.Text(string='Notes')

    def action_register_payment(self):
        """Register the payment"""
        self.ensure_one()
        
        billing = self.billing_id
        new_paid = billing.amount_paid + self.amount
        
        billing.write({
            'amount_paid': new_paid,
            'payment_date': self.payment_date,
            'payment_method': self.payment_method,
            'payment_reference': self.payment_reference,
        })
        
        # Update payment status
        if new_paid >= billing.total_amount:
            billing.payment_status = 'paid'
        elif new_paid > 0:
            billing.payment_status = 'partial'
        
        return {'type': 'ir.actions.act_window_close'}
