# -*- coding: utf-8 -*-
"""
Document Templates Module
Pre-defined document templates for quick document creation
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
from datetime import datetime, timedelta


class DocumentTemplate(models.Model):
    """Document Template"""
    _name = 'document.template'
    _description = 'Document Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True)
    code = fields.Char(string='Template Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Category
    category = fields.Selection([
        ('hr', 'HR Documents'),
        ('legal', 'Legal Documents'),
        ('financial', 'Financial Documents'),
        ('operational', 'Operational Documents'),
        ('compliance', 'Compliance Documents'),
        ('custom', 'Custom Documents'),
    ], string='Category', required=True, default='hr')
    
    document_type_id = fields.Many2one('tazweed.document.type', string='Document Type')
    
    # Template Content
    template_type = fields.Selection([
        ('file', 'File Template'),
        ('html', 'HTML Template'),
        ('qweb', 'QWeb Template'),
    ], string='Template Type', required=True, default='html')
    
    # File Template
    template_file = fields.Binary(string='Template File')
    template_filename = fields.Char(string='Template Filename')
    
    # HTML/QWeb Template
    template_body = fields.Html(string='Template Body')
    
    # Dynamic Fields
    field_ids = fields.One2many('document.template.field', 'template_id', string='Template Fields')
    
    # Settings
    active = fields.Boolean(string='Active', default=True)
    is_default = fields.Boolean(string='Default Template', default=False)
    requires_approval = fields.Boolean(string='Requires Approval', default=False)
    
    # Target Models
    applicable_to = fields.Selection([
        ('employee', 'Employee'),
        ('client', 'Client'),
        ('placement', 'Placement'),
        ('general', 'General'),
    ], string='Applicable To', default='employee')
    
    # Statistics
    usage_count = fields.Integer(string='Usage Count', default=0)
    last_used_date = fields.Datetime(string='Last Used')
    
    # Preview
    preview_html = fields.Html(string='Preview', compute='_compute_preview')
    
    # Description
    description = fields.Text(string='Description')
    instructions = fields.Text(string='Usage Instructions')
    
    @api.depends('template_body', 'field_ids')
    def _compute_preview(self):
        for record in self:
            if record.template_type == 'html' and record.template_body:
                # Replace placeholders with sample values
                preview = record.template_body
                for field in record.field_ids:
                    placeholder = '{{' + field.field_key + '}}'
                    preview = preview.replace(placeholder, field.sample_value or f'[{field.name}]')
                record.preview_html = preview
            else:
                record.preview_html = '<p>Preview not available for this template type.</p>'
    
    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            existing = self.search([
                ('code', '=', record.code),
                ('id', '!=', record.id),
            ])
            if existing:
                raise ValidationError(_('Template code must be unique.'))
    
    def action_generate_document(self):
        """Open wizard to generate document from template"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate Document'),
            'res_model': 'document.template.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
            }
        }
    
    def action_duplicate_template(self):
        """Duplicate this template"""
        self.ensure_one()
        new_template = self.copy({
            'name': f"{self.name} (Copy)",
            'code': f"{self.code}_copy",
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Template'),
            'res_model': 'document.template',
            'res_id': new_template.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def render_template(self, values):
        """Render template with provided values"""
        self.ensure_one()
        
        if self.template_type == 'html':
            content = self.template_body or ''
            for key, value in values.items():
                placeholder = '{{' + key + '}}'
                content = content.replace(placeholder, str(value) if value else '')
            return content
        
        elif self.template_type == 'qweb':
            # Use Odoo's QWeb rendering
            return self.env['ir.qweb']._render(self.template_body, values)
        
        elif self.template_type == 'file':
            # Return the file template (for Word/PDF templates)
            return self.template_file
        
        return ''


class DocumentTemplateField(models.Model):
    """Template Field Definition"""
    _name = 'document.template.field'
    _description = 'Template Field'
    _order = 'sequence'

    template_id = fields.Many2one('document.template', string='Template', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    
    name = fields.Char(string='Field Name', required=True)
    field_key = fields.Char(string='Field Key', required=True, help='Used in template as {{field_key}}')
    
    field_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('selection', 'Selection'),
        ('boolean', 'Yes/No'),
        ('employee', 'Employee'),
        ('client', 'Client'),
        ('currency', 'Currency Amount'),
    ], string='Field Type', required=True, default='text')
    
    # For selection type
    selection_options = fields.Text(string='Selection Options', help='One option per line')
    
    # Validation
    required = fields.Boolean(string='Required', default=False)
    default_value = fields.Char(string='Default Value')
    sample_value = fields.Char(string='Sample Value', help='Used for preview')
    
    # Auto-fill from model
    auto_fill = fields.Boolean(string='Auto-Fill', default=False)
    source_model = fields.Char(string='Source Model')
    source_field = fields.Char(string='Source Field')
    
    # Help
    help_text = fields.Char(string='Help Text')


class DocumentTemplateCategory(models.Model):
    """Template Category"""
    _name = 'document.template.category'
    _description = 'Template Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Category Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    description = fields.Text(string='Description')
    icon = fields.Char(string='Icon', default='fa-folder')
    color = fields.Integer(string='Color')
    
    template_ids = fields.One2many('document.template', 'category', string='Templates')
    template_count = fields.Integer(string='Template Count', compute='_compute_template_count')
    
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('template_ids')
    def _compute_template_count(self):
        for record in self:
            record.template_count = len(record.template_ids)


class DocumentTemplateGenerateWizard(models.TransientModel):
    """Wizard to generate document from template"""
    _name = 'document.template.generate.wizard'
    _description = 'Generate Document from Template'

    template_id = fields.Many2one('document.template', string='Template', required=True)
    
    # Target
    employee_id = fields.Many2one('hr.employee', string='Employee')
    client_id = fields.Many2one('tazweed.client', string='Client')
    
    # Document Info
    document_name = fields.Char(string='Document Name', required=True)
    expiry_date = fields.Date(string='Expiry Date')
    
    # Dynamic Fields (populated based on template)
    field_value_ids = fields.One2many('document.template.field.value', 'wizard_id', string='Field Values')
    
    # Output
    output_format = fields.Selection([
        ('html', 'HTML'),
        ('pdf', 'PDF'),
        ('docx', 'Word Document'),
    ], string='Output Format', default='pdf')
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            self.document_name = f"{self.template_id.name} - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Create field value lines
            self.field_value_ids = [(5, 0, 0)]
            for field in self.template_id.field_ids:
                self.field_value_ids = [(0, 0, {
                    'field_id': field.id,
                    'field_name': field.name,
                    'field_key': field.field_key,
                    'field_type': field.field_type,
                    'required': field.required,
                    'value': field.default_value or '',
                })]
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Auto-fill fields from employee"""
        if self.employee_id and self.template_id:
            for field_value in self.field_value_ids:
                field = field_value.field_id
                if field.auto_fill and field.source_model == 'hr.employee':
                    value = getattr(self.employee_id, field.source_field, None)
                    if value:
                        field_value.value = str(value)
    
    def action_generate(self):
        """Generate document from template"""
        self.ensure_one()
        
        # Validate required fields
        for field_value in self.field_value_ids:
            if field_value.required and not field_value.value:
                raise UserError(_('Field "%s" is required.') % field_value.field_name)
        
        # Prepare values
        values = {}
        for field_value in self.field_value_ids:
            values[field_value.field_key] = field_value.value
        
        # Add standard values
        values.update({
            'date_today': datetime.now().strftime('%Y-%m-%d'),
            'company_name': self.env.company.name,
        })
        
        if self.employee_id:
            values.update({
                'employee_name': self.employee_id.name,
                'employee_id': self.employee_id.identification_id or '',
                'employee_department': self.employee_id.department_id.name if self.employee_id.department_id else '',
                'employee_job': self.employee_id.job_id.name if self.employee_id.job_id else '',
            })
        
        if self.client_id:
            values.update({
                'client_name': self.client_id.name,
            })
        
        # Render template
        content = self.template_id.render_template(values)
        
        # Create document
        doc_vals = {
            'name': self.document_name,
            'document_type_id': self.template_id.document_type_id.id if self.template_id.document_type_id else False,
            'state': 'active',
        }
        
        if self.employee_id:
            doc_vals['employee_id'] = self.employee_id.id
        if self.client_id:
            doc_vals['client_id'] = self.client_id.id
        if self.expiry_date:
            doc_vals['expiry_date'] = self.expiry_date
        
        # Convert content to file
        if self.output_format == 'html':
            doc_vals['attachment'] = base64.b64encode(content.encode('utf-8'))
            doc_vals['attachment_name'] = f"{self.document_name}.html"
        elif self.output_format == 'pdf':
            # In production, use wkhtmltopdf or similar
            doc_vals['attachment'] = base64.b64encode(content.encode('utf-8'))
            doc_vals['attachment_name'] = f"{self.document_name}.html"
        
        document = self.env['document.center.unified'].create(doc_vals)
        
        # Update template usage
        self.template_id.write({
            'usage_count': self.template_id.usage_count + 1,
            'last_used_date': fields.Datetime.now(),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generated Document'),
            'res_model': 'document.center.unified',
            'res_id': document.id,
            'view_mode': 'form',
            'target': 'current',
        }


class DocumentTemplateFieldValue(models.TransientModel):
    """Field value in generate wizard"""
    _name = 'document.template.field.value'
    _description = 'Template Field Value'

    wizard_id = fields.Many2one('document.template.generate.wizard', string='Wizard', ondelete='cascade')
    field_id = fields.Many2one('document.template.field', string='Field')
    
    field_name = fields.Char(string='Field Name')
    field_key = fields.Char(string='Field Key')
    field_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('date', 'Date'),
        ('selection', 'Selection'),
        ('boolean', 'Yes/No'),
        ('employee', 'Employee'),
        ('client', 'Client'),
        ('currency', 'Currency Amount'),
    ], string='Field Type')
    
    required = fields.Boolean(string='Required')
    value = fields.Char(string='Value')
