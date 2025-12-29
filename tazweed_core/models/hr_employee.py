# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ==================== UAE IDENTIFICATION ====================
    emirates_id = fields.Char(string='Emirates ID')
    emirates_id_expiry = fields.Date(string='Emirates ID Expiry')
    
    # Passport
    passport_id = fields.Char(string='Passport Number')
    passport_expiry = fields.Date(string='Passport Expiry')
    passport_issue_place = fields.Char(string='Passport Issue Place')
    
    # Visa
    visa_type = fields.Selection([
        ('employment', 'Employment Visa'),
        ('visit', 'Visit Visa'),
        ('residence', 'Residence Visa'),
        ('investor', 'Investor Visa'),
        ('golden', 'Golden Visa'),
        ('freelance', 'Freelance Visa'),
        ('other', 'Other'),
    ], string='Visa Type')
    visa_number = fields.Char(string='Visa Number')
    visa_status = fields.Selection([
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('in_process', 'In Process'),
        ('pending', 'Pending'),
    ], string='Visa Status', default='valid')
    visa_expiry = fields.Date(string='Visa Expiry')
    visa_uid = fields.Char(string='Visa UID')
    
    # Labor Card
    labor_card_number = fields.Char(string='Labor Card Number')
    labor_card_expiry = fields.Date(string='Labor Card Expiry')
    mol_id = fields.Char(string='MOL ID')
    
    # ==================== SPONSOR ====================
    sponsor_id = fields.Many2one('tazweed.employee.sponsor', string='Sponsor')
    sponsor_type = fields.Selection([
        ('company', 'Company Sponsored'),
        ('self', 'Self Sponsored'),
        ('family', 'Family Sponsored'),
        ('other', 'Other'),
    ], string='Sponsor Type', default='company')
    
    # ==================== PLACEMENT ====================
    placement_status = fields.Selection([
        ('available', 'Available'),
        ('placed', 'Placed'),
        ('on_leave', 'On Leave'),
        ('resigned', 'Resigned'),
        ('terminated', 'Terminated'),
    ], string='Placement Status', default='available')
    is_available = fields.Boolean(string='Available for Placement', default=True)
    placement_date = fields.Date(string='Placement Date')
    client_id = fields.Many2one('res.partner', string='Current Client', domain=[('is_company', '=', True)])
    
    # ==================== CATEGORIES ====================
    employee_category_ids = fields.Many2many(
        'tazweed.employee.category',
        'hr_employee_category_rel',
        'employee_id',
        'category_id',
        string='Categories',
    )
    
    # ==================== RELATED RECORDS ====================
    bank_account_ids = fields.One2many(
        'tazweed.employee.bank',
        'employee_id',
        string='Bank Accounts'
    )
    document_ids = fields.One2many(
        'tazweed.employee.document',
        'employee_id',
        string='Documents'
    )
    
    # ==================== COMPUTED COUNTS ====================
    document_count = fields.Integer(string='Documents', compute='_compute_document_count')
    expiring_document_count = fields.Integer(string='Expiring Documents', compute='_compute_document_count')
    bank_account_count = fields.Integer(string='Bank Accounts', compute='_compute_bank_account_count')
    
    # ==================== STATUS FLAGS ====================
    is_uae_national = fields.Boolean(string='UAE National', compute='_compute_is_uae_national', store=True)
    is_new_employee = fields.Boolean(string='New Employee', compute='_compute_is_new_employee')
    has_expiring_documents = fields.Boolean(string='Has Expiring Documents', compute='_compute_document_status')
    
    @api.depends('country_id')
    def _compute_is_uae_national(self):
        uae = self.env.ref('base.ae', raise_if_not_found=False)
        for employee in self:
            employee.is_uae_national = employee.country_id == uae if uae else False

    def _compute_is_new_employee(self):
        today = date.today()
        for employee in self:
            if employee.create_date:
                days_since_creation = (today - employee.create_date.date()).days
                employee.is_new_employee = days_since_creation <= 30
            else:
                employee.is_new_employee = False

    def _compute_document_count(self):
        for employee in self:
            employee.document_count = self.env['tazweed.employee.document'].search_count([
                ('employee_id', '=', employee.id)
            ])
            employee.expiring_document_count = self.env['tazweed.employee.document'].search_count([
                ('employee_id', '=', employee.id),
                ('state', '=', 'expiring')
            ])

    def _compute_bank_account_count(self):
        for employee in self:
            employee.bank_account_count = self.env['tazweed.employee.bank'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def _compute_document_status(self):
        today = date.today()
        for employee in self:
            expiring = self.env['tazweed.employee.document'].search_count([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['expiring', 'expired']),
            ])
            employee.has_expiring_documents = expiring > 0

    # ==================== ACTIONS ====================
    def action_view_documents(self):
        """View employee documents"""
        return {
            'name': _('Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_bank_accounts(self):
        """View employee bank accounts"""
        return {
            'name': _('Bank Accounts'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.bank',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_add_document(self):
        """Open wizard to add document"""
        return {
            'name': _('Add Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }
