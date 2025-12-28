# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta


class ProServiceRequest(models.Model):
    """Service requests from HR or customers"""
    _name = 'pro.service.request'
    _description = 'PRO Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Request Number',
        readonly=True,
        copy=False,
        default=lambda self: _('New')
    )
    
    # Request Type
    request_type = fields.Selection([
        ('internal', 'Internal (Employee)'),
        ('external', 'External (Customer)'),
    ], string='Request Type', required=True, default='internal', tracking=True)
    
    # Beneficiary
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        tracking=True
    )
    customer_id = fields.Many2one(
        'pro.customer',
        string='Customer',
        tracking=True
    )
    beneficiary_name = fields.Char(
        string='Beneficiary Name',
        compute='_compute_beneficiary_name',
        store=True
    )
    
    # Service
    service_id = fields.Many2one(
        'pro.service',
        string='Service',
        required=True,
        tracking=True
    )
    category_id = fields.Many2one(
        related='service_id.category_id',
        string='Category',
        store=True
    )
    service_type = fields.Selection(
        related='service_id.service_type',
        string='Service Type',
        store=True
    )
    
    # Requester
    requester_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        tracking=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        tracking=True
    )
    
    # Dates
    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.today,
        required=True
    )
    expected_date = fields.Date(
        string='Expected Completion',
        compute='_compute_expected_date',
        store=True
    )
    completion_date = fields.Date(string='Actual Completion', tracking=True)
    
    # Priority & Urgency
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='0', tracking=True)
    is_urgent = fields.Boolean(string='Urgent Processing', tracking=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('documents_pending', 'Documents Pending'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    # Assignment
    assigned_to = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True,
        domain=[('groups_id', 'in', [
            # Will reference PRO Officer group
        ])]
    )
    
    # Documents
    document_ids = fields.One2many(
        'pro.request.document',
        'request_id',
        string='Documents'
    )
    documents_complete = fields.Boolean(
        string='Documents Complete',
        compute='_compute_documents_complete',
        store=True
    )
    missing_documents = fields.Text(
        string='Missing Documents',
        compute='_compute_documents_complete'
    )
    
    # Tasks
    task_ids = fields.One2many(
        'pro.task',
        'request_id',
        string='Tasks'
    )
    task_count = fields.Integer(
        string='Task Count',
        compute='_compute_task_count'
    )
    current_step_id = fields.Many2one(
        'pro.service.step',
        string='Current Step'
    )
    
    # Billing
    billing_ids = fields.One2many(
        'pro.billing',
        'request_id',
        string='Billing'
    )
    total_fees = fields.Float(
        string='Total Fees',
        compute='_compute_fees',
        store=True
    )
    
    # Notes
    description = fields.Text(string='Description/Notes')
    internal_notes = fields.Text(string='Internal Notes')
    hold_reason = fields.Text(string='Hold Reason')
    cancellation_reason = fields.Text(string='Cancellation Reason')
    
    # Tracking
    sla_status = fields.Selection([
        ('on_track', 'On Track'),
        ('at_risk', 'At Risk'),
        ('overdue', 'Overdue'),
    ], string='SLA Status', compute='_compute_sla_status', store=True)
    days_remaining = fields.Integer(
        string='Days Remaining',
        compute='_compute_sla_status'
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pro.service.request'
                ) or _('New')
        records = super().create(vals_list)
        for record in records:
            record._auto_attach_documents()
        return records

    @api.depends('employee_id', 'customer_id', 'request_type')
    def _compute_beneficiary_name(self):
        for record in self:
            if record.request_type == 'internal' and record.employee_id:
                record.beneficiary_name = record.employee_id.name
            elif record.request_type == 'external' and record.customer_id:
                record.beneficiary_name = record.customer_id.name
            else:
                record.beneficiary_name = ''

    @api.depends('service_id', 'is_urgent', 'request_date')
    def _compute_expected_date(self):
        for record in self:
            if record.service_id and record.request_date:
                days = record.service_id.urgent_days if record.is_urgent else record.service_id.processing_days
                record.expected_date = record.request_date + timedelta(days=days)
            else:
                record.expected_date = False

    @api.depends('service_id', 'is_urgent')
    def _compute_fees(self):
        for record in self:
            if record.service_id:
                total = record.service_id.total_fee
                if record.is_urgent and record.service_id.urgent_available:
                    total += record.service_id.urgent_fee
                record.total_fees = total
            else:
                record.total_fees = 0

    @api.depends('document_ids', 'service_id')
    def _compute_documents_complete(self):
        for record in self:
            if not record.service_id:
                record.documents_complete = False
                record.missing_documents = ''
                continue
            
            required_docs = record.service_id.required_document_ids
            attached_doc_types = record.document_ids.mapped('document_type_id')
            missing = required_docs - attached_doc_types
            
            record.documents_complete = len(missing) == 0
            record.missing_documents = ', '.join(missing.mapped('name')) if missing else ''

    @api.depends('task_ids')
    def _compute_task_count(self):
        for record in self:
            record.task_count = len(record.task_ids)

    @api.depends('expected_date', 'state')
    def _compute_sla_status(self):
        today = fields.Date.today()
        for record in self:
            if record.state in ('completed', 'cancelled'):
                record.sla_status = 'on_track'
                record.days_remaining = 0
            elif not record.expected_date:
                record.sla_status = 'on_track'
                record.days_remaining = 0
            else:
                days = (record.expected_date - today).days
                record.days_remaining = days
                if days < 0:
                    record.sla_status = 'overdue'
                elif days <= 2:
                    record.sla_status = 'at_risk'
                else:
                    record.sla_status = 'on_track'

    @api.onchange('request_type')
    def _onchange_request_type(self):
        if self.request_type == 'internal':
            self.customer_id = False
        else:
            self.employee_id = False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id

    @api.onchange('service_id')
    def _onchange_service_id(self):
        if self.service_id:
            # Check if urgent is available
            if not self.service_id.urgent_available:
                self.is_urgent = False

    def _auto_attach_documents(self):
        """Automatically attach documents from employee records"""
        self.ensure_one()
        if self.request_type != 'internal' or not self.employee_id:
            return
        
        # Get required documents for the service
        required_docs = self.service_id.required_document_ids
        
        # Search for employee documents
        EmployeeDoc = self.env.get('tazweed.employee.document')
        if not EmployeeDoc:
            return
        
        for doc_type in required_docs:
            if not doc_type.employee_document_type_id:
                continue
            
            # Find matching employee document
            emp_doc = EmployeeDoc.search([
                ('employee_id', '=', self.employee_id.id),
                ('document_type_id', '=', doc_type.employee_document_type_id.id),
                ('status', '=', 'valid'),
            ], limit=1, order='expiry_date desc')
            
            if emp_doc and emp_doc.document_file:
                # Create request document
                self.env['pro.request.document'].create({
                    'request_id': self.id,
                    'document_type_id': doc_type.id,
                    'name': emp_doc.document_name or doc_type.name,
                    'file': emp_doc.document_file,
                    'file_name': emp_doc.document_filename,
                    'document_number': emp_doc.document_number,
                    'issue_date': emp_doc.issue_date,
                    'expiry_date': emp_doc.expiry_date,
                    'source': 'auto',
                    'source_document_id': emp_doc.id,
                })

    def action_submit(self):
        """Submit the request for processing"""
        for record in self:
            if record.state != 'draft':
                raise UserError(_('Only draft requests can be submitted.'))
            
            if not record.documents_complete:
                record.state = 'documents_pending'
            else:
                record.state = 'submitted'
            
            # Create tasks from service steps
            record._create_tasks_from_steps()
        return True

    def action_start_processing(self):
        """Start processing the request"""
        for record in self:
            if record.state not in ('submitted', 'documents_pending'):
                raise UserError(_('Request must be submitted first.'))
            
            if not record.documents_complete:
                raise UserError(_('All required documents must be attached.'))
            
            record.state = 'in_progress'
            
            # Set first step as current
            first_task = record.task_ids.filtered(
                lambda t: t.state == 'pending'
            ).sorted('sequence')[:1]
            if first_task:
                first_task.action_start()
                record.current_step_id = first_task.step_id
        return True

    def action_hold(self):
        """Put request on hold"""
        for record in self:
            record.state = 'on_hold'
        return True

    def action_resume(self):
        """Resume request from hold"""
        for record in self:
            if record.state != 'on_hold':
                raise UserError(_('Only held requests can be resumed.'))
            record.state = 'in_progress'
        return True

    def action_complete(self):
        """Mark request as completed"""
        for record in self:
            record.state = 'completed'
            record.completion_date = fields.Date.today()
            
            # Create billing if not exists
            if not record.billing_ids:
                record._create_billing()
        return True

    def action_cancel(self):
        """Cancel the request"""
        for record in self:
            record.state = 'cancelled'
            # Cancel all pending tasks
            record.task_ids.filtered(
                lambda t: t.state in ('pending', 'in_progress')
            ).write({'state': 'cancelled'})
        return True

    def action_reset_to_draft(self):
        """Reset cancelled request to draft"""
        for record in self:
            if record.state != 'cancelled':
                raise UserError(_('Only cancelled requests can be reset.'))
            record.state = 'draft'
            record.cancellation_reason = False
        return True

    def _create_tasks_from_steps(self):
        """Create tasks from service steps"""
        self.ensure_one()
        Task = self.env['pro.task']
        
        for step in self.service_id.step_ids.sorted('sequence'):
            Task.create({
                'request_id': self.id,
                'step_id': step.id,
                'name': step.name,
                'sequence': step.sequence,
                'assigned_to': self.assigned_to.id if self.assigned_to else False,
            })

    def _create_billing(self):
        """Create billing record for the request"""
        self.ensure_one()
        self.env['pro.billing'].create({
            'request_id': self.id,
            'customer_id': self.customer_id.id if self.customer_id else False,
            'employee_id': self.employee_id.id if self.employee_id else False,
            'government_fee': self.service_id.government_fee,
            'service_fee': self.service_id.service_fee,
            'urgent_fee': self.service_id.urgent_fee if self.is_urgent else 0,
        })

    def action_view_tasks(self):
        """View tasks for this request"""
        self.ensure_one()
        return {
            'name': _('Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.task',
            'view_mode': 'list,form,kanban',
            'domain': [('request_id', '=', self.id)],
            'context': {'default_request_id': self.id},
        }

    def action_attach_documents(self):
        """Open wizard to attach documents"""
        self.ensure_one()
        return {
            'name': _('Attach Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.request.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }


class ProRequestDocument(models.Model):
    """Documents attached to service requests"""
    _name = 'pro.request.document'
    _description = 'PRO Request Document'
    _order = 'document_type_id'

    name = fields.Char(string='Document Name', required=True)
    request_id = fields.Many2one(
        'pro.service.request',
        string='Service Request',
        required=True,
        ondelete='cascade'
    )
    document_type_id = fields.Many2one(
        'pro.document.type',
        string='Document Type',
        required=True
    )
    
    # File
    file = fields.Binary(string='File', required=True, attachment=True)
    file_name = fields.Char(string='File Name')
    
    # Details
    document_number = fields.Char(string='Document Number')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    
    # Source
    source = fields.Selection([
        ('manual', 'Manual Upload'),
        ('auto', 'Auto-Attached'),
    ], string='Source', default='manual')
    source_document_id = fields.Integer(string='Source Document ID')
    
    # Verification
    verified = fields.Boolean(string='Verified')
    verified_by = fields.Many2one('res.users', string='Verified By')
    verified_date = fields.Datetime(string='Verified Date')
    
    notes = fields.Text(string='Notes')

    def action_verify(self):
        """Mark document as verified"""
        for record in self:
            record.verified = True
            record.verified_by = self.env.user
            record.verified_date = fields.Datetime.now()
        return True
