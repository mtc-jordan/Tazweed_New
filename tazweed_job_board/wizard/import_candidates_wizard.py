# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import csv
import io
import logging

_logger = logging.getLogger(__name__)


class ImportCandidatesWizard(models.TransientModel):
    """Wizard for importing candidates from job boards or files"""
    _name = 'import.candidates.wizard'
    _description = 'Import Candidates Wizard'

    # Import Source
    import_type = fields.Selection([
        ('board', 'From Job Board'),
        ('file', 'From File (CSV/Excel)'),
        ('linkedin', 'LinkedIn Import'),
    ], string='Import From', default='board', required=True)
    
    # Job Board Import
    job_board_id = fields.Many2one('job.board', string='Job Board',
        domain=[('active', '=', True), ('supports_sourcing', '=', True)])
    job_posting_id = fields.Many2one('job.posting', string='Job Posting',
        domain="[('job_board_id', '=', job_board_id), ('state', '=', 'active')]")
    
    # File Import
    import_file = fields.Binary(string='Import File')
    import_filename = fields.Char(string='Filename')
    
    # Target
    hr_job_id = fields.Many2one('hr.job', string='Target Job Position')
    
    # Options
    skip_duplicates = fields.Boolean(string='Skip Duplicates', default=True)
    auto_parse_resume = fields.Boolean(string='Auto Parse Resumes', default=False)
    auto_calculate_score = fields.Boolean(string='Auto Calculate Match Score', default=True)
    assign_recruiter_id = fields.Many2one('res.users', string='Assign to Recruiter')
    
    # Import Settings
    date_from = fields.Date(string='Applications From')
    date_to = fields.Date(string='Applications To')
    limit = fields.Integer(string='Maximum Records', default=100)
    
    # Preview
    preview_line_ids = fields.One2many('import.candidates.wizard.line', 'wizard_id', string='Preview')
    preview_count = fields.Integer(string='Records to Import', compute='_compute_preview_count')
    
    # Results
    imported_count = fields.Integer(string='Imported', readonly=True)
    skipped_count = fields.Integer(string='Skipped', readonly=True)
    error_count = fields.Integer(string='Errors', readonly=True)
    
    @api.depends('preview_line_ids')
    def _compute_preview_count(self):
        for wizard in self:
            wizard.preview_count = len(wizard.preview_line_ids.filtered(lambda l: l.to_import))
    
    @api.onchange('import_type')
    def _onchange_import_type(self):
        self.preview_line_ids = [(5, 0, 0)]
    
    def action_preview(self):
        """Preview candidates before import"""
        self.ensure_one()
        self.preview_line_ids = [(5, 0, 0)]
        
        if self.import_type == 'board':
            self._preview_from_board()
        elif self.import_type == 'file':
            self._preview_from_file()
        elif self.import_type == 'linkedin':
            self._preview_from_linkedin()
        
        return self._reopen_wizard()
    
    def _preview_from_board(self):
        """Preview candidates from job board"""
        if not self.job_board_id:
            raise UserError(_('Please select a job board.'))
        
        # Simulate fetching candidates from board API
        # In production, this would call the actual API
        sample_candidates = [
            {'name': 'Ahmed Al Maktoum', 'email': 'ahmed@example.com', 'title': 'Senior Developer', 'experience': 5},
            {'name': 'Fatima Hassan', 'email': 'fatima@example.com', 'title': 'Project Manager', 'experience': 7},
            {'name': 'Mohammed Ali', 'email': 'mohammed@example.com', 'title': 'Business Analyst', 'experience': 3},
        ]
        
        lines = []
        for candidate in sample_candidates[:self.limit]:
            # Check for duplicates
            is_duplicate = False
            if self.skip_duplicates and candidate.get('email'):
                existing = self.env['candidate.source'].search([
                    ('email', '=', candidate['email'])
                ], limit=1)
                is_duplicate = bool(existing)
            
            lines.append((0, 0, {
                'candidate_name': candidate.get('name'),
                'email': candidate.get('email'),
                'current_title': candidate.get('title'),
                'experience_years': candidate.get('experience'),
                'to_import': not is_duplicate,
                'is_duplicate': is_duplicate,
            }))
        
        self.preview_line_ids = lines
    
    def _preview_from_file(self):
        """Preview candidates from uploaded file"""
        if not self.import_file:
            raise UserError(_('Please upload a file.'))
        
        try:
            # Decode file
            file_content = base64.b64decode(self.import_file)
            
            if self.import_filename.endswith('.csv'):
                self._parse_csv(file_content)
            else:
                raise UserError(_('Unsupported file format. Please use CSV.'))
                
        except Exception as e:
            raise UserError(_('Error reading file: %s') % str(e))
    
    def _parse_csv(self, file_content):
        """Parse CSV file and create preview lines"""
        try:
            content = file_content.decode('utf-8')
        except:
            content = file_content.decode('latin-1')
        
        reader = csv.DictReader(io.StringIO(content))
        
        lines = []
        for row in reader:
            if len(lines) >= self.limit:
                break
            
            # Map CSV columns to fields
            name = row.get('Name') or row.get('name') or row.get('Full Name') or ''
            email = row.get('Email') or row.get('email') or ''
            phone = row.get('Phone') or row.get('phone') or row.get('Mobile') or ''
            title = row.get('Title') or row.get('Current Title') or row.get('Position') or ''
            company = row.get('Company') or row.get('Current Company') or ''
            experience = row.get('Experience') or row.get('Years') or 0
            
            try:
                experience = int(experience)
            except:
                experience = 0
            
            # Check for duplicates
            is_duplicate = False
            if self.skip_duplicates and email:
                existing = self.env['candidate.source'].search([
                    ('email', '=', email)
                ], limit=1)
                is_duplicate = bool(existing)
            
            lines.append((0, 0, {
                'candidate_name': name,
                'email': email,
                'phone': phone,
                'current_title': title,
                'current_company': company,
                'experience_years': experience,
                'to_import': not is_duplicate and bool(name),
                'is_duplicate': is_duplicate,
            }))
        
        self.preview_line_ids = lines
    
    def _preview_from_linkedin(self):
        """Preview candidates from LinkedIn"""
        if not self.job_board_id or self.job_board_id.code != 'linkedin':
            # Find LinkedIn board
            linkedin = self.env['job.board'].search([('code', '=', 'linkedin')], limit=1)
            if linkedin:
                self.job_board_id = linkedin
        
        # Placeholder for LinkedIn API integration
        raise UserError(_('LinkedIn import requires OAuth authentication. Please configure LinkedIn API credentials first.'))
    
    def _reopen_wizard(self):
        """Reopen the wizard"""
        return {
            'name': _('Import Candidates'),
            'type': 'ir.actions.act_window',
            'res_model': 'import.candidates.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_import(self):
        """Import selected candidates"""
        self.ensure_one()
        
        candidates_to_import = self.preview_line_ids.filtered(lambda l: l.to_import)
        
        if not candidates_to_import:
            raise UserError(_('No candidates selected for import.'))
        
        imported = 0
        skipped = 0
        errors = 0
        
        created_candidates = self.env['candidate.source']
        
        for line in candidates_to_import:
            try:
                # Create candidate
                vals = {
                    'candidate_name': line.candidate_name,
                    'email': line.email,
                    'phone': line.phone,
                    'current_title': line.current_title,
                    'current_company': line.current_company,
                    'experience_years': line.experience_years,
                    'job_board_id': self.job_board_id.id if self.job_board_id else False,
                    'job_posting_id': self.job_posting_id.id if self.job_posting_id else False,
                    'hr_job_id': self.hr_job_id.id if self.hr_job_id else False,
                    'recruiter_id': self.assign_recruiter_id.id if self.assign_recruiter_id else False,
                    'state': 'new',
                }
                
                candidate = self.env['candidate.source'].create(vals)
                created_candidates |= candidate
                
                # Auto calculate match score
                if self.auto_calculate_score and self.hr_job_id:
                    candidate.action_calculate_match_score()
                
                imported += 1
                
            except Exception as e:
                _logger.error(f"Error importing candidate {line.candidate_name}: {e}")
                errors += 1
        
        self.imported_count = imported
        self.skipped_count = skipped
        self.error_count = errors
        
        # Show result
        if len(created_candidates) == 1:
            return {
                'name': _('Imported Candidate'),
                'type': 'ir.actions.act_window',
                'res_model': 'candidate.source',
                'res_id': created_candidates.id,
                'view_mode': 'form',
            }
        elif created_candidates:
            return {
                'name': _('Imported Candidates'),
                'type': 'ir.actions.act_window',
                'res_model': 'candidate.source',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', created_candidates.ids)],
            }
        else:
            return {'type': 'ir.actions.act_window_close'}
    
    def action_download_template(self):
        """Download CSV template for import"""
        template_content = "Name,Email,Phone,Title,Company,Experience\n"
        template_content += "John Doe,john@example.com,+971501234567,Software Engineer,Tech Corp,5\n"
        
        attachment = self.env['ir.attachment'].create({
            'name': 'candidate_import_template.csv',
            'type': 'binary',
            'datas': base64.b64encode(template_content.encode('utf-8')),
            'mimetype': 'text/csv',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class ImportCandidatesWizardLine(models.TransientModel):
    """Preview line for candidate import"""
    _name = 'import.candidates.wizard.line'
    _description = 'Import Candidates Preview Line'

    wizard_id = fields.Many2one('import.candidates.wizard', string='Wizard', ondelete='cascade')
    
    # Candidate Data
    candidate_name = fields.Char(string='Name')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    current_title = fields.Char(string='Title')
    current_company = fields.Char(string='Company')
    experience_years = fields.Integer(string='Experience')
    linkedin_url = fields.Char(string='LinkedIn')
    
    # Import Status
    to_import = fields.Boolean(string='Import', default=True)
    is_duplicate = fields.Boolean(string='Duplicate')
    error_message = fields.Char(string='Error')
