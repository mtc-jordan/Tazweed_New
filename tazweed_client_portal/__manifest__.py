# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Client Portal',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Staffing',
    'summary': 'Self-service client portal for staffing agency clients',
    'description': """
Tazweed Client Portal
=====================

A modern, feature-rich self-service portal for staffing agency clients.

Key Features:
-------------
* Personalized client dashboard with real-time KPIs
* Job order management (create, view, track)
* Candidate review and approval workflow
* Placement tracking and status updates
* Invoice and payment management
* Document sharing and collaboration
* Real-time messaging and notifications
* Mobile-responsive design
* White-label branding support

Best Practices Implemented:
---------------------------
* Role-based access control (RBAC)
* Secure document sharing with audit trails
* Real-time status tracking
* Integrated communication channels
* Advanced analytics for clients
* Mobile-first responsive design
    """,
    'author': 'Tazweed HR Solutions',
    'website': 'https://www.tazweed.ae',
    'depends': [
        'base',
        'mail',
        'portal',
        'website',
    ],
    'data': [
        'security/client_portal_security.xml',
        'security/ir.model.access.csv',
        'data/portal_data.xml',
        'data/email_templates.xml',
        'views/client_portal_views.xml',
        'views/portal_templates.xml',
        'views/portal_dashboard.xml',
        'views/portal_job_order.xml',
        'views/portal_candidate.xml',
        'views/portal_placement.xml',
        'views/portal_invoice.xml',
        'views/portal_document.xml',
        'views/portal_message.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'tazweed_client_portal/static/src/css/portal.css',
            'tazweed_client_portal/static/src/js/portal.js',
            'tazweed_client_portal/static/src/js/charts.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
