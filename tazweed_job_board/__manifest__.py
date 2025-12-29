# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Job Board Integration',
    'version': '16.0.2.0.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Multi-channel job posting and candidate sourcing from major job boards',
    'description': """
Tazweed Job Board Integration
=============================

Comprehensive job board integration module for UAE staffing companies.

Key Features:
-------------
* Multi-Board Job Posting
    - Post to LinkedIn, Indeed, Bayt, GulfTalent, Naukrigulf
    - One-click syndication to multiple boards
    - Automatic sync of job updates
    
* LinkedIn Integration (NEW)
    - Direct LinkedIn API integration
    - Post jobs directly to LinkedIn
    - Import candidate applications
    - Track engagement metrics
    
* Indeed/Bayt Integration (NEW)
    - Multi-platform job posting
    - Sponsored job support
    - Budget management
    - Performance analytics
    
* AI Resume Scoring (NEW)
    - Automatic resume scoring
    - Skills matching
    - Experience analysis
    - Recommendation engine
    
* Candidate Sourcing
    - Import candidates from job boards
    - LinkedIn profile integration
    - Resume parsing and data extraction
    - Duplicate detection
    
* Analytics Dashboard
    - Source performance tracking
    - Cost-per-hire analysis
    - Time-to-fill metrics
    - ROI by channel
    
* Job Templates
    - Reusable job templates
    - Industry-specific templates
    - Compliance-ready descriptions
    
* Automation
    - Scheduled posting
    - Auto-refresh listings
    - Expiry management
    - Budget optimization

Supported Job Boards:
--------------------
* LinkedIn (Global)
* Indeed (Global)
* Bayt.com (MENA)
* GulfTalent (GCC)
* Naukrigulf (GCC)
* Monster Gulf (GCC)
* Dubizzle (UAE)
    """,
    'author': 'Tazweed HR Solutions',
    'website': 'https://www.tazweed.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'hr',
        'hr_recruitment',
    ],
    'data': [
        # Security
        'security/job_board_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/job_board_data.xml',
        'data/cron_data.xml',
        # Views
        'views/job_board_views.xml',
        'views/job_posting_views.xml',
        'views/job_template_views.xml',
        'views/candidate_source_views.xml',
        'views/analytics_views.xml',
        'views/wizard_views.xml',
        'views/dashboard_views.xml',
        'views/menu.xml',
        # New Feature Views
        'views/linkedin_integration_views.xml',
        'views/indeed_bayt_integration_views.xml',
        'views/ai_resume_scoring_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_job_board/static/src/css/dashboard.css',
            'tazweed_job_board/static/src/js/dashboard.js',
            'tazweed_job_board/static/src/xml/dashboard.xml',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
