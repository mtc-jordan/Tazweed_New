# -*- coding: utf-8 -*-
{
    'name': 'Tazweed WPS - Wage Protection System',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'UAE Wage Protection System (WPS) Management',
    'description': """
Tazweed WPS - Wage Protection System
====================================

Comprehensive UAE WPS management module providing:

Features:
---------
* SIF (Salary Information File) Generation
* UAE Bank Registry with routing codes
* Employee salary line management
* WPS compliance tracking and reporting
* Bank submission workflow
* Integration with payroll and HR modules

UAE Compliance:
---------------
* Central Bank of UAE WPS format
* All UAE bank routing codes
* Automated SIF file generation
* Compliance rate monitoring
    """,
    'author': 'Tazweed',
    'website': 'https://www.tazweed.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'mail',
        'tazweed_core',
    ],
    'data': [
        # Security
        'security/wps_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/sequence_data.xml',
        'data/uae_banks_data.xml',
        
        # Views
        'views/wps_line_views.xml',
        'views/wps_file_views.xml',
        'views/wps_compliance_views.xml',
        'views/wps_bank_views.xml',
        'views/wps_dashboard_views.xml',
        'views/wps_bank_api_views.xml',
        'views/wps_validation_views.xml',
        'views/wps_reconciliation_views.xml',
        'views/menu_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_wps/static/src/js/wps_dashboard.js',
            'tazweed_wps/static/src/xml/wps_dashboard.xml',
            'tazweed_wps/static/src/css/wps_dashboard.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 5,
}
