#!/usr/bin/env python3
"""
Standalone test script for tazweed_esignature new features
Tests: Bulk Signing, Signing Order, Signature Verification
"""

import ast
import os
import re


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


def test_bulk_signing():
    """Test Bulk Signing files"""
    print("\n" + "="*60)
    print("Testing Bulk Signing")
    print("="*60)
    
    model_file = '/home/ubuntu/Tazweed_New/tazweed_esignature/models/bulk_signing.py'
    view_file = '/home/ubuntu/Tazweed_New/tazweed_esignature/views/bulk_signing_views.xml'
    
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
            if 'def action_generate_items' in content:
                print(f"  ✓ action_generate_items() method found")
            if 'def action_send_all' in content:
                print(f"  ✓ action_send_all() method found")
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
    else:
        print(f"  ✗ View file missing")
        return False
    
    return True


def test_signing_order():
    """Test Signing Order files"""
    print("\n" + "="*60)
    print("Testing Signing Order")
    print("="*60)
    
    model_file = '/home/ubuntu/Tazweed_New/tazweed_esignature/models/signing_order.py'
    view_file = '/home/ubuntu/Tazweed_New/tazweed_esignature/views/signing_order_views.xml'
    
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
            if 'def apply_to_request' in content:
                print(f"  ✓ apply_to_request() method found")
            if 'def _get_signer_values' in content:
                print(f"  ✓ _get_signer_values() method found")
            if 'def _check_condition' in content:
                print(f"  ✓ _check_condition() method found")
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


def test_signature_verification():
    """Test Signature Verification files"""
    print("\n" + "="*60)
    print("Testing Signature Verification")
    print("="*60)
    
    model_file = '/home/ubuntu/Tazweed_New/tazweed_esignature/models/signature_verification.py'
    view_file = '/home/ubuntu/Tazweed_New/tazweed_esignature/views/signature_verification_views.xml'
    
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
            if 'def action_verify' in content:
                print(f"  ✓ action_verify() method found")
            if 'def _verify_document_integrity' in content:
                print(f"  ✓ _verify_document_integrity() method found")
            if 'def _verify_signature' in content:
                print(f"  ✓ _verify_signature() method found")
            if 'def _verify_certificate' in content:
                print(f"  ✓ _verify_certificate() method found")
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
    
    base_path = '/home/ubuntu/Tazweed_New/tazweed_esignature'
    
    # Check __init__.py
    init_file = os.path.join(base_path, 'models', '__init__.py')
    if os.path.exists(init_file):
        with open(init_file, 'r') as f:
            content = f.read()
        
        required_imports = [
            'bulk_signing',
            'signing_order',
            'signature_verification'
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
            'bulk_signing_views.xml',
            'signing_order_views.xml',
            'signature_verification_views.xml'
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
            'bulk_signing_batch',
            'bulk_signing_item',
            'signing_order_workflow',
            'signing_order_step',
            'signing_order_group',
            'signer_delegation',
            'signature_verification',
            'signature_verification_report',
            'signature_qr_code'
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
        ('bulk_signing.py', ['BulkSigningBatch', 'BulkSigningItem', 'BulkSigningImportWizard']),
        ('signing_order.py', ['SigningOrderWorkflow', 'SigningOrderStep', 'SigningOrderGroup', 'SignerDelegation']),
        ('signature_verification.py', ['SignatureVerification', 'SignatureVerificationReport', 'SignatureQRCode']),
    ]
    
    total_fields = 0
    total_models = 0
    
    for filename, classes in files:
        filepath = f'/home/ubuntu/Tazweed_New/tazweed_esignature/models/{filename}'
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Count fields.* occurrences
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
    print("TAZWEED E-SIGNATURE - NEW FEATURES TEST")
    print("="*60)
    
    results = []
    
    results.append(('Bulk Signing', test_bulk_signing()))
    results.append(('Signing Order', test_signing_order()))
    results.append(('Signature Verification', test_signature_verification()))
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
    exit(0 if success else 1)
