# -*- coding: utf-8 -*-
"""
Organization Chart Module
=========================
Interactive visual organization chart with drag-drop functionality,
department hierarchy, and employee positioning.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging

_logger = logging.getLogger(__name__)


class OrganizationChart(models.Model):
    """Organization Chart Configuration"""
    _name = 'organization.chart'
    _description = 'Organization Chart'
    _order = 'sequence, name'

    name = fields.Char(string='Chart Name', required=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Chart type
    chart_type = fields.Selection([
        ('hierarchical', 'Hierarchical'),
        ('matrix', 'Matrix'),
        ('flat', 'Flat'),
    ], string='Chart Type', default='hierarchical', required=True)
    
    # Root configuration
    root_employee_id = fields.Many2one(
        'hr.employee',
        string='Root Employee',
        help='Top-level employee in the chart (usually CEO/MD)'
    )
    root_department_id = fields.Many2one(
        'hr.department',
        string='Root Department',
        help='Top-level department to display'
    )
    
    # Display options
    show_photos = fields.Boolean(string='Show Photos', default=True)
    show_job_title = fields.Boolean(string='Show Job Title', default=True)
    show_department = fields.Boolean(string='Show Department', default=True)
    show_email = fields.Boolean(string='Show Email', default=False)
    show_phone = fields.Boolean(string='Show Phone', default=False)
    show_vacant_positions = fields.Boolean(string='Show Vacant Positions', default=False)
    
    # Styling
    node_color = fields.Char(string='Node Color', default='#875A7B')
    connector_color = fields.Char(string='Connector Color', default='#cccccc')
    
    # Statistics
    employee_count = fields.Integer(
        string='Employees',
        compute='_compute_statistics'
    )
    department_count = fields.Integer(
        string='Departments',
        compute='_compute_statistics'
    )
    
    def _compute_statistics(self):
        for chart in self:
            if chart.root_department_id:
                dept_ids = self._get_child_departments(chart.root_department_id)
                chart.department_count = len(dept_ids)
                chart.employee_count = self.env['hr.employee'].search_count([
                    ('department_id', 'in', dept_ids)
                ])
            else:
                chart.department_count = self.env['hr.department'].search_count([])
                chart.employee_count = self.env['hr.employee'].search_count([])
    
    def _get_child_departments(self, department):
        """Get all child departments recursively"""
        result = [department.id]
        for child in department.child_ids:
            result.extend(self._get_child_departments(child))
        return result
    
    def get_chart_data(self):
        """Get organization chart data in JSON format for visualization"""
        self.ensure_one()
        
        if self.chart_type == 'hierarchical':
            return self._get_hierarchical_data()
        elif self.chart_type == 'matrix':
            return self._get_matrix_data()
        else:
            return self._get_flat_data()
    
    def _get_hierarchical_data(self):
        """Generate hierarchical chart data"""
        self.ensure_one()
        
        def build_employee_node(employee):
            """Build node data for an employee"""
            subordinates = self.env['hr.employee'].search([
                ('parent_id', '=', employee.id)
            ])
            
            node = {
                'id': employee.id,
                'name': employee.name,
                'title': employee.job_id.name if employee.job_id else '',
                'department': employee.department_id.name if employee.department_id else '',
                'email': employee.work_email or '',
                'phone': employee.work_phone or '',
                'image': f'/web/image/hr.employee/{employee.id}/image_128' if employee.image_128 else '',
                'children': [],
            }
            
            for sub in subordinates:
                node['children'].append(build_employee_node(sub))
            
            return node
        
        def build_department_node(department):
            """Build node data for a department"""
            manager = department.manager_id
            
            node = {
                'id': f'dept_{department.id}',
                'name': department.name,
                'type': 'department',
                'manager': {
                    'id': manager.id if manager else None,
                    'name': manager.name if manager else 'Vacant',
                    'title': manager.job_id.name if manager and manager.job_id else '',
                    'image': f'/web/image/hr.employee/{manager.id}/image_128' if manager and manager.image_128 else '',
                } if manager or self.show_vacant_positions else None,
                'children': [],
            }
            
            # Add child departments
            for child_dept in department.child_ids:
                node['children'].append(build_department_node(child_dept))
            
            # Add employees in this department (excluding manager)
            employees = self.env['hr.employee'].search([
                ('department_id', '=', department.id),
                ('id', '!=', manager.id if manager else 0),
                ('parent_id', '=', manager.id if manager else False),
            ])
            
            for emp in employees:
                emp_node = build_employee_node(emp)
                emp_node['type'] = 'employee'
                node['children'].append(emp_node)
            
            return node
        
        # Build chart starting from root
        if self.root_employee_id:
            return build_employee_node(self.root_employee_id)
        elif self.root_department_id:
            return build_department_node(self.root_department_id)
        else:
            # Find top-level departments
            top_depts = self.env['hr.department'].search([
                ('parent_id', '=', False)
            ])
            return {
                'id': 'root',
                'name': 'Organization',
                'type': 'root',
                'children': [build_department_node(d) for d in top_depts]
            }
    
    def _get_matrix_data(self):
        """Generate matrix chart data"""
        self.ensure_one()
        
        departments = self.env['hr.department'].search([])
        employees = self.env['hr.employee'].search([])
        
        return {
            'type': 'matrix',
            'departments': [{
                'id': d.id,
                'name': d.name,
                'manager_id': d.manager_id.id if d.manager_id else None,
            } for d in departments],
            'employees': [{
                'id': e.id,
                'name': e.name,
                'department_id': e.department_id.id if e.department_id else None,
                'job_title': e.job_id.name if e.job_id else '',
                'image': f'/web/image/hr.employee/{e.id}/image_128' if e.image_128 else '',
            } for e in employees],
        }
    
    def _get_flat_data(self):
        """Generate flat chart data"""
        self.ensure_one()
        
        employees = self.env['hr.employee'].search([])
        
        return {
            'type': 'flat',
            'employees': [{
                'id': e.id,
                'name': e.name,
                'department': e.department_id.name if e.department_id else '',
                'job_title': e.job_id.name if e.job_id else '',
                'manager': e.parent_id.name if e.parent_id else '',
                'image': f'/web/image/hr.employee/{e.id}/image_128' if e.image_128 else '',
            } for e in employees],
        }
    
    def action_view_chart(self):
        """Open the organization chart view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'organization_chart',
            'name': self.name,
            'params': {
                'chart_id': self.id,
            },
        }
    
    @api.model
    def get_default_chart_data(self):
        """Get default organization chart data"""
        # Find or create default chart
        chart = self.search([], limit=1)
        if not chart:
            chart = self.create({
                'name': 'Organization Chart',
                'chart_type': 'hierarchical',
            })
        return chart.get_chart_data()


class OrganizationChartNode(models.Model):
    """Custom positioning for chart nodes"""
    _name = 'organization.chart.node'
    _description = 'Organization Chart Node'

    chart_id = fields.Many2one(
        'organization.chart',
        string='Chart',
        required=True,
        ondelete='cascade'
    )
    
    # Node reference
    node_type = fields.Selection([
        ('employee', 'Employee'),
        ('department', 'Department'),
        ('position', 'Position'),
    ], string='Node Type', required=True)
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string='Position')
    
    # Custom positioning
    x_position = fields.Float(string='X Position')
    y_position = fields.Float(string='Y Position')
    
    # Custom styling
    custom_color = fields.Char(string='Custom Color')
    custom_label = fields.Char(string='Custom Label')
    is_highlighted = fields.Boolean(string='Highlighted', default=False)
    
    # Visibility
    is_collapsed = fields.Boolean(string='Collapsed', default=False)
    is_hidden = fields.Boolean(string='Hidden', default=False)


class HrDepartment(models.Model):
    """Extend HR Department for org chart"""
    _inherit = 'hr.department'
    
    org_chart_color = fields.Char(string='Org Chart Color', default='#875A7B')
    org_chart_icon = fields.Char(string='Org Chart Icon')
    
    # Hierarchy info
    level = fields.Integer(
        string='Hierarchy Level',
        compute='_compute_level',
        store=True
    )
    full_path = fields.Char(
        string='Full Path',
        compute='_compute_full_path',
        store=True
    )
    
    @api.depends('parent_id', 'parent_id.level')
    def _compute_level(self):
        for dept in self:
            if dept.parent_id:
                dept.level = dept.parent_id.level + 1
            else:
                dept.level = 0
    
    @api.depends('name', 'parent_id', 'parent_id.full_path')
    def _compute_full_path(self):
        for dept in self:
            if dept.parent_id:
                dept.full_path = f"{dept.parent_id.full_path} / {dept.name}"
            else:
                dept.full_path = dept.name
    
    def get_org_chart_data(self):
        """Get org chart data for this department and its children"""
        self.ensure_one()
        
        def build_node(department):
            return {
                'id': department.id,
                'name': department.name,
                'color': department.org_chart_color,
                'manager': {
                    'id': department.manager_id.id,
                    'name': department.manager_id.name,
                    'image': f'/web/image/hr.employee/{department.manager_id.id}/image_128',
                } if department.manager_id else None,
                'employee_count': self.env['hr.employee'].search_count([
                    ('department_id', '=', department.id)
                ]),
                'children': [build_node(child) for child in department.child_ids],
            }
        
        return build_node(self)


class HrEmployee(models.Model):
    """Extend HR Employee for org chart"""
    _inherit = 'hr.employee'
    
    org_chart_position = fields.Char(
        string='Org Chart Position',
        help='Custom position label for org chart'
    )
    reporting_line_ids = fields.Many2many(
        'hr.employee',
        'employee_reporting_line_rel',
        'employee_id',
        'reports_to_id',
        string='Additional Reporting Lines',
        help='For matrix organizations with multiple reporting lines'
    )
    
    # Computed fields for org chart
    direct_reports_count = fields.Integer(
        string='Direct Reports',
        compute='_compute_direct_reports'
    )
    total_reports_count = fields.Integer(
        string='Total Reports',
        compute='_compute_direct_reports'
    )
    
    def _compute_direct_reports(self):
        for employee in self:
            direct = self.search([('parent_id', '=', employee.id)])
            employee.direct_reports_count = len(direct)
            
            # Calculate total reports recursively
            def count_all_reports(emp):
                reports = self.search([('parent_id', '=', emp.id)])
                total = len(reports)
                for report in reports:
                    total += count_all_reports(report)
                return total
            
            employee.total_reports_count = count_all_reports(employee)
    
    def get_org_chart_data(self):
        """Get org chart data for this employee and their reports"""
        self.ensure_one()
        
        def build_node(employee):
            subordinates = self.search([('parent_id', '=', employee.id)])
            return {
                'id': employee.id,
                'name': employee.name,
                'title': employee.job_id.name if employee.job_id else '',
                'department': employee.department_id.name if employee.department_id else '',
                'image': f'/web/image/hr.employee/{employee.id}/image_128' if employee.image_128 else '',
                'email': employee.work_email or '',
                'phone': employee.work_phone or '',
                'children': [build_node(sub) for sub in subordinates],
            }
        
        return build_node(self)
    
    def action_view_org_chart(self):
        """View org chart centered on this employee"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'organization_chart',
            'name': _('Organization Chart'),
            'params': {
                'employee_id': self.id,
            },
        }
    
    def action_view_direct_reports(self):
        """View direct reports"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Direct Reports'),
            'res_model': 'hr.employee',
            'view_mode': 'tree,form,kanban',
            'domain': [('parent_id', '=', self.id)],
        }
