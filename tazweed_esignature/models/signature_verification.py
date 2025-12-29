# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import base64
import hashlib
import hmac
import json
from datetime import datetime


class SignatureVerification(models.Model):
    """Signature Verification - Verify document and signature authenticity"""
    _name = 'signature.verification'
    _description = 'Signature Verification'
    _order = 'verification_date desc'

    name = fields.Char(
        string='Verification Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    # Document Being Verified
    document_file = fields.Binary(
        string='Document to Verify',
        attachment=True,
        required=True
    )
    document_filename = fields.Char(string='Document Filename')
    document_hash = fields.Char(
        string='Document Hash',
        compute='_compute_document_hash',
        store=True
    )
    
    # Verification Type
    verification_type = fields.Selection([
        ('document', 'Document Integrity'),
        ('signature', 'Signature Authenticity'),
        ('certificate', 'Certificate Validation'),
        ('full', 'Full Verification'),
    ], string='Verification Type', required=True, default='full')
    
    # Reference Information
    signature_request_id = fields.Many2one(
        'signature.request',
        string='Signature Request',
        help='Original signature request to verify against'
    )
    certificate_id = fields.Many2one(
        'signature.certificate',
        string='Certificate',
        help='Certificate to verify'
    )
    
    # Verification Results
    verification_result = fields.Selection([
        ('pending', 'Pending'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('partial', 'Partially Valid'),
        ('error', 'Error'),
    ], string='Verification Result', default='pending')
    
    # Detailed Results
    document_integrity = fields.Selection([
        ('pending', 'Pending'),
        ('valid', 'Valid - Document Unchanged'),
        ('invalid', 'Invalid - Document Modified'),
        ('unknown', 'Unknown - No Reference'),
    ], string='Document Integrity', default='pending')
    
    signature_validity = fields.Selection([
        ('pending', 'Pending'),
        ('valid', 'Valid'),
        ('invalid', 'Invalid'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
    ], string='Signature Validity', default='pending')
    
    certificate_validity = fields.Selection([
        ('pending', 'Pending'),
        ('valid', 'Valid'),
        ('expired', 'Expired'),
        ('revoked', 'Revoked'),
        ('not_found', 'Not Found'),
    ], string='Certificate Validity', default='pending')
    
    # Verification Details
    verification_details = fields.Text(
        string='Verification Details',
        readonly=True
    )
    verification_log = fields.Text(
        string='Verification Log',
        readonly=True
    )
    
    # Signer Information (from verification)
    signer_name = fields.Char(string='Signer Name', readonly=True)
    signer_email = fields.Char(string='Signer Email', readonly=True)
    signing_date = fields.Datetime(string='Signing Date', readonly=True)
    signing_ip = fields.Char(string='Signing IP', readonly=True)
    
    # Timestamps
    verification_date = fields.Datetime(
        string='Verification Date',
        default=fields.Datetime.now,
        readonly=True
    )
    
    # Verified By
    verified_by = fields.Many2one(
        'res.users',
        string='Verified By',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('signature.verification') or _('New')
        return super().create(vals_list)

    @api.depends('document_file')
    def _compute_document_hash(self):
        """Compute SHA-256 hash of the document"""
        for record in self:
            if record.document_file:
                doc_bytes = base64.b64decode(record.document_file)
                record.document_hash = hashlib.sha256(doc_bytes).hexdigest()
            else:
                record.document_hash = False

    def action_verify(self):
        """Perform verification"""
        self.ensure_one()
        
        log_entries = []
        details = {}
        
        try:
            # Step 1: Document Integrity Check
            if self.verification_type in ('document', 'full'):
                log_entries.append(f"[{datetime.now()}] Starting document integrity check...")
                integrity_result = self._verify_document_integrity()
                self.document_integrity = integrity_result['status']
                details['document_integrity'] = integrity_result
                log_entries.append(f"[{datetime.now()}] Document integrity: {integrity_result['status']}")
            
            # Step 2: Signature Validity Check
            if self.verification_type in ('signature', 'full'):
                log_entries.append(f"[{datetime.now()}] Starting signature validity check...")
                signature_result = self._verify_signature()
                self.signature_validity = signature_result['status']
                details['signature_validity'] = signature_result
                log_entries.append(f"[{datetime.now()}] Signature validity: {signature_result['status']}")
                
                # Extract signer info
                if signature_result.get('signer_info'):
                    self.signer_name = signature_result['signer_info'].get('name')
                    self.signer_email = signature_result['signer_info'].get('email')
                    self.signing_date = signature_result['signer_info'].get('signing_date')
                    self.signing_ip = signature_result['signer_info'].get('ip_address')
            
            # Step 3: Certificate Validation
            if self.verification_type in ('certificate', 'full'):
                log_entries.append(f"[{datetime.now()}] Starting certificate validation...")
                cert_result = self._verify_certificate()
                self.certificate_validity = cert_result['status']
                details['certificate_validity'] = cert_result
                log_entries.append(f"[{datetime.now()}] Certificate validity: {cert_result['status']}")
            
            # Determine overall result
            self._determine_overall_result()
            log_entries.append(f"[{datetime.now()}] Verification complete: {self.verification_result}")
            
        except Exception as e:
            self.verification_result = 'error'
            log_entries.append(f"[{datetime.now()}] ERROR: {str(e)}")
            details['error'] = str(e)
        
        self.verification_details = json.dumps(details, indent=2, default=str)
        self.verification_log = '\n'.join(log_entries)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Verification Complete'),
                'message': _('Result: %s') % dict(self._fields['verification_result'].selection).get(self.verification_result),
                'type': 'success' if self.verification_result == 'valid' else 'warning',
            }
        }

    def _verify_document_integrity(self):
        """Verify document has not been modified"""
        result = {
            'status': 'unknown',
            'message': '',
            'original_hash': None,
            'current_hash': self.document_hash,
        }
        
        if self.signature_request_id:
            original_hash = self.signature_request_id.document_hash
            result['original_hash'] = original_hash
            
            if original_hash == self.document_hash:
                result['status'] = 'valid'
                result['message'] = 'Document matches the original signed document.'
            else:
                result['status'] = 'invalid'
                result['message'] = 'Document has been modified since signing.'
        else:
            result['status'] = 'unknown'
            result['message'] = 'No reference document found for comparison.'
        
        return result

    def _verify_signature(self):
        """Verify signature authenticity"""
        result = {
            'status': 'pending',
            'message': '',
            'signer_info': None,
        }
        
        if not self.signature_request_id:
            result['status'] = 'invalid'
            result['message'] = 'No signature request found.'
            return result
        
        request = self.signature_request_id
        
        # Check if request is signed
        if request.state != 'signed':
            result['status'] = 'invalid'
            result['message'] = f'Signature request is not completed. Status: {request.state}'
            return result
        
        # Get signer information
        signed_signers = request.signer_ids.filtered(lambda s: s.state == 'signed')
        if signed_signers:
            signer = signed_signers[0]
            result['signer_info'] = {
                'name': signer.name,
                'email': signer.email,
                'signing_date': signer.signed_date,
                'ip_address': signer.signing_ip,
            }
            result['status'] = 'valid'
            result['message'] = 'Signature is valid and verified.'
        else:
            result['status'] = 'invalid'
            result['message'] = 'No valid signatures found.'
        
        return result

    def _verify_certificate(self):
        """Verify certificate validity"""
        result = {
            'status': 'pending',
            'message': '',
            'certificate_info': None,
        }
        
        certificate = self.certificate_id or (
            self.signature_request_id.certificate_id if self.signature_request_id else None
        )
        
        if not certificate:
            result['status'] = 'not_found'
            result['message'] = 'No certificate found.'
            return result
        
        result['certificate_info'] = {
            'reference': certificate.name,
            'issued_date': certificate.issue_date,
            'expiry_date': certificate.expiry_date,
        }
        
        # Check expiry
        if certificate.expiry_date and certificate.expiry_date < fields.Date.today():
            result['status'] = 'expired'
            result['message'] = 'Certificate has expired.'
            return result
        
        # Check revocation
        if certificate.state == 'revoked':
            result['status'] = 'revoked'
            result['message'] = 'Certificate has been revoked.'
            return result
        
        result['status'] = 'valid'
        result['message'] = 'Certificate is valid.'
        return result

    def _determine_overall_result(self):
        """Determine overall verification result"""
        results = []
        
        if self.verification_type in ('document', 'full'):
            results.append(self.document_integrity)
        if self.verification_type in ('signature', 'full'):
            results.append(self.signature_validity)
        if self.verification_type in ('certificate', 'full'):
            results.append(self.certificate_validity)
        
        if all(r == 'valid' for r in results):
            self.verification_result = 'valid'
        elif any(r in ('invalid', 'revoked') for r in results):
            self.verification_result = 'invalid'
        elif any(r == 'expired' for r in results):
            self.verification_result = 'partial'
        elif any(r in ('unknown', 'not_found') for r in results):
            self.verification_result = 'partial'
        else:
            self.verification_result = 'pending'


class SignatureVerificationReport(models.Model):
    """Signature Verification Report - Generate verification reports"""
    _name = 'signature.verification.report'
    _description = 'Signature Verification Report'
    _order = 'create_date desc'

    name = fields.Char(
        string='Report Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    # Verification Reference
    verification_id = fields.Many2one(
        'signature.verification',
        string='Verification',
        required=True,
        ondelete='cascade'
    )
    
    # Report Content
    report_type = fields.Selection([
        ('summary', 'Summary Report'),
        ('detailed', 'Detailed Report'),
        ('audit', 'Audit Report'),
    ], string='Report Type', required=True, default='summary')
    
    report_content = fields.Html(string='Report Content', readonly=True)
    report_pdf = fields.Binary(string='Report PDF', readonly=True)
    report_filename = fields.Char(string='Report Filename', readonly=True)
    
    # Timestamps
    generated_date = fields.Datetime(
        string='Generated Date',
        default=fields.Datetime.now,
        readonly=True
    )
    
    # Generated By
    generated_by = fields.Many2one(
        'res.users',
        string='Generated By',
        default=lambda self: self.env.user,
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence and report"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('signature.verification.report') or _('New')
        records = super().create(vals_list)
        for record in records:
            record._generate_report()
        return records

    def _generate_report(self):
        """Generate the verification report"""
        self.ensure_one()
        verification = self.verification_id
        
        if self.report_type == 'summary':
            content = self._generate_summary_report(verification)
        elif self.report_type == 'detailed':
            content = self._generate_detailed_report(verification)
        else:
            content = self._generate_audit_report(verification)
        
        self.report_content = content

    def _generate_summary_report(self, verification):
        """Generate summary verification report"""
        return f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h1 style="color: #333;">Signature Verification Report</h1>
            <hr/>
            
            <h2>Summary</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Reference:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{verification.name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Verification Date:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{verification.verification_date}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Overall Result:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd; color: {'green' if verification.verification_result == 'valid' else 'red'};">
                        <strong>{verification.verification_result.upper()}</strong>
                    </td>
                </tr>
            </table>
            
            <h2>Verification Details</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Document Integrity:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{verification.document_integrity}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Signature Validity:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{verification.signature_validity}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Certificate Validity:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{verification.certificate_validity}</td>
                </tr>
            </table>
            
            {f'''
            <h2>Signer Information</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Name:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{verification.signer_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Email:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{verification.signer_email}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;"><strong>Signing Date:</strong></td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{verification.signing_date}</td>
                </tr>
            </table>
            ''' if verification.signer_name else ''}
            
            <p style="margin-top: 30px; font-size: 12px; color: #666;">
                This report was generated on {fields.Datetime.now()} by {self.env.user.name}.
            </p>
        </div>
        """

    def _generate_detailed_report(self, verification):
        """Generate detailed verification report"""
        summary = self._generate_summary_report(verification)
        
        details_section = f"""
        <h2>Technical Details</h2>
        <pre style="background: #f5f5f5; padding: 15px; overflow-x: auto;">
{verification.verification_details or 'No details available'}
        </pre>
        
        <h2>Verification Log</h2>
        <pre style="background: #f5f5f5; padding: 15px; overflow-x: auto;">
{verification.verification_log or 'No log available'}
        </pre>
        """
        
        return summary.replace('</div>', details_section + '</div>')

    def _generate_audit_report(self, verification):
        """Generate audit verification report"""
        detailed = self._generate_detailed_report(verification)
        
        audit_section = f"""
        <h2>Audit Trail</h2>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background: #f0f0f0;">
                <th style="padding: 8px; border: 1px solid #ddd;">Timestamp</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Action</th>
                <th style="padding: 8px; border: 1px solid #ddd;">User</th>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{verification.verification_date}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">Verification Performed</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{verification.verified_by.name}</td>
            </tr>
        </table>
        """
        
        return detailed.replace('</div>', audit_section + '</div>')


class SignatureQRCode(models.Model):
    """Signature QR Code - Generate QR codes for document verification"""
    _name = 'signature.qr.code'
    _description = 'Signature QR Code'

    name = fields.Char(string='QR Code Reference', required=True)
    
    # Related Request
    signature_request_id = fields.Many2one(
        'signature.request',
        string='Signature Request',
        required=True,
        ondelete='cascade'
    )
    
    # QR Code Data
    qr_code_data = fields.Text(
        string='QR Code Data',
        readonly=True
    )
    qr_code_image = fields.Binary(
        string='QR Code Image',
        readonly=True
    )
    
    # Verification URL
    verification_url = fields.Char(
        string='Verification URL',
        compute='_compute_verification_url'
    )
    
    # Security
    verification_token = fields.Char(
        string='Verification Token',
        readonly=True
    )
    
    # Timestamps
    generated_date = fields.Datetime(
        string='Generated Date',
        default=fields.Datetime.now,
        readonly=True
    )

    @api.depends('verification_token')
    def _compute_verification_url(self):
        """Compute the verification URL"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            if record.verification_token:
                record.verification_url = f"{base_url}/signature/verify/{record.verification_token}"
            else:
                record.verification_url = False

    def generate_qr_code(self):
        """Generate QR code for the signature request"""
        self.ensure_one()
        import secrets
        
        # Generate verification token
        self.verification_token = secrets.token_urlsafe(32)
        
        # Create QR code data
        qr_data = {
            'type': 'signature_verification',
            'request_id': self.signature_request_id.id,
            'request_ref': self.signature_request_id.name,
            'token': self.verification_token,
            'document_hash': self.signature_request_id.document_hash,
            'signed_date': str(self.signature_request_id.completed_date) if self.signature_request_id.completed_date else None,
        }
        
        self.qr_code_data = json.dumps(qr_data)
        
        # Generate QR code image (would use qrcode library in production)
        # For now, just store the data
        
        return True
