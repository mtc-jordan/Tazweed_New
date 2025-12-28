# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class ProDashboard(models.Model):
    """Dashboard data model for PRO Services analytics"""
    _name = 'pro.dashboard'
    _description = 'PRO Services Dashboard'
    _auto = False  # This is a virtual model for dashboard

    @api.model
    def get_dashboard_data(self):
        """Get all dashboard KPIs and statistics"""
        today = fields.Date.today()
        first_day_month = today.replace(day=1)
        last_month_start = first_day_month - relativedelta(months=1)
        last_month_end = first_day_month - timedelta(days=1)
        
        return {
            'kpis': self._get_kpis(today, first_day_month),
            'request_stats': self._get_request_stats(),
            'task_stats': self._get_task_stats(),
            'revenue_stats': self._get_revenue_stats(first_day_month),
            'service_breakdown': self._get_service_breakdown(),
            'officer_performance': self._get_officer_performance(),
            'pending_tasks': self._get_pending_tasks(),
            'recent_completions': self._get_recent_completions(),
            'expiring_documents': self._get_expiring_documents(),
            'monthly_trends': self._get_monthly_trends(),
        }

    def _get_kpis(self, today, first_day_month):
        """Get main KPI values"""
        Request = self.env['pro.service.request']
        Task = self.env['pro.task']
        Billing = self.env['pro.billing']
        
        # Total Requests
        total_requests = Request.search_count([])
        active_requests = Request.search_count([('state', 'in', ['draft', 'submitted', 'approved', 'in_progress'])])
        completed_this_month = Request.search_count([
            ('state', '=', 'completed'),
            ('completion_date', '>=', first_day_month)
        ])
        
        # Tasks
        total_tasks = Task.search_count([])
        pending_tasks = Task.search_count([('state', '=', 'pending')])
        in_progress_tasks = Task.search_count([('state', '=', 'in_progress')])
        completed_tasks_today = Task.search_count([
            ('state', '=', 'completed'),
            ('end_date', '>=', datetime.combine(today, datetime.min.time())),
            ('end_date', '<', datetime.combine(today + timedelta(days=1), datetime.min.time()))
        ])
        
        # Revenue
        total_revenue = sum(Billing.search([('payment_status', '=', 'paid')]).mapped('total_amount'))
        revenue_this_month = sum(Billing.search([
            ('payment_status', '=', 'paid'),
            ('billing_date', '>=', first_day_month)
        ]).mapped('total_amount'))
        pending_payments = sum(Billing.search([
            ('payment_status', 'in', ['pending', 'partial'])
        ]).mapped('amount_due'))
        
        # Calculate completion rate
        completed_requests = Request.search_count([('state', '=', 'completed')])
        completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Calculate average processing time
        completed_reqs = Request.search([
            ('state', '=', 'completed'),
            ('submission_date', '!=', False),
            ('completion_date', '!=', False)
        ])
        if completed_reqs:
            total_days = sum([
                (r.completion_date - r.submission_date).days 
                for r in completed_reqs 
                if r.completion_date and r.submission_date
            ])
            avg_processing_days = total_days / len(completed_reqs)
        else:
            avg_processing_days = 0
        
        return {
            'total_requests': total_requests,
            'active_requests': active_requests,
            'completed_this_month': completed_this_month,
            'total_tasks': total_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'completed_tasks_today': completed_tasks_today,
            'total_revenue': total_revenue,
            'revenue_this_month': revenue_this_month,
            'pending_payments': pending_payments,
            'completion_rate': round(completion_rate, 1),
            'avg_processing_days': round(avg_processing_days, 1),
        }

    def _get_request_stats(self):
        """Get request statistics by state"""
        Request = self.env['pro.service.request']
        states = ['draft', 'submitted', 'approved', 'in_progress', 'completed', 'cancelled']
        
        stats = []
        colors = {
            'draft': '#95a5a6',
            'submitted': '#3498db',
            'approved': '#9b59b6',
            'in_progress': '#f39c12',
            'completed': '#27ae60',
            'cancelled': '#e74c3c',
        }
        
        for state in states:
            count = Request.search_count([('state', '=', state)])
            stats.append({
                'state': state,
                'label': dict(Request._fields['state'].selection).get(state, state),
                'count': count,
                'color': colors.get(state, '#95a5a6'),
            })
        
        return stats

    def _get_task_stats(self):
        """Get task statistics by state"""
        Task = self.env['pro.task']
        states = ['pending', 'in_progress', 'waiting', 'completed', 'cancelled']
        
        stats = []
        colors = {
            'pending': '#95a5a6',
            'in_progress': '#3498db',
            'waiting': '#f39c12',
            'completed': '#27ae60',
            'cancelled': '#e74c3c',
        }
        
        for state in states:
            count = Task.search_count([('state', '=', state)])
            stats.append({
                'state': state,
                'label': dict(Task._fields['state'].selection).get(state, state),
                'count': count,
                'color': colors.get(state, '#95a5a6'),
            })
        
        return stats

    def _get_revenue_stats(self, first_day_month):
        """Get revenue statistics"""
        Billing = self.env['pro.billing']
        
        # This month
        this_month = sum(Billing.search([
            ('billing_date', '>=', first_day_month),
            ('payment_status', '=', 'paid')
        ]).mapped('total_amount'))
        
        # Last month
        last_month_start = first_day_month - relativedelta(months=1)
        last_month = sum(Billing.search([
            ('billing_date', '>=', last_month_start),
            ('billing_date', '<', first_day_month),
            ('payment_status', '=', 'paid')
        ]).mapped('total_amount'))
        
        # Growth
        growth = ((this_month - last_month) / last_month * 100) if last_month > 0 else 0
        
        # By fee type
        govt_fees = sum(Billing.search([('payment_status', '=', 'paid')]).mapped('government_fee'))
        service_fees = sum(Billing.search([('payment_status', '=', 'paid')]).mapped('service_fee'))
        
        return {
            'this_month': this_month,
            'last_month': last_month,
            'growth': round(growth, 1),
            'government_fees': govt_fees,
            'service_fees': service_fees,
        }

    def _get_service_breakdown(self):
        """Get breakdown by service category"""
        self.env.cr.execute("""
            SELECT 
                sc.name as category,
                COUNT(sr.id) as count,
                COALESCE(SUM(pb.total_amount), 0) as revenue
            FROM pro_service_request sr
            JOIN pro_service ps ON sr.service_id = ps.id
            JOIN pro_service_category sc ON ps.category_id = sc.id
            LEFT JOIN pro_billing pb ON pb.request_id = sr.id AND pb.payment_status = 'paid'
            GROUP BY sc.id, sc.name
            ORDER BY count DESC
            LIMIT 10
        """)
        
        results = self.env.cr.dictfetchall()
        colors = ['#3498db', '#27ae60', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c', '#34495e', '#e67e22', '#2ecc71', '#95a5a6']
        
        for i, row in enumerate(results):
            row['color'] = colors[i % len(colors)]
        
        return results

    def _get_officer_performance(self):
        """Get PRO officer performance metrics"""
        self.env.cr.execute("""
            SELECT 
                ru.id as user_id,
                rp.name as officer_name,
                COUNT(CASE WHEN pt.state = 'completed' THEN 1 END) as completed_tasks,
                COUNT(CASE WHEN pt.state IN ('pending', 'in_progress', 'waiting') THEN 1 END) as active_tasks,
                COALESCE(AVG(
                    CASE WHEN pt.state = 'completed' AND pt.start_date IS NOT NULL AND pt.end_date IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (pt.end_date - pt.start_date)) / 3600
                    END
                ), 0) as avg_hours
            FROM pro_task pt
            JOIN res_users ru ON pt.assigned_to = ru.id
            JOIN res_partner rp ON ru.partner_id = rp.id
            GROUP BY ru.id, rp.name
            ORDER BY completed_tasks DESC
            LIMIT 10
        """)
        
        return self.env.cr.dictfetchall()

    def _get_pending_tasks(self):
        """Get list of pending and overdue tasks"""
        Task = self.env['pro.task']
        today = fields.Date.today()
        
        pending = Task.search([
            ('state', 'in', ['pending', 'in_progress', 'waiting']),
        ], order='due_date asc', limit=10)
        
        result = []
        for task in pending:
            is_overdue = task.due_date and task.due_date < today
            result.append({
                'id': task.id,
                'name': task.name,
                'request': task.request_id.name,
                'beneficiary': task.beneficiary_name,
                'assigned_to': task.assigned_to.name if task.assigned_to else 'Unassigned',
                'due_date': task.due_date,
                'state': task.state,
                'is_overdue': is_overdue,
                'priority': task.priority,
            })
        
        return result

    def _get_recent_completions(self):
        """Get recently completed requests"""
        Request = self.env['pro.service.request']
        
        completed = Request.search([
            ('state', '=', 'completed'),
        ], order='completion_date desc', limit=10)
        
        result = []
        for req in completed:
            result.append({
                'id': req.id,
                'name': req.name,
                'service': req.service_id.name,
                'beneficiary': req.beneficiary_name,
                'completion_date': req.completion_date,
                'total_amount': req.billing_id.total_amount if req.billing_id else 0,
            })
        
        return result

    def _get_expiring_documents(self):
        """Get documents expiring soon"""
        # This would integrate with document center
        return []

    def _get_monthly_trends(self):
        """Get monthly trends for the last 6 months"""
        trends = []
        today = fields.Date.today()
        
        for i in range(5, -1, -1):
            month_start = (today - relativedelta(months=i)).replace(day=1)
            month_end = month_start + relativedelta(months=1) - timedelta(days=1)
            
            # Requests
            requests = self.env['pro.service.request'].search_count([
                ('create_date', '>=', month_start),
                ('create_date', '<=', month_end)
            ])
            
            # Completed
            completed = self.env['pro.service.request'].search_count([
                ('state', '=', 'completed'),
                ('completion_date', '>=', month_start),
                ('completion_date', '<=', month_end)
            ])
            
            # Revenue
            revenue = sum(self.env['pro.billing'].search([
                ('billing_date', '>=', month_start),
                ('billing_date', '<=', month_end),
                ('payment_status', '=', 'paid')
            ]).mapped('total_amount'))
            
            trends.append({
                'month': month_start.strftime('%b %Y'),
                'requests': requests,
                'completed': completed,
                'revenue': revenue,
            })
        
        return trends
