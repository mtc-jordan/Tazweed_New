# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProServiceCategory(models.Model):
    """Categories for PRO services"""
    _name = 'pro.service.category'
    _description = 'PRO Service Category'
    _order = 'sequence, name'
    _parent_name = 'parent_id'
    _parent_store = True

    name = fields.Char(string='Category Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Hierarchy
    parent_id = fields.Many2one(
        'pro.service.category',
        string='Parent Category',
        ondelete='cascade',
        index=True
    )
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many(
        'pro.service.category',
        'parent_id',
        string='Sub Categories'
    )
    
    # Details
    description = fields.Text(string='Description')
    icon = fields.Char(string='Icon', help='Font Awesome icon class')
    color = fields.Integer(string='Color Index')
    
    # Related
    service_ids = fields.One2many(
        'pro.service',
        'category_id',
        string='Services'
    )
    service_count = fields.Integer(
        string='Service Count',
        compute='_compute_service_count'
    )
    
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Category code must be unique!'),
    ]

    @api.depends('service_ids')
    def _compute_service_count(self):
        for record in self:
            record.service_count = len(record.service_ids)

    def name_get(self):
        result = []
        for record in self:
            if record.parent_id:
                name = f"{record.parent_id.name} / {record.name}"
            else:
                name = record.name
            result.append((record.id, name))
        return result

    def action_view_services(self):
        """Open services for this category"""
        self.ensure_one()
        return {
            'name': f'Services - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'pro.service',
            'view_mode': 'tree,form',
            'domain': [('category_id', '=', self.id)],
            'context': {'default_category_id': self.id},
        }
