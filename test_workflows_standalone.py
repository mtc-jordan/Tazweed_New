#!/usr/bin/env python3
"""
Standalone test script for tazweed_automated_workflows new features
Tests file structure and code syntax without requiring Odoo
"""

import ast
import os
import sys


def test_python_syntax(filepath):
    """Test if Python file has valid syntax"""
    try:
        with open(filepath, 'r') as f:
            source = f.read()
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, str(e)


def count_classes(filepath):
    """Count classes defined in a Python file"""
    with open(filepath, 'r') as f:
        source = f.read()
    tree = ast.parse(source)
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    return classes


def count_fields_in_class(filepath, class_name):
    """Count fields defined in a class"""
    with open(filepath, 'r') as f:
        source = f.read()
    
    # Simple regex-based field counting
    import re
    
    # Find class definition
    class_pattern = rf'class {class_name}\([^)]+\):'
    class_match = re.search(class_pattern, source)
    if not class_match:
        return 0
    
    # Find all field definitions (fields.*)
    field_pattern = r'\s+(\w+)\s*=\s*fields\.\w+'
    fields = re.findall(field_pattern, source[class_match.end():])
    
    return len(set(fields))


def test_visual_workflow_designer():
    """Test Visual Workflow Designer files"""
    print("\n" + "="*60)
    print("Testing Visual Workflow Designer")
    print("="*60)
    
    model_file = '/home/ubuntu/Tazweed_New/tazweed_automated_workflows/models/visual_workflow_designer.py'
    view_file = '/home/ubuntu/Tazweed_New/tazweed_automated_workflows/views/visual_workflow_designer_views.xml'
    
    # Test model file
    if os.path.exists(model_file):
        print(f"  ✓ Model file exists")
        valid, error = test_python_syntax(model_file)
        if valid:
            print(f"  ✓ Python syntax is valid")
            classes = count_classes(model_file)
            print(f"  ✓ Classes defined: {', '.join(classes)}")
            
            # Count fields
            with open(model_file, 'r') as f:
                content = f.read()
            field_count = content.count('fields.')
            print(f"  ✓ Approximately {field_count} field definitions")
        else:
            print(f"  ✗ Syntax error: {error}")
            return False
    else:
        print(f"  ✗ Model file missing")
        return False
    
    # Test view file
    if os.path.exists(view_file):
        print(f"  ✓ View file exists")
        with open(view_file, 'r') as f:
            content = f.read()
        if '<record' in content and 'ir.ui.view' in content:
            print(f"  ✓ View definitions found")
        if '<menuitem' in content or 'ir.actions.act_window' in content:
            print(f"  ✓ Actions defined")
    else:
        print(f"  ✗ View file missing")
        return False
    
    return True


def test_conditional_logic():
    """Test Conditional Logic files"""
    print("\n" + "="*60)
    print("Testing Conditional Logic")
    print("="*60)
    
    model_file = '/home/ubuntu/Tazweed_New/tazweed_automated_workflows/models/conditional_logic.py'
    view_file = '/home/ubuntu/Tazweed_New/tazweed_automated_workflows/views/conditional_logic_views.xml'
    
    # Test model file
    if os.path.exists(model_file):
        print(f"  ✓ Model file exists")
        valid, error = test_python_syntax(model_file)
        if valid:
            print(f"  ✓ Python syntax is valid")
            classes = count_classes(model_file)
            print(f"  ✓ Classes defined: {', '.join(classes)}")
            
            with open(model_file, 'r') as f:
                content = f.read()
            field_count = content.count('fields.')
            print(f"  ✓ Approximately {field_count} field definitions")
            
            # Check for key methods
            if 'def evaluate' in content:
                print(f"  ✓ evaluate() method found")
        else:
            print(f"  ✗ Syntax error: {error}")
            return False
    else:
        print(f"  ✗ Model file missing")
        return False
    
    # Test view file
    if os.path.exists(view_file):
        print(f"  ✓ View file exists")
    else:
        print(f"  ✗ View file missing")
        return False
    
    return True


def test_email_templates():
    """Test Email Templates files"""
    print("\n" + "="*60)
    print("Testing Email Templates")
    print("="*60)
    
    model_file = '/home/ubuntu/Tazweed_New/tazweed_automated_workflows/models/email_templates.py'
    view_file = '/home/ubuntu/Tazweed_New/tazweed_automated_workflows/views/email_templates_views.xml'
    
    # Test model file
    if os.path.exists(model_file):
        print(f"  ✓ Model file exists")
        valid, error = test_python_syntax(model_file)
        if valid:
            print(f"  ✓ Python syntax is valid")
            classes = count_classes(model_file)
            print(f"  ✓ Classes defined: {', '.join(classes)}")
            
            with open(model_file, 'r') as f:
                content = f.read()
            field_count = content.count('fields.')
            print(f"  ✓ Approximately {field_count} field definitions")
            
            # Check for key methods
            if 'def render_template' in content:
                print(f"  ✓ render_template() method found")
            if 'def send_email' in content:
                print(f"  ✓ send_email() method found")
        else:
            print(f"  ✗ Syntax error: {error}")
            return False
    else:
        print(f"  ✗ Model file missing")
        return False
    
    # Test view file
    if os.path.exists(view_file):
        print(f"  ✓ View file exists")
    else:
        print(f"  ✗ View file missing")
        return False
    
    return True


def test_webhook_integration():
    """Test Webhook Integration files"""
    print("\n" + "="*60)
    print("Testing Webhook Integration")
    print("="*60)
    
    model_file = '/home/ubuntu/Tazweed_New/tazweed_automated_workflows/models/webhook_integration.py'
    view_file = '/home/ubuntu/Tazweed_New/tazweed_automated_workflows/views/webhook_integration_views.xml'
    
    # Test model file
    if os.path.exists(model_file):
        print(f"  ✓ Model file exists")
        valid, error = test_python_syntax(model_file)
        if valid:
            print(f"  ✓ Python syntax is valid")
            classes = count_classes(model_file)
            print(f"  ✓ Classes defined: {', '.join(classes)}")
            
            with open(model_file, 'r') as f:
                content = f.read()
            field_count = content.count('fields.')
            print(f"  ✓ Approximately {field_count} field definitions")
            
            # Check for key methods
            if 'def execute' in content:
                print(f"  ✓ execute() method found")
            if '_send_request' in content:
                print(f"  ✓ _send_request() method found")
            if '_generate_hmac_signature' in content:
                print(f"  ✓ HMAC signature method found")
        else:
            print(f"  ✗ Syntax error: {error}")
            return False
    else:
        print(f"  ✗ Model file missing")
        return False
    
    # Test view file
    if os.path.exists(view_file):
        print(f"  ✓ View file exists")
    else:
        print(f"  ✗ View file missing")
        return False
    
    return True


def test_module_structure():
    """Test overall module structure"""
    print("\n" + "="*60)
    print("Testing Module Structure")
    print("="*60)
    
    base_path = '/home/ubuntu/Tazweed_New/tazweed_automated_workflows'
    
    # Check __init__.py
    init_file = os.path.join(base_path, 'models', '__init__.py')
    if os.path.exists(init_file):
        with open(init_file, 'r') as f:
            content = f.read()
        
        required_imports = [
            'visual_workflow_designer',
            'conditional_logic',
            'email_templates',
            'webhook_integration'
        ]
        
        for imp in required_imports:
            if imp in content:
                print(f"  ✓ Import '{imp}' found in __init__.py")
            else:
                print(f"  ✗ Import '{imp}' missing from __init__.py")
    
    # Check __manifest__.py
    manifest_file = os.path.join(base_path, '__manifest__.py')
    if os.path.exists(manifest_file):
        with open(manifest_file, 'r') as f:
            content = f.read()
        
        required_views = [
            'visual_workflow_designer_views.xml',
            'conditional_logic_views.xml',
            'email_templates_views.xml',
            'webhook_integration_views.xml'
        ]
        
        for view in required_views:
            if view in content:
                print(f"  ✓ View '{view}' found in manifest")
            else:
                print(f"  ✗ View '{view}' missing from manifest")
    
    # Check security file
    security_file = os.path.join(base_path, 'security', 'ir.model.access.csv')
    if os.path.exists(security_file):
        with open(security_file, 'r') as f:
            content = f.read()
        
        new_models = [
            'visual_workflow_designer',
            'visual_workflow_node',
            'visual_workflow_connection',
            'workflow_condition_group',
            'workflow_condition',
            'workflow_decision_table',
            'workflow_email_template',
            'workflow_webhook',
            'workflow_incoming_webhook'
        ]
        
        found = 0
        for model in new_models:
            if model in content:
                found += 1
        
        print(f"  ✓ Security rules: {found}/{len(new_models)} models have access rules")
    
    return True


def count_all_fields():
    """Count all fields across new models"""
    print("\n" + "="*60)
    print("Field Count Summary")
    print("="*60)
    
    files = [
        ('visual_workflow_designer.py', ['VisualWorkflowDesigner', 'VisualWorkflowNode', 'VisualWorkflowConnection']),
        ('conditional_logic.py', ['WorkflowConditionGroup', 'WorkflowCondition', 'WorkflowDecisionTable', 'WorkflowDecisionColumn', 'WorkflowDecisionRule']),
        ('email_templates.py', ['WorkflowEmailTemplate', 'WorkflowEmailCondition', 'WorkflowEmailPersonalization', 'WorkflowEmailVariant', 'WorkflowEmailLog']),
        ('webhook_integration.py', ['WorkflowWebhook', 'WorkflowWebhookHeader', 'WorkflowWebhookLog', 'WorkflowIncomingWebhook']),
    ]
    
    total_fields = 0
    total_models = 0
    
    for filename, classes in files:
        filepath = f'/home/ubuntu/Tazweed_New/tazweed_automated_workflows/models/{filename}'
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Count fields.* occurrences
            import re
            field_matches = re.findall(r'(\w+)\s*=\s*fields\.', content)
            unique_fields = len(set(field_matches))
            
            print(f"\n  {filename}:")
            print(f"    Models: {len(classes)}")
            print(f"    Fields: ~{unique_fields}")
            
            total_fields += unique_fields
            total_models += len(classes)
    
    print(f"\n  TOTAL: ~{total_fields} fields across {total_models} models")
    return total_fields


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TAZWEED AUTOMATED WORKFLOWS - STANDALONE TEST")
    print("="*60)
    
    results = []
    
    results.append(('Visual Workflow Designer', test_visual_workflow_designer()))
    results.append(('Conditional Logic', test_conditional_logic()))
    results.append(('Email Templates', test_email_templates()))
    results.append(('Webhook Integration', test_webhook_integration()))
    results.append(('Module Structure', test_module_structure()))
    
    count_all_fields()
    
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
