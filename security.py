#! /usr/bin/env python

"""Authentication and authorization utilities"""

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


# Authorization helpers for web routes

def get_visible_privacy_levels(user):
    """
    Return list of privacy levels this user can see.

    Privacy levels: 0=public, 1=friends, 2=family, 3=private
    Permission levels: 'private', 'family', 'friends', 'public', or None

    Mapping:
    - 'private' permission → sees all [0, 1, 2, 3]
    - 'family' permission → sees [0, 1, 2] (public, friends, family)
    - 'friends' permission → sees [0, 1] (public, friends)
    - 'public' permission → sees [0] (public only)
    - None/unauthenticated → sees [0] (public only)

    Admin role always sees all regardless of permission level.
    """
    if not user or not user.is_authenticated:
        return [0]  # Unauthenticated: public only

    # Admin sees everything
    if user.has_role('admin'):
        return [0, 1, 2, 3]

    # Permission level based access
    permission_map = {
        'private': [0, 1, 2, 3],  # Private viewers see everything
        'family': [0, 1, 2],       # Family viewers see public, friends, family
        'friends': [0, 1],         # Friends viewers see public, friends
        'public': [0],             # Public viewers see public only
    }

    return permission_map.get(user.permission_level, [0])


def can_view_photo(user, photo):
    """
    Check if user can view this specific photo.

    Returns True if photo's privacy level is in user's visible levels.
    Treats NULL privacy as public (0).
    """
    visible_levels = get_visible_privacy_levels(user)
    privacy = photo.privacy if photo.privacy is not None else 0
    return privacy in visible_levels


def can_edit_photo(user, photo):
    """
    Check if user can edit/delete this photo.

    Rules:
    - Admin role: can edit all photos
    - Contributor role: can edit only their own uploads
    - All others: cannot edit
    """
    if not user or not user.is_authenticated:
        return False

    # Admins can edit everything
    if user.has_role('admin'):
        return True

    # Contributors can edit their own uploads
    if user.has_role('contributor'):
        # Check if this photo was uploaded by this user
        if photo.uploaded_by_id and photo.uploaded_by_id == user.id:
            return True

    return False


def can_manage_tags(user):
    """Check if user can create/edit/delete tags"""
    if not user or not user.is_authenticated:
        return False
    return user.has_role('admin') or user.has_role('contributor')


def can_manage_photosets(user):
    """Check if user can create/edit/delete photosets"""
    if not user or not user.is_authenticated:
        return False
    return user.has_role('admin') or user.has_role('contributor')
