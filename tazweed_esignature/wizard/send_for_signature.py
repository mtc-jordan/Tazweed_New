# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SendForSignatureWizard(models.TransientModel):
    """Wizard to send documents for signature."""
    _name = 'send.for.signature.wizard'
    _description = 'Send for Signature Wizard'

    document_name = fields.Char(string='Document Name', required=True)
    document_type = fields.Selection([
        ('contract', 'Employment Contract'),
        ('offer', 'Offer Letter'),
        ('nda', 'Non-Disclosure Agreement'),
        ('policy', 'Policy Acknowledgment'),
        ('termination', 'Termination Letter'),
        ('amendment', 'Contract Amendment'),
        ('other', 'Other Document'),
    ], string='Document Type', default='contract', required=True)
    
    document_file = fields.Binary(string='Document', required=True)
    document_filename = fields.Char(string='Filename')
    
    template_id = fields.Many2one('signature.template', string='Template')
    
    signer_name = fields.Char(string='Signer Name', required=True)
    signer_email = fields.Char(string='Signer Email', required=True)
    signer_role = fields.Selection([
        ('employee', 'Employee'),
        ('manager', 'Manager'),
        ('hr', 'HR Representative'),
        ('client', 'Client'),
        ('witness', 'Witness'),
        ('other', 'Other'),
    ], string='Role', default='employee')
    
    expiry_date = fields.Date(string='Expiry Date')
    message = fields.Text(string='Message to Signer')

    def action_send(self):
        """Create signature request and send for signature."""
        self.ensure_one()
        
        request = self.env['signature.request'].create({
            'document_name': self.document_name,
            'document_type': self.document_type,
            'document_file': self.document_file,
            'document_filename': self.document_filename,
            'template_id': self.template_id.id if self.template_id else False,
            'expiry_date': self.expiry_date,
        })
        
        self.env['signature.signer'].create({
            'request_id': request.id,
            'name': self.signer_name,
            'email': self.signer_email,
            'role': self.signer_role,
        })
        
        request.action_send_for_signature()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature Request'),
            'res_model': 'signature.request',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }
