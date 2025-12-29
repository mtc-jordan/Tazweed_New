# -*- coding: utf-8 -*-
"""
Bulk Document Upload Module
Upload multiple documents at once with batch processing
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import zipfile
import io
import os
from datetime import datetime


class DocumentBulkUpload(models.Model):
    """Bulk Document Upload Session"""
    _name = 'document.bulk.upload'
    _description = 'Bulk Document Upload'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Upload Session', required=True, default='New', copy=False)
    
    # Upload Configuration
    upload_type = fields.Selection([
        ('employee', 'Employee Documents'),
        ('client', 'Client Documents'),
        ('general', 'General Documents'),
        ('mixed', 'Mixed Documents'),
    ], string='Upload Type', required=True, default='employee')
    
    # Target
    employee_id = fields.Many2one('hr.employee', string='Employee')
    client_id = fields.Many2one('tazweed.client', string='Client')
    department_id = fields.Many2one('hr.department', string='Department')
    
    # Document Type
    document_type_id = fields.Many2one('tazweed.document.type', string='Document Type')
    auto_detect_type = fields.Boolean(string='Auto-Detect Document Type', default=True)
    
    # Upload Source
    source_type = fields.Selection([
        ('files', 'Individual Files'),
        ('zip', 'ZIP Archive'),
        ('folder', 'Folder Structure'),
    ], string='Source Type', default='files')
    
    # ZIP Upload
    zip_file = fields.Binary(string='ZIP File')
    zip_filename = fields.Char(string='ZIP Filename')
    
    # Files
    upload_line_ids = fields.One2many('document.bulk.upload.line', 'upload_id', string='Files')
    
    # Processing
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validating', 'Validating'),
        ('ready', 'Ready to Process'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('partial', 'Partially Completed'),
        ('failed', 'Failed'),
    ], string='Status', default='draft', tracking=True)
    
    # Statistics
    total_files = fields.Integer(string='Total Files', compute='_compute_stats')
    pending_files = fields.Integer(string='Pending', compute='_compute_stats')
    processed_files = fields.Integer(string='Processed', compute='_compute_stats')
    failed_files = fields.Integer(string='Failed', compute='_compute_stats')
    progress = fields.Float(string='Progress (%)', compute='_compute_stats')
    
    # Created Documents
    document_ids = fields.Many2many('document.center.unified', string='Created Documents')
    document_count = fields.Integer(string='Documents Created', compute='_compute_document_count')
    
    # Settings
    skip_duplicates = fields.Boolean(string='Skip Duplicates', default=True)
    overwrite_existing = fields.Boolean(string='Overwrite Existing', default=False)
    send_notifications = fields.Boolean(string='Send Notifications', default=False)
    run_ocr = fields.Boolean(string='Run OCR Processing', default=False)
    
    # Notes
    notes = fields.Text(string='Notes')
    error_log = fields.Text(string='Error Log')
    
    @api.depends('upload_line_ids', 'upload_line_ids.state')
    def _compute_stats(self):
        for record in self:
            lines = record.upload_line_ids
            record.total_files = len(lines)
            record.pending_files = len(lines.filtered(lambda l: l.state == 'pending'))
            record.processed_files = len(lines.filtered(lambda l: l.state == 'completed'))
            record.failed_files = len(lines.filtered(lambda l: l.state == 'failed'))
            record.progress = (record.processed_files / record.total_files * 100) if record.total_files else 0
    
    @api.depends('document_ids')
    def _compute_document_count(self):
        for record in self:
            record.document_count = len(record.document_ids)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('document.bulk.upload') or 'BULK-0001'
        return super().create(vals)
    
    @api.onchange('zip_file')
    def _onchange_zip_file(self):
        """Extract files from ZIP when uploaded"""
        if self.zip_file and self.source_type == 'zip':
            self._extract_zip_contents()
    
    def _extract_zip_contents(self):
        """Extract contents from ZIP file"""
        if not self.zip_file:
            return
        
        try:
            zip_data = base64.b64decode(self.zip_file)
            zip_buffer = io.BytesIO(zip_data)
            
            with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                # Clear existing lines
                self.upload_line_ids.unlink()
                
                for file_info in zip_ref.infolist():
                    # Skip directories
                    if file_info.is_dir():
                        continue
                    
                    # Skip hidden files
                    filename = os.path.basename(file_info.filename)
                    if filename.startswith('.'):
                        continue
                    
                    # Read file content
                    file_content = zip_ref.read(file_info.filename)
                    
                    # Create upload line
                    self.env['document.bulk.upload.line'].create({
                        'upload_id': self.id,
                        'filename': filename,
                        'file_content': base64.b64encode(file_content),
                        'file_size': len(file_content),
                        'file_path': file_info.filename,
                    })
        
        except zipfile.BadZipFile:
            raise UserError(_('Invalid ZIP file. Please upload a valid ZIP archive.'))
    
    def action_validate(self):
        """Validate all uploaded files"""
        self.ensure_one()
        self.write({'state': 'validating'})
        
        errors = []
        for line in self.upload_line_ids:
            try:
                line.action_validate()
            except Exception as e:
                errors.append(f"{line.filename}: {str(e)}")
        
        if errors:
            self.write({
                'error_log': '\n'.join(errors),
                'state': 'ready' if self.pending_files > 0 else 'failed',
            })
        else:
            self.write({'state': 'ready'})
    
    def action_process(self):
        """Process all validated files"""
        self.ensure_one()
        
        if self.state not in ['ready', 'partial']:
            raise UserError(_('Please validate files before processing.'))
        
        self.write({'state': 'processing'})
        
        created_docs = []
        errors = []
        
        for line in self.upload_line_ids.filtered(lambda l: l.state == 'pending'):
            try:
                doc = line.action_create_document()
                if doc:
                    created_docs.append(doc.id)
            except Exception as e:
                errors.append(f"{line.filename}: {str(e)}")
                line.write({
                    'state': 'failed',
                    'error_message': str(e),
                })
        
        # Update session
        self.write({
            'document_ids': [(6, 0, created_docs)],
            'error_log': '\n'.join(errors) if errors else False,
        })
        
        # Determine final state
        if self.failed_files == 0:
            self.write({'state': 'completed'})
        elif self.processed_files > 0:
            self.write({'state': 'partial'})
        else:
            self.write({'state': 'failed'})
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Upload Complete'),
                'message': _('%d documents created, %d failed') % (len(created_docs), len(errors)),
                'type': 'success' if not errors else 'warning',
                'sticky': False,
            }
        }
    
    def action_view_documents(self):
        """View created documents"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Documents'),
            'res_model': 'document.center.unified',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.document_ids.ids)],
        }
    
    def action_reset(self):
        """Reset upload session"""
        self.ensure_one()
        self.upload_line_ids.write({'state': 'pending', 'error_message': False})
        self.write({
            'state': 'draft',
            'error_log': False,
            'document_ids': [(5, 0, 0)],
        })


class DocumentBulkUploadLine(models.Model):
    """Individual file in bulk upload"""
    _name = 'document.bulk.upload.line'
    _description = 'Bulk Upload File'
    _order = 'sequence, id'

    upload_id = fields.Many2one('document.bulk.upload', string='Upload Session', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    # File Info
    filename = fields.Char(string='Filename', required=True)
    file_content = fields.Binary(string='File Content', attachment=True)
    file_size = fields.Integer(string='File Size (bytes)')
    file_path = fields.Char(string='Original Path')
    mime_type = fields.Char(string='MIME Type')
    
    # Document Mapping
    document_type_id = fields.Many2one('tazweed.document.type', string='Document Type')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    client_id = fields.Many2one('tazweed.client', string='Client')
    
    # Auto-detected Info
    detected_type = fields.Char(string='Detected Type')
    detected_employee = fields.Char(string='Detected Employee')
    
    # Expiry
    expiry_date = fields.Date(string='Expiry Date')
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('validated', 'Validated'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')
    
    error_message = fields.Text(string='Error Message')
    
    # Created Document
    document_id = fields.Many2one('document.center.unified', string='Created Document')
    
    def action_validate(self):
        """Validate this file"""
        self.ensure_one()
        
        # Check file exists
        if not self.file_content:
            raise ValidationError(_('No file content found.'))
        
        # Check file size (max 50MB)
        if self.file_size > 50 * 1024 * 1024:
            raise ValidationError(_('File size exceeds maximum limit of 50MB.'))
        
        # Detect MIME type from filename
        ext = os.path.splitext(self.filename)[1].lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }
        self.mime_type = mime_types.get(ext, 'application/octet-stream')
        
        # Auto-detect document type if enabled
        if self.upload_id.auto_detect_type and not self.document_type_id:
            self._auto_detect_document_type()
        
        # Use parent's document type if not detected
        if not self.document_type_id and self.upload_id.document_type_id:
            self.document_type_id = self.upload_id.document_type_id
        
        # Use parent's employee/client if not set
        if not self.employee_id and self.upload_id.employee_id:
            self.employee_id = self.upload_id.employee_id
        if not self.client_id and self.upload_id.client_id:
            self.client_id = self.upload_id.client_id
        
        self.write({'state': 'validated'})
    
    def _auto_detect_document_type(self):
        """Auto-detect document type from filename"""
        filename_lower = self.filename.lower()
        
        # Document type detection patterns
        patterns = {
            'passport': ['passport', 'جواز'],
            'emirates_id': ['emirates', 'eid', 'id card', 'هوية'],
            'visa': ['visa', 'تأشيرة'],
            'labor_card': ['labor', 'labour', 'work permit', 'عمل'],
            'contract': ['contract', 'agreement', 'عقد'],
            'medical': ['medical', 'health', 'طبي'],
            'insurance': ['insurance', 'تأمين'],
        }
        
        for doc_type, keywords in patterns.items():
            for keyword in keywords:
                if keyword in filename_lower:
                    # Find matching document type
                    doc_type_record = self.env['tazweed.document.type'].search([
                        ('name', 'ilike', doc_type)
                    ], limit=1)
                    if doc_type_record:
                        self.document_type_id = doc_type_record
                        self.detected_type = doc_type
                        return
    
    def action_create_document(self):
        """Create document from this upload line"""
        self.ensure_one()
        
        if self.state == 'completed':
            return self.document_id
        
        if not self.document_type_id:
            raise UserError(_('Document type is required.'))
        
        # Check for duplicates
        if self.upload_id.skip_duplicates:
            existing = self.env['document.center.unified'].search([
                ('attachment_name', '=', self.filename),
                ('document_type_id', '=', self.document_type_id.id),
            ], limit=1)
            
            if existing and not self.upload_id.overwrite_existing:
                self.write({'state': 'skipped', 'error_message': 'Duplicate document'})
                return None
        
        # Create document
        doc_vals = {
            'name': os.path.splitext(self.filename)[0],
            'document_type_id': self.document_type_id.id,
            'attachment': self.file_content,
            'attachment_name': self.filename,
            'state': 'active',
        }
        
        if self.employee_id:
            doc_vals['employee_id'] = self.employee_id.id
        if self.client_id:
            doc_vals['client_id'] = self.client_id.id
        if self.expiry_date:
            doc_vals['expiry_date'] = self.expiry_date
        
        document = self.env['document.center.unified'].create(doc_vals)
        
        # Run OCR if enabled
        if self.upload_id.run_ocr:
            try:
                ocr_result = self.env['document.ocr.result'].create({
                    'source_document_id': document.id,
                    'source_file': self.file_content,
                    'source_filename': self.filename,
                })
                ocr_result.action_process()
            except Exception:
                pass  # OCR failure shouldn't block document creation
        
        self.write({
            'state': 'completed',
            'document_id': document.id,
        })
        
        return document


class DocumentBulkUploadWizard(models.TransientModel):
    """Quick bulk upload wizard"""
    _name = 'document.bulk.upload.wizard'
    _description = 'Bulk Upload Wizard'

    upload_type = fields.Selection([
        ('employee', 'Employee Documents'),
        ('client', 'Client Documents'),
        ('general', 'General Documents'),
    ], string='Upload Type', required=True, default='employee')
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
    client_id = fields.Many2one('tazweed.client', string='Client')
    document_type_id = fields.Many2one('tazweed.document.type', string='Document Type')
    
    file_ids = fields.Many2many('ir.attachment', string='Files')
    
    auto_detect_type = fields.Boolean(string='Auto-Detect Document Type', default=True)
    run_ocr = fields.Boolean(string='Run OCR Processing', default=False)
    
    def action_upload(self):
        """Create bulk upload session and process"""
        self.ensure_one()
        
        # Create upload session
        upload = self.env['document.bulk.upload'].create({
            'upload_type': self.upload_type,
            'employee_id': self.employee_id.id if self.employee_id else False,
            'client_id': self.client_id.id if self.client_id else False,
            'document_type_id': self.document_type_id.id if self.document_type_id else False,
            'auto_detect_type': self.auto_detect_type,
            'run_ocr': self.run_ocr,
            'source_type': 'files',
        })
        
        # Create upload lines from attachments
        for attachment in self.file_ids:
            self.env['document.bulk.upload.line'].create({
                'upload_id': upload.id,
                'filename': attachment.name,
                'file_content': attachment.datas,
                'file_size': attachment.file_size,
            })
        
        # Validate and process
        upload.action_validate()
        if upload.state == 'ready':
            upload.action_process()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bulk Upload'),
            'res_model': 'document.bulk.upload',
            'res_id': upload.id,
            'view_mode': 'form',
            'target': 'current',
        }
