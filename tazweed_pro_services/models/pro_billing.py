# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProBilling(models.Model):
    """Billing records for PRO services"""
    _name = 'pro.billing'
    _description = 'PRO Service Billing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Billing Reference',
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    
    # Related Request
    request_id = fields.Many2one(
        'pro.service.request',
        string='Service Request',
        required=True,
        ondelete='cascade'
    )
    service_id = fields.Many2one(
        related='request_id.service_id',
        string='Service',
        store=True
    )
    
    # Customer/Employee
    customer_id = fields.Many2one(
        'pro.customer',
        string='Customer'
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee'
    )
    billing_party = fields.Char(
        string='Billing Party',
        compute='_compute_billing_party',
        store=True
    )
    
    # Customer Details for Invoice
    customer_name = fields.Char(string='Customer Name')
    customer_address = fields.Text(string='Customer Address')
    customer_phone = fields.Char(string='Phone')
    customer_email = fields.Char(string='Email')
    customer_trn = fields.Char(string='TRN (Tax Registration Number)')
    
    # Beneficiary Details (person for whom service was done)
    beneficiary_name = fields.Char(string='Beneficiary Name')
    beneficiary_passport = fields.Char(string='Passport Number')
    beneficiary_emirates_id = fields.Char(string='Emirates ID')
    beneficiary_nationality = fields.Char(string='Nationality')
    
    # Fees
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    government_fee = fields.Float(string='Government Fee', digits=(16, 2))
    service_fee = fields.Float(string='Service Fee', digits=(16, 2))
    urgent_fee = fields.Float(string='Urgent Fee', digits=(16, 2))
    additional_fees = fields.Float(string='Additional Fees', digits=(16, 2))
    discount = fields.Float(string='Discount', digits=(16, 2))
    
    # Totals
    subtotal = fields.Float(
        string='Subtotal',
        compute='_compute_totals',
        store=True
    )
    vat_rate = fields.Float(string='VAT Rate (%)', default=5.0)
    vat_amount = fields.Float(
        string='VAT Amount',
        compute='_compute_totals',
        store=True
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_totals',
        store=True
    )
    
    # Government Fee Breakdown
    govt_fee_breakdown = fields.Text(
        string='Government Fee Breakdown',
        help='Detailed breakdown of government fees'
    )
    
    # Payment
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
    ], string='Payment Status', default='pending', tracking=True)
    
    amount_paid = fields.Float(string='Amount Paid', digits=(16, 2))
    amount_due = fields.Float(
        string='Amount Due',
        compute='_compute_amount_due',
        store=True
    )
    
    payment_date = fields.Date(string='Payment Date')
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('online', 'Online Payment'),
    ], string='Payment Method')
    payment_reference = fields.Char(string='Payment Reference')
    
    # Invoice
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True
    )
    invoice_state = fields.Selection(
        related='invoice_id.state',
        string='Invoice Status'
    )
    
    # Dates
    billing_date = fields.Date(
        string='Billing Date',
        default=fields.Date.today
    )
    due_date = fields.Date(string='Due Date')
    
    # Line Items
    line_ids = fields.One2many(
        'pro.billing.line',
        'billing_id',
        string='Line Items'
    )
    
    # Government Receipts/Attachments
    receipt_ids = fields.One2many(
        'pro.billing.receipt',
        'billing_id',
        string='Government Receipts'
    )
    receipt_count = fields.Integer(
        string='Receipt Count',
        compute='_compute_receipt_count'
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    terms_conditions = fields.Text(
        string='Terms & Conditions',
        default=lambda self: self._get_default_terms()
    )

    def _get_default_terms(self):
        return """1. Payment is due within 15 days from the invoice date.
2. Government fees are non-refundable once submitted to authorities.
3. Service fees are subject to 5% VAT as per UAE regulations.
4. All prices are in UAE Dirhams (AED).
5. For any queries, please contact our PRO department."""

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pro.billing'
                ) or _('New')
        records = super().create(vals_list)
        for record in records:
            record._create_default_lines()
            record._populate_customer_details()
        return records

    def _populate_customer_details(self):
        """Populate customer details from customer or employee"""
        self.ensure_one()
        if self.customer_id:
            self.customer_name = self.customer_id.name
            self.customer_address = self.customer_id.address
            self.customer_phone = self.customer_id.phone
            self.customer_email = self.customer_id.email
            self.customer_trn = self.customer_id.trn if hasattr(self.customer_id, 'trn') else ''
        elif self.employee_id:
            self.customer_name = self.employee_id.name
            self.customer_phone = self.employee_id.mobile_phone or self.employee_id.work_phone
            self.customer_email = self.employee_id.work_email
            self.beneficiary_name = self.employee_id.name
            self.beneficiary_passport = self.employee_id.passport_id if hasattr(self.employee_id, 'passport_id') else ''
            self.beneficiary_emirates_id = self.employee_id.identification_id if hasattr(self.employee_id, 'identification_id') else ''

    @api.depends('customer_id', 'employee_id')
    def _compute_billing_party(self):
        for record in self:
            if record.customer_id:
                record.billing_party = record.customer_id.name
            elif record.employee_id:
                record.billing_party = record.employee_id.name
            else:
                record.billing_party = ''

    @api.depends('government_fee', 'service_fee', 'urgent_fee', 'additional_fees', 'discount', 'vat_rate')
    def _compute_totals(self):
        for record in self:
            subtotal = (
                record.government_fee +
                record.service_fee +
                record.urgent_fee +
                record.additional_fees -
                record.discount
            )
            record.subtotal = subtotal
            record.vat_amount = subtotal * (record.vat_rate / 100)
            record.total_amount = subtotal + record.vat_amount

    @api.depends('total_amount', 'amount_paid')
    def _compute_amount_due(self):
        for record in self:
            record.amount_due = record.total_amount - record.amount_paid

    @api.depends('receipt_ids')
    def _compute_receipt_count(self):
        for record in self:
            record.receipt_count = len(record.receipt_ids)

    def _create_default_lines(self):
        """Create default billing lines from fees"""
        self.ensure_one()
        BillingLine = self.env['pro.billing.line']
        
        if self.government_fee:
            BillingLine.create({
                'billing_id': self.id,
                'description': 'Government Fee - ' + (self.service_id.name if self.service_id else 'PRO Service'),
                'fee_type': 'government',
                'quantity': 1,
                'unit_price': self.government_fee,
                'amount': self.government_fee,
            })
        
        if self.service_fee:
            BillingLine.create({
                'billing_id': self.id,
                'description': 'Service Fee - ' + (self.service_id.name if self.service_id else 'PRO Service'),
                'fee_type': 'service',
                'quantity': 1,
                'unit_price': self.service_fee,
                'amount': self.service_fee,
            })
        
        if self.urgent_fee:
            BillingLine.create({
                'billing_id': self.id,
                'description': 'Urgent Processing Fee',
                'fee_type': 'urgent',
                'quantity': 1,
                'unit_price': self.urgent_fee,
                'amount': self.urgent_fee,
            })

    def action_register_payment(self):
        """Register payment for the billing"""
        self.ensure_one()
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_billing_id': self.id,
                'default_amount': self.amount_due,
            },
        }

    def action_create_invoice(self):
        """Create customer invoice from billing"""
        self.ensure_one()
        
        if self.invoice_id:
            raise UserError(_('Invoice already exists for this billing.'))
        
        # Determine partner
        if self.customer_id and self.customer_id.partner_id:
            partner_id = self.customer_id.partner_id.id
        elif self.employee_id and self.employee_id.user_id:
            partner_id = self.employee_id.user_id.partner_id.id
        else:
            raise UserError(_('No partner found for invoicing. Please link a contact.'))
        
        # Create invoice
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'invoice_date': self.billing_date,
            'invoice_date_due': self.due_date or self.billing_date,
            'ref': self.name,
            'invoice_line_ids': [],
        }
        
        # Add invoice lines
        for line in self.line_ids:
            invoice_vals['invoice_line_ids'].append((0, 0, {
                'name': line.description,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
            }))
        
        invoice = self.env['account.move'].create(invoice_vals)
        self.invoice_id = invoice
        
        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }

    def action_view_invoice(self):
        """View the linked invoice"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('No invoice linked to this billing.'))
        
        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }

    def action_view_receipts(self):
        """View government receipts"""
        self.ensure_one()
        return {
            'name': _('Government Receipts'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.billing.receipt',
            'view_mode': 'tree,form',
            'domain': [('billing_id', '=', self.id)],
            'context': {'default_billing_id': self.id},
        }

    def action_mark_paid(self):
        """Mark billing as paid"""
        for record in self:
            record.payment_status = 'paid'
            record.amount_paid = record.total_amount
            record.payment_date = fields.Date.today()
        return True

    def action_print_invoice(self):
        """Print PRO Services Invoice"""
        return self.env.ref('tazweed_pro_services.action_report_pro_invoice').report_action(self)


class ProBillingLine(models.Model):
    """Line items in billing"""
    _name = 'pro.billing.line'
    _description = 'PRO Billing Line'
    _order = 'sequence'

    billing_id = fields.Many2one(
        'pro.billing',
        string='Billing',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Char(string='Description', required=True)
    fee_type = fields.Selection([
        ('government', 'Government Fee'),
        ('service', 'Service Fee'),
        ('urgent', 'Urgent Fee'),
        ('additional', 'Additional Fee'),
        ('discount', 'Discount'),
        ('third_party', 'Third Party Fee'),
    ], string='Fee Type', default='service')
    
    # Service details
    service_date = fields.Date(string='Service Date')
    authority_name = fields.Char(string='Authority/Provider')
    reference_number = fields.Char(string='Reference Number')
    
    quantity = fields.Float(string='Quantity', default=1)
    unit_price = fields.Float(string='Unit Price', digits=(16, 2))
    amount = fields.Float(
        string='Amount',
        compute='_compute_amount',
        store=True,
        digits=(16, 2)
    )
    
    # Receipt attachment
    receipt_attachment = fields.Binary(string='Receipt/Proof')
    receipt_filename = fields.Char(string='Receipt Filename')

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for record in self:
            record.amount = record.quantity * record.unit_price

    @api.onchange('quantity', 'unit_price')
    def _onchange_calculate_amount(self):
        if self.quantity and self.unit_price:
            self.amount = self.quantity * self.unit_price


class ProBillingReceipt(models.Model):
    """Government receipts and third-party bills attached to billing"""
    _name = 'pro.billing.receipt'
    _description = 'PRO Billing Receipt'
    _order = 'date desc'

    billing_id = fields.Many2one(
        'pro.billing',
        string='Billing',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(string='Receipt Name', required=True)
    receipt_type = fields.Selection([
        ('government', 'Government Receipt'),
        ('typing_center', 'Typing Center Receipt'),
        ('medical', 'Medical Center Receipt'),
        ('translation', 'Translation Receipt'),
        ('attestation', 'Attestation Receipt'),
        ('third_party', 'Third Party Receipt'),
        ('other', 'Other'),
    ], string='Receipt Type', required=True, default='government')
    
    # Receipt Details
    authority_name = fields.Char(string='Authority/Provider Name')
    reference_number = fields.Char(string='Receipt/Reference Number')
    date = fields.Date(string='Receipt Date', default=fields.Date.today)
    
    # Amount
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    amount = fields.Float(string='Amount', digits=(16, 2), required=True)
    
    # Attachment
    attachment = fields.Binary(string='Receipt Image/PDF', required=True)
    attachment_filename = fields.Char(string='Filename')
    
    # Description
    description = fields.Text(string='Description')
    
    # Status
    is_reimbursable = fields.Boolean(
        string='Reimbursable',
        default=True,
        help='Check if this amount should be reimbursed by customer'
    )
