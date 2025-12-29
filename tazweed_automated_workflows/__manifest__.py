# -*- coding: utf-8 -*-
{
    'name': 'Tazweed Automated Workflows',
    'version': '16.0.3.0.0',
    'category': 'Human Resources/Automation',
    'summary': 'Smart HR Workflow Automation with AI-Powered Triggers & SLA Management',
    'description': '''
Tazweed Automated Workflows - Enterprise Edition
=================================================

World-class workflow automation platform for UAE HR operations with smart triggers,
SLA management, and comprehensive analytics.

🚀 KEY FEATURES
===============

📋 WORKFLOW ENGINE
------------------
• Visual workflow designer with drag-and-drop
• State machine with configurable transitions
• Parallel and sequential approval paths
• Dynamic routing based on conditions
• Version control for workflow definitions

⚡ SMART TRIGGERS
-----------------
• Event-based triggers (create, update, delete)
• Time-based triggers (scheduled, recurring)
• Condition-based triggers (field changes, thresholds)
• API triggers for external integrations
• Webhook support for real-time events

👥 APPROVAL MANAGEMENT
----------------------
• Multi-level approval chains
• Role-based and user-based approvers
• Delegation and substitution rules
• Auto-approval after timeout
• Bulk approval capabilities

⏰ SLA MANAGEMENT
-----------------
• Response time tracking
• Resolution time monitoring
• Escalation rules with multiple levels
• SLA breach notifications
• Performance analytics

📊 PRE-BUILT HR TEMPLATES
-------------------------
• Employee Onboarding Workflow
• Employee Offboarding Workflow
• Leave Request Approval
• Expense Claim Processing
• Salary Adjustment Request
• Promotion Workflow
• Transfer Request
• Probation Review
• Contract Renewal
• Performance Review Cycle
• Training Request
• Document Approval

🔔 NOTIFICATIONS
----------------
• Email notifications with templates
• In-app notifications
• SMS integration ready
• WhatsApp integration ready
• Customizable notification rules

📈 DASHBOARD & ANALYTICS
------------------------
• Real-time workflow monitoring
• Bottleneck identification
• Processing time analytics
• Approval rate statistics
• SLA compliance reports

🔗 INTEGRATIONS
---------------
• Tazweed Core integration
• Tazweed Payroll integration
• Tazweed Leave integration
• Tazweed Performance integration
• External API support

🛡️ SECURITY & COMPLIANCE
-------------------------
• Role-based access control
• Audit trail for all actions
• Data encryption support
• GDPR compliance ready
• UAE labor law compliance

NEW FEATURES (v3.0.0)
=====================

🎨 VISUAL WORKFLOW DESIGNER
---------------------------
• Drag-and-drop workflow builder
• Node palette with multiple node types
• Connection management
• Canvas settings and zoom controls
• Design validation and publishing

🔀 CONDITIONAL LOGIC
--------------------
• Condition groups with AND/OR/NOT/XOR logic
• Field comparisons with multiple operators
• Date-based conditions
• User-based conditions
• Record-based conditions
• Decision tables for complex logic

📧 EMAIL TEMPLATES
------------------
• Dynamic email templates
• Personalization blocks
• A/B testing support
• Email tracking (opens, clicks)
• Conditional sending

🔗 WEBHOOK INTEGRATION
----------------------
• Outgoing webhooks with retry logic
• Incoming webhooks with security
• Multiple authentication methods
• HMAC signature verification
• Response processing

    ''',
    'author': 'Tazweed',
    'website': 'https://tazweedjobs.ae',
    'depends': [
        'base',
        'hr',
        'mail',
        'hr_contract',
        'tazweed_core',
    ],
    'data': [
        # Security
        'security/workflow_security.xml',
        'security/ir.model.access.csv',
        # Data - Sequences
        'data/workflow_sequence.xml',
        # Data - Templates
        'data/notification_template_data.xml',
        'data/workflow_template_data.xml',
        # Data - Cron Jobs
        'data/workflow_cron.xml',
        # Views
        'views/workflow_definition_views.xml',
        'views/workflow_instance_views.xml',
        'views/automation_rule_views.xml',
        'views/scheduled_task_views.xml',
        'views/approval_workflow_views.xml',
        'views/notification_template_views.xml',
        'views/workflow_trigger_views.xml',
        'views/workflow_dashboard_views.xml',
        'views/sla_configuration_views.xml',
        'views/escalation_rule_views.xml',
        'views/workflow_execution_log_views.xml',
        # New Feature Views
        'views/visual_workflow_designer_views.xml',
        'views/conditional_logic_views.xml',
        'views/email_templates_views.xml',
        'views/webhook_integration_views.xml',
        # Menu
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tazweed_automated_workflows/static/src/css/workflow_dashboard.css',
            'tazweed_automated_workflows/static/src/js/workflow_dashboard.js',
            'tazweed_automated_workflows/static/src/xml/workflow_dashboard.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
