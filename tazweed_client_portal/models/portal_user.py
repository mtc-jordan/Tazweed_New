# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError
import secrets
import hashlib
from datetime import datetime, timedelta


class ClientPortalUser(models.Model):
    """Portal User with Role-Based Access Control"""
    _name = 'client.portal.user'
    _description = 'Client Portal User'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(string='Full Name', required=True, tracking=True)
    email = fields.Char(string='Email', required=True, tracking=True)
    phone = fields.Char(string='Phone')
    job_title = fields.Char(string='Job Title')
    department = fields.Char(string='Department')
    
    # Client Relationship
    client_id = fields.Many2one(
        'tazweed.client', string='Client', 
        required=True, ondelete='cascade', tracking=True
    )
    
    # Odoo User Link
    user_id = fields.Many2one('res.users', string='Odoo User', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Contact', readonly=True)
    
    # Access Control
    role = fields.Selection([
        ('admin', 'Administrator'),
        ('manager', 'Manager'),
        ('viewer', 'Viewer'),
        ('approver', 'Approver Only'),
    ], string='Role', default='viewer', required=True, tracking=True)
    
    # Granular Permissions
    can_view_job_orders = fields.Boolean(string='View Job Orders', default=True)
    can_create_job_orders = fields.Boolean(string='Create Job Orders', default=False)
    can_edit_job_orders = fields.Boolean(string='Edit Job Orders', default=False)
    can_view_candidates = fields.Boolean(string='View Candidates', default=True)
    can_approve_candidates = fields.Boolean(string='Approve Candidates', default=False)
    can_view_placements = fields.Boolean(string='View Placements', default=True)
    can_view_invoices = fields.Boolean(string='View Invoices', default=True)
    can_pay_invoices = fields.Boolean(string='Pay Invoices', default=False)
    can_view_documents = fields.Boolean(string='View Documents', default=True)
    can_upload_documents = fields.Boolean(string='Upload Documents', default=False)
    can_download_documents = fields.Boolean(string='Download Documents', default=True)
    can_send_messages = fields.Boolean(string='Send Messages', default=True)
    can_view_analytics = fields.Boolean(string='View Analytics', default=True)
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending Activation'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('deactivated', 'Deactivated'),
    ], string='Status', default='pending', tracking=True)
    
    # Authentication
    activation_token = fields.Char(string='Activation Token', readonly=True)
    token_expiry = fields.Datetime(string='Token Expiry', readonly=True)
    last_login = fields.Datetime(string='Last Login', readonly=True)
    login_count = fields.Integer(string='Login Count', default=0, readonly=True)
    
    # Notification Preferences
    notify_email = fields.Boolean(string='Email Notifications', default=True)
    notify_sms = fields.Boolean(string='SMS Notifications', default=False)
    notify_new_candidates = fields.Boolean(string='New Candidate Alerts', default=True)
    notify_placement_updates = fields.Boolean(string='Placement Updates', default=True)
    notify_invoice_alerts = fields.Boolean(string='Invoice Alerts', default=True)
    
    # Display
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    avatar = fields.Binary(string='Avatar')
    
    _sql_constraints = [
        ('email_client_unique', 'unique(email, client_id)', 
         'A user with this email already exists for this client!')
    ]
    
    @api.depends('name', 'email', 'role')
    def _compute_display_name(self):
        for user in self:
            role_label = dict(self._fields['role'].selection).get(user.role, '')
            user.display_name = f"{user.name} ({role_label})"
    
    @api.onchange('role')
    def _onchange_role(self):
        """Set default permissions based on role"""
        if self.role == 'admin':
            self.can_view_job_orders = True
            self.can_create_job_orders = True
            self.can_edit_job_orders = True
            self.can_view_candidates = True
            self.can_approve_candidates = True
            self.can_view_placements = True
            self.can_view_invoices = True
            self.can_pay_invoices = True
            self.can_view_documents = True
            self.can_upload_documents = True
            self.can_download_documents = True
            self.can_send_messages = True
            self.can_view_analytics = True
        elif self.role == 'manager':
            self.can_view_job_orders = True
            self.can_create_job_orders = True
            self.can_edit_job_orders = True
            self.can_view_candidates = True
            self.can_approve_candidates = True
            self.can_view_placements = True
            self.can_view_invoices = True
            self.can_pay_invoices = False
            self.can_view_documents = True
            self.can_upload_documents = True
            self.can_download_documents = True
            self.can_send_messages = True
            self.can_view_analytics = True
        elif self.role == 'approver':
            self.can_view_job_orders = True
            self.can_create_job_orders = False
            self.can_edit_job_orders = False
            self.can_view_candidates = True
            self.can_approve_candidates = True
            self.can_view_placements = True
            self.can_view_invoices = False
            self.can_pay_invoices = False
            self.can_view_documents = True
            self.can_upload_documents = False
            self.can_download_documents = True
            self.can_send_messages = True
            self.can_view_analytics = False
        else:  # viewer
            self.can_view_job_orders = True
            self.can_create_job_orders = False
            self.can_edit_job_orders = False
            self.can_view_candidates = True
            self.can_approve_candidates = False
            self.can_view_placements = True
            self.can_view_invoices = True
            self.can_pay_invoices = False
            self.can_view_documents = True
            self.can_upload_documents = False
            self.can_download_documents = True
            self.can_send_messages = True
            self.can_view_analytics = True
    
    def action_send_invitation(self):
        """Send portal invitation to user"""
        self.ensure_one()
        
        # Generate activation token
        token = secrets.token_urlsafe(32)
        self.write({
            'activation_token': token,
            'token_expiry': datetime.now() + timedelta(days=7),
            'state': 'pending',
        })
        
        # Create partner if not exists
        if not self.partner_id:
            partner = self.env['res.partner'].create({
                'name': self.name,
                'email': self.email,
                'phone': self.phone,
                'parent_id': self.client_id.partner_id.id if self.client_id.partner_id else False,
                'company_type': 'person',
            })
            self.partner_id = partner.id
        
        # Send invitation email
        template = self.env.ref('tazweed_client_portal.email_template_portal_invitation', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invitation Sent'),
                'message': _('Portal invitation has been sent to %s') % self.email,
                'type': 'success',
            }
        }
    
    def action_activate(self):
        """Activate portal user"""
        self.ensure_one()
        
        # Create Odoo portal user if not exists
        if not self.user_id:
            user = self.env['res.users'].sudo().create({
                'name': self.name,
                'login': self.email,
                'email': self.email,
                'partner_id': self.partner_id.id,
                'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
            })
            self.user_id = user.id
        
        self.state = 'active'
        return True
    
    def action_suspend(self):
        """Suspend portal user"""
        self.ensure_one()
        self.state = 'suspended'
        if self.user_id:
            self.user_id.sudo().active = False
        return True
    
    def action_reactivate(self):
        """Reactivate suspended user"""
        self.ensure_one()
        self.state = 'active'
        if self.user_id:
            self.user_id.sudo().active = True
        return True
    
    def action_deactivate(self):
        """Permanently deactivate user"""
        self.ensure_one()
        self.state = 'deactivated'
        if self.user_id:
            self.user_id.sudo().active = False
        return True
    
    def record_login(self):
        """Record user login"""
        self.ensure_one()
        self.write({
            'last_login': fields.Datetime.now(),
            'login_count': self.login_count + 1,
        })
    
    def check_permission(self, permission):
        """Check if user has a specific permission"""
        self.ensure_one()
        if self.state != 'active':
            return False
        return getattr(self, f'can_{permission}', False)
