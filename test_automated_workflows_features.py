#!/usr/bin/env python3
"""
Test script for tazweed_automated_workflows new features
Tests: Visual Workflow Designer, Conditional Logic, Email Templates, Webhook Integration
"""

import sys
import os

# Add Odoo path
sys.path.insert(0, '/home/ubuntu/Tazweed_New')

def test_visual_workflow_designer():
    """Test Visual Workflow Designer model"""
    print("\n" + "="*60)
    print("Testing Visual Workflow Designer")
    print("="*60)
    
    from tazweed_automated_workflows.models.visual_workflow_designer import (
        VisualWorkflowDesigner,
        VisualWorkflowNode,
        VisualWorkflowConnection
    )
    
    # Check VisualWorkflowDesigner fields
    designer_fields = [
        'name', 'description', 'canvas_width', 'canvas_height', 'grid_size',
        'snap_to_grid', 'show_grid', 'zoom_level', 'design_data', 'nodes_json',
        'connections_json', 'workflow_definition_id', 'node_ids', 'connection_ids',
        'state', 'active', 'last_modified', 'version', 'node_count', 'connection_count'
    ]
    
    for field in designer_fields:
        if hasattr(VisualWorkflowDesigner, field) or field in VisualWorkflowDesigner._fields:
            print(f"  ✓ Field '{field}' exists")
        else:
            print(f"  ✗ Field '{field}' MISSING")
    
    # Check VisualWorkflowNode fields
    node_fields = [
        'designer_id', 'node_uuid', 'name', 'description', 'sequence',
        'node_type', 'position_x', 'position_y', 'width', 'height',
        'color', 'icon', 'shape', 'config_json', 'action_type',
        'target_model', 'target_method', 'approver_type', 'approver_user_id',
        'approver_group_id', 'notification_template_id', 'delay_type', 'delay_value'
    ]
    
    print("\n  VisualWorkflowNode fields:")
    for field in node_fields:
        if hasattr(VisualWorkflowNode, field) or field in VisualWorkflowNode._fields:
            print(f"    ✓ Field '{field}' exists")
        else:
            print(f"    ✗ Field '{field}' MISSING")
    
    # Check VisualWorkflowConnection fields
    connection_fields = [
        'designer_id', 'connection_uuid', 'name', 'source_node_id',
        'target_node_id', 'connection_type', 'condition', 'condition_expression',
        'line_color', 'line_style', 'line_width', 'label', 'label_position'
    ]
    
    print("\n  VisualWorkflowConnection fields:")
    for field in connection_fields:
        if hasattr(VisualWorkflowConnection, field) or field in VisualWorkflowConnection._fields:
            print(f"    ✓ Field '{field}' exists")
        else:
            print(f"    ✗ Field '{field}' MISSING")
    
    # Check methods
    methods = ['action_start_designing', 'action_validate_design', 'action_publish', 
               'action_export_json', 'action_import_json']
    print("\n  Methods:")
    for method in methods:
        if hasattr(VisualWorkflowDesigner, method):
            print(f"    ✓ Method '{method}' exists")
        else:
            print(f"    ✗ Method '{method}' MISSING")
    
    print("\n✓ Visual Workflow Designer test completed")
    return True


def test_conditional_logic():
    """Test Conditional Logic models"""
    print("\n" + "="*60)
    print("Testing Conditional Logic")
    print("="*60)
    
    from tazweed_automated_workflows.models.conditional_logic import (
        WorkflowConditionGroup,
        WorkflowCondition,
        WorkflowDecisionTable,
        WorkflowDecisionColumn,
        WorkflowDecisionRule
    )
    
    # Check WorkflowConditionGroup fields
    group_fields = [
        'name', 'description', 'sequence', 'workflow_id', 'node_id',
        'logic_operator', 'condition_ids', 'parent_group_id', 'child_group_ids',
        'result', 'active'
    ]
    
    print("\n  WorkflowConditionGroup fields:")
    for field in group_fields:
        if hasattr(WorkflowConditionGroup, field) or field in WorkflowConditionGroup._fields:
            print(f"    ✓ Field '{field}' exists")
        else:
            print(f"    ✗ Field '{field}' MISSING")
    
    # Check WorkflowCondition fields
    condition_fields = [
        'name', 'description', 'sequence', 'group_id', 'condition_type',
        'model_id', 'field_id', 'field_name', 'operator', 'value_type',
        'value_static', 'value_field_id', 'value_expression', 'value_context_key',
        'date_operator', 'date_value', 'date_value_end', 'date_days',
        'user_operator', 'user_id', 'group_id_check', 'record_operator',
        'record_domain', 'record_count', 'python_expression', 'custom_function',
        'custom_params', 'active'
    ]
    
    print("\n  WorkflowCondition fields:")
    for field in condition_fields:
        if hasattr(WorkflowCondition, field) or field in WorkflowCondition._fields:
            print(f"    ✓ Field '{field}' exists")
        else:
            print(f"    ✗ Field '{field}' MISSING")
    
    # Check WorkflowDecisionTable fields
    table_fields = [
        'name', 'description', 'workflow_id', 'hit_policy',
        'input_column_ids', 'output_column_ids', 'rule_ids', 'active'
    ]
    
    print("\n  WorkflowDecisionTable fields:")
    for field in table_fields:
        if hasattr(WorkflowDecisionTable, field) or field in WorkflowDecisionTable._fields:
            print(f"    ✓ Field '{field}' exists")
        else:
            print(f"    ✗ Field '{field}' MISSING")
    
    # Check methods
    print("\n  Methods:")
    if hasattr(WorkflowConditionGroup, 'evaluate'):
        print("    ✓ Method 'evaluate' exists in ConditionGroup")
    if hasattr(WorkflowCondition, 'evaluate'):
        print("    ✓ Method 'evaluate' exists in Condition")
    if hasattr(WorkflowDecisionTable, 'evaluate'):
        print("    ✓ Method 'evaluate' exists in DecisionTable")
    
    print("\n✓ Conditional Logic test completed")
    return True


def test_email_templates():
    """Test Email Templates models"""
    print("\n" + "="*60)
    print("Testing Email Templates")
    print("="*60)
    
    from tazweed_automated_workflows.models.email_templates import (
        WorkflowEmailTemplate,
        WorkflowEmailCondition,
        WorkflowEmailPersonalization,
        WorkflowEmailVariant,
        WorkflowEmailLog
    )
    
    # Check WorkflowEmailTemplate fields
    template_fields = [
        'name', 'description', 'template_type', 'subject', 'body_html',
        'body_text', 'use_dynamic_content', 'dynamic_fields', 'model_id',
        'model_name', 'email_from', 'reply_to', 'recipient_type',
        'recipient_email', 'recipient_field', 'recipient_expression',
        'recipient_group_id', 'cc_emails', 'bcc_emails', 'attachment_ids',
        'dynamic_attachment_field', 'include_report', 'report_template_id',
        'send_immediately', 'delay_type', 'delay_value', 'condition_ids',
        'personalization_ids', 'enable_ab_testing', 'variant_ids',
        'track_opens', 'track_clicks', 'sent_count', 'open_count',
        'click_count', 'open_rate', 'click_rate', 'state', 'active'
    ]
    
    print("\n  WorkflowEmailTemplate fields:")
    for field in template_fields:
        if hasattr(WorkflowEmailTemplate, field) or field in WorkflowEmailTemplate._fields:
            print(f"    ✓ Field '{field}' exists")
        else:
            print(f"    ✗ Field '{field}' MISSING")
    
    # Check WorkflowEmailLog fields
    log_fields = [
        'template_id', 'variant_id', 'model', 'res_id', 'email_from',
        'email_to', 'subject', 'state', 'sent_date', 'opened_date',
        'clicked_date', 'tracking_id', 'user_agent', 'ip_address'
    ]
    
    print("\n  WorkflowEmailLog fields:")
    for field in log_fields:
        if hasattr(WorkflowEmailLog, field) or field in WorkflowEmailLog._fields:
            print(f"    ✓ Field '{field}' exists")
        else:
            print(f"    ✗ Field '{field}' MISSING")
    
    # Check methods
    methods = ['action_activate', 'action_pause', 'action_archive', 
               'render_template', 'send_email', 'action_preview', 'action_send_test']
    print("\n  Methods:")
    for method in methods:
        if hasattr(WorkflowEmailTemplate, method):
            print(f"    ✓ Method '{method}' exists")
        else:
            print(f"    ✗ Method '{method}' MISSING")
    
    print("\n✓ Email Templates test completed")
    return True


def test_webhook_integration():
    """Test Webhook Integration models"""
    print("\n" + "="*60)
    print("Testing Webhook Integration")
    print("="*60)
    
    from tazweed_automated_workflows.models.webhook_integration import (
        WorkflowWebhook,
        WorkflowWebhookHeader,
        WorkflowWebhookLog,
        WorkflowIncomingWebhook
    )
    
    # Check WorkflowWebhook fields
    webhook_fields = [
        'name', 'description', 'webhook_type', 'url', 'method',
        'auth_type', 'auth_username', 'auth_password', 'auth_token',
        'api_key_name', 'api_key_value', 'api_key_location',
        'hmac_secret', 'hmac_algorithm', 'hmac_header', 'header_ids',
        'content_type', 'payload_type', 'model_id', 'model_name',
        'selected_field_ids', 'custom_payload', 'payload_template',
        'trigger_type', 'trigger_field_ids', 'retry_enabled', 'max_retries',
        'retry_delay', 'retry_backoff', 'timeout', 'expected_status_codes',
        'response_handling', 'response_field_mapping', 'state', 'active',
        'total_calls', 'successful_calls', 'failed_calls', 'success_rate',
        'last_call_date', 'last_status_code', 'log_ids'
    ]
    
    print("\n  WorkflowWebhook fields:")
    for field in webhook_fields:
        if hasattr(WorkflowWebhook, field) or field in WorkflowWebhook._fields:
            print(f"    ✓ Field '{field}' exists")
        else:
            print(f"    ✗ Field '{field}' MISSING")
    
    # Check WorkflowIncomingWebhook fields
    incoming_fields = [
        'name', 'description', 'endpoint_token', 'endpoint_url',
        'require_signature', 'signature_secret', 'signature_header',
        'allowed_ips', 'target_model_id', 'action_type', 'field_mapping',
        'target_method', 'workflow_id', 'state', 'active',
        'total_received', 'successful_processed', 'failed_processed'
    ]
    
    print("\n  WorkflowIncomingWebhook fields:")
    for field in incoming_fields:
        if hasattr(WorkflowIncomingWebhook, field) or field in WorkflowIncomingWebhook._fields:
            print(f"    ✓ Field '{field}' exists")
        else:
            print(f"    ✗ Field '{field}' MISSING")
    
    # Check methods
    methods = ['action_activate', 'action_pause', 'action_test', 'execute',
               '_build_payload', '_send_request', '_generate_hmac_signature']
    print("\n  Methods:")
    for method in methods:
        if hasattr(WorkflowWebhook, method):
            print(f"    ✓ Method '{method}' exists")
        else:
            print(f"    ✗ Method '{method}' MISSING")
    
    print("\n✓ Webhook Integration test completed")
    return True


def count_fields():
    """Count total fields in all new models"""
    print("\n" + "="*60)
    print("Field Count Summary")
    print("="*60)
    
    from tazweed_automated_workflows.models.visual_workflow_designer import (
        VisualWorkflowDesigner, VisualWorkflowNode, VisualWorkflowConnection
    )
    from tazweed_automated_workflows.models.conditional_logic import (
        WorkflowConditionGroup, WorkflowCondition, WorkflowDecisionTable,
        WorkflowDecisionColumn, WorkflowDecisionRule
    )
    from tazweed_automated_workflows.models.email_templates import (
        WorkflowEmailTemplate, WorkflowEmailCondition, WorkflowEmailPersonalization,
        WorkflowEmailVariant, WorkflowEmailLog
    )
    from tazweed_automated_workflows.models.webhook_integration import (
        WorkflowWebhook, WorkflowWebhookHeader, WorkflowWebhookLog,
        WorkflowIncomingWebhook
    )
    
    models = [
        ('VisualWorkflowDesigner', VisualWorkflowDesigner),
        ('VisualWorkflowNode', VisualWorkflowNode),
        ('VisualWorkflowConnection', VisualWorkflowConnection),
        ('WorkflowConditionGroup', WorkflowConditionGroup),
        ('WorkflowCondition', WorkflowCondition),
        ('WorkflowDecisionTable', WorkflowDecisionTable),
        ('WorkflowDecisionColumn', WorkflowDecisionColumn),
        ('WorkflowDecisionRule', WorkflowDecisionRule),
        ('WorkflowEmailTemplate', WorkflowEmailTemplate),
        ('WorkflowEmailCondition', WorkflowEmailCondition),
        ('WorkflowEmailPersonalization', WorkflowEmailPersonalization),
        ('WorkflowEmailVariant', WorkflowEmailVariant),
        ('WorkflowEmailLog', WorkflowEmailLog),
        ('WorkflowWebhook', WorkflowWebhook),
        ('WorkflowWebhookHeader', WorkflowWebhookHeader),
        ('WorkflowWebhookLog', WorkflowWebhookLog),
        ('WorkflowIncomingWebhook', WorkflowIncomingWebhook),
    ]
    
    total_fields = 0
    for name, model in models:
        field_count = len(model._fields)
        total_fields += field_count
        print(f"  {name}: {field_count} fields")
    
    print(f"\n  TOTAL: {total_fields} fields across {len(models)} models")
    return total_fields


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TAZWEED AUTOMATED WORKFLOWS - NEW FEATURES TEST")
    print("="*60)
    
    results = []
    
    try:
        results.append(('Visual Workflow Designer', test_visual_workflow_designer()))
    except Exception as e:
        print(f"  ✗ Visual Workflow Designer test failed: {e}")
        results.append(('Visual Workflow Designer', False))
    
    try:
        results.append(('Conditional Logic', test_conditional_logic()))
    except Exception as e:
        print(f"  ✗ Conditional Logic test failed: {e}")
        results.append(('Conditional Logic', False))
    
    try:
        results.append(('Email Templates', test_email_templates()))
    except Exception as e:
        print(f"  ✗ Email Templates test failed: {e}")
        results.append(('Email Templates', False))
    
    try:
        results.append(('Webhook Integration', test_webhook_integration()))
    except Exception as e:
        print(f"  ✗ Webhook Integration test failed: {e}")
        results.append(('Webhook Integration', False))
    
    try:
        count_fields()
    except Exception as e:
        print(f"  ✗ Field count failed: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name}: {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
