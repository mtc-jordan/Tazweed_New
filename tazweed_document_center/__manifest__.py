# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Document Management Center',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Staffing',
    'summary': 'Comprehensive Document Management with Expiry Tracking & Alerts',
    'description': """
Tazweed Document Management Center
==================================

A complete document management solution for HR and staffing operations with 
advanced expiry tracking, automated alerts, and compliance monitoring.

Key Features:
-------------
* Centralized Document Dashboard
* Multi-level Expiry Alerts (90/60/30/15/7/1 days)
* Automated Email Notifications
* Renewal Workflow Management
* Document Compliance Reports
* Bulk Actions (Mass Renewal, Notifications)
* Employee Compliance Status Tracking
* Mobile-friendly Interface

Document Types Tracked:
-----------------------
* Emirates ID
* Passport
* Work Visa
* Labour Card
* Medical Insurance
* Trade License
* Employment Contract
* Certificates & Qualifications
* Custom Document Types

Alert System:
-------------
* Dashboard Alerts with Color Coding
* Email Notifications to HR/Managers
* Employee Self-service Notifications
* Escalation Workflows
* Scheduled Reminder Cron Jobs

Compliance Features:
--------------------
* UAE Labor Law Compliance
* MOHRE Document Requirements
* Audit Trail & History
* Document Verification Status
* Expiry Analytics & Reports

Best Practices:
---------------
* Role-based Access Control
* Secure Document Storage
* Version Control
* Digital Signatures Integration
* Automated Backup
    """,
    'author': 'Tazweed HR Solutions',
    'website': 'https://www.tazweed.ae',
    'depends': [
        'base',
        'web',
        'mail',
        'hr',
        'tazweed_core',
    ],
    'data': [
        # Security
        'security/document_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/document_data.xml',
        'data/cron_data.xml',
        'data/email_templates.xml',
        # Views
        'views/document_dashboard_views.xml',
        'views/document_alert_views.xml',
        'views/document_renewal_views.xml',
        'views/document_compliance_views.xml',
        'views/wizard_views.xml',
        'views/hr_employee_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_document_center/static/src/css/document_dashboard.css',
            'tazweed_document_center/static/src/js/document_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
