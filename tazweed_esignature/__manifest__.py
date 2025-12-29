# -*- coding: utf-8 -*-
{
    'name': 'Tazweed E-Signature',
    'version': '16.0.4.0.0',
    'category': 'Human Resources/Signatures',
    'summary': 'Digital Document Signing with UAE Compliance',
    'description': """
Tazweed E-Signature Module
==========================

A comprehensive digital signature solution for Odoo 16 with UAE compliance features.

**Key Features:**
- Modern OWL-based dashboard with real-time analytics
- Draw, type, or upload signatures
- Multi-signer document workflows with sequential/parallel signing
- Email notifications and automated reminders
- Audit trail and compliance tracking
- Mobile-responsive signature pad
- Template management with signature placement
- Integration with HR, Contracts, and Document Center
- UAE e-signature law compliance
- Signature certificate generation
- Bulk document signing

**Document Types Supported:**
- Employment Contracts
- Offer Letters
- Non-Disclosure Agreements
- Policy Acknowledgments
- Termination Letters
- Contract Amendments
- Visa Documents
- Labor Cards
- End of Service Settlements
- Warning Letters
- Promotion Letters
- Salary Certificates

**Technical Highlights:**
- Built with Odoo 16 OWL framework
- Modern UI/UX design
- Real-time updates
- Secure signature storage with SHA-256 hashing
- IP and device tracking for audit
- Automated expiry and reminder cron jobs

NEW FEATURES (v4.0.0)
=====================

**Bulk Signing:**
- Send same document to multiple signers
- Process different documents in bulk
- Template-based document generation
- CSV import for signers
- Progress tracking and statistics

**Signing Order Workflows:**
- Sequential and parallel signing
- Hybrid workflows with groups
- Conditional signing based on rules
- Signer delegation support
- Escalation rules

**Signature Verification:**
- Document integrity verification
- Signature authenticity check
- Certificate validation
- QR code generation
- Verification reports
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
        'tazweed_core',
    ],
    'data': [
        # Security
        'security/esignature_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/sequence_data.xml',
        'data/mail_template_data.xml',
        'data/document_type_data.xml',
        'data/esignature_cron.xml',
        # Views
        'views/signature_template_views.xml',
        'views/signature_request_views.xml',
        'views/signature_certificate_views.xml',
        # New Feature Views
        'views/bulk_signing_views.xml',
        'views/signing_order_views.xml',
        'views/signature_verification_views.xml',
        # Wizards (before menu)
        'wizard/send_for_signature_views.xml',
        'wizard/bulk_signature_views.xml',
        # Menu (last)
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
