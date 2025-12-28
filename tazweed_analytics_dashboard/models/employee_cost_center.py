# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class EmployeeCostCenter(models.Model):
    """Employee Cost Center for comprehensive cost analysis."""
    
    _name = 'employee.cost.center'
    _description = 'Employee Cost Center'
    _order = 'date desc, employee_id'
    _rec_name = 'display_name'
    
    # Period Information
    date = fields.Date(string='Period Date', required=True, index=True)
    period_type = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ], string='Period Type', default='monthly', required=True)
    
    # Employee Information
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, 
                                   ondelete='cascade', index=True)
    employee_name = fields.Char(related='employee_id.name', store=True)
    
    # Department & Job
    department_id = fields.Many2one('hr.department', string='Department',
                                     related='employee_id.department_id', store=True)
    job_id = fields.Many2one('hr.job', string='Job Position',
                              related='employee_id.job_id', store=True)
    
    # Client & Placement (for staffing)
    client_id = fields.Many2one('tazweed.client', string='Client')
    placement_id = fields.Many2one('tazweed.placement', string='Placement')
    
    # Cost Categories
    basic_salary = fields.Float(string='Basic Salary', digits=(16, 2))
    housing_allowance = fields.Float(string='Housing Allowance', digits=(16, 2))
    transport_allowance = fields.Float(string='Transport Allowance', digits=(16, 2))
    food_allowance = fields.Float(string='Food Allowance', digits=(16, 2))
    other_allowances = fields.Float(string='Other Allowances', digits=(16, 2))
    
    # Gross Salary
    gross_salary = fields.Float(string='Gross Salary', digits=(16, 2),
                                 compute='_compute_gross_salary', store=True)
    
    # Employer Contributions
    pension_contribution = fields.Float(string='Pension Contribution', digits=(16, 2),
                                         help='Employer pension contribution (UAE nationals)')
    medical_insurance = fields.Float(string='Medical Insurance', digits=(16, 2))
    life_insurance = fields.Float(string='Life Insurance', digits=(16, 2))
    workman_compensation = fields.Float(string='Workman Compensation', digits=(16, 2))
    
    # Visa & PRO Costs
    visa_cost = fields.Float(string='Visa Cost', digits=(16, 2))
    labor_card_cost = fields.Float(string='Labor Card Cost', digits=(16, 2))
    emirates_id_cost = fields.Float(string='Emirates ID Cost', digits=(16, 2))
    medical_test_cost = fields.Float(string='Medical Test Cost', digits=(16, 2))
    pro_service_cost = fields.Float(string='PRO Service Cost', digits=(16, 2))
    
    # Training & Development
    training_cost = fields.Float(string='Training Cost', digits=(16, 2))
    certification_cost = fields.Float(string='Certification Cost', digits=(16, 2))
    
    # Equipment & Assets
    equipment_cost = fields.Float(string='Equipment Cost', digits=(16, 2))
    uniform_cost = fields.Float(string='Uniform Cost', digits=(16, 2))
    
    # Overhead Allocation
    office_overhead = fields.Float(string='Office Overhead', digits=(16, 2))
    admin_overhead = fields.Float(string='Admin Overhead', digits=(16, 2))
    
    # Leave & Absence Costs
    leave_cost = fields.Float(string='Leave Cost', digits=(16, 2),
                               help='Cost of paid leave days')
    sick_leave_cost = fields.Float(string='Sick Leave Cost', digits=(16, 2))
    
    # End of Service
    gratuity_provision = fields.Float(string='Gratuity Provision', digits=(16, 2),
                                       help='Monthly provision for end of service gratuity')
    
    # Total Costs
    total_salary_cost = fields.Float(string='Total Salary Cost', digits=(16, 2),
                                      compute='_compute_total_costs', store=True)
    total_benefits_cost = fields.Float(string='Total Benefits Cost', digits=(16, 2),
                                        compute='_compute_total_costs', store=True)
    total_compliance_cost = fields.Float(string='Total Compliance Cost', digits=(16, 2),
                                          compute='_compute_total_costs', store=True)
    total_overhead_cost = fields.Float(string='Total Overhead Cost', digits=(16, 2),
                                        compute='_compute_total_costs', store=True)
    total_cost = fields.Float(string='Total Cost', digits=(16, 2),
                               compute='_compute_total_costs', store=True)
    
    # Revenue (for staffing)
    billing_rate = fields.Float(string='Billing Rate', digits=(16, 2),
                                 help='Monthly billing rate to client')
    revenue = fields.Float(string='Revenue', digits=(16, 2))
    
    # Profitability
    gross_margin = fields.Float(string='Gross Margin', digits=(16, 2),
                                 compute='_compute_profitability', store=True)
    gross_margin_percent = fields.Float(string='Gross Margin %', digits=(5, 2),
                                         compute='_compute_profitability', store=True)
    
    # Display Name
    display_name = fields.Char(compute='_compute_display_name', store=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    
    @api.depends('employee_id', 'date')
    def _compute_display_name(self):
        for record in self:
            if record.employee_id and record.date:
                record.display_name = f"{record.employee_id.name} - {record.date.strftime('%b %Y')}"
            else:
                record.display_name = "New Cost Entry"
    
    @api.depends('basic_salary', 'housing_allowance', 'transport_allowance', 
                 'food_allowance', 'other_allowances')
    def _compute_gross_salary(self):
        for record in self:
            record.gross_salary = (
                record.basic_salary +
                record.housing_allowance +
                record.transport_allowance +
                record.food_allowance +
                record.other_allowances
            )
    
    @api.depends('gross_salary', 'pension_contribution', 'medical_insurance',
                 'life_insurance', 'workman_compensation', 'visa_cost',
                 'labor_card_cost', 'emirates_id_cost', 'medical_test_cost',
                 'pro_service_cost', 'training_cost', 'certification_cost',
                 'equipment_cost', 'uniform_cost', 'office_overhead',
                 'admin_overhead', 'leave_cost', 'sick_leave_cost', 'gratuity_provision')
    def _compute_total_costs(self):
        for record in self:
            # Salary costs
            record.total_salary_cost = record.gross_salary + record.leave_cost + record.sick_leave_cost
            
            # Benefits costs
            record.total_benefits_cost = (
                record.pension_contribution +
                record.medical_insurance +
                record.life_insurance +
                record.workman_compensation +
                record.gratuity_provision
            )
            
            # Compliance costs (visa, PRO, etc.)
            record.total_compliance_cost = (
                record.visa_cost +
                record.labor_card_cost +
                record.emirates_id_cost +
                record.medical_test_cost +
                record.pro_service_cost
            )
            
            # Overhead costs
            record.total_overhead_cost = (
                record.training_cost +
                record.certification_cost +
                record.equipment_cost +
                record.uniform_cost +
                record.office_overhead +
                record.admin_overhead
            )
            
            # Total cost
            record.total_cost = (
                record.total_salary_cost +
                record.total_benefits_cost +
                record.total_compliance_cost +
                record.total_overhead_cost
            )
    
    @api.depends('revenue', 'total_cost')
    def _compute_profitability(self):
        for record in self:
            record.gross_margin = record.revenue - record.total_cost
            if record.revenue > 0:
                record.gross_margin_percent = (record.gross_margin / record.revenue) * 100
            else:
                record.gross_margin_percent = 0
    
    @api.model
    def generate_cost_data(self, date_from=None, date_to=None):
        """Generate cost center data for all employees."""
        if not date_from:
            date_from = fields.Date.today().replace(day=1)
        if not date_to:
            date_to = fields.Date.today()
        
        employees = self.env['hr.employee'].search([('active', '=', True)])
        
        for employee in employees:
            # Check if entry already exists
            existing = self.search([
                ('employee_id', '=', employee.id),
                ('date', '=', date_from),
                ('period_type', '=', 'monthly')
            ], limit=1)
            
            if existing:
                continue
            
            # Get contract data
            contract = employee.contract_id
            
            # Get placement data
            placement = None
            client = None
            if 'tazweed.placement' in self.env:
                placement = self.env['tazweed.placement'].search([
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'active')
                ], limit=1)
                if placement:
                    client = placement.client_id
            
            # Calculate costs
            basic_salary = contract.wage if contract else 0
            housing = getattr(contract, 'housing_allowance', 0) if contract else 0
            transport = getattr(contract, 'transport_allowance', 0) if contract else 0
            food = getattr(contract, 'food_allowance', 0) if contract else 0
            other = getattr(contract, 'other_allowances', 0) if contract else 0
            
            # Create cost entry
            self.create({
                'date': date_from,
                'period_type': 'monthly',
                'employee_id': employee.id,
                'client_id': client.id if client else False,
                'placement_id': placement.id if placement else False,
                'basic_salary': basic_salary,
                'housing_allowance': housing,
                'transport_allowance': transport,
                'food_allowance': food,
                'other_allowances': other,
                # Default provisions
                'gratuity_provision': basic_salary * 0.0575,  # ~21 days per year
                'medical_insurance': 500,  # Default estimate
            })
        
        return True


class EmployeeCostCenterDashboard(models.Model):
    """Cost Center Dashboard for analytics."""
    
    _name = 'employee.cost.center.dashboard'
    _description = 'Employee Cost Center Dashboard'
    _rec_name = 'name'
    
    name = fields.Char(string='Dashboard Name', required=True, default='Cost Center Dashboard')
    
    # Filters
    date_from = fields.Date(string='From Date', 
                             default=lambda self: fields.Date.today().replace(day=1) - relativedelta(months=11))
    date_to = fields.Date(string='To Date', default=fields.Date.today)
    
    department_ids = fields.Many2many('hr.department', string='Departments')
    client_ids = fields.Many2many('tazweed.client', string='Clients')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    
    # View Type
    view_type = fields.Selection([
        ('summary', 'Summary'),
        ('by_employee', 'By Employee'),
        ('by_department', 'By Department'),
        ('by_client', 'By Client'),
        ('by_cost_type', 'By Cost Type'),
        ('trend', 'Trend Analysis'),
    ], string='View Type', default='summary')
    
    # Dashboard Data (JSON)
    dashboard_data = fields.Text(string='Dashboard Data', compute='_compute_dashboard_data')
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    
    def _compute_dashboard_data(self):
        for record in self:
            record.dashboard_data = json.dumps(record.get_dashboard_data())
    
    def get_dashboard_data(self):
        """Get comprehensive dashboard data."""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.department_ids:
            domain.append(('department_id', 'in', self.department_ids.ids))
        if self.client_ids:
            domain.append(('client_id', 'in', self.client_ids.ids))
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
        
        CostCenter = self.env['employee.cost.center']
        records = CostCenter.search(domain)
        
        return {
            'summary': self._get_summary_data(records),
            'by_employee': self._get_by_employee_data(records),
            'by_department': self._get_by_department_data(records),
            'by_client': self._get_by_client_data(records),
            'by_cost_type': self._get_by_cost_type_data(records),
            'trend': self._get_trend_data(domain),
            'charts': self._get_charts(records),
            'kpis': self._get_kpis(records),
        }
    
    def _get_summary_data(self, records):
        """Get summary statistics."""
        if not records:
            return {
                'total_employees': 0,
                'total_cost': 0,
                'total_revenue': 0,
                'total_margin': 0,
                'avg_cost_per_employee': 0,
                'margin_percent': 0,
            }
        
        total_cost = sum(records.mapped('total_cost'))
        total_revenue = sum(records.mapped('revenue'))
        total_margin = total_revenue - total_cost
        unique_employees = len(set(records.mapped('employee_id.id')))
        
        return {
            'total_employees': unique_employees,
            'total_cost': total_cost,
            'total_revenue': total_revenue,
            'total_margin': total_margin,
            'avg_cost_per_employee': total_cost / unique_employees if unique_employees else 0,
            'margin_percent': (total_margin / total_revenue * 100) if total_revenue else 0,
        }
    
    def _get_by_employee_data(self, records):
        """Get cost breakdown by employee."""
        employee_data = {}
        
        for record in records:
            emp_id = record.employee_id.id
            if emp_id not in employee_data:
                employee_data[emp_id] = {
                    'employee_id': emp_id,
                    'employee_name': record.employee_name,
                    'department': record.department_id.name if record.department_id else 'N/A',
                    'client': record.client_id.name if record.client_id else 'Internal',
                    'total_cost': 0,
                    'salary_cost': 0,
                    'benefits_cost': 0,
                    'compliance_cost': 0,
                    'overhead_cost': 0,
                    'revenue': 0,
                    'margin': 0,
                }
            
            employee_data[emp_id]['total_cost'] += record.total_cost
            employee_data[emp_id]['salary_cost'] += record.total_salary_cost
            employee_data[emp_id]['benefits_cost'] += record.total_benefits_cost
            employee_data[emp_id]['compliance_cost'] += record.total_compliance_cost
            employee_data[emp_id]['overhead_cost'] += record.total_overhead_cost
            employee_data[emp_id]['revenue'] += record.revenue
            employee_data[emp_id]['margin'] += record.gross_margin
        
        return list(employee_data.values())
    
    def _get_by_department_data(self, records):
        """Get cost breakdown by department."""
        dept_data = {}
        
        for record in records:
            dept_name = record.department_id.name if record.department_id else 'Unassigned'
            if dept_name not in dept_data:
                dept_data[dept_name] = {
                    'department': dept_name,
                    'employee_count': set(),
                    'total_cost': 0,
                    'salary_cost': 0,
                    'benefits_cost': 0,
                    'revenue': 0,
                    'margin': 0,
                }
            
            dept_data[dept_name]['employee_count'].add(record.employee_id.id)
            dept_data[dept_name]['total_cost'] += record.total_cost
            dept_data[dept_name]['salary_cost'] += record.total_salary_cost
            dept_data[dept_name]['benefits_cost'] += record.total_benefits_cost
            dept_data[dept_name]['revenue'] += record.revenue
            dept_data[dept_name]['margin'] += record.gross_margin
        
        # Convert sets to counts
        for dept in dept_data.values():
            dept['employee_count'] = len(dept['employee_count'])
            dept['avg_cost'] = dept['total_cost'] / dept['employee_count'] if dept['employee_count'] else 0
        
        return list(dept_data.values())
    
    def _get_by_client_data(self, records):
        """Get cost breakdown by client."""
        client_data = {}
        
        for record in records:
            client_name = record.client_id.name if record.client_id else 'Internal/Unassigned'
            if client_name not in client_data:
                client_data[client_name] = {
                    'client': client_name,
                    'employee_count': set(),
                    'total_cost': 0,
                    'revenue': 0,
                    'margin': 0,
                    'margin_percent': 0,
                }
            
            client_data[client_name]['employee_count'].add(record.employee_id.id)
            client_data[client_name]['total_cost'] += record.total_cost
            client_data[client_name]['revenue'] += record.revenue
            client_data[client_name]['margin'] += record.gross_margin
        
        # Calculate percentages and convert sets
        for client in client_data.values():
            client['employee_count'] = len(client['employee_count'])
            if client['revenue'] > 0:
                client['margin_percent'] = (client['margin'] / client['revenue']) * 100
        
        return list(client_data.values())
    
    def _get_by_cost_type_data(self, records):
        """Get breakdown by cost type."""
        if not records:
            return []
        
        return [
            {
                'cost_type': 'Basic Salary',
                'amount': sum(records.mapped('basic_salary')),
                'color': '#2196F3',
            },
            {
                'cost_type': 'Housing Allowance',
                'amount': sum(records.mapped('housing_allowance')),
                'color': '#4CAF50',
            },
            {
                'cost_type': 'Transport Allowance',
                'amount': sum(records.mapped('transport_allowance')),
                'color': '#FF9800',
            },
            {
                'cost_type': 'Food Allowance',
                'amount': sum(records.mapped('food_allowance')),
                'color': '#9C27B0',
            },
            {
                'cost_type': 'Other Allowances',
                'amount': sum(records.mapped('other_allowances')),
                'color': '#00BCD4',
            },
            {
                'cost_type': 'Medical Insurance',
                'amount': sum(records.mapped('medical_insurance')),
                'color': '#E91E63',
            },
            {
                'cost_type': 'Pension Contribution',
                'amount': sum(records.mapped('pension_contribution')),
                'color': '#673AB7',
            },
            {
                'cost_type': 'Gratuity Provision',
                'amount': sum(records.mapped('gratuity_provision')),
                'color': '#3F51B5',
            },
            {
                'cost_type': 'Visa & PRO Costs',
                'amount': sum(records.mapped('total_compliance_cost')),
                'color': '#009688',
            },
            {
                'cost_type': 'Training & Equipment',
                'amount': sum(records.mapped('training_cost')) + sum(records.mapped('equipment_cost')),
                'color': '#795548',
            },
            {
                'cost_type': 'Overhead',
                'amount': sum(records.mapped('office_overhead')) + sum(records.mapped('admin_overhead')),
                'color': '#607D8B',
            },
        ]
    
    def _get_trend_data(self, base_domain):
        """Get monthly trend data."""
        CostCenter = self.env['employee.cost.center']
        trend_data = []
        
        today = fields.Date.today()
        for i in range(11, -1, -1):
            date = today - relativedelta(months=i)
            month_start = date.replace(day=1)
            month_end = (month_start + relativedelta(months=1)) - timedelta(days=1)
            
            domain = [
                ('date', '>=', month_start),
                ('date', '<=', month_end),
            ]
            
            records = CostCenter.search(domain)
            
            trend_data.append({
                'month': date.strftime('%b %Y'),
                'total_cost': sum(records.mapped('total_cost')),
                'salary_cost': sum(records.mapped('total_salary_cost')),
                'benefits_cost': sum(records.mapped('total_benefits_cost')),
                'revenue': sum(records.mapped('revenue')),
                'margin': sum(records.mapped('gross_margin')),
                'employee_count': len(set(records.mapped('employee_id.id'))),
            })
        
        return trend_data
    
    def _get_charts(self, records):
        """Get chart configurations."""
        cost_type_data = self._get_by_cost_type_data(records)
        dept_data = self._get_by_department_data(records)
        client_data = self._get_by_client_data(records)
        
        return [
            {
                'id': 'cost_breakdown',
                'title': 'Cost Breakdown by Type',
                'type': 'doughnut',
                'labels': [d['cost_type'] for d in cost_type_data if d['amount'] > 0],
                'datasets': [{
                    'data': [d['amount'] for d in cost_type_data if d['amount'] > 0],
                    'backgroundColor': [d['color'] for d in cost_type_data if d['amount'] > 0],
                }]
            },
            {
                'id': 'cost_by_department',
                'title': 'Total Cost by Department',
                'type': 'bar',
                'labels': [d['department'] for d in dept_data],
                'datasets': [{
                    'label': 'Total Cost',
                    'data': [d['total_cost'] for d in dept_data],
                    'backgroundColor': '#2196F3',
                }]
            },
            {
                'id': 'cost_by_client',
                'title': 'Total Cost by Client',
                'type': 'bar',
                'labels': [d['client'] for d in client_data[:10]],  # Top 10
                'datasets': [{
                    'label': 'Cost',
                    'data': [d['total_cost'] for d in client_data[:10]],
                    'backgroundColor': '#4CAF50',
                }, {
                    'label': 'Revenue',
                    'data': [d['revenue'] for d in client_data[:10]],
                    'backgroundColor': '#FF9800',
                }]
            },
            {
                'id': 'margin_by_client',
                'title': 'Margin % by Client',
                'type': 'bar',
                'labels': [d['client'] for d in client_data[:10]],
                'datasets': [{
                    'label': 'Margin %',
                    'data': [d['margin_percent'] for d in client_data[:10]],
                    'backgroundColor': '#9C27B0',
                }]
            },
        ]
    
    def _get_kpis(self, records):
        """Get KPI cards."""
        summary = self._get_summary_data(records)
        
        return [
            {
                'name': 'Total Employees',
                'value': summary['total_employees'],
                'format': 'number',
                'icon': 'fa-users',
                'color': '#2196F3',
            },
            {
                'name': 'Total Cost',
                'value': summary['total_cost'],
                'format': 'currency',
                'icon': 'fa-money',
                'color': '#F44336',
            },
            {
                'name': 'Total Revenue',
                'value': summary['total_revenue'],
                'format': 'currency',
                'icon': 'fa-line-chart',
                'color': '#4CAF50',
            },
            {
                'name': 'Gross Margin',
                'value': summary['total_margin'],
                'format': 'currency',
                'icon': 'fa-balance-scale',
                'color': '#FF9800',
            },
            {
                'name': 'Avg Cost/Employee',
                'value': summary['avg_cost_per_employee'],
                'format': 'currency',
                'icon': 'fa-user',
                'color': '#9C27B0',
            },
            {
                'name': 'Margin %',
                'value': summary['margin_percent'],
                'format': 'percent',
                'icon': 'fa-percent',
                'color': '#00BCD4',
            },
        ]
    
    def action_refresh(self):
        """Refresh dashboard data."""
        self._compute_dashboard_data()
        return True
    
    def action_generate_cost_data(self):
        """Generate cost data for current period."""
        self.env['employee.cost.center'].generate_cost_data(
            self.date_from, self.date_to
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Cost data generated successfully'),
                'type': 'success',
            }
        }
    
    def action_export_excel(self):
        """Export cost data to Excel."""
        # This would generate an Excel report
        return True
    
    def action_export_pdf(self):
        """Export cost data to PDF."""
        # This would generate a PDF report
        return True
