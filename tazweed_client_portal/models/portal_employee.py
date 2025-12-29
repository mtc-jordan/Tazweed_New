# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class ClientPortalEmployee(models.Model):
    """Client Portal Employee Management"""
    _name = 'client.portal.employee'
    _description = 'Client Portal Employee View'
    _auto = False

    @api.model
    def get_employees_for_client(self, client_id, filters=None):
        """Get all employees assigned to a client with detailed information"""
        placements = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id),
            ('state', '=', 'active')
        ])
        
        employees = []
        today = fields.Date.today()
        
        for placement in placements:
            emp = placement.employee_id
            if not emp:
                continue
            
            # Document status
            doc_status = self._get_document_status(emp, today)
            
            # Calculate tenure
            tenure_days = (today - placement.start_date).days if placement.start_date else 0
            tenure_months = tenure_days // 30
            tenure_years = tenure_months // 12
            
            if tenure_years > 0:
                tenure_str = f'{tenure_years}y {tenure_months % 12}m'
            else:
                tenure_str = f'{tenure_months}m'
            
            employee_data = {
                'id': emp.id,
                'placement_id': placement.id,
                'name': emp.name,
                'job_title': placement.job_title or emp.job_id.name if emp.job_id else '',
                'department': placement.department_id.name if placement.department_id else '',
                'start_date': placement.start_date,
                'tenure': tenure_str,
                'tenure_days': tenure_days,
                'email': emp.work_email or '',
                'phone': emp.work_phone or emp.mobile_phone or '',
                'photo': emp.image_128,
                'status': placement.state,
                'document_status': doc_status['status'],
                'expiring_documents': doc_status['expiring'],
                'expired_documents': doc_status['expired'],
                'location': placement.work_location if hasattr(placement, 'work_location') else '',
                'supervisor': placement.supervisor_id.name if hasattr(placement, 'supervisor_id') and placement.supervisor_id else '',
            }
            
            # Apply filters
            if filters:
                if filters.get('department') and employee_data['department'] != filters['department']:
                    continue
                if filters.get('status') == 'expiring' and doc_status['status'] != 'expiring':
                    continue
                if filters.get('status') == 'expired' and doc_status['status'] != 'expired':
                    continue
                if filters.get('search'):
                    search_term = filters['search'].lower()
                    if search_term not in employee_data['name'].lower() and \
                       search_term not in employee_data['job_title'].lower():
                        continue
            
            employees.append(employee_data)
        
        # Sort by name
        employees.sort(key=lambda x: x['name'])
        
        return employees
    
    def _get_document_status(self, employee, today):
        """Get document expiry status for an employee"""
        expiry_fields = {
            'visa_expiry_date': 'Visa',
            'passport_expiry_date': 'Passport',
            'labor_card_expiry': 'Labor Card',
            'emirates_id_expiry': 'Emirates ID',
        }
        
        expiring = []
        expired = []
        
        for field, doc_name in expiry_fields.items():
            if hasattr(employee, field):
                expiry_date = getattr(employee, field)
                if expiry_date:
                    if expiry_date < today:
                        expired.append({
                            'document': doc_name,
                            'expiry_date': expiry_date,
                            'days_overdue': (today - expiry_date).days,
                        })
                    elif expiry_date <= today + timedelta(days=30):
                        expiring.append({
                            'document': doc_name,
                            'expiry_date': expiry_date,
                            'days_remaining': (expiry_date - today).days,
                        })
        
        if expired:
            status = 'expired'
        elif expiring:
            status = 'expiring'
        else:
            status = 'compliant'
        
        return {
            'status': status,
            'expiring': expiring,
            'expired': expired,
        }
    
    @api.model
    def get_employee_details(self, client_id, employee_id):
        """Get detailed information for a specific employee"""
        placement = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id),
            ('employee_id', '=', employee_id),
            ('state', '=', 'active')
        ], limit=1)
        
        if not placement:
            raise UserError(_('Employee not found or not assigned to this client'))
        
        emp = placement.employee_id
        today = fields.Date.today()
        
        # Document status
        doc_status = self._get_document_status(emp, today)
        
        # Get attendance summary (if available)
        attendance_summary = self._get_attendance_summary(emp.id, client_id)
        
        # Get documents
        documents = self._get_employee_documents(emp.id, client_id)
        
        return {
            'employee': {
                'id': emp.id,
                'name': emp.name,
                'job_title': placement.job_title or (emp.job_id.name if emp.job_id else ''),
                'department': placement.department_id.name if placement.department_id else '',
                'email': emp.work_email or '',
                'phone': emp.work_phone or '',
                'mobile': emp.mobile_phone or '',
                'photo': emp.image_256,
                'nationality': emp.country_id.name if emp.country_id else '',
                'gender': emp.gender or '',
            },
            'placement': {
                'id': placement.id,
                'start_date': placement.start_date,
                'contract_type': placement.contract_type if hasattr(placement, 'contract_type') else '',
                'work_location': placement.work_location if hasattr(placement, 'work_location') else '',
                'supervisor': placement.supervisor_id.name if hasattr(placement, 'supervisor_id') and placement.supervisor_id else '',
                'status': placement.state,
            },
            'documents': {
                'status': doc_status['status'],
                'expiring': doc_status['expiring'],
                'expired': doc_status['expired'],
                'list': documents,
            },
            'attendance': attendance_summary,
        }
    
    def _get_attendance_summary(self, employee_id, client_id):
        """Get attendance summary for the current month"""
        today = fields.Date.today()
        month_start = today.replace(day=1)
        
        # Check if hr.attendance model exists
        if 'hr.attendance' not in self.env:
            return {
                'present_days': 0,
                'absent_days': 0,
                'late_days': 0,
                'total_hours': 0,
            }
        
        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', employee_id),
            ('check_in', '>=', month_start),
        ])
        
        present_days = len(set(a.check_in.date() for a in attendances))
        total_hours = sum(a.worked_hours for a in attendances if a.worked_hours)
        
        # Calculate working days in month
        working_days = 0
        current = month_start
        while current <= today:
            if current.weekday() < 5:  # Monday to Friday
                working_days += 1
            current += timedelta(days=1)
        
        absent_days = max(0, working_days - present_days)
        
        return {
            'present_days': present_days,
            'absent_days': absent_days,
            'late_days': 0,  # Would need more complex logic
            'total_hours': round(total_hours, 1),
            'working_days': working_days,
        }
    
    def _get_employee_documents(self, employee_id, client_id):
        """Get documents for an employee visible to client"""
        documents = []
        
        # Get from portal documents
        portal_docs = self.env['client.portal.document'].search([
            ('client_id', '=', client_id),
            ('employee_id', '=', employee_id),
            ('visibility', '=', 'client'),
        ])
        
        for doc in portal_docs:
            documents.append({
                'id': doc.id,
                'name': doc.name,
                'type': doc.document_type,
                'upload_date': doc.create_date,
                'expiry_date': doc.expiry_date if hasattr(doc, 'expiry_date') else None,
            })
        
        return documents
    
    @api.model
    def get_department_list(self, client_id):
        """Get list of departments for filtering"""
        placements = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id),
            ('state', '=', 'active')
        ])
        
        departments = set()
        for p in placements:
            if p.department_id:
                departments.add(p.department_id.name)
        
        return sorted(list(departments))


class ClientPortalAttendance(models.Model):
    """Client Portal Attendance View"""
    _name = 'client.portal.attendance'
    _description = 'Client Portal Attendance'
    _auto = False

    @api.model
    def get_attendance_report(self, client_id, date_from, date_to, employee_id=None):
        """Get attendance report for client's employees"""
        domain = [
            ('client_id', '=', client_id),
            ('state', '=', 'active')
        ]
        
        if employee_id:
            domain.append(('employee_id', '=', employee_id))
        
        placements = self.env['tazweed.placement'].search(domain)
        employee_ids = placements.mapped('employee_id').ids
        
        if 'hr.attendance' not in self.env:
            return {'error': 'Attendance module not installed'}
        
        attendances = self.env['hr.attendance'].search([
            ('employee_id', 'in', employee_ids),
            ('check_in', '>=', date_from),
            ('check_in', '<=', date_to),
        ])
        
        # Group by employee
        report = {}
        for att in attendances:
            emp_id = att.employee_id.id
            if emp_id not in report:
                report[emp_id] = {
                    'employee_id': emp_id,
                    'employee_name': att.employee_id.name,
                    'records': [],
                    'total_hours': 0,
                    'days_present': set(),
                }
            
            report[emp_id]['records'].append({
                'date': att.check_in.date(),
                'check_in': att.check_in,
                'check_out': att.check_out,
                'worked_hours': att.worked_hours or 0,
            })
            report[emp_id]['total_hours'] += att.worked_hours or 0
            report[emp_id]['days_present'].add(att.check_in.date())
        
        # Convert sets to counts
        for emp_id in report:
            report[emp_id]['days_present'] = len(report[emp_id]['days_present'])
            report[emp_id]['total_hours'] = round(report[emp_id]['total_hours'], 1)
        
        return list(report.values())


class ClientPortalPerformance(models.Model):
    """Client Portal Performance Metrics"""
    _name = 'client.portal.performance'
    _description = 'Client Portal Performance'
    _auto = False

    @api.model
    def get_performance_summary(self, client_id):
        """Get performance summary for client's employees"""
        placements = self.env['tazweed.placement'].search([
            ('client_id', '=', client_id),
            ('state', '=', 'active')
        ])
        
        employees = placements.mapped('employee_id')
        
        # Check if performance module exists
        if 'hr.appraisal' in self.env:
            appraisals = self.env['hr.appraisal'].search([
                ('employee_id', 'in', employees.ids),
                ('state', '=', 'done')
            ])
            
            # Calculate average rating
            ratings = [a.final_rating for a in appraisals if hasattr(a, 'final_rating') and a.final_rating]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
        else:
            avg_rating = 0
        
        return {
            'total_employees': len(employees),
            'average_rating': round(avg_rating, 2),
            'top_performers': [],  # Would need performance data
            'improvement_needed': [],  # Would need performance data
        }
