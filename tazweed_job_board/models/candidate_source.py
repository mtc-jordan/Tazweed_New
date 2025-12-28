# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import re
import hashlib

_logger = logging.getLogger(__name__)


class CandidateSource(models.Model):
    """Track candidates sourced from job boards"""
    _name = 'candidate.source'
    _description = 'Sourced Candidate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'candidate_name'

    # Basic Info
    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    candidate_name = fields.Char(string='Candidate Name', required=True, tracking=True)
    
    # Source Information
    job_board_id = fields.Many2one('job.board', string='Source Board', required=True)
    job_posting_id = fields.Many2one('job.posting', string='Applied To')
    hr_job_id = fields.Many2one('hr.job', string='Job Position')
    external_profile_id = fields.Char(string='External Profile ID')
    external_profile_url = fields.Char(string='Profile URL')
    
    # Contact Info
    email = fields.Char(string='Email', tracking=True)
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    linkedin_url = fields.Char(string='LinkedIn Profile')
    
    # Location
    country_id = fields.Many2one('res.country', string='Country')
    city = fields.Char(string='City')
    nationality_id = fields.Many2one('res.country', string='Nationality')
    
    # Professional Info
    current_title = fields.Char(string='Current Title')
    current_company = fields.Char(string='Current Company')
    experience_years = fields.Integer(string='Years of Experience')
    
    experience_level = fields.Selection([
        ('entry', 'Entry Level (0-2 years)'),
        ('mid', 'Mid Level (3-5 years)'),
        ('senior', 'Senior Level (6-10 years)'),
        ('expert', 'Expert (10+ years)'),
    ], string='Experience Level', compute='_compute_experience_level', store=True)
    
    # Education
    education_level = fields.Selection([
        ('high_school', 'High School'),
        ('diploma', 'Diploma'),
        ('bachelor', "Bachelor's Degree"),
        ('master', "Master's Degree"),
        ('phd', 'PhD'),
        ('other', 'Other'),
    ], string='Education Level')
    education_field = fields.Char(string='Field of Study')
    
    # Skills
    skills = fields.Text(string='Skills')
    skill_ids = fields.Many2many('hr.skill', string='Skill Tags')
    languages = fields.Char(string='Languages')
    
    # Documents
    resume = fields.Binary(string='Resume/CV')
    resume_filename = fields.Char(string='Resume Filename')
    resume_text = fields.Text(string='Parsed Resume Text')
    cover_letter = fields.Text(string='Cover Letter')
    
    # Salary Expectations
    expected_salary = fields.Float(string='Expected Salary')
    salary_currency = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    notice_period = fields.Integer(string='Notice Period (Days)')
    
    # Availability
    available_from = fields.Date(string='Available From')
    willing_to_relocate = fields.Boolean(string='Willing to Relocate')
    visa_status = fields.Selection([
        ('citizen', 'Citizen'),
        ('resident', 'Resident Visa'),
        ('visit', 'Visit Visa'),
        ('need_sponsorship', 'Needs Sponsorship'),
    ], string='Visa Status')
    
    # Scoring & Matching
    match_score = fields.Float(string='Match Score (%)', default=0)
    ai_score = fields.Float(string='AI Score', help='AI-generated relevance score')
    recruiter_rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars'),
    ], string='Recruiter Rating')
    
    # Status
    state = fields.Selection([
        ('new', 'New'),
        ('reviewing', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('contacted', 'Contacted'),
        ('interviewing', 'Interviewing'),
        ('offered', 'Offer Made'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ], string='Status', default='new', tracking=True)
    
    rejection_reason = fields.Selection([
        ('not_qualified', 'Not Qualified'),
        ('overqualified', 'Overqualified'),
        ('salary_mismatch', 'Salary Mismatch'),
        ('location', 'Location Issue'),
        ('visa', 'Visa/Work Permit Issue'),
        ('no_response', 'No Response'),
        ('other', 'Other'),
    ], string='Rejection Reason')
    rejection_notes = fields.Text(string='Rejection Notes')
    
    # Conversion
    applicant_id = fields.Many2one('hr.applicant', string='Converted to Applicant')
    employee_id = fields.Many2one('hr.employee', string='Hired as Employee')
    is_converted = fields.Boolean(string='Converted', compute='_compute_is_converted')
    
    # Duplicate Detection
    duplicate_hash = fields.Char(string='Duplicate Hash', compute='_compute_duplicate_hash', store=True)
    is_duplicate = fields.Boolean(string='Is Duplicate', compute='_compute_is_duplicate')
    duplicate_of_id = fields.Many2one('candidate.source', string='Duplicate Of')
    
    # Timestamps
    applied_date = fields.Datetime(string='Applied Date', default=fields.Datetime.now)
    first_contact_date = fields.Datetime(string='First Contact Date')
    last_activity_date = fields.Datetime(string='Last Activity')
    
    # Notes
    notes = fields.Text(string='Internal Notes')
    
    # Assigned Recruiter
    recruiter_id = fields.Many2one('res.users', string='Assigned Recruiter', tracking=True)
    
    @api.depends('experience_years')
    def _compute_experience_level(self):
        for candidate in self:
            years = candidate.experience_years or 0
            if years <= 2:
                candidate.experience_level = 'entry'
            elif years <= 5:
                candidate.experience_level = 'mid'
            elif years <= 10:
                candidate.experience_level = 'senior'
            else:
                candidate.experience_level = 'expert'
    
    @api.depends('applicant_id', 'employee_id')
    def _compute_is_converted(self):
        for candidate in self:
            candidate.is_converted = bool(candidate.applicant_id or candidate.employee_id)
    
    @api.depends('email', 'phone', 'candidate_name')
    def _compute_duplicate_hash(self):
        for candidate in self:
            # Create hash from email or phone+name
            if candidate.email:
                hash_input = candidate.email.lower().strip()
            elif candidate.phone and candidate.candidate_name:
                hash_input = f"{candidate.phone}-{candidate.candidate_name.lower()}"
            else:
                hash_input = str(candidate.id)
            
            candidate.duplicate_hash = hashlib.md5(hash_input.encode()).hexdigest()
    
    @api.depends('duplicate_hash')
    def _compute_is_duplicate(self):
        for candidate in self:
            if candidate.duplicate_hash:
                duplicates = self.search([
                    ('duplicate_hash', '=', candidate.duplicate_hash),
                    ('id', '!=', candidate.id),
                    ('id', '<', candidate.id),  # Earlier records
                ])
                candidate.is_duplicate = bool(duplicates)
                if duplicates:
                    candidate.duplicate_of_id = duplicates[0]
            else:
                candidate.is_duplicate = False
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('candidate.source') or 'New'
        return super().create(vals)
    
    def action_shortlist(self):
        """Shortlist the candidate"""
        self.write({'state': 'shortlisted'})
    
    def action_contact(self):
        """Mark as contacted"""
        self.write({
            'state': 'contacted',
            'first_contact_date': fields.Datetime.now(),
        })
    
    def action_reject(self):
        """Open rejection wizard"""
        return {
            'name': _('Reject Candidate'),
            'type': 'ir.actions.act_window',
            'res_model': 'candidate.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_candidate_ids': [(6, 0, self.ids)]},
        }
    
    def action_convert_to_applicant(self):
        """Convert sourced candidate to HR applicant"""
        self.ensure_one()
        
        if self.applicant_id:
            raise UserError(_('This candidate has already been converted to an applicant.'))
        
        # Create applicant
        applicant_vals = {
            'name': self.candidate_name,
            'partner_name': self.candidate_name,
            'email_from': self.email,
            'partner_phone': self.phone or self.mobile,
            'job_id': self.hr_job_id.id if self.hr_job_id else False,
            'source_id': self._get_or_create_source().id,
            'salary_expected': self.expected_salary,
            'description': self.notes,
        }
        
        applicant = self.env['hr.applicant'].create(applicant_vals)
        
        # Link and update status
        self.applicant_id = applicant
        self.state = 'interviewing'
        
        self.message_post(
            body=_('Converted to applicant: %s') % applicant.name,
            message_type='notification',
        )
        
        return {
            'name': _('Applicant'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.applicant',
            'res_id': applicant.id,
            'view_mode': 'form',
        }
    
    def _get_or_create_source(self):
        """Get or create UTM source for the job board"""
        Source = self.env['utm.source']
        source = Source.search([('name', '=', self.job_board_id.name)], limit=1)
        if not source:
            source = Source.create({'name': self.job_board_id.name})
        return source
    
    def action_view_profile(self):
        """Open external profile URL"""
        self.ensure_one()
        if self.external_profile_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.external_profile_url,
                'target': 'new',
            }
        elif self.linkedin_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.linkedin_url,
                'target': 'new',
            }
        else:
            raise UserError(_('No external profile URL available.'))
    
    def action_parse_resume(self):
        """Parse resume using AI (placeholder for AI integration)"""
        self.ensure_one()
        if not self.resume:
            raise UserError(_('No resume attached.'))
        
        # Placeholder for AI resume parsing
        # This would integrate with an AI service like OpenAI, Google Cloud, etc.
        self.message_post(
            body=_('Resume parsing initiated. Results will be updated shortly.'),
            message_type='notification',
        )
        
        return True
    
    def action_calculate_match_score(self):
        """Calculate match score against job requirements"""
        self.ensure_one()
        if not self.hr_job_id:
            raise UserError(_('No job position linked to calculate match score.'))
        
        score = 0
        max_score = 100
        
        # Experience match (30 points)
        if self.experience_years:
            job_min_exp = self.hr_job_id.min_experience or 0
            if self.experience_years >= job_min_exp:
                score += 30
            else:
                score += (self.experience_years / job_min_exp) * 30 if job_min_exp else 0
        
        # Skills match (40 points) - simplified
        if self.skills and self.hr_job_id.description:
            job_desc_lower = self.hr_job_id.description.lower()
            skills_list = [s.strip().lower() for s in self.skills.split(',')]
            matching_skills = sum(1 for s in skills_list if s in job_desc_lower)
            score += min(40, matching_skills * 10)
        
        # Location match (15 points)
        if self.city and self.hr_job_id.address_id:
            if self.city.lower() in (self.hr_job_id.address_id.city or '').lower():
                score += 15
        
        # Education match (15 points)
        if self.education_level in ['bachelor', 'master', 'phd']:
            score += 15
        elif self.education_level == 'diploma':
            score += 10
        
        self.match_score = min(score, max_score)
        
        return True
    
    @api.model
    def import_from_board(self, board_id, job_posting_id=None, limit=100):
        """Import candidates from a job board"""
        board = self.env['job.board'].browse(board_id)
        
        # Call board-specific import method
        method_name = f'_import_from_{board.code}'
        if hasattr(self, method_name):
            return getattr(self, method_name)(board, job_posting_id, limit)
        else:
            _logger.warning(f"No import method for board: {board.code}")
            return []
    
    def _import_from_linkedin(self, board, job_posting_id, limit):
        """Import candidates from LinkedIn"""
        # LinkedIn API implementation
        _logger.info(f"Importing candidates from LinkedIn")
        return []
    
    def _import_from_indeed(self, board, job_posting_id, limit):
        """Import candidates from Indeed"""
        _logger.info(f"Importing candidates from Indeed")
        return []
    
    def _import_from_bayt(self, board, job_posting_id, limit):
        """Import candidates from Bayt"""
        _logger.info(f"Importing candidates from Bayt")
        return []


class CandidateRejectWizard(models.TransientModel):
    """Wizard for rejecting candidates"""
    _name = 'candidate.reject.wizard'
    _description = 'Reject Candidate Wizard'
    
    candidate_ids = fields.Many2many('candidate.source', string='Candidates')
    rejection_reason = fields.Selection([
        ('not_qualified', 'Not Qualified'),
        ('overqualified', 'Overqualified'),
        ('salary_mismatch', 'Salary Mismatch'),
        ('location', 'Location Issue'),
        ('visa', 'Visa/Work Permit Issue'),
        ('no_response', 'No Response'),
        ('other', 'Other'),
    ], string='Reason', required=True)
    rejection_notes = fields.Text(string='Notes')
    send_notification = fields.Boolean(string='Send Rejection Email', default=False)
    
    def action_reject(self):
        """Reject selected candidates"""
        self.candidate_ids.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'rejection_notes': self.rejection_notes,
        })
        
        if self.send_notification:
            # Send rejection email
            template = self.env.ref('tazweed_job_board.email_template_candidate_rejection', raise_if_not_found=False)
            if template:
                for candidate in self.candidate_ids.filtered(lambda c: c.email):
                    template.send_mail(candidate.id, force_send=True)
        
        return {'type': 'ir.actions.act_window_close'}
