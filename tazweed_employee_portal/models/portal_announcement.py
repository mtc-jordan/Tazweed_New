# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TazweedPortalAnnouncement(models.Model):
    """Portal Announcements"""
    _name = 'tazweed.portal.announcement'
    _description = 'Portal Announcement'
    _order = 'publish_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Title',
        required=True,
        tracking=True,
    )
    content = fields.Html(
        string='Content',
        required=True,
    )
    summary = fields.Text(
        string='Summary',
        help='Short summary for preview',
    )
    
    announcement_type = fields.Selection([
        ('general', 'General'),
        ('policy', 'Policy Update'),
        ('event', 'Event'),
        ('holiday', 'Holiday'),
        ('urgent', 'Urgent'),
        ('hr', 'HR Update'),
        ('payroll', 'Payroll'),
    ], string='Type', default='general', required=True)
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    # Targeting
    target_type = fields.Selection([
        ('all', 'All Employees'),
        ('department', 'Specific Departments'),
        ('employees', 'Specific Employees'),
    ], string='Target', default='all', required=True)
    
    target_department_ids = fields.Many2many(
        'hr.department',
        string='Target Departments',
    )
    target_employees = fields.Many2many(
        'hr.employee',
        'announcement_employee_target_rel',
        'announcement_id',
        'employee_id',
        string='Target Employees',
    )
    
    # Tracking
    read_by_employees = fields.Many2many(
        'hr.employee',
        'announcement_employee_read_rel',
        'announcement_id',
        'employee_id',
        string='Read By',
    )
    read_count = fields.Integer(
        string='Read Count',
        compute='_compute_read_count',
    )
    
    # Dates
    publish_date = fields.Datetime(
        string='Publish Date',
        default=fields.Datetime.now,
    )
    expiry_date = fields.Date(
        string='Expiry Date',
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('expired', 'Expired'),
        ('archived', 'Archived'),
    ], string='Status', default='draft', tracking=True)
    
    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
    )
    
    # Author
    author_id = fields.Many2one(
        'res.users',
        string='Author',
        default=lambda self: self.env.user,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('read_by_employees')
    def _compute_read_count(self):
        """Compute read count"""
        for announcement in self:
            announcement.read_count = len(announcement.read_by_employees)

    @api.onchange('target_type')
    def _onchange_target_type(self):
        """Clear targets when type changes"""
        if self.target_type == 'all':
            self.target_department_ids = False
            self.target_employees = False
        elif self.target_type == 'department':
            self.target_employees = False
        elif self.target_type == 'employees':
            self.target_department_ids = False

    @api.onchange('target_department_ids')
    def _onchange_target_departments(self):
        """Set target employees from departments"""
        if self.target_type == 'department' and self.target_department_ids:
            employees = self.env['hr.employee'].search([
                ('department_id', 'in', self.target_department_ids.ids),
            ])
            self.target_employees = employees

    def action_publish(self):
        """Publish announcement"""
        self.write({
            'state': 'published',
            'publish_date': fields.Datetime.now(),
        })

    def action_archive(self):
        """Archive announcement"""
        self.write({'state': 'archived'})

    def action_reset_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})

    def mark_as_read(self, employee_id):
        """Mark announcement as read by employee"""
        self.ensure_one()
        if employee_id not in self.read_by_employees.ids:
            self.write({
                'read_by_employees': [(4, employee_id)],
            })

    @api.model
    def check_expired_announcements(self):
        """Cron job to expire old announcements"""
        expired = self.search([
            ('state', '=', 'published'),
            ('expiry_date', '<', fields.Date.today()),
        ])
        expired.write({'state': 'expired'})

    @api.model
    def get_employee_announcements(self, employee_id, limit=10):
        """Get announcements for an employee"""
        employee = self.env['hr.employee'].browse(employee_id)
        
        domain = [
            ('state', '=', 'published'),
            '|',
            ('target_type', '=', 'all'),
            '|',
            ('target_employees', 'in', employee_id),
            ('target_department_ids', 'in', employee.department_id.id if employee.department_id else []),
        ]
        
        return self.search(domain, limit=limit, order='publish_date desc')
