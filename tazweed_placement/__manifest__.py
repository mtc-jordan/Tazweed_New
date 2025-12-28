# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Placement & Recruitment',
    'version': '16.0.1.1.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Complete Recruitment and Placement Management for Staffing Business',
    'description': """
Tazweed Placement and Recruitment Module
========================================

Comprehensive recruitment and placement management for staffing/manpower business.

Features:
---------
* Client Management - Client companies, contacts, contracts
* Job Orders - Job requisitions with requirements
* Candidate Management - Candidate database with skills
* Placement Management - Placement tracking and billing
* Deployment Management - Site assignments and schedules
* Client Invoicing - Monthly invoice generation for clients
* Timesheet Integration - Support for timesheet-based billing
    """,
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
        'contacts',
    ],
    'data': [
        # Security
        'security/placement_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/placement_sequence.xml',
        'data/placement_data.xml',
        # Views - order matters for action references
        'views/placement_views.xml',
        'views/job_order_views.xml',
        'views/candidate_views.xml',
        'views/client_views.xml',
        'views/client_invoice_views.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 4,
}
