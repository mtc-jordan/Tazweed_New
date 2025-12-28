# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date
from dateutil.relativedelta import relativedelta


class EmployeeGratuity(models.Model):
    """Employee Gratuity (End of Service Benefits) - UAE Labour Law"""
    _name = 'tazweed.employee.gratuity'
    _description = 'Employee Gratuity'
    _order = 'create_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default='/',
        copy=False,
    )
    
    # Employee
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
    )
    
    # Contract
    contract_id = fields.Many2one(
        'hr.contract',
        string='Contract',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    
    # Service Details
    join_date = fields.Date(
        string='Join Date',
        related='employee_id.joining_date',
        store=True,
    )
    termination_date = fields.Date(
        string='Termination Date',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True,
    )
    
    # Service Duration
    service_years = fields.Float(
        string='Service Years',
        compute='_compute_service_duration',
        store=True,
    )
    service_months = fields.Integer(
        string='Service Months',
        compute='_compute_service_duration',
        store=True,
    )
    service_days = fields.Integer(
        string='Service Days',
        compute='_compute_service_duration',
        store=True,
    )
    
    # Termination Type
    termination_type = fields.Selection([
        ('resignation', 'Resignation'),
        ('termination', 'Termination by Employer'),
        ('end_contract', 'End of Contract'),
        ('retirement', 'Retirement'),
        ('death', 'Death'),
        ('disability', 'Disability'),
    ], string='Termination Type', required=True, default='resignation', tracking=True)
    
    # Contract Type
    contract_type = fields.Selection([
        ('limited', 'Limited Contract'),
        ('unlimited', 'Unlimited Contract'),
    ], string='Contract Type', required=True, default='unlimited')
    
    # Salary for Calculation
    basic_salary = fields.Float(
        string='Basic Salary',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    total_salary = fields.Float(
        string='Total Salary (for Gratuity)',
        help='Basic + Housing + Transport (as per UAE Law)',
        compute='_compute_total_salary',
        store=True,
    )
    housing_allowance = fields.Float(
        string='Housing Allowance',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    transport_allowance = fields.Float(
        string='Transport Allowance',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    
    # Gratuity Calculation
    gratuity_type = fields.Selection([
        ('uae_law', 'UAE Labour Law'),
        ('custom', 'Custom Calculation'),
    ], string='Calculation Method', default='uae_law', required=True)
    
    # Calculated Amounts
    first_5_years_amount = fields.Float(
        string='First 5 Years Amount',
        compute='_compute_gratuity',
        store=True,
        help='21 days per year for first 5 years',
    )
    after_5_years_amount = fields.Float(
        string='After 5 Years Amount',
        compute='_compute_gratuity',
        store=True,
        help='30 days per year after 5 years',
    )
    gross_gratuity = fields.Float(
        string='Gross Gratuity',
        compute='_compute_gratuity',
        store=True,
    )
    
    # Deductions
    deduction_percentage = fields.Float(
        string='Deduction Percentage',
        compute='_compute_deduction',
        store=True,
        help='Deduction based on resignation before completing service',
    )
    deduction_amount = fields.Float(
        string='Deduction Amount',
        compute='_compute_deduction',
        store=True,
    )
    
    # Final Amount
    net_gratuity = fields.Float(
        string='Net Gratuity',
        compute='_compute_net_gratuity',
        store=True,
    )
    
    # Other Dues
    leave_balance_days = fields.Float(
        string='Leave Balance (Days)',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    leave_encashment = fields.Float(
        string='Leave Encashment',
        compute='_compute_leave_encashment',
        store=True,
    )
    other_dues = fields.Float(
        string='Other Dues',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    other_deductions = fields.Float(
        string='Other Deductions',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    
    # Total Settlement
    total_settlement = fields.Float(
        string='Total Settlement',
        compute='_compute_total_settlement',
        store=True,
    )
    
    # State
    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    # Approval
    approved_by_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
    )
    approval_date = fields.Date(
        string='Approval Date',
        readonly=True,
    )
    
    # Payment
    payment_date = fields.Date(
        string='Payment Date',
        readonly=True,
    )
    payment_method = fields.Selection([
        ('bank', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
    ], string='Payment Method', default='bank')
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    
    # Notes
    notes = fields.Text(string='Notes')
    calculation_details = fields.Html(
        string='Calculation Details',
        compute='_compute_calculation_details',
    )

    @api.depends('join_date', 'termination_date')
    def _compute_service_duration(self):
        """Compute service duration"""
        for gratuity in self:
            if gratuity.join_date and gratuity.termination_date:
                delta = relativedelta(gratuity.termination_date, gratuity.join_date)
                gratuity.service_years = delta.years + delta.months / 12 + delta.days / 365
                gratuity.service_months = delta.years * 12 + delta.months
                gratuity.service_days = (gratuity.termination_date - gratuity.join_date).days
            else:
                gratuity.service_years = 0
                gratuity.service_months = 0
                gratuity.service_days = 0

    @api.depends('basic_salary', 'housing_allowance', 'transport_allowance')
    def _compute_total_salary(self):
        """Compute total salary for gratuity calculation"""
        for gratuity in self:
            # As per UAE Law, gratuity is calculated on basic salary
            # Some companies include housing and transport
            gratuity.total_salary = gratuity.basic_salary

    @api.depends('total_salary', 'service_years', 'gratuity_type')
    def _compute_gratuity(self):
        """Compute gratuity amount based on UAE Labour Law"""
        for gratuity in self:
            if gratuity.gratuity_type == 'uae_law':
                daily_wage = gratuity.total_salary / 30
                years = gratuity.service_years
                
                # First 5 years: 21 days per year
                first_5 = min(years, 5)
                first_5_amount = first_5 * 21 * daily_wage
                
                # After 5 years: 30 days per year
                after_5 = max(0, years - 5)
                after_5_amount = after_5 * 30 * daily_wage
                
                gratuity.first_5_years_amount = first_5_amount
                gratuity.after_5_years_amount = after_5_amount
                gratuity.gross_gratuity = first_5_amount + after_5_amount
            else:
                gratuity.first_5_years_amount = 0
                gratuity.after_5_years_amount = 0
                gratuity.gross_gratuity = 0

    @api.depends('gross_gratuity', 'service_years', 'termination_type', 'contract_type')
    def _compute_deduction(self):
        """Compute deduction based on resignation before completing service"""
        for gratuity in self:
            deduction_pct = 0.0
            
            # Deduction only applies to resignation in unlimited contracts
            if gratuity.termination_type == 'resignation' and gratuity.contract_type == 'unlimited':
                years = gratuity.service_years
                
                if years < 1:
                    # Less than 1 year: No gratuity
                    deduction_pct = 100.0
                elif years < 3:
                    # 1-3 years: No gratuity (as per UAE law)
                    deduction_pct = 100.0
                elif years < 5:
                    # 3-5 years: 1/3 of gratuity
                    deduction_pct = 66.67
                elif years < 7:
                    # 5-7 years: 2/3 of gratuity
                    deduction_pct = 33.33
                else:
                    # 7+ years: Full gratuity
                    deduction_pct = 0.0
            
            gratuity.deduction_percentage = deduction_pct
            gratuity.deduction_amount = gratuity.gross_gratuity * deduction_pct / 100

    @api.depends('gross_gratuity', 'deduction_amount')
    def _compute_net_gratuity(self):
        """Compute net gratuity after deductions"""
        for gratuity in self:
            gratuity.net_gratuity = gratuity.gross_gratuity - gratuity.deduction_amount

    @api.depends('leave_balance_days', 'basic_salary')
    def _compute_leave_encashment(self):
        """Compute leave encashment amount"""
        for gratuity in self:
            daily_wage = gratuity.basic_salary / 30
            gratuity.leave_encashment = gratuity.leave_balance_days * daily_wage

    @api.depends('net_gratuity', 'leave_encashment', 'other_dues', 'other_deductions')
    def _compute_total_settlement(self):
        """Compute total settlement amount"""
        for gratuity in self:
            gratuity.total_settlement = (
                gratuity.net_gratuity + 
                gratuity.leave_encashment + 
                gratuity.other_dues - 
                gratuity.other_deductions
            )

    def _compute_calculation_details(self):
        """Generate calculation details HTML"""
        for gratuity in self:
            details = f"""
            <div class="gratuity-calculation">
                <h4>Gratuity Calculation Details</h4>
                <table class="table table-sm">
                    <tr><td>Service Duration:</td><td>{gratuity.service_years:.2f} years</td></tr>
                    <tr><td>Daily Wage:</td><td>AED {gratuity.total_salary/30:.2f}</td></tr>
                    <tr><td colspan="2"><strong>First 5 Years (21 days/year)</strong></td></tr>
                    <tr><td>Years:</td><td>{min(gratuity.service_years, 5):.2f}</td></tr>
                    <tr><td>Amount:</td><td>AED {gratuity.first_5_years_amount:.2f}</td></tr>
                    <tr><td colspan="2"><strong>After 5 Years (30 days/year)</strong></td></tr>
                    <tr><td>Years:</td><td>{max(0, gratuity.service_years - 5):.2f}</td></tr>
                    <tr><td>Amount:</td><td>AED {gratuity.after_5_years_amount:.2f}</td></tr>
                    <tr><td><strong>Gross Gratuity:</strong></td><td><strong>AED {gratuity.gross_gratuity:.2f}</strong></td></tr>
                    <tr><td>Deduction ({gratuity.deduction_percentage:.2f}%):</td><td>AED {gratuity.deduction_amount:.2f}</td></tr>
                    <tr><td><strong>Net Gratuity:</strong></td><td><strong>AED {gratuity.net_gratuity:.2f}</strong></td></tr>
                </table>
            </div>
            """
            gratuity.calculation_details = details

    @api.model
    def create(self, vals):
        """Generate sequence on create"""
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('tazweed.employee.gratuity') or '/'
        return super().create(vals)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Populate fields from employee"""
        if self.employee_id:
            contract = self.employee_id.contract_id
            if contract:
                self.contract_id = contract.id
                self.basic_salary = contract.wage
                self.housing_allowance = contract.housing_allowance
                self.transport_allowance = contract.transport_allowance
            
            # Get leave balance
            # This would need integration with leave module
            self.leave_balance_days = 0

    def action_calculate(self):
        """Calculate gratuity"""
        self.write({'state': 'calculated'})

    def action_approve(self):
        """Approve gratuity"""
        self.write({
            'state': 'approved',
            'approved_by_id': self.env.user.id,
            'approval_date': fields.Date.today(),
        })

    def action_pay(self):
        """Mark as paid"""
        self.write({
            'state': 'paid',
            'payment_date': fields.Date.today(),
        })

    def action_cancel(self):
        """Cancel gratuity"""
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Reset to draft"""
        self.write({'state': 'draft'})
