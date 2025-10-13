"""
Authentication routes for HomeServe Pro.
Handles user registration, login, and token management.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from app.models.user import User
from app.models.vendor import Vendor
from app.models.audit_log import AuditLog
from app.utils.error_handlers import api_error_response, api_success_response
from app import limiter

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per hour")
def register():
    """
    Register a new user.
    
    Request Body:
        - email: User email
        - password: User password
        - name: User full name
        - phone: Phone number
        - role: User role (customer/vendor)
        - pincode: User pincode
        - address: Optional address
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'name', 'phone', 'role']
        for field in required_fields:
            if field not in data:
                return api_error_response(f'Missing required field: {field}', 400)
        
        # Validate role
        valid_roles = [User.ROLE_CUSTOMER, User.ROLE_VENDOR]
        if data['role'] not in valid_roles:
            return api_error_response(
                f'Invalid role. Must be one of: {", ".join(valid_roles)}',
                400
            )
        
        # Check if user already exists
        if User.find_by_email(data['email']):
            return api_error_response('Email already registered', 400)
        
        if User.find_by_phone(data['phone']):
            return api_error_response('Phone number already registered', 400)
        
        # Normalize email
        data['email'] = data['email'].lower()
        
        # Create user
        user_id = User.create(data)
        
        # If vendor, create vendor profile with pending_verification status
        if data['role'] == User.ROLE_VENDOR:
            vendor_data = {
                'user_id': user_id,
                'name': data['name'],
                'phone': data.get('phone'),
                'email': data.get('email'),
                'services': data.get('services', []),
                'pincodes': [data.get('pincode')] if data.get('pincode') else [],
                'onboarding_status': Vendor.STATUS_PENDING_VERIFICATION,
                'is_approved': False,
                'documents_verified': False,
                'payouts_enabled': False
            }
            Vendor.create(vendor_data)
        
        # Log registration
        AuditLog.log(
            action=AuditLog.ACTION_CREATE,
            entity_type='user',
            entity_id=user_id,
            user_id=user_id,
            details={'role': data['role']},
            ip_address=request.remote_addr
        )
        
        # Create tokens
        access_token = create_access_token(identity=user_id)
        refresh_token = create_refresh_token(identity=user_id)
        
        return api_success_response({
            'user_id': user_id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'role': data['role']
        }, 'Registration successful', 201)
        
    except Exception as e:
        return api_error_response(f'Registration failed: {str(e)}', 500)


@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """
    Login user and return JWT tokens.
    
    Request Body:
        - email: User email
        - password: User password
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('email') or not data.get('password'):
            return api_error_response('Email and password are required', 400)
        
        # Find user
        user = User.find_by_email(data['email'].lower())
        if not user:
            return api_error_response('Invalid email or password', 401)
        
        # Check if account is active
        if not user.get('active', True):
            return api_error_response('Account is inactive', 403)
        
        # Verify password
        if not User.verify_password(user, data['password']):
            return api_error_response('Invalid email or password', 401)
        
        # Create tokens
        user_id = str(user['_id'])
        access_token = create_access_token(identity=user_id)
        refresh_token = create_refresh_token(identity=user_id)
        
        # Log login
        AuditLog.log(
            action=AuditLog.ACTION_LOGIN,
            entity_type='user',
            entity_id=user_id,
            user_id=user_id,
            ip_address=request.remote_addr
        )
        
        return api_success_response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': User.to_dict(user)
        }, 'Login successful')
        
    except Exception as e:
        return api_error_response(f'Login failed: {str(e)}', 500)


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token using refresh token."""
    try:
        user_id = get_jwt_identity()
        access_token = create_access_token(identity=user_id)
        
        return api_success_response({
            'access_token': access_token
        }, 'Token refreshed successfully')
        
    except Exception as e:
        return api_error_response(f'Token refresh failed: {str(e)}', 500)


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information."""
    try:
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)
        
        if not user:
            return api_error_response('User not found', 404)
        
        return api_success_response(User.to_dict(user))
        
    except Exception as e:
        return api_error_response(f'Failed to get user: {str(e)}', 500)


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout user.
    Note: In a production app, you would add the token to a blocklist.
    """
    try:
        user_id = get_jwt_identity()
        
        # Log logout
        AuditLog.log(
            action=AuditLog.ACTION_LOGOUT,
            entity_type='user',
            entity_id=user_id,
            user_id=user_id,
            ip_address=request.remote_addr
        )
        
        return api_success_response(message='Logout successful')
        
    except Exception as e:
        return api_error_response(f'Logout failed: {str(e)}', 500)


@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """
    Change user password.
    
    Request Body:
        - current_password: Current password
        - new_password: New password
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('current_password') or not data.get('new_password'):
            return api_error_response('Current and new passwords are required', 400)
        
        # Get user
        user = User.find_by_id(user_id)
        if not user:
            return api_error_response('User not found', 404)
        
        # Verify current password
        if not User.verify_password(user, data['current_password']):
            return api_error_response('Current password is incorrect', 401)
        
        # Update password
        User.update(user_id, {'password': data['new_password']})
        
        # Log password change
        AuditLog.log(
            action=AuditLog.ACTION_UPDATE,
            entity_type='user',
            entity_id=user_id,
            user_id=user_id,
            details={'action': 'password_change'},
            ip_address=request.remote_addr
        )
        
        return api_success_response(message='Password changed successfully')
        
    except Exception as e:
        return api_error_response(f'Password change failed: {str(e)}', 500)

