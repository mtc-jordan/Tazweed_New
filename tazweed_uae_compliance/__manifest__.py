# -*- coding: utf-8 -*-
{
    'name': 'Tazweed UAE Compliance Engine',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Compliance',
    'summary': 'UAE Labour Law Compliance, WPS, Emiratization, MOHRE Integration',
    'description': """
Tazweed UAE Compliance Engine
=============================

Comprehensive UAE labour law compliance management system.

Features:
---------
* WPS (Wage Protection System)
    - SIF file generation
    - Bank integration
    - Payment tracking
    - Compliance reporting
    
* Emiratization
    - UAE national tracking
    - Quota management
    - Compliance monitoring
    - Penalty calculation
    
* MOHRE Integration
    - Labour contract registration
    - Work permit management
    - Establishment reporting
    - Inspection tracking
    
* Document Compliance
    - Visa tracking
    - Labour card management
    - Emirates ID tracking
    - Expiry alerts
    
* Gratuity Management
    - End of service calculation
    - UAE Labour Law compliance
    - Provision tracking
    """,
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'mail',
        'tazweed_wps',
    ],
    'data': [
        # Security
        'security/compliance_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/compliance_data.xml',
        # Views
        'views/wps_views.xml',
        'views/emiratization_views.xml',
        'views/mohre_views.xml',
        'views/document_compliance_views.xml',
        'views/menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 5,
}
