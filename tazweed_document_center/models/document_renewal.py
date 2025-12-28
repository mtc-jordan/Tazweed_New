# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentRenewalRequest(models.Model):
    """Document renewal request and workflow management."""
    _name = 'document.renewal.request'
    _description = 'Document Renewal Request'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Request Reference', required=True, copy=False,
                       readonly=True, default=lambda self: _('New'))
    
    document_id = fields.Many2one(
        'tazweed.employee.document',
        string='Document',
        required=True,
        ondelete='cascade'
    )
    
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='document_id.employee_id',
        store=True
    )
    
    document_type_id = fields.Many2one(
        'tazweed.document.type',
        string='Document Type',
        related='document_id.document_type_id',
        store=True
    )
    
    current_expiry_date = fields.Date(
        string='Current Expiry Date',
        related='document_id.expiry_date'
    )
    
    new_expiry_date = fields.Date(string='New Expiry Date')
    new_document_number = fields.Char(string='New Document Number')
    new_issue_date = fields.Date(string='New Issue Date')
    
    # Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted to Authority'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Request details
    requested_by = fields.Many2one('res.users', string='Requested By', 
                                    default=lambda self: self.env.user)
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now)
    
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    
    reason = fields.Text(string='Renewal Reason')
    notes = fields.Text(string='Notes')
    
    # Approval workflow
    approved_by = fields.Many2one('res.users', string='Approved By')
    approval_date = fields.Datetime(string='Approval Date')
    rejection_reason = fields.Text(string='Rejection Reason')
    
    # Processing
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    submission_date = fields.Date(string='Submission Date')
    expected_completion = fields.Date(string='Expected Completion')
    actual_completion = fields.Date(string='Actual Completion')
    
    # Costs
    renewal_cost = fields.Float(string='Renewal Cost')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                   default=lambda self: self.env.company.currency_id)
    
    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'document_renewal_attachment_rel',
        'renewal_id',
        'attachment_id',
        string='Attachments'
    )
    
    # New document after renewal
    renewed_document_id = fields.Many2one(
        'tazweed.employee.document',
        string='Renewed Document'
    )
    
    # Linked alert
    alert_id = fields.Many2one('document.alert', string='Related Alert')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='document_id.company_id',
        store=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('document.renewal.request') or _('New')
        return super().create(vals_list)

    def action_view_document(self):
        """View the related document."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.employee.document',
            'res_id': self.document_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_submit(self):
        """Submit renewal request for approval."""
        self.ensure_one()
        if not self.reason:
            raise UserError(_('Please provide a reason for renewal.'))
        
        self.write({'state': 'pending'})
        self._notify_approvers()
        return True

    def action_approve(self):
        """Approve renewal request."""
        self.ensure_one()
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })
        self._notify_requester('approved')
        return True

    def action_reject(self):
        """Reject renewal request."""
        self.ensure_one()
        return {
            'name': _('Reject Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.renewal.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_renewal_id': self.id},
        }

    def action_start_processing(self):
        """Start processing the renewal."""
        self.ensure_one()
        self.write({
            'state': 'in_progress',
            'assigned_to': self.env.user.id,
        })
        return True

    def action_submit_to_authority(self):
        """Mark as submitted to authority."""
        self.ensure_one()
        self.write({
            'state': 'submitted',
            'submission_date': fields.Date.today(),
        })
        return True

    def action_complete(self):
        """Complete the renewal process."""
        self.ensure_one()
        return {
            'name': _('Complete Renewal'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.renewal.complete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_renewal_id': self.id},
        }

    def action_cancel(self):
        """Cancel renewal request."""
        self.ensure_one()
        self.write({'state': 'cancelled'})
        return True

    def action_reset_draft(self):
        """Reset to draft."""
        self.ensure_one()
        self.write({'state': 'draft'})
        return True

    def _notify_approvers(self):
        """Notify HR managers about pending approval."""
        template = self.env.ref('tazweed_document_center.email_template_renewal_approval', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)

    def _notify_requester(self, action):
        """Notify requester about approval/rejection."""
        if action == 'approved':
            template = self.env.ref('tazweed_document_center.email_template_renewal_approved', raise_if_not_found=False)
        else:
            template = self.env.ref('tazweed_document_center.email_template_renewal_rejected', raise_if_not_found=False)
        
        if template:
            template.send_mail(self.id, force_send=True)


class DocumentRenewalRejectWizard(models.TransientModel):
    """Wizard to reject renewal request."""
    _name = 'document.renewal.reject.wizard'
    _description = 'Reject Renewal Request'

    renewal_id = fields.Many2one('document.renewal.request', string='Request', required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)
    
    def action_reject(self):
        """Reject the request."""
        self.ensure_one()
        self.renewal_id.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason,
        })
        self.renewal_id._notify_requester('rejected')
        return {'type': 'ir.actions.act_window_close'}


class DocumentRenewalCompleteWizard(models.TransientModel):
    """Wizard to complete renewal process."""
    _name = 'document.renewal.complete.wizard'
    _description = 'Complete Renewal Process'

    renewal_id = fields.Many2one('document.renewal.request', string='Request', required=True)
    new_document_number = fields.Char(string='New Document Number', required=True)
    new_issue_date = fields.Date(string='New Issue Date', required=True, default=fields.Date.today)
    new_expiry_date = fields.Date(string='New Expiry Date', required=True)
    attachment = fields.Binary(string='New Document Scan')
    attachment_filename = fields.Char(string='Filename')
    notes = fields.Text(string='Notes')
    
    def action_complete(self):
        """Complete the renewal and create new document."""
        self.ensure_one()
        
        # Create new document record
        old_doc = self.renewal_id.document_id
        new_doc = self.env['tazweed.employee.document'].create({
            'name': old_doc.name,
            'employee_id': old_doc.employee_id.id,
            'document_type_id': old_doc.document_type_id.id,
            'document_number': self.new_document_number,
            'issue_date': self.new_issue_date,
            'expiry_date': self.new_expiry_date,
            'issue_place': old_doc.issue_place,
            'issue_authority': old_doc.issue_authority,
            'attachment': self.attachment,
            'attachment_filename': self.attachment_filename,
            'notes': self.notes,
            'state': 'active',
        })
        
        # Update old document
        old_doc.write({
            'state': 'renewed',
            'renewed_document_id': new_doc.id,
        })
        
        # Update renewal request
        self.renewal_id.write({
            'state': 'completed',
            'actual_completion': fields.Date.today(),
            'renewed_document_id': new_doc.id,
            'new_document_number': self.new_document_number,
            'new_issue_date': self.new_issue_date,
            'new_expiry_date': self.new_expiry_date,
        })
        
        # Resolve related alert
        if self.renewal_id.alert_id:
            self.renewal_id.alert_id.write({
                'state': 'resolved',
                'resolved_by': self.env.user.id,
                'resolved_date': fields.Datetime.now(),
                'resolution_notes': _('Document renewed. New document: %s') % new_doc.name,
            })
        
        return {'type': 'ir.actions.act_window_close'}
