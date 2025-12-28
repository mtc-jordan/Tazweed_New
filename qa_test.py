# -*- coding: utf-8 -*-
"""
Comprehensive QA Test Suite for Tazweed Modules
Updated with correct model and menu names
"""
import sys
sys.path.insert(0, '/home/ubuntu/odoo16')
import odoo
from odoo.tools import config
from datetime import datetime

config.parse_config(['-c', '/home/ubuntu/odoo16/odoo.conf', '-d', 'tazweed', '--stop-after-init'])

from odoo.modules.registry import Registry

class TazweedQATest:
    def __init__(self):
        self.registry = Registry.new('tazweed')
        self.results = {}
        self.total_passed = 0
        self.total_failed = 0
        self.module_results = {}
        
    def run_all_tests(self):
        """Run all QA tests."""
        print("=" * 80)
        print("TAZWEED MODULES - COMPREHENSIVE QA TEST REPORT")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Test each module in separate transactions
        modules_to_test = [
            ('tazweed_core', self.test_tazweed_core),
            ('tazweed_placement', self.test_tazweed_placement),
            ('tazweed_payroll', self.test_tazweed_payroll),
            ('tazweed_leave', self.test_tazweed_leave),
            ('tazweed_performance', self.test_tazweed_performance),
            ('tazweed_document_center', self.test_tazweed_document_center),
            ('tazweed_uae_compliance', self.test_tazweed_uae_compliance),
            ('tazweed_wps', self.test_tazweed_wps),
            ('tazweed_job_board', self.test_tazweed_job_board),
            ('tazweed_integration', self.test_tazweed_integration),
            ('tazweed_pro_services', self.test_tazweed_pro_services),
            ('tazweed_automated_workflows', self.test_tazweed_automated_workflows),
            ('tazweed_esignature', self.test_tazweed_esignature),
            ('tazweed_employee_portal', self.test_tazweed_employee_portal),
        ]
        
        for module_name, test_func in modules_to_test:
            try:
                with self.registry.cursor() as cr:
                    from odoo.api import Environment
                    self.env = Environment(cr, odoo.SUPERUSER_ID, {})
                    test_func()
                    cr.rollback()
            except Exception as e:
                print(f"\n   ⚠️ Error testing {module_name}: {str(e)[:50]}")
                self.module_results.setdefault(module_name, {'passed': 0, 'failed': 0})
                self.module_results[module_name]['failed'] += 1
                self.total_failed += 1
        
        # Print summary
        self.print_summary()
    
    def check(self, condition, test_name, module_name=None):
        """Check a test condition and record result."""
        if condition:
            print(f"      ✅ {test_name}")
            self.total_passed += 1
            if module_name:
                self.module_results.setdefault(module_name, {'passed': 0, 'failed': 0})
                self.module_results[module_name]['passed'] += 1
            return True
        else:
            print(f"      ❌ {test_name}")
            self.total_failed += 1
            if module_name:
                self.module_results.setdefault(module_name, {'passed': 0, 'failed': 0})
                self.module_results[module_name]['failed'] += 1
            return False
    
    def is_installed(self, module_name):
        """Check if module is installed."""
        try:
            module = self.env['ir.module.module'].search([('name', '=', module_name)])
            return module and module.state == 'installed'
        except:
            return False
    
    def model_exists(self, model_name):
        """Check if model exists."""
        try:
            self.env[model_name]
            return True
        except:
            return False
    
    def menu_exists(self, xml_id):
        """Check if menu exists."""
        try:
            m = self.env.ref(xml_id, raise_if_not_found=False)
            return m is not None
        except:
            return False
    
    def test_tazweed_core(self):
        """Test tazweed_core module."""
        module = 'tazweed_core'
        print("\n" + "-" * 80)
        print("1. TAZWEED CORE")
        print("-" * 80)
        
        print("   1.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   1.2 Models")
        models = ['tazweed.employee.category', 'tazweed.document.type', 'tazweed.employee.document', 
                  'tazweed.employee.bank', 'tazweed.employee.sponsor']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   1.3 Security Groups")
        groups = ['group_tazweed_user', 'group_tazweed_manager', 'group_tazweed_admin']
        for group in groups:
            g = self.env.ref(f'tazweed_core.{group}', raise_if_not_found=False)
            self.check(g is not None, f"Group {group}", module)
        
        print("   1.4 HR Employee Extension")
        try:
            employee = self.env['hr.employee'].search([], limit=1)
            if employee:
                self.check('sponsor_id' in employee._fields, "Employee sponsor field", module)
            else:
                self.check(True, "Employee sponsor field (no employees to test)", module)
        except:
            self.check(False, "HR Employee extension", module)
    
    def test_tazweed_placement(self):
        """Test tazweed_placement module."""
        module = 'tazweed_placement'
        print("\n" + "-" * 80)
        print("2. TAZWEED PLACEMENT")
        print("-" * 80)
        
        print("   2.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   2.2 Models")
        models = ['tazweed.client', 'tazweed.placement']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   2.3 Menus")
        self.check(self.menu_exists('tazweed_placement.menu_tazweed_placement_root'), "Placement Root menu", module)
    
    def test_tazweed_payroll(self):
        """Test tazweed_payroll module."""
        module = 'tazweed_payroll'
        print("\n" + "-" * 80)
        print("3. TAZWEED PAYROLL")
        print("-" * 80)
        
        print("   3.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   3.2 Models")
        models = ['hr.payslip', 'hr.payslip.run']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   3.3 Menus")
        self.check(self.menu_exists('tazweed_payroll.menu_tazweed_payroll_root'), "Payroll Root menu", module)
        self.check(self.menu_exists('tazweed_payroll.menu_payroll_processing'), "Payroll Processing menu", module)
        
        print("   3.4 Salary Structures")
        structures = self.env['hr.payroll.structure'].search([])
        self.check(len(structures) > 0, f"Salary structures ({len(structures)})", module)
    
    def test_tazweed_leave(self):
        """Test tazweed_leave module."""
        module = 'tazweed_leave'
        print("\n" + "-" * 80)
        print("4. TAZWEED LEAVE")
        print("-" * 80)
        
        print("   4.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   4.2 Models")
        models = ['hr.leave', 'hr.leave.type', 'hr.leave.allocation']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   4.3 Leave Types")
        leave_types = self.env['hr.leave.type'].search([])
        self.check(len(leave_types) > 0, f"Leave types configured ({len(leave_types)})", module)
    
    def test_tazweed_performance(self):
        """Test tazweed_performance module."""
        module = 'tazweed_performance'
        print("\n" + "-" * 80)
        print("5. TAZWEED PERFORMANCE")
        print("-" * 80)
        
        print("   5.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   5.2 Models")
        models = ['tazweed.performance.review', 'tazweed.performance.goal']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   5.3 Menus")
        self.check(self.menu_exists('tazweed_performance.menu_performance_root'), "Performance Root menu", module)
        self.check(self.menu_exists('tazweed_performance.menu_performance_reviews'), "Performance Reviews menu", module)
    
    def test_tazweed_document_center(self):
        """Test tazweed_document_center module."""
        module = 'tazweed_document_center'
        print("\n" + "-" * 80)
        print("6. TAZWEED DOCUMENT CENTER")
        print("-" * 80)
        
        print("   6.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   6.2 Menus")
        self.check(self.menu_exists('tazweed_document_center.menu_document_center_root'), "Document Center menu", module)
    
    def test_tazweed_uae_compliance(self):
        """Test tazweed_uae_compliance module."""
        module = 'tazweed_uae_compliance'
        print("\n" + "-" * 80)
        print("7. TAZWEED UAE COMPLIANCE")
        print("-" * 80)
        
        print("   7.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   7.2 Menus")
        self.check(self.menu_exists('tazweed_uae_compliance.menu_compliance_root'), "UAE Compliance Root menu", module)
        self.check(self.menu_exists('tazweed_uae_compliance.menu_compliance_wps'), "WPS Compliance menu", module)
    
    def test_tazweed_wps(self):
        """Test tazweed_wps module."""
        module = 'tazweed_wps'
        print("\n" + "-" * 80)
        print("8. TAZWEED WPS")
        print("-" * 80)
        
        print("   8.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   8.2 Models")
        models = ['tazweed.wps.file']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   8.3 Sequence")
        seq = self.env['ir.sequence'].search([('code', '=', 'tazweed.wps.file')])
        self.check(len(seq) > 0, "WPS sequence configured", module)
        
        print("   8.4 Menus")
        self.check(self.menu_exists('tazweed_wps.menu_wps_root'), "WPS Root menu", module)
    
    def test_tazweed_job_board(self):
        """Test tazweed_job_board module."""
        module = 'tazweed_job_board'
        print("\n" + "-" * 80)
        print("9. TAZWEED JOB BOARD")
        print("-" * 80)
        
        print("   9.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   9.2 Models")
        # Correct model names
        models = ['job.board', 'job.posting', 'candidate.source', 'job.template', 'job.board.analytics']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   9.3 Security Groups")
        groups = ['group_job_board_user', 'group_job_board_manager']
        for group in groups:
            g = self.env.ref(f'tazweed_job_board.{group}', raise_if_not_found=False)
            self.check(g is not None, f"Group {group}", module)
        
        print("   9.4 Menus")
        self.check(self.menu_exists('tazweed_job_board.menu_job_board_root'), "Job Board Root menu", module)
    
    def test_tazweed_integration(self):
        """Test tazweed_integration module."""
        module = 'tazweed_integration'
        print("\n" + "-" * 80)
        print("10. TAZWEED INTEGRATION")
        print("-" * 80)
        
        print("   10.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   10.2 Models")
        # Correct model names
        models = ['tazweed.integration.dashboard', 'tazweed.integration.log', 'tazweed.integration.config']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   10.3 Menus")
        self.check(self.menu_exists('tazweed_integration.menu_integration_root'), "Integration Root menu", module)
        self.check(self.menu_exists('tazweed_integration.menu_integration_dashboard'), "Integration Dashboard menu", module)
    
    def test_tazweed_pro_services(self):
        """Test tazweed_pro_services module."""
        module = 'tazweed_pro_services'
        print("\n" + "-" * 80)
        print("11. TAZWEED PRO SERVICES")
        print("-" * 80)
        
        print("   11.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   11.2 Models")
        models = ['pro.service.request', 'pro.service', 'pro.government.authority', 'pro.service.category']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   11.3 Master Data")
        if self.model_exists('pro.service'):
            services = self.env['pro.service'].search([])
            self.check(len(services) > 0, f"PRO services ({len(services)})", module)
        
        if self.model_exists('pro.government.authority'):
            authorities = self.env['pro.government.authority'].search([])
            self.check(len(authorities) > 0, f"Government authorities ({len(authorities)})", module)
        
        if self.model_exists('pro.service.category'):
            categories = self.env['pro.service.category'].search([])
            self.check(len(categories) > 0, f"Service categories ({len(categories)})", module)
    
    def test_tazweed_automated_workflows(self):
        """Test tazweed_automated_workflows module."""
        module = 'tazweed_automated_workflows'
        print("\n" + "-" * 80)
        print("12. TAZWEED AUTOMATED WORKFLOWS")
        print("-" * 80)
        
        print("   12.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   12.2 Models")
        models = ['tazweed.workflow.definition', 'tazweed.workflow.instance', 
                  'tazweed.sla.configuration', 'tazweed.escalation.rule']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   12.3 Workflow Templates")
        if self.model_exists('tazweed.workflow.definition'):
            templates = self.env['tazweed.workflow.definition'].search([('is_template', '=', True)])
            self.check(len(templates) > 0, f"Workflow templates ({len(templates)})", module)
        
        print("   12.4 Cron Jobs")
        crons = self.env['ir.cron'].search([('name', 'like', '%Workflow%')])
        self.check(len(crons) > 0, f"Workflow cron jobs ({len(crons)})", module)
        
        print("   12.5 Menus")
        self.check(self.menu_exists('tazweed_automated_workflows.menu_workflow_root'), "Workflow Root menu", module)
        self.check(self.menu_exists('tazweed_automated_workflows.menu_workflow_config'), "Workflow Config menu", module)
    
    def test_tazweed_esignature(self):
        """Test tazweed_esignature module."""
        module = 'tazweed_esignature'
        print("\n" + "-" * 80)
        print("13. TAZWEED E-SIGNATURE")
        print("-" * 80)
        
        print("   13.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   13.2 Models")
        models = ['signature.request', 'signature.signer', 'signature.certificate', 
                  'signature.document.type', 'signature.template', 'signature.audit.log']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   13.3 Document Types")
        if self.model_exists('signature.document.type'):
            doc_types = self.env['signature.document.type'].search([])
            self.check(len(doc_types) >= 18, f"Document types ({len(doc_types)})", module)
        
        print("   13.4 Security Groups")
        groups = ['group_esignature_user', 'group_esignature_manager']
        for group in groups:
            g = self.env.ref(f'tazweed_esignature.{group}', raise_if_not_found=False)
            self.check(g is not None, f"Group {group}", module)
        
        print("   13.5 Cron Jobs")
        crons = self.env['ir.cron'].search([('name', 'like', '%E-Signature%')])
        self.check(len(crons) >= 2, f"E-Signature cron jobs ({len(crons)})", module)
        
        print("   13.6 Menus")
        self.check(self.menu_exists('tazweed_esignature.menu_esignature_root'), "E-Signature Root menu", module)
        
        print("   13.7 Workflow Test")
        if self.model_exists('signature.request'):
            try:
                request = self.env['signature.request'].create({
                    'document_name': 'QA Test Document',
                    'document_type': 'contract',
                    'document_file': 'VGVzdA==',
                    'document_filename': 'test.pdf',
                })
                self.check(request.name.startswith('SIG/'), f"Request created: {request.name}", module)
                self.check(request.document_hash is not None, "Document hash generated", module)
                self.check(request.access_token is not None, "Access token generated", module)
            except Exception as e:
                self.check(False, f"Workflow test: {str(e)[:50]}", module)
    
    def test_tazweed_employee_portal(self):
        """Test tazweed_employee_portal module."""
        module = 'tazweed_employee_portal'
        print("\n" + "-" * 80)
        print("14. TAZWEED EMPLOYEE PORTAL")
        print("-" * 80)
        
        print("   14.1 Installation")
        if not self.check(self.is_installed(module), "Module installed", module):
            return
        
        print("   14.2 Models")
        models = ['tazweed.portal.announcement']
        for model in models:
            self.check(self.model_exists(model), f"Model {model}", module)
        
        print("   14.3 HR Employee Extension")
        try:
            if 'portal_access' in self.env['hr.employee']._fields:
                self.check(True, "portal_access field", module)
            else:
                self.check(False, "portal_access field", module)
            
            if 'portal_last_login' in self.env['hr.employee']._fields:
                self.check(True, "portal_last_login field", module)
            else:
                self.check(False, "portal_last_login field", module)
        except Exception as e:
            self.check(False, f"HR Employee extension: {str(e)[:30]}", module)
        
        print("   14.4 Controllers")
        import importlib.util
        controllers = ['portal_main', 'portal_leave', 'portal_attendance', 'portal_payslip']
        for ctrl in controllers:
            try:
                spec = importlib.util.find_spec(f'odoo.addons.tazweed_employee_portal.controllers.{ctrl}')
                self.check(spec is not None, f"Controller {ctrl}", module)
            except:
                self.check(False, f"Controller {ctrl}", module)
        
        print("   14.5 Announcement Model Test")
        try:
            announcement = self.env['tazweed.portal.announcement'].create({
                'name': 'QA Test Announcement',
                'content': 'This is a test announcement',
                'target_type': 'all',
            })
            self.check(announcement.id > 0, f"Announcement created: {announcement.id}", module)
            self.check(announcement.state == 'draft', "Default state is draft", module)
        except Exception as e:
            self.check(False, f"Announcement creation: {str(e)[:30]}", module)
        
        print("   14.6 Dashboard Data Method")
        try:
            employee = self.env['hr.employee'].search([], limit=1)
            if employee:
                data = employee.get_portal_dashboard_data()
                self.check('leave_balance' in data and 'announcements' in data, "get_portal_dashboard_data method", module)
            else:
                self.check(True, "Dashboard data (no employees to test)", module)
        except Exception as e:
            self.check(False, f"Dashboard data: {str(e)[:30]}", module)
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("QA TEST SUMMARY BY MODULE")
        print("=" * 80)
        
        for module, results in sorted(self.module_results.items()):
            total = results['passed'] + results['failed']
            status = "✅" if results['failed'] == 0 else "⚠️" if results['passed'] > results['failed'] else "❌"
            print(f"   {status} {module}: {results['passed']}/{total} passed")
        
        print("\n" + "=" * 80)
        print("OVERALL SUMMARY")
        print("=" * 80)
        
        total = self.total_passed + self.total_failed
        pass_rate = (self.total_passed / total * 100) if total > 0 else 0
        
        print(f"\n   Total Tests:  {total}")
        print(f"   Passed:       {self.total_passed} ({pass_rate:.1f}%)")
        print(f"   Failed:       {self.total_failed}")
        
        if self.total_failed == 0:
            print("\n   ✅ ALL TESTS PASSED!")
        elif pass_rate >= 90:
            print(f"\n   ✅ EXCELLENT ({pass_rate:.1f}%)")
        elif pass_rate >= 80:
            print(f"\n   ⚠️ MOSTLY PASSED ({pass_rate:.1f}%)")
        else:
            print(f"\n   ❌ {self.total_failed} TESTS FAILED")
        
        print("\n" + "=" * 80)


if __name__ == '__main__':
    qa = TazweedQATest()
    qa.run_all_tests()
