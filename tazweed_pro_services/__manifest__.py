# -*- coding: utf-8 -*-
{
    'name': 'Tazweed PRO Services',
    'version': '16.0.2.0.0',
    'category': 'Human Resources',
    'summary': 'UAE PRO (Public Relations Officer) Services Management - World Class Module',
    'description': """
Tazweed PRO Services Module - World Class Edition
==================================================

Comprehensive PRO Services management for UAE businesses including:

**Service Categories:**
- Visa Services (Employment, Family, Golden, Green, Investor)
- Residence Permit Management (New, Renewal, Cancellation)
- Emirates ID Services (Application, Renewal, Replacement)
- Labor/Work Permit Services (MOHRE)
- Trade License Services (New, Renewal, Amendment)
- Document Attestation & Translation
- Medical Services (Health Cards, Fitness Tests)
- Government Approvals & Compliance

**Key Features:**
- 📊 Amazing Dashboard with KPIs and Analytics
- 💰 Step-Level Fee Management with Receipt Attachments
- 📄 Auto-Invoice Generation with Government Receipts
- 👤 Employee Cost Integration (Auto-track PRO costs)
- ✅ Service Configuration with Steps and Required Documents
- 📋 Service Request Management (Internal & External Customers)
- ⏱️ Task Assignment and Workflow Management
- 🔗 Automatic Document Attachment from Employee Records
- 💵 Billing and Invoice Generation
- ⏰ SLA Tracking and Alerts
- 🏛️ Government Authority Integration
- 📈 Comprehensive Reporting

**Workflow:**
1. HR/Customer submits service request
2. PRO Manager assigns to PRO Officer
3. System auto-attaches available documents
4. PRO Officer processes through defined steps
5. Each step can have fees and receipt uploads
6. Receipts automatically attached to customer invoice
7. Fees automatically added to employee cost center
8. Billing generated upon completion
9. Customer notified of completion

    """,
    'author': 'Tazweed',
    'website': 'https://tazweedjobs.ae',
    'depends': [
        'base',
        'hr',
        'account',
        'contacts',
        'mail',
        'tazweed_core',
        'tazweed_document_center',
    ],
    'data': [
        # Security
        'security/pro_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/pro_sequence.xml',
        'data/pro_service_category_data.xml',
        'data/pro_government_authority_data.xml',
        'data/pro_document_type_data.xml',
        'data/pro_service_master_data.xml',
        'data/pro_service_steps_data.xml',
        'data/pro_service_documents_data.xml',
        # Views
        'views/pro_dashboard_views.xml',
        'views/pro_service_views.xml',
        'views/pro_service_category_views.xml',
        'views/pro_service_step_views.xml',
        'views/pro_service_request_views.xml',
        'views/pro_task_views.xml',
        'views/pro_customer_views.xml',
        'views/pro_government_authority_views.xml',
        'views/pro_document_type_views.xml',
        'views/pro_billing_views.xml',
        'views/hr_employee_views.xml',
        # Wizards
        'wizard/pro_request_wizard_views.xml',
        # Menu
        'views/menu.xml',
        # Reports
        'reports/pro_service_report.xml',
        'reports/pro_invoice_report.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_pro_services/static/src/css/pro_services.css',
            'tazweed_pro_services/static/src/css/pro_dashboard.css',
            'tazweed_pro_services/static/src/js/pro_dashboard.js',
            'tazweed_pro_services/static/src/xml/pro_dashboard.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
