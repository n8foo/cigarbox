#! /usr/bin/env python

"""Simple API key authentication"""

from functools import wraps
from flask import request, jsonify, current_app

def api_key_required(f):
    """Decorator to require API key authentication for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = None

        # Check for API key in multiple places
        # 1. Authorization header (Bearer token)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            api_key = auth_header.replace('Bearer ', '')

        # 2. X-API-Key header
        if not api_key:
            api_key = request.headers.get('X-API-Key')

        # 3. Query parameter (least secure, but convenient for testing)
        if not api_key:
            api_key = request.args.get('api_key')

        # 4. Form data (for multipart uploads)
        if not api_key and request.form:
            api_key = request.form.get('api_key')

        if not api_key:
            return jsonify({
                'error': 'API key required',
                'message': 'Provide API key via Authorization: Bearer <key>, X-API-Key header, or api_key parameter'
            }), 401

        # Validate API key against config
        expected_key = current_app.config.get('API_KEY')
        if not expected_key:
            return jsonify({'error': 'Server configuration error: API_KEY not set'}), 500

        if api_key != expected_key:
            return jsonify({'error': 'Invalid API key'}), 401

        return f(*args, **kwargs)

    return decorated_function
