# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Employee Portal',
    'version': '16.0.2.0.0',
    'category': 'Human Resources/Employee',
    'summary': 'Employee Self-Service Portal with HR Service Requests',
    'description': """
Tazweed Employee Self-Service Portal
====================================

Comprehensive employee self-service portal for HR operations.

Features:
---------
* Employee Dashboard
* Leave Request Submission
* Leave Balance View
* Attendance Check-in/Check-out
* Payslip Viewing
* Document Management
* Profile Management
* Loan Requests
* Expense Claims
* Announcements

HR Service Requests:
--------------------
* Salary Certificate Request
* Experience Letter Request
* No Objection Certificate (NOC)
* Bank Letter Request
* Embassy/Visa Support Letter
* Employment Contract Copy
* Payslip Copy Request
* Name Change Request
* Bank Account Change
* Dependent Addition
* Insurance Card Request
* Salary Advance Request
* Employee Loan Request
* Expense Reimbursement
* And many more...

Workflow Features:
------------------
* Easy request submission
* Manager approval workflow
* HR approval workflow
* SLA tracking
* Email notifications
* Document generation
* Request tracking

Portal Features:
----------------
* Mobile-responsive design
* Real-time notifications
* Document upload/download
* Manager approvals
* Team calendar view

Author: Tazweed HR Team
Website: https://tazweedjobs.ae
    """,
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae',
    'license': 'LGPL-3',
    'depends': [
        'tazweed_core',
        'tazweed_leave',
        'portal',
        'website',
        'mail',
    ],
    'data': [
        # Security
        'security/portal_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/portal_data.xml',
        'data/hr_service_request_sequence.xml',
        'data/hr_service_request_type_data.xml',
        'data/hr_service_request_email_templates.xml',
        # Views
        'views/portal_templates.xml',
        'views/portal_dashboard.xml',
        'views/portal_leave.xml',
        'views/portal_attendance.xml',
        'views/portal_payslip.xml',
        'views/portal_document.xml',
        'views/dashboard_views.xml',
        'views/hr_service_request_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'tazweed_employee_portal/static/src/css/portal.css',
            'tazweed_employee_portal/static/src/js/portal.js',
        ],
        'web.assets_backend': [
            'tazweed_employee_portal/static/src/css/employee_dashboard.css',
            'tazweed_employee_portal/static/src/js/employee_dashboard.js',
            'tazweed_employee_portal/static/src/xml/employee_dashboard.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 4,
}
