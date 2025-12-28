# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
        ('compliance', 'Compliance'),
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

    def get_dashboard_data(self):
        """Get all data for the dashboard."""
        self.ensure_one()
        
        data = {
            'dashboard': {
                'id': self.id,
                'name': self.name,
                'type': self.dashboard_type,
                'layout': self.layout,
                'columns': self.columns,
            },
            'kpis': [],
            'charts': [],
            'summary': self._get_summary_data(),
        }
        
        # Get KPI data
        for kpi in self.kpi_ids:
            data['kpis'].append(kpi.get_kpi_data())
        
        # Get chart data based on dashboard type
        if self.dashboard_type == 'executive':
            data['charts'] = self._get_executive_charts()
        elif self.dashboard_type == 'hr_operations':
            data['charts'] = self._get_hr_operations_charts()
        elif self.dashboard_type == 'payroll':
            data['charts'] = self._get_payroll_charts()
        elif self.dashboard_type == 'recruitment':
            data['charts'] = self._get_recruitment_charts()
        elif self.dashboard_type == 'client':
            data['charts'] = self._get_client_charts()
        elif self.dashboard_type == 'compliance':
            data['charts'] = self._get_compliance_charts()
        
        return data

    def _get_summary_data(self):
        """Get summary statistics."""
        Employee = self.env['hr.employee'].sudo()
        Contract = self.env['hr.contract'].sudo()
        
        today = fields.Date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        
        return {
            'total_employees': Employee.search_count([('active', '=', True)]),
            'active_contracts': Contract.search_count([('state', '=', 'open')]),
            'new_hires_month': Employee.search_count([
                ('create_date', '>=', month_start)
            ]),
            'new_hires_year': Employee.search_count([
                ('create_date', '>=', year_start)
            ]),
        }

    def _get_executive_charts(self):
        """Get charts for executive dashboard."""
        return [
            self._get_headcount_trend_chart(),
            self._get_department_distribution_chart(),
            self._get_turnover_chart(),
            self._get_cost_analysis_chart(),
        ]

    def _get_hr_operations_charts(self):
        """Get charts for HR operations dashboard."""
        return [
            self._get_leave_analysis_chart(),
            self._get_attendance_chart(),
            self._get_employee_status_chart(),
        ]

    def _get_payroll_charts(self):
        """Get charts for payroll dashboard."""
        return [
            self._get_payroll_trend_chart(),
            self._get_salary_distribution_chart(),
            self._get_payroll_by_department_chart(),
        ]

    def _get_recruitment_charts(self):
        """Get charts for recruitment dashboard."""
        return [
            self._get_placement_pipeline_chart(),
            self._get_time_to_hire_chart(),
            self._get_source_effectiveness_chart(),
        ]

    def _get_client_charts(self):
        """Get charts for client dashboard."""
        return [
            self._get_client_revenue_chart(),
            self._get_placement_by_client_chart(),
            self._get_client_profitability_chart(),
        ]

    def _get_compliance_charts(self):
        """Get charts for compliance dashboard."""
        return [
            self._get_emiratization_chart(),
            self._get_visa_status_chart(),
            self._get_document_expiry_chart(),
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
                'fill': True,
            }]
        }

    def _get_department_distribution_chart(self):
        """Get employee distribution by department."""
        Employee = self.env['hr.employee'].sudo()
        
        departments = self.env['hr.department'].sudo().search([])
        labels = []
        data = []
        colors = ['#2196F3', '#4CAF50', '#FF9800', '#F44336', '#9C27B0', '#00BCD4', '#607D8B']
        
        for i, dept in enumerate(departments[:7]):
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
            
            # Calculate turnover rate
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

    def _get_cost_analysis_chart(self):
        """Get payroll cost analysis."""
        labels = ['Basic Salary', 'Housing', 'Transport', 'Other Allowances', 'Overtime']
        data = [60, 15, 10, 10, 5]  # Placeholder percentages
        
        return {
            'id': 'cost_analysis',
            'title': 'Payroll Cost Breakdown',
            'type': 'pie',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#00BCD4'],
            }]
        }

    def _get_leave_analysis_chart(self):
        """Get leave analysis."""
        labels = ['Annual', 'Sick', 'Unpaid', 'Maternity', 'Other']
        data = [45, 25, 15, 10, 5]  # Placeholder
        
        return {
            'id': 'leave_analysis',
            'title': 'Leave Distribution',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': ['#4CAF50', '#F44336', '#FF9800', '#9C27B0', '#607D8B'],
            }]
        }

    def _get_attendance_chart(self):
        """Get attendance trend."""
        labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        data = [95, 97, 96, 94, 92, 45, 10]  # Placeholder attendance %
        
        return {
            'id': 'attendance_trend',
            'title': 'Weekly Attendance Rate (%)',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Attendance %',
                'data': data,
                'backgroundColor': '#4CAF50',
            }]
        }

    def _get_employee_status_chart(self):
        """Get employee status distribution."""
        Employee = self.env['hr.employee'].sudo()
        
        active = Employee.search_count([('active', '=', True)])
        probation = Employee.search_count([
            ('active', '=', True),
            # Add probation filter if field exists
        ])
        
        return {
            'id': 'employee_status',
            'title': 'Employee Status',
            'type': 'doughnut',
            'labels': ['Active', 'Probation', 'Notice Period'],
            'datasets': [{
                'data': [active - probation, probation, 0],
                'backgroundColor': ['#4CAF50', '#FF9800', '#F44336'],
            }]
        }

    def _get_payroll_trend_chart(self):
        """Get payroll cost trend."""
        labels = []
        data = []
        today = fields.Date.today()
        
        for i in range(5, -1, -1):
            date = today - relativedelta(months=i)
            labels.append(date.strftime('%b %Y'))
            # Placeholder data - would calculate from actual payslips
            data.append(500000 + (i * 10000))
        
        return {
            'id': 'payroll_trend',
            'title': 'Monthly Payroll Cost (AED)',
            'type': 'line',
            'labels': labels,
            'datasets': [{
                'label': 'Payroll Cost',
                'data': data,
                'borderColor': '#2196F3',
                'fill': True,
            }]
        }

    def _get_salary_distribution_chart(self):
        """Get salary distribution."""
        labels = ['< 5K', '5K-10K', '10K-15K', '15K-25K', '> 25K']
        data = [15, 35, 25, 15, 10]  # Placeholder
        
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
        departments = self.env['hr.department'].sudo().search([], limit=6)
        labels = [d.name for d in departments]
        data = [100000, 150000, 80000, 120000, 90000, 60000][:len(labels)]  # Placeholder
        
        return {
            'id': 'payroll_by_dept',
            'title': 'Payroll by Department (AED)',
            'type': 'horizontalBar',
            'labels': labels,
            'datasets': [{
                'label': 'Cost',
                'data': data,
                'backgroundColor': '#00BCD4',
            }]
        }

    def _get_placement_pipeline_chart(self):
        """Get placement pipeline."""
        labels = ['New', 'Screening', 'Interview', 'Offer', 'Placed']
        data = [25, 18, 12, 8, 5]  # Placeholder
        
        return {
            'id': 'placement_pipeline',
            'title': 'Placement Pipeline',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Candidates',
                'data': data,
                'backgroundColor': ['#2196F3', '#03A9F4', '#00BCD4', '#009688', '#4CAF50'],
            }]
        }

    def _get_time_to_hire_chart(self):
        """Get time to hire trend."""
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        data = [25, 22, 28, 20, 18, 21]  # Days
        
        return {
            'id': 'time_to_hire',
            'title': 'Average Time to Hire (Days)',
            'type': 'line',
            'labels': labels,
            'datasets': [{
                'label': 'Days',
                'data': data,
                'borderColor': '#FF9800',
            }]
        }

    def _get_source_effectiveness_chart(self):
        """Get recruitment source effectiveness."""
        labels = ['Job Boards', 'Referrals', 'LinkedIn', 'Walk-ins', 'Agencies']
        data = [35, 25, 20, 12, 8]  # Percentage
        
        return {
            'id': 'source_effectiveness',
            'title': 'Recruitment Sources',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': ['#2196F3', '#4CAF50', '#0077B5', '#FF9800', '#9C27B0'],
            }]
        }

    def _get_client_revenue_chart(self):
        """Get client revenue trend."""
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
        data = [250000, 280000, 320000, 290000, 350000, 380000]
        
        return {
            'id': 'client_revenue',
            'title': 'Monthly Revenue (AED)',
            'type': 'line',
            'labels': labels,
            'datasets': [{
                'label': 'Revenue',
                'data': data,
                'borderColor': '#4CAF50',
                'fill': True,
            }]
        }

    def _get_placement_by_client_chart(self):
        """Get placements by client."""
        labels = ['Client A', 'Client B', 'Client C', 'Client D', 'Others']
        data = [45, 30, 25, 20, 30]
        
        return {
            'id': 'placement_by_client',
            'title': 'Placements by Client',
            'type': 'pie',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#607D8B'],
            }]
        }

    def _get_client_profitability_chart(self):
        """Get client profitability."""
        labels = ['Client A', 'Client B', 'Client C', 'Client D', 'Client E']
        revenue = [100000, 80000, 60000, 50000, 40000]
        cost = [70000, 55000, 45000, 38000, 32000]
        
        return {
            'id': 'client_profitability',
            'title': 'Client Profitability (AED)',
            'type': 'bar',
            'labels': labels,
            'datasets': [
                {'label': 'Revenue', 'data': revenue, 'backgroundColor': '#4CAF50'},
                {'label': 'Cost', 'data': cost, 'backgroundColor': '#F44336'},
            ]
        }

    def _get_emiratization_chart(self):
        """Get Emiratization status."""
        Employee = self.env['hr.employee'].sudo()
        
        total = Employee.search_count([('active', '=', True)]) or 1
        # Assuming there's a nationality field
        uae_nationals = 0  # Would filter by nationality
        
        target = 10  # Target percentage
        current = (uae_nationals / total) * 100
        
        return {
            'id': 'emiratization',
            'title': 'Emiratization Status',
            'type': 'gauge',
            'value': round(current, 1),
            'target': target,
            'max': 20,
        }

    def _get_visa_status_chart(self):
        """Get visa status distribution."""
        labels = ['Valid', 'Expiring Soon', 'Expired', 'In Process']
        data = [120, 15, 5, 10]  # Placeholder
        
        return {
            'id': 'visa_status',
            'title': 'Visa Status',
            'type': 'doughnut',
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': ['#4CAF50', '#FF9800', '#F44336', '#2196F3'],
            }]
        }

    def _get_document_expiry_chart(self):
        """Get document expiry timeline."""
        labels = ['This Week', 'This Month', 'Next Month', '2-3 Months', '3+ Months']
        data = [3, 8, 12, 25, 102]  # Documents expiring
        
        return {
            'id': 'document_expiry',
            'title': 'Document Expiry Timeline',
            'type': 'bar',
            'labels': labels,
            'datasets': [{
                'label': 'Documents',
                'data': data,
                'backgroundColor': ['#F44336', '#FF9800', '#FFC107', '#8BC34A', '#4CAF50'],
            }]
        }
