# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class JobBoardAnalytics(models.Model):
    """Analytics and reporting for job board performance"""
    _name = 'job.board.analytics'
    _description = 'Job Board Analytics'
    _order = 'date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(string='Name', compute='_compute_display_name')
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    
    # Dimensions
    job_board_id = fields.Many2one('job.board', string='Job Board')
    hr_job_id = fields.Many2one('hr.job', string='Job Position')
    job_posting_id = fields.Many2one('job.posting', string='Job Posting')
    department_id = fields.Many2one('hr.department', string='Department')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Metrics - Impressions & Engagement
    impressions = fields.Integer(string='Impressions', default=0)
    views = fields.Integer(string='Views', default=0)
    clicks = fields.Integer(string='Clicks', default=0)
    
    # Metrics - Applications
    applications = fields.Integer(string='Applications', default=0)
    qualified_applications = fields.Integer(string='Qualified Applications', default=0)
    
    # Metrics - Conversions
    interviews = fields.Integer(string='Interviews Scheduled', default=0)
    offers = fields.Integer(string='Offers Made', default=0)
    hires = fields.Integer(string='Hires', default=0)
    
    # Metrics - Cost
    spend = fields.Float(string='Spend (AED)', default=0.0)
    
    # Calculated Metrics
    click_rate = fields.Float(string='Click Rate (%)', compute='_compute_rates', store=True)
    application_rate = fields.Float(string='Application Rate (%)', compute='_compute_rates', store=True)
    interview_rate = fields.Float(string='Interview Rate (%)', compute='_compute_rates', store=True)
    offer_rate = fields.Float(string='Offer Rate (%)', compute='_compute_rates', store=True)
    hire_rate = fields.Float(string='Hire Rate (%)', compute='_compute_rates', store=True)
    
    cost_per_click = fields.Float(string='Cost per Click', compute='_compute_costs', store=True)
    cost_per_application = fields.Float(string='Cost per Application', compute='_compute_costs', store=True)
    cost_per_hire = fields.Float(string='Cost per Hire', compute='_compute_costs', store=True)
    
    @api.depends('job_board_id', 'date')
    def _compute_display_name(self):
        for record in self:
            board_name = record.job_board_id.name if record.job_board_id else 'All Boards'
            record.display_name = f"{board_name} - {record.date}"
    
    @api.depends('impressions', 'views', 'clicks', 'applications', 'interviews', 'offers', 'hires')
    def _compute_rates(self):
        for record in self:
            record.click_rate = (record.clicks / record.views * 100) if record.views else 0
            record.application_rate = (record.applications / record.clicks * 100) if record.clicks else 0
            record.interview_rate = (record.interviews / record.applications * 100) if record.applications else 0
            record.offer_rate = (record.offers / record.interviews * 100) if record.interviews else 0
            record.hire_rate = (record.hires / record.offers * 100) if record.offers else 0
    
    @api.depends('spend', 'clicks', 'applications', 'hires')
    def _compute_costs(self):
        for record in self:
            record.cost_per_click = record.spend / record.clicks if record.clicks else 0
            record.cost_per_application = record.spend / record.applications if record.applications else 0
            record.cost_per_hire = record.spend / record.hires if record.hires else 0
    
    @api.model
    def get_dashboard_data(self, days=30):
        """Get aggregated dashboard data for the OWL dashboard component"""
        date_from = fields.Date.today() - timedelta(days=days)
        date_to = fields.Date.today()
        
        # Get analytics records
        domain = [('date', '>=', date_from), ('date', '<=', date_to)]
        records = self.search(domain)
        
        # Get job postings
        postings = self.env['job.posting'].search([])
        active_postings = postings.filtered(lambda p: p.state == 'active')
        
        # Aggregate metrics from postings
        total_views = sum(postings.mapped('view_count'))
        total_applications = sum(postings.mapped('application_count'))
        total_hires = sum(postings.mapped('hired_count'))
        
        # If no analytics records, use posting data
        if not records:
            total_views = total_views or 0
            total_applications = total_applications or 0
            total_hires = total_hires or 0
        else:
            total_views = sum(records.mapped('views')) or total_views
            total_applications = sum(records.mapped('applications')) or total_applications
            total_hires = sum(records.mapped('hires')) or total_hires
        
        # Applications over time
        applications_over_time = []
        for i in range(days, -1, -1):
            date = fields.Date.today() - timedelta(days=i)
            day_records = records.filtered(lambda r: r.date == date)
            applications_over_time.append({
                'date': date.strftime('%b %d'),
                'views': sum(day_records.mapped('views')) if day_records else 0,
                'applications': sum(day_records.mapped('applications')) if day_records else 0,
            })
        
        # Board distribution
        board_distribution = []
        for board in self.env['job.board'].search([('active', '=', True)], limit=8):
            board_postings = postings.filtered(lambda p: p.job_board_id == board)
            board_apps = sum(board_postings.mapped('application_count'))
            if board_apps > 0:
                board_distribution.append({
                    'board': board.name,
                    'applications': board_apps,
                })
        
        # Funnel data
        funnel = {
            'views': total_views,
            'applications': total_applications,
            'interviews': sum(records.mapped('interviews')) if records else int(total_applications * 0.3),
            'offers': sum(records.mapped('offers')) if records else int(total_applications * 0.1),
            'hires': total_hires,
        }
        
        # Cost per hire by board
        cost_per_hire = []
        for board in self.env['job.board'].search([('active', '=', True)], limit=6):
            board_postings = postings.filtered(lambda p: p.job_board_id == board)
            board_hires = sum(board_postings.mapped('hired_count'))
            board_cost = sum(board_postings.mapped('cost'))
            if board_hires > 0:
                cost_per_hire.append({
                    'board': board.name,
                    'cost': board_cost / board_hires,
                })
        
        # Top postings
        top_postings = []
        sorted_postings = postings.sorted(key=lambda p: p.application_count, reverse=True)[:5]
        for posting in sorted_postings:
            top_postings.append({
                'id': posting.id,
                'title': posting.title or posting.display_name,
                'board': posting.job_board_id.name if posting.job_board_id else 'N/A',
                'views': posting.view_count,
                'applications': posting.application_count,
            })
        
        # Board performance
        board_performance = []
        for board in self.env['job.board'].search([('active', '=', True)], limit=6):
            board_postings = postings.filtered(lambda p: p.job_board_id == board)
            board_performance.append({
                'name': board.name,
                'postings': len(board_postings),
                'applications': sum(board_postings.mapped('application_count')),
                'hires': sum(board_postings.mapped('hired_count')),
                'spend': sum(board_postings.mapped('cost')),
            })
        
        # Alerts
        alerts = []
        
        # Check for expiring postings
        expiring_soon = postings.filtered(
            lambda p: p.state == 'active' and p.expiry_date and 
            p.expiry_date <= fields.Date.today() + timedelta(days=7)
        )
        if expiring_soon:
            alerts.append({
                'type': 'warning',
                'message': f'{len(expiring_soon)} job posting(s) expiring within 7 days',
                'action': 'View',
                'action_url': '#',
            })
        
        # Check for failed postings
        failed_postings = postings.filtered(lambda p: p.state == 'failed')
        if failed_postings:
            alerts.append({
                'type': 'danger',
                'message': f'{len(failed_postings)} job posting(s) failed to publish',
                'action': 'Fix',
                'action_url': '#',
            })
        
        # Low performing postings
        low_performers = postings.filtered(
            lambda p: p.state == 'active' and p.view_count > 100 and p.application_count == 0
        )
        if low_performers:
            alerts.append({
                'type': 'info',
                'message': f'{len(low_performers)} posting(s) have views but no applications',
                'action': 'Review',
                'action_url': '#',
            })
        
        return {
            'active_postings': len(active_postings),
            'total_views': total_views,
            'total_applications': total_applications,
            'total_hires': total_hires,
            'applications_over_time': applications_over_time,
            'board_distribution': board_distribution,
            'funnel': funnel,
            'cost_per_hire': cost_per_hire,
            'top_postings': top_postings,
            'board_performance': board_performance,
            'alerts': alerts,
        }
    
    @api.model
    def _cron_aggregate_daily_metrics(self):
        """Cron job to aggregate daily metrics from postings"""
        yesterday = fields.Date.today() - timedelta(days=1)
        
        # Get all active postings
        postings = self.env['job.posting'].search([('state', '=', 'active')])
        
        for posting in postings:
            # Check if record already exists
            existing = self.search([
                ('date', '=', yesterday),
                ('job_posting_id', '=', posting.id),
            ])
            
            if not existing:
                # Create analytics record
                self.create({
                    'date': yesterday,
                    'job_board_id': posting.job_board_id.id,
                    'hr_job_id': posting.hr_job_id.id,
                    'job_posting_id': posting.id,
                    'department_id': posting.department_id.id,
                    'company_id': posting.company_id.id,
                    'views': posting.view_count,
                    'clicks': posting.click_count,
                    'applications': posting.application_count,
                    'spend': posting.cost,
                })
        
        _logger.info(f"Aggregated daily metrics for {yesterday}")


class JobBoardReport(models.Model):
    """Saved reports for job board analytics"""
    _name = 'job.board.report'
    _description = 'Job Board Report'
    _order = 'name'

    name = fields.Char(string='Report Name', required=True)
    description = fields.Text(string='Description')
    
    # Report Type
    report_type = fields.Selection([
        ('performance', 'Performance Overview'),
        ('roi', 'ROI Analysis'),
        ('source', 'Source Comparison'),
        ('funnel', 'Recruitment Funnel'),
        ('cost', 'Cost Analysis'),
        ('trend', 'Trend Analysis'),
        ('custom', 'Custom Report'),
    ], string='Report Type', default='performance')
    
    # Filters
    date_range = fields.Selection([
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('this_week', 'This Week'),
        ('last_week', 'Last Week'),
        ('this_month', 'This Month'),
        ('last_month', 'Last Month'),
        ('this_quarter', 'This Quarter'),
        ('last_quarter', 'Last Quarter'),
        ('this_year', 'This Year'),
        ('custom', 'Custom Range'),
    ], string='Date Range', default='this_month')
    
    date_from = fields.Date(string='From Date')
    date_to = fields.Date(string='To Date')
    
    job_board_ids = fields.Many2many('job.board', string='Job Boards')
    department_ids = fields.Many2many('hr.department', string='Departments')
    hr_job_ids = fields.Many2many('hr.job', string='Job Positions')
    
    # Display Options
    group_by = fields.Selection([
        ('board', 'Job Board'),
        ('job', 'Job Position'),
        ('department', 'Department'),
        ('date', 'Date'),
    ], string='Group By', default='board')
    
    chart_type = fields.Selection([
        ('bar', 'Bar Chart'),
        ('line', 'Line Chart'),
        ('pie', 'Pie Chart'),
        ('table', 'Table'),
    ], string='Chart Type', default='bar')
    
    # Metrics to Include
    show_impressions = fields.Boolean(string='Show Impressions', default=True)
    show_clicks = fields.Boolean(string='Show Clicks', default=True)
    show_applications = fields.Boolean(string='Show Applications', default=True)
    show_hires = fields.Boolean(string='Show Hires', default=True)
    show_cost = fields.Boolean(string='Show Cost', default=True)
    show_rates = fields.Boolean(string='Show Conversion Rates', default=True)
    
    # Scheduling
    is_scheduled = fields.Boolean(string='Scheduled Report')
    schedule_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Frequency')
    recipient_ids = fields.Many2many('res.users', string='Recipients')
    last_sent = fields.Datetime(string='Last Sent')
    
    # Access
    is_public = fields.Boolean(string='Public Report', default=False)
    owner_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.user)
    
    def action_generate_report(self):
        """Generate and display the report"""
        self.ensure_one()
        
        # Calculate date range
        date_from, date_to = self._get_date_range()
        
        # Get board IDs
        board_ids = self.job_board_ids.ids if self.job_board_ids else None
        
        # Get dashboard data
        data = self.env['job.board.analytics'].get_dashboard_data(days=30)
        
        # Return action to display report
        return {
            'name': self.name,
            'type': 'ir.actions.client',
            'tag': 'job_board_report',
            'context': {
                'report_id': self.id,
                'data': data,
            },
        }
    
    def _get_date_range(self):
        """Calculate date range based on selection"""
        today = fields.Date.today()
        
        if self.date_range == 'today':
            return today, today
        elif self.date_range == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif self.date_range == 'this_week':
            start = today - timedelta(days=today.weekday())
            return start, today
        elif self.date_range == 'last_week':
            start = today - timedelta(days=today.weekday() + 7)
            end = start + timedelta(days=6)
            return start, end
        elif self.date_range == 'this_month':
            start = today.replace(day=1)
            return start, today
        elif self.date_range == 'last_month':
            first_of_month = today.replace(day=1)
            end = first_of_month - timedelta(days=1)
            start = end.replace(day=1)
            return start, end
        elif self.date_range == 'this_quarter':
            quarter = (today.month - 1) // 3
            start = today.replace(month=quarter * 3 + 1, day=1)
            return start, today
        elif self.date_range == 'this_year':
            start = today.replace(month=1, day=1)
            return start, today
        elif self.date_range == 'custom':
            return self.date_from, self.date_to
        
        return today - timedelta(days=30), today
