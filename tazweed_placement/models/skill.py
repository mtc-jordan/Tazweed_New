# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TazweedSkill(models.Model):
    """Skills for Candidates and Job Orders"""
    _name = 'tazweed.skill'
    _description = 'Skill'
    _order = 'name'

    name = fields.Char(string='Skill Name', required=True)
    category = fields.Selection([
        ('technical', 'Technical'),
        ('soft', 'Soft Skills'),
        ('language', 'Language'),
        ('certification', 'Certification'),
        ('other', 'Other'),
    ], string='Category', default='technical')
    
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Skill name must be unique!'),
    ]
