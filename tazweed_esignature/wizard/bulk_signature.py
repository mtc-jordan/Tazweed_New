# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BulkSignatureWizard(models.TransientModel):
    """Wizard for sending multiple documents for signature at once."""
    _name = 'bulk.signature.wizard'
    _description = 'Bulk Signature Wizard'

    document_type = fields.Selection([
        ('contract', 'Employment Contract'),
        ('offer', 'Offer Letter'),
        ('nda', 'Non-Disclosure Agreement'),
        ('policy', 'Policy Acknowledgment'),
        ('other', 'Other Document'),
    ], string='Document Type', required=True, default='policy')
    
    document_type_id = fields.Many2one(
        'signature.document.type',
        string='Document Category'
    )
    
    template_id = fields.Many2one(
        'signature.template',
        string='Template'
    )
    
    document_file = fields.Binary(
        string='Document',
        required=True
    )
    document_filename = fields.Char(string='Filename')
    
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        required=True
    )
    
    signing_order = fields.Selection([
        ('parallel', 'All at Once'),
        ('sequential', 'In Order'),
    ], string='Signing Order', default='parallel')
    
    expiry_days = fields.Integer(
        string='Expiry (Days)',
        default=14
    )
    
    reminder_enabled = fields.Boolean(
        string='Enable Reminders',
        default=True
    )
    
    include_manager = fields.Boolean(
        string='Include Manager as Signer',
        default=False
    )
    
    include_hr = fields.Boolean(
        string='Include HR as Signer',
        default=False
    )

    @api.onchange('document_type_id')
    def _onchange_document_type_id(self):
        """Update defaults from document type."""
        if self.document_type_id:
            self.expiry_days = self.document_type_id.default_expiry_days
            if self.document_type_id.default_template_id:
                self.template_id = self.document_type_id.default_template_id

    def action_create_requests(self):
        """Create signature requests for all selected employees."""
        self.ensure_one()
        
        if not self.employee_ids:
            raise UserError(_('Please select at least one employee.'))
        if not self.document_file:
            raise UserError(_('Please attach a document.'))
        
        created_requests = self.env['signature.request']
        
        for employee in self.employee_ids:
            # Create signature request
            request_vals = {
                'document_name': f"{self.document_filename or 'Document'} - {employee.name}",
                'document_type': self.document_type,
                'document_type_id': self.document_type_id.id if self.document_type_id else False,
                'template_id': self.template_id.id if self.template_id else False,
                'document_file': self.document_file,
                'document_filename': self.document_filename,
                'employee_id': employee.id,
                'signing_order': self.signing_order,
                'expiry_date': fields.Date.add(fields.Date.today(), days=self.expiry_days),
                'reminder_enabled': self.reminder_enabled,
            }
            
            request = self.env['signature.request'].create(request_vals)
            
            # Add employee as signer
            signer_sequence = 1
            self.env['signature.signer'].create({
                'request_id': request.id,
                'name': employee.name,
                'email': employee.work_email or employee.private_email,
                'phone': employee.mobile_phone or employee.phone,
                'role': 'employee',
                'sequence': signer_sequence,
            })
            signer_sequence += 1
            
            # Add manager if requested
            if self.include_manager and employee.parent_id:
                self.env['signature.signer'].create({
                    'request_id': request.id,
                    'name': employee.parent_id.name,
                    'email': employee.parent_id.work_email,
                    'role': 'manager',
                    'sequence': signer_sequence,
                })
                signer_sequence += 1
            
            # Add HR if requested
            if self.include_hr:
                hr_user = self.env.ref('hr.group_hr_manager', raise_if_not_found=False)
                if hr_user:
                    hr_employees = self.env['hr.employee'].search([
                        ('user_id.groups_id', 'in', hr_user.id)
                    ], limit=1)
                    if hr_employees:
                        self.env['signature.signer'].create({
                            'request_id': request.id,
                            'name': hr_employees.name,
                            'email': hr_employees.work_email,
                            'role': 'hr',
                            'sequence': signer_sequence,
                        })
            
            created_requests |= request
        
        # Return action to view created requests
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Signature Requests'),
            'res_model': 'signature.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_requests.ids)],
            'context': {'create': False},
        }

    def action_create_and_send(self):
        """Create signature requests and send them immediately."""
        self.ensure_one()
        
        result = self.action_create_requests()
        
        # Send all created requests
        request_ids = result.get('domain', [[]])[0][2] if result.get('domain') else []
        requests = self.env['signature.request'].browse(request_ids)
        
        for request in requests:
            try:
                request.action_send_for_signature()
            except Exception:
                pass  # Continue even if one fails
        
        return result
