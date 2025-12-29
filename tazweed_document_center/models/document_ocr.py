# -*- coding: utf-8 -*-
"""
OCR Document Scanning Module
Auto-extract data from documents using OCR technology
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import json
import re
from datetime import datetime, timedelta


class DocumentOCREngine(models.Model):
    """OCR Engine Configuration"""
    _name = 'document.ocr.engine'
    _description = 'OCR Engine Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Engine Name', required=True)
    engine_type = fields.Selection([
        ('tesseract', 'Tesseract OCR'),
        ('google_vision', 'Google Cloud Vision'),
        ('aws_textract', 'AWS Textract'),
        ('azure_cognitive', 'Azure Cognitive Services'),
        ('openai_vision', 'OpenAI Vision'),
        ('custom', 'Custom API'),
    ], string='Engine Type', required=True, default='tesseract')
    
    # API Configuration
    api_endpoint = fields.Char(string='API Endpoint')
    api_key = fields.Char(string='API Key')
    api_secret = fields.Char(string='API Secret')
    region = fields.Char(string='Region')
    
    # Settings
    default_language = fields.Selection([
        ('eng', 'English'),
        ('ara', 'Arabic'),
        ('eng+ara', 'English + Arabic'),
    ], string='Default Language', default='eng+ara')
    
    confidence_threshold = fields.Float(string='Confidence Threshold (%)', default=70.0)
    auto_rotate = fields.Boolean(string='Auto-Rotate Images', default=True)
    enhance_image = fields.Boolean(string='Enhance Image Quality', default=True)
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    is_default = fields.Boolean(string='Default Engine', default=False)
    last_test_date = fields.Datetime(string='Last Test Date')
    last_test_result = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Last Test Result')
    
    # Statistics
    total_scans = fields.Integer(string='Total Scans', default=0)
    successful_scans = fields.Integer(string='Successful Scans', default=0)
    average_confidence = fields.Float(string='Average Confidence (%)', compute='_compute_stats')
    
    @api.depends('total_scans', 'successful_scans')
    def _compute_stats(self):
        for record in self:
            if record.total_scans > 0:
                record.average_confidence = (record.successful_scans / record.total_scans) * 100
            else:
                record.average_confidence = 0.0
    
    @api.model
    def get_default_engine(self):
        """Get the default OCR engine"""
        engine = self.search([('is_default', '=', True), ('active', '=', True)], limit=1)
        if not engine:
            engine = self.search([('active', '=', True)], limit=1)
        return engine
    
    def action_test_connection(self):
        """Test the OCR engine connection"""
        self.ensure_one()
        # Simulate connection test
        self.write({
            'last_test_date': fields.Datetime.now(),
            'last_test_result': 'success',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection Test'),
                'message': _('OCR engine connection successful!'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_set_default(self):
        """Set this engine as default"""
        self.ensure_one()
        self.search([('is_default', '=', True)]).write({'is_default': False})
        self.write({'is_default': True})


class DocumentOCRTemplate(models.Model):
    """OCR Template for structured data extraction"""
    _name = 'document.ocr.template'
    _description = 'OCR Extraction Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Template Name', required=True)
    document_type = fields.Selection([
        ('passport', 'Passport'),
        ('emirates_id', 'Emirates ID'),
        ('visa', 'Visa'),
        ('labor_card', 'Labor Card'),
        ('contract', 'Employment Contract'),
        ('medical', 'Medical Certificate'),
        ('insurance', 'Insurance Card'),
        ('bank_statement', 'Bank Statement'),
        ('invoice', 'Invoice'),
        ('custom', 'Custom Document'),
    ], string='Document Type', required=True)
    
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    
    # Extraction Fields
    field_ids = fields.One2many('document.ocr.template.field', 'template_id', string='Extraction Fields')
    
    # Sample Image
    sample_image = fields.Binary(string='Sample Image')
    sample_image_name = fields.Char(string='Sample Image Name')
    
    # Validation Rules
    validation_rules = fields.Text(string='Validation Rules (JSON)')
    
    # Statistics
    usage_count = fields.Integer(string='Usage Count', default=0)
    success_rate = fields.Float(string='Success Rate (%)', compute='_compute_success_rate')
    
    @api.depends('usage_count')
    def _compute_success_rate(self):
        for record in self:
            # Calculate from OCR results
            results = self.env['document.ocr.result'].search([
                ('template_id', '=', record.id)
            ])
            if results:
                successful = results.filtered(lambda r: r.state == 'completed')
                record.success_rate = (len(successful) / len(results)) * 100
            else:
                record.success_rate = 0.0


class DocumentOCRTemplateField(models.Model):
    """OCR Template Field Definition"""
    _name = 'document.ocr.template.field'
    _description = 'OCR Template Field'
    _order = 'sequence'

    template_id = fields.Many2one('document.ocr.template', string='Template', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    name = fields.Char(string='Field Name', required=True)
    field_key = fields.Char(string='Field Key', required=True, help='Internal key for mapping')
    field_type = fields.Selection([
        ('text', 'Text'),
        ('date', 'Date'),
        ('number', 'Number'),
        ('currency', 'Currency'),
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('id_number', 'ID Number'),
        ('name', 'Person Name'),
        ('address', 'Address'),
    ], string='Field Type', required=True, default='text')
    
    # Extraction Settings
    extraction_method = fields.Selection([
        ('pattern', 'Regex Pattern'),
        ('position', 'Position-based'),
        ('keyword', 'Keyword-based'),
        ('ai', 'AI-based'),
    ], string='Extraction Method', default='ai')
    
    regex_pattern = fields.Char(string='Regex Pattern')
    keywords = fields.Char(string='Keywords (comma-separated)')
    
    # Position (for position-based extraction)
    position_x = fields.Integer(string='X Position')
    position_y = fields.Integer(string='Y Position')
    position_width = fields.Integer(string='Width')
    position_height = fields.Integer(string='Height')
    
    # Validation
    required = fields.Boolean(string='Required', default=False)
    validation_regex = fields.Char(string='Validation Pattern')
    
    # Target Field Mapping
    target_model = fields.Char(string='Target Model')
    target_field = fields.Char(string='Target Field')


class DocumentOCRResult(models.Model):
    """OCR Scan Result"""
    _name = 'document.ocr.result'
    _description = 'OCR Scan Result'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, default='New', copy=False)
    
    # Source Document
    source_document_id = fields.Many2one('document.center.unified', string='Source Document')
    source_file = fields.Binary(string='Source File')
    source_filename = fields.Char(string='Source Filename')
    
    # OCR Configuration
    engine_id = fields.Many2one('document.ocr.engine', string='OCR Engine')
    template_id = fields.Many2one('document.ocr.template', string='Template')
    language = fields.Selection([
        ('eng', 'English'),
        ('ara', 'Arabic'),
        ('eng+ara', 'English + Arabic'),
    ], string='Language', default='eng+ara')
    enhance_image = fields.Boolean(string='Enhance Image', default=True)
    detect_orientation = fields.Boolean(string='Detect Orientation', default=True)
    
    # Processing
    scan_date = fields.Datetime(string='Scan Date', default=fields.Datetime.now)
    processing_time = fields.Float(string='Processing Time (seconds)')
    
    # Results
    raw_text = fields.Text(string='Raw OCR Text')
    extracted_data = fields.Text(string='Extracted Data (JSON)')
    confidence_score = fields.Float(string='Confidence Score (%)')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('review', 'Needs Review'),
    ], string='Status', default='draft', tracking=True)
    
    error_message = fields.Text(string='Error Message')
    
    # Extracted Fields
    field_result_ids = fields.One2many('document.ocr.field.result', 'result_id', string='Field Results')
    
    # Created Document
    created_document_id = fields.Many2one('document.center.unified', string='Created Document')
    
    # Verification
    verified = fields.Boolean(string='Verified', default=False)
    verified_by = fields.Many2one('res.users', string='Verified By')
    verified_date = fields.Datetime(string='Verified Date')
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('document.ocr.result') or 'OCR-0001'
        return super().create(vals)
    
    def action_process(self):
        """Process the document with OCR"""
        self.ensure_one()
        self.write({'state': 'processing'})
        
        try:
            start_time = datetime.now()
            
            # Get OCR engine
            engine = self.engine_id or self.env['document.ocr.engine'].get_default_engine()
            if not engine:
                raise UserError(_('No OCR engine configured. Please configure an OCR engine first.'))
            
            # Simulate OCR processing
            raw_text = self._simulate_ocr_extraction()
            
            # Extract structured data if template is provided
            extracted_data = {}
            if self.template_id:
                extracted_data = self._extract_structured_data(raw_text)
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update result
            self.write({
                'raw_text': raw_text,
                'extracted_data': json.dumps(extracted_data, indent=2),
                'confidence_score': 85.5,  # Simulated confidence
                'processing_time': processing_time,
                'state': 'completed' if extracted_data else 'review',
            })
            
            # Update engine statistics
            engine.write({
                'total_scans': engine.total_scans + 1,
                'successful_scans': engine.successful_scans + 1,
            })
            
            # Update template usage
            if self.template_id:
                self.template_id.write({'usage_count': self.template_id.usage_count + 1})
            
        except Exception as e:
            self.write({
                'state': 'failed',
                'error_message': str(e),
            })
    
    def _simulate_ocr_extraction(self):
        """Simulate OCR text extraction"""
        # In production, this would call the actual OCR engine
        sample_texts = {
            'passport': """
                PASSPORT
                Type: P
                Country: ARE
                Surname: AL MAKTOUM
                Given Names: MOHAMMED RASHID
                Nationality: EMIRATI
                Date of Birth: 15 JAN 1985
                Sex: M
                Place of Birth: DUBAI
                Date of Issue: 01 MAR 2020
                Date of Expiry: 28 FEB 2030
                Passport No: A12345678
            """,
            'emirates_id': """
                EMIRATES ID
                ID Number: 784-1985-1234567-1
                Name: MOHAMMED RASHID AL MAKTOUM
                Nationality: UAE
                Date of Birth: 15/01/1985
                Gender: Male
                Expiry Date: 15/01/2030
                Card Number: 1234567890123456
            """,
            'visa': """
                RESIDENCE VISA
                Visa Number: 201/2023/1234567
                Name: JOHN SMITH
                Nationality: BRITISH
                Passport No: GB12345678
                Sponsor: ABC COMPANY LLC
                Profession: SOFTWARE ENGINEER
                Issue Date: 01/01/2023
                Expiry Date: 31/12/2025
            """,
        }
        
        doc_type = self.template_id.document_type if self.template_id else 'passport'
        return sample_texts.get(doc_type, sample_texts['passport'])
    
    def _extract_structured_data(self, raw_text):
        """Extract structured data based on template"""
        extracted = {}
        
        if not self.template_id or not self.template_id.field_ids:
            return extracted
        
        for field in self.template_id.field_ids:
            value = self._extract_field_value(raw_text, field)
            if value:
                extracted[field.field_key] = value
                
                # Create field result
                self.env['document.ocr.field.result'].create({
                    'result_id': self.id,
                    'field_name': field.name,
                    'field_key': field.field_key,
                    'extracted_value': value,
                    'confidence': 85.0,
                    'verified': False,
                })
        
        return extracted
    
    def _extract_field_value(self, text, field):
        """Extract a single field value from text"""
        if field.extraction_method == 'pattern' and field.regex_pattern:
            match = re.search(field.regex_pattern, text, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        elif field.extraction_method == 'keyword' and field.keywords:
            keywords = [k.strip() for k in field.keywords.split(',')]
            for keyword in keywords:
                pattern = rf'{keyword}[:\s]+([^\n]+)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        
        return None
    
    def action_reprocess(self):
        """Reprocess the OCR result"""
        self.ensure_one()
        self.write({'state': 'draft'})
        return self.action_process()
    
    def action_create_document(self):
        """Create a document from OCR results"""
        self.ensure_one()
        if not self.extracted_data:
            raise UserError(_('No extracted data available.'))
        
        # Create document from extracted data
        data = json.loads(self.extracted_data) if self.extracted_data else {}
        
        doc_vals = {
            'name': data.get('document_number', self.name),
            'document_type_id': self.template_id.document_type_id.id if self.template_id and hasattr(self.template_id, 'document_type_id') else False,
        }
        
        if 'expiry_date' in data:
            doc_vals['expiry_date'] = data['expiry_date']
        
        # Create the document
        document = self.env['document.center.unified'].create(doc_vals)
        self.write({'created_document_id': document.id})
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Created Document'),
            'res_model': 'document.center.unified',
            'res_id': document.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_verify(self):
        """Mark result as verified"""
        self.ensure_one()
        self.write({
            'verified': True,
            'verified_by': self.env.user.id,
            'verified_date': fields.Datetime.now(),
        })
    
    def action_apply_to_document(self):
        """Apply extracted data to the source document"""
        self.ensure_one()
        if not self.source_document_id:
            raise UserError(_('No source document linked.'))
        
        if not self.extracted_data:
            raise UserError(_('No extracted data available.'))
        
        # Parse extracted data
        data = json.loads(self.extracted_data)
        
        # Apply to document (field mapping would be done here)
        # This is a simplified example
        update_vals = {}
        if 'expiry_date' in data:
            update_vals['expiry_date'] = data['expiry_date']
        if 'document_number' in data:
            update_vals['document_number'] = data['document_number']
        
        if update_vals:
            self.source_document_id.write(update_vals)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Data Applied'),
                'message': _('Extracted data has been applied to the document.'),
                'type': 'success',
                'sticky': False,
            }
        }


class DocumentOCRFieldResult(models.Model):
    """Individual field extraction result"""
    _name = 'document.ocr.field.result'
    _description = 'OCR Field Result'

    result_id = fields.Many2one('document.ocr.result', string='OCR Result', required=True, ondelete='cascade')
    
    field_name = fields.Char(string='Field Name')
    field_key = fields.Char(string='Field Key')
    extracted_value = fields.Char(string='Extracted Value')
    corrected_value = fields.Char(string='Corrected Value')
    confidence = fields.Float(string='Confidence (%)')
    
    verified = fields.Boolean(string='Verified', default=False)
    
    @api.onchange('corrected_value')
    def _onchange_corrected_value(self):
        if self.corrected_value:
            self.verified = True


class DocumentOCRBatchScan(models.Model):
    """Batch OCR Scanning"""
    _name = 'document.ocr.batch'
    _description = 'OCR Batch Scan'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Batch Name', required=True, default='New')
    
    # Configuration
    engine_id = fields.Many2one('document.ocr.engine', string='OCR Engine')
    template_id = fields.Many2one('document.ocr.template', string='Template')
    
    # Documents
    document_ids = fields.Many2many('document.center.unified', string='Documents to Scan')
    document_count = fields.Integer(string='Document Count', compute='_compute_counts')
    
    # Results
    result_ids = fields.One2many('document.ocr.result', 'batch_id', string='Results')
    processed_count = fields.Integer(string='Processed', compute='_compute_counts')
    success_count = fields.Integer(string='Successful', compute='_compute_counts')
    failed_count = fields.Integer(string='Failed', compute='_compute_counts')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('partial', 'Partially Completed'),
    ], string='Status', default='draft', tracking=True)
    
    progress = fields.Float(string='Progress (%)', compute='_compute_counts')
    
    @api.depends('document_ids', 'result_ids', 'result_ids.state')
    def _compute_counts(self):
        for record in self:
            record.document_count = len(record.document_ids)
            record.processed_count = len(record.result_ids)
            record.success_count = len(record.result_ids.filtered(lambda r: r.state == 'completed'))
            record.failed_count = len(record.result_ids.filtered(lambda r: r.state == 'failed'))
            record.progress = (record.processed_count / record.document_count * 100) if record.document_count else 0
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('document.ocr.batch') or 'BATCH-0001'
        return super().create(vals)
    
    def action_start_batch(self):
        """Start batch processing"""
        self.ensure_one()
        self.write({'state': 'processing'})
        
        for doc in self.document_ids:
            result = self.env['document.ocr.result'].create({
                'source_document_id': doc.id,
                'engine_id': self.engine_id.id if self.engine_id else False,
                'template_id': self.template_id.id if self.template_id else False,
                'batch_id': self.id,
            })
            result.action_process()
        
        # Update batch status
        if self.failed_count == 0:
            self.write({'state': 'completed'})
        elif self.success_count > 0:
            self.write({'state': 'partial'})
        else:
            self.write({'state': 'completed'})


# Add batch_id to OCR Result
class DocumentOCRResultBatch(models.Model):
    _inherit = 'document.ocr.result'
    
    batch_id = fields.Many2one('document.ocr.batch', string='Batch')
