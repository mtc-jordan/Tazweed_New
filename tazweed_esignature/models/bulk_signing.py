# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import secrets
from datetime import datetime, timedelta


class BulkSigningBatch(models.Model):
    """Bulk Signing Batch - Manage multiple signature requests at once"""
    _name = 'bulk.signing.batch'
    _description = 'Bulk Signing Batch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Batch Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    description = fields.Text(string='Description')
    
    # Batch Configuration
    batch_type = fields.Selection([
        ('same_document', 'Same Document to Multiple Signers'),
        ('different_documents', 'Different Documents'),
        ('template_based', 'Template-Based Generation'),
    ], string='Batch Type', required=True, default='same_document')
    
    # Template for template-based batches
    template_id = fields.Many2one(
        'signature.template',
        string='Document Template',
        help='Template to use for generating documents'
    )
    
    # Master Document (for same_document type)
    master_document = fields.Binary(
        string='Master Document',
        attachment=True
    )
    master_filename = fields.Char(string='Master Filename')
    
    # Document Type
    document_type = fields.Selection([
        ('contract', 'Employment Contract'),
        ('offer', 'Offer Letter'),
        ('nda', 'Non-Disclosure Agreement'),
        ('policy', 'Policy Acknowledgment'),
        ('termination', 'Termination Letter'),
        ('amendment', 'Contract Amendment'),
        ('other', 'Other Document'),
    ], string='Document Type', default='contract', required=True)
    
    # Batch Items
    item_ids = fields.One2many(
        'bulk.signing.item',
        'batch_id',
        string='Batch Items'
    )
    
    # Signer Source
    signer_source = fields.Selection([
        ('manual', 'Manual Selection'),
        ('employee_list', 'Employee List'),
        ('department', 'By Department'),
        ('csv_import', 'CSV Import'),
    ], string='Signer Source', default='manual')
    
    # Employee Selection
    employee_ids = fields.Many2many(
        'hr.employee',
        'bulk_signing_employee_rel',
        'batch_id',
        'employee_id',
        string='Employees'
    )
    department_ids = fields.Many2many(
        'hr.department',
        'bulk_signing_department_rel',
        'batch_id',
        'department_id',
        string='Departments'
    )
    
    # Signing Configuration
    signing_order = fields.Selection([
        ('parallel', 'All at Once'),
        ('sequential', 'In Order'),
    ], string='Signing Order', default='parallel')
    
    expiry_days = fields.Integer(
        string='Expiry Days',
        default=30,
        help='Number of days until signature requests expire'
    )
    
    reminder_enabled = fields.Boolean(
        string='Enable Reminders',
        default=True
    )
    reminder_days = fields.Integer(
        string='Reminder After (Days)',
        default=3
    )
    
    # Additional Signers (e.g., HR Manager, Department Head)
    additional_signer_ids = fields.Many2many(
        'res.users',
        'bulk_signing_additional_signers_rel',
        'batch_id',
        'user_id',
        string='Additional Signers',
        help='Additional signers to be added to all requests (e.g., HR Manager)'
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('processing', 'Processing'),
        ('sent', 'Sent'),
        ('partially_completed', 'Partially Completed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Statistics
    total_count = fields.Integer(
        string='Total Requests',
        compute='_compute_statistics',
        store=True
    )
    sent_count = fields.Integer(
        string='Sent',
        compute='_compute_statistics',
        store=True
    )
    signed_count = fields.Integer(
        string='Signed',
        compute='_compute_statistics',
        store=True
    )
    pending_count = fields.Integer(
        string='Pending',
        compute='_compute_statistics',
        store=True
    )
    failed_count = fields.Integer(
        string='Failed',
        compute='_compute_statistics',
        store=True
    )
    progress = fields.Float(
        string='Progress (%)',
        compute='_compute_statistics',
        store=True
    )
    
    # Dates
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True
    )
    sent_date = fields.Datetime(
        string='Sent Date',
        readonly=True
    )
    completed_date = fields.Datetime(
        string='Completed Date',
        readonly=True
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    # Created By
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('bulk.signing.batch') or _('New')
        return super().create(vals_list)

    @api.depends('item_ids', 'item_ids.state')
    def _compute_statistics(self):
        """Compute batch statistics"""
        for batch in self:
            items = batch.item_ids
            batch.total_count = len(items)
            batch.sent_count = len(items.filtered(lambda i: i.state in ('sent', 'partially_signed', 'signed')))
            batch.signed_count = len(items.filtered(lambda i: i.state == 'signed'))
            batch.pending_count = len(items.filtered(lambda i: i.state in ('draft', 'sent', 'partially_signed')))
            batch.failed_count = len(items.filtered(lambda i: i.state == 'failed'))
            batch.progress = (batch.signed_count / batch.total_count * 100) if batch.total_count > 0 else 0

    def action_generate_items(self):
        """Generate batch items based on configuration"""
        self.ensure_one()
        
        if self.signer_source == 'employee_list':
            employees = self.employee_ids
        elif self.signer_source == 'department':
            employees = self.env['hr.employee'].search([
                ('department_id', 'in', self.department_ids.ids)
            ])
        else:
            employees = self.env['hr.employee']
        
        # Clear existing items
        self.item_ids.unlink()
        
        # Create items for each employee
        for employee in employees:
            self.env['bulk.signing.item'].create({
                'batch_id': self.id,
                'employee_id': employee.id,
                'signer_name': employee.name,
                'signer_email': employee.work_email,
                'document_name': f"{self.document_type} - {employee.name}",
            })
        
        self.write({'state': 'ready'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Items Generated'),
                'message': _('%d items generated successfully.') % len(employees),
                'type': 'success',
            }
        }

    def action_send_all(self):
        """Send all signature requests in the batch"""
        self.ensure_one()
        
        if not self.item_ids:
            raise UserError(_('No items in this batch. Please generate items first.'))
        
        self.write({
            'state': 'processing',
            'sent_date': fields.Datetime.now()
        })
        
        success_count = 0
        error_count = 0
        
        for item in self.item_ids.filtered(lambda i: i.state == 'draft'):
            try:
                item.action_create_and_send()
                success_count += 1
            except Exception as e:
                item.write({
                    'state': 'failed',
                    'error_message': str(e)
                })
                error_count += 1
        
        # Update batch state
        if error_count == 0:
            self.write({'state': 'sent'})
        else:
            self.write({'state': 'partially_completed'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Batch Sent'),
                'message': _('%d sent successfully, %d failed.') % (success_count, error_count),
                'type': 'success' if error_count == 0 else 'warning',
            }
        }

    def action_cancel(self):
        """Cancel the batch and all pending requests"""
        self.ensure_one()
        
        for item in self.item_ids:
            if item.signature_request_id and item.signature_request_id.state not in ('signed', 'cancelled'):
                item.signature_request_id.action_cancel()
            item.write({'state': 'cancelled'})
        
        self.write({'state': 'cancelled'})

    def action_send_reminders(self):
        """Send reminders for all pending items"""
        self.ensure_one()
        
        reminder_count = 0
        for item in self.item_ids.filtered(lambda i: i.state in ('sent', 'partially_signed')):
            if item.signature_request_id:
                item.signature_request_id.action_send_reminder()
                reminder_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reminders Sent'),
                'message': _('%d reminders sent.') % reminder_count,
                'type': 'success',
            }
        }

    def action_view_requests(self):
        """View all signature requests in this batch"""
        self.ensure_one()
        request_ids = self.item_ids.mapped('signature_request_id').ids
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature Requests'),
            'res_model': 'signature.request',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', request_ids)],
        }


class BulkSigningItem(models.Model):
    """Bulk Signing Item - Individual item in a bulk signing batch"""
    _name = 'bulk.signing.item'
    _description = 'Bulk Signing Item'
    _order = 'sequence, id'

    batch_id = fields.Many2one(
        'bulk.signing.batch',
        string='Batch',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Signer Information
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        ondelete='set null'
    )
    signer_name = fields.Char(string='Signer Name', required=True)
    signer_email = fields.Char(string='Signer Email', required=True)
    signer_phone = fields.Char(string='Signer Phone')
    
    # Document
    document_name = fields.Char(string='Document Name')
    document_file = fields.Binary(
        string='Document',
        attachment=True,
        help='Leave empty to use master document from batch'
    )
    document_filename = fields.Char(string='Document Filename')
    
    # Custom Data (for template-based generation)
    custom_data = fields.Text(
        string='Custom Data (JSON)',
        help='JSON data for template placeholders'
    )
    
    # Generated Request
    signature_request_id = fields.Many2one(
        'signature.request',
        string='Signature Request',
        readonly=True
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('partially_signed', 'Partially Signed'),
        ('signed', 'Signed'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    
    # Error Message
    error_message = fields.Text(string='Error Message', readonly=True)
    
    # Dates
    sent_date = fields.Datetime(string='Sent Date', readonly=True)
    signed_date = fields.Datetime(string='Signed Date', readonly=True)

    def action_create_and_send(self):
        """Create signature request and send for signing"""
        self.ensure_one()
        batch = self.batch_id
        
        # Determine document to use
        document = self.document_file or batch.master_document
        filename = self.document_filename or batch.master_filename or 'document.pdf'
        
        if not document:
            raise UserError(_('No document available for this item.'))
        
        # Create signature request
        request_vals = {
            'document_name': self.document_name or f"{batch.document_type} - {self.signer_name}",
            'document_type': batch.document_type,
            'document_file': document,
            'document_filename': filename,
            'employee_id': self.employee_id.id if self.employee_id else False,
            'signing_order': batch.signing_order,
            'expiry_date': fields.Date.today() + timedelta(days=batch.expiry_days),
            'reminder_enabled': batch.reminder_enabled,
            'reminder_days': batch.reminder_days,
        }
        
        request = self.env['signature.request'].create(request_vals)
        
        # Add primary signer
        self.env['signature.signer'].create({
            'request_id': request.id,
            'name': self.signer_name,
            'email': self.signer_email,
            'phone': self.signer_phone,
            'role': 'signer',
            'sequence': 1,
        })
        
        # Add additional signers from batch
        sequence = 2
        for user in batch.additional_signer_ids:
            self.env['signature.signer'].create({
                'request_id': request.id,
                'name': user.name,
                'email': user.email,
                'user_id': user.id,
                'role': 'approver',
                'sequence': sequence,
            })
            sequence += 1
        
        # Send for signature
        request.action_send_for_signature()
        
        # Update item
        self.write({
            'signature_request_id': request.id,
            'state': 'sent',
            'sent_date': fields.Datetime.now(),
        })
        
        return request

    def action_view_request(self):
        """View the signature request"""
        self.ensure_one()
        if not self.signature_request_id:
            raise UserError(_('No signature request created yet.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature Request'),
            'res_model': 'signature.request',
            'view_mode': 'form',
            'res_id': self.signature_request_id.id,
        }


class BulkSigningImportWizard(models.TransientModel):
    """Wizard for importing signers from CSV"""
    _name = 'bulk.signing.import.wizard'
    _description = 'Bulk Signing Import Wizard'

    batch_id = fields.Many2one(
        'bulk.signing.batch',
        string='Batch',
        required=True
    )
    csv_file = fields.Binary(
        string='CSV File',
        required=True
    )
    csv_filename = fields.Char(string='CSV Filename')
    
    # Column Mapping
    name_column = fields.Char(string='Name Column', default='name')
    email_column = fields.Char(string='Email Column', default='email')
    phone_column = fields.Char(string='Phone Column', default='phone')
    
    has_header = fields.Boolean(string='Has Header Row', default=True)
    delimiter = fields.Char(string='Delimiter', default=',')

    def action_import(self):
        """Import signers from CSV"""
        self.ensure_one()
        import csv
        import io
        
        # Decode CSV file
        csv_data = base64.b64decode(self.csv_file).decode('utf-8')
        reader = csv.DictReader(io.StringIO(csv_data), delimiter=self.delimiter)
        
        created_count = 0
        for row in reader:
            name = row.get(self.name_column, '')
            email = row.get(self.email_column, '')
            phone = row.get(self.phone_column, '')
            
            if name and email:
                self.env['bulk.signing.item'].create({
                    'batch_id': self.batch_id.id,
                    'signer_name': name,
                    'signer_email': email,
                    'signer_phone': phone,
                    'document_name': f"{self.batch_id.document_type} - {name}",
                })
                created_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Complete'),
                'message': _('%d signers imported successfully.') % created_count,
                'type': 'success',
            }
        }
