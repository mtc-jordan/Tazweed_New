# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Placement & Recruitment',
    'version': '16.0.3.0.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Complete Recruitment and Placement Management with AI Matching & Forecasting',
    'description': """
Tazweed Placement and Recruitment Module v3.0
==============================================

Comprehensive recruitment and placement management for staffing/manpower business.

Key Features:
-------------
* **Client Management** - Client companies, contacts, contracts, rate cards
* **Job Orders** - Job requisitions with detailed requirements
* **Candidate Management** - Full candidate database with skills & experience
* **Recruitment Pipeline** - Visual kanban pipeline for tracking candidates
* **Interview Management** - Schedule and track interviews with feedback
* **Candidate Matching** - Automatic scoring based on job requirements
* **Placement Management** - Placement tracking with compensation details
* **Client Invoicing** - Invoice generation with VAT support
* **OWL Dashboard** - Modern dashboard with KPIs and analytics

What's New in v3.0:
-------------------
* **AI Candidate Matching** - Auto-match candidates to job requirements using AI-powered scoring
* **Video Interview Integration** - Schedule and conduct video interviews with Zoom, Teams, Meet
* **Offer Letter Generator** - Automated offer letter generation with e-signature integration
* **Placement Forecasting** - Predict placement needs based on historical trends and data analysis
* Enhanced interview templates with question banks
* Improved analytics and reporting
    """,
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/sequence_data.xml',
        'data/recruitment_stage_data.xml',
        # Views - Core
        'views/candidate_views.xml',
        'views/client_views.xml',
        'views/job_order_views.xml',
        'views/pipeline_views.xml',
        'views/interview_views.xml',
        'views/placement_views.xml',
        'views/wizard_views.xml',
        'views/dashboard_views.xml',
        # Views - New Features
        'views/ai_candidate_matching_views.xml',
        'views/video_interview_views.xml',
        'views/offer_letter_views.xml',
        'views/placement_forecasting_views.xml',
        # Menu
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_placement/static/src/scss/placement_dashboard.scss',
            'tazweed_placement/static/src/js/placement_dashboard.js',
            'tazweed_placement/static/src/xml/placement_dashboard.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 4,
}
