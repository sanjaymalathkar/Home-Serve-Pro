"""
JWT callback handlers for HomeServe Pro.
Handles JWT token lifecycle and user lookup.
"""

from flask import jsonify
from app.models.user import User


def user_identity_lookup(user):
    """
    Callback to convert user object to identity for JWT.
    
    Args:
        user: User object or user ID
        
    Returns:
        str: User ID
    """
    if isinstance(user, dict):
        return str(user['_id'])
    return str(user)


def user_lookup_callback(_jwt_header, jwt_data):
    """
    Callback to load user from JWT identity.
    
    Args:
        _jwt_header: JWT header
        jwt_data: JWT payload data
        
    Returns:
        dict: User object or None
    """
    identity = jwt_data['sub']
    return User.find_by_id(identity)


def expired_token_callback(jwt_header, jwt_data):
    """Callback for expired JWT tokens."""
    return jsonify({
        'error': 'Token expired',
        'message': 'The token has expired. Please login again.'
    }), 401


def invalid_token_callback(error):
    """Callback for invalid JWT tokens."""
    return jsonify({
        'error': 'Invalid token',
        'message': 'The token is invalid. Please login again.'
    }), 401


def unauthorized_callback(error):
    """Callback for missing JWT tokens."""
    return jsonify({
        'error': 'Authorization required',
        'message': 'Please provide a valid authentication token.'
    }), 401

