# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class WPSBank(models.Model):
    """UAE Bank Registry for WPS"""
    _name = 'tazweed.wps.bank'
    _description = 'UAE WPS Bank'
    _order = 'name'

    name = fields.Char(string='Bank Name', required=True)
    code = fields.Char(string='Bank Code', required=True, help='3-letter bank code')
    routing_code = fields.Char(string='Routing Code', required=True, help='WPS routing code')
    swift_code = fields.Char(string='SWIFT/BIC Code')
    
    # Bank Details
    short_name = fields.Char(string='Short Name')
    bank_type = fields.Selection([
        ('local', 'Local Bank'),
        ('foreign', 'Foreign Bank'),
        ('islamic', 'Islamic Bank'),
        ('exchange', 'Exchange House'),
    ], string='Bank Type', default='local')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    is_wps_enabled = fields.Boolean(string='WPS Enabled', default=True)
    
    # Contact
    website = fields.Char(string='Website')
    phone = fields.Char(string='Phone')
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Bank code must be unique!'),
        ('routing_code_unique', 'UNIQUE(routing_code)', 'Routing code must be unique!'),
    ]

    def name_get(self):
        result = []
        for bank in self:
            name = f'{bank.name} ({bank.code})'
            result.append((bank.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', ('name', operator, name), ('code', operator, name), ('routing_code', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
