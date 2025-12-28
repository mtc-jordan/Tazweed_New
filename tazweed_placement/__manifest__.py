# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Placement & Recruitment',
    'version': '16.0.2.0.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Complete Recruitment and Placement Management for Staffing Business',
    'description': """
Tazweed Placement and Recruitment Module v2.0
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

What's New in v2.0:
-------------------
* Modern OWL dashboard with Chart.js
* Recruitment pipeline with kanban view
* Interview scheduling and management
* Candidate-job matching algorithm
* Enhanced UI/UX with modern styling
* Calendar integration for interviews
* Improved reporting and analytics
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
        # Views
        'views/candidate_views.xml',
        'views/client_views.xml',
        'views/job_order_views.xml',
        'views/pipeline_views.xml',
        'views/interview_views.xml',
        'views/placement_views.xml',
        'views/wizard_views.xml',
        'views/dashboard_views.xml',
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
