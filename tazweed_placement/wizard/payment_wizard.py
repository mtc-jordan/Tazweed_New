# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PaymentWizard(models.TransientModel):
    """Wizard to register payment for invoice"""
    _name = 'tazweed.payment.wizard'
    _description = 'Register Payment'

    invoice_id = fields.Many2one('tazweed.placement.invoice', string='Invoice', required=True)
    
    # Invoice Info
    invoice_amount = fields.Float(related='invoice_id.total_amount', string='Invoice Amount')
    amount_due = fields.Float(related='invoice_id.amount_due', string='Amount Due')
    
    # Payment Details
    payment_amount = fields.Float(string='Payment Amount', required=True)
    payment_date = fields.Date(string='Payment Date', required=True, default=fields.Date.today)
    payment_reference = fields.Char(string='Payment Reference')
    
    payment_method = fields.Selection([
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('other', 'Other'),
    ], string='Payment Method', default='bank_transfer')
    
    notes = fields.Text(string='Notes')

    @api.onchange('invoice_id')
    def _onchange_invoice(self):
        if self.invoice_id:
            self.payment_amount = self.invoice_id.amount_due

    @api.constrains('payment_amount')
    def _check_payment_amount(self):
        for wizard in self:
            if wizard.payment_amount <= 0:
                raise ValidationError(_('Payment amount must be positive.'))
            if wizard.payment_amount > wizard.amount_due:
                raise ValidationError(_('Payment amount cannot exceed amount due.'))

    def action_register_payment(self):
        """Register the payment"""
        self.ensure_one()
        
        new_paid = self.invoice_id.amount_paid + self.payment_amount
        new_due = self.invoice_id.total_amount - new_paid
        
        vals = {
            'amount_paid': new_paid,
            'payment_date': self.payment_date,
            'payment_reference': self.payment_reference,
        }
        
        if new_due <= 0:
            vals['state'] = 'paid'
        else:
            vals['state'] = 'partial'
        
        self.invoice_id.write(vals)
        
        # Log payment
        self.invoice_id.message_post(
            body=_(
                'Payment registered: %s %s\nReference: %s\nMethod: %s',
                self.invoice_id.currency_id.symbol,
                self.payment_amount,
                self.payment_reference or '-',
                dict(self._fields['payment_method'].selection).get(self.payment_method)
            )
        )
        
        return {'type': 'ir.actions.act_window_close'}
