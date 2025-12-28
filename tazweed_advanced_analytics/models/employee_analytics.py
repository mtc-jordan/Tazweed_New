from odoo import models, fields, api
from datetime import datetime, timedelta


class EmployeeAnalytics(models.Model):
    """Employee analytics and metrics."""
    
    _name = 'tazweed.employee.analytics'
    _description = 'Employee Analytics'
    _rec_name = 'analytics_name'
    
    analytics_name = fields.Char(
        string='Analytics Name',
        required=True
    )
    
    # Period
    period_start = fields.Date(
        string='Period Start',
        required=True
    )
    
    period_end = fields.Date(
        string='Period End',
        required=True
    )
    
    # Headcount Metrics
    total_headcount = fields.Integer(
        string='Total Headcount',
        compute='_compute_headcount_metrics',
        help='Total active employees'
    )
    
    new_hires = fields.Integer(
        string='New Hires',
        compute='_compute_headcount_metrics',
        help='New hires in period'
    )
    
    separations = fields.Integer(
        string='Separations',
        compute='_compute_headcount_metrics',
        help='Separations in period'
    )
    
    turnover_rate = fields.Float(
        string='Turnover Rate %',
        compute='_compute_headcount_metrics',
        help='Turnover rate'
    )
    
    # Department Distribution
    departments_count = fields.Integer(
        string='Departments',
        compute='_compute_department_distribution',
        help='Number of departments'
    )
    
    largest_department = fields.Many2one(
        'hr.department',
        string='Largest Department',
        compute='_compute_department_distribution',
        help='Largest department'
    )
    
    largest_department_size = fields.Integer(
        string='Largest Dept Size',
        compute='_compute_department_distribution',
        help='Size of largest department'
    )
    
    # Tenure Analysis
    average_tenure_years = fields.Float(
        string='Average Tenure (Years)',
        compute='_compute_tenure_analysis',
        help='Average tenure'
    )
    
    employees_less_1_year = fields.Integer(
        string='< 1 Year',
        compute='_compute_tenure_analysis',
        help='Employees with less than 1 year'
    )
    
    employees_1_5_years = fields.Integer(
        string='1-5 Years',
        compute='_compute_tenure_analysis',
        help='Employees with 1-5 years'
    )
    
    employees_5_10_years = fields.Integer(
        string='5-10 Years',
        compute='_compute_tenure_analysis',
        help='Employees with 5-10 years'
    )
    
    employees_10_plus_years = fields.Integer(
        string='10+ Years',
        compute='_compute_tenure_analysis',
        help='Employees with 10+ years'
    )
    
    # Leave Balance
    total_leave_balance = fields.Float(
        string='Total Leave Balance',
        compute='_compute_leave_balance',
        help='Total leave balance'
    )
    
    average_leave_balance = fields.Float(
        string='Average Leave Balance',
        compute='_compute_leave_balance',
        help='Average leave balance per employee'
    )
    
    employees_zero_balance = fields.Integer(
        string='Zero Balance',
        compute='_compute_leave_balance',
        help='Employees with zero leave balance'
    )
    
    # Attendance Metrics
    average_attendance_rate = fields.Float(
        string='Average Attendance %',
        compute='_compute_attendance_metrics',
        help='Average attendance rate'
    )
    
    total_absent_days = fields.Float(
        string='Total Absent Days',
        compute='_compute_attendance_metrics',
        help='Total absent days'
    )
    
    high_absenteeism_count = fields.Integer(
        string='High Absenteeism',
        compute='_compute_attendance_metrics',
        help='Employees with high absenteeism'
    )
    
    # Salary Analysis
    total_salary_expense = fields.Float(
        string='Total Salary Expense',
        compute='_compute_salary_analysis',
        help='Total salary expense'
    )
    
    average_salary = fields.Float(
        string='Average Salary',
        compute='_compute_salary_analysis',
        help='Average salary'
    )
    
    salary_min = fields.Float(
        string='Min Salary',
        compute='_compute_salary_analysis',
        help='Minimum salary'
    )
    
    salary_max = fields.Float(
        string='Max Salary',
        compute='_compute_salary_analysis',
        help='Maximum salary'
    )
    
    salary_range = fields.Float(
        string='Salary Range',
        compute='_compute_salary_analysis',
        help='Salary range'
    )
    
    @api.depends('period_start', 'period_end')
    def _compute_headcount_metrics(self):
        """Compute headcount metrics."""
        for record in self:
            # Total active employees
            active_employees = self.env['hr.employee'].search([
                ('active', '=', True),
                ('company_id', '=', self.env.company.id),
            ])
            
            record.total_headcount = len(active_employees)
            
            # New hires
            new_hires = self.env['hr.employee'].search([
                ('create_date', '>=', record.period_start),
                ('create_date', '<=', record.period_end),
            ])
            
            record.new_hires = len(new_hires)
            
            # Separations (archived employees)
            separations = self.env['hr.employee'].search([
                ('active', '=', False),
                ('write_date', '>=', record.period_start),
                ('write_date', '<=', record.period_end),
            ])
            
            record.separations = len(separations)
            
            # Turnover rate
            if record.total_headcount > 0:
                record.turnover_rate = (record.separations / record.total_headcount) * 100
            else:
                record.turnover_rate = 0
    
    @api.depends('period_start', 'period_end')
    def _compute_department_distribution(self):
        """Compute department distribution."""
        for record in self:
            employees = self.env['hr.employee'].search([
                ('active', '=', True),
                ('company_id', '=', self.env.company.id),
            ])
            
            departments = set(employees.mapped('department_id'))
            record.departments_count = len(departments)
            
            # Find largest department
            dept_counts = {}
            for emp in employees:
                if emp.department_id:
                    dept_counts[emp.department_id.id] = dept_counts.get(emp.department_id.id, 0) + 1
            
            if dept_counts:
                largest_dept_id = max(dept_counts, key=dept_counts.get)
                record.largest_department = largest_dept_id
                record.largest_department_size = dept_counts[largest_dept_id]
            else:
                record.largest_department = False
                record.largest_department_size = 0
    
    @api.depends('period_start', 'period_end')
    def _compute_tenure_analysis(self):
        """Compute tenure analysis."""
        for record in self:
            employees = self.env['hr.employee'].search([
                ('active', '=', True),
                ('company_id', '=', self.env.company.id),
            ])
            
            tenures = []
            for emp in employees:
                if emp.create_date:
                    tenure = (datetime.now().date() - emp.create_date.date()).days / 365.25
                    tenures.append(tenure)
            
            if tenures:
                record.average_tenure_years = sum(tenures) / len(tenures)
            else:
                record.average_tenure_years = 0
            
            record.employees_less_1_year = len([t for t in tenures if t < 1])
            record.employees_1_5_years = len([t for t in tenures if 1 <= t < 5])
            record.employees_5_10_years = len([t for t in tenures if 5 <= t < 10])
            record.employees_10_plus_years = len([t for t in tenures if t >= 10])
    
    @api.depends('period_start', 'period_end')
    def _compute_leave_balance(self):
        """Compute leave balance."""
        for record in self:
            leave_balances = self.env['tazweed.leave.balance'].search([
                ('employee_id.active', '=', True),
            ])
            
            record.total_leave_balance = sum(leave_balances.mapped('balance_days'))
            
            if len(leave_balances) > 0:
                record.average_leave_balance = record.total_leave_balance / len(leave_balances)
            else:
                record.average_leave_balance = 0
            
            record.employees_zero_balance = len(leave_balances.filtered(lambda l: l.balance_days == 0))
    
    @api.depends('period_start', 'period_end')
    def _compute_attendance_metrics(self):
        """Compute attendance metrics."""
        for record in self:
            attendances = self.env['tazweed.attendance'].search([
                ('attendance_date', '>=', record.period_start),
                ('attendance_date', '<=', record.period_end),
            ])
            
            # Calculate attendance rate
            total_days = (record.period_end - record.period_start).days
            employees = set(attendances.mapped('employee_id'))
            
            if employees and total_days > 0:
                present_days = len(attendances.filtered(lambda a: a.status == 'present'))
                total_expected = len(employees) * total_days
                record.average_attendance_rate = (present_days / total_expected) * 100 if total_expected > 0 else 0
            else:
                record.average_attendance_rate = 0
            
            # Absent days
            record.total_absent_days = len(attendances.filtered(lambda a: a.status == 'absent'))
            
            # High absenteeism (more than 10% absent)
            emp_absent_count = {}
            for att in attendances:
                emp_absent_count[att.employee_id.id] = emp_absent_count.get(att.employee_id.id, 0) + (1 if att.status == 'absent' else 0)
            
            record.high_absenteeism_count = len([count for count in emp_absent_count.values() if count > (total_days * 0.1)])
    
    @api.depends('period_start', 'period_end')
    def _compute_salary_analysis(self):
        """Compute salary analysis."""
        for record in self:
            payslips = self.env['tazweed.payslip'].search([
                ('payslip_date', '>=', record.period_start),
                ('payslip_date', '<=', record.period_end),
                ('state', 'in', ['confirmed', 'approved']),
            ])
            
            record.total_salary_expense = sum(payslips.mapped('gross_salary'))
            
            salaries = payslips.mapped('gross_salary')
            if salaries:
                record.average_salary = sum(salaries) / len(salaries)
                record.salary_min = min(salaries)
                record.salary_max = max(salaries)
                record.salary_range = record.salary_max - record.salary_min
            else:
                record.average_salary = 0
                record.salary_min = 0
                record.salary_max = 0
                record.salary_range = 0
