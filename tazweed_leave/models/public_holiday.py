# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class TazweedPublicHoliday(models.Model):
    """UAE Public Holidays"""
    _name = 'tazweed.public.holiday'
    _description = 'Public Holiday'
    _order = 'date desc'

    name = fields.Char(string='Holiday Name', required=True)
    name_ar = fields.Char(string='Holiday Name (Arabic)')
    date = fields.Date(string='Date', required=True)
    date_to = fields.Date(string='Date To', help='For multi-day holidays')
    
    holiday_type = fields.Selection([
        ('national', 'National Holiday'),
        ('religious', 'Religious Holiday'),
        ('commemorative', 'Commemorative Day'),
        ('other', 'Other'),
    ], string='Holiday Type', default='national', required=True)
    
    is_paid = fields.Boolean(
        string='Paid Holiday',
        default=True,
    )
    
    applicable_to = fields.Selection([
        ('all', 'All Employees'),
        ('uae_nationals', 'UAE Nationals Only'),
        ('private_sector', 'Private Sector Only'),
        ('public_sector', 'Public Sector Only'),
    ], string='Applicable To', default='all')
    
    year = fields.Integer(
        string='Year',
        compute='_compute_year',
        store=True,
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft')
    
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('date')
    def _compute_year(self):
        """Compute year from date"""
        for holiday in self:
            holiday.year = holiday.date.year if holiday.date else False

    @api.constrains('date', 'date_to')
    def _check_dates(self):
        """Validate dates"""
        for holiday in self:
            if holiday.date_to and holiday.date_to < holiday.date:
                raise ValidationError(_('End date must be after start date.'))

    def action_confirm(self):
        """Confirm holiday"""
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        """Cancel holiday"""
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    @api.model
    def get_holidays_in_range(self, date_from, date_to, company_id=None):
        """Get holidays within a date range"""
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'confirmed'),
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))
        return self.search(domain)

    @api.model
    def is_holiday(self, check_date, company_id=None):
        """Check if a date is a holiday"""
        domain = [
            ('date', '=', check_date),
            ('state', '=', 'confirmed'),
        ]
        if company_id:
            domain.append(('company_id', '=', company_id))
        return bool(self.search(domain, limit=1))


class TazweedPublicHolidayYear(models.Model):
    """Public Holiday Year Configuration"""
    _name = 'tazweed.public.holiday.year'
    _description = 'Public Holiday Year'
    _order = 'year desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
    )
    year = fields.Integer(string='Year', required=True)
    
    holiday_ids = fields.One2many(
        'tazweed.public.holiday',
        'year',
        string='Holidays',
        domain="[('year', '=', year)]",
    )
    
    holiday_count = fields.Integer(
        string='Holiday Count',
        compute='_compute_holiday_count',
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', default='draft')

    @api.depends('year')
    def _compute_name(self):
        """Compute name from year"""
        for record in self:
            record.name = f'Public Holidays {record.year}'

    @api.depends('holiday_ids')
    def _compute_holiday_count(self):
        """Compute holiday count"""
        for record in self:
            record.holiday_count = len(record.holiday_ids)

    def action_confirm_all(self):
        """Confirm all holidays in this year"""
        self.holiday_ids.filtered(lambda h: h.state == 'draft').action_confirm()
        self.write({'state': 'confirmed'})

    def action_generate_standard_holidays(self):
        """Generate standard UAE holidays for the year"""
        self.ensure_one()
        
        standard_holidays = [
            ('New Year\'s Day', '01-01', 'national'),
            ('Commemoration Day', '11-30', 'commemorative'),
            ('National Day', '12-02', 'national'),
            ('National Day', '12-03', 'national'),
        ]
        
        for name, date_str, holiday_type in standard_holidays:
            holiday_date = date(self.year, int(date_str.split('-')[0]), int(date_str.split('-')[1]))
            
            # Check if already exists
            existing = self.env['tazweed.public.holiday'].search([
                ('date', '=', holiday_date),
                ('name', '=', name),
            ], limit=1)
            
            if not existing:
                self.env['tazweed.public.holiday'].create({
                    'name': name,
                    'date': holiday_date,
                    'holiday_type': holiday_type,
                    'state': 'draft',
                })
        
        return True
