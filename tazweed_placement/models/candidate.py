# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date
from dateutil.relativedelta import relativedelta


class Candidate(models.Model):
    """Recruitment Candidate"""
    _name = 'tazweed.candidate'
    _description = 'Candidate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    code = fields.Char(
        string='Candidate ID',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Photo
    image_1920 = fields.Image(string='Photo', max_width=1920, max_height=1920)
    image_128 = fields.Image(string='Photo', max_width=128, max_height=128, store=True)
    
    # Personal Info
    first_name = fields.Char(string='First Name')
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name')
    
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender')
    
    date_of_birth = fields.Date(string='Date of Birth')
    age = fields.Integer(string='Age', compute='_compute_age')
    
    nationality_id = fields.Many2one('res.country', string='Nationality')
    is_uae_national = fields.Boolean(string='UAE National', compute='_compute_is_uae_national', store=True)
    
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ], string='Marital Status')
    
    religion = fields.Selection([
        ('islam', 'Islam'),
        ('christianity', 'Christianity'),
        ('hinduism', 'Hinduism'),
        ('buddhism', 'Buddhism'),
        ('other', 'Other'),
    ], string='Religion')
    
    # Contact
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile', required=True)
    whatsapp = fields.Char(string='WhatsApp')
    
    address = fields.Text(string='Current Address')
    city = fields.Char(string='City')
    country_id = fields.Many2one('res.country', string='Country')
    
    # Professional
    job_title = fields.Char(string='Current/Last Job Title')
    current_employer = fields.Char(string='Current/Last Employer')
    
    total_experience = fields.Float(string='Total Experience (Years)', compute='_compute_total_experience', store=True)
    
    education_level = fields.Selection([
        ('high_school', 'High School'),
        ('diploma', 'Diploma'),
        ('bachelor', "Bachelor's Degree"),
        ('master', "Master's Degree"),
        ('phd', 'PhD'),
        ('other', 'Other'),
    ], string='Highest Education')
    
    # Skills
    skill_ids = fields.Many2many('tazweed.skill', string='Skills')
    languages = fields.Char(string='Languages')
    
    # Documents
    passport_number = fields.Char(string='Passport Number')
    passport_expiry = fields.Date(string='Passport Expiry')
    
    visa_status = fields.Selection([
        ('none', 'No Visa'),
        ('visit', 'Visit Visa'),
        ('employment', 'Employment Visa'),
        ('residence', 'Residence Visa'),
        ('cancelled', 'Cancelled'),
    ], string='Visa Status', default='none')
    
    visa_expiry = fields.Date(string='Visa Expiry')
    
    # Expectations
    expected_salary = fields.Float(string='Expected Salary')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    notice_period = fields.Selection([
        ('immediate', 'Immediate'),
        ('1_week', '1 Week'),
        ('2_weeks', '2 Weeks'),
        ('1_month', '1 Month'),
        ('2_months', '2 Months'),
        ('3_months', '3 Months'),
    ], string='Notice Period', default='immediate')
    
    available_from = fields.Date(string='Available From')
    
    willing_to_relocate = fields.Boolean(string='Willing to Relocate')
    preferred_locations = fields.Char(string='Preferred Locations')
    
    # Source
    source = fields.Selection([
        ('website', 'Website'),
        ('referral', 'Referral'),
        ('job_portal', 'Job Portal'),
        ('social_media', 'Social Media'),
        ('walk_in', 'Walk-in'),
        ('agency', 'Agency'),
        ('other', 'Other'),
    ], string='Source', tracking=True)
    
    source_detail = fields.Char(string='Source Detail')
    referred_by = fields.Many2one('res.users', string='Referred By')
    
    # Resume
    resume = fields.Binary(string='Resume/CV')
    resume_name = fields.Char(string='Resume Filename')
    
    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('screening', 'Screening'),
        ('qualified', 'Qualified'),
        ('in_process', 'In Process'),
        ('placed', 'Placed'),
        ('rejected', 'Rejected'),
        ('blacklisted', 'Blacklisted'),
    ], string='Status', default='new', tracking=True)
    
    # Related Records
    education_ids = fields.One2many('tazweed.candidate.education', 'candidate_id', string='Education')
    experience_ids = fields.One2many('tazweed.candidate.experience', 'candidate_id', string='Experience')
    document_ids = fields.One2many('tazweed.candidate.document', 'candidate_id', string='Documents')
    pipeline_ids = fields.One2many('tazweed.recruitment.pipeline', 'candidate_id', string='Pipeline Records')
    interview_ids = fields.One2many('tazweed.interview', 'candidate_id', string='Interviews')
    placement_ids = fields.One2many('tazweed.placement', 'candidate_id', string='Placements')
    
    # Counts
    pipeline_count = fields.Integer(compute='_compute_counts')
    interview_count = fields.Integer(compute='_compute_counts')
    placement_count = fields.Integer(compute='_compute_counts')
    
    # Scoring
    profile_score = fields.Float(string='Profile Score', compute='_compute_profile_score', store=True)
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Candidate ID must be unique!'),
        ('email_uniq', 'unique(email)', 'Email must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('code', _('New')) == _('New'):
            vals['code'] = self.env['ir.sequence'].next_by_code('tazweed.candidate') or _('New')
        return super().create(vals)

    @api.depends('date_of_birth')
    def _compute_age(self):
        today = date.today()
        for candidate in self:
            if candidate.date_of_birth:
                candidate.age = relativedelta(today, candidate.date_of_birth).years
            else:
                candidate.age = 0

    @api.depends('nationality_id')
    def _compute_is_uae_national(self):
        uae = self.env.ref('base.ae', raise_if_not_found=False)
        for candidate in self:
            candidate.is_uae_national = candidate.nationality_id == uae if uae else False

    @api.depends('experience_ids', 'experience_ids.duration_years')
    def _compute_total_experience(self):
        for candidate in self:
            candidate.total_experience = sum(exp.duration_years for exp in candidate.experience_ids)

    def _compute_counts(self):
        for candidate in self:
            candidate.pipeline_count = len(candidate.pipeline_ids)
            candidate.interview_count = len(candidate.interview_ids)
            candidate.placement_count = len(candidate.placement_ids)

    @api.depends('education_ids', 'experience_ids', 'skill_ids', 'resume', 'passport_number')
    def _compute_profile_score(self):
        """Calculate profile completeness score (0-100)"""
        for candidate in self:
            score = 0
            # Basic info (30 points)
            if candidate.name:
                score += 5
            if candidate.email:
                score += 5
            if candidate.mobile:
                score += 5
            if candidate.nationality_id:
                score += 5
            if candidate.date_of_birth:
                score += 5
            if candidate.image_1920:
                score += 5
            
            # Professional (30 points)
            if candidate.education_ids:
                score += 10
            if candidate.experience_ids:
                score += 10
            if candidate.skill_ids:
                score += 10
            
            # Documents (20 points)
            if candidate.resume:
                score += 10
            if candidate.passport_number:
                score += 5
            if candidate.document_ids:
                score += 5
            
            # Expectations (20 points)
            if candidate.expected_salary:
                score += 10
            if candidate.notice_period:
                score += 5
            if candidate.available_from:
                score += 5
            
            candidate.profile_score = score

    def action_qualify(self):
        self.write({'state': 'qualified'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_blacklist(self):
        self.write({'state': 'blacklisted'})

    def action_reactivate(self):
        self.write({'state': 'new'})

    def action_view_pipeline(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pipeline'),
            'res_model': 'tazweed.recruitment.pipeline',
            'view_mode': 'kanban,tree,form',
            'domain': [('candidate_id', '=', self.id)],
            'context': {'default_candidate_id': self.id},
        }

    def action_view_interviews(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Interviews'),
            'res_model': 'tazweed.interview',
            'view_mode': 'tree,form,calendar',
            'domain': [('candidate_id', '=', self.id)],
            'context': {'default_candidate_id': self.id},
        }


class CandidateEducation(models.Model):
    """Candidate Education History"""
    _name = 'tazweed.candidate.education'
    _description = 'Candidate Education'
    _order = 'date_end desc, date_start desc'

    candidate_id = fields.Many2one('tazweed.candidate', required=True, ondelete='cascade')
    
    degree = fields.Selection([
        ('high_school', 'High School'),
        ('diploma', 'Diploma'),
        ('bachelor', "Bachelor's Degree"),
        ('master', "Master's Degree"),
        ('phd', 'PhD'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ], string='Degree', required=True)
    
    field_of_study = fields.Char(string='Field of Study', required=True)
    institution = fields.Char(string='Institution', required=True)
    country_id = fields.Many2one('res.country', string='Country')
    
    date_start = fields.Date(string='Start Date')
    date_end = fields.Date(string='End Date')
    
    grade = fields.Char(string='Grade/GPA')
    is_completed = fields.Boolean(string='Completed', default=True)
    
    certificate = fields.Binary(string='Certificate')
    certificate_name = fields.Char(string='Certificate Filename')
    
    notes = fields.Text(string='Notes')


class CandidateExperience(models.Model):
    """Candidate Work Experience"""
    _name = 'tazweed.candidate.experience'
    _description = 'Candidate Experience'
    _order = 'date_end desc, date_start desc'

    candidate_id = fields.Many2one('tazweed.candidate', required=True, ondelete='cascade')
    
    company = fields.Char(string='Company', required=True)
    job_title = fields.Char(string='Job Title', required=True)
    
    industry_id = fields.Many2one('res.partner.industry', string='Industry')
    country_id = fields.Many2one('res.country', string='Country')
    city = fields.Char(string='City')
    
    date_start = fields.Date(string='Start Date', required=True)
    date_end = fields.Date(string='End Date')
    is_current = fields.Boolean(string='Current Job')
    
    duration_years = fields.Float(string='Duration (Years)', compute='_compute_duration', store=True)
    
    responsibilities = fields.Text(string='Responsibilities')
    achievements = fields.Text(string='Achievements')
    
    salary = fields.Float(string='Salary')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    reason_leaving = fields.Char(string='Reason for Leaving')
    
    reference_name = fields.Char(string='Reference Name')
    reference_phone = fields.Char(string='Reference Phone')
    reference_email = fields.Char(string='Reference Email')

    @api.depends('date_start', 'date_end', 'is_current')
    def _compute_duration(self):
        today = date.today()
        for exp in self:
            if exp.date_start:
                end_date = today if exp.is_current else (exp.date_end or today)
                delta = relativedelta(end_date, exp.date_start)
                exp.duration_years = delta.years + delta.months / 12
            else:
                exp.duration_years = 0


class CandidateDocument(models.Model):
    """Candidate Document"""
    _name = 'tazweed.candidate.document'
    _description = 'Candidate Document'
    _order = 'create_date desc'

    candidate_id = fields.Many2one('tazweed.candidate', required=True, ondelete='cascade')
    
    name = fields.Char(string='Document Name', required=True)
    document_type = fields.Selection([
        ('passport', 'Passport'),
        ('visa', 'Visa'),
        ('emirates_id', 'Emirates ID'),
        ('resume', 'Resume/CV'),
        ('certificate', 'Certificate'),
        ('degree', 'Degree'),
        ('experience_letter', 'Experience Letter'),
        ('photo', 'Photo'),
        ('other', 'Other'),
    ], string='Document Type', required=True)
    
    document = fields.Binary(string='Document', required=True)
    document_name = fields.Char(string='File Name')
    
    document_number = fields.Char(string='Document Number')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    
    is_verified = fields.Boolean(string='Verified')
    verified_by = fields.Many2one('res.users', string='Verified By')
    verified_date = fields.Date(string='Verified Date')
    
    notes = fields.Text(string='Notes')
