# -*- coding: utf-8 -*-
"""
Notification Alerts Module
Provides automated alerts for document expiry, compliance thresholds, and payroll anomalies
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta
import logging

_logger = logging.getLogger(__name__)


class NotificationAlertRule(models.Model):
    """Alert Rule Configuration for automated notifications."""
    _name = 'notification.alert.rule'
    _description = 'Notification Alert Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    alert_type = fields.Selection([
        ('document_expiry', 'Document Expiry'),
        ('compliance_threshold', 'Compliance Threshold'),
        ('payroll_anomaly', 'Payroll Anomaly'),
        ('recruitment_target', 'Recruitment Target'),
        ('cost_threshold', 'Cost Threshold'),
    ], string='Alert Type', required=True)
    
    # Document Expiry Settings
    document_type = fields.Selection([
        ('visa', 'Visa'),
        ('passport', 'Passport'),
        ('emirates_id', 'Emirates ID'),
        ('labor_card', 'Labor Card'),
        ('all', 'All Documents'),
    ], string='Document Type', default='all')
    days_before_expiry = fields.Integer(string='Days Before Expiry', default=30,
                                         help='Alert when document expires within this many days')
    
    # Compliance Threshold Settings
    compliance_threshold = fields.Float(string='Compliance Threshold %', default=90.0,
                                         help='Alert when compliance rate falls below this threshold')
    
    # Payroll Anomaly Settings
    salary_variance_threshold = fields.Float(string='Salary Variance %', default=20.0,
                                              help='Alert when salary varies more than this percentage from average')
    
    # Cost Threshold Settings
    cost_threshold = fields.Float(string='Cost Threshold', default=100000.0,
                                   help='Alert when total cost exceeds this amount')
    cost_increase_threshold = fields.Float(string='Cost Increase %', default=15.0,
                                            help='Alert when cost increases by more than this percentage')
    
    # Notification Settings
    notification_type = fields.Selection([
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('danger', 'Critical Alert'),
    ], string='Notification Level', default='warning')
    
    recipient_ids = fields.Many2many('res.users', string='Recipients',
                                      help='Users who will receive this alert')
    send_email = fields.Boolean(string='Send Email', default=True)
    
    # Scheduling
    check_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Check Frequency', default='daily')
    
    last_check_date = fields.Datetime(string='Last Check')
    
    @api.model
    def run_all_alerts(self):
        """Run all active alert rules. Called by cron job."""
        rules = self.search([('active', '=', True)])
        for rule in rules:
            try:
                rule.run_alert_check()
            except Exception as e:
                _logger.error(f"Error running alert rule {rule.name}: {e}")
        return True

    def run_alert_check(self):
        """Run alert check for this rule."""
        self.ensure_one()
        
        if self.alert_type == 'document_expiry':
            self._check_document_expiry()
        elif self.alert_type == 'compliance_threshold':
            self._check_compliance_threshold()
        elif self.alert_type == 'payroll_anomaly':
            self._check_payroll_anomaly()
        elif self.alert_type == 'recruitment_target':
            self._check_recruitment_target()
        elif self.alert_type == 'cost_threshold':
            self._check_cost_threshold()
        
        self.last_check_date = fields.Datetime.now()

    def _check_document_expiry(self):
        """Check for expiring documents and create alerts."""
        self.ensure_one()
        Employee = self.env['hr.employee']
        Notification = self.env['analytics.dashboard.notification']
        
        today = date.today()
        expiry_date = today + timedelta(days=self.days_before_expiry)
        
        employees = Employee.search([])
        expiring_docs = []
        
        for emp in employees:
            docs_to_check = []
            
            if self.document_type in ['visa', 'all'] and emp.visa_expiry:
                if today <= emp.visa_expiry <= expiry_date:
                    docs_to_check.append(('Visa', emp.visa_expiry))
                elif emp.visa_expiry < today:
                    docs_to_check.append(('Visa (EXPIRED)', emp.visa_expiry))
            
            if self.document_type in ['passport', 'all'] and emp.passport_expiry:
                if today <= emp.passport_expiry <= expiry_date:
                    docs_to_check.append(('Passport', emp.passport_expiry))
                elif emp.passport_expiry < today:
                    docs_to_check.append(('Passport (EXPIRED)', emp.passport_expiry))
            
            if self.document_type in ['emirates_id', 'all'] and emp.emirates_id_expiry:
                if today <= emp.emirates_id_expiry <= expiry_date:
                    docs_to_check.append(('Emirates ID', emp.emirates_id_expiry))
                elif emp.emirates_id_expiry < today:
                    docs_to_check.append(('Emirates ID (EXPIRED)', emp.emirates_id_expiry))
            
            if self.document_type in ['labor_card', 'all'] and emp.labor_card_expiry:
                if today <= emp.labor_card_expiry <= expiry_date:
                    docs_to_check.append(('Labor Card', emp.labor_card_expiry))
                elif emp.labor_card_expiry < today:
                    docs_to_check.append(('Labor Card (EXPIRED)', emp.labor_card_expiry))
            
            for doc_type, doc_expiry in docs_to_check:
                expiring_docs.append({
                    'employee': emp.name,
                    'employee_id': emp.id,
                    'document': doc_type,
                    'expiry_date': doc_expiry,
                    'days_left': (doc_expiry - today).days
                })
        
        if expiring_docs:
            # Create notification for each recipient
            for user in self.recipient_ids or [self.env.user]:
                # Group by urgency
                expired = [d for d in expiring_docs if d['days_left'] < 0]
                critical = [d for d in expiring_docs if 0 <= d['days_left'] <= 7]
                warning = [d for d in expiring_docs if 7 < d['days_left'] <= 30]
                
                message_parts = []
                if expired:
                    message_parts.append(f"⛔ {len(expired)} EXPIRED documents")
                if critical:
                    message_parts.append(f"🔴 {len(critical)} documents expiring within 7 days")
                if warning:
                    message_parts.append(f"🟡 {len(warning)} documents expiring within 30 days")
                
                message = "\n".join(message_parts)
                message += f"\n\nTotal: {len(expiring_docs)} documents require attention."
                
                # Add details for first 5
                message += "\n\nTop Priority:"
                for doc in sorted(expiring_docs, key=lambda x: x['days_left'])[:5]:
                    message += f"\n• {doc['employee']}: {doc['document']} - {doc['expiry_date']}"
                
                Notification.create_notification(
                    title=f"Document Expiry Alert: {len(expiring_docs)} documents",
                    message=message,
                    notification_type='danger' if expired else self.notification_type,
                    category='compliance',
                    user_id=user.id
                )
        
        return len(expiring_docs)

    def _check_compliance_threshold(self):
        """Check compliance rate against threshold."""
        self.ensure_one()
        Employee = self.env['hr.employee']
        Notification = self.env['analytics.dashboard.notification']
        
        employees = Employee.search([])
        today = date.today()
        
        compliant_count = 0
        for emp in employees:
            is_compliant = True
            
            # Check if all critical documents are valid
            if emp.visa_expiry and emp.visa_expiry < today:
                is_compliant = False
            if emp.passport_expiry and emp.passport_expiry < today:
                is_compliant = False
            if emp.emirates_id_expiry and emp.emirates_id_expiry < today:
                is_compliant = False
            
            if is_compliant:
                compliant_count += 1
        
        total = len(employees)
        compliance_rate = (compliant_count / total * 100) if total else 100
        
        if compliance_rate < self.compliance_threshold:
            for user in self.recipient_ids or [self.env.user]:
                Notification.create_notification(
                    title=f"Compliance Alert: Rate at {compliance_rate:.1f}%",
                    message=f"Compliance rate ({compliance_rate:.1f}%) has fallen below the threshold ({self.compliance_threshold}%).\n\n"
                            f"Compliant: {compliant_count}/{total} employees\n"
                            f"Non-compliant: {total - compliant_count} employees\n\n"
                            f"Please review and take immediate action.",
                    notification_type=self.notification_type,
                    category='compliance',
                    user_id=user.id
                )
        
        return compliance_rate

    def _check_payroll_anomaly(self):
        """Check for payroll anomalies."""
        self.ensure_one()
        CostCenter = self.env['employee.cost.center']
        Notification = self.env['analytics.dashboard.notification']
        
        records = CostCenter.search([])
        if not records:
            return 0
        
        salaries = [r.salary_cost for r in records if r.salary_cost > 0]
        if not salaries:
            return 0
        
        avg_salary = sum(salaries) / len(salaries)
        anomalies = []
        
        for record in records:
            if record.salary_cost > 0:
                variance = abs(record.salary_cost - avg_salary) / avg_salary * 100
                if variance > self.salary_variance_threshold:
                    anomalies.append({
                        'employee': record.employee_id.name,
                        'salary': record.salary_cost,
                        'variance': variance,
                        'direction': 'above' if record.salary_cost > avg_salary else 'below'
                    })
        
        if anomalies:
            for user in self.recipient_ids or [self.env.user]:
                message = f"Detected {len(anomalies)} salary anomalies (variance > {self.salary_variance_threshold}%):\n\n"
                message += f"Average Salary: AED {avg_salary:,.2f}\n\n"
                
                for a in anomalies[:10]:
                    message += f"• {a['employee']}: AED {a['salary']:,.2f} ({a['variance']:.1f}% {a['direction']} average)\n"
                
                Notification.create_notification(
                    title=f"Payroll Anomaly: {len(anomalies)} cases detected",
                    message=message,
                    notification_type=self.notification_type,
                    category='payroll',
                    user_id=user.id
                )
        
        return len(anomalies)

    def _check_recruitment_target(self):
        """Check recruitment targets."""
        self.ensure_one()
        # Placeholder for recruitment target checking
        return 0

    def _check_cost_threshold(self):
        """Check cost thresholds."""
        self.ensure_one()
        CostCenter = self.env['employee.cost.center']
        Notification = self.env['analytics.dashboard.notification']
        
        total_cost = sum(CostCenter.search([]).mapped('total_cost'))
        
        if total_cost > self.cost_threshold:
            for user in self.recipient_ids or [self.env.user]:
                Notification.create_notification(
                    title=f"Cost Alert: Total cost exceeds threshold",
                    message=f"Total cost (AED {total_cost:,.2f}) has exceeded the threshold (AED {self.cost_threshold:,.2f}).\n\n"
                            f"Overage: AED {total_cost - self.cost_threshold:,.2f}\n\n"
                            f"Please review cost center allocations.",
                    notification_type=self.notification_type,
                    category='cost_center',
                    user_id=user.id
                )
        
        return total_cost


class NotificationAlertCron(models.Model):
    """Extend ir.cron for alert scheduling."""
    _inherit = 'ir.cron'

    @api.model
    def _run_analytics_alerts(self):
        """Cron method to run all analytics alerts."""
        self.env['notification.alert.rule'].run_all_alerts()
        return True
