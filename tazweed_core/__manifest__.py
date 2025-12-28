# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Core HR',
    'version': '16.0.2.1.0',
    'category': 'Human Resources',
    'summary': 'Core HR Management for UAE Manpower Companies',
    'description': """
Tazweed Core HR Module
======================
A comprehensive HR management solution designed for UAE manpower companies.

Features:
---------
* Modern OWL Dashboard with real-time KPIs
* Employee management with UAE-specific fields
* Document management with expiry tracking
* Bank account management
* Sponsor/Company management with visa quota
* Contract extensions with allowances
* Beautiful, responsive UI/UX design
    """,
    'author': 'Tazweed',
    'website': 'https://www.tazweed.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'mail',
        'contacts',
    ],
    'data': [
        'security/tazweed_core_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/document_type_data.xml',
        'data/employee_category_data.xml',
        'views/hr_employee_views.xml',
        'views/employee_document_views.xml',
        'views/employee_bank_views.xml',
        'views/employee_sponsor_views.xml',
        'views/employee_category_views.xml',
        'views/document_type_views.xml',
        'views/dashboard_views.xml',
        'views/menu.xml',
        'wizard/document_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # External libraries
            ('include', 'web._assets_helpers'),
            'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js',
            # Styles
            'tazweed_core/static/src/scss/dashboard.scss',
            'tazweed_core/static/src/css/tazweed_core.css',
            # OWL Components
            'tazweed_core/static/src/js/tazweed_dashboard.js',
            'tazweed_core/static/src/xml/dashboard_template.xml',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 1,
}
