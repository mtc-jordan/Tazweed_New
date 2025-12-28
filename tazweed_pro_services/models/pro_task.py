# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class ProTask(models.Model):
    """Individual tasks within a service request - Enhanced with fees and receipts"""
    _name = 'pro.task'
    _description = 'PRO Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_id, sequence'

    name = fields.Char(string='Task Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    # Parent Request
    request_id = fields.Many2one(
        'pro.service.request',
        string='Service Request',
        required=True,
        ondelete='cascade'
    )
    
    # Service Step Reference
    step_id = fields.Many2one(
        'pro.service.step',
        string='Service Step'
    )
    step_type = fields.Selection(
        related='step_id.step_type',
        string='Step Type'
    )
    
    # Related Info
    service_id = fields.Many2one(
        related='request_id.service_id',
        string='Service',
        store=True
    )
    employee_id = fields.Many2one(
        related='request_id.employee_id',
        string='Employee',
        store=True
    )
    customer_id = fields.Many2one(
        related='request_id.customer_id',
        string='Customer',
        store=True
    )
    beneficiary_name = fields.Char(
        related='request_id.beneficiary_name',
        string='Beneficiary'
    )
    
    # Assignment
    assigned_to = fields.Many2one(
        'res.users',
        string='Assigned To',
        tracking=True
    )
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('waiting', 'Waiting'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='pending', tracking=True)
    
    # Priority
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1')
    
    # Dates
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    due_date = fields.Date(string='Due Date')
    
    # Time Tracking
    estimated_hours = fields.Float(
        string='Estimated Hours',
        related='step_id.estimated_duration'
    )
    actual_hours = fields.Float(string='Actual Hours')
    
    # Location
    location = fields.Selection(
        related='step_id.location',
        string='Location'
    )
    government_authority_id = fields.Many2one(
        related='step_id.government_authority_id',
        string='Government Authority'
    )
    
    # Documents
    required_document_ids = fields.Many2many(
        related='step_id.required_document_ids',
        string='Required Documents'
    )
    output_document_ids = fields.One2many(
        'pro.task.document',
        'task_id',
        string='Output Documents'
    )
    
    # ========== ENHANCED FEE MANAGEMENT ==========
    
    # Step has fees?
    has_fees = fields.Boolean(
        string='Has Fees',
        default=False,
        help='Check if this step requires payment'
    )
    
    # Fee Details
    fee_type = fields.Selection([
        ('government', 'Government Fee'),
        ('typing_center', 'Typing Center'),
        ('medical', 'Medical Center'),
        ('translation', 'Translation'),
        ('attestation', 'Attestation'),
        ('third_party', 'Third Party'),
        ('other', 'Other'),
    ], string='Fee Type', default='government')
    
    fee_description = fields.Char(string='Fee Description')
    
    # Expected vs Actual Fees
    expected_fee = fields.Float(
        string='Expected Fee',
        digits=(16, 2),
        help='Expected fee amount based on service configuration'
    )
    actual_fee_paid = fields.Float(
        string='Actual Fee Paid',
        digits=(16, 2),
        tracking=True,
        help='Actual amount paid'
    )
    fee_currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    # Fee paid by
    fee_paid_by = fields.Selection([
        ('company', 'Company'),
        ('customer', 'Customer'),
        ('employee', 'Employee'),
    ], string='Fee Paid By', default='company')
    
    # Invoice Options
    include_in_invoice = fields.Boolean(
        string='Include in Customer Invoice',
        default=True,
        help='Check to include this fee in the customer invoice'
    )
    invoice_line_id = fields.Many2one(
        'pro.billing.line',
        string='Invoice Line',
        readonly=True
    )
    is_invoiced = fields.Boolean(
        string='Invoiced',
        compute='_compute_is_invoiced',
        store=True
    )
    
    # Receipt/Proof of Payment
    has_receipt = fields.Boolean(
        string='Has Receipt',
        compute='_compute_has_receipt',
        store=True
    )
    receipt_ids = fields.One2many(
        'pro.task.receipt',
        'task_id',
        string='Receipts'
    )
    receipt_count = fields.Integer(
        string='Receipt Count',
        compute='_compute_receipt_count'
    )
    
    # Payment Details
    payment_date = fields.Date(string='Payment Date')
    payment_reference = fields.Char(string='Payment Reference')
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
        ('company_account', 'Company Account'),
    ], string='Payment Method')
    
    # Reference Numbers
    reference_number = fields.Char(string='Reference Number')
    receipt_number = fields.Char(string='Receipt Number')
    transaction_id = fields.Char(string='Transaction ID')
    
    # Notes
    instructions = fields.Html(
        related='step_id.instructions',
        string='Instructions'
    )
    notes = fields.Text(string='Notes')
    completion_notes = fields.Text(string='Completion Notes')
    
    # Attachments
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'pro_task_attachment_rel',
        'task_id',
        'attachment_id',
        string='Attachments'
    )
    
    # Employee Cost Integration
    cost_added_to_employee = fields.Boolean(
        string='Cost Added to Employee',
        default=False,
        help='Check if this cost has been added to employee cost center'
    )
    employee_cost_line_id = fields.Many2one(
        'tazweed.employee.cost.center.line',
        string='Employee Cost Line',
        readonly=True
    )

    @api.depends('invoice_line_id')
    def _compute_is_invoiced(self):
        for record in self:
            record.is_invoiced = bool(record.invoice_line_id)

    @api.depends('receipt_ids')
    def _compute_has_receipt(self):
        for record in self:
            record.has_receipt = bool(record.receipt_ids)

    @api.depends('receipt_ids')
    def _compute_receipt_count(self):
        for record in self:
            record.receipt_count = len(record.receipt_ids)

    @api.onchange('step_id')
    def _onchange_step_id(self):
        """Auto-fill fee information from step configuration"""
        if self.step_id:
            self.expected_fee = self.step_id.government_fee + self.step_id.service_fee
            if self.step_id.government_fee > 0 or self.step_id.service_fee > 0:
                self.has_fees = True
            self.fee_description = self.step_id.name

    def action_start(self):
        """Start working on the task"""
        for record in self:
            if record.state != 'pending':
                raise UserError(_('Only pending tasks can be started.'))
            record.state = 'in_progress'
            record.start_date = fields.Datetime.now()
            
            # Update request current step
            record.request_id.current_step_id = record.step_id
        return True

    def action_wait(self):
        """Put task in waiting state (e.g., waiting for government)"""
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_('Only in-progress tasks can be put on wait.'))
            record.state = 'waiting'
        return True

    def action_resume(self):
        """Resume task from waiting"""
        for record in self:
            if record.state != 'waiting':
                raise UserError(_('Only waiting tasks can be resumed.'))
            record.state = 'in_progress'
        return True

    def action_complete(self):
        """Complete the task and handle fee processing"""
        for record in self:
            if record.state not in ('in_progress', 'waiting'):
                raise UserError(_('Only in-progress or waiting tasks can be completed.'))
            
            record.state = 'completed'
            record.end_date = fields.Datetime.now()
            
            # Calculate actual hours
            if record.start_date:
                delta = record.end_date - record.start_date
                record.actual_hours = delta.total_seconds() / 3600
            
            # Process fees if applicable
            if record.has_fees and record.actual_fee_paid > 0:
                record._process_task_fees()
            
            # Auto-proceed to next task if configured
            if record.step_id and record.step_id.auto_proceed:
                record._proceed_to_next_task()
            
            # Check if all tasks are completed
            record._check_request_completion()
        return True

    def _process_task_fees(self):
        """Process fees - add to invoice and employee cost"""
        self.ensure_one()
        
        # Add to customer invoice if selected
        if self.include_in_invoice and self.request_id.billing_id:
            self._add_fee_to_invoice()
        
        # Add to employee cost if it's an internal employee service
        if self.employee_id and self.fee_paid_by == 'company':
            self._add_fee_to_employee_cost()
        
        # Add receipts to billing
        if self.receipt_ids and self.request_id.billing_id:
            self._attach_receipts_to_billing()

    def _add_fee_to_invoice(self):
        """Add this task's fee to the billing invoice"""
        self.ensure_one()
        if not self.request_id.billing_id:
            return
        
        BillingLine = self.env['pro.billing.line']
        line = BillingLine.create({
            'billing_id': self.request_id.billing_id.id,
            'description': self.fee_description or self.name,
            'fee_type': self.fee_type if self.fee_type in ('government', 'service', 'urgent', 'additional', 'third_party') else 'additional',
            'authority_name': self.government_authority_id.name if self.government_authority_id else '',
            'reference_number': self.receipt_number or self.reference_number,
            'service_date': self.payment_date or fields.Date.today(),
            'quantity': 1,
            'unit_price': self.actual_fee_paid,
            'amount': self.actual_fee_paid,
        })
        self.invoice_line_id = line

    def _add_fee_to_employee_cost(self):
        """Add this fee to the employee's cost center"""
        self.ensure_one()
        if not self.employee_id:
            return
        
        # Find or create employee cost center
        CostCenter = self.env['tazweed.employee.cost.center']
        cost_center = CostCenter.search([('employee_id', '=', self.employee_id.id)], limit=1)
        
        if not cost_center:
            cost_center = CostCenter.create({
                'employee_id': self.employee_id.id,
            })
        
        # Add cost line
        if hasattr(cost_center, 'pro_cost_ids'):
            ProCostLine = self.env['tazweed.employee.cost.center.pro.line']
            line = ProCostLine.create({
                'cost_center_id': cost_center.id,
                'task_id': self.id,
                'description': f"PRO: {self.fee_description or self.name}",
                'amount': self.actual_fee_paid,
                'date': self.payment_date or fields.Date.today(),
                'service_type': self.fee_type,
            })
            self.employee_cost_line_id = line
            self.cost_added_to_employee = True

    def _attach_receipts_to_billing(self):
        """Attach task receipts to the billing record"""
        self.ensure_one()
        if not self.request_id.billing_id:
            return
        
        BillingReceipt = self.env['pro.billing.receipt']
        for receipt in self.receipt_ids:
            BillingReceipt.create({
                'billing_id': self.request_id.billing_id.id,
                'name': receipt.name,
                'receipt_type': receipt.receipt_type,
                'authority_name': receipt.authority_name,
                'reference_number': receipt.reference_number,
                'date': receipt.date,
                'amount': receipt.amount,
                'attachment': receipt.attachment,
                'attachment_filename': receipt.attachment_filename,
                'description': f"From Task: {self.name}",
                'is_reimbursable': self.include_in_invoice,
            })

    def action_cancel(self):
        """Cancel the task"""
        for record in self:
            record.state = 'cancelled'
        return True

    def _proceed_to_next_task(self):
        """Start the next task in sequence"""
        self.ensure_one()
        next_task = self.request_id.task_ids.filtered(
            lambda t: t.sequence > self.sequence and t.state == 'pending'
        ).sorted('sequence')[:1]
        
        if next_task:
            next_task.action_start()

    def _check_request_completion(self):
        """Check if all tasks are completed and update request"""
        self.ensure_one()
        pending_tasks = self.request_id.task_ids.filtered(
            lambda t: t.state in ('pending', 'in_progress', 'waiting')
        )
        
        if not pending_tasks:
            self.request_id.action_complete()

    def action_add_output_document(self):
        """Open wizard to add output document"""
        self.ensure_one()
        return {
            'name': _('Add Output Document'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.task.document',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    def action_add_receipt(self):
        """Open wizard to add receipt"""
        self.ensure_one()
        return {
            'name': _('Add Receipt'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.task.receipt',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.id,
                'default_amount': self.actual_fee_paid,
                'default_receipt_type': self.fee_type,
            },
        }

    def action_view_receipts(self):
        """View all receipts for this task"""
        self.ensure_one()
        return {
            'name': _('Task Receipts'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.task.receipt',
            'view_mode': 'tree,form',
            'domain': [('task_id', '=', self.id)],
            'context': {'default_task_id': self.id},
        }

    def action_mark_fee_paid(self):
        """Quick action to mark fee as paid"""
        self.ensure_one()
        return {
            'name': _('Record Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'pro.task.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_task_id': self.id,
                'default_amount': self.expected_fee,
            },
        }


class ProTaskDocument(models.Model):
    """Documents produced by tasks"""
    _name = 'pro.task.document'
    _description = 'PRO Task Document'

    name = fields.Char(string='Document Name', required=True)
    task_id = fields.Many2one(
        'pro.task',
        string='Task',
        required=True,
        ondelete='cascade'
    )
    document_type_id = fields.Many2one(
        'pro.document.type',
        string='Document Type'
    )
    
    # File
    file = fields.Binary(string='File', attachment=True)
    file_name = fields.Char(string='File Name')
    
    # Details
    document_number = fields.Char(string='Document Number')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    issuing_authority = fields.Char(string='Issuing Authority')
    
    notes = fields.Text(string='Notes')


class ProTaskReceipt(models.Model):
    """Receipts/Proofs of payment for task fees"""
    _name = 'pro.task.receipt'
    _description = 'PRO Task Receipt'
    _order = 'date desc'

    name = fields.Char(string='Receipt Name', required=True)
    task_id = fields.Many2one(
        'pro.task',
        string='Task',
        required=True,
        ondelete='cascade'
    )
    
    # Receipt Type
    receipt_type = fields.Selection([
        ('government', 'Government Receipt'),
        ('typing_center', 'Typing Center Receipt'),
        ('medical', 'Medical Center Receipt'),
        ('translation', 'Translation Receipt'),
        ('attestation', 'Attestation Receipt'),
        ('third_party', 'Third Party Receipt'),
        ('other', 'Other'),
    ], string='Receipt Type', required=True, default='government')
    
    # Details
    authority_name = fields.Char(string='Authority/Provider Name')
    reference_number = fields.Char(string='Receipt/Reference Number')
    date = fields.Date(string='Receipt Date', default=fields.Date.today)
    
    # Amount
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    amount = fields.Float(string='Amount', digits=(16, 2), required=True)
    
    # Attachment
    attachment = fields.Binary(string='Receipt Image/PDF', required=True)
    attachment_filename = fields.Char(string='Filename')
    
    # Description
    description = fields.Text(string='Description')
    
    # Auto-attach to invoice
    attach_to_invoice = fields.Boolean(
        string='Attach to Invoice',
        default=True,
        help='Automatically attach this receipt to the customer invoice'
    )
