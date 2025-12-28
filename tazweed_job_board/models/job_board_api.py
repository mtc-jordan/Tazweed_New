# -*- coding: utf-8 -*-

import logging
import json
import requests
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class JobBoardAPIConnector(models.AbstractModel):
    """Base class for job board API connectors"""
    _name = 'job.board.api.connector'
    _description = 'Job Board API Connector Base'

    @api.model
    def get_connector(self, board_type):
        """Factory method to get the appropriate connector"""
        connectors = {
            'linkedin': LinkedInConnector,
            'indeed': IndeedConnector,
            'bayt': BaytConnector,
            'gulftalent': GulfTalentConnector,
            'naukrigulf': NaukriGulfConnector,
            'monster': MonsterConnector,
            'dubizzle': DubizzleConnector,
            'glassdoor': GlassdoorConnector,
        }
        return connectors.get(board_type)

    def _make_request(self, method, url, headers=None, data=None, params=None):
        """Make HTTP request with error handling"""
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            _logger.error(f"API request failed: {str(e)}")
            raise UserError(_("API request failed: %s") % str(e))


class LinkedInConnector:
    """LinkedIn Jobs API Connector"""
    
    BASE_URL = "https://api.linkedin.com/v2"
    
    def __init__(self, api_key, api_secret, access_token):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
    
    def post_job(self, job_data):
        """Post a job to LinkedIn"""
        url = f"{self.BASE_URL}/simpleJobPostings"
        
        payload = {
            "externalJobPostingId": job_data.get('external_id'),
            "title": job_data.get('title'),
            "description": {
                "text": job_data.get('description')
            },
            "location": {
                "country": job_data.get('country', 'AE'),
                "city": job_data.get('city', 'Dubai')
            },
            "listedAt": int(datetime.now().timestamp() * 1000),
            "jobPostingOperationType": "CREATE",
            "companyApplyUrl": job_data.get('apply_url'),
            "employmentStatus": self._map_employment_type(job_data.get('employment_type')),
            "experienceLevel": self._map_experience_level(job_data.get('experience_level')),
        }
        
        if job_data.get('salary_min') and job_data.get('salary_max'):
            payload["salaryRange"] = {
                "min": {"amount": job_data['salary_min'], "currencyCode": "AED"},
                "max": {"amount": job_data['salary_max'], "currencyCode": "AED"}
            }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def update_job(self, external_id, job_data):
        """Update an existing job posting"""
        job_data['external_id'] = external_id
        return self.post_job(job_data)
    
    def close_job(self, external_id):
        """Close/expire a job posting"""
        url = f"{self.BASE_URL}/simpleJobPostings"
        payload = {
            "externalJobPostingId": external_id,
            "jobPostingOperationType": "CLOSE"
        }
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def get_applications(self, job_id, since_date=None):
        """Get applications for a job"""
        url = f"{self.BASE_URL}/jobApplications"
        params = {"jobId": job_id}
        if since_date:
            params['modifiedSince'] = int(since_date.timestamp() * 1000)
        
        response = requests.get(url, headers=self.headers, params=params)
        return self._handle_response(response)
    
    def _map_employment_type(self, emp_type):
        mapping = {
            'full_time': 'FULL_TIME',
            'part_time': 'PART_TIME',
            'contract': 'CONTRACT',
            'temporary': 'TEMPORARY',
            'internship': 'INTERNSHIP',
        }
        return mapping.get(emp_type, 'FULL_TIME')
    
    def _map_experience_level(self, level):
        mapping = {
            'entry': 'ENTRY_LEVEL',
            'associate': 'ASSOCIATE',
            'mid_senior': 'MID_SENIOR_LEVEL',
            'director': 'DIRECTOR',
            'executive': 'EXECUTIVE',
        }
        return mapping.get(level, 'MID_SENIOR_LEVEL')
    
    def _handle_response(self, response):
        if response.status_code in [200, 201]:
            return {'success': True, 'data': response.json() if response.content else {}}
        else:
            return {'success': False, 'error': response.text}


class IndeedConnector:
    """Indeed Jobs API Connector"""
    
    BASE_URL = "https://apis.indeed.com/v2"
    
    def __init__(self, api_key, employer_id):
        self.api_key = api_key
        self.employer_id = employer_id
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Indeed-Employer-Id': employer_id
        }
    
    def post_job(self, job_data):
        """Post a job to Indeed"""
        url = f"{self.BASE_URL}/jobs"
        
        payload = {
            "title": job_data.get('title'),
            "description": job_data.get('description'),
            "location": {
                "city": job_data.get('city', 'Dubai'),
                "country": job_data.get('country', 'AE'),
                "postalCode": job_data.get('postal_code', '')
            },
            "compensation": {
                "type": "SALARY",
                "range": {
                    "min": job_data.get('salary_min', 0),
                    "max": job_data.get('salary_max', 0),
                    "currency": "AED",
                    "period": "YEAR"
                }
            } if job_data.get('show_salary') else None,
            "employmentType": self._map_employment_type(job_data.get('employment_type')),
            "remoteType": self._map_remote_type(job_data.get('remote_type')),
            "applyUrl": job_data.get('apply_url'),
            "expiresAt": job_data.get('expiry_date'),
        }
        
        # Remove None values
        payload = {k: v for k, v in payload.items() if v is not None}
        
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def update_job(self, job_id, job_data):
        """Update an existing job"""
        url = f"{self.BASE_URL}/jobs/{job_id}"
        response = requests.put(url, headers=self.headers, json=job_data)
        return self._handle_response(response)
    
    def close_job(self, job_id):
        """Close a job posting"""
        url = f"{self.BASE_URL}/jobs/{job_id}"
        response = requests.delete(url, headers=self.headers)
        return self._handle_response(response)
    
    def get_analytics(self, job_id, date_range='30d'):
        """Get job posting analytics"""
        url = f"{self.BASE_URL}/jobs/{job_id}/analytics"
        params = {'dateRange': date_range}
        response = requests.get(url, headers=self.headers, params=params)
        return self._handle_response(response)
    
    def _map_employment_type(self, emp_type):
        mapping = {
            'full_time': 'FULLTIME',
            'part_time': 'PARTTIME',
            'contract': 'CONTRACT',
            'temporary': 'TEMPORARY',
            'internship': 'INTERN',
        }
        return mapping.get(emp_type, 'FULLTIME')
    
    def _map_remote_type(self, remote):
        mapping = {
            'onsite': 'ONSITE',
            'remote': 'REMOTE',
            'hybrid': 'HYBRID',
        }
        return mapping.get(remote, 'ONSITE')
    
    def _handle_response(self, response):
        if response.status_code in [200, 201, 204]:
            return {'success': True, 'data': response.json() if response.content else {}}
        else:
            return {'success': False, 'error': response.text}


class BaytConnector:
    """Bayt.com Jobs API Connector"""
    
    BASE_URL = "https://api.bayt.com/v1"
    
    def __init__(self, api_key, company_id):
        self.api_key = api_key
        self.company_id = company_id
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json',
        }
    
    def post_job(self, job_data):
        """Post a job to Bayt.com"""
        url = f"{self.BASE_URL}/jobs"
        
        payload = {
            "company_id": self.company_id,
            "title": job_data.get('title'),
            "description": job_data.get('description'),
            "requirements": job_data.get('requirements', ''),
            "location": {
                "country": "UAE",
                "city": job_data.get('city', 'Dubai'),
            },
            "job_type": self._map_job_type(job_data.get('employment_type')),
            "career_level": self._map_career_level(job_data.get('experience_level')),
            "education_level": job_data.get('education_level', 'bachelors'),
            "salary": {
                "min": job_data.get('salary_min'),
                "max": job_data.get('salary_max'),
                "currency": "AED",
                "hide": not job_data.get('show_salary', False)
            },
            "apply_url": job_data.get('apply_url'),
            "expires_at": job_data.get('expiry_date'),
            "industry": job_data.get('industry', 'other'),
            "skills": job_data.get('skills', []),
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def update_job(self, job_id, job_data):
        """Update an existing job"""
        url = f"{self.BASE_URL}/jobs/{job_id}"
        response = requests.put(url, headers=self.headers, json=job_data)
        return self._handle_response(response)
    
    def close_job(self, job_id):
        """Close a job posting"""
        url = f"{self.BASE_URL}/jobs/{job_id}/close"
        response = requests.post(url, headers=self.headers)
        return self._handle_response(response)
    
    def refresh_job(self, job_id):
        """Refresh/bump a job posting"""
        url = f"{self.BASE_URL}/jobs/{job_id}/refresh"
        response = requests.post(url, headers=self.headers)
        return self._handle_response(response)
    
    def get_applications(self, job_id, page=1, per_page=50):
        """Get applications for a job"""
        url = f"{self.BASE_URL}/jobs/{job_id}/applications"
        params = {'page': page, 'per_page': per_page}
        response = requests.get(url, headers=self.headers, params=params)
        return self._handle_response(response)
    
    def search_candidates(self, query, filters=None):
        """Search candidate database"""
        url = f"{self.BASE_URL}/candidates/search"
        payload = {
            "query": query,
            "filters": filters or {},
            "page": 1,
            "per_page": 50
        }
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def _map_job_type(self, emp_type):
        mapping = {
            'full_time': 'full-time',
            'part_time': 'part-time',
            'contract': 'contract',
            'temporary': 'temporary',
            'internship': 'internship',
        }
        return mapping.get(emp_type, 'full-time')
    
    def _map_career_level(self, level):
        mapping = {
            'entry': 'entry-level',
            'junior': 'junior',
            'mid': 'mid-level',
            'senior': 'senior',
            'manager': 'manager',
            'director': 'director',
            'executive': 'executive',
        }
        return mapping.get(level, 'mid-level')
    
    def _handle_response(self, response):
        if response.status_code in [200, 201]:
            return {'success': True, 'data': response.json() if response.content else {}}
        else:
            return {'success': False, 'error': response.text}


class GulfTalentConnector:
    """GulfTalent Jobs API Connector"""
    
    BASE_URL = "https://api.gulftalent.com/v1"
    
    def __init__(self, api_key, employer_id):
        self.api_key = api_key
        self.employer_id = employer_id
        self.headers = {
            'Authorization': f'ApiKey {api_key}',
            'Content-Type': 'application/json',
        }
    
    def post_job(self, job_data):
        """Post a job to GulfTalent"""
        url = f"{self.BASE_URL}/employers/{self.employer_id}/jobs"
        
        payload = {
            "title": job_data.get('title'),
            "description": job_data.get('description'),
            "requirements": job_data.get('requirements', ''),
            "benefits": job_data.get('benefits', ''),
            "country": "AE",
            "city": job_data.get('city', 'Dubai'),
            "employment_type": job_data.get('employment_type', 'full_time'),
            "experience_years_min": job_data.get('experience_min', 0),
            "experience_years_max": job_data.get('experience_max', 10),
            "salary_min": job_data.get('salary_min'),
            "salary_max": job_data.get('salary_max'),
            "salary_currency": "AED",
            "salary_hidden": not job_data.get('show_salary', False),
            "apply_url": job_data.get('apply_url'),
            "expiry_date": job_data.get('expiry_date'),
            "featured": job_data.get('is_featured', False),
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def update_job(self, job_id, job_data):
        """Update an existing job"""
        url = f"{self.BASE_URL}/employers/{self.employer_id}/jobs/{job_id}"
        response = requests.put(url, headers=self.headers, json=job_data)
        return self._handle_response(response)
    
    def close_job(self, job_id):
        """Close a job posting"""
        url = f"{self.BASE_URL}/employers/{self.employer_id}/jobs/{job_id}"
        response = requests.delete(url, headers=self.headers)
        return self._handle_response(response)
    
    def get_applications(self, job_id):
        """Get applications for a job"""
        url = f"{self.BASE_URL}/employers/{self.employer_id}/jobs/{job_id}/applications"
        response = requests.get(url, headers=self.headers)
        return self._handle_response(response)
    
    def _handle_response(self, response):
        if response.status_code in [200, 201]:
            return {'success': True, 'data': response.json() if response.content else {}}
        else:
            return {'success': False, 'error': response.text}


class NaukriGulfConnector:
    """NaukriGulf Jobs API Connector"""
    
    BASE_URL = "https://api.naukrigulf.com/v1"
    
    def __init__(self, api_key, company_id):
        self.api_key = api_key
        self.company_id = company_id
        self.headers = {
            'X-Api-Key': api_key,
            'Content-Type': 'application/json',
        }
    
    def post_job(self, job_data):
        """Post a job to NaukriGulf"""
        url = f"{self.BASE_URL}/jobs"
        
        payload = {
            "company_id": self.company_id,
            "title": job_data.get('title'),
            "description": job_data.get('description'),
            "location": job_data.get('city', 'Dubai'),
            "country": "UAE",
            "job_type": job_data.get('employment_type', 'full_time'),
            "experience": f"{job_data.get('experience_min', 0)}-{job_data.get('experience_max', 10)} years",
            "salary_from": job_data.get('salary_min'),
            "salary_to": job_data.get('salary_max'),
            "apply_link": job_data.get('apply_url'),
            "valid_till": job_data.get('expiry_date'),
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def _handle_response(self, response):
        if response.status_code in [200, 201]:
            return {'success': True, 'data': response.json() if response.content else {}}
        else:
            return {'success': False, 'error': response.text}


class MonsterConnector:
    """Monster Gulf Jobs API Connector"""
    
    BASE_URL = "https://api.monster.com/v1"
    
    def __init__(self, api_key, account_id):
        self.api_key = api_key
        self.account_id = account_id
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
    
    def post_job(self, job_data):
        """Post a job to Monster"""
        url = f"{self.BASE_URL}/jobs"
        
        payload = {
            "accountId": self.account_id,
            "jobTitle": job_data.get('title'),
            "jobDescription": job_data.get('description'),
            "location": {
                "city": job_data.get('city', 'Dubai'),
                "country": "AE"
            },
            "employmentType": job_data.get('employment_type', 'FULL_TIME'),
            "applyUrl": job_data.get('apply_url'),
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def _handle_response(self, response):
        if response.status_code in [200, 201]:
            return {'success': True, 'data': response.json() if response.content else {}}
        else:
            return {'success': False, 'error': response.text}


class DubizzleConnector:
    """Dubizzle Jobs API Connector"""
    
    BASE_URL = "https://api.dubizzle.com/v1"
    
    def __init__(self, api_key, user_id):
        self.api_key = api_key
        self.user_id = user_id
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json',
        }
    
    def post_job(self, job_data):
        """Post a job to Dubizzle"""
        url = f"{self.BASE_URL}/classifieds/jobs"
        
        payload = {
            "user_id": self.user_id,
            "title": job_data.get('title'),
            "description": job_data.get('description'),
            "category": "jobs",
            "subcategory": job_data.get('job_category', 'other'),
            "city": job_data.get('city', 'dubai'),
            "employment_type": job_data.get('employment_type', 'full_time'),
            "salary": {
                "min": job_data.get('salary_min'),
                "max": job_data.get('salary_max'),
            } if job_data.get('show_salary') else None,
            "contact_email": job_data.get('contact_email'),
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def _handle_response(self, response):
        if response.status_code in [200, 201]:
            return {'success': True, 'data': response.json() if response.content else {}}
        else:
            return {'success': False, 'error': response.text}


class GlassdoorConnector:
    """Glassdoor Jobs API Connector"""
    
    BASE_URL = "https://api.glassdoor.com/v1"
    
    def __init__(self, partner_id, api_key):
        self.partner_id = partner_id
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Basic {base64.b64encode(f"{partner_id}:{api_key}".encode()).decode()}',
            'Content-Type': 'application/json',
        }
    
    def post_job(self, job_data):
        """Post a job to Glassdoor"""
        url = f"{self.BASE_URL}/jobs"
        
        payload = {
            "jobTitle": job_data.get('title'),
            "jobDescription": job_data.get('description'),
            "location": {
                "city": job_data.get('city', 'Dubai'),
                "country": "United Arab Emirates"
            },
            "employmentType": job_data.get('employment_type', 'FULL_TIME'),
            "applyUrl": job_data.get('apply_url'),
        }
        
        response = requests.post(url, headers=self.headers, json=payload)
        return self._handle_response(response)
    
    def _handle_response(self, response):
        if response.status_code in [200, 201]:
            return {'success': True, 'data': response.json() if response.content else {}}
        else:
            return {'success': False, 'error': response.text}
