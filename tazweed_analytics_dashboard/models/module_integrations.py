# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class EmployeeCostCenterIntegration(models.Model):
    """Integration methods for Employee Cost Center with other modules."""
    
    _inherit = 'employee.cost.center'
    
    # Link to Payroll
    payslip_id = fields.Many2one('hr.payslip', string='Payslip', ondelete='set null')
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Batch', ondelete='set null')
    
    # Link to Placement
    placement_id = fields.Many2one('tazweed.placement', string='Placement', ondelete='set null')
    
    # Link to Client Invoice
    invoice_id = fields.Many2one('tazweed.placement.invoice', string='Invoice', ondelete='set null')
    
    @api.model
    def generate_from_payroll(self, date_from=None, date_to=None, department_ids=None):
        """Generate cost center records from payroll data."""
        if not date_from:
            date_from = fields.Date.today().replace(day=1) - relativedelta(months=1)
        if not date_to:
            date_to = fields.Date.today().replace(day=1) - timedelta(days=1)
        
        Payslip = self.env['hr.payslip'].sudo()
        domain = [
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', 'in', ['done', 'verify']),
        ]
        
        if department_ids:
            domain.append(('employee_id.department_id', 'in', department_ids))
        
        payslips = Payslip.search(domain)
        created_records = []
        
        for slip in payslips:
            # Check if record already exists
            existing = self.search([
                ('employee_id', '=', slip.employee_id.id),
                ('date', '=', slip.date_from),
                ('payslip_id', '=', slip.id),
            ], limit=1)
            
            if existing:
                continue
            
            # Extract salary components from payslip lines
            salary_data = self._extract_payslip_data(slip)
            
            # Get placement and client info
            placement = self._get_employee_placement(slip.employee_id, slip.date_from)
            
            vals = {
                'employee_id': slip.employee_id.id,
                'department_id': slip.employee_id.department_id.id,
                'job_id': slip.employee_id.job_id.id,
                'date': slip.date_from,
                'period_type': 'monthly',
                'payslip_id': slip.id,
                'payslip_run_id': slip.payslip_run_id.id if slip.payslip_run_id else False,
                **salary_data,
            }
            
            if placement:
                vals.update({
                    'placement_id': placement.id,
                    'client_id': placement.client_id.id if placement.client_id else False,
                    'revenue': self._get_placement_revenue(placement, slip.date_from),
                })
            
            record = self.create(vals)
            created_records.append(record.id)
        
        return created_records
    
    def _extract_payslip_data(self, payslip):
        """Extract salary data from payslip lines."""
        data = {
            'basic_salary': 0,
            'housing_allowance': 0,
            'transport_allowance': 0,
            'food_allowance': 0,
            'other_allowances': 0,
            'gross_salary': 0,
            'pension_contribution': 0,
            'medical_insurance': 0,
        }
        
        for line in payslip.line_ids:
            code = line.code.upper() if line.code else ''
            amount = line.total or 0
            
            if code == 'BASIC':
                data['basic_salary'] = amount
            elif code in ['HRA', 'HOUSING']:
                data['housing_allowance'] = amount
            elif code in ['TRA', 'TRANSPORT']:
                data['transport_allowance'] = amount
            elif code in ['FOOD', 'MEAL']:
                data['food_allowance'] = amount
            elif code == 'GROSS':
                data['gross_salary'] = amount
            elif code in ['PENSION', 'GPSSA']:
                data['pension_contribution'] = amount
            elif code in ['MEDICAL', 'INSURANCE']:
                data['medical_insurance'] = amount
            elif line.category_id and line.category_id.code == 'ALW':
                data['other_allowances'] += amount
        
        return data
    
    def _get_employee_placement(self, employee, date):
        """Get active placement for employee on given date."""
        Placement = self.env['tazweed.placement'].sudo()
        if 'tazweed.placement' not in self.env:
            return False
        
        placement = Placement.search([
            ('employee_id', '=', employee.id),
            ('start_date', '<=', date),
            '|',
            ('end_date', '>=', date),
            ('end_date', '=', False),
            ('state', '=', 'active'),
        ], limit=1)
        
        return placement
    
    def _get_placement_revenue(self, placement, date):
        """Calculate revenue from placement for the month."""
        if not placement or not placement.client_id:
            return 0
        
        # Get billing rate from placement or client contract
        billing_rate = placement.billing_rate if hasattr(placement, 'billing_rate') else 0
        
        if not billing_rate and placement.client_id:
            # Try to get from client rates
            ClientRate = self.env['tazweed.client.rate'].sudo()
            if 'tazweed.client.rate' in self.env:
                rate = ClientRate.search([
                    ('client_id', '=', placement.client_id.id),
                    ('job_id', '=', placement.job_id.id if placement.job_id else False),
                ], limit=1)
                if rate:
                    billing_rate = rate.rate
        
        return billing_rate
    
    @api.model
    def generate_from_placements(self, date_from=None, date_to=None, client_ids=None):
        """Generate cost center records from placement data."""
        if not date_from:
            date_from = fields.Date.today().replace(day=1) - relativedelta(months=1)
        if not date_to:
            date_to = fields.Date.today().replace(day=1) - timedelta(days=1)
        
        Placement = self.env['tazweed.placement'].sudo()
        if 'tazweed.placement' not in self.env:
            return []
        
        domain = [
            ('start_date', '<=', date_to),
            '|',
            ('end_date', '>=', date_from),
            ('end_date', '=', False),
            ('state', '=', 'active'),
        ]
        
        if client_ids:
            domain.append(('client_id', 'in', client_ids))
        
        placements = Placement.search(domain)
        created_records = []
        
        for placement in placements:
            if not placement.employee_id:
                continue
            
            # Check if record already exists
            existing = self.search([
                ('employee_id', '=', placement.employee_id.id),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('placement_id', '=', placement.id),
            ], limit=1)
            
            if existing:
                continue
            
            # Get contract data for costs
            contract = placement.employee_id.contract_id
            
            vals = {
                'employee_id': placement.employee_id.id,
                'department_id': placement.employee_id.department_id.id,
                'job_id': placement.job_id.id if placement.job_id else placement.employee_id.job_id.id,
                'date': date_from,
                'period_type': 'monthly',
                'placement_id': placement.id,
                'client_id': placement.client_id.id if placement.client_id else False,
                'revenue': self._get_placement_revenue(placement, date_from),
            }
            
            if contract:
                vals.update({
                    'basic_salary': contract.wage or 0,
                    'housing_allowance': getattr(contract, 'housing_allowance', 0) or 0,
                    'transport_allowance': getattr(contract, 'transport_allowance', 0) or 0,
                    'food_allowance': getattr(contract, 'food_allowance', 0) or 0,
                })
            
            record = self.create(vals)
            created_records.append(record.id)
        
        return created_records
    
    @api.model
    def sync_with_invoices(self, date_from=None, date_to=None):
        """Sync cost center records with client invoices."""
        if not date_from:
            date_from = fields.Date.today().replace(day=1) - relativedelta(months=1)
        if not date_to:
            date_to = fields.Date.today().replace(day=1) - timedelta(days=1)
        
        Invoice = self.env['tazweed.placement.invoice'].sudo()
        if 'tazweed.placement.invoice' not in self.env:
            return 0
        
        invoices = Invoice.search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', 'in', ['posted', 'paid']),
        ])
        
        updated_count = 0
        
        for invoice in invoices:
            # Find matching cost center records
            for line in invoice.line_ids:
                if not line.employee_id:
                    continue
                
                cost_records = self.search([
                    ('employee_id', '=', line.employee_id.id),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('client_id', '=', invoice.client_id.id if invoice.client_id else False),
                ])
                
                for record in cost_records:
                    record.write({
                        'invoice_id': invoice.id,
                        'revenue': line.amount or record.revenue,
                    })
                    updated_count += 1
        
        return updated_count


class CostCenterDashboardIntegration(models.Model):
    """Integration methods for Cost Center Dashboard."""
    
    _inherit = 'employee.cost.center.dashboard'
    
    def action_generate_from_payroll(self):
        """Generate cost data from payroll."""
        self.ensure_one()
        
        CostCenter = self.env['employee.cost.center']
        
        department_ids = self.department_ids.ids if self.department_ids else None
        
        created = CostCenter.generate_from_payroll(
            date_from=self.date_from,
            date_to=self.date_to,
            department_ids=department_ids,
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Data Generated'),
                'message': _('Created %d cost center records from payroll.') % len(created),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_generate_from_placements(self):
        """Generate cost data from placements."""
        self.ensure_one()
        
        CostCenter = self.env['employee.cost.center']
        
        client_ids = None
        if self.id:
            try:
                if self.client_ids:
                    client_ids = self.client_ids.ids
            except Exception:
                pass
        
        created = CostCenter.generate_from_placements(
            date_from=self.date_from,
            date_to=self.date_to,
            client_ids=client_ids,
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Data Generated'),
                'message': _('Created %d cost center records from placements.') % len(created),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_sync_invoices(self):
        """Sync with client invoices."""
        self.ensure_one()
        
        CostCenter = self.env['employee.cost.center']
        
        updated = CostCenter.sync_with_invoices(
            date_from=self.date_from,
            date_to=self.date_to,
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sync Complete'),
                'message': _('Updated %d cost center records with invoice data.') % updated,
                'type': 'success',
                'sticky': False,
            }
        }


class PayrollDashboardIntegration(models.Model):
    """Integration methods for Payroll Dashboard."""
    
    _inherit = 'payroll.analytics.dashboard'
    
    def action_generate_cost_data(self):
        """Generate cost center data from payroll."""
        self.ensure_one()
        
        CostCenter = self.env['employee.cost.center']
        
        department_ids = None
        if self.id:
            try:
                if self.department_ids:
                    department_ids = self.department_ids.ids
            except Exception:
                pass
        
        created = CostCenter.generate_from_payroll(
            date_from=self.date_from,
            date_to=self.date_to,
            department_ids=department_ids,
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cost Data Generated'),
                'message': _('Created %d cost center records from payroll data.') % len(created),
                'type': 'success',
                'sticky': False,
            }
        }


class RecruitmentDashboardIntegration(models.Model):
    """Integration methods for Recruitment Dashboard."""
    
    _inherit = 'recruitment.analytics.dashboard'
    
    def action_generate_placement_costs(self):
        """Generate cost center data from placements."""
        self.ensure_one()
        
        CostCenter = self.env['employee.cost.center']
        
        client_ids = None
        if self.id:
            try:
                if self.client_ids:
                    client_ids = self.client_ids.ids
            except Exception:
                pass
        
        created = CostCenter.generate_from_placements(
            date_from=self.date_from,
            date_to=self.date_to,
            client_ids=client_ids,
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Cost Data Generated'),
                'message': _('Created %d cost center records from placement data.') % len(created),
                'type': 'success',
                'sticky': False,
            }
        }
