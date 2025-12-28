# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta


class PlacementDashboard(models.AbstractModel):
    """Dashboard data provider for Placement module"""
    _name = 'tazweed.placement.dashboard'
    _description = 'Placement Dashboard'

    @api.model
    def get_dashboard_data(self):
        """Get all dashboard data"""
        return {
            'kpis': self._get_kpis(),
            'pipeline_data': self._get_pipeline_data(),
            'placement_trend': self._get_placement_trend(),
            'source_data': self._get_source_data(),
            'job_category_data': self._get_job_category_data(),
            'recent_placements': self._get_recent_placements(),
            'upcoming_interviews': self._get_upcoming_interviews(),
        }

    def _get_kpis(self):
        """Get KPI values"""
        Candidate = self.env['tazweed.candidate']
        Client = self.env['tazweed.client']
        JobOrder = self.env['tazweed.job.order']
        Placement = self.env['tazweed.placement']
        Interview = self.env['tazweed.interview']
        
        today = date.today()
        first_of_month = today.replace(day=1)
        
        # This month placements
        this_month_placements = Placement.search([
            ('date_placed', '>=', first_of_month),
            ('state', 'in', ('active', 'completed', 'probation')),
        ])
        
        # This month revenue
        this_month_revenue = sum(p.bill_rate for p in this_month_placements)
        
        return {
            'total_candidates': Candidate.search_count([]),
            'active_candidates': Candidate.search_count([('state', 'in', ('new', 'qualified', 'in_process'))]),
            'total_clients': Client.search_count([]),
            'active_clients': Client.search_count([('state', '=', 'active')]),
            'open_job_orders': JobOrder.search_count([('state', 'in', ('open', 'in_progress'))]),
            'total_placements': Placement.search_count([]),
            'active_placements': Placement.search_count([('state', '=', 'active')]),
            'pending_interviews': Interview.search_count([('state', 'in', ('scheduled', 'confirmed'))]),
            'this_month_placements': len(this_month_placements),
            'this_month_revenue': this_month_revenue,
        }

    def _get_pipeline_data(self):
        """Get pipeline distribution by stage"""
        Pipeline = self.env['tazweed.recruitment.pipeline']
        Stage = self.env['tazweed.recruitment.stage']
        
        stages = Stage.search([])
        result = []
        
        for stage in stages:
            count = Pipeline.search_count([
                ('stage_id', '=', stage.id),
                ('result', '=', 'pending'),
            ])
            result.append({
                'stage': stage.name,
                'count': count,
            })
        
        return result

    def _get_placement_trend(self):
        """Get placement trend for last 6 months"""
        Placement = self.env['tazweed.placement']
        
        result = []
        today = date.today()
        
        for i in range(5, -1, -1):
            month_start = (today - relativedelta(months=i)).replace(day=1)
            month_end = month_start + relativedelta(months=1) - timedelta(days=1)
            
            placements = Placement.search([
                ('date_placed', '>=', month_start),
                ('date_placed', '<=', month_end),
                ('state', 'in', ('active', 'completed', 'probation', 'extended')),
            ])
            
            result.append({
                'month': month_start.strftime('%b %Y'),
                'count': len(placements),
                'revenue': sum(p.bill_rate for p in placements),
            })
        
        return result

    def _get_source_data(self):
        """Get candidate distribution by source"""
        Candidate = self.env['tazweed.candidate']
        
        sources = [
            ('website', 'Website'),
            ('referral', 'Referral'),
            ('job_portal', 'Job Portal'),
            ('social_media', 'Social Media'),
            ('walk_in', 'Walk-in'),
            ('agency', 'Agency'),
            ('other', 'Other'),
        ]
        
        result = []
        for source_key, source_label in sources:
            count = Candidate.search_count([('source', '=', source_key)])
            if count > 0:
                result.append({
                    'source': source_label,
                    'count': count,
                })
        
        # Add candidates without source
        no_source = Candidate.search_count([('source', '=', False)])
        if no_source > 0:
            result.append({
                'source': 'Unknown',
                'count': no_source,
            })
        
        return result

    def _get_job_category_data(self):
        """Get job order distribution by category"""
        JobOrder = self.env['tazweed.job.order']
        
        categories = [
            ('unskilled', 'Unskilled'),
            ('semi_skilled', 'Semi-Skilled'),
            ('skilled', 'Skilled'),
            ('professional', 'Professional'),
            ('managerial', 'Managerial'),
            ('executive', 'Executive'),
        ]
        
        result = []
        for cat_key, cat_label in categories:
            count = JobOrder.search_count([
                ('job_category', '=', cat_key),
                ('state', 'in', ('open', 'in_progress')),
            ])
            if count > 0:
                result.append({
                    'category': cat_label,
                    'count': count,
                })
        
        return result

    def _get_recent_placements(self, limit=5):
        """Get recent placements"""
        Placement = self.env['tazweed.placement']
        
        placements = Placement.search([
            ('state', 'in', ('active', 'probation', 'completed')),
        ], order='date_placed desc', limit=limit)
        
        return [{
            'id': p.id,
            'candidate_name': p.candidate_id.name,
            'job_title': p.job_title,
            'client_name': p.client_id.name,
            'state': p.state,
            'date_start': p.date_start.strftime('%Y-%m-%d') if p.date_start else '',
        } for p in placements]

    def _get_upcoming_interviews(self, limit=5):
        """Get upcoming interviews"""
        Interview = self.env['tazweed.interview']
        
        interviews = Interview.search([
            ('state', 'in', ('scheduled', 'confirmed')),
            ('scheduled_date', '>=', datetime.now()),
        ], order='scheduled_date asc', limit=limit)
        
        interview_types = dict(Interview._fields['interview_type'].selection)
        
        return [{
            'id': i.id,
            'candidate_name': i.candidate_id.name,
            'job_title': i.job_order_id.job_title,
            'interview_type': interview_types.get(i.interview_type, i.interview_type),
            'state': i.state,
            'scheduled_date': i.scheduled_date.strftime('%Y-%m-%d %H:%M') if i.scheduled_date else '',
        } for i in interviews]
