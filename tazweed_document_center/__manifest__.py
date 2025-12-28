# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Document Management Center',
    'version': '16.0.2.0.0',
    'category': 'Human Resources/Staffing',
    'summary': 'Central Document Hub with Cross-Module Integration & Expiry Tracking',
    'description': """
Tazweed Document Management Center
==================================

A complete document management solution serving as the central hub for all HR 
documents across modules with advanced expiry tracking, automated alerts, and 
compliance monitoring.

Key Features:
-------------
* **Central Document Hub** - Aggregates documents from all HR modules
* **Cross-Module Integration** - Syncs with Core, Placement, Payroll, Leave, Performance
* **Multi-level Expiry Alerts** (90/60/30/15/7/1 days)
* **Automated Email Notifications**
* **Renewal Workflow Management**
* **Document Compliance Reports**
* **Bulk Actions** (Mass Renewal, Notifications)
* **Employee Compliance Status Tracking**
* **Version Control** - Track document versions
* **Verification Workflow** - Document verification status
* **Mobile-friendly Interface**

Document Categories:
--------------------
* Identity Documents (Passport, Emirates ID)
* Visa & Work Permits
* Contracts & Agreements
* Certificates & Qualifications
* Medical Documents
* Financial Documents
* Leave Documents
* Performance Documents

Source Modules:
---------------
* HR Core - Employee documents
* Placement - Candidate documents
* Payroll - Salary certificates, payslips
* Leave - Leave request documents
* Performance - Review documents
* Manual Upload - Direct uploads

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
        'views/unified_document_views.xml',
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
            'tazweed_document_center/static/src/xml/document_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
