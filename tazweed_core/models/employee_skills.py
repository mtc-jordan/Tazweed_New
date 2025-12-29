# -*- coding: utf-8 -*-
"""
Employee Skills Matrix Module
=============================
Track employee skills, certifications, and competencies with
proficiency levels, endorsements, and gap analysis.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class SkillCategory(models.Model):
    """Skill Categories for organization"""
    _name = 'employee.skill.category'
    _description = 'Skill Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category Name', required=True, translate=True)
    description = fields.Text(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color')
    
    # Parent category for hierarchy
    parent_id = fields.Many2one(
        'employee.skill.category',
        string='Parent Category',
        ondelete='cascade'
    )
    child_ids = fields.One2many(
        'employee.skill.category',
        'parent_id',
        string='Sub-categories'
    )
    
    # Skills in this category
    skill_ids = fields.One2many(
        'employee.skill',
        'category_id',
        string='Skills'
    )
    skill_count = fields.Integer(
        string='Skills Count',
        compute='_compute_skill_count'
    )
    
    def _compute_skill_count(self):
        for category in self:
            category.skill_count = len(category.skill_ids)


class Skill(models.Model):
    """Skills that can be assigned to employees"""
    _name = 'employee.skill'
    _description = 'Skill'
    _order = 'category_id, sequence, name'

    name = fields.Char(string='Skill Name', required=True, translate=True)
    description = fields.Html(string='Description')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Category
    category_id = fields.Many2one(
        'employee.skill.category',
        string='Category',
        required=True
    )
    
    # Skill type
    skill_type = fields.Selection([
        ('technical', 'Technical Skill'),
        ('soft', 'Soft Skill'),
        ('language', 'Language'),
        ('certification', 'Certification'),
        ('tool', 'Tool/Software'),
        ('domain', 'Domain Knowledge'),
    ], string='Skill Type', default='technical', required=True)
    
    # Proficiency levels
    proficiency_level_ids = fields.One2many(
        'employee.skill.proficiency.level',
        'skill_id',
        string='Proficiency Levels'
    )
    
    # Requirements
    is_certifiable = fields.Boolean(
        string='Requires Certification',
        help='This skill requires a certification to validate'
    )
    certification_validity_months = fields.Integer(
        string='Certification Validity (Months)',
        help='How long the certification is valid'
    )
    
    # Job positions requiring this skill
    job_ids = fields.Many2many(
        'hr.job',
        'job_skill_rel',
        'skill_id',
        'job_id',
        string='Required for Jobs'
    )
    
    # Statistics
    employee_count = fields.Integer(
        string='Employees with Skill',
        compute='_compute_employee_count'
    )
    
    def _compute_employee_count(self):
        for skill in self:
            skill.employee_count = self.env['employee.skill.line'].search_count([
                ('skill_id', '=', skill.id)
            ])
    
    def action_view_employees(self):
        """View employees with this skill"""
        self.ensure_one()
        skill_lines = self.env['employee.skill.line'].search([('skill_id', '=', self.id)])
        employee_ids = skill_lines.mapped('employee_id').ids
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employees with %s') % self.name,
            'res_model': 'hr.employee',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', employee_ids)],
            'context': {'create': False},
        }
    
    @api.model
    def create(self, vals):
        record = super().create(vals)
        # Create default proficiency levels if not provided
        if not record.proficiency_level_ids:
            record._create_default_proficiency_levels()
        return record
    
    def _create_default_proficiency_levels(self):
        """Create default proficiency levels for a skill"""
        self.ensure_one()
        levels = [
            {'name': 'Beginner', 'level': 1, 'description': 'Basic understanding, needs guidance'},
            {'name': 'Intermediate', 'level': 2, 'description': 'Can work independently on routine tasks'},
            {'name': 'Advanced', 'level': 3, 'description': 'Expert level, can mentor others'},
            {'name': 'Expert', 'level': 4, 'description': 'Industry-recognized expertise'},
        ]
        for level_data in levels:
            self.env['employee.skill.proficiency.level'].create({
                'skill_id': self.id,
                **level_data
            })


class SkillProficiencyLevel(models.Model):
    """Proficiency levels for skills"""
    _name = 'employee.skill.proficiency.level'
    _description = 'Skill Proficiency Level'
    _order = 'skill_id, level'

    skill_id = fields.Many2one(
        'employee.skill',
        string='Skill',
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(string='Level Name', required=True)
    level = fields.Integer(string='Level', required=True)
    description = fields.Text(string='Description')
    color = fields.Integer(string='Color')


class EmployeeSkillLine(models.Model):
    """Employee's skills with proficiency"""
    _name = 'employee.skill.line'
    _description = 'Employee Skill'
    _order = 'employee_id, skill_id'
    _rec_name = 'skill_id'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade'
    )
    skill_id = fields.Many2one(
        'employee.skill',
        string='Skill',
        required=True
    )
    category_id = fields.Many2one(
        'employee.skill.category',
        string='Category',
        related='skill_id.category_id',
        store=True
    )
    skill_type = fields.Selection(
        related='skill_id.skill_type',
        store=True
    )
    
    # Proficiency
    proficiency_level_id = fields.Many2one(
        'employee.skill.proficiency.level',
        string='Proficiency Level',
        domain="[('skill_id', '=', skill_id)]"
    )
    proficiency_level = fields.Integer(
        string='Level',
        related='proficiency_level_id.level',
        store=True
    )
    proficiency_percentage = fields.Float(
        string='Proficiency %',
        compute='_compute_proficiency_percentage',
        store=True
    )
    
    # Self-assessment vs verified
    is_self_assessed = fields.Boolean(
        string='Self Assessed',
        default=True
    )
    is_verified = fields.Boolean(
        string='Verified',
        default=False
    )
    verified_by = fields.Many2one(
        'res.users',
        string='Verified By'
    )
    verified_date = fields.Date(string='Verified Date')
    
    # Certification (if applicable)
    certification_id = fields.Many2one(
        'tazweed.employee.document',
        string='Certification Document'
    )
    certification_expiry = fields.Date(string='Certification Expiry')
    is_certification_valid = fields.Boolean(
        string='Certification Valid',
        compute='_compute_certification_valid'
    )
    
    # Experience
    years_of_experience = fields.Float(string='Years of Experience')
    last_used_date = fields.Date(string='Last Used')
    
    # Endorsements
    endorsement_ids = fields.One2many(
        'employee.skill.endorsement',
        'skill_line_id',
        string='Endorsements'
    )
    endorsement_count = fields.Integer(
        string='Endorsements',
        compute='_compute_endorsement_count'
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    
    _sql_constraints = [
        ('employee_skill_unique', 'unique(employee_id, skill_id)',
         'An employee can only have each skill once!')
    ]
    
    @api.depends('proficiency_level_id', 'skill_id')
    def _compute_proficiency_percentage(self):
        for line in self:
            if line.proficiency_level_id and line.skill_id:
                max_level = max(line.skill_id.proficiency_level_ids.mapped('level') or [1])
                line.proficiency_percentage = (line.proficiency_level / max_level) * 100
            else:
                line.proficiency_percentage = 0
    
    @api.depends('certification_expiry')
    def _compute_certification_valid(self):
        today = fields.Date.today()
        for line in self:
            if line.certification_expiry:
                line.is_certification_valid = line.certification_expiry >= today
            else:
                line.is_certification_valid = True
    
    def _compute_endorsement_count(self):
        for line in self:
            line.endorsement_count = len(line.endorsement_ids)
    
    def action_verify(self):
        """Verify the skill"""
        self.ensure_one()
        self.write({
            'is_verified': True,
            'verified_by': self.env.user.id,
            'verified_date': fields.Date.today(),
        })
        return True
    
    def action_request_endorsement(self):
        """Request endorsement from colleagues"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Endorsement'),
            'res_model': 'employee.skill.endorsement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_skill_line_id': self.id,
            },
        }


class EmployeeSkillEndorsement(models.Model):
    """Endorsements from colleagues"""
    _name = 'employee.skill.endorsement'
    _description = 'Skill Endorsement'
    _order = 'create_date desc'

    skill_line_id = fields.Many2one(
        'employee.skill.line',
        string='Skill',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='skill_line_id.employee_id',
        store=True
    )
    skill_id = fields.Many2one(
        'employee.skill',
        string='Skill',
        related='skill_line_id.skill_id',
        store=True
    )
    
    # Endorser
    endorser_id = fields.Many2one(
        'hr.employee',
        string='Endorsed By',
        required=True
    )
    endorser_user_id = fields.Many2one(
        'res.users',
        string='Endorser User',
        related='endorser_id.user_id'
    )
    
    # Endorsement details
    rating = fields.Selection([
        ('1', 'Basic'),
        ('2', 'Good'),
        ('3', 'Very Good'),
        ('4', 'Excellent'),
        ('5', 'Expert'),
    ], string='Rating', required=True)
    comment = fields.Text(string='Comment')
    
    # Relationship
    relationship = fields.Selection([
        ('manager', 'Manager'),
        ('peer', 'Peer/Colleague'),
        ('subordinate', 'Direct Report'),
        ('client', 'Client'),
        ('external', 'External'),
    ], string='Relationship', required=True)
    
    _sql_constraints = [
        ('endorsement_unique', 'unique(skill_line_id, endorser_id)',
         'Each person can only endorse a skill once!')
    ]


class SkillGapAnalysis(models.Model):
    """Skill gap analysis for employees or teams"""
    _name = 'employee.skill.gap.analysis'
    _description = 'Skill Gap Analysis'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Analysis Name', required=True)
    
    # Scope
    analysis_type = fields.Selection([
        ('employee', 'Individual Employee'),
        ('department', 'Department'),
        ('job', 'Job Position'),
        ('team', 'Custom Team'),
    ], string='Analysis Type', required=True, default='employee')
    
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one('hr.department', string='Department')
    job_id = fields.Many2one('hr.job', string='Job Position')
    employee_ids = fields.Many2many(
        'hr.employee',
        'skill_gap_employee_rel',
        string='Team Members'
    )
    
    # Required skills (target)
    required_skill_ids = fields.One2many(
        'employee.skill.gap.requirement',
        'analysis_id',
        string='Required Skills'
    )
    
    # Results
    gap_line_ids = fields.One2many(
        'employee.skill.gap.line',
        'analysis_id',
        string='Gap Analysis Results'
    )
    
    # Summary
    total_skills = fields.Integer(
        string='Total Skills',
        compute='_compute_summary'
    )
    skills_met = fields.Integer(
        string='Skills Met',
        compute='_compute_summary'
    )
    skills_gap = fields.Integer(
        string='Skills Gap',
        compute='_compute_summary'
    )
    gap_percentage = fields.Float(
        string='Gap %',
        compute='_compute_summary'
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('analyzing', 'Analyzing'),
        ('completed', 'Completed'),
    ], string='Status', default='draft')
    
    analysis_date = fields.Date(string='Analysis Date')
    notes = fields.Html(string='Notes')
    
    @api.depends('gap_line_ids')
    def _compute_summary(self):
        for analysis in self:
            lines = analysis.gap_line_ids
            total = len(lines)
            met = len(lines.filtered(lambda l: l.gap_status == 'met'))
            
            analysis.total_skills = total
            analysis.skills_met = met
            analysis.skills_gap = total - met
            analysis.gap_percentage = ((total - met) / total * 100) if total > 0 else 0
    
    def action_analyze(self):
        """Run the gap analysis"""
        self.ensure_one()
        self.write({'state': 'analyzing'})
        
        # Clear previous results
        self.gap_line_ids.unlink()
        
        # Get employees to analyze
        employees = self._get_employees_to_analyze()
        
        # Analyze each required skill
        for req in self.required_skill_ids:
            for employee in employees:
                # Find employee's skill level
                skill_line = self.env['employee.skill.line'].search([
                    ('employee_id', '=', employee.id),
                    ('skill_id', '=', req.skill_id.id),
                ], limit=1)
                
                current_level = skill_line.proficiency_level if skill_line else 0
                gap = req.required_level - current_level
                
                if gap > 0:
                    status = 'gap'
                elif gap < 0:
                    status = 'exceeded'
                else:
                    status = 'met'
                
                self.env['employee.skill.gap.line'].create({
                    'analysis_id': self.id,
                    'employee_id': employee.id,
                    'skill_id': req.skill_id.id,
                    'required_level': req.required_level,
                    'current_level': current_level,
                    'gap': gap,
                    'gap_status': status,
                })
        
        self.write({
            'state': 'completed',
            'analysis_date': fields.Date.today(),
        })
        
        return True
    
    def _get_employees_to_analyze(self):
        """Get list of employees based on analysis type"""
        self.ensure_one()
        
        if self.analysis_type == 'employee':
            return self.employee_id
        elif self.analysis_type == 'department':
            return self.env['hr.employee'].search([
                ('department_id', '=', self.department_id.id)
            ])
        elif self.analysis_type == 'job':
            return self.env['hr.employee'].search([
                ('job_id', '=', self.job_id.id)
            ])
        elif self.analysis_type == 'team':
            return self.employee_ids
        
        return self.env['hr.employee']
    
    def action_create_training_plan(self):
        """Create training plan based on gaps"""
        self.ensure_one()
        # This would integrate with a training module
        return {
            'type': 'ir.actions.act_window',
            'name': _('Training Plan'),
            'res_model': 'employee.skill.gap.line',
            'view_mode': 'tree,form',
            'domain': [('analysis_id', '=', self.id), ('gap_status', '=', 'gap')],
        }


class SkillGapRequirement(models.Model):
    """Required skills for gap analysis"""
    _name = 'employee.skill.gap.requirement'
    _description = 'Skill Gap Requirement'

    analysis_id = fields.Many2one(
        'employee.skill.gap.analysis',
        string='Analysis',
        required=True,
        ondelete='cascade'
    )
    skill_id = fields.Many2one(
        'employee.skill',
        string='Skill',
        required=True
    )
    required_level = fields.Integer(
        string='Required Level',
        required=True,
        default=2
    )
    is_mandatory = fields.Boolean(string='Mandatory', default=True)
    notes = fields.Text(string='Notes')


class SkillGapLine(models.Model):
    """Gap analysis results"""
    _name = 'employee.skill.gap.line'
    _description = 'Skill Gap Line'

    analysis_id = fields.Many2one(
        'employee.skill.gap.analysis',
        string='Analysis',
        required=True,
        ondelete='cascade'
    )
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    skill_id = fields.Many2one('employee.skill', string='Skill', required=True)
    
    required_level = fields.Integer(string='Required Level')
    current_level = fields.Integer(string='Current Level')
    gap = fields.Integer(string='Gap')
    
    gap_status = fields.Selection([
        ('gap', 'Gap'),
        ('met', 'Met'),
        ('exceeded', 'Exceeded'),
    ], string='Status')
    
    # Training recommendation
    training_recommendation = fields.Text(string='Training Recommendation')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Priority', compute='_compute_priority', store=True)
    
    @api.depends('gap')
    def _compute_priority(self):
        for line in self:
            if line.gap >= 3:
                line.priority = 'critical'
            elif line.gap == 2:
                line.priority = 'high'
            elif line.gap == 1:
                line.priority = 'medium'
            else:
                line.priority = 'low'


class HrEmployee(models.Model):
    """Extend HR Employee for skills"""
    _inherit = 'hr.employee'
    
    skill_line_ids = fields.One2many(
        'employee.skill.line',
        'employee_id',
        string='Skills'
    )
    skill_count = fields.Integer(
        string='Skills Count',
        compute='_compute_skill_count'
    )
    verified_skill_count = fields.Integer(
        string='Verified Skills',
        compute='_compute_skill_count'
    )
    
    # Skill summary by type
    technical_skills = fields.Integer(
        string='Technical Skills',
        compute='_compute_skill_count'
    )
    soft_skills = fields.Integer(
        string='Soft Skills',
        compute='_compute_skill_count'
    )
    certifications = fields.Integer(
        string='Certifications',
        compute='_compute_skill_count'
    )
    
    def _compute_skill_count(self):
        for employee in self:
            skills = employee.skill_line_ids
            employee.skill_count = len(skills)
            employee.verified_skill_count = len(skills.filtered('is_verified'))
            employee.technical_skills = len(skills.filtered(
                lambda s: s.skill_type == 'technical'
            ))
            employee.soft_skills = len(skills.filtered(
                lambda s: s.skill_type == 'soft'
            ))
            employee.certifications = len(skills.filtered(
                lambda s: s.skill_type == 'certification'
            ))
    
    def action_view_skills(self):
        """View employee skills"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Skills'),
            'res_model': 'employee.skill.line',
            'view_mode': 'tree,form,kanban',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
    
    def action_skill_gap_analysis(self):
        """Run skill gap analysis for this employee"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Skill Gap Analysis'),
            'res_model': 'employee.skill.gap.analysis',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_analysis_type': 'employee',
                'default_employee_id': self.id,
                'default_name': f'Skill Gap Analysis - {self.name}',
            },
        }


class HrJob(models.Model):
    """Extend HR Job for required skills"""
    _inherit = 'hr.job'
    
    required_skill_ids = fields.Many2many(
        'employee.skill',
        'job_skill_rel',
        'job_id',
        'skill_id',
        string='Required Skills'
    )
    
    def action_view_skill_matrix(self):
        """View skill matrix for this job position"""
        self.ensure_one()
        employees = self.env['hr.employee'].search([
            ('job_id', '=', self.id)
        ])
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Skill Matrix'),
            'res_model': 'employee.skill.line',
            'view_mode': 'pivot,tree',
            'domain': [('employee_id', 'in', employees.ids)],
        }
