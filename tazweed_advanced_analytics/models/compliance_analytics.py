from odoo import models, fields, api
from datetime import datetime, timedelta


class ComplianceAnalytics(models.Model):
    """Compliance analytics and tracking."""
    
    _name = 'tazweed.compliance.analytics'
    _description = 'Compliance Analytics'
    _rec_name = 'analytics_name'
    
    analytics_name = fields.Char(
        string='Analytics Name',
        required=True,
        help='Name of compliance analytics'
    )
    
    # Period
    period_start = fields.Date(
        string='Period Start',
        required=True
    )
    
    period_end = fields.Date(
        string='Period End',
        required=True
    )
    
    # Emiratization Metrics
    total_employees = fields.Integer(
        string='Total Employees',
        compute='_compute_emiratization_metrics',
        store=True,
        help='Total employees'
    )
    
    uae_nationals = fields.Integer(
        string='UAE Nationals',
        compute='_compute_emiratization_metrics',
        store=True,
        help='Number of UAE nationals'
    )
    
    emiratization_percentage = fields.Float(
        string='Emiratization %',
        compute='_compute_emiratization_metrics',
        store=True,
        help='Emiratization percentage'
    )
    
    emiratization_compliant = fields.Boolean(
        string='Emiratization Compliant',
        compute='_compute_emiratization_metrics',
        store=True,
        help='Emiratization compliant'
    )
    
    # WPS Metrics
    wps_submitted_count = fields.Integer(
        string='WPS Submitted',
        help='WPS submissions'
    )
    
    wps_pending_count = fields.Integer(
        string='WPS Pending',
        help='WPS pending'
    )
    
    wps_compliance_rate = fields.Float(
        string='WPS Compliance %',
        help='WPS compliance rate'
    )
    
    # MOHRE Metrics
    mohre_reported_count = fields.Integer(
        string='MOHRE Reported',
        help='MOHRE reported employees'
    )
    
    mohre_pending_count = fields.Integer(
        string='MOHRE Pending',
        help='MOHRE pending'
    )
    
    mohre_compliance_rate = fields.Float(
        string='MOHRE Compliance %',
        help='MOHRE compliance rate'
    )
    
    # Labour Law Metrics
    minimum_wage_compliant = fields.Integer(
        string='Minimum Wage Compliant',
        help='Employees with minimum wage'
    )
    
    minimum_wage_non_compliant = fields.Integer(
        string='Minimum Wage Non-Compliant',
        help='Employees below minimum wage'
    )
    
    minimum_wage_compliance_rate = fields.Float(
        string='Minimum Wage Compliance %',
        help='Minimum wage compliance rate'
    )
    
    # Leave Compliance
    leave_compliant = fields.Integer(
        string='Leave Compliant',
        help='Employees with compliant leave'
    )
    
    leave_non_compliant = fields.Integer(
        string='Leave Non-Compliant',
        help='Employees exceeding leave limit'
    )
    
    leave_compliance_rate = fields.Float(
        string='Leave Compliance %',
        help='Leave compliance rate'
    )
    
    # Overall Compliance
    overall_compliance_score = fields.Float(
        string='Overall Compliance Score',
        compute='_compute_overall_compliance',
        store=True,
        help='Overall compliance score (0-100)'
    )
    
    compliance_status = fields.Selection(
        [('excellent', 'Excellent'), ('good', 'Good'), ('fair', 'Fair'), ('poor', 'Poor')],
        string='Compliance Status',
        compute='_compute_overall_compliance',
        store=True,
        help='Overall compliance status'
    )
    
    # Risk Assessment
    high_risk_count = fields.Integer(
        string='High Risk',
        help='High risk items'
    )
    
    medium_risk_count = fields.Integer(
        string='Medium Risk',
        help='Medium risk items'
    )
    
    low_risk_count = fields.Integer(
        string='Low Risk',
        help='Low risk items'
    )
    
    @api.depends('period_start', 'period_end')
    def _compute_emiratization_metrics(self):
        """Compute emiratization metrics."""
        for record in self:
            try:
                employees = self.env['hr.employee'].search([
                    ('active', '=', True),
                    ('company_id', '=', self.env.company.id),
                ])
                
                record.total_employees = len(employees)
                
                uae_nationals = employees.filtered(lambda e: e.country_id and e.country_id.code == 'AE')
                record.uae_nationals = len(uae_nationals)
                
                if record.total_employees > 0:
                    record.emiratization_percentage = (record.uae_nationals / record.total_employees) * 100
                    record.emiratization_compliant = record.emiratization_percentage >= 2
                else:
                    record.emiratization_percentage = 0
                    record.emiratization_compliant = False
            except Exception:
                record.total_employees = 0
                record.uae_nationals = 0
                record.emiratization_percentage = 0
                record.emiratization_compliant = False
    
    @api.depends('emiratization_compliant', 'wps_compliance_rate', 'mohre_compliance_rate', 
                 'minimum_wage_compliance_rate', 'leave_compliance_rate')
    def _compute_overall_compliance(self):
        """Compute overall compliance score."""
        for record in self:
            # Calculate weighted compliance score
            scores = [
                record.emiratization_percentage if record.emiratization_compliant else 0,
                record.wps_compliance_rate or 0,
                record.mohre_compliance_rate or 0,
                record.minimum_wage_compliance_rate or 0,
                record.leave_compliance_rate or 0,
            ]
            
            record.overall_compliance_score = sum(scores) / len(scores) if scores else 0
            
            # Determine status
            if record.overall_compliance_score >= 90:
                record.compliance_status = 'excellent'
            elif record.overall_compliance_score >= 75:
                record.compliance_status = 'good'
            elif record.overall_compliance_score >= 60:
                record.compliance_status = 'fair'
            else:
                record.compliance_status = 'poor'
    
    def action_refresh_compliance(self):
        """Refresh compliance data."""
        self._compute_emiratization_metrics()
        self._compute_overall_compliance()
        return True
