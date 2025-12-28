{
    'name': 'Tazweed Advanced Analytics & Reporting',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Analytics',
    'summary': 'Advanced reporting and analytics with stunning dashboards for HR and Payroll',
    'description': '''
Tazweed Advanced Analytics & Reporting Module
==============================================

Comprehensive analytics and reporting solution with modern, interactive dashboards.

Features:
---------
* Payroll Analytics Dashboard
* Compliance Analytics Dashboard
* Performance Analytics Dashboard
* Employee Analytics Dashboard
* Advanced Reports with Export
* Interactive Visualizations
    ''',
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae/',
    'depends': [
        'base',
        'hr',
        'web',
        'mail',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/analytics_data.xml',
        # Views
        'views/payroll_analytics_views.xml',
        'views/compliance_analytics_views.xml',
        'views/performance_analytics_views.xml',
        'views/employee_analytics_views.xml',
        'views/dashboard_views.xml',
        'views/report_generator_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_advanced_analytics/static/src/css/analytics_dashboard.css',
            'tazweed_advanced_analytics/static/src/css/analytics_cards.css',
            'tazweed_advanced_analytics/static/src/css/analytics_charts.css',
            'tazweed_advanced_analytics/static/src/js/analytics_dashboard.js',
            'tazweed_advanced_analytics/static/src/js/analytics_charts.js',
            'tazweed_advanced_analytics/static/src/js/analytics_filters.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
