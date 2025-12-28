# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeeSponsor(models.Model):
    """Employee Sponsor Management"""
    _name = 'tazweed.employee.sponsor'
    _description = 'Employee Sponsor'
    _order = 'name'

    name = fields.Char(string='Sponsor Name', required=True)
    code = fields.Char(string='Sponsor Code', readonly=True, copy=False, default='New')
    
    sponsor_type = fields.Selection([
        ('company', 'Company'),
        ('individual', 'Individual'),
        ('free_zone', 'Free Zone'),
        ('government', 'Government'),
    ], string='Sponsor Type', required=True, default='company')
    
    # Contact Information
    partner_id = fields.Many2one('res.partner', string='Related Partner')
    trade_license_number = fields.Char(string='Trade License Number')
    trade_license_expiry = fields.Date(string='Trade License Expiry')
    establishment_id = fields.Char(string='Establishment ID', help='MOHRE Establishment ID')
    mol_number = fields.Char(string='MOL Number', help='Ministry of Labour Number')
    
    # Address
    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='Emirate')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.ref('base.ae', raise_if_not_found=False))
    
    # Contact
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')
    
    # Quota
    visa_quota = fields.Integer(string='Visa Quota', default=0)
    used_quota = fields.Integer(string='Used Quota', compute='_compute_quota')
    available_quota = fields.Integer(string='Available Quota', compute='_compute_quota')
    
    # Status
    state = fields.Selection([
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='active')
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    # Computed fields
    employee_count = fields.Integer(string='Employee Count', compute='_compute_quota')

    @api.depends('visa_quota')
    def _compute_quota(self):
        for record in self:
            count = self.env['hr.employee'].search_count([('sponsor_id', '=', record.id)])
            record.employee_count = count
            record.used_quota = count
            record.available_quota = max(0, record.visa_quota - count)

    @api.model
    def create(self, vals):
        if vals.get('code', 'New') == 'New':
            vals['code'] = self.env['ir.sequence'].next_by_code('tazweed.employee.sponsor') or 'New'
        return super().create(vals)

    def action_view_employees(self):
        """View employees under this sponsor"""
        return {
            'name': _('Sponsored Employees'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'kanban,tree,form',
            'domain': [('sponsor_id', '=', self.id)],
            'context': {'default_sponsor_id': self.id},
        }
