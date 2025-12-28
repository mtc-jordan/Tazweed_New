# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class JobTemplate(models.Model):
    """Reusable job posting templates"""
    _name = 'job.template'
    _description = 'Job Posting Template'
    _order = 'sequence, name'

    name = fields.Char(string='Template Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    # Template Category
    category = fields.Selection([
        ('general', 'General'),
        ('it', 'IT & Technology'),
        ('finance', 'Finance & Accounting'),
        ('hr', 'Human Resources'),
        ('sales', 'Sales & Marketing'),
        ('operations', 'Operations'),
        ('engineering', 'Engineering'),
        ('healthcare', 'Healthcare'),
        ('hospitality', 'Hospitality'),
        ('construction', 'Construction'),
        ('retail', 'Retail'),
        ('custom', 'Custom'),
    ], string='Category', default='general')
    
    # Template Content
    title_template = fields.Char(string='Title Template', help='Use {position} for job title placeholder')
    description_template = fields.Html(string='Description Template')
    requirements_template = fields.Html(string='Requirements Template')
    benefits_template = fields.Html(string='Benefits Template')
    
    # Default Settings
    default_employment_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('internship', 'Internship'),
    ], string='Default Employment Type', default='full_time')
    
    default_experience_level = fields.Selection([
        ('entry', 'Entry Level'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior Level'),
        ('executive', 'Executive'),
    ], string='Default Experience Level', default='mid')
    
    default_remote_type = fields.Selection([
        ('onsite', 'On-site'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    ], string='Default Work Type', default='onsite')
    
    # Keywords & Tags
    keywords = fields.Char(string='Keywords', help='Comma-separated keywords for SEO')
    industry_tags = fields.Char(string='Industry Tags')
    
    # Board-specific settings
    linkedin_industry = fields.Char(string='LinkedIn Industry Code')
    indeed_category = fields.Char(string='Indeed Category')
    bayt_sector = fields.Char(string='Bayt Sector')
    
    # Usage Statistics
    usage_count = fields.Integer(string='Times Used', default=0)
    last_used = fields.Datetime(string='Last Used')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    is_global = fields.Boolean(string='Available to All Companies', default=False)
    
    def action_use_template(self):
        """Open wizard to create job posting from template"""
        self.ensure_one()
        self.usage_count += 1
        self.last_used = fields.Datetime.now()
        
        return {
            'name': _('Create Job Posting from Template'),
            'type': 'ir.actions.act_window',
            'res_model': 'post.job.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_template_id': self.id,
                'default_title': self.title_template,
                'default_description': self.description_template,
                'default_requirements': self.requirements_template,
                'default_benefits': self.benefits_template,
                'default_employment_type': self.default_employment_type,
                'default_experience_level': self.default_experience_level,
                'default_remote_type': self.default_remote_type,
            },
        }
    
    def action_preview(self):
        """Preview the template"""
        self.ensure_one()
        return {
            'name': _('Template Preview'),
            'type': 'ir.actions.act_window',
            'res_model': 'job.template',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'flags': {'mode': 'readonly'},
        }
    
    @api.model
    def get_templates_by_category(self, category=None):
        """Get templates grouped by category"""
        domain = [('active', '=', True)]
        if category:
            domain.append(('category', '=', category))
        
        templates = self.search(domain)
        result = {}
        for template in templates:
            if template.category not in result:
                result[template.category] = []
            result[template.category].append({
                'id': template.id,
                'name': template.name,
                'usage_count': template.usage_count,
            })
        return result


class JobTemplateVariable(models.Model):
    """Variables that can be used in job templates"""
    _name = 'job.template.variable'
    _description = 'Job Template Variable'
    
    name = fields.Char(string='Variable Name', required=True)
    code = fields.Char(string='Variable Code', required=True, help='Use in template as {code}')
    description = fields.Text(string='Description')
    default_value = fields.Char(string='Default Value')
    
    variable_type = fields.Selection([
        ('text', 'Text'),
        ('number', 'Number'),
        ('selection', 'Selection'),
        ('date', 'Date'),
    ], string='Type', default='text')
    
    selection_options = fields.Text(string='Selection Options', help='One option per line')
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Variable code must be unique!'),
    ]
