# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request


class ESignatureController(http.Controller):
    """Controller for public signature pages."""

    @http.route('/sign/<string:request_token>/<string:signer_token>', type='http', auth='public', website=True)
    def sign_document(self, request_token, signer_token, **kwargs):
        """Public page for signing a document."""
        signature_request = request.env['signature.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)
        
        if not signature_request:
            return request.render('tazweed_esignature.sign_error', {
                'error': 'Invalid or expired signature request.'
            })
        
        signer = signature_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )
        
        if not signer:
            return request.render('tazweed_esignature.sign_error', {
                'error': 'Invalid signer token.'
            })
        
        signer = signer[0]
        
        if signer.state == 'pending':
            signer.action_mark_viewed(
                ip_address=request.httprequest.remote_addr,
                user_agent=request.httprequest.user_agent.string
            )
        
        return request.render('tazweed_esignature.sign_document', {
            'request': signature_request,
            'signer': signer,
        })

    @http.route('/sign/submit', type='json', auth='public', csrf=False)
    def submit_signature(self, request_token, signer_token, signature_data, signature_type='draw', **kwargs):
        """Submit a signature."""
        signature_request = request.env['signature.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)
        
        if not signature_request:
            return {'success': False, 'error': 'Invalid request'}
        
        signer = signature_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )
        
        if not signer:
            return {'success': False, 'error': 'Invalid signer'}
        
        signer = signer[0]
        
        try:
            signer.action_sign(
                signature_data=signature_data,
                signature_type=signature_type,
                ip_address=request.httprequest.remote_addr,
                user_agent=request.httprequest.user_agent.string
            )
            return {'success': True, 'message': 'Signature submitted successfully'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @http.route('/sign/decline', type='json', auth='public', csrf=False)
    def decline_signature(self, request_token, signer_token, reason='', **kwargs):
        """Decline to sign."""
        signature_request = request.env['signature.request'].sudo().search([
            ('access_token', '=', request_token)
        ], limit=1)
        
        if not signature_request:
            return {'success': False, 'error': 'Invalid request'}
        
        signer = signature_request.signer_ids.filtered(
            lambda s: s.access_token == signer_token
        )
        
        if not signer:
            return {'success': False, 'error': 'Invalid signer'}
        
        signer = signer[0]
        
        try:
            signer.action_decline(reason=reason)
            return {'success': True, 'message': 'Signature declined'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
