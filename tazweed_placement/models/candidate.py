# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date


class Candidate(models.Model):
    """Candidate for Placement"""
    _name = 'tazweed.candidate'
    _description = 'Candidate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    code = fields.Char(string='Candidate ID', copy=False, readonly=True, default=lambda self: _('New'))
    
    # Personal Info
    first_name = fields.Char(string='First Name')
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name')
    
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age')
    
    nationality_id = fields.Many2one('res.country', string='Nationality')
    country_of_birth = fields.Many2one('res.country', string='Country of Birth')
    
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')
    
    # Contact
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    
    address = fields.Text(string='Current Address')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country')
    
    # Documents
    passport_no = fields.Char(string='Passport No.')
    passport_expiry = fields.Date(string='Passport Expiry')
    emirates_id = fields.Char(string='Emirates ID')
    emirates_id_expiry = fields.Date(string='Emirates ID Expiry')
    
    visa_status = fields.Selection([
        ('none', 'No Visa'),
        ('visit', 'Visit Visa'),
        ('employment', 'Employment Visa'),
        ('residence', 'Residence Visa'),
        ('cancelled', 'Cancelled'),
    ], string='Visa Status', default='none')
    
    # Qualifications
    education_level = fields.Selection([
        ('high_school', 'High School'),
        ('diploma', 'Diploma'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('phd', 'PhD'),
    ], string='Education Level')
    
    education_ids = fields.One2many('tazweed.candidate.education', 'candidate_id', string='Education')
    experience_ids = fields.One2many('tazweed.candidate.experience', 'candidate_id', string='Experience')
    
    total_experience = fields.Float(string='Total Experience (Years)', compute='_compute_experience')
    
    skill_ids = fields.Many2many('hr.skill', string='Skills')
    
    # Preferences
    expected_salary = fields.Float(string='Expected Salary')
    preferred_location = fields.Char(string='Preferred Location')
    notice_period = fields.Integer(string='Notice Period (Days)')
    available_from = fields.Date(string='Available From')
    
    # Documents
    cv = fields.Binary(string='CV/Resume')
    cv_name = fields.Char(string='CV Name')
    photo = fields.Binary(string='Photo')
    
    document_ids = fields.One2many('tazweed.candidate.document', 'candidate_id', string='Documents')
    
    # Placements
    placement_ids = fields.One2many('tazweed.placement', 'candidate_id', string='Placements')
    placement_count = fields.Integer(compute='_compute_counts')
    
    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('active', 'Active'),
        ('placed', 'Placed'),
        ('blacklisted', 'Blacklisted'),
        ('inactive', 'Inactive'),
    ], string='Status', default='new', tracking=True)
    
    source = fields.Selection([
        ('walk_in', 'Walk-in'),
        ('referral', 'Referral'),
        ('job_portal', 'Job Portal'),
        ('agency', 'Agency'),
        ('social_media', 'Social Media'),
    ], string='Source')
    
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tazweed.candidate') or _('New')
        return super().create(vals)

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for rec in self:
            if rec.date_of_birth:
                rec.age = today.year - rec.date_of_birth.year
            else:
                rec.age = 0

    @api.depends('experience_ids')
    def _compute_experience(self):
        for rec in self:
            rec.total_experience = sum(exp.duration_years for exp in rec.experience_ids)

    def _compute_counts(self):
        for rec in self:
            rec.placement_count = len(rec.placement_ids)

    def action_activate(self):
        self.write({'state': 'active'})

    def action_blacklist(self):
        self.write({'state': 'blacklisted'})


class CandidateEducation(models.Model):
    """Candidate Education"""
    _name = 'tazweed.candidate.education'
    _description = 'Candidate Education'
    _order = 'year_end desc'

    candidate_id = fields.Many2one('tazweed.candidate', required=True, ondelete='cascade')
    
    degree = fields.Char(string='Degree/Certificate', required=True)
    field_of_study = fields.Char(string='Field of Study')
    institution = fields.Char(string='Institution', required=True)
    country_id = fields.Many2one('res.country', string='Country')
    
    year_start = fields.Integer(string='Start Year')
    year_end = fields.Integer(string='End Year')
    
    grade = fields.Char(string='Grade/GPA')
    is_verified = fields.Boolean(string='Verified')


class CandidateExperience(models.Model):
    """Candidate Work Experience"""
    _name = 'tazweed.candidate.experience'
    _description = 'Candidate Experience'
    _order = 'date_end desc'

    candidate_id = fields.Many2one('tazweed.candidate', required=True, ondelete='cascade')
    
    company_name = fields.Char(string='Company', required=True)
    job_title = fields.Char(string='Job Title', required=True)
    
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    is_current = fields.Boolean(string='Current Job')
    
    duration_years = fields.Float(string='Duration (Years)', compute='_compute_duration', store=True)
    
    country_id = fields.Many2one('res.country', string='Country')
    description = fields.Text(string='Description')
    
    is_verified = fields.Boolean(string='Verified')

    @api.depends('date_start', 'date_end', 'is_current')
    def _compute_duration(self):
        for exp in self:
            if exp.date_start:
                end = exp.date_end or date.today()
                delta = end - exp.date_start
                exp.duration_years = round(delta.days / 365.25, 1)
            else:
                exp.duration_years = 0


class CandidateDocument(models.Model):
    """Candidate Document"""
    _name = 'tazweed.candidate.document'
    _description = 'Candidate Document'

    candidate_id = fields.Many2one('tazweed.candidate', required=True, ondelete='cascade')
    
    name = fields.Char(string='Document Name', required=True)
    document_type = fields.Selection([
        ('passport', 'Passport'),
        ('emirates_id', 'Emirates ID'),
        ('visa', 'Visa'),
        ('cv', 'CV/Resume'),
        ('certificate', 'Certificate'),
        ('experience_letter', 'Experience Letter'),
        ('medical', 'Medical Report'),
        ('other', 'Other'),
    ], string='Document Type', required=True)
    
    document = fields.Binary(string='Document', required=True)
    document_name = fields.Char(string='File Name')
    
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    
    is_verified = fields.Boolean(string='Verified')
    notes = fields.Text(string='Notes')
