# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class PerformanceReview(models.Model):
    """Performance Review"""
    _name = 'tazweed.performance.review'
    _description = 'Performance Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Manager',
        related='employee_id.parent_id',
        store=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        related='employee_id.job_id',
        store=True,
    )
    
    period_id = fields.Many2one(
        'tazweed.performance.period',
        string='Review Period',
        required=True,
        tracking=True,
    )
    template_id = fields.Many2one(
        'tazweed.performance.template',
        string='Review Template',
        tracking=True,
    )
    
    review_type = fields.Selection([
        ('annual', 'Annual Review'),
        ('semi_annual', 'Semi-Annual Review'),
        ('quarterly', 'Quarterly Review'),
        ('probation', 'Probation Review'),
        ('project', 'Project Review'),
        ('adhoc', 'Ad-hoc Review'),
    ], string='Review Type', default='annual', required=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('self_review', 'Self Review'),
        ('manager_review', 'Manager Review'),
        ('calibration', 'Calibration'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Dates
    date_start = fields.Date(string='Review Start Date')
    date_end = fields.Date(string='Review End Date')
    self_review_date = fields.Date(string='Self Review Date')
    manager_review_date = fields.Date(string='Manager Review Date')
    completion_date = fields.Date(string='Completion Date')
    
    # Goals
    goal_ids = fields.One2many(
        'tazweed.performance.goal',
        'review_id',
        string='Goals',
    )
    goal_count = fields.Integer(compute='_compute_counts')
    goal_score = fields.Float(string='Goal Score', compute='_compute_scores', store=True)
    goal_weight = fields.Float(string='Goal Weight (%)', default=40)
    
    # KPIs
    kpi_ids = fields.One2many(
        'tazweed.performance.kpi.line',
        'review_id',
        string='KPIs',
    )
    kpi_count = fields.Integer(compute='_compute_counts')
    kpi_score = fields.Float(string='KPI Score', compute='_compute_scores', store=True)
    kpi_weight = fields.Float(string='KPI Weight (%)', default=30)
    
    # Competencies
    competency_ids = fields.One2many(
        'tazweed.performance.competency.line',
        'review_id',
        string='Competencies',
    )
    competency_count = fields.Integer(compute='_compute_counts')
    competency_score = fields.Float(string='Competency Score', compute='_compute_scores', store=True)
    competency_weight = fields.Float(string='Competency Weight (%)', default=30)
    
    # Scores
    self_rating = fields.Float(string='Self Rating', digits=(3, 2))
    manager_rating = fields.Float(string='Manager Rating', digits=(3, 2))
    final_rating = fields.Float(string='Final Rating', digits=(3, 2), tracking=True)
    overall_score = fields.Float(string='Overall Score', compute='_compute_overall_score', store=True)
    
    rating_label = fields.Selection([
        ('exceptional', 'Exceptional'),
        ('exceeds', 'Exceeds Expectations'),
        ('meets', 'Meets Expectations'),
        ('needs_improvement', 'Needs Improvement'),
        ('unsatisfactory', 'Unsatisfactory'),
    ], string='Rating Label', compute='_compute_rating_label', store=True)
    
    # Comments
    self_assessment = fields.Html(string='Self Assessment')
    manager_assessment = fields.Html(string='Manager Assessment')
    employee_comments = fields.Text(string='Employee Comments')
    manager_comments = fields.Text(string='Manager Comments')
    hr_comments = fields.Text(string='HR Comments')
    
    # Strengths & Improvements
    strengths = fields.Text(string='Key Strengths')
    areas_for_improvement = fields.Text(string='Areas for Improvement')
    achievements = fields.Text(string='Key Achievements')
    
    # Development
    development_plan_id = fields.Many2one(
        'tazweed.development.plan',
        string='Development Plan',
    )
    training_recommendations = fields.Text(string='Training Recommendations')
    career_aspirations = fields.Text(string='Career Aspirations')
    
    # Feedback
    feedback_ids = fields.One2many(
        'tazweed.performance.feedback',
        'review_id',
        string='Feedback',
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    # Acknowledgement
    employee_acknowledged = fields.Boolean(string='Employee Acknowledged')
    employee_acknowledged_date = fields.Datetime(string='Acknowledgement Date')
    employee_signature = fields.Binary(string='Employee Signature')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.performance.review') or _('New')
        return super().create(vals)

    @api.depends('goal_ids', 'kpi_ids', 'competency_ids')
    def _compute_counts(self):
        for review in self:
            review.goal_count = len(review.goal_ids)
            review.kpi_count = len(review.kpi_ids)
            review.competency_count = len(review.competency_ids)

    @api.depends('goal_ids.achievement_score', 'kpi_ids.score', 'competency_ids.rating')
    def _compute_scores(self):
        for review in self:
            # Goal Score
            if review.goal_ids:
                total_weight = sum(g.weight for g in review.goal_ids)
                if total_weight:
                    review.goal_score = sum(g.achievement_score * g.weight for g in review.goal_ids) / total_weight
                else:
                    review.goal_score = sum(g.achievement_score for g in review.goal_ids) / len(review.goal_ids)
            else:
                review.goal_score = 0
            
            # KPI Score
            if review.kpi_ids:
                review.kpi_score = sum(k.score for k in review.kpi_ids) / len(review.kpi_ids)
            else:
                review.kpi_score = 0
            
            # Competency Score
            if review.competency_ids:
                review.competency_score = sum(c.rating for c in review.competency_ids) / len(review.competency_ids)
            else:
                review.competency_score = 0

    @api.depends('goal_score', 'kpi_score', 'competency_score', 'goal_weight', 'kpi_weight', 'competency_weight')
    def _compute_overall_score(self):
        for review in self:
            total_weight = review.goal_weight + review.kpi_weight + review.competency_weight
            if total_weight:
                review.overall_score = (
                    (review.goal_score * review.goal_weight) +
                    (review.kpi_score * review.kpi_weight) +
                    (review.competency_score * review.competency_weight)
                ) / total_weight
            else:
                review.overall_score = 0

    @api.depends('final_rating')
    def _compute_rating_label(self):
        for review in self:
            rating = review.final_rating
            if rating >= 4.5:
                review.rating_label = 'exceptional'
            elif rating >= 3.5:
                review.rating_label = 'exceeds'
            elif rating >= 2.5:
                review.rating_label = 'meets'
            elif rating >= 1.5:
                review.rating_label = 'needs_improvement'
            else:
                review.rating_label = 'unsatisfactory'

    def action_start_self_review(self):
        """Start self review"""
        self.write({
            'state': 'self_review',
            'date_start': date.today(),
        })
        return True

    def action_submit_self_review(self):
        """Submit self review"""
        self.write({
            'state': 'manager_review',
            'self_review_date': date.today(),
        })
        # Notify manager
        if self.manager_id and self.manager_id.user_id:
            self.message_post(
                body=_('Self review submitted by %s. Please complete the manager assessment.') % self.employee_id.name,
                partner_ids=[self.manager_id.user_id.partner_id.id],
            )
        return True

    def action_submit_manager_review(self):
        """Submit manager review"""
        if not self.manager_rating:
            raise UserError(_('Please provide a manager rating before submitting.'))
        self.write({
            'state': 'calibration',
            'manager_review_date': date.today(),
        })
        return True

    def action_complete(self):
        """Complete the review"""
        if not self.final_rating:
            self.final_rating = self.manager_rating or self.overall_score
        self.write({
            'state': 'completed',
            'completion_date': date.today(),
        })
        return True

    def action_cancel(self):
        """Cancel the review"""
        self.write({'state': 'cancelled'})
        return True

    def action_reset_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
        return True

    def action_acknowledge(self):
        """Employee acknowledgement"""
        self.write({
            'employee_acknowledged': True,
            'employee_acknowledged_date': fields.Datetime.now(),
        })
        return True


class PerformanceCompetencyLine(models.Model):
    """Performance Review Competency Line"""
    _name = 'tazweed.performance.competency.line'
    _description = 'Performance Review Competency Line'

    review_id = fields.Many2one(
        'tazweed.performance.review',
        string='Review',
        required=True,
        ondelete='cascade',
    )
    competency_id = fields.Many2one(
        'tazweed.competency',
        string='Competency',
        required=True,
    )
    
    expected_level = fields.Selection([
        ('1', 'Basic'),
        ('2', 'Developing'),
        ('3', 'Proficient'),
        ('4', 'Advanced'),
        ('5', 'Expert'),
    ], string='Expected Level', default='3')
    
    self_rating = fields.Float(string='Self Rating', digits=(3, 2))
    manager_rating = fields.Float(string='Manager Rating', digits=(3, 2))
    rating = fields.Float(string='Final Rating', digits=(3, 2))
    
    self_comments = fields.Text(string='Self Comments')
    manager_comments = fields.Text(string='Manager Comments')
    
    gap = fields.Float(string='Gap', compute='_compute_gap', store=True)

    @api.depends('rating', 'expected_level')
    def _compute_gap(self):
        for line in self:
            expected = float(line.expected_level or 0)
            line.gap = expected - (line.rating or 0)


    @api.model
    def get_performance_dashboard_data(self, period='current'):
        """Get dashboard data for performance management"""
        today = date.today()
        
        # Calculate date range based on period
        if period == 'current':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        elif period == 'quarter':
            quarter = (today.month - 1) // 3
            start_date = date(today.year, quarter * 3 + 1, 1)
            from dateutil.relativedelta import relativedelta
            end_date = (start_date + relativedelta(months=3)) - relativedelta(days=1)
        elif period == 'year':
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        else:  # all
            start_date = date(2000, 1, 1)
            end_date = date(2100, 12, 31)
        
        # Get reviews in the period
        reviews = self.search([
            ('create_date', '>=', start_date),
            ('create_date', '<=', end_date),
        ])
        
        completed_reviews = reviews.filtered(lambda r: r.state == 'completed')
        pending_reviews = reviews.filtered(lambda r: r.state not in ['completed', 'cancelled'])
        
        # Calculate stats
        total_reviews = len(reviews)
        pending_count = len(pending_reviews)
        completed_count = len(completed_reviews)
        avg_rating = sum(completed_reviews.mapped('final_rating')) / max(len(completed_reviews), 1)
        
        # Goals stats
        Goal = self.env.get('tazweed.performance.goal')
        active_goals = 0
        goals_achieved = 0
        if Goal:
            all_goals = Goal.search([])
            active_goals = len(all_goals.filtered(lambda g: g.state in ['in_progress', 'draft']))
            goals_achieved = len(all_goals.filtered(lambda g: g.state == 'achieved'))
        
        # Feedback stats
        Feedback = self.env.get('tazweed.performance.feedback')
        feedback_count = Feedback.search_count([]) if Feedback else 0
        
        # Development plans
        DevPlan = self.env.get('tazweed.development.plan')
        dev_plans_count = DevPlan.search_count([]) if DevPlan else 0
        
        # Rating distribution
        rating_distribution = []
        rating_labels = ['1 Star', '2 Stars', '3 Stars', '4 Stars', '5 Stars']
        for i, label in enumerate(rating_labels, 1):
            count = len(completed_reviews.filtered(
                lambda r: i - 0.5 <= r.final_rating < i + 0.5
            ))
            if count > 0:
                rating_distribution.append({
                    'rating': label,
                    'count': count,
                })
        
        # Reviews by department
        departments = self.env['hr.department'].search([], limit=8)
        reviews_by_department = []
        for dept in departments:
            dept_reviews = reviews.filtered(lambda r: r.department_id.id == dept.id)
            completed = len(dept_reviews.filtered(lambda r: r.state == 'completed'))
            pending = len(dept_reviews.filtered(lambda r: r.state not in ['completed', 'cancelled']))
            if completed > 0 or pending > 0:
                reviews_by_department.append({
                    'name': dept.name[:12],
                    'completed': completed,
                    'pending': pending,
                })
        
        # Goal progress
        goal_progress = []
        if Goal:
            states = [
                ('draft', 'Not Started'),
                ('in_progress', 'In Progress'),
                ('achieved', 'Achieved'),
                ('cancelled', 'Cancelled'),
            ]
            for state, label in states:
                count = Goal.search_count([('state', '=', state)])
                if count > 0:
                    goal_progress.append({
                        'status': label,
                        'count': count,
                    })
        
        # Recent reviews
        recent_reviews = []
        recent = self.search([], order='create_date desc', limit=10)
        for review in recent:
            recent_reviews.append({
                'id': review.id,
                'employee_name': review.employee_id.name if review.employee_id else 'Unknown',
                'period': review.period_id.name if review.period_id else '',
                'rating': review.final_rating,
                'state': review.state,
            })
        
        # Top performers
        top_performers = []
        top = completed_reviews.sorted(key=lambda r: r.final_rating, reverse=True)[:10]
        for review in top:
            top_performers.append({
                'id': review.id,
                'name': review.employee_id.name if review.employee_id else 'Unknown',
                'department': review.department_id.name if review.department_id else '',
                'rating': review.final_rating,
            })
        
        # Upcoming reviews (reviews due soon)
        upcoming_reviews = []
        upcoming = pending_reviews.filtered(lambda r: r.date_end and r.date_end >= today)
        upcoming = upcoming.sorted(key=lambda r: r.date_end)[:5]
        for review in upcoming:
            days_until = (review.date_end - today).days if review.date_end else 0
            upcoming_reviews.append({
                'id': review.id,
                'employee_name': review.employee_id.name if review.employee_id else 'Unknown',
                'due_date': str(review.date_end) if review.date_end else '',
                'days_until': days_until,
            })
        
        # Alerts
        alerts = []
        if pending_count > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'fa-exclamation-triangle',
                'message': f'{pending_count} performance reviews pending completion',
            })
        
        overdue_count = len(pending_reviews.filtered(
            lambda r: r.date_end and r.date_end < today
        ))
        if overdue_count > 0:
            alerts.append({
                'type': 'danger',
                'icon': 'fa-clock-o',
                'message': f'{overdue_count} reviews are overdue',
            })
        
        return {
            'stats': {
                'totalReviews': total_reviews,
                'pendingReviews': pending_count,
                'completedReviews': completed_count,
                'avgRating': round(avg_rating, 2),
                'activeGoals': active_goals,
                'goalsAchieved': goals_achieved,
                'feedbackGiven': feedback_count,
                'developmentPlans': dev_plans_count,
            },
            'rating_distribution': rating_distribution,
            'reviews_by_department': reviews_by_department,
            'goal_progress': goal_progress,
            'recent_reviews': recent_reviews,
            'top_performers': top_performers,
            'upcoming_reviews': upcoming_reviews,
            'alerts': alerts,
        }
