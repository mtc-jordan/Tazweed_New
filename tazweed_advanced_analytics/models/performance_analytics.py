from odoo import models, fields, api
from datetime import datetime, timedelta


class PerformanceAnalytics(models.Model):
    """Performance analytics and metrics."""
    
    _name = 'tazweed.performance.analytics'
    _description = 'Performance Analytics'
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
    
    # Employee Performance
    total_employees = fields.Integer(
        string='Total Employees',
        compute='_compute_employee_performance',
        help='Total employees'
    )
    
    average_rating = fields.Float(
        string='Average Rating',
        compute='_compute_employee_performance',
        help='Average performance rating'
    )
    
    excellent_count = fields.Integer(
        string='Excellent (4.5+)',
        compute='_compute_employee_performance',
        help='Employees with excellent rating'
    )
    
    good_count = fields.Integer(
        string='Good (4.0-4.49)',
        compute='_compute_employee_performance',
        help='Employees with good rating'
    )
    
    average_count = fields.Integer(
        string='Average (3.0-3.99)',
        compute='_compute_employee_performance',
        help='Employees with average rating'
    )
    
    poor_count = fields.Integer(
        string='Poor (<3.0)',
        compute='_compute_employee_performance',
        help='Employees with poor rating'
    )
    
    # Department Performance
    top_department = fields.Many2one(
        'hr.department',
        string='Top Department',
        compute='_compute_department_performance',
        help='Top performing department'
    )
    
    top_department_rating = fields.Float(
        string='Top Dept Rating',
        compute='_compute_department_performance',
        help='Top department average rating'
    )
    
    bottom_department = fields.Many2one(
        'hr.department',
        string='Bottom Department',
        compute='_compute_department_performance',
        help='Bottom performing department'
    )
    
    bottom_department_rating = fields.Float(
        string='Bottom Dept Rating',
        compute='_compute_department_performance',
        help='Bottom department average rating'
    )
    
    # Goal Metrics
    total_goals = fields.Integer(
        string='Total Goals',
        compute='_compute_goal_metrics',
        help='Total goals set'
    )
    
    goals_achieved = fields.Integer(
        string='Goals Achieved',
        compute='_compute_goal_metrics',
        help='Goals achieved'
    )
    
    goals_in_progress = fields.Integer(
        string='Goals In Progress',
        compute='_compute_goal_metrics',
        help='Goals in progress'
    )
    
    goal_achievement_rate = fields.Float(
        string='Goal Achievement %',
        compute='_compute_goal_metrics',
        help='Goal achievement rate'
    )
    
    # KPI Metrics
    total_kpis = fields.Integer(
        string='Total KPIs',
        compute='_compute_kpi_metrics',
        help='Total KPIs'
    )
    
    kpis_on_track = fields.Integer(
        string='KPIs On Track',
        compute='_compute_kpi_metrics',
        help='KPIs on track'
    )
    
    kpis_at_risk = fields.Integer(
        string='KPIs At Risk',
        compute='_compute_kpi_metrics',
        help='KPIs at risk'
    )
    
    kpi_achievement_rate = fields.Float(
        string='KPI Achievement %',
        compute='_compute_kpi_metrics',
        help='KPI achievement rate'
    )
    
    # Development Plans
    development_plans_active = fields.Integer(
        string='Active Development Plans',
        compute='_compute_development_metrics',
        help='Active development plans'
    )
    
    development_plans_completed = fields.Integer(
        string='Completed Development Plans',
        compute='_compute_development_metrics',
        help='Completed development plans'
    )
    
    # Trends
    performance_trend = fields.Selection(
        [('up', 'Up'), ('down', 'Down'), ('stable', 'Stable')],
        string='Performance Trend',
        compute='_compute_trends',
        help='Performance trend'
    )
    
    goal_trend = fields.Selection(
        [('up', 'Up'), ('down', 'Down'), ('stable', 'Stable')],
        string='Goal Trend',
        compute='_compute_trends',
        help='Goal achievement trend'
    )
    
    @api.depends('period_start', 'period_end')
    def _compute_employee_performance(self):
        """Compute employee performance metrics."""
        for record in self:
            appraisals = self.env['tazweed.hr.appraisal'].search([
                ('appraisal_date', '>=', record.period_start),
                ('appraisal_date', '<=', record.period_end),
                ('state', '=', 'approved'),
            ])
            
            record.total_employees = len(set(appraisals.mapped('employee_id')))
            
            ratings = [float(a.overall_rating) for a in appraisals if a.overall_rating]
            if ratings:
                record.average_rating = sum(ratings) / len(ratings)
            else:
                record.average_rating = 0
            
            record.excellent_count = len(appraisals.filtered(lambda a: float(a.overall_rating or 0) >= 4.5))
            record.good_count = len(appraisals.filtered(lambda a: 4.0 <= float(a.overall_rating or 0) < 4.5))
            record.average_count = len(appraisals.filtered(lambda a: 3.0 <= float(a.overall_rating or 0) < 4.0))
            record.poor_count = len(appraisals.filtered(lambda a: float(a.overall_rating or 0) < 3.0))
    
    @api.depends('period_start', 'period_end')
    def _compute_department_performance(self):
        """Compute department performance."""
        for record in self:
            appraisals = self.env['tazweed.hr.appraisal'].search([
                ('appraisal_date', '>=', record.period_start),
                ('appraisal_date', '<=', record.period_end),
                ('state', '=', 'approved'),
            ])
            
            dept_ratings = {}
            for appraisal in appraisals:
                dept = appraisal.employee_id.department_id
                if dept:
                    if dept.id not in dept_ratings:
                        dept_ratings[dept.id] = []
                    dept_ratings[dept.id].append(float(appraisal.overall_rating or 0))
            
            if dept_ratings:
                dept_averages = {dept_id: sum(ratings) / len(ratings) for dept_id, ratings in dept_ratings.items()}
                
                top_dept_id = max(dept_averages, key=dept_averages.get)
                record.top_department = top_dept_id
                record.top_department_rating = dept_averages[top_dept_id]
                
                bottom_dept_id = min(dept_averages, key=dept_averages.get)
                record.bottom_department = bottom_dept_id
                record.bottom_department_rating = dept_averages[bottom_dept_id]
            else:
                record.top_department = False
                record.top_department_rating = 0
                record.bottom_department = False
                record.bottom_department_rating = 0
    
    @api.depends('period_start', 'period_end')
    def _compute_goal_metrics(self):
        """Compute goal metrics."""
        for record in self:
            goals = self.env['tazweed.employee.goal'].search([
                ('date_start', '>=', record.period_start),
                ('date_start', '<=', record.period_end),
            ])
            
            record.total_goals = len(goals)
            record.goals_achieved = len(goals.filtered(lambda g: g.state == 'achieved'))
            record.goals_in_progress = len(goals.filtered(lambda g: g.state == 'in_progress'))
            
            if record.total_goals > 0:
                record.goal_achievement_rate = (record.goals_achieved / record.total_goals) * 100
            else:
                record.goal_achievement_rate = 0
    
    @api.depends('period_start', 'period_end')
    def _compute_kpi_metrics(self):
        """Compute KPI metrics."""
        for record in self:
            kpis = self.env['tazweed.kpi.tracking'].search([
                ('date_start', '>=', record.period_start),
                ('date_start', '<=', record.period_end),
            ])
            
            record.total_kpis = len(kpis)
            record.kpis_on_track = len(kpis.filtered(lambda k: k.status == 'on_track'))
            record.kpis_at_risk = len(kpis.filtered(lambda k: k.status == 'at_risk'))
            
            if record.total_kpis > 0:
                record.kpi_achievement_rate = (record.kpis_on_track / record.total_kpis) * 100
            else:
                record.kpi_achievement_rate = 0
    
    @api.depends('period_start', 'period_end')
    def _compute_development_metrics(self):
        """Compute development metrics."""
        for record in self:
            plans = self.env['tazweed.development.plan'].search([
                ('date_start', '>=', record.period_start),
                ('date_start', '<=', record.period_end),
            ])
            
            record.development_plans_active = len(plans.filtered(lambda p: p.state == 'active'))
            record.development_plans_completed = len(plans.filtered(lambda p: p.state == 'completed'))
    
    @api.depends('period_start', 'period_end')
    def _compute_trends(self):
        """Compute performance trends."""
        for record in self:
            from dateutil.relativedelta import relativedelta
            
            # Previous period
            prev_start = record.period_start - relativedelta(months=1)
            prev_end = record.period_end - relativedelta(months=1)
            
            # Current period
            current_appraisals = self.env['tazweed.hr.appraisal'].search([
                ('appraisal_date', '>=', record.period_start),
                ('appraisal_date', '<=', record.period_end),
                ('state', '=', 'approved'),
            ])
            
            current_rating = sum([float(a.overall_rating or 0) for a in current_appraisals]) / len(current_appraisals) if current_appraisals else 0
            
            # Previous period
            prev_appraisals = self.env['tazweed.hr.appraisal'].search([
                ('appraisal_date', '>=', prev_start),
                ('appraisal_date', '<=', prev_end),
                ('state', '=', 'approved'),
            ])
            
            prev_rating = sum([float(a.overall_rating or 0) for a in prev_appraisals]) / len(prev_appraisals) if prev_appraisals else 0
            
            record.performance_trend = 'up' if current_rating > prev_rating else ('down' if current_rating < prev_rating else 'stable')
            
            # Goal trend
            current_goals = self.env['tazweed.employee.goal'].search([
                ('date_start', '>=', record.period_start),
                ('date_start', '<=', record.period_end),
            ])
            
            current_goal_rate = len(current_goals.filtered(lambda g: g.state == 'achieved')) / len(current_goals) * 100 if current_goals else 0
            
            prev_goals = self.env['tazweed.employee.goal'].search([
                ('date_start', '>=', prev_start),
                ('date_start', '<=', prev_end),
            ])
            
            prev_goal_rate = len(prev_goals.filtered(lambda g: g.state == 'achieved')) / len(prev_goals) * 100 if prev_goals else 0
            
            record.goal_trend = 'up' if current_goal_rate > prev_goal_rate else ('down' if current_goal_rate < prev_goal_rate else 'stable')
