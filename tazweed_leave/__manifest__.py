# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Leave & Attendance',
    'version': '16.0.2.0.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Leave Management and Attendance Tracking for UAE',
    'description': """
Tazweed Leave & Attendance Module
=================================

Comprehensive leave management and attendance tracking system with UAE compliance.

Leave Management:
-----------------
* Leave Types (Annual, Sick, Maternity, etc.)
* Leave Allocations
* Leave Requests and Approvals
* Leave Balance Tracking
* Leave Encashment
* Carry Forward Rules

UAE Specific:
-------------
* UAE Public Holidays
* UAE Labour Law Leave Entitlements
* Hajj Leave
* Maternity/Paternity Leave (UAE Law)
* Sick Leave Rules (UAE Law)

Attendance:
-----------
* Check-in/Check-out
* Attendance Tracking
* Late/Early Tracking
* Overtime Calculation
* Attendance Reports

Integration:
------------
* Payroll Integration
* Calendar Integration
* Employee Portal

Author: Tazweed HR Team
Website: https://tazweedjobs.ae
    """,
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae',
    'license': 'LGPL-3',
    'depends': [
        'tazweed_core',
        'hr_holidays',
        'hr_attendance',
    ],
    'data': [
        # Security
        'security/tazweed_leave_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/leave_type_data.xml',
        'data/public_holiday_data.xml',
        'data/leave_sequence_data.xml',
        # Views
        'views/hr_leave_type_views.xml',
        'views/hr_leave_views.xml',
        'views/hr_leave_allocation_views.xml',
        'views/hr_attendance_views.xml',
        'views/public_holiday_views.xml',
        'views/dashboard_views.xml',
        'views/menu.xml',
        # Wizards
        'wizard/wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_leave/static/src/css/leave.css',
            'tazweed_leave/static/src/css/leave_dashboard.css',
            'tazweed_leave/static/src/js/leave_dashboard.js',
            'tazweed_leave/static/src/xml/leave_dashboard.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 3,
}
