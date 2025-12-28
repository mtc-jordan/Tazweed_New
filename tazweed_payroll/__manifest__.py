# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Payroll',
    'version': '16.0.2.0.1',
    'category': 'Human Resources/Payroll',
    'summary': 'Enterprise Payroll Management for UAE with WPS Integration',
    'description': """
Tazweed Payroll Module
======================

Enterprise-grade payroll management system with UAE-specific features.
Full payroll functionality without requiring Odoo Enterprise.

Key Features:
-------------
* Salary Structure Management
* Salary Rules Engine
* Payslip Generation and Processing
* Batch Payroll Processing
* WPS (Wage Protection System) Integration
* Bank Transfer File Generation
* Overtime Calculation
* Deduction Management
* Allowance Management
* Loan Management
* End of Service Benefits (Gratuity)
* Leave Encashment
* Multi-currency Support
* Payroll Reports and Analytics

UAE Specific Features:
----------------------
* WPS File Generation (SIF Format)
* Emiratization Compliance
* MOHRE Reporting
* UAE Labour Law Compliance
* Gratuity Calculation (UAE Law)
* Leave Salary Calculation

Author: Tazweed HR Team
Website: https://tazweedjobs.ae
    """,
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae',
    'license': 'LGPL-3',
    'depends': [
        'tazweed_core',
        'tazweed_wps',
        'hr_contract',
    ],
    'data': [
        # Security
        'security/tazweed_payroll_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/payroll_sequence_data.xml',
        'data/salary_rule_category_data.xml',
        'data/salary_structure_data.xml',
        'data/salary_rule_data.xml',
        # Views
        'views/hr_salary_structure_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/payroll_loan_views.xml',
        'views/gratuity_views.xml',
        'views/wps_file_views.xml',
        'views/dashboard_views.xml',
        'views/menu.xml',
        # Wizards
        'wizard/wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_payroll/static/src/css/payroll.css',
            'tazweed_payroll/static/src/css/payroll_dashboard.css',
            'tazweed_payroll/static/src/js/payroll_dashboard.js',
            'tazweed_payroll/static/src/xml/payroll_dashboard.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 2,
}
