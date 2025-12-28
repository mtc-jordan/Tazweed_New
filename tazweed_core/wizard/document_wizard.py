# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date


class DocumentRenewWizard(models.TransientModel):
    """Wizard to renew employee documents"""
    _name = 'tazweed.document.renew.wizard'
    _description = 'Document Renewal Wizard'

    document_id = fields.Many2one('tazweed.employee.document', string='Document', required=True)
    new_document_number = fields.Char(string='New Document Number')
    new_issue_date = fields.Date(string='New Issue Date', default=fields.Date.today)
    new_expiry_date = fields.Date(string='New Expiry Date', required=True)
    new_attachment = fields.Binary(string='New Attachment')
    new_attachment_name = fields.Char(string='Attachment Name')
    notes = fields.Text(string='Notes')

    def action_renew(self):
        """Renew the document"""
        self.ensure_one()
        vals = {
            'expiry_date': self.new_expiry_date,
        }
        if self.new_document_number:
            vals['document_number'] = self.new_document_number
        if self.new_issue_date:
            vals['issue_date'] = self.new_issue_date
        if self.new_attachment:
            vals['attachment'] = self.new_attachment
            vals['attachment_name'] = self.new_attachment_name
        if self.notes:
            vals['notes'] = (self.document_id.notes or '') + '\n\nRenewal Notes: ' + self.notes
        
        self.document_id.write(vals)
        return {'type': 'ir.actions.act_window_close'}
