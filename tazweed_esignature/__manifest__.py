# -*- coding: utf-8 -*-
{
    'name': 'Tazweed E-Signature',
    'version': '16.0.2.0.0',
    'category': 'Human Resources/Signatures',
    'summary': 'Digital Document Signing with Modern OWL Dashboard',
    'description': """
Tazweed E-Signature Module
==========================

A comprehensive digital signature solution for Odoo 16 featuring:

**Key Features:**
- Modern OWL-based dashboard with real-time analytics
- Draw, type, or upload signatures
- Multi-signer document workflows
- Email notifications and reminders
- Audit trail and compliance tracking
- Mobile-responsive signature pad
- Template management
- Integration with HR and Contracts

**Technical Highlights:**
- Built with Odoo 16 OWL framework
- Modern UI/UX design
- Real-time updates
- Secure signature storage with hashing
    """,
    'author': 'Tazweed',
    'website': 'https://www.tazweed.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'hr',
        'hr_contract',
        'web',
    ],
    'data': [
        # Security
        'security/esignature_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/sequence_data.xml',
        'data/mail_template_data.xml',
        # Views
        'views/signature_template_views.xml',
        'views/signature_request_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # CSS
            'tazweed_esignature/static/src/css/esignature.css',
            # JS Components
            'tazweed_esignature/static/src/js/signature_pad.js',
            'tazweed_esignature/static/src/js/esignature_dashboard.js',
            # XML Templates
            'tazweed_esignature/static/src/xml/signature_pad.xml',
            'tazweed_esignature/static/src/xml/esignature_dashboard.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/banner.png'],
}
