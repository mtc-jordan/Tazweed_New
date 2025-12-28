# -*- coding: utf-8 -*-

from odoo import models, fields, api


class RecruitmentStage(models.Model):
    """Recruitment Pipeline Stage"""
    _name = 'tazweed.recruitment.stage'
    _description = 'Recruitment Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='This stage is folded in the kanban view when there are no records in that stage.',
    )
    
    is_initial = fields.Boolean(
        string='Initial Stage',
        help='Candidates are automatically placed in this stage when added to pipeline.',
    )
    
    is_hired = fields.Boolean(
        string='Hired Stage',
        help='Candidates in this stage are considered hired.',
    )
    
    is_rejected = fields.Boolean(
        string='Rejected Stage',
        help='Candidates in this stage are considered rejected.',
    )
    
    requirements = fields.Text(
        string='Requirements',
        help='Requirements to move to this stage.',
    )
    
    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        help='Email template to send when candidate enters this stage.',
    )
    
    color = fields.Integer(string='Color Index')
    
    pipeline_count = fields.Integer(
        string='Pipeline Count',
        compute='_compute_pipeline_count',
    )

    def _compute_pipeline_count(self):
        pipeline_data = self.env['tazweed.recruitment.pipeline'].read_group(
            [('stage_id', 'in', self.ids)],
            ['stage_id'],
            ['stage_id'],
        )
        mapped_data = {data['stage_id'][0]: data['stage_id_count'] for data in pipeline_data}
        for stage in self:
            stage.pipeline_count = mapped_data.get(stage.id, 0)
