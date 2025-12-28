# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta


class WPSDashboard(models.AbstractModel):
    """WPS Dashboard Data Provider"""
    _name = 'tazweed.wps.dashboard'
    _description = 'WPS Dashboard'

    @api.model
    def get_wps_dashboard_data(self):
        """Get WPS dashboard data"""
        company = self.env.company
        today = date.today()
        current_month = str(today.month).zfill(2)
        current_year = str(today.year)
        
        # WPS Files
        WPSFile = self.env['tazweed.wps.file']
        all_files = WPSFile.search([('company_id', '=', company.id)])
        
        draft_files = all_files.filtered(lambda f: f.state == 'draft')
        generated_files = all_files.filtered(lambda f: f.state == 'generated')
        submitted_files = all_files.filtered(lambda f: f.state == 'submitted')
        processed_files = all_files.filtered(lambda f: f.state == 'processed')
        rejected_files = all_files.filtered(lambda f: f.state == 'rejected')
        
        # Current month files
        current_month_files = all_files.filtered(
            lambda f: f.period_month == current_month and f.period_year == current_year
        )
        
        # Compliance
        WPSCompliance = self.env['tazweed.wps.compliance']
        compliance_reports = WPSCompliance.search([
            ('company_id', '=', company.id),
        ], order='period_year desc, period_month desc', limit=12)
        
        latest_compliance = compliance_reports[0] if compliance_reports else None
        
        # Employees
        total_employees = self.env['hr.employee'].search_count([
            ('company_id', '=', company.id),
            ('contract_id', '!=', False),
        ])
        
        # Banks
        total_banks = self.env['tazweed.wps.bank'].search_count([('is_wps_enabled', '=', True)])
        
        # Monthly trend (last 6 months)
        monthly_trend = []
        for i in range(5, -1, -1):
            month_date = today - relativedelta(months=i)
            month = str(month_date.month).zfill(2)
            year = str(month_date.year)
            
            month_files = all_files.filtered(
                lambda f: f.period_month == month and f.period_year == year
            )
            processed = month_files.filtered(lambda f: f.state == 'processed')
            
            monthly_trend.append({
                'month': month_date.strftime('%b %Y'),
                'files': len(month_files),
                'processed': len(processed),
                'amount': sum(processed.mapped('total_net')),
            })
        
        # Status distribution
        status_distribution = [
            {'status': 'Draft', 'count': len(draft_files)},
            {'status': 'Generated', 'count': len(generated_files)},
            {'status': 'Submitted', 'count': len(submitted_files)},
            {'status': 'Processed', 'count': len(processed_files)},
            {'status': 'Rejected', 'count': len(rejected_files)},
        ]
        
        # Recent files
        recent_files = []
        for f in all_files[:5]:
            recent_files.append({
                'id': f.id,
                'name': f.name,
                'period': f.period_display,
                'employees': f.employee_count,
                'amount': f.total_net,
                'state': f.state,
            })
        
        return {
            'summary': {
                'total_files': len(all_files),
                'draft_files': len(draft_files),
                'pending_submission': len(generated_files),
                'submitted': len(submitted_files),
                'processed': len(processed_files),
                'rejected': len(rejected_files),
                'current_month_status': current_month_files[0].state if current_month_files else 'not_created',
            },
            'compliance': {
                'rate': latest_compliance.compliance_rate if latest_compliance else 0,
                'is_compliant': latest_compliance.is_compliant if latest_compliance else True,
                'employees_paid': latest_compliance.employees_paid_wps if latest_compliance else 0,
                'employees_not_paid': latest_compliance.employees_not_paid if latest_compliance else 0,
            },
            'employees': {
                'total': total_employees,
                'with_bank': self.env['hr.employee'].search_count([
                    ('company_id', '=', company.id),
                    ('bank_account_id', '!=', False),
                ]),
            },
            'banks': {
                'total': total_banks,
            },
            'monthly_trend': monthly_trend,
            'status_distribution': status_distribution,
            'recent_files': recent_files,
        }
