# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json


class RecruitmentDashboard(models.Model):
    """Recruitment Analytics Dashboard for comprehensive recruitment metrics."""
    
    _name = 'recruitment.analytics.dashboard'
    _description = 'Recruitment Analytics Dashboard'
    _rec_name = 'name'
    
    name = fields.Char(string='Dashboard Name', required=True, default='Recruitment Dashboard')
    
    # Filters
    date_from = fields.Date(string='From Date', 
                             default=lambda self: fields.Date.today().replace(day=1) - relativedelta(months=11))
    date_to = fields.Date(string='To Date', default=fields.Date.today)
    
    department_ids = fields.Many2many('hr.department', 
                                       'recruitment_dashboard_department_rel',
                                       'dashboard_id', 'department_id',
                                       string='Departments')
    client_ids = fields.Many2many('tazweed.client', 
                                   'recruitment_dashboard_client_rel',
                                   'dashboard_id', 'client_id',
                                   string='Clients')
    job_ids = fields.Many2many('hr.job', 
                                'recruitment_dashboard_job_rel',
                                'dashboard_id', 'job_id',
                                string='Job Positions')
    
    # View Type
    view_type = fields.Selection([
        ('summary', 'Summary'),
        ('by_stage', 'By Stage'),
        ('by_source', 'By Source'),
        ('by_job', 'By Job Position'),
        ('by_recruiter', 'By Recruiter'),
        ('trend', 'Trend Analysis'),
    ], string='View Type', default='summary')
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    
    # Computed KPI Fields
    total_candidates = fields.Integer(string='Total Candidates', compute='_compute_kpi_values')
    total_job_orders = fields.Integer(string='Total Job Orders', compute='_compute_kpi_values')
    total_placements = fields.Integer(string='Total Placements', compute='_compute_kpi_values')
    total_interviews = fields.Integer(string='Total Interviews', compute='_compute_kpi_values')
    conversion_rate = fields.Float(string='Conversion Rate %', digits=(5, 2), compute='_compute_kpi_values')
    avg_time_to_fill = fields.Float(string='Avg Time to Fill (Days)', digits=(5, 1), compute='_compute_kpi_values')
    offer_acceptance_rate = fields.Float(string='Offer Acceptance Rate %', digits=(5, 2), compute='_compute_kpi_values')
    interview_to_offer_rate = fields.Float(string='Interview to Offer Rate %', digits=(5, 2), compute='_compute_kpi_values')
    
    # Pipeline Metrics
    candidates_in_pipeline = fields.Integer(string='In Pipeline', compute='_compute_kpi_values')
    candidates_shortlisted = fields.Integer(string='Shortlisted', compute='_compute_kpi_values')
    candidates_interviewed = fields.Integer(string='Interviewed', compute='_compute_kpi_values')
    candidates_offered = fields.Integer(string='Offered', compute='_compute_kpi_values')
    candidates_hired = fields.Integer(string='Hired', compute='_compute_kpi_values')
    candidates_rejected = fields.Integer(string='Rejected', compute='_compute_kpi_values')
    
    # Dashboard Data (JSON)
    dashboard_data = fields.Text(string='Dashboard Data', compute='_compute_dashboard_data')
    
    @api.depends('date_from', 'date_to', 'department_ids', 'client_ids', 'job_ids')
    def _compute_kpi_values(self):
        """Compute KPI values for recruitment dashboard."""
        for record in self:
            # Set default values
            record.total_candidates = 0
            record.total_job_orders = 0
            record.total_placements = 0
            record.total_interviews = 0
            record.conversion_rate = 0
            record.avg_time_to_fill = 0
            record.offer_acceptance_rate = 0
            record.interview_to_offer_rate = 0
            record.candidates_in_pipeline = 0
            record.candidates_shortlisted = 0
            record.candidates_interviewed = 0
            record.candidates_offered = 0
            record.candidates_hired = 0
            record.candidates_rejected = 0
            
            if not record.date_from or not record.date_to:
                continue
            
            try:
                # Build domain for candidates
                candidate_domain = [
                    ('create_date', '>=', record.date_from),
                    ('create_date', '<=', record.date_to),
                ]
                
                # Build domain for job orders
                job_order_domain = [
                    ('create_date', '>=', record.date_from),
                    ('create_date', '<=', record.date_to),
                ]
                
                # Build domain for placements
                placement_domain = [
                    ('create_date', '>=', record.date_from),
                    ('create_date', '<=', record.date_to),
                ]
                
                # Build domain for interviews
                interview_domain = [
                    ('scheduled_date', '>=', record.date_from),
                    ('scheduled_date', '<=', record.date_to),
                ]
                
                # Apply filters
                if record.id:
                    try:
                        if record.client_ids:
                            job_order_domain.append(('client_id', 'in', record.client_ids.ids))
                            placement_domain.append(('client_id', 'in', record.client_ids.ids))
                    except Exception:
                        pass
                    try:
                        if record.job_ids:
                            candidate_domain.append(('job_id', 'in', record.job_ids.ids))
                            job_order_domain.append(('job_id', 'in', record.job_ids.ids))
                    except Exception:
                        pass
                
                # Get candidates
                Candidate = self.env['tazweed.candidate'].sudo()
                if 'tazweed.candidate' in self.env:
                    candidates = Candidate.search(candidate_domain)
                    record.total_candidates = len(candidates)
                    
                    # Pipeline metrics by stage
                    for cand in candidates:
                        stage = cand.stage_id.name.lower() if cand.stage_id else ''
                        if 'new' in stage or 'applied' in stage:
                            record.candidates_in_pipeline += 1
                        elif 'shortlist' in stage:
                            record.candidates_shortlisted += 1
                        elif 'interview' in stage:
                            record.candidates_interviewed += 1
                        elif 'offer' in stage:
                            record.candidates_offered += 1
                        elif 'hired' in stage or 'placed' in stage:
                            record.candidates_hired += 1
                        elif 'reject' in stage:
                            record.candidates_rejected += 1
                
                # Get job orders
                JobOrder = self.env['tazweed.job.order'].sudo()
                if 'tazweed.job.order' in self.env:
                    job_orders = JobOrder.search(job_order_domain)
                    record.total_job_orders = len(job_orders)
                
                # Get placements
                Placement = self.env['tazweed.placement'].sudo()
                if 'tazweed.placement' in self.env:
                    placements = Placement.search(placement_domain)
                    record.total_placements = len(placements)
                    
                    # Calculate avg time to fill
                    fill_times = []
                    for p in placements:
                        if p.start_date and p.create_date:
                            days = (p.start_date - p.create_date.date()).days
                            if days > 0:
                                fill_times.append(days)
                    if fill_times:
                        record.avg_time_to_fill = sum(fill_times) / len(fill_times)
                
                # Get interviews
                Interview = self.env['tazweed.interview'].sudo()
                if 'tazweed.interview' in self.env:
                    interviews = Interview.search(interview_domain)
                    record.total_interviews = len(interviews)
                
                # Calculate rates
                if record.total_candidates > 0:
                    record.conversion_rate = (record.candidates_hired / record.total_candidates) * 100
                
                if record.candidates_offered > 0:
                    record.offer_acceptance_rate = (record.candidates_hired / record.candidates_offered) * 100
                
                if record.candidates_interviewed > 0:
                    record.interview_to_offer_rate = (record.candidates_offered / record.candidates_interviewed) * 100
                    
            except Exception:
                pass
    
    def _compute_dashboard_data(self):
        for record in self:
            record.dashboard_data = json.dumps(record.get_dashboard_data())
    
    def get_dashboard_data(self):
        """Get comprehensive recruitment dashboard data."""
        self.ensure_one()
        
        if not self.date_from or not self.date_to:
            return {
                'summary': {},
                'pipeline': [],
                'by_source': [],
                'by_job': [],
                'trend': [],
                'charts': {},
            }
        
        return {
            'summary': self._get_summary_data(),
            'pipeline': self._get_pipeline_data(),
            'by_source': self._get_by_source_data(),
            'by_job': self._get_by_job_data(),
            'trend': self._get_trend_data(),
            'charts': self._get_charts_data(),
        }
    
    def _get_summary_data(self):
        """Get summary statistics."""
        return {
            'total_candidates': self.total_candidates,
            'total_job_orders': self.total_job_orders,
            'total_placements': self.total_placements,
            'total_interviews': self.total_interviews,
            'conversion_rate': self.conversion_rate,
            'avg_time_to_fill': self.avg_time_to_fill,
            'offer_acceptance_rate': self.offer_acceptance_rate,
        }
    
    def _get_pipeline_data(self):
        """Get pipeline funnel data."""
        return [
            {'stage': 'Applied', 'count': self.candidates_in_pipeline},
            {'stage': 'Shortlisted', 'count': self.candidates_shortlisted},
            {'stage': 'Interviewed', 'count': self.candidates_interviewed},
            {'stage': 'Offered', 'count': self.candidates_offered},
            {'stage': 'Hired', 'count': self.candidates_hired},
        ]
    
    def _get_by_source_data(self):
        """Get candidates by source."""
        result = []
        try:
            Candidate = self.env['tazweed.candidate'].sudo()
            if 'tazweed.candidate' in self.env:
                candidates = Candidate.search([
                    ('create_date', '>=', self.date_from),
                    ('create_date', '<=', self.date_to),
                ])
                source_counts = {}
                for cand in candidates:
                    source = cand.source or 'Unknown'
                    source_counts[source] = source_counts.get(source, 0) + 1
                
                for source, count in source_counts.items():
                    result.append({'source': source, 'count': count})
        except Exception:
            pass
        return result
    
    def _get_by_job_data(self):
        """Get candidates by job position."""
        result = []
        try:
            Candidate = self.env['tazweed.candidate'].sudo()
            if 'tazweed.candidate' in self.env:
                candidates = Candidate.search([
                    ('create_date', '>=', self.date_from),
                    ('create_date', '<=', self.date_to),
                ])
                job_counts = {}
                for cand in candidates:
                    job = cand.job_id.name if cand.job_id else 'Unassigned'
                    job_counts[job] = job_counts.get(job, 0) + 1
                
                for job, count in job_counts.items():
                    result.append({'job': job, 'count': count})
        except Exception:
            pass
        return result
    
    def _get_trend_data(self):
        """Get monthly trend data."""
        result = []
        try:
            Candidate = self.env['tazweed.candidate'].sudo()
            if 'tazweed.candidate' in self.env:
                # Group by month
                current = self.date_from
                while current <= self.date_to:
                    month_end = current + relativedelta(months=1, days=-1)
                    if month_end > self.date_to:
                        month_end = self.date_to
                    
                    candidates = Candidate.search_count([
                        ('create_date', '>=', current),
                        ('create_date', '<=', month_end),
                    ])
                    
                    result.append({
                        'month': current.strftime('%Y-%m'),
                        'candidates': candidates,
                    })
                    
                    current = current + relativedelta(months=1)
        except Exception:
            pass
        return result
    
    def _get_charts_data(self):
        """Get chart configuration data."""
        return {
            'pipeline_chart': {
                'type': 'funnel',
                'data': self._get_pipeline_data(),
            },
            'source_chart': {
                'type': 'pie',
                'data': self._get_by_source_data(),
            },
            'trend_chart': {
                'type': 'line',
                'data': self._get_trend_data(),
            },
        }
    
    def action_refresh(self):
        """Refresh dashboard data."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dashboard Refreshed'),
                'message': _('Recruitment dashboard data has been refreshed.'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_view_candidates(self):
        """Open candidates view."""
        self.ensure_one()
        return {
            'name': _('Candidates'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.candidate',
            'view_mode': 'tree,form,kanban',
            'domain': [
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to),
            ],
            'context': {'default_date': fields.Date.today()},
        }
    
    def action_view_job_orders(self):
        """Open job orders view."""
        self.ensure_one()
        return {
            'name': _('Job Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.job.order',
            'view_mode': 'tree,form,kanban',
            'domain': [
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to),
            ],
        }
    
    def action_view_placements(self):
        """Open placements view."""
        self.ensure_one()
        return {
            'name': _('Placements'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.placement',
            'view_mode': 'tree,form',
            'domain': [
                ('create_date', '>=', self.date_from),
                ('create_date', '<=', self.date_to),
            ],
        }
    
    def action_view_interviews(self):
        """Open interviews view."""
        self.ensure_one()
        return {
            'name': _('Interviews'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.interview',
            'view_mode': 'tree,form,calendar',
            'domain': [
                ('scheduled_date', '>=', self.date_from),
                ('scheduled_date', '<=', self.date_to),
            ],
        }
