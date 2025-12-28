# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, timedelta


class DocumentComplianceTracker(models.Model):
    """Document Compliance Tracker"""
    _name = 'tazweed.document.compliance'
    _description = 'Document Compliance Tracker'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date'

    name = fields.Char(string='Reference', compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    
    document_type = fields.Selection([
        ('passport', 'Passport'),
        ('emirates_id', 'Emirates ID'),
        ('visa', 'Visa'),
        ('labour_card', 'Labour Card'),
        ('medical', 'Medical Insurance'),
        ('work_permit', 'Work Permit'),
        ('driving_license', 'Driving License'),
        ('trade_license', 'Trade License'),
        ('other', 'Other'),
    ], string='Document Type', required=True)
    
    document_number = fields.Char(string='Document Number')
    
    # Dates
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    
    # Expiry Tracking
    days_to_expiry = fields.Integer(string='Days to Expiry', compute='_compute_expiry', store=True)
    expiry_status = fields.Selection([
        ('valid', 'Valid'),
        ('expiring_soon', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Expiry Status', compute='_compute_expiry', store=True)
    
    # Alerts
    alert_days = fields.Integer(string='Alert Days Before', default=30)
    is_alert_sent = fields.Boolean(string='Alert Sent')
    alert_date = fields.Date(string='Alert Date')
    
    # Renewal
    renewal_status = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Renewal Status', default='not_required')
    
    renewal_date = fields.Date(string='Renewal Date')
    renewal_cost = fields.Float(string='Renewal Cost')
    
    # Document
    document = fields.Binary(string='Document')
    document_name = fields.Char(string='Document Name')
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('employee_id', 'document_type')
    def _compute_name(self):
        for rec in self:
            doc_type = dict(rec._fields['document_type'].selection).get(rec.document_type, '')
            rec.name = f'{rec.employee_id.name} - {doc_type}'

    @api.depends('expiry_date', 'alert_days')
    def _compute_expiry(self):
        today = date.today()
        for rec in self:
            if rec.expiry_date:
                delta = rec.expiry_date - today
                rec.days_to_expiry = delta.days
                
                if delta.days < 0:
                    rec.expiry_status = 'expired'
                elif delta.days <= rec.alert_days:
                    rec.expiry_status = 'expiring_soon'
                else:
                    rec.expiry_status = 'valid'
            else:
                rec.days_to_expiry = 0
                rec.expiry_status = 'valid'

    def action_send_alert(self):
        """Send expiry alert"""
        self.ensure_one()
        # Send notification
        self.message_post(
            body=_('Document expiry alert: %s expires on %s') % (self.document_type, self.expiry_date),
            message_type='notification',
        )
        self.write({
            'is_alert_sent': True,
            'alert_date': date.today(),
        })
        return True

    def action_start_renewal(self):
        self.write({'renewal_status': 'in_progress'})

    def action_complete_renewal(self):
        self.write({
            'renewal_status': 'completed',
            'renewal_date': date.today(),
        })

    @api.model
    def _cron_check_expiry(self):
        """Cron job to check document expiry"""
        today = date.today()
        
        # Find documents expiring soon
        expiring = self.search([
            ('expiry_status', '=', 'expiring_soon'),
            ('is_alert_sent', '=', False),
        ])
        
        for doc in expiring:
            doc.action_send_alert()
        
        return True


class ComplianceDashboard(models.Model):
    """Compliance Dashboard"""
    _name = 'tazweed.compliance.dashboard'
    _description = 'Compliance Dashboard'
    _auto = False

    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company')
    
    # WPS Compliance
    wps_compliance_rate = fields.Float(string='WPS Compliance %')
    wps_pending_files = fields.Integer(string='WPS Pending Files')
    
    # Emiratization
    emiratization_rate = fields.Float(string='Emiratization %')
    emiratization_gap = fields.Integer(string='Emiratization Gap')
    
    # Documents
    expiring_documents = fields.Integer(string='Expiring Documents')
    expired_documents = fields.Integer(string='Expired Documents')
    
    # Work Permits
    expiring_permits = fields.Integer(string='Expiring Permits')
    expired_permits = fields.Integer(string='Expired Permits')

    def init(self):
        """Create view for compliance dashboard"""
        self.env.cr.execute("""
            DROP VIEW IF EXISTS tazweed_compliance_dashboard;
            CREATE OR REPLACE VIEW tazweed_compliance_dashboard AS (
                SELECT
                    1 as id,
                    'Compliance Dashboard' as name,
                    c.id as company_id,
                    0.0 as wps_compliance_rate,
                    0 as wps_pending_files,
                    0.0 as emiratization_rate,
                    0 as emiratization_gap,
                    0 as expiring_documents,
                    0 as expired_documents,
                    0 as expiring_permits,
                    0 as expired_permits
                FROM res_company c
                LIMIT 1
            )
        """)
