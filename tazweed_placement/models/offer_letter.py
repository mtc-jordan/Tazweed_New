# -*- coding: utf-8 -*-
"""
Offer Letter Generator Module
Automated offer letter generation with e-signature integration
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import base64
import logging

_logger = logging.getLogger(__name__)


class OfferLetter(models.Model):
    """Offer Letter Management"""
    _name = 'offer.letter'
    _description = 'Offer Letter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # Core Fields
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    
    # Candidate & Job
    candidate_id = fields.Many2one(
        'tazweed.candidate',
        string='Candidate',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    job_order_id = fields.Many2one(
        'tazweed.job.order',
        string='Job Order',
        ondelete='set null',
        tracking=True,
    )
    client_id = fields.Many2one(
        'tazweed.client',
        string='Client',
        related='job_order_id.client_id',
        store=True,
    )
    
    # Template
    template_id = fields.Many2one(
        'offer.letter.template',
        string='Offer Template',
        required=True,
    )
    
    # Job Details
    job_title = fields.Char(
        string='Job Title',
        required=True,
    )
    department = fields.Char(
        string='Department',
    )
    reporting_to = fields.Char(
        string='Reporting To',
    )
    work_location = fields.Char(
        string='Work Location',
    )
    employment_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
    ], string='Employment Type', default='full_time', required=True)
    
    # Dates
    offer_date = fields.Date(
        string='Offer Date',
        default=fields.Date.today,
        required=True,
    )
    validity_date = fields.Date(
        string='Valid Until',
        required=True,
    )
    proposed_start_date = fields.Date(
        string='Proposed Start Date',
        required=True,
    )
    
    # Compensation
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    basic_salary = fields.Monetary(
        string='Basic Salary',
        currency_field='currency_id',
        required=True,
    )
    housing_allowance = fields.Monetary(
        string='Housing Allowance',
        currency_field='currency_id',
    )
    transport_allowance = fields.Monetary(
        string='Transport Allowance',
        currency_field='currency_id',
    )
    other_allowances = fields.Monetary(
        string='Other Allowances',
        currency_field='currency_id',
    )
    total_package = fields.Monetary(
        string='Total Package',
        currency_field='currency_id',
        compute='_compute_total_package',
        store=True,
    )
    salary_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('annual', 'Annual'),
    ], string='Salary Frequency', default='monthly')
    
    # Benefits
    probation_period = fields.Integer(
        string='Probation Period (months)',
        default=3,
    )
    notice_period = fields.Integer(
        string='Notice Period (days)',
        default=30,
    )
    annual_leave = fields.Integer(
        string='Annual Leave (days)',
        default=30,
    )
    medical_insurance = fields.Boolean(
        string='Medical Insurance',
        default=True,
    )
    visa_sponsorship = fields.Boolean(
        string='Visa Sponsorship',
        default=True,
    )
    air_ticket = fields.Selection([
        ('none', 'None'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
    ], string='Air Ticket', default='annual')
    other_benefits = fields.Text(
        string='Other Benefits',
    )
    
    # Terms & Conditions
    special_conditions = fields.Text(
        string='Special Conditions',
    )
    confidentiality_clause = fields.Boolean(
        string='Confidentiality Clause',
        default=True,
    )
    non_compete_clause = fields.Boolean(
        string='Non-Compete Clause',
        default=False,
    )
    non_compete_duration = fields.Integer(
        string='Non-Compete Duration (months)',
    )
    
    # Generated Document
    offer_document = fields.Binary(
        string='Offer Letter Document',
        attachment=True,
    )
    offer_document_name = fields.Char(
        string='Document Name',
    )
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('sent', 'Sent to Candidate'),
        ('viewed', 'Viewed by Candidate'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('negotiating', 'Negotiating'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
    ], string='Status', default='draft', tracking=True)
    
    # E-Signature
    esignature_request_id = fields.Many2one(
        'esignature.request',
        string='E-Signature Request',
    )
    candidate_signature = fields.Binary(
        string='Candidate Signature',
    )
    candidate_signed_date = fields.Datetime(
        string='Candidate Signed Date',
    )
    company_signature = fields.Binary(
        string='Company Signature',
    )
    company_signed_by = fields.Many2one(
        'res.users',
        string='Signed By (Company)',
    )
    company_signed_date = fields.Datetime(
        string='Company Signed Date',
    )
    
    # Tracking
    sent_date = fields.Datetime(
        string='Sent Date',
    )
    viewed_date = fields.Datetime(
        string='First Viewed Date',
    )
    response_date = fields.Datetime(
        string='Response Date',
    )
    
    # Negotiation
    negotiation_notes = fields.Text(
        string='Negotiation Notes',
    )
    counter_offer_salary = fields.Monetary(
        string='Counter Offer Salary',
        currency_field='currency_id',
    )
    
    # Related Fields
    candidate_name = fields.Char(
        related='candidate_id.name',
        string='Candidate Name',
        store=True,
    )
    candidate_email = fields.Char(
        related='candidate_id.email',
        string='Candidate Email',
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('offer.letter') or _('New')
        return super().create(vals)

    @api.depends('basic_salary', 'housing_allowance', 'transport_allowance', 'other_allowances')
    def _compute_total_package(self):
        for record in self:
            record.total_package = (
                record.basic_salary +
                record.housing_allowance +
                record.transport_allowance +
                record.other_allowances
            )

    @api.onchange('job_order_id')
    def _onchange_job_order(self):
        if self.job_order_id:
            self.job_title = self.job_order_id.job_title
            self.work_location = getattr(self.job_order_id, 'location', '')
            if hasattr(self.job_order_id, 'salary_max'):
                self.basic_salary = self.job_order_id.salary_max or 0

    @api.constrains('validity_date', 'offer_date')
    def _check_validity_date(self):
        for record in self:
            if record.validity_date and record.offer_date:
                if record.validity_date < record.offer_date:
                    raise ValidationError(_('Validity date must be after offer date.'))

    def action_generate_offer(self):
        """Generate the offer letter document"""
        self.ensure_one()
        
        if not self.template_id:
            raise UserError(_('Please select an offer letter template.'))
        
        # Generate document content
        content = self._render_offer_letter()
        
        # Convert to PDF (simplified - in production use proper PDF generation)
        document = base64.b64encode(content.encode('utf-8'))
        
        self.write({
            'offer_document': document,
            'offer_document_name': f"Offer_Letter_{self.candidate_name}_{self.name}.html",
            'state': 'generated',
        })
        
        self.message_post(
            body=_('Offer letter generated.'),
            subject=_('Offer Letter Generated'),
        )
        
        return True

    def _render_offer_letter(self):
        """Render the offer letter content from template"""
        template = self.template_id
        
        # Replace placeholders with actual values
        content = template.content or ''
        
        replacements = {
            '{{candidate_name}}': self.candidate_name or '',
            '{{job_title}}': self.job_title or '',
            '{{department}}': self.department or '',
            '{{reporting_to}}': self.reporting_to or '',
            '{{work_location}}': self.work_location or '',
            '{{offer_date}}': self.offer_date.strftime('%B %d, %Y') if self.offer_date else '',
            '{{validity_date}}': self.validity_date.strftime('%B %d, %Y') if self.validity_date else '',
            '{{start_date}}': self.proposed_start_date.strftime('%B %d, %Y') if self.proposed_start_date else '',
            '{{basic_salary}}': f"{self.currency_id.symbol} {self.basic_salary:,.2f}",
            '{{housing_allowance}}': f"{self.currency_id.symbol} {self.housing_allowance:,.2f}",
            '{{transport_allowance}}': f"{self.currency_id.symbol} {self.transport_allowance:,.2f}",
            '{{other_allowances}}': f"{self.currency_id.symbol} {self.other_allowances:,.2f}",
            '{{total_package}}': f"{self.currency_id.symbol} {self.total_package:,.2f}",
            '{{probation_period}}': str(self.probation_period),
            '{{notice_period}}': str(self.notice_period),
            '{{annual_leave}}': str(self.annual_leave),
            '{{company_name}}': self.env.company.name or '',
            '{{reference}}': self.name or '',
        }
        
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        
        return content

    def action_send_offer(self):
        """Send offer letter to candidate"""
        self.ensure_one()
        
        if self.state not in ['generated', 'negotiating']:
            raise UserError(_('Please generate the offer letter first.'))
        
        # Send email with offer letter
        template = self.env.ref('tazweed_placement.email_template_offer_letter', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        
        self.write({
            'state': 'sent',
            'sent_date': fields.Datetime.now(),
        })
        
        self.message_post(
            body=_('Offer letter sent to %s.') % self.candidate_email,
            subject=_('Offer Letter Sent'),
        )
        
        return True

    def action_request_esignature(self):
        """Create e-signature request for the offer letter"""
        self.ensure_one()
        
        if not self.offer_document:
            raise UserError(_('Please generate the offer letter first.'))
        
        # Create e-signature request
        esign_request = self.env['esignature.request'].create({
            'name': f"Offer Letter - {self.candidate_name}",
            'document': self.offer_document,
            'document_name': self.offer_document_name,
            'signer_name': self.candidate_name,
            'signer_email': self.candidate_email,
            'expiry_date': self.validity_date,
        })
        
        self.esignature_request_id = esign_request
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('E-Signature Request'),
            'res_model': 'esignature.request',
            'res_id': esign_request.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_accept(self):
        """Mark offer as accepted"""
        self.write({
            'state': 'accepted',
            'response_date': fields.Datetime.now(),
        })
        
        # Create placement if job order exists
        if self.job_order_id:
            self._create_placement()
        
        self.message_post(
            body=_('Offer accepted by candidate.'),
            subject=_('Offer Accepted'),
        )
        
        return True

    def action_decline(self):
        """Mark offer as declined"""
        self.write({
            'state': 'declined',
            'response_date': fields.Datetime.now(),
        })
        
        self.message_post(
            body=_('Offer declined by candidate.'),
            subject=_('Offer Declined'),
        )
        
        return True

    def action_negotiate(self):
        """Open negotiation wizard"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Negotiation'),
            'res_model': 'offer.letter.negotiation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_offer_id': self.id,
            },
        }

    def action_withdraw(self):
        """Withdraw the offer"""
        self.state = 'withdrawn'
        self.message_post(
            body=_('Offer withdrawn.'),
            subject=_('Offer Withdrawn'),
        )
        return True

    def _create_placement(self):
        """Create a placement record when offer is accepted"""
        placement = self.env['tazweed.placement'].create({
            'candidate_id': self.candidate_id.id,
            'job_order_id': self.job_order_id.id,
            'client_id': self.client_id.id,
            'job_title': self.job_title,
            'date_start': self.proposed_start_date,
            'salary': self.basic_salary,
        })
        
        self.message_post(
            body=_('Placement %s created.') % placement.name,
            subject=_('Placement Created'),
        )
        
        return placement

    @api.model
    def _cron_check_expired_offers(self):
        """Check and mark expired offers"""
        today = fields.Date.today()
        expired_offers = self.search([
            ('state', 'in', ['generated', 'sent', 'viewed', 'negotiating']),
            ('validity_date', '<', today),
        ])
        
        for offer in expired_offers:
            offer.state = 'expired'
            offer.message_post(
                body=_('Offer has expired.'),
                subject=_('Offer Expired'),
            )


class OfferLetterTemplate(models.Model):
    """Offer Letter Templates"""
    _name = 'offer.letter.template'
    _description = 'Offer Letter Template'
    _order = 'name'

    name = fields.Char(
        string='Template Name',
        required=True,
    )
    description = fields.Text(
        string='Description',
    )
    employment_type = fields.Selection([
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('temporary', 'Temporary'),
        ('all', 'All Types'),
    ], string='Employment Type', default='all')
    
    content = fields.Html(
        string='Template Content',
        help='Use placeholders like {{candidate_name}}, {{job_title}}, {{basic_salary}}, etc.',
    )
    
    # Default Values
    default_probation = fields.Integer(
        string='Default Probation (months)',
        default=3,
    )
    default_notice = fields.Integer(
        string='Default Notice Period (days)',
        default=30,
    )
    default_leave = fields.Integer(
        string='Default Annual Leave (days)',
        default=30,
    )
    
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
