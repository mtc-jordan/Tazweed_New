# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class JobOrder(models.Model):
    """Job Order from Client"""
    _name = 'tazweed.job.order'
    _description = 'Job Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Job Order Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Client
    client_id = fields.Many2one('tazweed.client', string='Client', required=True, tracking=True)
    client_contact_id = fields.Many2one(
        'tazweed.client.contact',
        string='Client Contact',
        domain="[('client_id', '=', client_id)]",
    )
    
    # Job Details
    job_id = fields.Many2one('hr.job', string='Position', required=True)
    job_title = fields.Char(string='Job Title', required=True)
    department = fields.Char(string='Department')
    
    job_category = fields.Selection([
        ('unskilled', 'Unskilled'),
        ('semi_skilled', 'Semi-Skilled'),
        ('skilled', 'Skilled'),
        ('professional', 'Professional'),
        ('managerial', 'Managerial'),
        ('executive', 'Executive'),
    ], string='Job Category', required=True)
    
    employment_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('part_time', 'Part-Time'),
        ('project', 'Project-Based'),
    ], string='Employment Type', required=True, default='permanent')
    
    # Requirements
    positions_required = fields.Integer(string='Positions Required', default=1, required=True)
    positions_filled = fields.Integer(string='Positions Filled', compute='_compute_positions_filled')
    positions_remaining = fields.Integer(string='Positions Remaining', compute='_compute_positions_filled')
    
    min_experience = fields.Float(string='Min Experience (Years)')
    max_experience = fields.Float(string='Max Experience (Years)')
    
    education_required = fields.Selection([
        ('high_school', 'High School'),
        ('diploma', 'Diploma'),
        ('bachelor', "Bachelor's Degree"),
        ('master', "Master's Degree"),
        ('phd', 'PhD'),
        ('any', 'Any'),
    ], string='Education Required', default='any')
    
    skill_ids = fields.Many2many('tazweed.skill', string='Required Skills')
    
    # Location
    work_location = fields.Char(string='Work Location')
    emirate = fields.Selection([
        ('abu_dhabi', 'Abu Dhabi'),
        ('dubai', 'Dubai'),
        ('sharjah', 'Sharjah'),
        ('ajman', 'Ajman'),
        ('umm_al_quwain', 'Umm Al Quwain'),
        ('ras_al_khaimah', 'Ras Al Khaimah'),
        ('fujairah', 'Fujairah'),
    ], string='Emirate')
    
    # Compensation
    salary_min = fields.Float(string='Salary Min')
    salary_max = fields.Float(string='Salary Max')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    benefits = fields.Text(string='Benefits')
    
    # Billing
    bill_rate = fields.Float(string='Bill Rate')
    markup_pct = fields.Float(string='Markup %')
    
    # Dates
    date_received = fields.Date(string='Date Received', default=fields.Date.today)
    date_required = fields.Date(string='Required By')
    date_closed = fields.Date(string='Date Closed')
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal', tracking=True)
    
    # Description
    description = fields.Html(string='Job Description')
    requirements = fields.Html(string='Requirements')
    responsibilities = fields.Html(string='Responsibilities')
    
    # Preferences
    gender_preference = fields.Selection([
        ('any', 'Any'),
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender Preference', default='any')
    
    age_min = fields.Integer(string='Min Age')
    age_max = fields.Integer(string='Max Age')
    
    nationality_ids = fields.Many2many('res.country', string='Preferred Nationalities')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('filled', 'Filled'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Assignment
    recruiter_id = fields.Many2one('res.users', string='Assigned Recruiter', tracking=True)
    # team_id = fields.Many2one('crm.team', string='Sales Team')  # Requires CRM module
    
    # Related Records
    pipeline_ids = fields.One2many('tazweed.recruitment.pipeline', 'job_order_id', string='Pipeline')
    placement_ids = fields.One2many('tazweed.placement', 'job_order_id', string='Placements')
    
    # Counts
    pipeline_count = fields.Integer(compute='_compute_counts')
    interview_count = fields.Integer(compute='_compute_counts')
    placement_count = fields.Integer(compute='_compute_counts')
    
    # Matching
    match_score_threshold = fields.Float(string='Match Score Threshold', default=60)
    
    notes = fields.Text(string='Internal Notes')
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Job Order reference must be unique!'),
    ]

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.job.order') or _('New')
        return super().create(vals)

    @api.depends('placement_ids', 'placement_ids.state')
    def _compute_positions_filled(self):
        for order in self:
            filled = len(order.placement_ids.filtered(lambda p: p.state in ('active', 'completed')))
            order.positions_filled = filled
            order.positions_remaining = order.positions_required - filled

    def _compute_counts(self):
        for order in self:
            order.pipeline_count = len(order.pipeline_ids)
            order.interview_count = len(order.pipeline_ids.mapped('interview_ids'))
            order.placement_count = len(order.placement_ids)

    def action_open(self):
        self.write({'state': 'open'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_hold(self):
        self.write({'state': 'on_hold'})

    def action_fill(self):
        self.write({
            'state': 'filled',
            'date_closed': fields.Date.today(),
        })

    def action_cancel(self):
        self.write({
            'state': 'cancelled',
            'date_closed': fields.Date.today(),
        })

    def action_reopen(self):
        self.write({
            'state': 'open',
            'date_closed': False,
        })

    def action_view_pipeline(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recruitment Pipeline'),
            'res_model': 'tazweed.recruitment.pipeline',
            'view_mode': 'kanban,tree,form',
            'domain': [('job_order_id', '=', self.id)],
            'context': {'default_job_order_id': self.id},
        }

    def action_view_placements(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Placements'),
            'res_model': 'tazweed.placement',
            'view_mode': 'tree,form',
            'domain': [('job_order_id', '=', self.id)],
            'context': {'default_job_order_id': self.id},
        }

    def action_find_candidates(self):
        """Find matching candidates for this job order"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Find Candidates'),
            'res_model': 'tazweed.candidate.match.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_job_order_id': self.id},
        }

    def get_matching_candidates(self, limit=50):
        """Calculate match scores for candidates"""
        self.ensure_one()
        
        domain = [('state', 'in', ('new', 'qualified', 'screening'))]
        candidates = self.env['tazweed.candidate'].search(domain, limit=limit)
        
        results = []
        for candidate in candidates:
            score = self._calculate_match_score(candidate)
            if score >= self.match_score_threshold:
                results.append({
                    'candidate_id': candidate.id,
                    'candidate_name': candidate.name,
                    'score': score,
                })
        
        return sorted(results, key=lambda x: x['score'], reverse=True)

    def _calculate_match_score(self, candidate):
        """Calculate match score between job order and candidate"""
        score = 0
        max_score = 0
        
        # Experience match (25 points)
        max_score += 25
        if self.min_experience and self.max_experience:
            if self.min_experience <= candidate.total_experience <= self.max_experience:
                score += 25
            elif candidate.total_experience >= self.min_experience:
                score += 15
        elif self.min_experience and candidate.total_experience >= self.min_experience:
            score += 25
        
        # Education match (20 points)
        max_score += 20
        education_levels = {
            'high_school': 1,
            'diploma': 2,
            'bachelor': 3,
            'master': 4,
            'phd': 5,
            'any': 0,
        }
        if self.education_required == 'any':
            score += 20
        elif candidate.education_level:
            req_level = education_levels.get(self.education_required, 0)
            cand_level = education_levels.get(candidate.education_level, 0)
            if cand_level >= req_level:
                score += 20
            elif cand_level == req_level - 1:
                score += 10
        
        # Skills match (25 points)
        max_score += 25
        if self.skill_ids and candidate.skill_ids:
            common_skills = self.skill_ids & candidate.skill_ids
            if common_skills:
                skill_ratio = len(common_skills) / len(self.skill_ids)
                score += int(25 * skill_ratio)
        elif not self.skill_ids:
            score += 25
        
        # Salary match (15 points)
        max_score += 15
        if candidate.expected_salary:
            if self.salary_min and self.salary_max:
                if self.salary_min <= candidate.expected_salary <= self.salary_max:
                    score += 15
                elif candidate.expected_salary <= self.salary_max * 1.1:
                    score += 10
            elif self.salary_max and candidate.expected_salary <= self.salary_max:
                score += 15
        else:
            score += 10  # No expectation is flexible
        
        # Availability (15 points)
        max_score += 15
        if candidate.notice_period == 'immediate':
            score += 15
        elif candidate.notice_period in ('1_week', '2_weeks'):
            score += 12
        elif candidate.notice_period == '1_month':
            score += 8
        else:
            score += 5
        
        return round((score / max_score) * 100, 1) if max_score > 0 else 0
