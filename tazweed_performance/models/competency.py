# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Competency(models.Model):
    """Competency Definition"""
    _name = 'tazweed.competency'
    _description = 'Competency'
    _inherit = ['mail.thread']
    _order = 'category, name'

    name = fields.Char(string='Competency Name', required=True, tracking=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    
    category = fields.Selection([
        ('core', 'Core Competency'),
        ('functional', 'Functional Competency'),
        ('leadership', 'Leadership Competency'),
        ('technical', 'Technical Competency'),
        ('behavioral', 'Behavioral Competency'),
    ], string='Category', required=True, default='core')
    
    competency_type = fields.Selection([
        ('required', 'Required'),
        ('preferred', 'Preferred'),
        ('optional', 'Optional'),
    ], string='Type', default='required')
    
    # Proficiency Levels
    level_1_description = fields.Text(string='Level 1 - Basic')
    level_2_description = fields.Text(string='Level 2 - Developing')
    level_3_description = fields.Text(string='Level 3 - Proficient')
    level_4_description = fields.Text(string='Level 4 - Advanced')
    level_5_description = fields.Text(string='Level 5 - Expert')
    
    # Behavioral Indicators
    behavioral_indicators = fields.Text(string='Behavioral Indicators')
    
    # Applicability
    department_ids = fields.Many2many(
        'hr.department',
        string='Applicable Departments',
    )
    job_ids = fields.Many2many(
        'hr.job',
        string='Applicable Job Positions',
    )
    
    # Related Skills
    skill_ids = fields.Many2many(
        'hr.skill',
        string='Related Skills',
    )
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )


class CompetencyAssessment(models.Model):
    """Competency Assessment"""
    _name = 'tazweed.competency.assessment'
    _description = 'Competency Assessment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
    )
    assessor_id = fields.Many2one(
        'hr.employee',
        string='Assessor',
        default=lambda self: self.env.user.employee_id,
    )
    
    date = fields.Date(string='Assessment Date', default=fields.Date.today)
    
    assessment_type = fields.Selection([
        ('self', 'Self Assessment'),
        ('manager', 'Manager Assessment'),
        ('peer', 'Peer Assessment'),
        ('360', '360-Degree Assessment'),
    ], string='Assessment Type', default='manager')
    
    line_ids = fields.One2many(
        'tazweed.competency.assessment.line',
        'assessment_id',
        string='Competency Lines',
    )
    
    overall_rating = fields.Float(
        string='Overall Rating',
        compute='_compute_overall_rating',
        store=True,
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    
    notes = fields.Text(string='Notes')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.competency.assessment') or _('New')
        return super().create(vals)

    @api.depends('line_ids.rating')
    def _compute_overall_rating(self):
        for assessment in self:
            if assessment.line_ids:
                assessment.overall_rating = sum(l.rating for l in assessment.line_ids) / len(assessment.line_ids)
            else:
                assessment.overall_rating = 0

    def action_start(self):
        """Start assessment"""
        self.write({'state': 'in_progress'})
        return True

    def action_complete(self):
        """Complete assessment"""
        self.write({'state': 'completed'})
        return True


class CompetencyAssessmentLine(models.Model):
    """Competency Assessment Line"""
    _name = 'tazweed.competency.assessment.line'
    _description = 'Competency Assessment Line'

    assessment_id = fields.Many2one(
        'tazweed.competency.assessment',
        string='Assessment',
        required=True,
        ondelete='cascade',
    )
    competency_id = fields.Many2one(
        'tazweed.competency',
        string='Competency',
        required=True,
    )
    
    expected_level = fields.Selection([
        ('1', 'Basic'),
        ('2', 'Developing'),
        ('3', 'Proficient'),
        ('4', 'Advanced'),
        ('5', 'Expert'),
    ], string='Expected Level', default='3')
    
    rating = fields.Float(string='Rating', digits=(3, 2))
    
    gap = fields.Float(string='Gap', compute='_compute_gap', store=True)
    
    strengths = fields.Text(string='Strengths')
    development_areas = fields.Text(string='Development Areas')
    comments = fields.Text(string='Comments')

    @api.depends('rating', 'expected_level')
    def _compute_gap(self):
        for line in self:
            expected = float(line.expected_level or 0)
            line.gap = expected - (line.rating or 0)


class CompetencyMatrix(models.Model):
    """Competency Matrix for Job Positions"""
    _name = 'tazweed.competency.matrix'
    _description = 'Competency Matrix'

    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        required=True,
    )
    competency_id = fields.Many2one(
        'tazweed.competency',
        string='Competency',
        required=True,
    )
    
    required_level = fields.Selection([
        ('1', 'Basic'),
        ('2', 'Developing'),
        ('3', 'Proficient'),
        ('4', 'Advanced'),
        ('5', 'Expert'),
    ], string='Required Level', default='3')
    
    weight = fields.Float(string='Weight (%)', default=100)
    is_critical = fields.Boolean(string='Critical')
    
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('job_competency_uniq', 'unique(job_id, competency_id)', 
         'Competency already exists for this job position!'),
    ]
