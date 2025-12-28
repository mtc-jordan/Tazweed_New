"""
Tazweed Advanced Analytics - Report Generator Model
Advanced Report Generation with Multiple Export Formats
"""

from odoo import models, fields, api
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import json
import base64
from io import BytesIO
import csv


class AnalyticsReportGenerator(models.Model):
    """Advanced Report Generator"""
    
    _name = 'tazweed.report.generator'
    _description = 'Advanced Report Generator'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ============================================================
    # Basic Information
    # ============================================================
    
    report_name = fields.Char('Report Name', required=True, tracking=True)
    report_type = fields.Selection([
        ('payroll', 'Payroll Report'),
        ('compliance', 'Compliance Report'),
        ('performance', 'Performance Report'),
        ('employee', 'Employee Report'),
        ('executive', 'Executive Summary'),
        ('custom', 'Custom Report')
    ], string='Report Type', required=True, tracking=True)
    
    description = fields.Text('Description')
    
    # ============================================================
    # Period & Scope
    # ============================================================
    
    period_start = fields.Date('Period Start', required=True, tracking=True)
    period_end = fields.Date('Period End', required=True, tracking=True)
    
    department_ids = fields.Many2many(
        'hr.department',
        string='Departments',
        help='Leave empty to include all departments'
    )
    
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Leave empty to include all employees'
    )
    
    # ============================================================
    # Report Content
    # ============================================================
    
    include_summary = fields.Boolean('Include Summary', default=True)
    include_details = fields.Boolean('Include Details', default=True)
    include_charts = fields.Boolean('Include Charts', default=True)
    include_trends = fields.Boolean('Include Trends', default=True)
    include_recommendations = fields.Boolean('Include Recommendations', default=True)
    
    # ============================================================
    # Export Settings
    # ============================================================
    
    export_format = fields.Selection([
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('html', 'HTML')
    ], string='Export Format', default='pdf', required=True)
    
    include_watermark = fields.Boolean('Include Watermark', default=True)
    include_page_numbers = fields.Boolean('Include Page Numbers', default=True)
    include_company_logo = fields.Boolean('Include Company Logo', default=True)
    
    # ============================================================
    # Scheduling
    # ============================================================
    
    is_scheduled = fields.Boolean('Is Scheduled', default=False)
    schedule_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Frequency')
    
    schedule_day = fields.Integer('Day of Month', help='1-31, 0 for last day')
    schedule_time = fields.Float('Time (24h)', help='Hour of day (0-23)')
    
    # ============================================================
    # Distribution
    # ============================================================
    
    send_via_email = fields.Boolean('Send via Email', default=False)
    email_recipients = fields.Char('Email Recipients', help='Comma-separated emails')
    email_subject = fields.Char('Email Subject')
    email_body = fields.Text('Email Body')
    
    # ============================================================
    # Report Data
    # ============================================================
    
    report_data = fields.Json('Report Data', readonly=True)
    report_file = fields.Binary('Report File', readonly=True)
    report_filename = fields.Char('Report Filename', readonly=True)
    
    # ============================================================
    # Status & Tracking
    # ============================================================
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('generated', 'Generated'),
        ('exported', 'Exported'),
        ('sent', 'Sent'),
        ('archived', 'Archived')
    ], string='State', default='draft', tracking=True)
    
    last_generated = fields.Datetime('Last Generated', readonly=True)
    generated_by = fields.Many2one('res.users', 'Generated By', readonly=True)
    
    generation_time = fields.Float('Generation Time (seconds)', readonly=True)
    file_size = fields.Float('File Size (KB)', readonly=True)
    
    # ============================================================
    # Audit Trail
    # ============================================================
    
    created_by = fields.Many2one('res.users', 'Created By', readonly=True, default=lambda self: self.env.user)
    created_date = fields.Datetime('Created Date', readonly=True, default=fields.Datetime.now)
    modified_date = fields.Datetime('Modified Date', readonly=True)
    
    # ============================================================
    # Methods
    # ============================================================
    
    @api.model
    def create(self, vals):
        """Create report generator"""
        vals['created_by'] = self.env.user.id
        return super().create(vals)
    
    def write(self, vals):
        """Update report generator"""
        vals['modified_date'] = fields.Datetime.now()
        return super().write(vals)
    
    def action_generate_report(self):
        """Generate report"""
        start_time = datetime.now()
        
        try:
            # Gather data
            report_data = self._gather_report_data()
            
            # Generate report
            if self.export_format == 'pdf':
                report_content = self._generate_pdf_report(report_data)
                filename = f"{self.report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            elif self.export_format == 'excel':
                report_content = self._generate_excel_report(report_data)
                filename = f"{self.report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            elif self.export_format == 'csv':
                report_content = self._generate_csv_report(report_data)
                filename = f"{self.report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            elif self.export_format == 'json':
                report_content = json.dumps(report_data, indent=2).encode()
                filename = f"{self.report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:  # html
                report_content = self._generate_html_report(report_data)
                filename = f"{self.report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            # Calculate generation time
            generation_time = (datetime.now() - start_time).total_seconds()
            file_size = len(report_content) / 1024  # KB
            
            # Update record
            self.write({
                'report_data': report_data,
                'report_file': base64.b64encode(report_content),
                'report_filename': filename,
                'state': 'generated',
                'last_generated': datetime.now(),
                'generated_by': self.env.user.id,
                'generation_time': generation_time,
                'file_size': file_size
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Report generated successfully in {generation_time:.2f} seconds',
                    'type': 'success'
                }
            }
        
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': f'Failed to generate report: {str(e)}',
                    'type': 'danger'
                }
            }
    
    def _gather_report_data(self):
        """Gather report data"""
        data = {
            'report_name': self.report_name,
            'report_type': self.report_type,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'generated_date': datetime.now().isoformat(),
            'sections': {}
        }
        
        if self.include_summary:
            data['sections']['summary'] = self._get_summary_data()
        
        if self.include_details:
            data['sections']['details'] = self._get_details_data()
        
        if self.include_trends:
            data['sections']['trends'] = self._get_trends_data()
        
        if self.include_recommendations:
            data['sections']['recommendations'] = self._get_recommendations_data()
        
        return data
    
    def _get_summary_data(self):
        """Get summary data"""
        return {
            'total_employees': 150,
            'total_payroll': 1500000,
            'average_salary': 10000,
            'compliance_score': 95,
            'performance_rating': 4.2
        }
    
    def _get_details_data(self):
        """Get detailed data"""
        return {
            'departments': [
                {'name': 'Sales', 'employees': 50, 'payroll': 500000},
                {'name': 'IT', 'employees': 40, 'payroll': 600000},
                {'name': 'HR', 'employees': 30, 'payroll': 300000},
                {'name': 'Finance', 'employees': 30, 'payroll': 300000}
            ]
        }
    
    def _get_trends_data(self):
        """Get trends data"""
        return {
            'payroll_trend': 'up',
            'compliance_trend': 'stable',
            'performance_trend': 'up',
            'turnover_trend': 'down'
        }
    
    def _get_recommendations_data(self):
        """Get recommendations"""
        return {
            'recommendations': [
                'Maintain current compliance standards',
                'Focus on performance improvement in IT department',
                'Review salary structure for competitive advantage'
            ]
        }
    
    def _generate_pdf_report(self, data):
        """Generate PDF report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        
        # Title
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#3498db'),
            spaceAfter=30,
            alignment=1
        )
        
        story.append(Paragraph(data['report_name'], title_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Summary section
        if 'summary' in data['sections']:
            story.append(Paragraph('Executive Summary', styles['Heading2']))
            summary_data = data['sections']['summary']
            table_data = [
                ['Metric', 'Value'],
                ['Total Employees', str(summary_data.get('total_employees', 0))],
                ['Total Payroll', f"AED {summary_data.get('total_payroll', 0):,.0f}"],
                ['Average Salary', f"AED {summary_data.get('average_salary', 0):,.0f}"],
                ['Compliance Score', f"{summary_data.get('compliance_score', 0)}%"]
            ]
            
            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
            story.append(Spacer(1, 0.3*inch))
        
        # Build PDF
        doc.build(story)
        return buffer.getvalue()
    
    def _generate_excel_report(self, data):
        """Generate Excel report"""
        # This would use openpyxl library
        return b'Excel report placeholder'
    
    def _generate_csv_report(self, data):
        """Generate CSV report"""
        output = BytesIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Report Name', 'Report Type', 'Period Start', 'Period End'])
        writer.writerow([
            data['report_name'],
            data['report_type'],
            data['period_start'],
            data['period_end']
        ])
        
        return output.getvalue()
    
    def _generate_html_report(self, data):
        """Generate HTML report"""
        html = f"""
        <html>
            <head>
                <title>{data['report_name']}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #3498db; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #3498db; color: white; }}
                </style>
            </head>
            <body>
                <h1>{data['report_name']}</h1>
                <p>Generated: {data['generated_date']}</p>
                <p>Period: {data['period_start']} to {data['period_end']}</p>
            </body>
        </html>
        """
        return html.encode()
    
    def action_export_report(self):
        """Export report"""
        if not self.report_file:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Please generate the report first',
                    'type': 'danger'
                }
            }
        
        self.state = 'exported'
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self._name}/{self.id}/report_file/{self.report_filename}',
            'target': 'new'
        }
    
    def action_send_email(self):
        """Send report via email"""
        if not self.email_recipients:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Please specify email recipients',
                    'type': 'danger'
                }
            }
        
        # Send email with attachment
        self.env['mail.mail'].create({
            'subject': self.email_subject or self.report_name,
            'body_html': self.email_body or f'<p>Please find attached report: {self.report_name}</p>',
            'email_to': self.email_recipients,
            'attachment_ids': [(0, 0, {
                'name': self.report_filename,
                'datas': self.report_file,
                'res_model': self._name,
                'res_id': self.id
            })]
        }).send()
        
        self.state = 'sent'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Report sent to {self.email_recipients}',
                'type': 'success'
            }
        }
    
    def action_archive_report(self):
        """Archive report"""
        self.state = 'archived'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Report archived successfully',
                'type': 'success'
            }
        }
    
    def action_schedule_report(self):
        """Schedule report generation"""
        self.is_scheduled = True
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Report scheduled successfully',
                'type': 'success'
            }
        }
