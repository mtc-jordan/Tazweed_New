# -*- coding: utf-8 -*-
"""
AI Candidate Matching Module
Auto-match candidates to job requirements using AI-powered scoring
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class AICandidateMatch(models.Model):
    """AI-powered candidate matching for job orders"""
    _name = 'ai.candidate.match'
    _description = 'AI Candidate Match'
    _order = 'match_score desc, create_date desc'
    _rec_name = 'display_name'

    # Core Fields
    job_order_id = fields.Many2one(
        'tazweed.job.order',
        string='Job Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    candidate_id = fields.Many2one(
        'tazweed.candidate',
        string='Candidate',
        required=True,
        ondelete='cascade',
        index=True,
    )
    engine_run_id = fields.Many2one(
        'ai.matching.engine',
        string='Matching Run',
        ondelete='set null',
    )
    
    # Match Scores
    match_score = fields.Float(
        string='Overall Match %',
        compute='_compute_match_score',
        store=True,
        help='Overall match percentage based on all criteria',
    )
    skill_match_score = fields.Float(
        string='Skills Match %',
        default=0.0,
    )
    experience_match_score = fields.Float(
        string='Experience Match %',
        default=0.0,
    )
    education_match_score = fields.Float(
        string='Education Match %',
        default=0.0,
    )
    location_match_score = fields.Float(
        string='Location Match %',
        default=0.0,
    )
    salary_match_score = fields.Float(
        string='Salary Match %',
        default=0.0,
    )
    availability_match_score = fields.Float(
        string='Availability Match %',
        default=0.0,
    )
    
    # Match Details
    matching_skills = fields.Text(
        string='Matching Skills',
        help='JSON list of matching skills',
    )
    missing_skills = fields.Text(
        string='Missing Skills',
        help='JSON list of missing required skills',
    )
    match_details = fields.Text(
        string='Match Analysis',
        help='Detailed analysis of the match',
    )
    
    # Status
    state = fields.Selection([
        ('pending', 'Pending Review'),
        ('shortlisted', 'Shortlisted'),
        ('contacted', 'Contacted'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired'),
    ], string='Status', default='pending', tracking=True)
    
    # Recommendation
    recommendation = fields.Selection([
        ('highly_recommended', 'Highly Recommended'),
        ('recommended', 'Recommended'),
        ('consider', 'Consider'),
        ('not_recommended', 'Not Recommended'),
    ], string='AI Recommendation', compute='_compute_recommendation', store=True)
    
    recommendation_reason = fields.Text(
        string='Recommendation Reason',
        compute='_compute_recommendation',
        store=True,
    )
    
    # Audit Fields
    matched_date = fields.Datetime(
        string='Matched Date',
        default=fields.Datetime.now,
    )
    reviewed_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
    )
    reviewed_date = fields.Datetime(
        string='Reviewed Date',
    )
    notes = fields.Text(string='Notes')
    
    # Related Fields
    client_id = fields.Many2one(
        related='job_order_id.client_id',
        string='Client',
        store=True,
    )
    job_title = fields.Char(
        related='job_order_id.job_title',
        string='Job Title',
        store=True,
    )
    candidate_name = fields.Char(
        related='candidate_id.name',
        string='Candidate Name',
        store=True,
    )
    
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )

    _sql_constraints = [
        ('unique_job_candidate', 'unique(job_order_id, candidate_id)',
         'A candidate can only be matched once per job order!'),
    ]

    @api.depends('candidate_id', 'job_order_id')
    def _compute_display_name(self):
        for record in self:
            if record.candidate_id and record.job_order_id:
                record.display_name = f"{record.candidate_id.name} - {record.job_order_id.job_title}"
            else:
                record.display_name = "New Match"

    @api.depends('skill_match_score', 'experience_match_score', 'education_match_score',
                 'location_match_score', 'salary_match_score', 'availability_match_score')
    def _compute_match_score(self):
        """Calculate overall match score with weighted average"""
        weights = {
            'skill': 0.35,
            'experience': 0.25,
            'education': 0.15,
            'location': 0.10,
            'salary': 0.10,
            'availability': 0.05,
        }
        for record in self:
            record.match_score = (
                record.skill_match_score * weights['skill'] +
                record.experience_match_score * weights['experience'] +
                record.education_match_score * weights['education'] +
                record.location_match_score * weights['location'] +
                record.salary_match_score * weights['salary'] +
                record.availability_match_score * weights['availability']
            )

    @api.depends('match_score')
    def _compute_recommendation(self):
        """Generate AI recommendation based on match score"""
        for record in self:
            score = record.match_score
            if score >= 85:
                record.recommendation = 'highly_recommended'
                record.recommendation_reason = _(
                    'Excellent match! Candidate exceeds most requirements with a %.1f%% match score. '
                    'Strong alignment in skills, experience, and qualifications.'
                ) % score
            elif score >= 70:
                record.recommendation = 'recommended'
                record.recommendation_reason = _(
                    'Good match with %.1f%% score. Candidate meets most key requirements. '
                    'Minor gaps can be addressed through training.'
                ) % score
            elif score >= 50:
                record.recommendation = 'consider'
                record.recommendation_reason = _(
                    'Moderate match at %.1f%%. Candidate has potential but may need '
                    'additional development in some areas.'
                ) % score
            else:
                record.recommendation = 'not_recommended'
                record.recommendation_reason = _(
                    'Low match score of %.1f%%. Significant gaps in required skills or experience. '
                    'Consider other candidates first.'
                ) % score

    def action_shortlist(self):
        """Shortlist the candidate"""
        self.write({
            'state': 'shortlisted',
            'reviewed_by': self.env.uid,
            'reviewed_date': fields.Datetime.now(),
        })
        return True

    def action_reject(self):
        """Reject the candidate"""
        self.write({
            'state': 'rejected',
            'reviewed_by': self.env.uid,
            'reviewed_date': fields.Datetime.now(),
        })
        return True

    def action_schedule_interview(self):
        """Open interview scheduling wizard"""
        self.write({'state': 'interview_scheduled'})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Interview'),
            'res_model': 'tazweed.interview',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_candidate_id': self.candidate_id.id,
                'default_job_order_id': self.job_order_id.id,
            },
        }

    def action_view_candidate(self):
        """View candidate details"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Candidate'),
            'res_model': 'tazweed.candidate',
            'res_id': self.candidate_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class AIMatchingEngine(models.Model):
    """AI Matching Engine for running batch matching"""
    _name = 'ai.matching.engine'
    _description = 'AI Matching Engine'
    _order = 'create_date desc'

    name = fields.Char(
        string='Matching Run',
        required=True,
        default=lambda self: _('Match Run %s') % fields.Datetime.now().strftime('%Y-%m-%d %H:%M'),
    )
    job_order_id = fields.Many2one(
        'tazweed.job.order',
        string='Job Order',
        help='Leave empty to match all open job orders',
    )
    
    # Configuration
    minimum_score = fields.Float(
        string='Minimum Match Score',
        default=50.0,
        help='Only create matches above this score',
    )
    max_matches_per_job = fields.Integer(
        string='Max Matches per Job',
        default=20,
        help='Maximum number of matches to create per job order',
    )
    include_inactive_candidates = fields.Boolean(
        string='Include Inactive Candidates',
        default=False,
    )
    
    # Results
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Status', default='draft')
    
    matches_created = fields.Integer(
        string='Matches Created',
        default=0,
    )
    jobs_processed = fields.Integer(
        string='Jobs Processed',
        default=0,
    )
    candidates_evaluated = fields.Integer(
        string='Candidates Evaluated',
        default=0,
    )
    execution_time = fields.Float(
        string='Execution Time (seconds)',
        default=0.0,
    )
    error_message = fields.Text(string='Error Message')
    
    # Match Results
    match_ids = fields.One2many(
        'ai.candidate.match',
        'engine_run_id',
        string='Matches',
    )

    def action_run_matching(self):
        """Run the AI matching algorithm"""
        self.ensure_one()
        start_time = datetime.now()
        
        try:
            self.state = 'running'
            self.env.cr.commit()
            
            # Get job orders to process
            if self.job_order_id:
                job_orders = self.job_order_id
            else:
                job_orders = self.env['tazweed.job.order'].search([
                    ('state', 'in', ['open', 'in_progress']),
                ])
            
            # Get candidates
            candidate_domain = []
            if not self.include_inactive_candidates:
                candidate_domain.append(('active', '=', True))
            candidates = self.env['tazweed.candidate'].search(candidate_domain)
            
            matches_created = 0
            jobs_processed = 0
            candidates_evaluated = 0
            
            for job in job_orders:
                job_matches = []
                
                for candidate in candidates:
                    candidates_evaluated += 1
                    
                    # Check if match already exists
                    existing = self.env['ai.candidate.match'].search([
                        ('job_order_id', '=', job.id),
                        ('candidate_id', '=', candidate.id),
                    ], limit=1)
                    
                    if existing:
                        continue
                    
                    # Calculate match scores
                    scores = self._calculate_match_scores(job, candidate)
                    
                    # Calculate overall score
                    overall_score = (
                        scores['skill'] * 0.35 +
                        scores['experience'] * 0.25 +
                        scores['education'] * 0.15 +
                        scores['location'] * 0.10 +
                        scores['salary'] * 0.10 +
                        scores['availability'] * 0.05
                    )
                    
                    if overall_score >= self.minimum_score:
                        job_matches.append({
                            'candidate': candidate,
                            'scores': scores,
                            'overall': overall_score,
                        })
                
                # Sort by overall score and take top matches
                job_matches.sort(key=lambda x: x['overall'], reverse=True)
                job_matches = job_matches[:self.max_matches_per_job]
                
                # Create match records
                for match_data in job_matches:
                    self.env['ai.candidate.match'].create({
                        'job_order_id': job.id,
                        'candidate_id': match_data['candidate'].id,
                        'skill_match_score': match_data['scores']['skill'],
                        'experience_match_score': match_data['scores']['experience'],
                        'education_match_score': match_data['scores']['education'],
                        'location_match_score': match_data['scores']['location'],
                        'salary_match_score': match_data['scores']['salary'],
                        'availability_match_score': match_data['scores']['availability'],
                        'matching_skills': json.dumps(match_data['scores'].get('matching_skills', [])),
                        'missing_skills': json.dumps(match_data['scores'].get('missing_skills', [])),
                        'match_details': match_data['scores'].get('details', ''),
                    })
                    matches_created += 1
                
                jobs_processed += 1
            
            # Update results
            execution_time = (datetime.now() - start_time).total_seconds()
            self.write({
                'state': 'completed',
                'matches_created': matches_created,
                'jobs_processed': jobs_processed,
                'candidates_evaluated': candidates_evaluated,
                'execution_time': execution_time,
            })
            
        except Exception as e:
            _logger.exception("AI Matching failed")
            self.write({
                'state': 'failed',
                'error_message': str(e),
            })
        
        return True

    def _calculate_match_scores(self, job, candidate):
        """Calculate match scores between job and candidate"""
        scores = {
            'skill': 0.0,
            'experience': 0.0,
            'education': 0.0,
            'location': 0.0,
            'salary': 0.0,
            'availability': 0.0,
            'matching_skills': [],
            'missing_skills': [],
            'details': '',
        }
        
        # Skill matching
        job_skills = set()
        candidate_skills = set()
        
        if hasattr(job, 'required_skill_ids') and job.required_skill_ids:
            job_skills = set(job.required_skill_ids.mapped('name'))
        if hasattr(candidate, 'skill_ids') and candidate.skill_ids:
            candidate_skills = set(candidate.skill_ids.mapped('name'))
        
        if job_skills:
            matching = job_skills & candidate_skills
            scores['matching_skills'] = list(matching)
            scores['missing_skills'] = list(job_skills - candidate_skills)
            scores['skill'] = (len(matching) / len(job_skills)) * 100 if job_skills else 100
        else:
            scores['skill'] = 80  # Default if no skills specified
        
        # Experience matching
        required_exp = getattr(job, 'min_experience', 0) or 0
        candidate_exp = getattr(candidate, 'years_experience', 0) or 0
        
        if required_exp > 0:
            if candidate_exp >= required_exp:
                scores['experience'] = 100
            else:
                scores['experience'] = (candidate_exp / required_exp) * 100
        else:
            scores['experience'] = 80  # Default
        
        # Education matching (simplified)
        scores['education'] = 75  # Default score
        
        # Location matching
        job_location = getattr(job, 'location', '') or ''
        candidate_location = getattr(candidate, 'current_location', '') or ''
        
        if job_location and candidate_location:
            if job_location.lower() in candidate_location.lower() or candidate_location.lower() in job_location.lower():
                scores['location'] = 100
            else:
                scores['location'] = 50
        else:
            scores['location'] = 70  # Default
        
        # Salary matching
        job_salary_max = getattr(job, 'salary_max', 0) or 0
        candidate_expected = getattr(candidate, 'expected_salary', 0) or 0
        
        if job_salary_max > 0 and candidate_expected > 0:
            if candidate_expected <= job_salary_max:
                scores['salary'] = 100
            else:
                # Calculate how far over budget
                over_percentage = ((candidate_expected - job_salary_max) / job_salary_max) * 100
                scores['salary'] = max(0, 100 - over_percentage)
        else:
            scores['salary'] = 75  # Default
        
        # Availability matching
        scores['availability'] = 85  # Default - could be enhanced with actual availability data
        
        # Build details
        scores['details'] = (
            f"Skill Match: {scores['skill']:.1f}% ({len(scores['matching_skills'])} matching, "
            f"{len(scores['missing_skills'])} missing)\n"
            f"Experience: {scores['experience']:.1f}% ({candidate_exp} years vs {required_exp} required)\n"
            f"Education: {scores['education']:.1f}%\n"
            f"Location: {scores['location']:.1f}%\n"
            f"Salary: {scores['salary']:.1f}%\n"
            f"Availability: {scores['availability']:.1f}%"
        )
        
        return scores


# Add engine_run_id to AICandidateMatch
AICandidateMatch.engine_run_id = fields.Many2one(
    'ai.matching.engine',
    string='Matching Run',
    ondelete='set null',
)
