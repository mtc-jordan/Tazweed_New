# -*- coding: utf-8 -*-
"""
Document Versioning Module
Track document versions and changes with full history
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import hashlib
from datetime import datetime


class DocumentVersion(models.Model):
    """Document Version History"""
    _name = 'document.version'
    _description = 'Document Version'
    _order = 'version_number desc'

    name = fields.Char(string='Version Name', compute='_compute_name', store=True)
    document_id = fields.Many2one('document.center.unified', string='Document', required=True, ondelete='cascade')
    
    # Version Info
    version_number = fields.Integer(string='Version Number', required=True)
    version_label = fields.Char(string='Version Label')
    is_current = fields.Boolean(string='Current Version', default=False)
    is_major = fields.Boolean(string='Major Version', default=False)
    
    # File Content
    file_content = fields.Binary(string='File Content', attachment=True)
    file_name = fields.Char(string='File Name')
    file_size = fields.Integer(string='File Size (bytes)')
    file_hash = fields.Char(string='File Hash (MD5)')
    mime_type = fields.Char(string='MIME Type')
    
    # Metadata
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    create_date = fields.Datetime(string='Created On', default=fields.Datetime.now)
    
    # Change Information
    change_summary = fields.Text(string='Change Summary')
    change_type = fields.Selection([
        ('initial', 'Initial Upload'),
        ('update', 'Content Update'),
        ('correction', 'Correction'),
        ('renewal', 'Renewal'),
        ('amendment', 'Amendment'),
        ('translation', 'Translation'),
    ], string='Change Type', default='update')
    
    # Comparison
    changes_from_previous = fields.Text(string='Changes from Previous', compute='_compute_changes')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('deleted', 'Deleted'),
    ], string='Status', default='draft')
    
    @api.depends('document_id', 'version_number')
    def _compute_name(self):
        for record in self:
            if record.document_id and record.version_number:
                record.name = f"{record.document_id.name} - v{record.version_number}"
            else:
                record.name = 'New Version'
    
    @api.depends('version_number')
    def _compute_changes(self):
        for record in self:
            # Get previous version
            previous = self.search([
                ('document_id', '=', record.document_id.id),
                ('version_number', '<', record.version_number),
            ], order='version_number desc', limit=1)
            
            if previous:
                changes = []
                if record.file_hash != previous.file_hash:
                    changes.append('File content changed')
                if record.file_size != previous.file_size:
                    size_diff = record.file_size - previous.file_size
                    changes.append(f'File size: {size_diff:+d} bytes')
                record.changes_from_previous = '\n'.join(changes) if changes else 'No changes detected'
            else:
                record.changes_from_previous = 'Initial version'
    
    @api.model
    def create(self, vals):
        # Calculate file hash if content provided
        if vals.get('file_content'):
            content = base64.b64decode(vals['file_content'])
            vals['file_hash'] = hashlib.md5(content).hexdigest()
            vals['file_size'] = len(content)
        
        record = super().create(vals)
        
        # If this is marked as current, unmark others
        if record.is_current:
            self.search([
                ('document_id', '=', record.document_id.id),
                ('id', '!=', record.id),
                ('is_current', '=', True),
            ]).write({'is_current': False})
        
        return record
    
    def action_set_current(self):
        """Set this version as the current version"""
        self.ensure_one()
        
        # Unmark other versions
        self.search([
            ('document_id', '=', self.document_id.id),
            ('is_current', '=', True),
        ]).write({'is_current': False})
        
        # Mark this as current
        self.write({
            'is_current': True,
            'state': 'active',
        })
        
        # Update main document with this version's file
        if self.file_content:
            self.document_id.write({
                'attachment': self.file_content,
                'attachment_name': self.file_name,
            })
    
    def action_download(self):
        """Download this version"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/document.version/{self.id}/file_content/{self.file_name}?download=true',
            'target': 'self',
        }
    
    def action_compare_with_previous(self):
        """Open comparison view with previous version"""
        self.ensure_one()
        previous = self.search([
            ('document_id', '=', self.document_id.id),
            ('version_number', '<', self.version_number),
        ], order='version_number desc', limit=1)
        
        if not previous:
            raise UserError(_('No previous version to compare with.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Version Comparison'),
            'res_model': 'document.version.comparison',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_version_1_id': previous.id,
                'default_version_2_id': self.id,
            }
        }


class DocumentVersionComparison(models.TransientModel):
    """Compare two document versions"""
    _name = 'document.version.comparison'
    _description = 'Document Version Comparison'

    version_1_id = fields.Many2one('document.version', string='Version 1', required=True)
    version_2_id = fields.Many2one('document.version', string='Version 2', required=True)
    
    # Version 1 Info
    v1_version_number = fields.Integer(related='version_1_id.version_number', string='V1 Number')
    v1_file_size = fields.Integer(related='version_1_id.file_size', string='V1 Size')
    v1_created_by = fields.Many2one(related='version_1_id.created_by', string='V1 Created By')
    v1_create_date = fields.Datetime(related='version_1_id.create_date', string='V1 Date')
    
    # Version 2 Info
    v2_version_number = fields.Integer(related='version_2_id.version_number', string='V2 Number')
    v2_file_size = fields.Integer(related='version_2_id.file_size', string='V2 Size')
    v2_created_by = fields.Many2one(related='version_2_id.created_by', string='V2 Created By')
    v2_create_date = fields.Datetime(related='version_2_id.create_date', string='V2 Date')
    
    # Comparison Results
    size_difference = fields.Integer(string='Size Difference', compute='_compute_comparison')
    content_changed = fields.Boolean(string='Content Changed', compute='_compute_comparison')
    comparison_notes = fields.Text(string='Comparison Notes', compute='_compute_comparison')
    
    @api.depends('version_1_id', 'version_2_id')
    def _compute_comparison(self):
        for record in self:
            if record.version_1_id and record.version_2_id:
                record.size_difference = record.version_2_id.file_size - record.version_1_id.file_size
                record.content_changed = record.version_1_id.file_hash != record.version_2_id.file_hash
                
                notes = []
                if record.content_changed:
                    notes.append('File content has been modified')
                if record.size_difference > 0:
                    notes.append(f'File size increased by {record.size_difference} bytes')
                elif record.size_difference < 0:
                    notes.append(f'File size decreased by {abs(record.size_difference)} bytes')
                
                record.comparison_notes = '\n'.join(notes) if notes else 'No significant changes detected'
            else:
                record.size_difference = 0
                record.content_changed = False
                record.comparison_notes = ''


class UnifiedDocumentVersioning(models.Model):
    """Extend Unified Document with versioning capabilities"""
    _inherit = 'document.center.unified'

    # Version Control
    version_ids = fields.One2many('document.version', 'document_id', string='Versions')
    current_version_id = fields.Many2one('document.version', string='Current Version', 
                                          compute='_compute_current_version', store=True)
    version_count = fields.Integer(string='Version Count', compute='_compute_version_count')
    latest_version_number = fields.Integer(string='Latest Version', compute='_compute_version_count')
    
    # Version Settings
    auto_version = fields.Boolean(string='Auto-Version on Update', default=True)
    keep_all_versions = fields.Boolean(string='Keep All Versions', default=True)
    max_versions = fields.Integer(string='Max Versions to Keep', default=10)
    
    @api.depends('version_ids', 'version_ids.is_current')
    def _compute_current_version(self):
        for record in self:
            current = record.version_ids.filtered(lambda v: v.is_current)
            record.current_version_id = current[0] if current else False
    
    @api.depends('version_ids')
    def _compute_version_count(self):
        for record in self:
            record.version_count = len(record.version_ids)
            if record.version_ids:
                record.latest_version_number = max(record.version_ids.mapped('version_number'))
            else:
                record.latest_version_number = 0
    
    def action_create_version(self):
        """Create a new version from current document"""
        self.ensure_one()
        
        # Get next version number
        next_version = self.latest_version_number + 1
        
        # Create new version
        version = self.env['document.version'].create({
            'document_id': self.id,
            'version_number': next_version,
            'file_content': self.attachment,
            'file_name': self.attachment_name,
            'is_current': True,
            'change_type': 'update',
            'state': 'active',
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Version'),
            'res_model': 'document.version',
            'res_id': version.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_versions(self):
        """View all versions of this document"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Document Versions'),
            'res_model': 'document.version',
            'view_mode': 'tree,form',
            'domain': [('document_id', '=', self.id)],
            'context': {'default_document_id': self.id},
        }
    
    def write(self, vals):
        """Auto-create version when attachment changes"""
        result = super().write(vals)
        
        if vals.get('attachment') and self.auto_version:
            for record in self:
                # Create new version automatically
                next_version = record.latest_version_number + 1
                self.env['document.version'].create({
                    'document_id': record.id,
                    'version_number': next_version,
                    'file_content': vals['attachment'],
                    'file_name': vals.get('attachment_name', record.attachment_name),
                    'is_current': True,
                    'change_type': 'update',
                    'state': 'active',
                })
                
                # Clean up old versions if needed
                if not record.keep_all_versions and record.version_count > record.max_versions:
                    old_versions = record.version_ids.filtered(
                        lambda v: not v.is_current
                    ).sorted('version_number')[:-record.max_versions]
                    old_versions.write({'state': 'archived'})
        
        return result
