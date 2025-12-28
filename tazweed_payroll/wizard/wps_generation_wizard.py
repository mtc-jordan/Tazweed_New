# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class WPSGenerationWizard(models.TransientModel):
    """Wizard to generate WPS file"""
    _name = 'tazweed.wps.generation.wizard'
    _description = 'WPS Generation Wizard'

    # Batch
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Payslip Batch',
        required=True,
    )
    
    # Period
    salary_month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='Salary Month', required=True,
       default=lambda self: str(date.today().month).zfill(2),
    )
    
    salary_year = fields.Char(
        string='Salary Year',
        required=True,
        default=lambda self: str(date.today().year),
    )
    
    # Employer Details
    employer_eid = fields.Char(
        string='Employer Emirates ID',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'tazweed_payroll.wps_employer_eid', ''
        ),
    )
    employer_bank_code = fields.Char(
        string='Employer Bank Code',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'tazweed_payroll.wps_employer_bank_code', ''
        ),
    )
    employer_account = fields.Char(
        string='Employer Bank Account',
        default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
            'tazweed_payroll.wps_employer_account', ''
        ),
    )
    
    # Options
    file_type = fields.Selection([
        ('sif', 'SIF (Salary Information File)'),
        ('non_sif', 'Non-SIF'),
    ], string='File Type', default='sif', required=True)
    
    include_pending = fields.Boolean(
        string='Include Pending Payslips',
        default=False,
        help='Include payslips that are not yet confirmed',
    )

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run_id(self):
        """Set month/year from batch"""
        if self.payslip_run_id:
            self.salary_month = str(self.payslip_run_id.date_start.month).zfill(2)
            self.salary_year = str(self.payslip_run_id.date_start.year)

    def action_generate(self):
        """Generate WPS file"""
        self.ensure_one()
        
        # Validate
        if not self.employer_eid:
            raise UserError(_('Please configure Employer Emirates ID.'))
        
        # Create WPS file record
        wps_file = self.env['tazweed.wps.file'].create({
            'payslip_run_id': self.payslip_run_id.id,
            'salary_month': self.salary_month,
            'salary_year': self.salary_year,
            'employer_eid': self.employer_eid,
            'employer_bank_code': self.employer_bank_code,
            'employer_account': self.employer_account,
            'file_type': self.file_type,
        })
        
        # Generate lines
        wps_file.action_generate_lines()
        
        # Generate file
        wps_file.action_generate_file()
        
        # Update batch
        self.payslip_run_id.write({
            'wps_file_id': wps_file.id,
            'wps_generated': True,
        })
        
        # Return action to view WPS file
        return {
            'name': _('WPS File'),
            'type': 'ir.actions.act_window',
            'res_model': 'tazweed.wps.file',
            'res_id': wps_file.id,
            'view_mode': 'form',
        }
