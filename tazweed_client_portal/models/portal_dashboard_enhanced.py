# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class ClientPortalDashboardEnhanced(models.Model):
    """Enhanced Client Portal Dashboard with Comprehensive Analytics"""
    _name = 'client.portal.dashboard.enhanced'
    _description = 'Enhanced Client Portal Dashboard'
    _auto = False

    @api.model
    def get_comprehensive_dashboard(self, client_id, date_from=None, date_to=None):
        """Get comprehensive dashboard data with all KPIs and analytics"""
        client = self.env['tazweed.client'].browse(client_id)
        if not client.exists():
            raise UserError(_('Client not found'))
        
        today = fields.Date.today()
        if not date_from:
            date_from = today - relativedelta(months=6)
        if not date_to:
            date_to = today
        
        return {
            'summary_kpis': self._get_summary_kpis(client_id),
            'workforce_metrics': self._get_workforce_metrics(client_id),
            'financial_summary': self._get_financial_summary(client_id, date_from, date_to),
            'recruitment_pipeline': self._get_recruitment_pipeline(client_id),
            'compliance_status': self._get_compliance_status(client_id),
            'charts': {
                'placement_trend': self._get_placement_trend(client_id, 12),
                'cost_breakdown': self._get_cost_breakdown(client_id),
                'job_order_status': self._get_job_order_status(client_id),
                'department_distribution': self._get_department_distribution(client_id),
                'monthly_invoices': self._get_monthly_invoices(client_id, 6),
            },
            'recent_activity': self._get_recent_activity(client_id, 15),
            'pending_actions': self._get_pending_actions(client_id),
            'alerts': self._get_alerts(client_id),
        }
    
    def _get_summary_kpis(self, client_id):
        """Get main summary KPIs"""
        # Job Orders
        job_orders = self.env['tazweed.job.order'].search([('client_id', '=', client_id)])
        active_job_orders = job_orders.filtered(lambda j: j.state in ['open', 'in_progress'])
        
        # Placements
        placements = self.env['tazweed.placement'].search([('client_id', '=', client_id)])
        active_placements = placements.filtered(lambda p: p.state == 'active')
        
        # Candidates - count via placements since candidates don't have direct client link
        pending_candidates = self.env['tazweed.placement'].search_count([
            ('client_id', '=', client_id),
            ('state', '=', 'pending')
        ])
        
        # Invoices
        pending_invoices = self.env['tazweed.placement.invoice'].search([
            ('client_id', '=', client_id),
            ('state', '=', 'sent')
        ])
        total_outstanding = sum(pending_invoices.mapped('total_amount')) if pending_invoices else 0
        
        # Requests
        open_requests = self.env['client.request'].search_count([
            ('client_id', '=', client_id),
            ('state', 'not in', ['completed', 'rejected', 'cancelled'])
        ])
        
        # Fill Rate
        total_positions = sum(job_orders.mapped('positions_required')) or 1
        filled_positions = sum(job_orders.mapped('positions_filled'))
        fill_rate = (filled_positions / total_positions * 100) if total_positions > 0 else 0
        
        return {
            'active_job_orders': len(active_job_orders),
            'total_job_orders': len(job_orders),
            'active_placements': len(active_placements),
            'total_placements': len(placements),
            'pending_candidates': pending_candidates,
            'pending_invoices': len(pending_invoices),
            'total_outstanding': total_outstanding,
            'open_requests': open_requests,
            'fill_rate': round(fill_rate, 1),
        }
    
    def _get_workforce_metrics(self, client_id):
        """Get workforce-related metrics"""
        placements = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id),
            ('state', '=', 'active')
        ])
        
        # Calculate metrics
        total_workers = len(placements)
        
        # Get employees from placements
        employees = placements.mapped('employee_id')
        
        # Department breakdown
        dept_counts = {}
        for placement in placements:
            dept = placement.department if placement.department else 'Unassigned'
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        # Tenure analysis
        today = fields.Date.today()
        tenure_data = {
            'less_than_3_months': 0,
            '3_to_6_months': 0,
            '6_to_12_months': 0,
            'over_12_months': 0,
        }
        
        for placement in placements:
            if placement.date_start:
                months = (today - placement.date_start).days / 30
                if months < 3:
                    tenure_data['less_than_3_months'] += 1
                elif months < 6:
                    tenure_data['3_to_6_months'] += 1
                elif months < 12:
                    tenure_data['6_to_12_months'] += 1
                else:
                    tenure_data['over_12_months'] += 1
        
        # Turnover rate (last 12 months)
        year_ago = today - relativedelta(months=12)
        terminated_placements = self.env['tazweed.placement'].search_count([
            ('client_id', '=', client_id),
            ('state', '=', 'terminated'),
            ('date_end', '>=', year_ago),
        ])
        avg_workforce = total_workers if total_workers > 0 else 1
        turnover_rate = (terminated_placements / avg_workforce * 100)
        
        return {
            'total_workers': total_workers,
            'department_breakdown': dept_counts,
            'tenure_distribution': tenure_data,
            'turnover_rate': round(turnover_rate, 1),
            'avg_tenure_months': self._calculate_avg_tenure(placements),
        }
    
    def _calculate_avg_tenure(self, placements):
        """Calculate average tenure in months"""
        if not placements:
            return 0
        
        today = fields.Date.today()
        total_days = 0
        count = 0
        
        for p in placements:
            if p.date_start:
                total_days += (today - p.date_start).days
                count += 1
        
        if count == 0:
            return 0
        
        return round(total_days / count / 30, 1)
    
    def _get_financial_summary(self, client_id, date_from, date_to):
        """Get financial summary for the period"""
        invoices = self.env['tazweed.placement.invoice'].search([
            ('client_id', '=', client_id),
            ('date_invoice', '>=', date_from),
            ('date_invoice', '<=', date_to),
        ])
        
        total_invoiced = sum(invoices.mapped('total_amount'))
        paid_invoices = invoices.filtered(lambda i: i.state == 'paid')
        total_paid = sum(paid_invoices.mapped('total_amount'))
        
        pending_invoices = invoices.filtered(lambda i: i.state == 'sent')
        total_pending = sum(pending_invoices.mapped('total_amount'))
        
        overdue_invoices = pending_invoices.filtered(
            lambda i: i.date_due and i.date_due < fields.Date.today()
        )
        total_overdue = sum(overdue_invoices.mapped('total_amount'))
        
        return {
            'total_invoiced': total_invoiced,
            'total_paid': total_paid,
            'total_pending': total_pending,
            'total_overdue': total_overdue,
            'invoice_count': len(invoices),
            'paid_count': len(paid_invoices),
            'pending_count': len(pending_invoices),
            'overdue_count': len(overdue_invoices),
            'payment_rate': round((total_paid / total_invoiced * 100) if total_invoiced > 0 else 0, 1),
        }
    
    def _get_recruitment_pipeline(self, client_id):
        """Get recruitment pipeline metrics"""
        # Active job orders
        active_orders = self.env['tazweed.job.order'].search([
            ('client_id', '=', client_id),
            ('state', 'in', ['open', 'in_progress'])
        ])
        
        total_positions = sum(active_orders.mapped('positions_required'))
        filled_positions = sum(active_orders.mapped('positions_filled'))
        
        # Candidates by stage - use placements since candidates don't have direct client link
        placements_for_pipeline = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id)
        ])
        
        stage_counts = {
            'submitted': 0,
            'screening': 0,
            'pending': 0,
            'approved': 0,
            'rejected': 0,
            'active': 0,
        }
        
        for placement in placements_for_pipeline:
            state = placement.state or 'submitted'
            if state in stage_counts:
                stage_counts[state] += 1
        
        # Average time to fill (completed orders)
        completed_orders = self.env['tazweed.job.order'].search([
            ('client_id', '=', client_id),
            ('state', '=', 'completed')
        ])
        
        avg_time_to_fill = 0
        if completed_orders:
            total_days = sum([
                (o.completion_date - o.create_date.date()).days
                for o in completed_orders if o.completion_date
            ])
            avg_time_to_fill = total_days / len(completed_orders) if completed_orders else 0
        
        return {
            'active_orders': len(active_orders),
            'total_positions': total_positions,
            'filled_positions': filled_positions,
            'open_positions': total_positions - filled_positions,
            'fill_rate': round((filled_positions / total_positions * 100) if total_positions > 0 else 0, 1),
            'candidate_stages': stage_counts,
            'avg_time_to_fill': round(avg_time_to_fill, 1),
        }
    
    def _get_compliance_status(self, client_id):
        """Get compliance status for employees"""
        placements = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id),
            ('state', '=', 'active')
        ])
        
        employees = placements.mapped('employee_id')
        today = fields.Date.today()
        
        # Document expiry tracking
        expiring_soon = 0  # Within 30 days
        expired = 0
        compliant = 0
        
        for emp in employees:
            # Check various document expiry fields
            expiry_fields = [
                'visa_expiry_date', 'passport_expiry_date', 
                'labor_card_expiry', 'emirates_id_expiry'
            ]
            
            emp_status = 'compliant'
            for field in expiry_fields:
                if hasattr(emp, field):
                    expiry_date = getattr(emp, field)
                    if expiry_date:
                        if expiry_date < today:
                            emp_status = 'expired'
                            break
                        elif expiry_date <= today + timedelta(days=30):
                            emp_status = 'expiring'
            
            if emp_status == 'expired':
                expired += 1
            elif emp_status == 'expiring':
                expiring_soon += 1
            else:
                compliant += 1
        
        total = len(employees) or 1
        compliance_rate = (compliant / total * 100)
        
        return {
            'total_employees': len(employees),
            'compliant': compliant,
            'expiring_soon': expiring_soon,
            'expired': expired,
            'compliance_rate': round(compliance_rate, 1),
        }
    
    def _get_placement_trend(self, client_id, months):
        """Get placement trend for the last N months"""
        today = fields.Date.today()
        data = []
        
        for i in range(months - 1, -1, -1):
            month_date = today - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            
            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
            
            # New placements
            new_count = self.env['tazweed.placement'].search_count([
                ('client_id', '=', client_id),
                ('date_start', '>=', month_start),
                ('date_start', '<=', month_end),
            ])
            
            # Terminated placements
            terminated_count = self.env['tazweed.placement'].search_count([
                ('client_id', '=', client_id),
                ('date_end', '>=', month_start),
                ('date_end', '<=', month_end),
                ('state', '=', 'terminated'),
            ])
            
            data.append({
                'month': month_date.strftime('%b %Y'),
                'new': new_count,
                'terminated': terminated_count,
                'net': new_count - terminated_count,
            })
        
        return data
    
    def _get_cost_breakdown(self, client_id):
        """Get cost breakdown by category"""
        # This would typically come from cost center data
        cost_centers = self.env['employee.cost.center'].search([
            ('client_id', '=', client_id)
        ])
        
        if not cost_centers:
            return {
                'salary': 0,
                'benefits': 0,
                'compliance': 0,
                'overhead': 0,
            }
        
        return {
            'salary': sum(cost_centers.mapped('salary_cost')),
            'benefits': sum(cost_centers.mapped('benefits_cost')),
            'compliance': sum(cost_centers.mapped('compliance_cost')),
            'overhead': sum(cost_centers.mapped('overhead_cost')),
        }
    
    def _get_job_order_status(self, client_id):
        """Get job order status distribution"""
        job_orders = self.env['tazweed.job.order'].search([('client_id', '=', client_id)])
        
        status_counts = {}
        for order in job_orders:
            status = order.state or 'draft'
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return status_counts
    
    def _get_department_distribution(self, client_id):
        """Get employee distribution by department"""
        placements = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id),
            ('state', '=', 'active')
        ])
        
        dept_counts = {}
        for placement in placements:
            dept = placement.department if placement.department else 'Unassigned'
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        return dept_counts
    
    def _get_monthly_invoices(self, client_id, months):
        """Get monthly invoice data"""
        today = fields.Date.today()
        data = []
        
        for i in range(months - 1, -1, -1):
            month_date = today - relativedelta(months=i)
            month_start = month_date.replace(day=1)
            
            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
            
            invoices = self.env['tazweed.placement.invoice'].search([
                ('client_id', '=', client_id),
                ('date_invoice', '>=', month_start),
                ('date_invoice', '<=', month_end),
            ])
            
            data.append({
                'month': month_date.strftime('%b %Y'),
                'amount': sum(invoices.mapped('total_amount')),
                'count': len(invoices),
            })
        
        return data
    
    def _get_recent_activity(self, client_id, limit=15):
        """Get recent activity feed"""
        activities = []
        
        # Recent placements
        recent_placements = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id)
        ], order='create_date desc', limit=5)
        
        for p in recent_placements:
            activities.append({
                'type': 'placement',
                'icon': 'fa-user-plus',
                'color': 'success',
                'title': _('New Placement'),
                'message': f'{p.employee_id.name} started' if p.employee_id else 'New placement',
                'date': p.create_date,
                'link': f'/my/placements/{p.id}',
            })
        
        # Recent job orders
        recent_orders = self.env['tazweed.job.order'].search([
            ('client_id', '=', client_id)
        ], order='create_date desc', limit=5)
        
        for o in recent_orders:
            activities.append({
                'type': 'job_order',
                'icon': 'fa-briefcase',
                'color': 'primary',
                'title': _('Job Order'),
                'message': o.name,
                'date': o.create_date,
                'link': f'/my/job-orders/{o.id}',
            })
        
        # Recent requests
        recent_requests = self.env['client.request'].search([
            ('client_id', '=', client_id)
        ], order='create_date desc', limit=5)
        
        for r in recent_requests:
            activities.append({
                'type': 'request',
                'icon': 'fa-ticket',
                'color': 'info',
                'title': _('Request'),
                'message': r.subject,
                'date': r.create_date,
                'link': f'/my/requests/{r.id}',
            })
        
        # Sort by date
        activities.sort(key=lambda x: x['date'], reverse=True)
        
        # Format dates
        for activity in activities:
            activity['date'] = activity['date'].strftime('%b %d, %Y %H:%M')
        
        return activities[:limit]
    
    def _get_pending_actions(self, client_id):
        """Get pending actions requiring client attention"""
        actions = []
        
        # Pending candidate reviews - use placements since candidates don't have direct client link
        pending_candidates = self.env['tazweed.placement'].search_count([
            ('client_id', '=', client_id),
            ('state', '=', 'pending')
        ])
        
        if pending_candidates > 0:
            actions.append({
                'type': 'candidates',
                'icon': 'fa-user-clock',
                'color': 'warning',
                'title': _('Candidates Pending Review'),
                'count': pending_candidates,
                'link': '/my/candidates?filterby=pending',
            })
        
        # Pending invoices
        pending_invoices = self.env['tazweed.placement.invoice'].search_count([
            ('client_id', '=', client_id),
            ('state', '=', 'sent')
        ])
        
        if pending_invoices > 0:
            actions.append({
                'type': 'invoices',
                'icon': 'fa-file-invoice-dollar',
                'color': 'danger',
                'title': _('Invoices Pending Payment'),
                'count': pending_invoices,
                'link': '/my/invoices?filterby=pending',
            })
        
        # Unread messages
        unread_messages = self.env['client.portal.message'].search_count([
            ('client_id', '=', client_id),
            ('is_read', '=', False),
            ('direction', '=', 'outgoing')
        ])
        
        if unread_messages > 0:
            actions.append({
                'type': 'messages',
                'icon': 'fa-envelope',
                'color': 'info',
                'title': _('Unread Messages'),
                'count': unread_messages,
                'link': '/my/messages',
            })
        
        # Open requests
        open_requests = self.env['client.request'].search_count([
            ('client_id', '=', client_id),
            ('state', '=', 'pending_info')
        ])
        
        if open_requests > 0:
            actions.append({
                'type': 'requests',
                'icon': 'fa-question-circle',
                'color': 'primary',
                'title': _('Requests Awaiting Info'),
                'count': open_requests,
                'link': '/my/requests?filterby=pending_info',
            })
        
        return actions
    
    def _get_alerts(self, client_id):
        """Get important alerts for the client"""
        alerts = []
        today = fields.Date.today()
        
        # Document expiry alerts
        placements = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id),
            ('state', '=', 'active')
        ])
        
        employees = placements.mapped('employee_id')
        expiring_docs = 0
        
        for emp in employees:
            expiry_fields = ['visa_expiry_date', 'passport_expiry_date', 
                           'labor_card_expiry', 'emirates_id_expiry']
            
            for field in expiry_fields:
                if hasattr(emp, field):
                    expiry_date = getattr(emp, field)
                    if expiry_date and expiry_date <= today + timedelta(days=30):
                        expiring_docs += 1
                        break
        
        if expiring_docs > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'fa-exclamation-triangle',
                'title': _('Document Expiry Alert'),
                'message': f'{expiring_docs} employee(s) have documents expiring soon',
                'link': '/my/employees?filterby=expiring',
            })
        
        # Overdue invoices
        overdue_invoices = self.env['tazweed.placement.invoice'].search_count([
            ('client_id', '=', client_id),
            ('state', '=', 'sent'),
            ('date_due', '<', today)
        ])
        
        if overdue_invoices > 0:
            alerts.append({
                'type': 'danger',
                'icon': 'fa-exclamation-circle',
                'title': _('Overdue Invoices'),
                'message': f'{overdue_invoices} invoice(s) are overdue',
                'link': '/my/invoices?filterby=overdue',
            })
        
        # SLA breaches
        overdue_requests = self.env['client.request'].search_count([
            ('client_id', '=', client_id),
            ('sla_status', '=', 'overdue'),
            ('state', 'not in', ['completed', 'rejected', 'cancelled'])
        ])
        
        if overdue_requests > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'fa-clock',
                'title': _('SLA Alert'),
                'message': f'{overdue_requests} request(s) have breached SLA',
                'link': '/my/requests?filterby=overdue',
            })
        
        return alerts


class ClientPortalReport(models.Model):
    """Client Portal Report Generation"""
    _name = 'client.portal.report'
    _description = 'Client Portal Report'
    
    name = fields.Char(string='Report Name', required=True)
    client_id = fields.Many2one('tazweed.client', string='Client', required=True)
    report_type = fields.Selection([
        ('workforce', 'Workforce Summary'),
        ('financial', 'Financial Summary'),
        ('recruitment', 'Recruitment Report'),
        ('compliance', 'Compliance Report'),
        ('comprehensive', 'Comprehensive Report'),
    ], string='Report Type', required=True)
    
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    
    generated_date = fields.Datetime(string='Generated Date', readonly=True)
    report_file = fields.Binary(string='Report File')
    report_filename = fields.Char(string='Filename')
    
    def action_generate_report(self):
        """Generate the report"""
        self.ensure_one()
        
        dashboard = self.env['client.portal.dashboard.enhanced']
        data = dashboard.get_comprehensive_dashboard(
            self.client_id.id, 
            self.date_from, 
            self.date_to
        )
        
        # Generate report based on type
        if self.report_type == 'workforce':
            content = self._generate_workforce_report(data)
        elif self.report_type == 'financial':
            content = self._generate_financial_report(data)
        elif self.report_type == 'recruitment':
            content = self._generate_recruitment_report(data)
        elif self.report_type == 'compliance':
            content = self._generate_compliance_report(data)
        else:
            content = self._generate_comprehensive_report(data)
        
        # For now, store as JSON (can be enhanced to PDF/Excel)
        import base64
        self.report_file = base64.b64encode(json.dumps(content, indent=2, default=str).encode())
        self.report_filename = f'{self.name}_{fields.Date.today()}.json'
        self.generated_date = fields.Datetime.now()
        
        return True
    
    def _generate_workforce_report(self, data):
        return {
            'title': 'Workforce Summary Report',
            'client': self.client_id.name,
            'period': f'{self.date_from} to {self.date_to}',
            'data': data.get('workforce_metrics', {}),
        }
    
    def _generate_financial_report(self, data):
        return {
            'title': 'Financial Summary Report',
            'client': self.client_id.name,
            'period': f'{self.date_from} to {self.date_to}',
            'data': data.get('financial_summary', {}),
        }
    
    def _generate_recruitment_report(self, data):
        return {
            'title': 'Recruitment Report',
            'client': self.client_id.name,
            'period': f'{self.date_from} to {self.date_to}',
            'data': data.get('recruitment_pipeline', {}),
        }
    
    def _generate_compliance_report(self, data):
        return {
            'title': 'Compliance Report',
            'client': self.client_id.name,
            'period': f'{self.date_from} to {self.date_to}',
            'data': data.get('compliance_status', {}),
        }
    
    def _generate_comprehensive_report(self, data):
        return {
            'title': 'Comprehensive Report',
            'client': self.client_id.name,
            'period': f'{self.date_from} to {self.date_to}',
            'summary': data.get('summary_kpis', {}),
            'workforce': data.get('workforce_metrics', {}),
            'financial': data.get('financial_summary', {}),
            'recruitment': data.get('recruitment_pipeline', {}),
            'compliance': data.get('compliance_status', {}),
        }
