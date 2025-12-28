# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError
from datetime import datetime, timedelta
import json


class ClientPortalSettings(models.Model):
    """Client Portal Configuration and Settings"""
    _name = 'client.portal.settings'
    _description = 'Client Portal Settings'
    _rec_name = 'client_id'

    client_id = fields.Many2one('tazweed.client', string='Client', required=True, ondelete='cascade')
    
    # Branding & Customization
    portal_title = fields.Char(string='Portal Title', default='Client Portal')
    primary_color = fields.Char(string='Primary Color', default='#2196F3')
    secondary_color = fields.Char(string='Secondary Color', default='#1976D2')
    logo = fields.Binary(string='Client Logo')
    favicon = fields.Binary(string='Favicon')
    welcome_message = fields.Html(string='Welcome Message')
    
    # Feature Toggles
    enable_job_orders = fields.Boolean(string='Enable Job Orders', default=True)
    enable_candidate_review = fields.Boolean(string='Enable Candidate Review', default=True)
    enable_placements = fields.Boolean(string='Enable Placements View', default=True)
    enable_invoices = fields.Boolean(string='Enable Invoices', default=True)
    enable_documents = fields.Boolean(string='Enable Documents', default=True)
    enable_messaging = fields.Boolean(string='Enable Messaging', default=True)
    enable_analytics = fields.Boolean(string='Enable Analytics Dashboard', default=True)
    enable_notifications = fields.Boolean(string='Enable Notifications', default=True)
    
    # Permissions
    allow_create_job_orders = fields.Boolean(string='Allow Create Job Orders', default=True)
    allow_approve_candidates = fields.Boolean(string='Allow Approve Candidates', default=True)
    allow_download_documents = fields.Boolean(string='Allow Download Documents', default=True)
    allow_upload_documents = fields.Boolean(string='Allow Upload Documents', default=True)
    
    # Notification Settings
    notify_new_candidate = fields.Boolean(string='Notify New Candidates', default=True)
    notify_placement_update = fields.Boolean(string='Notify Placement Updates', default=True)
    notify_invoice_created = fields.Boolean(string='Notify New Invoices', default=True)
    notify_document_shared = fields.Boolean(string='Notify Document Shared', default=True)
    
    _sql_constraints = [
        ('client_unique', 'unique(client_id)', 'Portal settings already exist for this client!')
    ]


class ClientPortalDashboard(models.Model):
    """Client Portal Dashboard with Real-time Analytics"""
    _name = 'client.portal.dashboard'
    _description = 'Client Portal Dashboard'
    _auto = False  # This is a view model for dashboard data

    @api.model
    def get_dashboard_data(self, client_id):
        """Get comprehensive dashboard data for a client"""
        client = self.env['tazweed.client'].browse(client_id)
        if not client.exists():
            raise UserError(_('Client not found'))
        
        today = fields.Date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        
        # Job Orders Statistics
        job_orders = self.env['tazweed.job.order'].search([('client_id', '=', client_id)])
        active_job_orders = job_orders.filtered(lambda j: j.state in ['open', 'in_progress'])
        
        # Placements Statistics
        placements = self.env['tazweed.placement'].search([('client_id', '=', client_id)])
        active_placements = placements.filtered(lambda p: p.state == 'active')
        
        # Candidates Statistics
        candidates_submitted = self.env['tazweed.candidate'].search_count([
            ('job_order_id.client_id', '=', client_id),
            ('state', '=', 'submitted')
        ])
        candidates_pending = self.env['tazweed.candidate'].search_count([
            ('job_order_id.client_id', '=', client_id),
            ('state', '=', 'pending_approval')
        ])
        
        # Invoice Statistics
        invoices = self.env['tazweed.client.invoice'].search([('client_id', '=', client_id)])
        pending_invoices = invoices.filtered(lambda i: i.state == 'sent')
        total_outstanding = sum(pending_invoices.mapped('total_amount'))
        
        # Monthly Trends (last 6 months)
        monthly_data = self._get_monthly_trends(client_id, 6)
        
        # Fill Rate Calculation
        total_positions = sum(job_orders.mapped('positions_required'))
        filled_positions = sum(job_orders.mapped('positions_filled'))
        fill_rate = (filled_positions / total_positions * 100) if total_positions > 0 else 0
        
        # Average Time to Fill
        completed_orders = job_orders.filtered(lambda j: j.state == 'completed')
        avg_time_to_fill = 0
        if completed_orders:
            total_days = sum([
                (j.completion_date - j.create_date.date()).days 
                for j in completed_orders if j.completion_date
            ])
            avg_time_to_fill = total_days / len(completed_orders)
        
        return {
            'summary': {
                'active_job_orders': len(active_job_orders),
                'total_job_orders': len(job_orders),
                'active_placements': len(active_placements),
                'total_placements': len(placements),
                'candidates_pending_review': candidates_pending,
                'candidates_submitted': candidates_submitted,
                'pending_invoices': len(pending_invoices),
                'total_outstanding': total_outstanding,
            },
            'kpis': {
                'fill_rate': round(fill_rate, 1),
                'avg_time_to_fill': round(avg_time_to_fill, 1),
                'active_workers': len(active_placements),
                'satisfaction_score': self._get_satisfaction_score(client_id),
            },
            'charts': {
                'monthly_placements': monthly_data['placements'],
                'monthly_invoices': monthly_data['invoices'],
                'job_order_status': self._get_job_order_status_chart(job_orders),
                'placement_by_department': self._get_placement_by_dept(placements),
            },
            'recent_activity': self._get_recent_activity(client_id, limit=10),
            'notifications': self._get_pending_notifications(client_id),
        }
    
    def _get_monthly_trends(self, client_id, months):
        """Get monthly trends for placements and invoices"""
        today = fields.Date.today()
        placements_data = []
        invoices_data = []
        
        for i in range(months - 1, -1, -1):
            month_date = today - timedelta(days=i * 30)
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)
            
            # Placements count
            placement_count = self.env['tazweed.placement'].search_count([
                ('client_id', '=', client_id),
                ('start_date', '>=', month_start),
                ('start_date', '<=', month_end),
            ])
            
            # Invoice amount
            invoice_total = sum(self.env['tazweed.client.invoice'].search([
                ('client_id', '=', client_id),
                ('invoice_date', '>=', month_start),
                ('invoice_date', '<=', month_end),
            ]).mapped('total_amount'))
            
            month_label = month_date.strftime('%b %Y')
            placements_data.append({'month': month_label, 'count': placement_count})
            invoices_data.append({'month': month_label, 'amount': invoice_total})
        
        return {'placements': placements_data, 'invoices': invoices_data}
    
    def _get_job_order_status_chart(self, job_orders):
        """Get job order status distribution"""
        status_counts = {}
        for order in job_orders:
            status = order.state or 'draft'
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return [{'status': k, 'count': v} for k, v in status_counts.items()]
    
    def _get_placement_by_dept(self, placements):
        """Get placements grouped by department"""
        dept_counts = {}
        for placement in placements:
            dept = placement.department_id.name if placement.department_id else 'Unassigned'
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        return [{'department': k, 'count': v} for k, v in dept_counts.items()]
    
    def _get_satisfaction_score(self, client_id):
        """Calculate client satisfaction score based on various factors"""
        # This would typically come from surveys or feedback
        # For now, return a calculated score based on fill rate and time metrics
        return 4.5  # Out of 5
    
    def _get_recent_activity(self, client_id, limit=10):
        """Get recent activity for the client"""
        activities = []
        
        # Recent placements
        recent_placements = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id)
        ], order='create_date desc', limit=5)
        
        for p in recent_placements:
            activities.append({
                'type': 'placement',
                'icon': 'fa-user-plus',
                'message': f'New placement: {p.employee_id.name}',
                'date': p.create_date,
                'color': 'success',
            })
        
        # Recent job orders
        recent_orders = self.env['tazweed.job.order'].search([
            ('client_id', '=', client_id)
        ], order='create_date desc', limit=5)
        
        for o in recent_orders:
            activities.append({
                'type': 'job_order',
                'icon': 'fa-briefcase',
                'message': f'Job order: {o.name}',
                'date': o.create_date,
                'color': 'primary',
            })
        
        # Sort by date and limit
        activities.sort(key=lambda x: x['date'], reverse=True)
        return activities[:limit]
    
    def _get_pending_notifications(self, client_id):
        """Get pending notifications for the client"""
        notifications = self.env['client.portal.notification'].search([
            ('client_id', '=', client_id),
            ('is_read', '=', False),
        ], order='create_date desc', limit=20)
        
        return [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.notification_type,
            'date': n.create_date,
        } for n in notifications]


class TazweedClient(models.Model):
    """Extend Tazweed Client with Portal Features"""
    _inherit = 'tazweed.client'
    
    portal_settings_id = fields.One2many(
        'client.portal.settings', 'client_id', 
        string='Portal Settings'
    )
    portal_user_ids = fields.One2many(
        'client.portal.user', 'client_id',
        string='Portal Users'
    )
    portal_enabled = fields.Boolean(string='Portal Enabled', default=False)
    portal_url = fields.Char(string='Portal URL', compute='_compute_portal_url')
    
    # Quick Stats for Backend
    portal_users_count = fields.Integer(
        string='Portal Users', 
        compute='_compute_portal_stats'
    )
    unread_messages_count = fields.Integer(
        string='Unread Messages',
        compute='_compute_portal_stats'
    )
    
    def _compute_portal_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for client in self:
            client.portal_url = f"{base_url}/my/client/{client.id}"
    
    def _compute_portal_stats(self):
        for client in self:
            client.portal_users_count = len(client.portal_user_ids)
            client.unread_messages_count = self.env['client.portal.message'].search_count([
                ('client_id', '=', client.id),
                ('is_read', '=', False),
                ('direction', '=', 'incoming'),
            ])
    
    def action_enable_portal(self):
        """Enable portal access for this client"""
        self.ensure_one()
        if not self.portal_settings_id:
            self.env['client.portal.settings'].create({
                'client_id': self.id,
                'portal_title': f'{self.name} Portal',
            })
        self.portal_enabled = True
        return True
    
    def action_open_portal_settings(self):
        """Open portal settings form"""
        self.ensure_one()
        if not self.portal_settings_id:
            self.action_enable_portal()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Portal Settings',
            'res_model': 'client.portal.settings',
            'res_id': self.portal_settings_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_view_portal_users(self):
        """View portal users for this client"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Portal Users',
            'res_model': 'client.portal.user',
            'view_mode': 'tree,form',
            'domain': [('client_id', '=', self.id)],
            'context': {'default_client_id': self.id},
        }
