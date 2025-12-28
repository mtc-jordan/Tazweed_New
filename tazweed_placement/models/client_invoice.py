# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class ClientInvoice(models.Model):
    """Client Invoice for Placement Services"""
    _name = 'tazweed.client.invoice'
    _description = 'Client Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_invoice desc, name desc'

    name = fields.Char(
        string='Invoice Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Client
    client_id = fields.Many2one(
        'tazweed.client',
        string='Client',
        required=True,
        tracking=True,
    )
    partner_id = fields.Many2one(
        related='client_id.partner_id',
        string='Partner',
        store=True,
    )
    
    # Dates
    date_invoice = fields.Date(
        string='Invoice Date',
        default=fields.Date.today,
        required=True,
        tracking=True,
    )
    date_due = fields.Date(
        string='Due Date',
        compute='_compute_due_date',
        store=True,
    )
    period_start = fields.Date(
        string='Period Start',
        required=True,
    )
    period_end = fields.Date(
        string='Period End',
        required=True,
    )
    
    # Invoice Lines
    line_ids = fields.One2many(
        'tazweed.client.invoice.line',
        'invoice_id',
        string='Invoice Lines',
    )
    
    # Amounts
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    amount_untaxed = fields.Monetary(
        string='Subtotal',
        compute='_compute_amounts',
        store=True,
    )
    amount_tax = fields.Monetary(
        string='VAT (5%)',
        compute='_compute_amounts',
        store=True,
    )
    amount_total = fields.Monetary(
        string='Total',
        compute='_compute_amounts',
        store=True,
    )
    
    # VAT
    apply_vat = fields.Boolean(
        string='Apply VAT',
        default=True,
    )
    vat_rate = fields.Float(
        string='VAT Rate (%)',
        default=5.0,
    )
    
    # Odoo Invoice Link
    account_move_id = fields.Many2one(
        'account.move',
        string='Accounting Invoice',
        readonly=True,
        copy=False,
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.client.invoice') or _('New')
        return super().create(vals)

    @api.depends('date_invoice', 'client_id.payment_terms')
    def _compute_due_date(self):
        for invoice in self:
            if invoice.date_invoice and invoice.client_id:
                days = invoice.client_id.payment_terms or 30
                invoice.date_due = invoice.date_invoice + timedelta(days=days)
            else:
                invoice.date_due = invoice.date_invoice

    @api.depends('line_ids.amount', 'apply_vat', 'vat_rate')
    def _compute_amounts(self):
        for invoice in self:
            invoice.amount_untaxed = sum(line.amount for line in invoice.line_ids)
            if invoice.apply_vat:
                invoice.amount_tax = invoice.amount_untaxed * invoice.vat_rate / 100
            else:
                invoice.amount_tax = 0
            invoice.amount_total = invoice.amount_untaxed + invoice.amount_tax

    def action_confirm(self):
        """Confirm invoice"""
        self.write({'state': 'confirmed'})

    def action_send(self):
        """Mark as sent"""
        self.write({'state': 'sent'})

    def action_paid(self):
        """Mark as paid"""
        self.write({'state': 'paid'})

    def action_cancel(self):
        """Cancel invoice"""
        self.write({'state': 'cancelled'})

    def action_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def action_create_accounting_invoice(self):
        """Create Odoo accounting invoice"""
        self.ensure_one()
        
        if self.account_move_id:
            raise UserError(_('Accounting invoice already exists.'))
        
        if not self.line_ids:
            raise UserError(_('Cannot create invoice without lines.'))
        
        # Check if account module is installed
        if 'account.move' not in self.env:
            raise UserError(_('Accounting module is not installed.'))
        
        # Prepare invoice lines
        invoice_lines = []
        for line in self.line_ids:
            invoice_lines.append((0, 0, {
                'name': line.description,
                'quantity': line.quantity,
                'price_unit': line.unit_price,
            }))
        
        # Create the accounting invoice
        move_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.date_invoice,
            'invoice_date_due': self.date_due,
            'ref': self.name,
            'invoice_line_ids': invoice_lines,
        }
        
        move = self.env['account.move'].create(move_vals)
        self.account_move_id = move
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
        }

    def action_view_accounting_invoice(self):
        """View linked accounting invoice"""
        self.ensure_one()
        if not self.account_move_id:
            raise UserError(_('No accounting invoice linked.'))
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.account_move_id.id,
            'view_mode': 'form',
        }

    @api.model
    def generate_monthly_invoices(self, client_id=None, period_start=None, period_end=None):
        """Generate monthly invoices for all active placements"""
        if not period_start:
            # Default to previous month
            today = date.today()
            period_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            period_end = today.replace(day=1) - timedelta(days=1)
        
        domain = [('state', '=', 'active')]
        if client_id:
            domain.append(('client_id', '=', client_id))
        
        placements = self.env['tazweed.placement'].search(domain)
        
        # Group by client
        client_placements = {}
        for placement in placements:
            if placement.client_id.id not in client_placements:
                client_placements[placement.client_id.id] = []
            client_placements[placement.client_id.id].append(placement)
        
        invoices = self.env['tazweed.client.invoice']
        
        for client_id, client_placements_list in client_placements.items():
            client = self.env['tazweed.client'].browse(client_id)
            
            # Create invoice
            invoice = self.create({
                'client_id': client_id,
                'period_start': period_start,
                'period_end': period_end,
            })
            
            # Create lines for each placement
            for placement in client_placements_list:
                # Get employee contract
                contract = placement.employee_id.contract_id if placement.employee_id else None
                
                if contract and contract.billing_type == 'timesheet':
                    # For timesheet-based, calculate from timesheets
                    hours = self._get_timesheet_hours(
                        placement.employee_id, period_start, period_end
                    )
                    quantity = hours
                    unit_price = contract.billing_rate or contract.hourly_rate
                    description = f"{placement.candidate_id.name} - {placement.job_title} ({hours} hours)"
                else:
                    # For fixed, use monthly billing rate
                    quantity = 1
                    if contract:
                        unit_price = contract.billing_rate or placement.total_billing
                    else:
                        unit_price = placement.total_billing
                    description = f"{placement.candidate_id.name} - {placement.job_title} (Monthly)"
                
                self.env['tazweed.client.invoice.line'].create({
                    'invoice_id': invoice.id,
                    'placement_id': placement.id,
                    'employee_id': placement.employee_id.id if placement.employee_id else False,
                    'description': description,
                    'quantity': quantity,
                    'unit_price': unit_price,
                })
            
            invoices |= invoice
        
        return invoices

    def _get_timesheet_hours(self, employee, period_start, period_end):
        """Get total timesheet hours for employee in period"""
        if 'account.analytic.line' not in self.env:
            return 0
        
        timesheets = self.env['account.analytic.line'].search([
            ('employee_id', '=', employee.id),
            ('date', '>=', period_start),
            ('date', '<=', period_end),
        ])
        return sum(ts.unit_amount for ts in timesheets)


class ClientInvoiceLine(models.Model):
    """Client Invoice Line"""
    _name = 'tazweed.client.invoice.line'
    _description = 'Client Invoice Line'
    _order = 'sequence, id'

    invoice_id = fields.Many2one(
        'tazweed.client.invoice',
        string='Invoice',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    
    # References
    placement_id = fields.Many2one(
        'tazweed.placement',
        string='Placement',
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
    )
    
    # Line Details
    description = fields.Char(
        string='Description',
        required=True,
    )
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
    )
    unit_price = fields.Float(
        string='Unit Price',
        digits=(16, 2),
    )
    
    # Computed
    currency_id = fields.Many2one(
        related='invoice_id.currency_id',
    )
    amount = fields.Monetary(
        string='Amount',
        compute='_compute_amount',
        store=True,
    )

    @api.depends('quantity', 'unit_price')
    def _compute_amount(self):
        for line in self:
            line.amount = line.quantity * line.unit_price


class ClientInvoiceWizard(models.TransientModel):
    """Wizard to generate client invoices"""
    _name = 'tazweed.client.invoice.wizard'
    _description = 'Generate Client Invoices'

    client_id = fields.Many2one(
        'tazweed.client',
        string='Client',
        help='Leave empty to generate for all clients',
    )
    period_start = fields.Date(
        string='Period Start',
        required=True,
        default=lambda self: (date.today().replace(day=1) - timedelta(days=1)).replace(day=1),
    )
    period_end = fields.Date(
        string='Period End',
        required=True,
        default=lambda self: date.today().replace(day=1) - timedelta(days=1),
    )

    def action_generate(self):
        """Generate invoices"""
        invoices = self.env['tazweed.client.invoice'].generate_monthly_invoices(
            client_id=self.client_id.id if self.client_id else None,
            period_start=self.period_start,
            period_end=self.period_end,
        )
        
        if not invoices:
            raise UserError(_('No active placements found for the selected period.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Invoices'),
            'res_model': 'tazweed.client.invoice',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', invoices.ids)],
        }
