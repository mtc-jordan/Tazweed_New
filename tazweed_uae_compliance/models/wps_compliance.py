# -*- coding: utf-8 -*-
"""
WPS Compliance Extensions for tazweed_uae_compliance

This module extends the WPS models from tazweed_wps with additional
compliance-specific functionality.
"""

from odoo import models, fields, api, _
from datetime import date


class WPSFileComplianceExtension(models.Model):
    """Extend WPS File with compliance features"""
    _inherit = 'tazweed.wps.file'
    
    # Additional compliance fields
    compliance_checked = fields.Boolean(
        string='Compliance Checked',
        default=False,
        help='Indicates if compliance check has been performed',
    )
    compliance_check_date = fields.Date(
        string='Compliance Check Date',
    )
    compliance_notes = fields.Text(
        string='Compliance Notes',
    )
    
    def action_check_compliance(self):
        """Perform compliance check on WPS file"""
        for wps in self:
            # Check all lines have valid data
            invalid_lines = wps.line_ids.filtered(lambda l: not l.is_valid)
            if invalid_lines:
                wps.compliance_notes = _('Found %d invalid employee lines') % len(invalid_lines)
            else:
                wps.compliance_notes = _('All employee lines are valid')
            
            wps.compliance_checked = True
            wps.compliance_check_date = date.today()
        
        return True


class WPSComplianceExtension(models.Model):
    """Extend WPS Compliance Report with additional features"""
    _inherit = 'tazweed.wps.compliance'
    
    # Additional compliance tracking
    mohre_reported = fields.Boolean(
        string='Reported to MOHRE',
        default=False,
    )
    mohre_report_date = fields.Date(
        string='MOHRE Report Date',
    )
    mohre_reference = fields.Char(
        string='MOHRE Reference',
    )
    
    # Penalty tracking
    penalty_amount = fields.Float(
        string='Penalty Amount',
        digits=(16, 2),
    )
    penalty_reason = fields.Text(
        string='Penalty Reason',
    )
    penalty_paid = fields.Boolean(
        string='Penalty Paid',
        default=False,
    )
    
    def action_report_to_mohre(self):
        """Mark as reported to MOHRE"""
        for rec in self:
            rec.mohre_reported = True
            rec.mohre_report_date = date.today()
        return True
