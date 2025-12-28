# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json


class AnalyticsDashboard(models.Model):
    _name = 'analytics.dashboard'
    _description = 'Analytics Dashboard'
    _order = 'sequence, name'

    name = fields.Char(string='Dashboard Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    dashboard_type = fields.Selection([
        ('executive', 'Executive Summary'),
        ('hr_operations', 'HR Operations'),
        ('payroll', 'Payroll & Finance'),
        ('recruitment', 'Recruitment Pipeline'),
        ('client', 'Client Performance'),
        ('client_requests', 'Client Requests'),
        ('compliance', 'Compliance'),
        ('employee_requests', 'Employee Requests'),
        ('workflows', 'Workflows & Automation'),
        ('custom', 'Custom Dashboard'),
    ], string='Dashboard Type', required=True, default='executive')
    
    description = fields.Text(string='Description')
    
    # Access Control
    user_ids = fields.Many2many('res.users', string='Allowed Users')
    group_ids = fields.Many2many('res.groups', string='Allowed Groups')
    
    # KPIs
    kpi_ids = fields.Many2many('analytics.kpi', string='KPIs')
    
    # Layout
    layout = fields.Selection([
        ('grid', 'Grid Layout'),
        ('list', 'List Layout'),
        ('mixed', 'Mixed Layout'),
    ], string='Layout', default='grid')
    
    columns = fields.Integer(string='Columns', default=4)
    
    # Refresh
    auto_refresh = fields.Boolean(string='Auto Refresh', default=True)
    refresh_interval = fields.Integer(string='Refresh Interval (seconds)', default=300)
    
    # Date Filters
    date_range = fields.Selection([
        ('today', 'Today'),
        ('week', 'This Week'),
        ('month', 'This Month'),
        ('quarter', 'This Quarter'),
        ('year', 'This Year'),
        ('custom', 'Custom Range'),
    ], string='Date Range', default='month')
    
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)

    def action_view_dashboard(self):
        """Open the dashboard view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'tazweed_analytics_dashboard',
            'params': {
                'dashboard_id': self.id,
            },
            'context': {'dashboard_id': self.id},
        }

    def _get_date_range(self):
        """Get date range based on selection."""
        today = fields.Date.today()
        
        if self.date_range == 'today':
            return today, today
        elif self.date_range == 'week':
            start = today - timedelta(days=today.weekday())
            return start, today
        elif self.date_range == 'month':
            return today.replace(day=1), today
        elif self.date_range == 'quarter':
            quarter_month = ((today.month - 1) // 3) * 3 + 1
            return today.replace(month=quarter_month, day=1), today
        elif self.date_range == 'year':
            return today.replace(month=1, day=1), today
        elif self.date_range == 'custom' and self.date_from and self.date_to:
            return self.date_from, self.date_to
        else:
            return today.replace(day=1), today

    def get_chart_data(self):
        """Get chart data for the dashboard (alias for get_dashboard_data)."""
        data = self.get_dashboard_data()
        return data.get('charts', [])

    def get_dashboard_data(self):
        """Get all data for the dashboard."""
        self.ensure_one()
        
        date_from, date_to = self._get_date_range()
        
        data = {
            'dashboard': {
                'id': self.id,
                'name': self.name or '',
                'type': self.dashboard_type or '',
                'layout': self.layout or 'grid',
                'columns': self.columns or 3,
                'date_from': str(date_from) if date_from else '',
                'date_to': str(date_to) if date_to else '',
            },
            'kpis': [],
            'charts': [],
            'summary': self._get_summary_data(date_from, date_to) or {},
            'alerts': self._get_alerts() or [],
        }
        
        # Get KPI data
        for kpi in self.kpi_ids:
            kpi_data = kpi.get_kpi_data()
            if kpi_data:
                data['kpis'].append(kpi_data)
        
        # Get chart data based on dashboard type
        chart_methods = {
            'executive': self._get_executive_charts,
            'hr_operations': self._get_hr_operations_charts,
            'payroll': self._get_payroll_charts,
            'recruitment': self._get_recruitment_charts,
            'client': self._get_client_charts,
            'client_requests': self._get_client_request_charts,
            'compliance': self._get_compliance_charts,
            'employee_requests': self._get_employee_request_charts,
            'workflows': self._get_workflow_charts,
        }
        
        if self.dashboard_type in chart_methods:
            charts = chart_methods[self.dashboard_type](date_from, date_to)
            data['charts'] = charts if charts else []
        
        return data

    def _get_summary_data(self, date_from, date_to):
        """Get summary statistics."""
        Employee = self.env['hr.employee'].sudo()
        
        today = fields.Date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        
        summary = {
            'total_employees': Employee.search_count([('active', '=', True)]),
            'new_hires_month': Employee.search_count([
                ('create_date', '>=', month_start)
            ]),
            'new_hires_year': Employee.search_count([
                ('create_date', '>=', year_start)
            ]),
        }
        
        # Add client request stats if model exists
        if 'client.request' in self.env:
            ClientRequest = self.env['client.request'].sudo()
            summary.update({
                'total_client_requests': ClientRequest.search_count([]),
                'pending_client_requests': ClientRequest.search_count([
                    ('state', 'in', ['submitted', 'under_review', 'pending_info'])
                ]),
                'overdue_client_requests': ClientRequest.search_count([
                    ('sla_status', '=', 'overdue'),
                    ('state', 'not in', ['completed', 'rejected', 'cancelled'])
                ]),
            })
        
        # Add HR service request stats if model exists
        if 'hr.service.request' in self.env:
            HRRequest = self.env['hr.service.request'].sudo()
            summary.update({
                'total_hr_requests': HRRequest.search_count([]),
                'pending_hr_requests': HRRequest.search_count([
                    ('state', 'in', ['submitted', 'manager_approval', 'hr_approval', 'processing'])
                ]),
            })
        
        # Add placement stats if model exists
        if 'tazweed.placement' in self.env:
            Placement = self.env['tazweed.placement'].sudo()
            summary.update({
                'total_placements': Placement.search_count([]),
                'active_placements': Placement.search_count([('state', '=', 'active')]),
            })
        
        return summary

    def _get_alerts(self):
        """Get system alerts and notifications."""
        alerts = []
        today = fields.Date.today()
        
        # Check for overdue client requests
        if 'client.request' in self.env:
            overdue = self.env['client.request'].sudo().search_count([
                ('sla_status', '=', 'overdue'),
                ('state', 'not in', ['completed', 'rejected', 'cancelled'])
            ])
            if overdue > 0:
                alerts.append({
                    'type': 'danger',
                    'title': 'Overdue Client Requests',
                    'message': f'{overdue} client request(s) are overdue',
                    'count': overdue,
                })
        
        # Check for expiring documents
        if 'hr.employee.document' in self.env:
            expiring = self.env['hr.employee.document'].sudo().search_count([
                ('expiry_date', '>=', today),
                ('expiry_date', '<=', today + timedelta(days=30))
            ])
            if expiring > 0:
                alerts.append({
                    'type': 'warning',
                    'title': 'Expiring Documents',
                    'message': f'{expiring} document(s) expiring in 30 days',
                    'count': expiring,
                })
        
        # Check for pending HR requests
        if 'hr.service.request' in self.env:
            pending = self.env['hr.service.request'].sudo().search_count([
                ('state', 'in', ['submitted', 'manager_approval', 'hr_approval']),
                ('create_date', '<=', fields.Datetime.now() - timedelta(days=3))
            ])
            if pending > 0:
                alerts.append({
                    'type': 'warning',
                    'title': 'Pending HR Requests',
                    'message': f'{pending} HR request(s) pending for more than 3 days',
                    'count': pending,
                })
        
        return alerts

    # ==========================================
    # EXECUTIVE DASHBOARD CHARTS
    # ==========================================
    
    def _get_executive_charts(self, date_from, date_to):
        """Get charts for executive dashboard."""
        return [
            self._get_headcount_trend_chart(),
            self._get_department_distribution_chart(),
            self._get_turnover_chart(),
            self._get_key_metrics_chart(date_from, date_to),
        ]

    def _get_headcount_trend_chart(self):
        """Get headcount trend over last 12 months."""
        Employee = self.env['hr.employee'].sudo()
        
        labels = []
        data = []
        today = fields.Date.today()
        
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            month_end = (date.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
            
            labels.append(date.strftime('%b %Y'))
            count = Employee.search_count([
                ('create_date', '<=', month_end),
                '|', ('active', '=', True),
                ('departure_date', '>', month_end)
            ])
            data.append(count)
        
        return {
            'id': 'headcount_trend',
            'title': 'Headcount Trend',
            'type': 'line',
            'labels': labels,
            'datasets': [{
                'label': 'Employees',
                'data': data,
                'borderColor': '#2196F3',
                'backgroundColor': 'rgba(33, 150, 243, 0.1)',
                'fill': True,
            }]
        }

    def _get_department_distribution_chart(self):
        """Get employee distribution by department."""
        Employee = self.env['hr.employee'].sudo()
        
        departments = self.env['hr.department'].sudo().search([])
        labels = []
        data = []
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', '#00BCD4', '#607D8B', '#795548']
        
        for dept in departments[:8]:
            count = Employee.search_count([
                ('department_id', '=', dept.id),
                ('active', '=', True)
            ])
            if count > 0:
                labels.append(dept.name)
                data.append(count)
        
        return {
            'id': 'department_distribution',
            'title': 'Employees by Department',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors[:len(data)],
            }]
        }

    def _get_turnover_chart(self):
        """Get turnover rate trend."""
        Employee = self.env['hr.employee'].sudo()
        
        labels = []
        data = []
        today = fields.Date.today()
        
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            month_start = date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            labels.append(date.strftime('%b'))
            
            departed = Employee.search_count([
                ('departure_date', '>=', month_start),
                ('departure_date', '<=', month_end)
            ])
            total = Employee.search_count([
                ('create_date', '<=', month_end)
            ]) or 1
            
            rate = (departed / total) * 100
            data.append(round(rate, 1))
        
        return {
            'id': 'turnover_trend',
            'title': 'Monthly Turnover Rate (%)',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Turnover %',
                'data': data,
                'backgroundColor': '#F44336',
            }]
        }

    def _get_key_metrics_chart(self, date_from, date_to):
        """Get key metrics summary."""
        metrics = []
        
        # Employee metrics
        Employee = self.env['hr.employee'].sudo()
        total_emp = Employee.search_count([('active', '=', True)])
        metrics.append({'label': 'Total Employees', 'value': total_emp})
        
        # Client metrics
        if 'tazweed.client' in self.env:
            clients = self.env['tazweed.client'].sudo().search_count([('active', '=', True)])
            metrics.append({'label': 'Active Clients', 'value': clients})
        
        # Placement metrics
        if 'tazweed.placement' in self.env:
            placements = self.env['tazweed.placement'].sudo().search_count([('state', '=', 'active')])
            metrics.append({'label': 'Active Placements', 'value': placements})
        
        # Request metrics
        if 'client.request' in self.env:
            requests = self.env['client.request'].sudo().search_count([
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to)
            ])
            metrics.append({'label': 'Client Requests', 'value': requests})
        
        return {
            'id': 'key_metrics',
            'title': 'Key Metrics',
            'type': 'metrics',
            'data': metrics,
        }

    # ==========================================
    # CLIENT REQUEST DASHBOARD CHARTS
    # ==========================================
    
    def _get_client_request_charts(self, date_from, date_to):
        """Get charts for client request dashboard."""
        return [
            self._get_request_by_status_chart(date_from, date_to),
            self._get_request_by_category_chart(date_from, date_to),
            self._get_request_trend_chart(),
            self._get_sla_compliance_chart(date_from, date_to),
            self._get_request_by_client_chart(date_from, date_to),
            self._get_avg_resolution_time_chart(),
        ]

    def _get_request_by_status_chart(self, date_from, date_to):
        """Get client requests by status."""
        if 'client.request' not in self.env:
            return self._empty_chart('request_by_status', 'Requests by Status')
        
        ClientRequest = self.env['client.request'].sudo()
        
        statuses = [
            ('draft', 'Draft', '#9E9E9E'),
            ('submitted', 'Submitted', '#2196F3'),
            ('under_review', 'Under Review', '#FF9800'),
            ('pending_info', 'Pending Info', '#FFC107'),
            ('approved', 'Approved', '#4CAF50'),
            ('in_progress', 'In Progress', '#00BCD4'),
            ('completed', 'Completed', '#8BC34A'),
            ('rejected', 'Rejected', '#F44336'),
            ('cancelled', 'Cancelled', '#607D8B'),
        ]
        
        labels = []
        data = []
        colors = []
        
        for state, label, color in statuses:
            count = ClientRequest.search_count([
                ('state', '=', state),
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to)
            ])
            if count > 0:
                labels.append(label)
                data.append(count)
                colors.append(color)
        
        return {
            'id': 'request_by_status',
            'title': 'Requests by Status',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors,
            }]
        }

    def _get_request_by_category_chart(self, date_from, date_to):
        """Get client requests by category."""
        if 'client.request' not in self.env:
            return self._empty_chart('request_by_category', 'Requests by Category')
        
        ClientRequest = self.env['client.request'].sudo()
        
        categories = [
            ('invoice', 'Invoice & Billing', '#2196F3'),
            ('worker', 'Worker Management', '#4CAF50'),
            ('document', 'Documents', '#FF9800'),
            ('service', 'Services', '#9C27B0'),
            ('support', 'Support', '#00BCD4'),
            ('feedback', 'Feedback', '#607D8B'),
        ]
        
        labels = []
        data = []
        colors = []
        
        for cat, label, color in categories:
            count = ClientRequest.search_count([
                ('category', '=', cat),
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to)
            ])
            if count > 0:
                labels.append(label)
                data.append(count)
                colors.append(color)
        
        return {
            'id': 'request_by_category',
            'title': 'Requests by Category',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Requests',
                'data': data,
                'backgroundColor': colors,
            }]
        }

    def _get_request_trend_chart(self):
        """Get client request trend over last 12 months."""
        if 'client.request' not in self.env:
            return self._empty_chart('request_trend', 'Request Trend')
        
        ClientRequest = self.env['client.request'].sudo()
        
        labels = []
        submitted_data = []
        completed_data = []
        today = fields.Date.today()
        
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            month_start = date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            labels.append(date.strftime('%b %Y'))
            
            submitted = ClientRequest.search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ])
            completed = ClientRequest.search_count([
                ('completed_date', '>=', month_start),
                ('completed_date', '<=', month_end),
                ('state', '=', 'completed')
            ])
            
            submitted_data.append(submitted)
            completed_data.append(completed)
        
        return {
            'id': 'request_trend',
            'title': 'Request Trend (12 Months)',
            'type': 'line',
            'labels': labels,
            'datasets': [
                {
                    'label': 'Submitted',
                    'data': submitted_data,
                    'borderColor': '#2196F3',
                    'fill': False,
                },
                {
                    'label': 'Completed',
                    'data': completed_data,
                    'borderColor': '#4CAF50',
                    'fill': False,
                }
            ]
        }

    def _get_sla_compliance_chart(self, date_from, date_to):
        """Get SLA compliance rate."""
        if 'client.request' not in self.env:
            return self._empty_chart('sla_compliance', 'SLA Compliance')
        
        ClientRequest = self.env['client.request'].sudo()
        
        completed = ClientRequest.search([
            ('state', '=', 'completed'),
            ('completed_date', '>=', date_from),
            ('completed_date', '<=', date_to)
        ])
        
        on_time = 0
        late = 0
        
        for req in completed:
            if req.completed_date and req.expected_date:
                if req.completed_date.date() <= req.expected_date:
                    on_time += 1
                else:
                    late += 1
            else:
                on_time += 1  # Assume on time if no dates
        
        total = on_time + late
        compliance_rate = (on_time / total * 100) if total > 0 else 100
        
        return {
            'id': 'sla_compliance',
            'title': f'SLA Compliance: {compliance_rate:.1f}%',
            'type': 'doughnut',
            'labels': ['On Time', 'Late'],
            'datasets': [{
                'data': [on_time, late],
                'backgroundColor': ['#4CAF50', '#F44336'],
            }]
        }

    def _get_request_by_client_chart(self, date_from, date_to):
        """Get requests by top clients."""
        if 'client.request' not in self.env:
            return self._empty_chart('request_by_client', 'Requests by Client')
        
        self.env.cr.execute("""
            SELECT c.name, COUNT(r.id) as count
            FROM client_request r
            JOIN tazweed_client c ON r.client_id = c.id
            WHERE r.create_date >= %s AND r.create_date <= %s
            GROUP BY c.id, c.name
            ORDER BY count DESC
            LIMIT 10
        """, (date_from, date_to))
        
        results = self.env.cr.fetchall()
        
        labels = [r[0] for r in results] if results else ['No Data']
        data = [r[1] for r in results] if results else [0]
        
        return {
            'id': 'request_by_client',
            'title': 'Top 10 Clients by Requests',
            'type': 'horizontalBar',
            'labels': labels,
            'datasets': [{
                'label': 'Requests',
                'data': data,
                'backgroundColor': '#2196F3',
            }]
        }

    def _get_avg_resolution_time_chart(self):
        """Get average resolution time by category."""
        if 'client.request' not in self.env:
            return self._empty_chart('avg_resolution', 'Avg Resolution Time')
        
        self.env.cr.execute("""
            SELECT 
                category,
                AVG(EXTRACT(EPOCH FROM (completed_date - submitted_date))/3600) as avg_hours
            FROM client_request
            WHERE state = 'completed' 
            AND completed_date IS NOT NULL 
            AND submitted_date IS NOT NULL
            GROUP BY category
            ORDER BY avg_hours DESC
        """)
        
        results = self.env.cr.fetchall()
        
        category_labels = {
            'invoice': 'Invoice & Billing',
            'worker': 'Worker Management',
            'document': 'Documents',
            'service': 'Services',
            'support': 'Support',
            'feedback': 'Feedback',
        }
        
        labels = [category_labels.get(r[0], r[0]) for r in results] if results else ['No Data']
        data = [round(r[1], 1) for r in results] if results else [0]
        
        return {
            'id': 'avg_resolution',
            'title': 'Avg Resolution Time (Hours)',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Hours',
                'data': data,
                'backgroundColor': '#FF9800',
            }]
        }

    # ==========================================
    # EMPLOYEE REQUEST DASHBOARD CHARTS
    # ==========================================
    
    def _get_employee_request_charts(self, date_from, date_to):
        """Get charts for employee request dashboard."""
        return [
            self._get_hr_request_by_status_chart(date_from, date_to),
            self._get_hr_request_by_type_chart(date_from, date_to),
            self._get_hr_request_trend_chart(),
            self._get_hr_request_by_department_chart(date_from, date_to),
        ]

    def _get_hr_request_by_status_chart(self, date_from, date_to):
        """Get HR requests by status."""
        if 'hr.service.request' not in self.env:
            return self._empty_chart('hr_request_by_status', 'HR Requests by Status')
        
        HRRequest = self.env['hr.service.request'].sudo()
        
        statuses = [
            ('draft', 'Draft', '#9E9E9E'),
            ('submitted', 'Submitted', '#2196F3'),
            ('manager_approval', 'Manager Approval', '#FF9800'),
            ('hr_approval', 'HR Approval', '#FFC107'),
            ('processing', 'Processing', '#00BCD4'),
            ('ready', 'Ready', '#8BC34A'),
            ('completed', 'Completed', '#4CAF50'),
            ('rejected', 'Rejected', '#F44336'),
            ('cancelled', 'Cancelled', '#607D8B'),
        ]
        
        labels = []
        data = []
        colors = []
        
        for state, label, color in statuses:
            count = HRRequest.search_count([
                ('state', '=', state),
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to)
            ])
            if count > 0:
                labels.append(label)
                data.append(count)
                colors.append(color)
        
        return {
            'id': 'hr_request_by_status',
            'title': 'HR Requests by Status',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors,
            }]
        }

    def _get_hr_request_by_type_chart(self, date_from, date_to):
        """Get HR requests by type."""
        if 'hr.service.request' not in self.env:
            return self._empty_chart('hr_request_by_type', 'HR Requests by Type')
        
        self.env.cr.execute("""
            SELECT t.name, COUNT(r.id) as count
            FROM hr_service_request r
            JOIN hr_service_request_type t ON r.request_type_id = t.id
            WHERE r.create_date >= %s AND r.create_date <= %s
            GROUP BY t.id, t.name
            ORDER BY count DESC
            LIMIT 10
        """, (date_from, date_to))
        
        results = self.env.cr.fetchall()
        
        labels = [r[0] for r in results] if results else ['No Data']
        data = [r[1] for r in results] if results else [0]
        
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', 
                  '#00BCD4', '#607D8B', '#795548', '#E91E63', '#3F51B5']
        
        return {
            'id': 'hr_request_by_type',
            'title': 'Top 10 HR Request Types',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Requests',
                'data': data,
                'backgroundColor': colors[:len(data)],
            }]
        }

    def _get_hr_request_trend_chart(self):
        """Get HR request trend over last 12 months."""
        if 'hr.service.request' not in self.env:
            return self._empty_chart('hr_request_trend', 'HR Request Trend')
        
        HRRequest = self.env['hr.service.request'].sudo()
        
        labels = []
        data = []
        today = fields.Date.today()
        
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            month_start = date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            labels.append(date.strftime('%b %Y'))
            
            count = HRRequest.search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ])
            data.append(count)
        
        return {
            'id': 'hr_request_trend',
            'title': 'HR Request Trend (12 Months)',
            'type': 'line',
            'labels': labels,
            'datasets': [{
                'label': 'Requests',
                'data': data,
                'borderColor': '#9C27B0',
                'backgroundColor': 'rgba(156, 39, 176, 0.1)',
                'fill': True,
            }]
        }

    def _get_hr_request_by_department_chart(self, date_from, date_to):
        """Get HR requests by department."""
        if 'hr.service.request' not in self.env:
            return self._empty_chart('hr_request_by_dept', 'HR Requests by Department')
        
        self.env.cr.execute("""
            SELECT d.name, COUNT(r.id) as count
            FROM hr_service_request r
            JOIN hr_employee e ON r.employee_id = e.id
            JOIN hr_department d ON e.department_id = d.id
            WHERE r.create_date >= %s AND r.create_date <= %s
            GROUP BY d.id, d.name
            ORDER BY count DESC
            LIMIT 8
        """, (date_from, date_to))
        
        results = self.env.cr.fetchall()
        
        labels = [r[0] for r in results] if results else ['No Data']
        data = [r[1] for r in results] if results else [0]
        
        return {
            'id': 'hr_request_by_dept',
            'title': 'HR Requests by Department',
            'type': 'horizontalBar',
            'labels': labels,
            'datasets': [{
                'label': 'Requests',
                'data': data,
                'backgroundColor': '#00BCD4',
            }]
        }

    # ==========================================
    # HR OPERATIONS DASHBOARD CHARTS
    # ==========================================
    
    def _get_hr_operations_charts(self, date_from, date_to):
        """Get charts for HR operations dashboard."""
        return [
            self._get_leave_analysis_chart(date_from, date_to),
            self._get_employee_status_chart(),
            self._get_contract_expiry_chart(),
            self._get_new_hires_chart(),
        ]

    def _get_leave_analysis_chart(self, date_from, date_to):
        """Get leave analysis by type."""
        if 'hr.leave' not in self.env:
            return self._empty_chart('leave_analysis', 'Leave Distribution')
        
        self.env.cr.execute("""
            SELECT lt.name, COUNT(l.id) as count
            FROM hr_leave l
            JOIN hr_leave_type lt ON l.holiday_status_id = lt.id
            WHERE l.state = 'validate'
            AND l.date_from >= %s AND l.date_from <= %s
            GROUP BY lt.id, lt.name
            ORDER BY count DESC
            LIMIT 8
        """, (date_from, date_to))
        
        results = self.env.cr.fetchall()
        
        labels = [r[0] for r in results] if results else ['No Data']
        data = [r[1] for r in results] if results else [0]
        
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', '#00BCD4', '#607D8B', '#795548']
        
        return {
            'id': 'leave_analysis',
            'title': 'Leave Distribution',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors[:len(data)],
            }]
        }

    def _get_employee_status_chart(self):
        """Get employee status distribution."""
        Employee = self.env['hr.employee'].sudo()
        
        active = Employee.search_count([('active', '=', True)])
        inactive = Employee.search_count([('active', '=', False)])
        
        # Check for probation if field exists
        probation = 0
        if 'probation_end_date' in Employee._fields:
            today = fields.Date.today()
            probation = Employee.search_count([
                ('active', '=', True),
                ('probation_end_date', '>=', today)
            ])
        
        return {
            'id': 'employee_status',
            'title': 'Employee Status',
            'type': 'pie',
            'labels': ['Active', 'Inactive', 'On Probation'],
            'datasets': [{
                'data': [active - probation, inactive, probation],
                'backgroundColor': ['#4CAF50', '#F44336', '#FF9800'],
            }]
        }

    def _get_contract_expiry_chart(self):
        """Get contracts expiring soon."""
        if 'hr.contract' not in self.env:
            return self._empty_chart('contract_expiry', 'Contract Expiry')
        
        Contract = self.env['hr.contract'].sudo()
        today = fields.Date.today()
        
        expired = Contract.search_count([
            ('state', '=', 'open'),
            ('date_end', '<', today)
        ])
        
        expiring_30 = Contract.search_count([
            ('state', '=', 'open'),
            ('date_end', '>=', today),
            ('date_end', '<=', today + timedelta(days=30))
        ])
        
        expiring_90 = Contract.search_count([
            ('state', '=', 'open'),
            ('date_end', '>', today + timedelta(days=30)),
            ('date_end', '<=', today + timedelta(days=90))
        ])
        
        valid = Contract.search_count([
            ('state', '=', 'open'),
            ('date_end', '>', today + timedelta(days=90))
        ])
        
        return {
            'id': 'contract_expiry',
            'title': 'Contract Status',
            'type': 'doughnut',
            'labels': ['Expired', 'Expiring (30 days)', 'Expiring (90 days)', 'Valid'],
            'datasets': [{
                'data': [expired, expiring_30, expiring_90, valid],
                'backgroundColor': ['#F44336', '#FF9800', '#FFC107', '#4CAF50'],
            }]
        }

    def _get_new_hires_chart(self):
        """Get new hires trend."""
        Employee = self.env['hr.employee'].sudo()
        
        labels = []
        data = []
        today = fields.Date.today()
        
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            month_start = date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            labels.append(date.strftime('%b'))
            
            count = Employee.search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ])
            data.append(count)
        
        return {
            'id': 'new_hires',
            'title': 'New Hires (12 Months)',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'New Hires',
                'data': data,
                'backgroundColor': '#4CAF50',
            }]
        }

    # ==========================================
    # PAYROLL DASHBOARD CHARTS
    # ==========================================
    
    def _get_payroll_charts(self, date_from, date_to):
        """Get charts for payroll dashboard."""
        return [
            self._get_payroll_trend_chart(),
            self._get_salary_distribution_chart(),
            self._get_payroll_by_department_chart(),
        ]

    def _get_payroll_trend_chart(self):
        """Get payroll cost trend."""
        labels = []
        data = []
        today = fields.Date.today()
        
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            labels.append(date.strftime('%b %Y'))
            
            # Try to get actual payroll data
            if 'hr.payslip' in self.env:
                month_start = date.replace(day=1)
                month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
                
                self.env.cr.execute("""
                    SELECT COALESCE(SUM(net_wage), 0)
                    FROM hr_payslip
                    WHERE state = 'done'
                    AND date_from >= %s AND date_to <= %s
                """, (month_start, month_end))
                
                result = self.env.cr.fetchone()
                data.append(float(result[0]) if result else 0)
            else:
                data.append(0)
        
        return {
            'id': 'payroll_trend',
            'title': 'Payroll Cost Trend',
            'type': 'line',
            'labels': labels,
            'datasets': [{
                'label': 'Payroll Cost',
                'data': data,
                'borderColor': '#2196F3',
                'backgroundColor': 'rgba(33, 150, 243, 0.1)',
                'fill': True,
            }]
        }

    def _get_salary_distribution_chart(self):
        """Get salary distribution."""
        if 'hr.contract' not in self.env:
            return self._empty_chart('salary_distribution', 'Salary Distribution')
        
        Contract = self.env['hr.contract'].sudo()
        
        ranges = [
            (0, 5000, '0-5K'),
            (5000, 10000, '5K-10K'),
            (10000, 15000, '10K-15K'),
            (15000, 20000, '15K-20K'),
            (20000, 50000, '20K-50K'),
            (50000, float('inf'), '50K+'),
        ]
        
        labels = []
        data = []
        
        for min_sal, max_sal, label in ranges:
            if max_sal == float('inf'):
                count = Contract.search_count([
                    ('state', '=', 'open'),
                    ('wage', '>=', min_sal)
                ])
            else:
                count = Contract.search_count([
                    ('state', '=', 'open'),
                    ('wage', '>=', min_sal),
                    ('wage', '<', max_sal)
                ])
            labels.append(label)
            data.append(count)
        
        return {
            'id': 'salary_distribution',
            'title': 'Salary Distribution',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Employees',
                'data': data,
                'backgroundColor': '#9C27B0',
            }]
        }

    def _get_payroll_by_department_chart(self):
        """Get payroll cost by department."""
        if 'hr.contract' not in self.env:
            return self._empty_chart('payroll_by_dept', 'Payroll by Department')
        
        self.env.cr.execute("""
            SELECT d.name, SUM(c.wage) as total
            FROM hr_contract c
            JOIN hr_employee e ON c.employee_id = e.id
            JOIN hr_department d ON e.department_id = d.id
            WHERE c.state = 'open'
            GROUP BY d.id, d.name
            ORDER BY total DESC
            LIMIT 8
        """)
        
        results = self.env.cr.fetchall()
        
        labels = [r[0] for r in results] if results else ['No Data']
        data = [float(r[1]) for r in results] if results else [0]
        
        return {
            'id': 'payroll_by_dept',
            'title': 'Payroll by Department',
            'type': 'horizontalBar',
            'labels': labels,
            'datasets': [{
                'label': 'Monthly Cost',
                'data': data,
                'backgroundColor': '#FF9800',
            }]
        }

    # ==========================================
    # RECRUITMENT DASHBOARD CHARTS
    # ==========================================
    
    def _get_recruitment_charts(self, date_from, date_to):
        """Get charts for recruitment dashboard."""
        return [
            self._get_placement_pipeline_chart(),
            self._get_job_applications_chart(date_from, date_to),
            self._get_hiring_sources_chart(date_from, date_to),
        ]

    def _get_placement_pipeline_chart(self):
        """Get placement pipeline."""
        if 'tazweed.placement' not in self.env:
            return self._empty_chart('placement_pipeline', 'Placement Pipeline')
        
        Placement = self.env['tazweed.placement'].sudo()
        
        states = [
            ('draft', 'Draft', '#9E9E9E'),
            ('pending', 'Pending', '#FF9800'),
            ('active', 'Active', '#4CAF50'),
            ('completed', 'Completed', '#2196F3'),
            ('cancelled', 'Cancelled', '#F44336'),
        ]
        
        labels = []
        data = []
        colors = []
        
        for state, label, color in states:
            count = Placement.search_count([('state', '=', state)])
            if count > 0:
                labels.append(label)
                data.append(count)
                colors.append(color)
        
        return {
            'id': 'placement_pipeline',
            'title': 'Placement Pipeline',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors,
            }]
        }

    def _get_job_applications_chart(self, date_from, date_to):
        """Get job applications trend."""
        if 'job.application' not in self.env:
            return self._empty_chart('job_applications', 'Job Applications')
        
        JobApp = self.env['job.application'].sudo()
        
        labels = []
        data = []
        today = fields.Date.today()
        
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            month_start = date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            labels.append(date.strftime('%b'))
            
            count = JobApp.search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ])
            data.append(count)
        
        return {
            'id': 'job_applications',
            'title': 'Job Applications (12 Months)',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Applications',
                'data': data,
                'backgroundColor': '#2196F3',
            }]
        }

    def _get_hiring_sources_chart(self, date_from, date_to):
        """Get hiring sources effectiveness."""
        if 'candidate.source' not in self.env:
            return self._empty_chart('hiring_sources', 'Hiring Sources')
        
        self.env.cr.execute("""
            SELECT s.name, COUNT(a.id) as count
            FROM job_application a
            JOIN candidate_source s ON a.source_id = s.id
            WHERE a.create_date >= %s AND a.create_date <= %s
            GROUP BY s.id, s.name
            ORDER BY count DESC
            LIMIT 8
        """, (date_from, date_to))
        
        results = self.env.cr.fetchall()
        
        labels = [r[0] for r in results] if results else ['No Data']
        data = [r[1] for r in results] if results else [0]
        
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', '#00BCD4', '#607D8B', '#795548']
        
        return {
            'id': 'hiring_sources',
            'title': 'Top Hiring Sources',
            'type': 'pie',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors[:len(data)],
            }]
        }

    # ==========================================
    # CLIENT DASHBOARD CHARTS
    # ==========================================
    
    def _get_client_charts(self, date_from, date_to):
        """Get charts for client dashboard."""
        return [
            self._get_client_distribution_chart(),
            self._get_placement_by_client_chart(),
            self._get_client_growth_chart(),
        ]

    def _get_client_distribution_chart(self):
        """Get client distribution by industry."""
        if 'tazweed.client' not in self.env:
            return self._empty_chart('client_distribution', 'Clients by Industry')
        
        Client = self.env['tazweed.client'].sudo()
        
        # Group by industry if field exists
        if 'industry_id' in Client._fields:
            self.env.cr.execute("""
                SELECT i.name, COUNT(c.id) as count
                FROM tazweed_client c
                JOIN res_partner_industry i ON c.industry_id = i.id
                WHERE c.active = true
                GROUP BY i.id, i.name
                ORDER BY count DESC
                LIMIT 8
            """)
            results = self.env.cr.fetchall()
            labels = [r[0] for r in results] if results else ['No Data']
            data = [r[1] for r in results] if results else [0]
        else:
            labels = ['All Clients']
            data = [Client.search_count([('active', '=', True)])]
        
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', '#00BCD4', '#607D8B', '#795548']
        
        return {
            'id': 'client_distribution',
            'title': 'Clients by Industry',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors[:len(data)],
            }]
        }

    def _get_placement_by_client_chart(self):
        """Get placements by client."""
        if 'tazweed.placement' not in self.env:
            return self._empty_chart('placement_by_client', 'Placements by Client')
        
        self.env.cr.execute("""
            SELECT c.name, COUNT(p.id) as count
            FROM tazweed_placement p
            JOIN tazweed_client c ON p.client_id = c.id
            WHERE p.state = 'active'
            GROUP BY c.id, c.name
            ORDER BY count DESC
            LIMIT 10
        """)
        
        results = self.env.cr.fetchall()
        
        labels = [r[0] for r in results] if results else ['No Data']
        data = [r[1] for r in results] if results else [0]
        
        return {
            'id': 'placement_by_client',
            'title': 'Top 10 Clients by Placements',
            'type': 'horizontalBar',
            'labels': labels,
            'datasets': [{
                'label': 'Active Placements',
                'data': data,
                'backgroundColor': '#4CAF50',
            }]
        }

    def _get_client_growth_chart(self):
        """Get client growth trend."""
        if 'tazweed.client' not in self.env:
            return self._empty_chart('client_growth', 'Client Growth')
        
        Client = self.env['tazweed.client'].sudo()
        
        labels = []
        data = []
        today = fields.Date.today()
        
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            month_end = (date.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
            
            labels.append(date.strftime('%b %Y'))
            count = Client.search_count([
                ('create_date', '<=', month_end),
                ('active', '=', True)
            ])
            data.append(count)
        
        return {
            'id': 'client_growth',
            'title': 'Client Growth',
            'type': 'line',
            'labels': labels,
            'datasets': [{
                'label': 'Total Clients',
                'data': data,
                'borderColor': '#2196F3',
                'backgroundColor': 'rgba(33, 150, 243, 0.1)',
                'fill': True,
            }]
        }

    # ==========================================
    # COMPLIANCE DASHBOARD CHARTS
    # ==========================================
    
    def _get_compliance_charts(self, date_from, date_to):
        """Get charts for compliance dashboard."""
        return [
            self._get_emiratization_chart(),
            self._get_visa_status_chart(),
            self._get_document_expiry_chart(),
            self._get_wps_compliance_chart(),
        ]

    def _get_emiratization_chart(self):
        """Get Emiratization statistics."""
        Employee = self.env['hr.employee'].sudo()
        
        total = Employee.search_count([('active', '=', True)])
        
        # Check for nationality field
        uae_count = 0
        if 'country_id' in Employee._fields:
            uae = self.env['res.country'].sudo().search([('code', '=', 'AE')], limit=1)
            if uae:
                uae_count = Employee.search_count([
                    ('active', '=', True),
                    ('country_id', '=', uae.id)
                ])
        
        non_uae = total - uae_count
        emiratization_rate = (uae_count / total * 100) if total > 0 else 0
        
        return {
            'id': 'emiratization',
            'title': f'Emiratization Rate: {emiratization_rate:.1f}%',
            'type': 'doughnut',
            'labels': ['UAE Nationals', 'Expatriates'],
            'datasets': [{
                'data': [uae_count, non_uae],
                'backgroundColor': ['#4CAF50', '#2196F3'],
            }]
        }

    def _get_visa_status_chart(self):
        """Get visa status distribution."""
        if 'hr.employee.document' not in self.env:
            return self._empty_chart('visa_status', 'Visa Status')
        
        Document = self.env['hr.employee.document'].sudo()
        today = fields.Date.today()
        
        # Count visa documents by status
        valid = Document.search_count([
            ('document_type', 'ilike', 'visa'),
            ('expiry_date', '>', today + timedelta(days=90))
        ])
        
        expiring_90 = Document.search_count([
            ('document_type', 'ilike', 'visa'),
            ('expiry_date', '>', today + timedelta(days=30)),
            ('expiry_date', '<=', today + timedelta(days=90))
        ])
        
        expiring_30 = Document.search_count([
            ('document_type', 'ilike', 'visa'),
            ('expiry_date', '>', today),
            ('expiry_date', '<=', today + timedelta(days=30))
        ])
        
        expired = Document.search_count([
            ('document_type', 'ilike', 'visa'),
            ('expiry_date', '<=', today)
        ])
        
        return {
            'id': 'visa_status',
            'title': 'Visa Status',
            'type': 'doughnut',
            'labels': ['Valid', 'Expiring (90 days)', 'Expiring (30 days)', 'Expired'],
            'datasets': [{
                'data': [valid, expiring_90, expiring_30, expired],
                'backgroundColor': ['#4CAF50', '#FFC107', '#FF9800', '#F44336'],
            }]
        }

    def _get_document_expiry_chart(self):
        """Get document expiry timeline."""
        if 'hr.employee.document' not in self.env:
            return self._empty_chart('document_expiry', 'Document Expiry')
        
        Document = self.env['hr.employee.document'].sudo()
        today = fields.Date.today()
        
        labels = ['Expired', 'This Week', 'This Month', '3 Months', '6 Months', 'Valid']
        data = []
        
        # Expired
        data.append(Document.search_count([('expiry_date', '<', today)]))
        
        # This week
        data.append(Document.search_count([
            ('expiry_date', '>=', today),
            ('expiry_date', '<=', today + timedelta(days=7))
        ]))
        
        # This month
        data.append(Document.search_count([
            ('expiry_date', '>', today + timedelta(days=7)),
            ('expiry_date', '<=', today + timedelta(days=30))
        ]))
        
        # 3 months
        data.append(Document.search_count([
            ('expiry_date', '>', today + timedelta(days=30)),
            ('expiry_date', '<=', today + timedelta(days=90))
        ]))
        
        # 6 months
        data.append(Document.search_count([
            ('expiry_date', '>', today + timedelta(days=90)),
            ('expiry_date', '<=', today + timedelta(days=180))
        ]))
        
        # Valid (more than 6 months)
        data.append(Document.search_count([
            ('expiry_date', '>', today + timedelta(days=180))
        ]))
        
        return {
            'id': 'document_expiry',
            'title': 'Document Expiry Timeline',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Documents',
                'data': data,
                'backgroundColor': ['#F44336', '#FF5722', '#FF9800', '#FFC107', '#CDDC39', '#4CAF50'],
            }]
        }

    def _get_wps_compliance_chart(self):
        """Get WPS compliance status."""
        if 'tazweed.wps.file' not in self.env:
            return self._empty_chart('wps_compliance', 'WPS Compliance')
        
        WPSFile = self.env['tazweed.wps.file'].sudo()
        
        states = [
            ('draft', 'Draft', '#9E9E9E'),
            ('generated', 'Generated', '#2196F3'),
            ('submitted', 'Submitted', '#FF9800'),
            ('processed', 'Processed', '#4CAF50'),
            ('rejected', 'Rejected', '#F44336'),
        ]
        
        labels = []
        data = []
        colors = []
        
        for state, label, color in states:
            count = WPSFile.search_count([('state', '=', state)])
            if count > 0:
                labels.append(label)
                data.append(count)
                colors.append(color)
        
        return {
            'id': 'wps_compliance',
            'title': 'WPS File Status',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors,
            }]
        }

    # ==========================================
    # WORKFLOW DASHBOARD CHARTS
    # ==========================================
    
    def _get_workflow_charts(self, date_from, date_to):
        """Get charts for workflow dashboard."""
        return [
            self._get_workflow_instances_chart(date_from, date_to),
            self._get_workflow_by_type_chart(date_from, date_to),
            self._get_workflow_completion_chart(),
        ]

    def _get_workflow_instances_chart(self, date_from, date_to):
        """Get workflow instances by status."""
        if 'tazweed.workflow.instance' not in self.env:
            return self._empty_chart('workflow_instances', 'Workflow Instances')
        
        WorkflowInstance = self.env['tazweed.workflow.instance'].sudo()
        
        states = [
            ('draft', 'Draft', '#9E9E9E'),
            ('running', 'Running', '#2196F3'),
            ('pending', 'Pending Approval', '#FF9800'),
            ('completed', 'Completed', '#4CAF50'),
            ('cancelled', 'Cancelled', '#F44336'),
        ]
        
        labels = []
        data = []
        colors = []
        
        for state, label, color in states:
            count = WorkflowInstance.search_count([
                ('state', '=', state),
                ('create_date', '>=', date_from),
                ('create_date', '<=', date_to)
            ])
            if count > 0:
                labels.append(label)
                data.append(count)
                colors.append(color)
        
        return {
            'id': 'workflow_instances',
            'title': 'Workflow Instances',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors,
            }]
        }

    def _get_workflow_by_type_chart(self, date_from, date_to):
        """Get workflows by type."""
        if 'tazweed.workflow.instance' not in self.env:
            return self._empty_chart('workflow_by_type', 'Workflows by Type')
        
        self.env.cr.execute("""
            SELECT d.name, COUNT(i.id) as count
            FROM tazweed_workflow_instance i
            JOIN tazweed_workflow_definition d ON i.workflow_id = d.id
            WHERE i.create_date >= %s AND i.create_date <= %s
            GROUP BY d.id, d.name
            ORDER BY count DESC
            LIMIT 10
        """, (date_from, date_to))
        
        results = self.env.cr.fetchall()
        
        labels = [r[0] for r in results] if results else ['No Data']
        data = [r[1] for r in results] if results else [0]
        
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', 
                  '#00BCD4', '#607D8B', '#795548', '#E91E63', '#3F51B5']
        
        return {
            'id': 'workflow_by_type',
            'title': 'Top Workflow Types',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Instances',
                'data': data,
                'backgroundColor': colors[:len(data)],
            }]
        }

    def _get_workflow_completion_chart(self):
        """Get workflow completion trend."""
        if 'tazweed.workflow.instance' not in self.env:
            return self._empty_chart('workflow_completion', 'Workflow Completion')
        
        WorkflowInstance = self.env['tazweed.workflow.instance'].sudo()
        
        labels = []
        started_data = []
        completed_data = []
        today = fields.Date.today()
        
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            month_start = date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            labels.append(date.strftime('%b'))
            
            started = WorkflowInstance.search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ])
            completed = WorkflowInstance.search_count([
                ('state', '=', 'completed'),
                ('write_date', '>=', month_start),
                ('write_date', '<=', month_end)
            ])
            
            started_data.append(started)
            completed_data.append(completed)
        
        return {
            'id': 'workflow_completion',
            'title': 'Workflow Trend',
            'type': 'line',
            'labels': labels,
            'datasets': [
                {
                    'label': 'Started',
                    'data': started_data,
                    'borderColor': '#2196F3',
                    'fill': False,
                },
                {
                    'label': 'Completed',
                    'data': completed_data,
                    'borderColor': '#4CAF50',
                    'fill': False,
                }
            ]
        }

    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def _empty_chart(self, chart_id, title):
        """Return an empty chart placeholder."""
        return {
            'id': chart_id,
            'title': title,
            'type': 'empty',
            'message': 'No data available',
            'labels': [],
            'datasets': []
        }

    def export_to_pdf(self):
        """Export dashboard to PDF."""
        # This would be implemented with a report action
        return self.env.ref('tazweed_analytics_dashboard.action_report_dashboard').report_action(self)

    def export_to_excel(self):
        """Export dashboard data to Excel."""
        # This would generate an Excel file with all dashboard data
        data = self.get_dashboard_data()
        # Implementation would use xlsxwriter or openpyxl
        return True
