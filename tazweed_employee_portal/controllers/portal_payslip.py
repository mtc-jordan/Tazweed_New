# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from datetime import datetime


class TazweedPayslipPortal(CustomerPortal):
    """Payslip Portal Controller - Optional features when payroll is installed"""

    def _get_current_employee(self):
        """Get current user's employee record"""
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', user.id),
        ], limit=1)
        return employee

    def _payroll_installed(self):
        """Check if payroll module is installed"""
        return 'hr.payslip' in request.env

    @http.route(['/my/payslips', '/my/payslips/page/<int:page>'], type='http', auth='user', website=True)
    def portal_payslips(self, page=1, year=None, **kw):
        """Payslips List"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        # Check if payroll module is installed
        if not self._payroll_installed():
            return request.render('tazweed_employee_portal.portal_payslips_not_available', {
                'page_name': 'payslips',
                'employee': employee,
            })
        
        Payslip = request.env['hr.payslip'].sudo()
        
        domain = [
            ('employee_id', '=', employee.id),
            ('state', '=', 'done'),
        ]
        
        # Year filter
        if year:
            year = int(year)
            domain.append(('date_from', '>=', f'{year}-01-01'))
            domain.append(('date_to', '<=', f'{year}-12-31'))
        
        payslip_count = Payslip.search_count(domain)
        
        pager = portal_pager(
            url='/my/payslips',
            url_args={'year': year},
            total=payslip_count,
            page=page,
            step=12,
        )
        
        payslips = Payslip.search(
            domain,
            order='date_to desc',
            limit=12,
            offset=pager['offset'],
        )
        
        # Get available years
        all_payslips = Payslip.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'done'),
        ])
        years = sorted(set(p.date_to.year for p in all_payslips), reverse=True) if all_payslips else []
        
        values = {
            'page_name': 'payslips',
            'payslips': payslips,
            'pager': pager,
            'employee': employee,
            'years': years,
            'selected_year': year,
        }
        
        return request.render('tazweed_employee_portal.portal_payslips', values)

    @http.route(['/my/payslips/<int:payslip_id>'], type='http', auth='user', website=True)
    def portal_payslip_detail(self, payslip_id, **kw):
        """Payslip Detail"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        if not self._payroll_installed():
            return request.redirect('/my/payslips')
        
        payslip = request.env['hr.payslip'].sudo().browse(payslip_id)
        if not payslip.exists() or payslip.employee_id.id != employee.id:
            return request.redirect('/my/payslips')
        
        # Group lines by category
        lines_by_category = {}
        for line in payslip.line_ids:
            category = line.category_id.name if line.category_id else 'Other'
            if category not in lines_by_category:
                lines_by_category[category] = []
            lines_by_category[category].append(line)
        
        values = {
            'page_name': 'payslip_detail',
            'payslip': payslip,
            'employee': employee,
            'lines_by_category': lines_by_category,
        }
        
        return request.render('tazweed_employee_portal.portal_payslip_detail', values)

    @http.route(['/my/payslips/<int:payslip_id>/download'], type='http', auth='user', website=True)
    def portal_payslip_download(self, payslip_id, **kw):
        """Download Payslip PDF"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        if not self._payroll_installed():
            return request.redirect('/my/payslips')
        
        payslip = request.env['hr.payslip'].sudo().browse(payslip_id)
        if not payslip.exists() or payslip.employee_id.id != employee.id:
            return request.redirect('/my/payslips')
        
        # Generate PDF
        try:
            pdf_content, content_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'hr_payroll.action_report_payslip',
                [payslip.id],
            )
            
            filename = f'payslip_{payslip.number or payslip.id}.pdf'
            
            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ],
            )
        except Exception:
            return request.redirect(f'/my/payslips/{payslip_id}')

    @http.route(['/my/salary-history'], type='http', auth='user', website=True)
    def portal_salary_history(self, **kw):
        """Salary History"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        if not self._payroll_installed():
            return request.render('tazweed_employee_portal.portal_payslips_not_available', {
                'page_name': 'salary_history',
                'employee': employee,
            })
        
        # Get all payslips
        payslips = request.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'done'),
        ], order='date_to desc')
        
        # Prepare chart data
        chart_data = []
        for payslip in payslips[:12]:  # Last 12 months
            net_amount = sum(line.total for line in payslip.line_ids if line.code == 'NET')
            gross_amount = sum(line.total for line in payslip.line_ids if line.code == 'GROSS')
            chart_data.append({
                'month': payslip.date_to.strftime('%b %Y'),
                'net': net_amount,
                'gross': gross_amount,
            })
        
        chart_data.reverse()  # Oldest first
        
        values = {
            'page_name': 'salary_history',
            'employee': employee,
            'payslips': payslips,
            'chart_data': chart_data,
        }
        
        return request.render('tazweed_employee_portal.portal_salary_history', values)

    @http.route(['/my/loans'], type='http', auth='user', website=True)
    def portal_loans(self, **kw):
        """Loans List"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        # Check if loan model exists
        if 'tazweed.payroll.loan' not in request.env:
            return request.render('tazweed_employee_portal.portal_payslips_not_available', {
                'page_name': 'loans',
                'employee': employee,
            })
        
        loans = request.env['tazweed.payroll.loan'].sudo().search([
            ('employee_id', '=', employee.id),
        ], order='request_date desc')
        
        values = {
            'page_name': 'loans',
            'employee': employee,
            'loans': loans,
        }
        
        return request.render('tazweed_employee_portal.portal_loans', values)

    @http.route(['/my/loans/<int:loan_id>'], type='http', auth='user', website=True)
    def portal_loan_detail(self, loan_id, **kw):
        """Loan Detail"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        if 'tazweed.payroll.loan' not in request.env:
            return request.redirect('/my')
        
        loan = request.env['tazweed.payroll.loan'].sudo().browse(loan_id)
        if not loan.exists() or loan.employee_id.id != employee.id:
            return request.redirect('/my/loans')
        
        values = {
            'page_name': 'loan_detail',
            'employee': employee,
            'loan': loan,
        }
        
        return request.render('tazweed_employee_portal.portal_loan_detail', values)

    @http.route(['/my/loans/new'], type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_loan_new(self, **post):
        """Request New Loan"""
        employee = self._get_current_employee()
        if not employee:
            return request.redirect('/my')
        
        if 'tazweed.payroll.loan' not in request.env:
            return request.redirect('/my')
        
        if request.httprequest.method == 'POST':
            try:
                loan_vals = {
                    'employee_id': employee.id,
                    'loan_type': post.get('loan_type'),
                    'amount': float(post.get('amount', 0)),
                    'installments': int(post.get('installments', 1)),
                    'reason': post.get('reason', ''),
                }
                
                loan = request.env['tazweed.payroll.loan'].sudo().create(loan_vals)
                
                return request.redirect(f'/my/loans/{loan.id}')
            except Exception as e:
                values = {
                    'page_name': 'loan_new',
                    'employee': employee,
                    'error': str(e),
                }
                return request.render('tazweed_employee_portal.portal_loan_new', values)
        
        values = {
            'page_name': 'loan_new',
            'employee': employee,
        }
        
        return request.render('tazweed_employee_portal.portal_loan_new', values)
