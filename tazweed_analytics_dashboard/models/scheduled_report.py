# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging

_logger = logging.getLogger(__name__)


class ScheduledReport(models.Model):
    """Scheduled Report for automated email delivery of analytics reports."""
    
    _name = 'analytics.scheduled.report'
    _description = 'Scheduled Analytics Report'
    _rec_name = 'name'
    _order = 'next_run_date'
    
    name = fields.Char(string='Report Name', required=True)
    active = fields.Boolean(string='Active', default=True)
    
    # Report Type
    report_type = fields.Selection([
        ('cost_center', 'Cost Center Report'),
        ('recruitment', 'Recruitment Report'),
        ('compliance', 'Compliance Report'),
        ('payroll', 'Payroll Report'),
        ('executive', 'Executive Summary'),
        ('custom', 'Custom Report'),
    ], string='Report Type', required=True, default='executive')
    
    # Schedule Settings
    frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
    ], string='Frequency', required=True, default='weekly')
    
    day_of_week = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], string='Day of Week', default='0')
    
    day_of_month = fields.Integer(string='Day of Month', default=1,
                                   help='Day of month for monthly/quarterly reports')
    
    time_of_day = fields.Float(string='Time (24h)', default=8.0,
                                help='Time to send report in 24-hour format')
    
    # Date Range
    date_range_type = fields.Selection([
        ('last_7_days', 'Last 7 Days'),
        ('last_30_days', 'Last 30 Days'),
        ('last_month', 'Last Month'),
        ('last_quarter', 'Last Quarter'),
        ('last_year', 'Last Year'),
        ('ytd', 'Year to Date'),
        ('custom', 'Custom Range'),
    ], string='Date Range', default='last_month')
    
    custom_date_from = fields.Date(string='Custom From Date')
    custom_date_to = fields.Date(string='Custom To Date')
    
    # Recipients
    recipient_ids = fields.Many2many('res.users', 
                                      'scheduled_report_user_rel',
                                      'report_id', 'user_id',
                                      string='Recipients')
    additional_emails = fields.Text(string='Additional Emails',
                                     help='Additional email addresses, one per line')
    
    # Filters
    department_ids = fields.Many2many('hr.department',
                                       'scheduled_report_department_rel',
                                       'report_id', 'department_id',
                                       string='Departments')
    client_ids = fields.Many2many('tazweed.client',
                                   'scheduled_report_client_rel',
                                   'report_id', 'client_id',
                                   string='Clients')
    
    # Format
    format = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('html', 'HTML Email'),
    ], string='Format', default='pdf')
    
    include_charts = fields.Boolean(string='Include Charts', default=True)
    include_details = fields.Boolean(string='Include Details', default=True)
    
    # Execution Info
    last_run_date = fields.Datetime(string='Last Run', readonly=True)
    next_run_date = fields.Datetime(string='Next Run', compute='_compute_next_run_date', store=True)
    last_run_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    ], string='Last Status', default='pending')
    last_run_message = fields.Text(string='Last Run Message', readonly=True)
    
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    
    @api.depends('frequency', 'day_of_week', 'day_of_month', 'time_of_day', 'last_run_date')
    def _compute_next_run_date(self):
        """Compute the next scheduled run date."""
        for record in self:
            now = datetime.now()
            
            if record.frequency == 'daily':
                next_date = now.replace(hour=int(record.time_of_day), minute=0, second=0, microsecond=0)
                if next_date <= now:
                    next_date += timedelta(days=1)
            
            elif record.frequency == 'weekly':
                target_day = int(record.day_of_week or 0)
                days_ahead = target_day - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                next_date = now + timedelta(days=days_ahead)
                next_date = next_date.replace(hour=int(record.time_of_day), minute=0, second=0, microsecond=0)
            
            elif record.frequency == 'monthly':
                day = min(record.day_of_month or 1, 28)
                next_date = now.replace(day=day, hour=int(record.time_of_day), minute=0, second=0, microsecond=0)
                if next_date <= now:
                    next_date += relativedelta(months=1)
            
            elif record.frequency == 'quarterly':
                day = min(record.day_of_month or 1, 28)
                # Find next quarter start
                quarter_month = ((now.month - 1) // 3 + 1) * 3 + 1
                if quarter_month > 12:
                    quarter_month = 1
                    year = now.year + 1
                else:
                    year = now.year
                next_date = now.replace(year=year, month=quarter_month, day=day, 
                                        hour=int(record.time_of_day), minute=0, second=0, microsecond=0)
            else:
                next_date = now + timedelta(days=1)
            
            record.next_run_date = next_date
    
    def _get_date_range(self):
        """Get the date range for the report."""
        self.ensure_one()
        today = fields.Date.today()
        
        if self.date_range_type == 'last_7_days':
            return (today - timedelta(days=7), today)
        elif self.date_range_type == 'last_30_days':
            return (today - timedelta(days=30), today)
        elif self.date_range_type == 'last_month':
            first_day = today.replace(day=1) - relativedelta(months=1)
            last_day = today.replace(day=1) - timedelta(days=1)
            return (first_day, last_day)
        elif self.date_range_type == 'last_quarter':
            quarter = (today.month - 1) // 3
            if quarter == 0:
                start = today.replace(year=today.year-1, month=10, day=1)
                end = today.replace(year=today.year-1, month=12, day=31)
            else:
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                start = today.replace(month=start_month, day=1)
                end = today.replace(month=end_month, day=1) + relativedelta(months=1) - timedelta(days=1)
            return (start, end)
        elif self.date_range_type == 'last_year':
            return (today.replace(year=today.year-1, month=1, day=1),
                    today.replace(year=today.year-1, month=12, day=31))
        elif self.date_range_type == 'ytd':
            return (today.replace(month=1, day=1), today)
        elif self.date_range_type == 'custom':
            return (self.custom_date_from or today - timedelta(days=30),
                    self.custom_date_to or today)
        else:
            return (today - timedelta(days=30), today)
    
    def _get_recipients(self):
        """Get list of email recipients."""
        self.ensure_one()
        emails = []
        
        # Add user emails
        for user in self.recipient_ids:
            if user.email:
                emails.append(user.email)
        
        # Add additional emails
        if self.additional_emails:
            for email in self.additional_emails.split('\n'):
                email = email.strip()
                if email and '@' in email:
                    emails.append(email)
        
        return list(set(emails))  # Remove duplicates
    
    def action_run_now(self):
        """Manually run the report now."""
        self.ensure_one()
        return self._execute_report()
    
    def action_preview(self):
        """Preview the report."""
        self.ensure_one()
        date_from, date_to = self._get_date_range()
        
        # Open the appropriate dashboard with date filters
        if self.report_type == 'cost_center':
            return {
                'name': _('Cost Center Preview'),
                'type': 'ir.actions.act_window',
                'res_model': 'employee.cost.center.dashboard',
                'view_mode': 'form',
                'context': {
                    'default_date_from': date_from,
                    'default_date_to': date_to,
                },
                'target': 'new',
            }
        elif self.report_type == 'recruitment':
            return {
                'name': _('Recruitment Preview'),
                'type': 'ir.actions.act_window',
                'res_model': 'recruitment.analytics.dashboard',
                'view_mode': 'form',
                'context': {
                    'default_date_from': date_from,
                    'default_date_to': date_to,
                },
                'target': 'new',
            }
        elif self.report_type == 'compliance':
            return {
                'name': _('Compliance Preview'),
                'type': 'ir.actions.act_window',
                'res_model': 'compliance.analytics.dashboard',
                'view_mode': 'form',
                'context': {
                    'default_date_from': date_from,
                    'default_date_to': date_to,
                },
                'target': 'new',
            }
        elif self.report_type == 'payroll':
            return {
                'name': _('Payroll Preview'),
                'type': 'ir.actions.act_window',
                'res_model': 'payroll.analytics.dashboard',
                'view_mode': 'form',
                'context': {
                    'default_date_from': date_from,
                    'default_date_to': date_to,
                },
                'target': 'new',
            }
        else:
            return {
                'name': _('Analytics Preview'),
                'type': 'ir.actions.act_window',
                'res_model': 'tazweed.analytics.dashboard',
                'view_mode': 'form',
                'context': {
                    'default_date_from': date_from,
                    'default_date_to': date_to,
                },
                'target': 'new',
            }
    
    def _execute_report(self):
        """Execute the scheduled report."""
        self.ensure_one()
        
        try:
            date_from, date_to = self._get_date_range()
            recipients = self._get_recipients()
            
            if not recipients:
                raise UserError(_('No recipients configured for this report.'))
            
            # Generate report data based on type
            report_data = self._generate_report_data(date_from, date_to)
            
            # Send email
            self._send_report_email(recipients, report_data, date_from, date_to)
            
            # Update status
            self.write({
                'last_run_date': fields.Datetime.now(),
                'last_run_status': 'success',
                'last_run_message': _('Report sent successfully to %d recipients.') % len(recipients),
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Report Sent'),
                    'message': _('Report sent successfully to %d recipients.') % len(recipients),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error('Failed to execute scheduled report %s: %s', self.name, str(e))
            self.write({
                'last_run_date': fields.Datetime.now(),
                'last_run_status': 'failed',
                'last_run_message': str(e),
            })
            raise UserError(_('Failed to generate report: %s') % str(e))
    
    def _generate_report_data(self, date_from, date_to):
        """Generate report data based on report type."""
        self.ensure_one()
        
        data = {
            'report_name': self.name,
            'report_type': self.report_type,
            'date_from': str(date_from),
            'date_to': str(date_to),
            'generated_at': str(fields.Datetime.now()),
            'company': self.company_id.name,
        }
        
        if self.report_type == 'cost_center':
            data['content'] = self._get_cost_center_data(date_from, date_to)
        elif self.report_type == 'recruitment':
            data['content'] = self._get_recruitment_data(date_from, date_to)
        elif self.report_type == 'compliance':
            data['content'] = self._get_compliance_data(date_from, date_to)
        elif self.report_type == 'payroll':
            data['content'] = self._get_payroll_data(date_from, date_to)
        else:
            data['content'] = self._get_executive_data(date_from, date_to)
        
        return data
    
    def _get_cost_center_data(self, date_from, date_to):
        """Get cost center report data."""
        CostCenter = self.env['employee.cost.center'].sudo()
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]
        
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        if self.client_ids:
            domain.append(('client_id', 'in', self.client_ids.ids))
        
        records = CostCenter.search(domain)
        
        return {
            'total_records': len(records),
            'total_cost': sum(records.mapped('total_cost')),
            'total_revenue': sum(records.mapped('revenue')),
            'total_margin': sum(records.mapped('gross_margin')),
        }
    
    def _get_recruitment_data(self, date_from, date_to):
        """Get recruitment report data."""
        Candidate = self.env['tazweed.candidate'].sudo()
        Placement = self.env['tazweed.placement'].sudo()
        
        candidates = Candidate.search_count([
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
        ]) if 'tazweed.candidate' in self.env else 0
        
        placements = Placement.search_count([
            ('create_date', '>=', date_from),
            ('create_date', '<=', date_to),
        ]) if 'tazweed.placement' in self.env else 0
        
        return {
            'total_candidates': candidates,
            'total_placements': placements,
            'conversion_rate': (placements / candidates * 100) if candidates > 0 else 0,
        }
    
    def _get_compliance_data(self, date_from, date_to):
        """Get compliance report data."""
        today = fields.Date.today()
        EmployeeDocument = self.env['tazweed.employee.document'].sudo()
        
        if 'tazweed.employee.document' in self.env:
            total = EmployeeDocument.search_count([])
            expired = EmployeeDocument.search_count([('expiry_date', '<', today)])
            expiring = EmployeeDocument.search_count([
                ('expiry_date', '>=', today),
                ('expiry_date', '<=', today + timedelta(days=30)),
            ])
            valid = total - expired
            
            return {
                'total_documents': total,
                'valid_documents': valid,
                'expired_documents': expired,
                'expiring_soon': expiring,
                'compliance_rate': (valid / total * 100) if total > 0 else 0,
            }
        
        return {'total_documents': 0, 'compliance_rate': 0}
    
    def _get_payroll_data(self, date_from, date_to):
        """Get payroll report data."""
        Payslip = self.env['hr.payslip'].sudo()
        
        if 'hr.payslip' in self.env:
            payslips = Payslip.search([
                ('date_from', '>=', date_from),
                ('date_to', '<=', date_to),
            ])
            
            gross = 0
            net = 0
            for slip in payslips:
                for line in slip.line_ids:
                    if line.code == 'GROSS':
                        gross += line.total or 0
                    elif line.code == 'NET':
                        net += line.total or 0
            
            return {
                'total_payslips': len(payslips),
                'total_gross': gross,
                'total_net': net,
                'total_deductions': gross - net,
            }
        
        return {'total_payslips': 0, 'total_gross': 0, 'total_net': 0}
    
    def _get_executive_data(self, date_from, date_to):
        """Get executive summary data."""
        return {
            'cost_center': self._get_cost_center_data(date_from, date_to),
            'recruitment': self._get_recruitment_data(date_from, date_to),
            'compliance': self._get_compliance_data(date_from, date_to),
            'payroll': self._get_payroll_data(date_from, date_to),
        }
    
    def _send_report_email(self, recipients, report_data, date_from, date_to):
        """Send the report via email."""
        self.ensure_one()
        
        # Build email content
        subject = _('%s - %s to %s') % (self.name, date_from, date_to)
        
        body_html = self._build_email_body(report_data)
        
        # Create and send email
        mail_values = {
            'subject': subject,
            'body_html': body_html,
            'email_to': ', '.join(recipients),
            'auto_delete': True,
        }
        
        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.send()
    
    def _build_email_body(self, report_data):
        """Build HTML email body."""
        content = report_data.get('content', {})
        
        html = """
        <div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
            <h2 style="color: #2196F3; border-bottom: 2px solid #2196F3; padding-bottom: 10px;">
                📊 {report_name}
            </h2>
            <p><strong>Period:</strong> {date_from} to {date_to}</p>
            <p><strong>Generated:</strong> {generated_at}</p>
            <p><strong>Company:</strong> {company}</p>
            <hr/>
        """.format(**report_data)
        
        if self.report_type == 'cost_center':
            html += self._build_cost_center_html(content)
        elif self.report_type == 'recruitment':
            html += self._build_recruitment_html(content)
        elif self.report_type == 'compliance':
            html += self._build_compliance_html(content)
        elif self.report_type == 'payroll':
            html += self._build_payroll_html(content)
        else:
            html += self._build_executive_html(content)
        
        html += """
            <hr/>
            <p style="color: #666; font-size: 12px;">
                This is an automated report from Tazweed Analytics Dashboard.
            </p>
        </div>
        """
        
        return html
    
    def _build_cost_center_html(self, content):
        """Build cost center report HTML."""
        return """
        <h3>💰 Cost Center Summary</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #E3F2FD;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Records</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_records}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Cost</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_cost:,.2f}</td>
            </tr>
            <tr style="background: #E8F5E9;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Revenue</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_revenue:,.2f}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Gross Margin</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_margin:,.2f}</td>
            </tr>
        </table>
        """.format(**content)
    
    def _build_recruitment_html(self, content):
        """Build recruitment report HTML."""
        return """
        <h3>👥 Recruitment Summary</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #E3F2FD;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Candidates</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_candidates}</td>
            </tr>
            <tr style="background: #E8F5E9;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Placements</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_placements}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Conversion Rate</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{conversion_rate:.1f}%</td>
            </tr>
        </table>
        """.format(**content)
    
    def _build_compliance_html(self, content):
        """Build compliance report HTML."""
        return """
        <h3>🛡️ Compliance Summary</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #E3F2FD;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Documents</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_documents}</td>
            </tr>
            <tr style="background: #E8F5E9;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Valid Documents</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{valid_documents}</td>
            </tr>
            <tr style="background: #FFEBEE;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Expired Documents</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{expired_documents}</td>
            </tr>
            <tr style="background: #FFF3E0;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Expiring Soon</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{expiring_soon}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Compliance Rate</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{compliance_rate:.1f}%</td>
            </tr>
        </table>
        """.format(**content)
    
    def _build_payroll_html(self, content):
        """Build payroll report HTML."""
        return """
        <h3>💵 Payroll Summary</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #E3F2FD;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Payslips</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_payslips}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Gross</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_gross:,.2f}</td>
            </tr>
            <tr style="background: #E8F5E9;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Net</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_net:,.2f}</td>
            </tr>
            <tr style="background: #FFEBEE;">
                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Total Deductions</strong></td>
                <td style="padding: 10px; border: 1px solid #ddd;">{total_deductions:,.2f}</td>
            </tr>
        </table>
        """.format(**content)
    
    def _build_executive_html(self, content):
        """Build executive summary HTML."""
        html = "<h3>📈 Executive Summary</h3>"
        
        if 'cost_center' in content:
            html += self._build_cost_center_html(content['cost_center'])
        if 'recruitment' in content:
            html += self._build_recruitment_html(content['recruitment'])
        if 'compliance' in content:
            html += self._build_compliance_html(content['compliance'])
        if 'payroll' in content:
            html += self._build_payroll_html(content['payroll'])
        
        return html
    
    @api.model
    def _cron_execute_scheduled_reports(self):
        """Cron job to execute scheduled reports."""
        now = fields.Datetime.now()
        reports = self.search([
            ('active', '=', True),
            ('next_run_date', '<=', now),
        ])
        
        for report in reports:
            try:
                report._execute_report()
            except Exception as e:
                _logger.error('Failed to execute scheduled report %s: %s', report.name, str(e))
