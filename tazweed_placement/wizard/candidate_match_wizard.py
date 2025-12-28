# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CandidateMatchWizard(models.TransientModel):
    """Wizard to find and add matching candidates to pipeline"""
    _name = 'tazweed.candidate.match.wizard'
    _description = 'Find Matching Candidates'

    job_order_id = fields.Many2one('tazweed.job.order', string='Job Order', required=True)
    
    # Filters
    min_score = fields.Float(string='Minimum Match Score', default=50)
    max_results = fields.Integer(string='Maximum Results', default=50)
    
    # Results
    match_ids = fields.One2many('tazweed.candidate.match.line', 'wizard_id', string='Matching Candidates')
    
    def action_search(self):
        """Search for matching candidates"""
        self.ensure_one()
        
        # Clear previous results
        self.match_ids.unlink()
        
        # Get matching candidates
        matches = self.job_order_id.get_matching_candidates(limit=self.max_results)
        
        # Create match lines
        for match in matches:
            if match['score'] >= self.min_score:
                self.env['tazweed.candidate.match.line'].create({
                    'wizard_id': self.id,
                    'candidate_id': match['candidate_id'],
                    'match_score': match['score'],
                })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Matching Candidates'),
            'res_model': 'tazweed.candidate.match.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_add_selected(self):
        """Add selected candidates to pipeline"""
        self.ensure_one()
        
        selected = self.match_ids.filtered(lambda m: m.selected)
        if not selected:
            raise ValidationError(_('Please select at least one candidate.'))
        
        # Get initial stage
        initial_stage = self.env['tazweed.recruitment.stage'].search([('is_initial', '=', True)], limit=1)
        if not initial_stage:
            initial_stage = self.env['tazweed.recruitment.stage'].search([], limit=1)
        
        pipeline_ids = []
        for match in selected:
            # Check if already in pipeline
            existing = self.env['tazweed.recruitment.pipeline'].search([
                ('candidate_id', '=', match.candidate_id.id),
                ('job_order_id', '=', self.job_order_id.id),
            ])
            
            if not existing:
                pipeline = self.env['tazweed.recruitment.pipeline'].create({
                    'candidate_id': match.candidate_id.id,
                    'job_order_id': self.job_order_id.id,
                    'stage_id': initial_stage.id if initial_stage else False,
                })
                pipeline_ids.append(pipeline.id)
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pipeline'),
            'res_model': 'tazweed.recruitment.pipeline',
            'view_mode': 'kanban,tree,form',
            'domain': [('job_order_id', '=', self.job_order_id.id)],
        }


class CandidateMatchLine(models.TransientModel):
    """Match result line"""
    _name = 'tazweed.candidate.match.line'
    _description = 'Candidate Match Line'
    _order = 'match_score desc'

    wizard_id = fields.Many2one('tazweed.candidate.match.wizard', required=True, ondelete='cascade')
    candidate_id = fields.Many2one('tazweed.candidate', string='Candidate', required=True)
    
    # Candidate Info
    candidate_name = fields.Char(related='candidate_id.name')
    candidate_email = fields.Char(related='candidate_id.email')
    candidate_mobile = fields.Char(related='candidate_id.mobile')
    total_experience = fields.Float(related='candidate_id.total_experience')
    education_level = fields.Selection(related='candidate_id.education_level')
    expected_salary = fields.Float(related='candidate_id.expected_salary')
    
    match_score = fields.Float(string='Match Score')
    selected = fields.Boolean(string='Select', default=False)
