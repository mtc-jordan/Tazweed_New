# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Integration',
    'version': '16.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Integration Layer for All Tazweed Modules',
    'description': """
Tazweed Integration Module
==========================

Central integration layer connecting all Tazweed HR modules.

Features:
---------
* Payroll Integration
    - Leave deductions
    - Attendance tracking
    - Performance bonuses
    - Loan deductions
    
* Compliance Integration
    - WPS payroll data
    - Emiratization reporting
    - Document compliance
    
* Placement Integration
    - Candidate to employee conversion
    - Placement payroll
    - Client billing
    
* Analytics Integration
    - Cross-module reporting
    - Unified dashboards
    - KPI tracking
    """,
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
    ],
    'data': [
        # Security
        'security/integration_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/integration_data.xml',
        # Views
        'views/integration_dashboard_views.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': 10,
}
