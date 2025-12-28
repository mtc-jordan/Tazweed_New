# -*- coding: utf-8 -*-

from odoo import models, fields, api


class TazweedPortalMixin(models.AbstractModel):
    """Mixin for portal-accessible models"""
    _name = 'tazweed.portal.mixin'
    _description = 'Portal Mixin'

    portal_visible = fields.Boolean(
        string='Visible in Portal',
        default=True,
    )
    portal_editable = fields.Boolean(
        string='Editable in Portal',
        default=False,
    )

    def _get_portal_url(self):
        """Get the portal URL for this record"""
        self.ensure_one()
        return f'/my/{self._name.replace(".", "_")}/{self.id}'

    @api.model
    def _get_portal_domain(self, employee_id):
        """Get domain for portal records"""
        return [('employee_id', '=', employee_id)]


class HrLeavePortal(models.Model):
    """Extend hr.leave for portal access"""
    _inherit = 'hr.leave'

    def _get_portal_url(self):
        """Get portal URL for leave request"""
        self.ensure_one()
        return f'/my/leaves/{self.id}'


class HrAttendancePortal(models.Model):
    """Extend hr.attendance for portal access"""
    _inherit = 'hr.attendance'

    def _get_portal_url(self):
        """Get portal URL for attendance"""
        self.ensure_one()
        return f'/my/attendance/{self.id}'


class HrPayslipPortal(models.Model):
    """Extend hr.payslip for portal access"""
    _inherit = 'hr.payslip'

    portal_visible = fields.Boolean(
        string='Visible in Portal',
        default=True,
    )

    def _get_portal_url(self):
        """Get portal URL for payslip"""
        self.ensure_one()
        return f'/my/payslips/{self.id}'


class EmployeeDocumentPortal(models.Model):
    """Extend tazweed.employee.document for portal access"""
    _inherit = 'tazweed.employee.document'

    portal_visible = fields.Boolean(
        string='Visible in Portal',
        default=True,
    )
    portal_downloadable = fields.Boolean(
        string='Downloadable in Portal',
        default=True,
    )

    def _get_portal_url(self):
        """Get portal URL for document"""
        self.ensure_one()
        return f'/my/documents/{self.id}'
