# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class EmployeeDocument(models.Model):
    """Employee Document Management"""
    _name = 'tazweed.employee.document'
    _description = 'Employee Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date asc, id desc'
    _rec_name = 'display_name'

    name = fields.Char(string='Document Name', required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
        index=True,
    )
    document_type_id = fields.Many2one(
        'tazweed.document.type',
        string='Document Type',
        required=True,
    )
    document_number = fields.Char(string='Document Number')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    issue_place = fields.Char(string='Issue Place')
    issue_authority = fields.Char(string='Issuing Authority')
    
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')
    attachment_filename = fields.Char(
        string='Attachment Filename',
        related='attachment_name',
        store=True,
    )
    
    state = fields.Selection([
        ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Status', compute='_compute_state', store=True)
    
    days_to_expiry = fields.Integer(
        string='Days to Expiry',
        compute='_compute_state',
        store=True,
    )
    
    notes = fields.Text(string='Notes')
    is_renewable = fields.Boolean(
        string='Is Renewable',
        related='document_type_id.is_renewable',
        store=True,
        readonly=True,
    )
    renewal_reminder_days = fields.Integer(
        string='Renewal Reminder Days',
        default=30,
        help='Number of days before expiry to send renewal reminder',
    )
    renewed_document_id = fields.Many2one(
        'tazweed.employee.document',
        string='Renewed Document',
        help='Reference to the new document that replaced this one',
    )
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('name', 'document_type_id', 'employee_id')
    def _compute_display_name(self):
        for record in self:
            if record.document_type_id and record.employee_id:
                record.display_name = f"{record.employee_id.name} - {record.document_type_id.name}"
            else:
                record.display_name = record.name or 'New Document'

    @api.depends('expiry_date', 'document_type_id.alert_days')
    def _compute_state(self):
        today = date.today()
        for record in self:
            if not record.expiry_date:
                record.state = 'valid'
                record.days_to_expiry = 999
            else:
                delta = (record.expiry_date - today).days
                record.days_to_expiry = delta
                alert_days = record.document_type_id.alert_days or 30
                if delta < 0:
                    record.state = 'expired'
                elif delta <= alert_days:
                    record.state = 'expiring'
                else:
                    record.state = 'valid'

    @api.constrains('issue_date', 'expiry_date')
    def _check_dates(self):
        for record in self:
            if record.issue_date and record.expiry_date:
                if record.issue_date > record.expiry_date:
                    raise ValidationError(_('Issue date cannot be after expiry date.'))

    def action_renew(self):
        """Open wizard to renew document"""
        return {
            'name': _('Renew Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.document.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_document_id': self.id},
        }
