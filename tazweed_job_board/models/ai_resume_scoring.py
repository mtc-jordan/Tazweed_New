# -*- coding: utf-8 -*-
"""
AI-Powered Resume Scoring for Tazweed Job Board
Automatically score and rank candidates based on job requirements
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import json
from datetime import datetime
import re
import hashlib

_logger = logging.getLogger(__name__)


class AIResumeScorer(models.Model):
    """AI Resume Scoring Engine"""
    _name = 'ai.resume.scorer'
    _description = 'AI Resume Scorer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Scoring Session', required=True, tracking=True,
                       default=lambda self: _('New Scoring Session'))
    
    job_posting_id = fields.Many2one('job.posting', string='Job Posting')
    
    # Scoring Configuration
    scoring_model = fields.Selection([
        ('basic', 'Basic Keyword Matching'),
        ('advanced', 'Advanced NLP Analysis'),
        ('ml', 'Machine Learning Model'),
    ], string='Scoring Model', default='advanced', required=True)
    
    # Weights for different criteria
    skills_weight = fields.Float(string='Skills Weight %', default=30)
    experience_weight = fields.Float(string='Experience Weight %', default=25)
    education_weight = fields.Float(string='Education Weight %', default=20)
    certifications_weight = fields.Float(string='Certifications Weight %', default=15)
    keywords_weight = fields.Float(string='Keywords Weight %', default=10)
    
    # Job Requirements (for matching)
    required_skills = fields.Text(string='Required Skills',
                                   help='Comma-separated list of required skills')
    preferred_skills = fields.Text(string='Preferred Skills',
                                    help='Comma-separated list of preferred skills')
    min_experience = fields.Float(string='Minimum Experience (Years)')
    max_experience = fields.Float(string='Maximum Experience (Years)')
    required_education = fields.Selection([
        ('any', 'Any'),
        ('high_school', 'High School'),
        ('associate', 'Associate Degree'),
        ('bachelor', "Bachelor's Degree"),
        ('master', "Master's Degree"),
        ('doctorate', 'Doctorate'),
    ], string='Required Education', default='any')
    required_certifications = fields.Text(string='Required Certifications')
    keywords = fields.Text(string='Keywords to Match')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('configured', 'Configured'),
        ('running', 'Running'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)
    
    # Results
    total_resumes = fields.Integer(string='Total Resumes', compute='_compute_statistics')
    scored_resumes = fields.Integer(string='Scored Resumes', compute='_compute_statistics')
    avg_score = fields.Float(string='Average Score', compute='_compute_statistics')
    top_candidates = fields.Integer(string='Top Candidates (>80%)', compute='_compute_statistics')
    
    # Related records
    score_ids = fields.One2many('ai.resume.score', 'scorer_id', string='Resume Scores')
    
    # Dates
    started_at = fields.Datetime(string='Started At')
    completed_at = fields.Datetime(string='Completed At')

    @api.depends('score_ids')
    def _compute_statistics(self):
        for rec in self:
            scores = rec.score_ids
            rec.total_resumes = len(scores)
            rec.scored_resumes = len(scores.filtered(lambda s: s.state == 'scored'))
            rec.avg_score = sum(scores.mapped('total_score')) / len(scores) if scores else 0
            rec.top_candidates = len(scores.filtered(lambda s: s.total_score >= 80))

    @api.constrains('skills_weight', 'experience_weight', 'education_weight', 
                    'certifications_weight', 'keywords_weight')
    def _check_weights(self):
        for rec in self:
            total = (rec.skills_weight + rec.experience_weight + rec.education_weight +
                     rec.certifications_weight + rec.keywords_weight)
            if abs(total - 100) > 0.01:
                raise ValidationError(_('Total weights must equal 100%. Current total: %.2f%%') % total)

    @api.onchange('job_posting_id')
    def _onchange_job_posting(self):
        """Auto-fill requirements from job posting"""
        if self.job_posting_id:
            self.name = f'Scoring: {self.job_posting_id.name}'
            # In production, extract requirements from job posting

    def action_configure(self):
        """Mark as configured"""
        self.ensure_one()
        self.write({'state': 'configured'})

    def action_start_scoring(self):
        """Start the scoring process"""
        self.ensure_one()
        if not self.score_ids:
            raise UserError(_('No resumes to score. Please add resumes first.'))
        
        self.write({
            'state': 'running',
            'started_at': datetime.now(),
        })
        
        # Score all resumes
        for score in self.score_ids:
            score._calculate_score()
        
        self.write({
            'state': 'completed',
            'completed_at': datetime.now(),
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Scoring Complete'),
                'message': _('Successfully scored %d resumes') % len(self.score_ids),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_add_candidates(self):
        """Open wizard to add candidates for scoring"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Candidates'),
            'res_model': 'add.candidates.scoring.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_scorer_id': self.id},
        }

    def action_view_results(self):
        """View scoring results"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Scoring Results'),
            'res_model': 'ai.resume.score',
            'view_mode': 'tree,form',
            'domain': [('scorer_id', '=', self.id)],
            'context': {'default_scorer_id': self.id},
        }


class AIResumeScore(models.Model):
    """Individual Resume Score"""
    _name = 'ai.resume.score'
    _description = 'AI Resume Score'
    _order = 'total_score desc'

    scorer_id = fields.Many2one('ai.resume.scorer', string='Scoring Session',
                                 required=True, ondelete='cascade')
    candidate_id = fields.Many2one('tazweed.candidate', string='Candidate')
    
    # Resume Info
    candidate_name = fields.Char(string='Candidate Name', required=True)
    email = fields.Char(string='Email')
    resume = fields.Binary(string='Resume')
    resume_filename = fields.Char(string='Resume Filename')
    resume_text = fields.Text(string='Extracted Text')
    
    # Individual Scores (0-100)
    skills_score = fields.Float(string='Skills Score')
    experience_score = fields.Float(string='Experience Score')
    education_score = fields.Float(string='Education Score')
    certifications_score = fields.Float(string='Certifications Score')
    keywords_score = fields.Float(string='Keywords Score')
    
    # Weighted Total Score
    total_score = fields.Float(string='Total Score', compute='_compute_total_score', store=True)
    
    # AI Analysis
    matched_skills = fields.Text(string='Matched Skills')
    missing_skills = fields.Text(string='Missing Skills')
    experience_years = fields.Float(string='Detected Experience (Years)')
    education_level = fields.Char(string='Detected Education')
    matched_certifications = fields.Text(string='Matched Certifications')
    matched_keywords = fields.Text(string='Matched Keywords')
    
    # Recommendation
    recommendation = fields.Selection([
        ('strong_hire', 'Strong Hire'),
        ('hire', 'Hire'),
        ('maybe', 'Maybe'),
        ('no_hire', 'No Hire'),
    ], string='Recommendation', compute='_compute_recommendation', store=True)
    
    recommendation_reason = fields.Text(string='Recommendation Reason')
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('scoring', 'Scoring'),
        ('scored', 'Scored'),
        ('error', 'Error'),
    ], string='Status', default='pending')
    
    error_message = fields.Text(string='Error Message')
    
    # Ranking
    rank = fields.Integer(string='Rank')

    @api.depends('skills_score', 'experience_score', 'education_score',
                 'certifications_score', 'keywords_score', 'scorer_id')
    def _compute_total_score(self):
        for rec in self:
            if rec.scorer_id:
                rec.total_score = (
                    rec.skills_score * rec.scorer_id.skills_weight / 100 +
                    rec.experience_score * rec.scorer_id.experience_weight / 100 +
                    rec.education_score * rec.scorer_id.education_weight / 100 +
                    rec.certifications_score * rec.scorer_id.certifications_weight / 100 +
                    rec.keywords_score * rec.scorer_id.keywords_weight / 100
                )
            else:
                rec.total_score = 0

    @api.depends('total_score')
    def _compute_recommendation(self):
        for rec in self:
            if rec.total_score >= 85:
                rec.recommendation = 'strong_hire'
            elif rec.total_score >= 70:
                rec.recommendation = 'hire'
            elif rec.total_score >= 50:
                rec.recommendation = 'maybe'
            else:
                rec.recommendation = 'no_hire'

    def _calculate_score(self):
        """Calculate all scores for this resume"""
        self.ensure_one()
        self.write({'state': 'scoring'})
        
        try:
            scorer = self.scorer_id
            
            # Extract text from resume if not already done
            if not self.resume_text and self.resume:
                self._extract_resume_text()
            
            resume_text = (self.resume_text or '').lower()
            
            # Calculate Skills Score
            skills_score, matched_skills, missing_skills = self._score_skills(
                resume_text, scorer.required_skills, scorer.preferred_skills)
            
            # Calculate Experience Score
            experience_score, detected_exp = self._score_experience(
                resume_text, scorer.min_experience, scorer.max_experience)
            
            # Calculate Education Score
            education_score, detected_edu = self._score_education(
                resume_text, scorer.required_education)
            
            # Calculate Certifications Score
            certs_score, matched_certs = self._score_certifications(
                resume_text, scorer.required_certifications)
            
            # Calculate Keywords Score
            keywords_score, matched_kw = self._score_keywords(
                resume_text, scorer.keywords)
            
            # Generate recommendation reason
            reason = self._generate_recommendation_reason(
                skills_score, experience_score, education_score,
                matched_skills, missing_skills, detected_exp)
            
            self.write({
                'skills_score': skills_score,
                'experience_score': experience_score,
                'education_score': education_score,
                'certifications_score': certs_score,
                'keywords_score': keywords_score,
                'matched_skills': matched_skills,
                'missing_skills': missing_skills,
                'experience_years': detected_exp,
                'education_level': detected_edu,
                'matched_certifications': matched_certs,
                'matched_keywords': matched_kw,
                'recommendation_reason': reason,
                'state': 'scored',
            })
            
        except Exception as e:
            _logger.error(f'Resume scoring error: {e}')
            self.write({
                'state': 'error',
                'error_message': str(e),
            })

    def _extract_resume_text(self):
        """Extract text from resume file"""
        # In production, use PDF/DOCX parser
        # For demo, we'll use placeholder text
        self.resume_text = "Sample resume text for demonstration"

    def _score_skills(self, resume_text, required_skills, preferred_skills):
        """Score based on skills matching"""
        required = [s.strip().lower() for s in (required_skills or '').split(',') if s.strip()]
        preferred = [s.strip().lower() for s in (preferred_skills or '').split(',') if s.strip()]
        
        matched = []
        missing = []
        
        for skill in required:
            if skill in resume_text:
                matched.append(skill)
            else:
                missing.append(skill)
        
        for skill in preferred:
            if skill in resume_text:
                matched.append(skill)
        
        if not required and not preferred:
            return 75, '', ''  # Default score if no skills specified
        
        total_skills = len(required) + len(preferred) * 0.5
        matched_count = len([s for s in matched if s in required]) + len([s for s in matched if s in preferred]) * 0.5
        
        score = min(100, (matched_count / total_skills * 100)) if total_skills > 0 else 75
        
        return score, ', '.join(matched), ', '.join(missing)

    def _score_experience(self, resume_text, min_exp, max_exp):
        """Score based on experience"""
        # Extract years of experience from resume
        exp_patterns = [
            r'(\d+)\+?\s*years?\s*(of)?\s*experience',
            r'experience[:\s]+(\d+)\s*years?',
            r'(\d+)\s*years?\s*(in|of)',
        ]
        
        detected_exp = 0
        for pattern in exp_patterns:
            match = re.search(pattern, resume_text)
            if match:
                detected_exp = float(match.group(1))
                break
        
        # Calculate score
        if min_exp and detected_exp < min_exp:
            score = max(0, 100 - (min_exp - detected_exp) * 20)
        elif max_exp and detected_exp > max_exp:
            score = max(50, 100 - (detected_exp - max_exp) * 10)
        else:
            score = 100
        
        return score, detected_exp

    def _score_education(self, resume_text, required_education):
        """Score based on education"""
        education_levels = {
            'doctorate': ['phd', 'doctorate', 'doctoral'],
            'master': ['master', 'mba', 'msc', 'ma', 'ms'],
            'bachelor': ['bachelor', 'bsc', 'ba', 'bs', 'undergraduate'],
            'associate': ['associate', 'diploma'],
            'high_school': ['high school', 'secondary'],
        }
        
        detected_level = 'any'
        for level, keywords in education_levels.items():
            for kw in keywords:
                if kw in resume_text:
                    detected_level = level
                    break
            if detected_level != 'any':
                break
        
        level_scores = {
            'any': 75,
            'high_school': 60,
            'associate': 70,
            'bachelor': 80,
            'master': 90,
            'doctorate': 100,
        }
        
        if required_education == 'any':
            score = level_scores.get(detected_level, 75)
        else:
            req_score = level_scores.get(required_education, 75)
            det_score = level_scores.get(detected_level, 75)
            score = min(100, det_score / req_score * 100) if req_score > 0 else 75
        
        return score, detected_level

    def _score_certifications(self, resume_text, required_certs):
        """Score based on certifications"""
        required = [c.strip().lower() for c in (required_certs or '').split(',') if c.strip()]
        
        if not required:
            return 75, ''  # Default score if no certifications specified
        
        matched = [c for c in required if c in resume_text]
        score = len(matched) / len(required) * 100 if required else 75
        
        return score, ', '.join(matched)

    def _score_keywords(self, resume_text, keywords):
        """Score based on keyword matching"""
        kw_list = [k.strip().lower() for k in (keywords or '').split(',') if k.strip()]
        
        if not kw_list:
            return 75, ''  # Default score if no keywords specified
        
        matched = [k for k in kw_list if k in resume_text]
        score = len(matched) / len(kw_list) * 100 if kw_list else 75
        
        return score, ', '.join(matched)

    def _generate_recommendation_reason(self, skills_score, exp_score, edu_score,
                                         matched_skills, missing_skills, detected_exp):
        """Generate human-readable recommendation reason"""
        reasons = []
        
        if skills_score >= 80:
            reasons.append(f"Strong skills match ({matched_skills})")
        elif missing_skills:
            reasons.append(f"Missing key skills: {missing_skills}")
        
        if exp_score >= 80:
            reasons.append(f"Excellent experience ({detected_exp} years)")
        elif exp_score < 50:
            reasons.append(f"Limited experience ({detected_exp} years)")
        
        if edu_score >= 80:
            reasons.append("Education meets requirements")
        
        return '. '.join(reasons) if reasons else "Standard candidate profile"


class AddCandidatesScoringWizard(models.TransientModel):
    """Wizard to add candidates for scoring"""
    _name = 'add.candidates.scoring.wizard'
    _description = 'Add Candidates for Scoring'

    scorer_id = fields.Many2one('ai.resume.scorer', string='Scoring Session', required=True)
    candidate_ids = fields.Many2many('tazweed.candidate', string='Candidates')
    source = fields.Selection([
        ('candidates', 'From Candidates'),
        ('applications', 'From Job Applications'),
        ('upload', 'Upload Resumes'),
    ], string='Source', default='candidates')

    def action_add(self):
        """Add selected candidates to scoring session"""
        self.ensure_one()
        
        for candidate in self.candidate_ids:
            self.env['ai.resume.score'].create({
                'scorer_id': self.scorer_id.id,
                'candidate_id': candidate.id,
                'candidate_name': candidate.name,
                'email': candidate.email,
                'resume': candidate.resume,
                'resume_filename': candidate.resume_filename,
            })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Candidates Added'),
                'message': _('Added %d candidates for scoring') % len(self.candidate_ids),
                'type': 'success',
                'sticky': False,
            }
        }
