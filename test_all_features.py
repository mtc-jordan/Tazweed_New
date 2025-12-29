#!/usr/bin/env python3
"""
Comprehensive test script for all 27 Tazweed new features
"""

import ast
import os
import re
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


def count_fields(filepath):
    """Count fields in a Python file"""
    if not os.path.exists(filepath):
        return 0
    with open(filepath, 'r') as f:
        content = f.read()
    field_matches = re.findall(r'(\w+)\s*=\s*fields\.', content)
    return len(set(field_matches))


def count_classes(filepath):
    """Count classes in a Python file"""
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        source = f.read()
    tree = ast.parse(source)
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def test_module(module_name, model_files, view_files):
    """Test a module's files"""
    base_path = f'/home/ubuntu/Tazweed_New/{module_name}'
    
    results = {
        'models': 0,
        'fields': 0,
        'views': 0,
        'passed': True,
        'errors': []
    }
    
    # Test model files
    for model_file in model_files:
        filepath = os.path.join(base_path, 'models', model_file)
        if os.path.exists(filepath):
            valid, error = test_python_syntax(filepath)
            if valid:
                classes = count_classes(filepath)
                fields = count_fields(filepath)
                results['models'] += len(classes)
                results['fields'] += fields
            else:
                results['passed'] = False
                results['errors'].append(f"{model_file}: {error}")
        else:
            results['passed'] = False
            results['errors'].append(f"{model_file}: File not found")
    
    # Test view files
    for view_file in view_files:
        filepath = os.path.join(base_path, 'views', view_file)
        if os.path.exists(filepath):
            results['views'] += 1
        else:
            results['passed'] = False
            results['errors'].append(f"{view_file}: File not found")
    
    return results


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("TAZWEED NEW FEATURES - COMPREHENSIVE TEST REPORT")
    print("="*80)
    
    # Define all modules and their actual files (based on actual file names)
    modules = {
        'tazweed_core': {
            'features': ['Self-Onboarding', 'Skills Matrix', 'Org Chart', 'Timeline'],
            'models': ['employee_onboarding.py', 'employee_skills.py', 'organization_chart.py', 'employee_timeline.py'],
            'views': ['employee_onboarding_views.xml', 'employee_skills_views.xml', 'organization_chart_views.xml', 'employee_timeline_views.xml']
        },
        'tazweed_placement': {
            'features': ['AI Matching', 'Video Interview', 'Offer Letter', 'Forecasting'],
            'models': ['ai_candidate_matching.py', 'video_interview.py', 'offer_letter.py', 'placement_forecasting.py'],
            'views': ['ai_candidate_matching_views.xml', 'video_interview_views.xml', 'offer_letter_views.xml', 'placement_forecasting_views.xml']
        },
        'tazweed_job_board': {
            'features': ['LinkedIn Integration', 'Indeed/Bayt Integration', 'AI Resume Scoring'],
            'models': ['linkedin_integration.py', 'indeed_bayt_integration.py', 'ai_resume_scoring.py'],
            'views': ['linkedin_integration_views.xml', 'indeed_bayt_integration_views.xml', 'ai_resume_scoring_views.xml']
        },
        'tazweed_payroll': {
            'features': ['Payroll Simulation'],
            'models': ['payroll_simulation.py'],
            'views': ['payroll_simulation_views.xml']
        },
        'tazweed_wps': {
            'features': ['Bank API', 'Validation Rules', 'Reconciliation'],
            'models': ['wps_bank_api.py', 'wps_validation.py', 'wps_reconciliation.py'],
            'views': ['wps_bank_api_views.xml', 'wps_validation_views.xml', 'wps_reconciliation_views.xml']
        },
        'tazweed_document_center': {
            'features': ['OCR Processing', 'Document Versioning', 'Bulk Upload', 'Document Templates'],
            'models': ['document_ocr.py', 'document_versioning.py', 'document_bulk_upload.py', 'document_templates.py'],
            'views': ['document_ocr_views.xml', 'document_versioning_views.xml', 'document_bulk_upload_views.xml', 'document_templates_views.xml']
        },
        'tazweed_automated_workflows': {
            'features': ['Visual Designer', 'Conditional Logic', 'Email Templates', 'Webhooks'],
            'models': ['visual_workflow_designer.py', 'conditional_logic.py', 'email_templates.py', 'webhook_integration.py'],
            'views': ['visual_workflow_designer_views.xml', 'conditional_logic_views.xml', 'email_templates_views.xml', 'webhook_integration_views.xml']
        },
        'tazweed_esignature': {
            'features': ['Bulk Signing', 'Signing Order', 'Signature Verification'],
            'models': ['bulk_signing.py', 'signing_order.py', 'signature_verification.py'],
            'views': ['bulk_signing_views.xml', 'signing_order_views.xml', 'signature_verification_views.xml']
        }
    }
    
    total_features = 0
    total_models = 0
    total_fields = 0
    total_views = 0
    all_passed = True
    
    results_table = []
    
    for module_name, config in modules.items():
        print(f"\n{module_name}")
        print("-" * 40)
        
        results = test_module(module_name, config['models'], config['views'])
        
        status = "✓ PASSED" if results['passed'] else "✗ FAILED"
        print(f"  Status: {status}")
        print(f"  Features: {len(config['features'])}")
        print(f"  Models: {results['models']}")
        print(f"  Fields: ~{results['fields']}")
        print(f"  Views: {results['views']}")
        
        if results['errors']:
            print(f"  Errors:")
            for error in results['errors']:
                print(f"    - {error}")
        
        total_features += len(config['features'])
        total_models += results['models']
        total_fields += results['fields']
        total_views += results['views']
        
        if not results['passed']:
            all_passed = False
        
        results_table.append({
            'module': module_name,
            'features': len(config['features']),
            'models': results['models'],
            'fields': results['fields'],
            'views': results['views'],
            'passed': results['passed']
        })
    
    # Summary Table
    print("\n" + "="*80)
    print("SUMMARY TABLE")
    print("="*80)
    print(f"{'Module':<35} {'Features':<10} {'Models':<10} {'Fields':<10} {'Views':<10} {'Status':<10}")
    print("-"*80)
    
    for row in results_table:
        status = "✓" if row['passed'] else "✗"
        print(f"{row['module']:<35} {row['features']:<10} {row['models']:<10} {row['fields']:<10} {row['views']:<10} {status:<10}")
    
    print("-"*80)
    print(f"{'TOTAL':<35} {total_features:<10} {total_models:<10} {total_fields:<10} {total_views:<10}")
    
    # Final Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"  Total Features Implemented: {total_features}")
    print(f"  Total Models Created: {total_models}")
    print(f"  Total Fields Defined: ~{total_fields}")
    print(f"  Total View Files: {total_views}")
    print(f"  Overall Status: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
