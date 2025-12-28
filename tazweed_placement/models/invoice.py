# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class PlacementInvoice(models.Model):
    """Placement Invoice"""
    _name = 'tazweed.placement.invoice'
    _description = 'Placement Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_invoice desc'

    name = fields.Char(
        string='Invoice Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Relations
    placement_id = fields.Many2one('tazweed.placement', string='Placement', required=True)
    client_id = fields.Many2one('tazweed.client', string='Client', required=True)
    
    # Invoice Details
    invoice_type = fields.Selection([
        ('monthly', 'Monthly Invoice'),
        ('placement_fee', 'Placement Fee'),
        ('one_time', 'One-Time Charge'),
        ('adjustment', 'Adjustment'),
    ], string='Invoice Type', required=True, default='monthly')
    
    date_invoice = fields.Date(string='Invoice Date', default=fields.Date.today, required=True)
    date_due = fields.Date(string='Due Date', required=True)
    
    period_start = fields.Date(string='Period Start')
    period_end = fields.Date(string='Period End')
    
    # Amounts
    amount = fields.Float(string='Amount', required=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    vat_pct = fields.Float(string='VAT %', default=5.0)
    vat_amount = fields.Float(string='VAT Amount', compute='_compute_totals', store=True)
    total_amount = fields.Float(string='Total Amount', compute='_compute_totals', store=True)
    
    # Payment
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    amount_paid = fields.Float(string='Amount Paid')
    amount_due = fields.Float(string='Amount Due', compute='_compute_amount_due', store=True)
    
    payment_date = fields.Date(string='Payment Date')
    payment_reference = fields.Char(string='Payment Reference')
    
    # Link to Odoo Invoice (requires account module)
    # odoo_invoice_id = fields.Many2one('account.move', string='Odoo Invoice')
    
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.placement.invoice') or _('New')
        return super().create(vals)

    @api.depends('amount', 'vat_pct')
    def _compute_totals(self):
        for invoice in self:
            invoice.vat_amount = invoice.amount * (invoice.vat_pct / 100)
            invoice.total_amount = invoice.amount + invoice.vat_amount

    @api.depends('total_amount', 'amount_paid')
    def _compute_amount_due(self):
        for invoice in self:
            invoice.amount_due = invoice.total_amount - invoice.amount_paid

    def action_send(self):
        self.write({'state': 'sent'})

    def action_register_payment(self):
        """Open payment wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Register Payment'),
            'res_model': 'tazweed.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_invoice_id': self.id},
        }

    def action_mark_paid(self):
        self.write({
            'state': 'paid',
            'amount_paid': self.total_amount,
            'payment_date': fields.Date.today(),
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_create_odoo_invoice(self):
        """Create corresponding Odoo account.move invoice"""
        self.ensure_one()
        
        # This would create an actual Odoo invoice
        # For now, just a placeholder
        pass

    @api.model
    def check_overdue_invoices(self):
        """Cron job to mark overdue invoices"""
        today = date.today()
        overdue = self.search([
            ('state', 'in', ('sent', 'partial')),
            ('date_due', '<', today),
        ])
        overdue.write({'state': 'overdue'})
