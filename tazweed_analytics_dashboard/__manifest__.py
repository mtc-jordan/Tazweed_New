# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Analytics Dashboard',
    'version': '16.0.2.0.0',
    'category': 'Human Resources/Staffing',
    'summary': 'Advanced HR & Staffing Analytics with Interactive Dashboards',
    'description': """
Tazweed Analytics Dashboard
===========================

A comprehensive analytics and business intelligence solution for HR and staffing operations.

Key Features:
-------------
* Executive Dashboard with real-time KPIs
* Workforce Analytics & Demographics
* Payroll Analytics & Cost Analysis
* Recruitment & Placement Metrics
* Client Profitability Analysis
* Compliance & Emiratization Tracking
* Predictive Analytics & Trends
* Custom Report Builder
* Export to Excel/PDF
* Scheduled Email Reports

Dashboard Types:
----------------
* Executive Summary Dashboard
* HR Operations Dashboard
* Payroll & Finance Dashboard
* Recruitment Pipeline Dashboard
* Client Performance Dashboard
* Compliance Dashboard
* Employee Cost Center Dashboard
* Employee Lifecycle Dashboard

KPIs Tracked:
-------------
* Headcount & Turnover Rate
* Time-to-Hire & Cost-per-Hire
* Revenue per Employee
* Payroll Cost Ratio
* Placement Fill Rate
* Client Satisfaction Score
* Emiratization Percentage
* Leave Utilization Rate
* Training Hours per Employee
* Contract Renewal Rate
* Document Compliance Rate

Best Practices:
---------------
* Real-time data refresh
* Drill-down capabilities
* Mobile-responsive design
* Role-based access control
* Scheduled report delivery
* Data visualization best practices
    """,
    'author': 'Tazweed HR Solutions',
    'website': 'https://www.tazweed.ae',
    'depends': [
        'base',
        'web',
        'hr',
        'mail',
    ],
    'data': [
        'security/analytics_security.xml',
        'security/ir.model.access.csv',
        'data/analytics_data.xml',
        'data/kpi_data.xml',
        'views/dashboard_views.xml',
        'views/kpi_views.xml',
        'views/report_views.xml',
        'views/cost_center_views.xml',
        'views/recruitment_dashboard_views.xml',
        'views/compliance_dashboard_views.xml',
        'views/payroll_dashboard_views.xml',
        'views/scheduled_report_views.xml',
        'views/graph_views.xml',
        'views/dashboard_widgets_views.xml',
        'views/notification_alerts_views.xml',
        'views/menu.xml',
        'data/scheduled_report_cron.xml',
        'data/email_templates.xml',
        'data/notification_alerts_cron.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_analytics_dashboard/static/src/css/dashboard.css',
            'tazweed_analytics_dashboard/static/src/js/dashboard.js',
            'tazweed_analytics_dashboard/static/lib/chart.min.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
