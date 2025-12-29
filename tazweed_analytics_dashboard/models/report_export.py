# -*- coding: utf-8 -*-
"""
Report Export Module
Provides PDF and Excel export functionality for analytics dashboards
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
from datetime import datetime, date, timedelta
import logging

_logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    _logger.warning("reportlab not installed. PDF export will be limited.")

try:
    import xlsxwriter
    XLSXWRITER_AVAILABLE = True
except ImportError:
    XLSXWRITER_AVAILABLE = False
    _logger.warning("xlsxwriter not installed. Excel export will be limited.")


class ReportExportMixin(models.AbstractModel):
    """Mixin class providing export functionality for dashboard models."""
    _name = 'report.export.mixin'
    _description = 'Report Export Mixin'

    def _get_report_data(self):
        """Override in child classes to provide report data."""
        return {
            'title': 'Analytics Report',
            'subtitle': '',
            'date': fields.Date.today(),
            'summary': {},
            'tables': [],
            'charts': [],
        }

    def _generate_pdf_report(self, data):
        """Generate PDF report from data."""
        if not REPORTLAB_AVAILABLE:
            raise UserError(_("PDF generation requires reportlab library. Please install it."))
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#667eea')
        ))
        styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.gray
        ))
        styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#333333')
        ))
        styles.add(ParagraphStyle(
            name='KPIValue',
            parent=styles['Normal'],
            fontSize=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#667eea')
        ))
        
        elements = []
        
        # Title
        elements.append(Paragraph(data.get('title', 'Analytics Report'), styles['CustomTitle']))
        
        # Subtitle with date
        subtitle = data.get('subtitle', '')
        report_date = data.get('date', fields.Date.today())
        if isinstance(report_date, str):
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        elements.append(Paragraph(f"{subtitle}<br/>Generated: {report_date.strftime('%B %d, %Y')}", styles['CustomSubtitle']))
        elements.append(Spacer(1, 20))
        
        # Summary KPIs
        summary = data.get('summary', {})
        if summary:
            elements.append(Paragraph("Key Performance Indicators", styles['SectionHeader']))
            
            kpi_data = []
            kpi_row = []
            for key, value in summary.items():
                kpi_row.append([
                    Paragraph(str(value), styles['KPIValue']),
                    Paragraph(key.replace('_', ' ').title(), styles['Normal'])
                ])
                if len(kpi_row) == 4:
                    kpi_data.append(kpi_row)
                    kpi_row = []
            if kpi_row:
                kpi_data.append(kpi_row)
            
            if kpi_data:
                # Flatten for table
                flat_data = []
                for row in kpi_data:
                    value_row = []
                    label_row = []
                    for cell in row:
                        value_row.append(cell[0])
                        label_row.append(cell[1])
                    flat_data.append(value_row)
                    flat_data.append(label_row)
                
                kpi_table = Table(flat_data, colWidths=[130] * 4)
                kpi_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                    ('TOPPADDING', (0, 0), (-1, -1), 10),
                ]))
                elements.append(kpi_table)
                elements.append(Spacer(1, 20))
        
        # Data Tables
        for table_data in data.get('tables', []):
            table_title = table_data.get('title', 'Data')
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            
            if headers and rows:
                elements.append(Paragraph(table_title, styles['SectionHeader']))
                
                table_content = [headers] + rows
                col_widths = [500 / len(headers)] * len(headers)
                
                t = Table(table_content, colWidths=col_widths)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 20))
        
        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            f"© {datetime.now().year} Tazweed Analytics Dashboard - Confidential",
            ParagraphStyle(name='Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.gray)
        ))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def _generate_excel_report(self, data):
        """Generate Excel report from data."""
        if not XLSXWRITER_AVAILABLE:
            raise UserError(_("Excel generation requires xlsxwriter library. Please install it."))
        
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        
        # Formats
        title_format = workbook.add_format({
            'bold': True, 'font_size': 18, 'font_color': '#667eea',
            'align': 'center', 'valign': 'vcenter'
        })
        header_format = workbook.add_format({
            'bold': True, 'font_size': 11, 'font_color': 'white',
            'bg_color': '#667eea', 'align': 'center', 'valign': 'vcenter',
            'border': 1
        })
        cell_format = workbook.add_format({
            'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1
        })
        number_format = workbook.add_format({
            'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1,
            'num_format': '#,##0.00'
        })
        kpi_value_format = workbook.add_format({
            'bold': True, 'font_size': 14, 'font_color': '#667eea',
            'align': 'center', 'valign': 'vcenter'
        })
        kpi_label_format = workbook.add_format({
            'font_size': 10, 'font_color': '#666666',
            'align': 'center', 'valign': 'vcenter'
        })
        
        # Summary Sheet
        summary_sheet = workbook.add_worksheet('Summary')
        summary_sheet.set_column('A:D', 20)
        
        # Title
        summary_sheet.merge_range('A1:D1', data.get('title', 'Analytics Report'), title_format)
        summary_sheet.set_row(0, 30)
        
        # Date
        report_date = data.get('date', fields.Date.today())
        if isinstance(report_date, str):
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        summary_sheet.merge_range('A2:D2', f"Generated: {report_date.strftime('%B %d, %Y')}", 
                                   workbook.add_format({'align': 'center', 'font_color': '#666666'}))
        
        # KPIs
        row = 4
        summary = data.get('summary', {})
        col = 0
        for key, value in summary.items():
            summary_sheet.write(row, col, str(value), kpi_value_format)
            summary_sheet.write(row + 1, col, key.replace('_', ' ').title(), kpi_label_format)
            col += 1
            if col >= 4:
                col = 0
                row += 3
        
        # Data Sheets
        for idx, table_data in enumerate(data.get('tables', [])):
            table_title = table_data.get('title', f'Data {idx + 1}')
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])
            
            # Create sheet with safe name
            sheet_name = table_title[:31].replace('/', '-').replace('\\', '-')
            sheet = workbook.add_worksheet(sheet_name)
            
            # Set column widths
            for col_idx in range(len(headers)):
                sheet.set_column(col_idx, col_idx, 15)
            
            # Headers
            for col_idx, header in enumerate(headers):
                sheet.write(0, col_idx, header, header_format)
            
            # Data rows
            for row_idx, row_data in enumerate(rows):
                for col_idx, cell_value in enumerate(row_data):
                    if isinstance(cell_value, (int, float)):
                        sheet.write(row_idx + 1, col_idx, cell_value, number_format)
                    else:
                        sheet.write(row_idx + 1, col_idx, str(cell_value), cell_format)
        
        workbook.close()
        buffer.seek(0)
        return buffer.getvalue()

    def action_export_pdf(self):
        """Export dashboard data to PDF."""
        self.ensure_one()
        data = self._get_report_data()
        pdf_content = self._generate_pdf_report(data)
        
        # Create attachment
        filename = f"{data.get('title', 'Report').replace(' ', '_')}_{fields.Date.today()}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_export_excel(self):
        """Export dashboard data to Excel."""
        self.ensure_one()
        data = self._get_report_data()
        excel_content = self._generate_excel_report(data)
        
        # Create attachment
        filename = f"{data.get('title', 'Report').replace(' ', '_')}_{fields.Date.today()}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class CostCenterDashboardExport(models.Model):
    """Extend Cost Center Dashboard with export functionality."""
    _inherit = 'employee.cost.center.dashboard'

    def _get_report_data(self):
        """Get cost center report data."""
        self.ensure_one()
        
        # Get dashboard data
        dashboard_data = self.get_dashboard_data()
        
        # Build summary
        summary = {
            'total_employees': dashboard_data.get('total_employees', 0),
            'total_cost': f"AED {dashboard_data.get('total_cost', 0):,.2f}",
            'total_revenue': f"AED {dashboard_data.get('total_revenue', 0):,.2f}",
            'gross_margin': f"AED {dashboard_data.get('gross_margin', 0):,.2f}",
            'margin_percent': f"{dashboard_data.get('margin_percent', 0):.1f}%",
            'avg_cost_per_employee': f"AED {dashboard_data.get('avg_cost_per_employee', 0):,.2f}",
        }
        
        # Build cost breakdown table
        cost_breakdown = dashboard_data.get('cost_breakdown', {})
        cost_table = {
            'title': 'Cost Breakdown',
            'headers': ['Category', 'Amount (AED)'],
            'rows': [
                ['Salary Cost', cost_breakdown.get('salary', 0)],
                ['Benefits Cost', cost_breakdown.get('benefits', 0)],
                ['Compliance Cost', cost_breakdown.get('compliance', 0)],
                ['Overhead Cost', cost_breakdown.get('overhead', 0)],
            ]
        }
        
        # Get detailed cost center records
        records = self.env['employee.cost.center'].search([])
        detail_table = {
            'title': 'Cost Center Details',
            'headers': ['Employee', 'Department', 'Total Cost', 'Revenue', 'Margin'],
            'rows': [[
                r.employee_id.name or 'N/A',
                r.department_id.name or 'N/A',
                r.total_cost,
                r.revenue,
                r.gross_margin
            ] for r in records[:50]]  # Limit to 50 records
        }
        
        return {
            'title': f'Cost Center Report - {self.name}',
            'subtitle': 'Employee Cost Analysis',
            'date': fields.Date.today(),
            'summary': summary,
            'tables': [cost_table, detail_table],
        }

    def action_export_pdf(self):
        """Export cost center dashboard to PDF."""
        mixin = self.env['report.export.mixin']
        data = self._get_report_data()
        pdf_content = mixin._generate_pdf_report(data)
        
        filename = f"Cost_Center_Report_{fields.Date.today()}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_export_excel(self):
        """Export cost center dashboard to Excel."""
        mixin = self.env['report.export.mixin']
        data = self._get_report_data()
        excel_content = mixin._generate_excel_report(data)
        
        filename = f"Cost_Center_Report_{fields.Date.today()}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class RecruitmentDashboardExport(models.Model):
    """Extend Recruitment Dashboard with export functionality."""
    _inherit = 'recruitment.analytics.dashboard'

    def _get_report_data(self):
        """Get recruitment report data."""
        self.ensure_one()
        dashboard_data = self.get_dashboard_data()
        summary_data = dashboard_data.get('summary', {})
        
        summary = {
            'total_candidates': summary_data.get('total_candidates', 0),
            'active_candidates': summary_data.get('active_candidates', 0),
            'total_placements': summary_data.get('total_placements', 0),
            'conversion_rate': f"{summary_data.get('conversion_rate', 0):.1f}%",
        }
        
        # Pipeline table
        pipeline = dashboard_data.get('pipeline', [])
        pipeline_table = {
            'title': 'Recruitment Pipeline',
            'headers': ['Stage', 'Count'],
            'rows': [[p.get('stage', ''), p.get('count', 0)] for p in pipeline]
        }
        
        return {
            'title': f'Recruitment Report - {self.name}',
            'subtitle': 'Recruitment Analytics',
            'date': fields.Date.today(),
            'summary': summary,
            'tables': [pipeline_table],
        }

    def action_export_pdf(self):
        """Export recruitment dashboard to PDF."""
        mixin = self.env['report.export.mixin']
        data = self._get_report_data()
        pdf_content = mixin._generate_pdf_report(data)
        
        filename = f"Recruitment_Report_{fields.Date.today()}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_export_excel(self):
        """Export recruitment dashboard to Excel."""
        mixin = self.env['report.export.mixin']
        data = self._get_report_data()
        excel_content = mixin._generate_excel_report(data)
        
        filename = f"Recruitment_Report_{fields.Date.today()}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class ComplianceDashboardExport(models.Model):
    """Extend Compliance Dashboard with export functionality."""
    _inherit = 'compliance.analytics.dashboard'

    def action_export_pdf(self):
        """Export compliance dashboard to PDF."""
        mixin = self.env['report.export.mixin']
        dashboard_data = self.get_dashboard_data()
        summary_data = dashboard_data.get('summary', {})
        
        data = {
            'title': f'Compliance Report - {self.name}',
            'subtitle': 'Document Compliance Analytics',
            'date': fields.Date.today(),
            'summary': {
                'total_documents': summary_data.get('total_documents', 0),
                'valid_documents': summary_data.get('valid_documents', 0),
                'expired_documents': summary_data.get('expired_documents', 0),
                'expiring_soon': summary_data.get('expiring_soon', 0),
                'compliance_rate': f"{summary_data.get('compliance_rate', 0):.1f}%",
            },
            'tables': [],
        }
        
        pdf_content = mixin._generate_pdf_report(data)
        
        filename = f"Compliance_Report_{fields.Date.today()}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_export_excel(self):
        """Export compliance dashboard to Excel."""
        mixin = self.env['report.export.mixin']
        dashboard_data = self.get_dashboard_data()
        summary_data = dashboard_data.get('summary', {})
        
        data = {
            'title': f'Compliance Report - {self.name}',
            'subtitle': 'Document Compliance Analytics',
            'date': fields.Date.today(),
            'summary': {
                'total_documents': summary_data.get('total_documents', 0),
                'valid_documents': summary_data.get('valid_documents', 0),
                'expired_documents': summary_data.get('expired_documents', 0),
                'expiring_soon': summary_data.get('expiring_soon', 0),
                'compliance_rate': f"{summary_data.get('compliance_rate', 0):.1f}%",
            },
            'tables': [],
        }
        
        excel_content = mixin._generate_excel_report(data)
        
        filename = f"Compliance_Report_{fields.Date.today()}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


class PayrollDashboardExport(models.Model):
    """Extend Payroll Dashboard with export functionality."""
    _inherit = 'payroll.analytics.dashboard'

    def action_export_pdf(self):
        """Export payroll dashboard to PDF."""
        mixin = self.env['report.export.mixin']
        dashboard_data = self.get_dashboard_data()
        summary_data = dashboard_data.get('summary', {})
        
        data = {
            'title': f'Payroll Report - {self.name}',
            'subtitle': 'Payroll Analytics',
            'date': fields.Date.today(),
            'summary': {
                'total_gross': f"AED {summary_data.get('total_gross', 0):,.2f}",
                'total_net': f"AED {summary_data.get('total_net', 0):,.2f}",
                'total_deductions': f"AED {summary_data.get('total_deductions', 0):,.2f}",
                'avg_salary': f"AED {summary_data.get('avg_salary', 0):,.2f}",
            },
            'tables': [],
        }
        
        pdf_content = mixin._generate_pdf_report(data)
        
        filename = f"Payroll_Report_{fields.Date.today()}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_export_excel(self):
        """Export payroll dashboard to Excel."""
        mixin = self.env['report.export.mixin']
        dashboard_data = self.get_dashboard_data()
        summary_data = dashboard_data.get('summary', {})
        
        data = {
            'title': f'Payroll Report - {self.name}',
            'subtitle': 'Payroll Analytics',
            'date': fields.Date.today(),
            'summary': {
                'total_gross': summary_data.get('total_gross', 0),
                'total_net': summary_data.get('total_net', 0),
                'total_deductions': summary_data.get('total_deductions', 0),
                'avg_salary': summary_data.get('avg_salary', 0),
            },
            'tables': [],
        }
        
        excel_content = mixin._generate_excel_report(data)
        
        filename = f"Payroll_Report_{fields.Date.today()}.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(excel_content),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
