"""
Custom decorators for HomeServe Pro.
Includes role-based access control and other middleware.
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models.user import User


def role_required(*allowed_roles):
    """
    Decorator to restrict access based on user roles.
    
    Usage:
        @role_required('customer', 'vendor')
        def some_route():
            pass
    
    Args:
        *allowed_roles: Variable number of allowed role strings
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Verify JWT token
            verify_jwt_in_request()
            
            # Get current user
            user_id = get_jwt_identity()
            user = User.find_by_id(user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if not user.get('active'):
                return jsonify({'error': 'Account is inactive'}), 403
            
            # Check if user role is in allowed roles
            user_role = user.get('role')
            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'Access denied',
                    'message': f'This endpoint requires one of the following roles: {", ".join(allowed_roles)}'
                }), 403
            
            # Pass user to the route function
            return fn(user=user, *args, **kwargs)
        
        return wrapper
    return decorator


def customer_required(fn):
    """Decorator to restrict access to customers only."""
    return role_required(User.ROLE_CUSTOMER)(fn)


def vendor_required(fn):
    """Decorator to restrict access to vendors only."""
    return role_required(User.ROLE_VENDOR)(fn)


def onboard_manager_required(fn):
    """Decorator to restrict access to onboard managers only."""
    return role_required(User.ROLE_ONBOARD_MANAGER, User.ROLE_SUPER_ADMIN)(fn)


def ops_manager_required(fn):
    """Decorator to restrict access to ops managers only."""
    return role_required(User.ROLE_OPS_MANAGER, User.ROLE_SUPER_ADMIN)(fn)


def super_admin_required(fn):
    """Decorator to restrict access to super admins only."""
    return role_required(User.ROLE_SUPER_ADMIN)(fn)


def admin_required(fn):
    """Decorator to restrict access to any admin role."""
    return role_required(
        User.ROLE_ONBOARD_MANAGER,
        User.ROLE_OPS_MANAGER,
        User.ROLE_SUPER_ADMIN
    )(fn)

