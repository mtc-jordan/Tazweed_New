# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class UnifiedDocument(models.Model):
    """Unified Document View - Aggregates documents from all HR modules."""
    _name = 'document.center.unified'
    _description = 'Unified Document Center'
    _order = 'expiry_date asc, create_date desc'
    _rec_name = 'display_name'

    name = fields.Char(string='Document Name', required=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Source Information
    source_module = fields.Selection([
        ('core', 'HR Core'),
        ('placement', 'Placement'),
        ('payroll', 'Payroll'),
        ('leave', 'Leave'),
        ('performance', 'Performance'),
        ('manual', 'Manual Upload'),
    ], string='Source Module', required=True, default='manual')
    
    source_model = fields.Char(string='Source Model')
    source_record_id = fields.Integer(string='Source Record ID')
    
    # Document Classification
    document_category = fields.Selection([
        ('identity', 'Identity Documents'),
        ('visa', 'Visa & Work Permits'),
        ('contract', 'Contracts & Agreements'),
        ('certificate', 'Certificates & Qualifications'),
        ('medical', 'Medical Documents'),
        ('financial', 'Financial Documents'),
        ('leave', 'Leave Documents'),
        ('performance', 'Performance Documents'),
        ('other', 'Other Documents'),
    ], string='Category', required=True, default='other')
    
    document_type_id = fields.Many2one(
        'tazweed.document.type',
        string='Document Type',
    )
    
    # Related Records
    employee_id = fields.Many2one('hr.employee', string='Employee', index=True)
    candidate_id = fields.Many2one('tazweed.candidate', string='Candidate')
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
    )
    
    # Document Details
    document_number = fields.Char(string='Document Number')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    issue_place = fields.Char(string='Issue Place')
    issue_authority = fields.Char(string='Issuing Authority')
    
    # Attachment
    attachment = fields.Binary(string='Attachment')
    attachment_name = fields.Char(string='Attachment Name')
    file_size = fields.Integer(string='File Size (KB)')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
        ('archived', 'Archived'),
    ], string='Status', compute='_compute_state', store=True, default='draft')
    
    days_to_expiry = fields.Integer(
        string='Days to Expiry',
        compute='_compute_state',
        store=True,
    )
    
    expiry_status = fields.Selection([
        ('no_expiry', 'No Expiry'),
        ('valid', 'Valid (>90 days)'),
        ('expiring_90', 'Expiring in 90 days'),
        ('expiring_60', 'Expiring in 60 days'),
        ('expiring_30', 'Expiring in 30 days'),
        ('expiring_15', 'Expiring in 15 days'),
        ('expiring_7', 'Expiring in 7 days'),
        ('expired', 'Expired'),
    ], string='Expiry Status', compute='_compute_state', store=True)
    
    # Version Control
    version = fields.Integer(string='Version', default=1)
    is_latest = fields.Boolean(string='Is Latest Version', default=True)
    previous_version_id = fields.Many2one('document.center.unified', string='Previous Version')
    
    # Verification
    is_verified = fields.Boolean(string='Verified', default=False)
    verified_by_id = fields.Many2one('res.users', string='Verified By')
    verified_date = fields.Datetime(string='Verification Date')
    verification_notes = fields.Text(string='Verification Notes')
    
    # Alerts
    alert_sent = fields.Boolean(string='Alert Sent', default=False)
    last_alert_date = fields.Date(string='Last Alert Date')
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('name', 'document_type_id', 'employee_id', 'candidate_id')
    def _compute_display_name(self):
        for record in self:
            parts = []
            try:
                if record.employee_id and record.employee_id.exists():
                    parts.append(record.employee_id.name or 'Unknown Employee')
                elif record.candidate_id and record.candidate_id.exists():
                    parts.append(record.candidate_id.name or 'Unknown Candidate')
                if record.document_type_id and record.document_type_id.exists():
                    parts.append(record.document_type_id.name or 'Unknown Type')
                elif record.name:
                    parts.append(record.name)
            except Exception:
                parts = [record.name or 'Document']
            record.display_name = ' - '.join(parts) if parts else 'New Document'

    @api.depends('expiry_date')
    def _compute_state(self):
        today = fields.Date.today()
        for record in self:
            if not record.expiry_date:
                record.state = 'valid'
                record.days_to_expiry = 999
                record.expiry_status = 'no_expiry'
            else:
                delta = (record.expiry_date - today).days
                record.days_to_expiry = delta
                
                if delta < 0:
                    record.state = 'expired'
                    record.expiry_status = 'expired'
                elif delta <= 7:
                    record.state = 'expiring'
                    record.expiry_status = 'expiring_7'
                elif delta <= 15:
                    record.state = 'expiring'
                    record.expiry_status = 'expiring_15'
                elif delta <= 30:
                    record.state = 'expiring'
                    record.expiry_status = 'expiring_30'
                elif delta <= 60:
                    record.state = 'valid'
                    record.expiry_status = 'expiring_60'
                elif delta <= 90:
                    record.state = 'valid'
                    record.expiry_status = 'expiring_90'
                else:
                    record.state = 'valid'
                    record.expiry_status = 'valid'

    def action_verify(self):
        """Mark document as verified."""
        self.write({
            'is_verified': True,
            'verified_by_id': self.env.user.id,
            'verified_date': fields.Datetime.now(),
        })
        return True

    def action_archive(self):
        """Archive the document."""
        self.write({'state': 'archived', 'active': False})
        return True

    def action_view_source(self):
        """Navigate to source record."""
        self.ensure_one()
        if self.source_model and self.source_record_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': self.source_model,
                'res_id': self.source_record_id,
                'view_mode': 'form',
                'target': 'current',
            }
        raise UserError(_('No source record linked to this document.'))

    def action_create_new_version(self):
        """Create a new version of this document."""
        self.ensure_one()
        new_doc = self.copy({
            'version': self.version + 1,
            'previous_version_id': self.id,
            'is_verified': False,
            'verified_by_id': False,
            'verified_date': False,
        })
        self.write({'is_latest': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'document.center.unified',
            'res_id': new_doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def sync_from_employee_documents(self):
        """Sync documents from tazweed.employee.document."""
        EmployeeDoc = self.env['tazweed.employee.document'].sudo()
        docs = EmployeeDoc.search([])
        
        for doc in docs:
            existing = self.search([
                ('source_model', '=', 'tazweed.employee.document'),
                ('source_record_id', '=', doc.id),
            ], limit=1)
            
            # Determine category based on document type
            category = 'other'
            if doc.document_type_id:
                type_name = doc.document_type_id.name.lower()
                if 'passport' in type_name or 'emirates' in type_name or 'id' in type_name:
                    category = 'identity'
                elif 'visa' in type_name or 'permit' in type_name or 'labour' in type_name:
                    category = 'visa'
                elif 'contract' in type_name:
                    category = 'contract'
                elif 'certificate' in type_name or 'qualification' in type_name:
                    category = 'certificate'
                elif 'medical' in type_name or 'insurance' in type_name:
                    category = 'medical'
            
            vals = {
                'name': doc.name,
                'source_module': 'core',
                'source_model': 'tazweed.employee.document',
                'source_record_id': doc.id,
                'document_category': category,
                'document_type_id': doc.document_type_id.id if doc.document_type_id else False,
                'employee_id': doc.employee_id.id if doc.employee_id else False,
                'document_number': doc.document_number,
                'issue_date': doc.issue_date,
                'expiry_date': doc.expiry_date,
                'issue_place': doc.issue_place,
                'issue_authority': doc.issue_authority,
                'attachment': doc.attachment,
                'attachment_name': doc.attachment_name,
                'notes': doc.notes,
                'company_id': doc.company_id.id if doc.company_id else self.env.company.id,
            }
            
            if existing:
                existing.write(vals)
            else:
                self.create(vals)
        
        return True

    @api.model
    def sync_from_candidate_documents(self):
        """Sync documents from tazweed.candidate (if placement module installed)."""
        if 'tazweed.candidate' not in self.env:
            return True
            
        Candidate = self.env['tazweed.candidate'].sudo()
        candidates = Candidate.search([])
        
        for candidate in candidates:
            # Check for resume/CV
            if hasattr(candidate, 'resume') and candidate.resume:
                existing = self.search([
                    ('source_model', '=', 'tazweed.candidate'),
                    ('source_record_id', '=', candidate.id),
                    ('document_category', '=', 'certificate'),
                ], limit=1)
                
                vals = {
                    'name': f"Resume - {candidate.name}",
                    'source_module': 'placement',
                    'source_model': 'tazweed.candidate',
                    'source_record_id': candidate.id,
                    'document_category': 'certificate',
                    'candidate_id': candidate.id,
                    'attachment': candidate.resume,
                    'attachment_name': getattr(candidate, 'resume_filename', 'resume.pdf'),
                    'company_id': candidate.company_id.id if hasattr(candidate, 'company_id') and candidate.company_id else self.env.company.id,
                }
                
                if existing:
                    existing.write(vals)
                else:
                    self.create(vals)
        
        return True

    @api.model
    def sync_all_documents(self):
        """Sync documents from all modules."""
        self.sync_from_employee_documents()
        self.sync_from_candidate_documents()
        return True

    @api.model
    def get_document_center_data(self):
        """Get data for document center dashboard."""
        today = fields.Date.today()
        docs = self.sudo().search([('active', '=', True)])
        
        # Statistics
        total_docs = len(docs)
        expired = len(docs.filtered(lambda d: d.state == 'expired'))
        expiring_7 = len(docs.filtered(lambda d: d.expiry_status == 'expiring_7'))
        expiring_15 = len(docs.filtered(lambda d: d.expiry_status == 'expiring_15'))
        expiring_30 = len(docs.filtered(lambda d: d.expiry_status == 'expiring_30'))
        expiring_60 = len(docs.filtered(lambda d: d.expiry_status == 'expiring_60'))
        expiring_90 = len(docs.filtered(lambda d: d.expiry_status == 'expiring_90'))
        valid = len(docs.filtered(lambda d: d.state == 'valid'))
        verified = len(docs.filtered(lambda d: d.is_verified))
        
        # By Category
        by_category = []
        categories = dict(self._fields['document_category'].selection)
        for cat_key, cat_label in categories.items():
            count = len(docs.filtered(lambda d: d.document_category == cat_key))
            if count > 0:
                by_category.append({'name': cat_label, 'count': count})
        
        # By Source Module
        by_source = []
        sources = dict(self._fields['source_module'].selection)
        for src_key, src_label in sources.items():
            count = len(docs.filtered(lambda d: d.source_module == src_key))
            if count > 0:
                by_source.append({'name': src_label, 'count': count})
        
        # By Department
        by_department = []
        departments = self.env['hr.department'].search([], limit=10)
        for dept in departments:
            count = len(docs.filtered(lambda d: d.department_id.id == dept.id))
            if count > 0:
                by_department.append({'name': dept.name[:15], 'count': count})
        
        # Expiry Timeline
        expiry_timeline = [
            {'label': 'Expired', 'count': expired, 'color': '#EF4444'},
            {'label': '7 Days', 'count': expiring_7, 'color': '#F97316'},
            {'label': '15 Days', 'count': expiring_15, 'color': '#F59E0B'},
            {'label': '30 Days', 'count': expiring_30, 'color': '#EAB308'},
            {'label': '60 Days', 'count': expiring_60, 'color': '#84CC16'},
            {'label': '90 Days', 'count': expiring_90, 'color': '#22C55E'},
            {'label': 'Valid', 'count': valid - expiring_90 - expiring_60, 'color': '#10B981'},
        ]
        
        # Recent Documents
        recent_docs = []
        recent = self.search([('active', '=', True)], order='create_date desc', limit=10)
        for doc in recent:
            recent_docs.append({
                'id': doc.id,
                'name': doc.display_name,
                'category': dict(self._fields['document_category'].selection).get(doc.document_category, ''),
                'employee': doc.employee_id.name if doc.employee_id else (doc.candidate_id.name if doc.candidate_id else ''),
                'expiry_date': str(doc.expiry_date) if doc.expiry_date else '',
                'state': doc.state,
                'source': dict(self._fields['source_module'].selection).get(doc.source_module, ''),
            })
        
        # Expiring Soon (next 30 days)
        expiring_soon = []
        expiring = docs.filtered(
            lambda d: d.expiry_date and today <= d.expiry_date <= today + timedelta(days=30)
        ).sorted(key=lambda d: d.expiry_date)[:10]
        for doc in expiring:
            expiring_soon.append({
                'id': doc.id,
                'name': doc.display_name,
                'employee': doc.employee_id.name if doc.employee_id else '',
                'expiry_date': str(doc.expiry_date) if doc.expiry_date else '',
                'days_left': doc.days_to_expiry,
            })
        
        # Alerts
        alerts = []
        if expired > 0:
            alerts.append({
                'type': 'danger',
                'icon': 'fa-exclamation-circle',
                'message': f'{expired} document(s) have expired and need immediate attention',
            })
        if expiring_7 > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'fa-clock-o',
                'message': f'{expiring_7} document(s) expiring within 7 days',
            })
        if expiring_30 > 0:
            alerts.append({
                'type': 'info',
                'icon': 'fa-info-circle',
                'message': f'{expiring_30} document(s) expiring within 30 days',
            })
        
        compliance_rate = ((total_docs - expired) / total_docs * 100) if total_docs > 0 else 100
        
        return {
            'stats': {
                'totalDocuments': total_docs,
                'expiredDocuments': expired,
                'expiringDocuments': expiring_7 + expiring_15 + expiring_30,
                'validDocuments': valid,
                'verifiedDocuments': verified,
                'complianceRate': round(compliance_rate, 1),
                'expiring7Days': expiring_7,
                'expiring30Days': expiring_30,
            },
            'by_category': by_category,
            'by_source': by_source,
            'by_department': by_department,
            'expiry_timeline': expiry_timeline,
            'recent_documents': recent_docs,
            'expiring_soon': expiring_soon,
            'alerts': alerts,
        }
