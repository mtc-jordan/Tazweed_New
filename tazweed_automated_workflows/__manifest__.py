{
    'name': 'Tazweed Automated Workflows & Scheduling',
    'version': '16.0.1.0.0',
    'category': 'Human Resources/Automation',
    'summary': 'Automated workflows, scheduling, and task automation for HR and Payroll',
    'description': '''
Tazweed Automated Workflows & Scheduling Module
================================================

Comprehensive automation and scheduling solution for HR and Payroll processes.

Features:
---------
* Workflow Automation
* Task Scheduling
* Approval Workflows
* Notifications & Alerts
* Automation Rules
* Scheduled Reports
    ''',
    'author': 'Tazweed HR Team',
    'website': 'https://tazweedjobs.ae/',
    'depends': [
        'base',
        'hr',
        'mail',
    ],
    'data': [
        # Security
        'security/workflow_security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/workflow_data.xml',
        # Views
        'views/workflow_definition_views.xml',
        'views/workflow_instance_views.xml',
        'views/automation_rule_views.xml',
        'views/scheduled_task_views.xml',
        'views/approval_workflow_views.xml',
        'views/notification_template_views.xml',
        'views/workflow_trigger_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_automated_workflows/static/src/css/workflow_dashboard.css',
            'tazweed_automated_workflows/static/src/js/workflow_dashboard.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
