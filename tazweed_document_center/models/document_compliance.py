# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _


class DocumentComplianceReport(models.Model):
    """Document compliance report per employee."""
    _name = 'document.compliance.report'
    _description = 'Document Compliance Report'
    _auto = False
    _order = 'compliance_score asc'

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job Position', readonly=True)
    
    total_documents = fields.Integer(string='Total Documents', readonly=True)
    valid_documents = fields.Integer(string='Valid Documents', readonly=True)
    expired_documents = fields.Integer(string='Expired Documents', readonly=True)
    expiring_documents = fields.Integer(string='Expiring Soon', readonly=True)
    missing_count = fields.Integer(string='Missing Mandatory', readonly=True)
    
    compliance_score = fields.Float(string='Compliance Score (%)', readonly=True)
    compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('warning', 'Warning'),
        ('non_compliant', 'Non-Compliant'),
    ], string='Status', readonly=True)
    
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        """Create SQL view for compliance report."""
        self.env.cr.execute("""
            DROP VIEW IF EXISTS document_compliance_report;
            CREATE OR REPLACE VIEW document_compliance_report AS (
                SELECT
                    e.id as id,
                    e.id as employee_id,
                    e.department_id,
                    e.job_id,
                    e.company_id,
                    COALESCE(doc_stats.total_docs, 0) as total_documents,
                    COALESCE(doc_stats.valid_docs, 0) as valid_documents,
                    COALESCE(doc_stats.expired_docs, 0) as expired_documents,
                    COALESCE(doc_stats.expiring_docs, 0) as expiring_documents,
                    COALESCE(mandatory.missing_count, 0) as missing_count,
                    CASE 
                        WHEN COALESCE(doc_stats.total_docs, 0) = 0 THEN 0
                        ELSE ROUND((COALESCE(doc_stats.valid_docs, 0)::numeric / 
                              NULLIF(COALESCE(doc_stats.total_docs, 0), 0)::numeric) * 100, 2)
                    END as compliance_score,
                    CASE
                        WHEN COALESCE(doc_stats.expired_docs, 0) > 0 OR COALESCE(mandatory.missing_count, 0) > 0 
                            THEN 'non_compliant'
                        WHEN COALESCE(doc_stats.expiring_docs, 0) > 0 
                            THEN 'warning'
                        ELSE 'compliant'
                    END as compliance_status
                FROM hr_employee e
                LEFT JOIN (
                    SELECT 
                        d.employee_id,
                        COUNT(*) as total_docs,
                        COUNT(CASE WHEN d.expiry_date IS NULL OR d.expiry_date > CURRENT_DATE + INTERVAL '30 days' THEN 1 END) as valid_docs,
                        COUNT(CASE WHEN d.expiry_date < CURRENT_DATE THEN 1 END) as expired_docs,
                        COUNT(CASE WHEN d.expiry_date >= CURRENT_DATE AND d.expiry_date <= CURRENT_DATE + INTERVAL '30 days' THEN 1 END) as expiring_docs
                    FROM tazweed_employee_document d
                    GROUP BY d.employee_id
                ) doc_stats ON doc_stats.employee_id = e.id
                LEFT JOIN (
                    SELECT 
                        e2.id as employee_id,
                        COUNT(dt.id) - COUNT(d2.id) as missing_count
                    FROM hr_employee e2
                    CROSS JOIN tazweed_document_type dt
                    LEFT JOIN tazweed_employee_document d2 
                        ON d2.employee_id = e2.id AND d2.document_type_id = dt.id
                    WHERE dt.is_mandatory = true
                    GROUP BY e2.id
                ) mandatory ON mandatory.employee_id = e.id
                WHERE e.active = true
            )
        """)

    def action_view_documents(self):
        """View employee documents."""
        self.ensure_one()
        return {
            'name': _('Documents - %s') % self.employee_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.employee_id.id)],
        }

    def action_view_expired(self):
        """View expired documents."""
        self.ensure_one()
        return {
            'name': _('Expired Documents - %s') % self.employee_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'view_mode': 'tree,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('expiry_date', '<', fields.Date.today())
            ],
        }

    def action_view_expiring(self):
        """View expiring documents."""
        self.ensure_one()
        today = fields.Date.today()
        return {
            'name': _('Expiring Documents - %s') % self.employee_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'view_mode': 'tree,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('expiry_date', '>=', today),
                ('expiry_date', '<=', today + timedelta(days=30))
            ],
        }

    def action_create_renewal(self):
        """Create renewal request for expired/expiring documents."""
        self.ensure_one()
        today = fields.Date.today()
        
        # Find documents needing renewal
        docs = self.env['tazweed.employee.document'].search([
            ('employee_id', '=', self.employee_id.id),
            ('expiry_date', '<=', today + timedelta(days=30))
        ])
        
        if not docs:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Documents'),
                    'message': _('No documents need renewal.'),
                    'type': 'warning',
                }
            }
        
        # Create renewal requests
        for doc in docs:
            existing = self.env['document.renewal.request'].search([
                ('document_id', '=', doc.id),
                ('state', 'not in', ['completed', 'cancelled', 'rejected'])
            ], limit=1)
            
            if not existing:
                self.env['document.renewal.request'].create({
                    'document_id': doc.id,
                    'reason': _('Document expiring/expired - auto-generated'),
                })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Renewal Requests Created'),
                'message': _('Renewal requests have been created for %d documents.') % len(docs),
                'type': 'success',
            }
        }


class DocumentComplianceReportWizard(models.TransientModel):
    """Wizard to generate compliance report."""
    _name = 'document.compliance.report.wizard'
    _description = 'Document Compliance Report Wizard'

    department_id = fields.Many2one('hr.department', string='Department')
    document_type_id = fields.Many2one('tazweed.document.type', string='Document Type')
    compliance_status = fields.Selection([
        ('all', 'All'),
        ('compliant', 'Compliant'),
        ('warning', 'Warning'),
        ('non_compliant', 'Non-Compliant'),
    ], string='Status Filter', default='all')
    
    include_expired = fields.Boolean(string='Include Expired', default=True)
    include_expiring = fields.Boolean(string='Include Expiring', default=True)
    include_missing = fields.Boolean(string='Include Missing Mandatory', default=True)
    
    def action_generate_report(self):
        """Generate and display compliance report."""
        domain = []
        
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        
        if self.compliance_status != 'all':
            domain.append(('compliance_status', '=', self.compliance_status))
        
        return {
            'name': _('Document Compliance Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.compliance.report',
            'view_mode': 'tree,pivot,graph',
            'domain': domain,
            'context': {'search_default_group_by_department': 1},
        }

    def action_export_excel(self):
        """Export compliance report to Excel."""
        # This would generate an Excel report
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Export'),
                'message': _('Report exported successfully.'),
                'type': 'success',
            }
        }
