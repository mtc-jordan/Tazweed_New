# -*- coding: utf-8 -*-

import re
import logging
import base64
from io import BytesIO
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False


class ResumeParser(models.TransientModel):
    """Resume/CV Parser for extracting candidate information"""
    _name = 'resume.parser'
    _description = 'Resume Parser'

    @api.model
    def parse_resume(self, file_content, filename):
        """
        Parse resume file and extract candidate information
        
        Args:
            file_content: Base64 encoded file content
            filename: Original filename with extension
            
        Returns:
            dict: Extracted candidate data
        """
        try:
            # Decode file content
            content = base64.b64decode(file_content)
            
            # Extract text based on file type
            if filename.lower().endswith('.pdf'):
                text = self._extract_pdf_text(content)
            elif filename.lower().endswith(('.doc', '.docx')):
                text = self._extract_docx_text(content)
            elif filename.lower().endswith('.txt'):
                text = content.decode('utf-8', errors='ignore')
            else:
                raise UserError(_("Unsupported file format. Please upload PDF, DOC, DOCX, or TXT files."))
            
            # Parse extracted text
            return self._parse_text(text)
            
        except Exception as e:
            _logger.error(f"Resume parsing error: {str(e)}")
            return {'error': str(e)}

    def _extract_pdf_text(self, content):
        """Extract text from PDF file"""
        if not HAS_PYPDF2:
            raise UserError(_("PyPDF2 library is required for PDF parsing. Please install it."))
        
        text = ""
        try:
            pdf_file = BytesIO(content)
            reader = PyPDF2.PdfReader(pdf_file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except Exception as e:
            _logger.error(f"PDF extraction error: {str(e)}")
        return text

    def _extract_docx_text(self, content):
        """Extract text from DOCX file"""
        if not HAS_DOCX:
            raise UserError(_("python-docx library is required for DOCX parsing. Please install it."))
        
        text = ""
        try:
            doc_file = BytesIO(content)
            doc = Document(doc_file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            _logger.error(f"DOCX extraction error: {str(e)}")
        return text

    def _parse_text(self, text):
        """Parse text and extract structured information"""
        data = {
            'name': '',
            'email': '',
            'phone': '',
            'linkedin': '',
            'location': '',
            'skills': [],
            'experience_years': 0,
            'education': '',
            'current_company': '',
            'current_title': '',
            'summary': '',
            'languages': [],
            'raw_text': text[:5000],  # Store first 5000 chars for reference
        }
        
        # Extract email
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        if emails:
            data['email'] = emails[0]
        
        # Extract phone numbers (UAE format and international)
        phone_patterns = [
            r'\+971[\s-]?\d{1,2}[\s-]?\d{3}[\s-]?\d{4}',  # UAE
            r'\+\d{1,3}[\s-]?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{3,4}',  # International
            r'0\d{1,2}[\s-]?\d{3}[\s-]?\d{4}',  # Local UAE
            r'\d{3}[\s.-]?\d{3}[\s.-]?\d{4}',  # US format
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                data['phone'] = phones[0].strip()
                break
        
        # Extract LinkedIn URL
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin = re.findall(linkedin_pattern, text.lower())
        if linkedin:
            data['linkedin'] = f"https://www.{linkedin[0]}"
        
        # Extract name (usually at the beginning)
        lines = text.strip().split('\n')
        for line in lines[:5]:
            line = line.strip()
            # Skip lines that look like contact info
            if '@' in line or re.search(r'\d{3}', line) or not line:
                continue
            # Name is usually 2-4 words, all capitalized or title case
            words = line.split()
            if 2 <= len(words) <= 4:
                if all(w[0].isupper() for w in words if w):
                    data['name'] = line
                    break
        
        # Extract skills
        skill_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node',
            'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'aws', 'azure',
            'docker', 'kubernetes', 'git', 'agile', 'scrum', 'project management',
            'excel', 'powerpoint', 'word', 'sap', 'erp', 'crm', 'salesforce',
            'accounting', 'finance', 'marketing', 'sales', 'hr', 'recruitment',
            'communication', 'leadership', 'teamwork', 'problem solving',
            'arabic', 'english', 'hindi', 'urdu', 'french', 'spanish',
            'autocad', 'photoshop', 'illustrator', 'figma', 'sketch',
            'machine learning', 'data science', 'analytics', 'tableau', 'power bi',
        ]
        text_lower = text.lower()
        for skill in skill_keywords:
            if skill in text_lower:
                data['skills'].append(skill.title())
        
        # Extract experience years
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'experience[:\s]*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*(?:in|of)',
        ]
        for pattern in exp_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                data['experience_years'] = int(matches[0])
                break
        
        # Extract education
        education_keywords = ['bachelor', 'master', 'mba', 'phd', 'diploma', 'degree', 'bsc', 'msc', 'bba']
        for line in lines:
            line_lower = line.lower()
            for keyword in education_keywords:
                if keyword in line_lower:
                    data['education'] = line.strip()
                    break
            if data['education']:
                break
        
        # Extract location (UAE cities)
        uae_cities = ['dubai', 'abu dhabi', 'sharjah', 'ajman', 'ras al khaimah', 'fujairah', 'umm al quwain']
        for city in uae_cities:
            if city in text_lower:
                data['location'] = city.title()
                break
        
        # Extract languages
        language_keywords = ['arabic', 'english', 'hindi', 'urdu', 'french', 'spanish', 'german', 'chinese', 'tagalog', 'malayalam']
        for lang in language_keywords:
            if lang in text_lower:
                data['languages'].append(lang.title())
        
        # Generate summary from first paragraph
        paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 50]
        if paragraphs:
            data['summary'] = paragraphs[0][:500]
        
        return data

    @api.model
    def create_candidate_from_resume(self, file_content, filename, job_id=None, source_id=None):
        """
        Parse resume and create a candidate record
        
        Args:
            file_content: Base64 encoded file content
            filename: Original filename
            job_id: Optional job position ID
            source_id: Optional source ID (job board)
            
        Returns:
            hr.applicant record
        """
        # Parse resume
        parsed_data = self.parse_resume(file_content, filename)
        
        if 'error' in parsed_data:
            raise UserError(_("Failed to parse resume: %s") % parsed_data['error'])
        
        # Check for duplicate by email
        if parsed_data.get('email'):
            existing = self.env['hr.applicant'].search([
                ('email_from', '=', parsed_data['email'])
            ], limit=1)
            if existing:
                return existing
        
        # Create applicant
        applicant_vals = {
            'name': parsed_data.get('name') or 'Unknown Candidate',
            'partner_name': parsed_data.get('name') or 'Unknown Candidate',
            'email_from': parsed_data.get('email'),
            'partner_phone': parsed_data.get('phone'),
            'linkedin_profile': parsed_data.get('linkedin'),
            'description': parsed_data.get('summary'),
            'job_id': job_id,
        }
        
        # Add source if provided
        if source_id:
            applicant_vals['source_id'] = source_id
        
        applicant = self.env['hr.applicant'].create(applicant_vals)
        
        # Attach resume
        self.env['ir.attachment'].create({
            'name': filename,
            'datas': file_content,
            'res_model': 'hr.applicant',
            'res_id': applicant.id,
        })
        
        # Store parsed skills as tags if available
        if parsed_data.get('skills'):
            skill_text = ', '.join(parsed_data['skills'][:10])
            applicant.write({
                'description': f"{applicant.description or ''}\n\nSkills: {skill_text}"
            })
        
        return applicant

    @api.model
    def bulk_import_resumes(self, files, job_id=None, source_id=None):
        """
        Import multiple resumes at once
        
        Args:
            files: List of dicts with 'content' and 'filename'
            job_id: Optional job position ID
            source_id: Optional source ID
            
        Returns:
            dict: Import results
        """
        results = {
            'success': [],
            'failed': [],
            'duplicates': [],
        }
        
        for file_data in files:
            try:
                applicant = self.create_candidate_from_resume(
                    file_data['content'],
                    file_data['filename'],
                    job_id,
                    source_id
                )
                results['success'].append({
                    'filename': file_data['filename'],
                    'applicant_id': applicant.id,
                    'name': applicant.name,
                })
            except UserError as e:
                if 'duplicate' in str(e).lower():
                    results['duplicates'].append({
                        'filename': file_data['filename'],
                        'error': str(e),
                    })
                else:
                    results['failed'].append({
                        'filename': file_data['filename'],
                        'error': str(e),
                    })
            except Exception as e:
                results['failed'].append({
                    'filename': file_data['filename'],
                    'error': str(e),
                })
        
        return results
