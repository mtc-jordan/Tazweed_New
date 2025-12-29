# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Client Portal',
    'version': '16.0.3.0.0',
    'category': 'Human Resources/Staffing',
    'summary': 'Enhanced self-service client portal for staffing agency clients with comprehensive features',
    'description': """
Tazweed Client Portal - Enhanced Edition
========================================

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

NEW - Enhanced Dashboard:
-------------------------
* Interactive charts with Chart.js
* Real-time data refresh
* Customizable widgets
* Financial summary section
* Pending actions overview
* Recent activity timeline

NEW - Employee Management:
--------------------------
* View all assigned employees
* Employee attendance tracking
* Performance metrics
* Document expiry alerts
* Compliance status monitoring

NEW - Client Request System:
----------------------------
* 35+ pre-configured request types
* Quick action buttons for common requests
* Request tracking timeline
* Bulk request actions
* SLA tracking and escalation management
* Email notifications for all request stages
* Client satisfaction rating and feedback

NEW - Reporting & Analytics:
----------------------------
* Downloadable reports (PDF/Excel)
* Custom date range filters
* Trend analysis
* Workforce summary reports
* Financial summary reports

NEW - UI/UX Improvements:
-------------------------
* Modern card-based design
* Dark mode support
* Mobile-responsive improvements
* Notification center
* Loading states and animations

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
        'data/client_request_sequence.xml',
        'data/client_request_type_data.xml',
        'data/client_request_email_templates.xml',
        'views/client_portal_views.xml',
        'views/client_request_views.xml',
        'views/portal_templates.xml',
        'views/portal_dashboard.xml',
        'views/portal_job_order.xml',
        'views/portal_candidate.xml',
        'views/portal_placement.xml',
        'views/portal_invoice.xml',
        'views/portal_document.xml',
        'views/portal_message.xml',
        'views/portal_enhanced_templates.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'tazweed_client_portal/static/src/css/portal.css',
            'tazweed_client_portal/static/src/css/portal_enhanced.css',
            'tazweed_client_portal/static/src/js/portal.js',
            'tazweed_client_portal/static/src/js/charts.js',
            'tazweed_client_portal/static/src/js/portal_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
