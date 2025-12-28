# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AddToPipelineWizard(models.TransientModel):
    """Wizard to add candidate to job order pipeline"""
    _name = 'tazweed.add.pipeline.wizard'
    _description = 'Add to Pipeline'

    candidate_id = fields.Many2one('tazweed.candidate', string='Candidate', required=True)
    job_order_id = fields.Many2one(
        'tazweed.job.order',
        string='Job Order',
        required=True,
        domain="[('state', 'in', ('open', 'in_progress'))]",
    )
    
    stage_id = fields.Many2one('tazweed.recruitment.stage', string='Initial Stage')
    recruiter_id = fields.Many2one('res.users', string='Recruiter', default=lambda self: self.env.user)
    
    notes = fields.Text(string='Notes')

    @api.onchange('job_order_id')
    def _onchange_job_order(self):
        if self.job_order_id:
            # Get initial stage
            initial = self.env['tazweed.recruitment.stage'].search([('is_initial', '=', True)], limit=1)
            if initial:
                self.stage_id = initial.id

    def action_add(self):
        """Add candidate to pipeline"""
        self.ensure_one()
        
        # Check if already in pipeline
        existing = self.env['tazweed.recruitment.pipeline'].search([
            ('candidate_id', '=', self.candidate_id.id),
            ('job_order_id', '=', self.job_order_id.id),
        ])
        
        if existing:
            raise ValidationError(_('Candidate is already in pipeline for this job order.'))
        
        # Get stage
        stage = self.stage_id
        if not stage:
            stage = self.env['tazweed.recruitment.stage'].search([('is_initial', '=', True)], limit=1)
        if not stage:
            stage = self.env['tazweed.recruitment.stage'].search([], limit=1)
        
        pipeline = self.env['tazweed.recruitment.pipeline'].create({
            'candidate_id': self.candidate_id.id,
            'job_order_id': self.job_order_id.id,
            'stage_id': stage.id if stage else False,
            'recruiter_id': self.recruiter_id.id,
            'notes': self.notes,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pipeline'),
            'res_model': 'tazweed.recruitment.pipeline',
            'view_mode': 'form',
            'res_id': pipeline.id,
        }
