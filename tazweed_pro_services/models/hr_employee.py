# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HrEmployee(models.Model):
    """Extend HR Employee for PRO services"""
    _inherit = 'hr.employee'

    # PRO Service Requests
    pro_request_ids = fields.One2many(
        'pro.service.request',
        'employee_id',
        string='PRO Service Requests'
    )
    pro_request_count = fields.Integer(
        string='PRO Requests',
        compute='_compute_pro_request_count'
    )
    
    # Active PRO Requests
    active_pro_requests = fields.Integer(
        string='Active PRO Requests',
        compute='_compute_pro_request_count'
    )

    @api.depends('pro_request_ids')
    def _compute_pro_request_count(self):
        for record in self:
            record.pro_request_count = len(record.pro_request_ids)
            record.active_pro_requests = len(record.pro_request_ids.filtered(
                lambda r: r.state not in ('completed', 'cancelled')
            ))

    def action_view_pro_requests(self):
        """View PRO service requests for this employee"""
        self.ensure_one()
        return {
            'name': _('PRO Service Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.service.request',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id,
                'default_request_type': 'internal',
            },
        }

    def action_create_pro_request(self):
        """Create new PRO service request for this employee"""
        self.ensure_one()
        return {
            'name': _('New PRO Service Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.service.request',
            'view_mode': 'form',
            'context': {
                'default_employee_id': self.id,
                'default_request_type': 'internal',
                'default_department_id': self.department_id.id,
            },
        }
