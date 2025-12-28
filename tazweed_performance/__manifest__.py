# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Performance Management',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Performance',
    'summary': 'Comprehensive Performance Management System for Tazweed',
    'description': """
Tazweed Performance Management System
=====================================

Enterprise-grade performance management module with:

**Performance Reviews:**
- Annual/Semi-annual/Quarterly reviews
- Self-assessment
- Manager assessment
- 360-degree feedback
- Review templates

**Goal Management:**
- SMART goal setting
- Goal cascading
- Progress tracking
- Goal alignment
- Milestone tracking

**KPI Management:**
- KPI definition
- Target setting
- Actual tracking
- Variance analysis
- KPI dashboards

**Competency Framework:**
- Competency library
- Skill assessment
- Gap analysis
- Development recommendations

**Development Plans:**
- Individual development plans
- Training recommendations
- Career path planning
- Succession planning

**Feedback System:**
- Continuous feedback
- Recognition and rewards
- Peer feedback
- Manager feedback

**Analytics and Reporting:**
- Performance dashboards
- Trend analysis
- Team comparisons
- Export capabilities

Author: Tazweed HR Team
Website: https://tazweedjobs.ae
    """,
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae',
    'license': 'LGPL-3',
    'depends': [
        'tazweed_core',
        'hr',
        'mail',
    ],
    'data': [
        # Security
        'security/performance_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/performance_sequence.xml',
        'data/performance_data.xml',
        # Views - order matters for action references
        'views/performance_goal_views.xml',
        'views/competency_views.xml',
        'views/feedback_views.xml',
        'views/performance_review_views.xml',
        'views/dashboard_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_performance/static/src/css/performance.css',
            'tazweed_performance/static/src/css/performance_dashboard.css',
            'tazweed_performance/static/src/js/performance_dashboard.js',
            'tazweed_performance/static/src/xml/performance_dashboard.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 5,
}
