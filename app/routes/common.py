"""
Common routes for HomeServe Pro.
Shared endpoints accessible by all authenticated users.
"""

from flask import Blueprint, request, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.notification import Notification
from app.models.service import Service
from app.utils.error_handlers import api_error_response, api_success_response
from app.utils.file_upload import save_image, get_file_url
import os

common_bp = Blueprint('common', __name__)


@common_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with DB ping."""
    db_ok = True
    db_error = None
    try:
        from app import mongo
        # Ping the MongoDB server; raises if unreachable
        mongo.db.command('ping')
    except Exception as e:
        db_ok = False
        db_error = str(e)
    return api_success_response({
        'status': 'healthy' if db_ok else 'degraded',
        'service': 'HomeServe Pro API',
        'database': {'ok': db_ok, 'error': db_error}
    })


@common_bp.route('/services', methods=['GET'])
def get_public_services():
    """Get all available services (public endpoint)."""
    try:
        query = request.args.get('q', '')
        pincode = request.args.get('pincode', '')

        if query:
            services = Service.search(query, pincode)
        else:
            services = Service.find_all_active()

        return api_success_response([Service.to_dict(s) for s in services])

    except Exception as e:
        return api_error_response(f'Failed to get services: {str(e)}', 500)



@common_bp.route('/vendors', methods=['GET'])
def get_public_vendors():
    """Get approved, registered vendors (public endpoint).
    Optional query params:
      - service_id: filter by service id
      - service: filter by service name
      - pincode: filter by serviceable pincode
      - availability: 'true' to return only currently available vendors
    """
    try:
        from app.models.vendor import Vendor
        # Resolve filters
        service_id = request.args.get('service_id', '').strip()
        service_name = request.args.get('service', '').strip()
        pincode = request.args.get('pincode', '').strip()
        availability_only = request.args.get('availability', 'false').lower() == 'true'

        # If service_id is provided, resolve to name
        if service_id and not service_name:
            svc = Service.find_by_id(service_id)
            if svc:
                service_name = svc.get('name', '')

        # Build base filters: only approved vendors with linked user
        filters = { 'onboarding_status': 'approved' }
        if availability_only:
            filters['availability'] = True
        if service_name:
            filters['services'] = service_name
        if pincode:
            filters['pincodes'] = pincode

        vendors = Vendor.find_all(filters, skip=0, limit=100)

        # Keep only vendors that have a valid user account
        result = []
        for v in vendors:
            user = None
            try:
                if v.get('user_id'):
                    user = User.find_by_id(str(v['user_id']))
            except Exception:
                user = None
            if not user or user.get('role') != 'vendor':
                continue
            v_dict = Vendor.to_dict(v)
            # Prefer vendor.name; fallback to user.name
            if not v_dict.get('name'):
                v_dict['name'] = user.get('name') or user.get('email')
            # Expose minimal public fields
            public = {
                'id': v_dict['id'],
                'name': v_dict.get('name'),
                'services': v_dict.get('services', []),
                'pincodes': v_dict.get('pincodes', []),
                'availability': v_dict.get('availability', False),
                'ratings': v_dict.get('ratings', 0.0),
                'total_ratings': v_dict.get('total_ratings', 0),
                'completed_jobs': v_dict.get('completed_jobs', 0),
                'profile_image': v_dict.get('profile_image')
            }
            result.append(public)

        return api_success_response(result)
    except Exception as e:
        return api_error_response(f'Failed to get vendors: {str(e)}', 500)

@common_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile."""
    try:
        user_id = get_jwt_identity()
        user = User.find_by_id(user_id)

        if not user:
            return api_error_response('User not found', 404)

        return api_success_response(User.to_dict(user))

    except Exception as e:
        return api_error_response(f'Failed to get profile: {str(e)}', 500)


@common_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user profile.

    Request Body:
        - name: User name
        - phone: Phone number
        - address: Address
        - pincode: Pincode
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()

        # Remove fields that shouldn't be updated via this endpoint
        data.pop('email', None)
        data.pop('password', None)
        data.pop('role', None)
        data.pop('verified', None)
        data.pop('active', None)

        User.update(user_id, data)

        updated_user = User.find_by_id(user_id)
        return api_success_response(User.to_dict(updated_user), 'Profile updated successfully')

    except Exception as e:
        return api_error_response(f'Failed to update profile: {str(e)}', 500)


@common_bp.route('/profile/photo', methods=['POST'])
@jwt_required()
def upload_profile_photo():
    """Upload profile photo."""
    try:
        user_id = get_jwt_identity()

        if 'photo' not in request.files:
            return api_error_response('No photo file provided', 400)

        photo = request.files['photo']
        photo_path = save_image(photo, subfolder='profiles')

        if not photo_path:
            return api_error_response('Failed to save photo', 500)

        photo_url = get_file_url(photo_path)
        User.update(user_id, {'profile_image': photo_url})

        return api_success_response({
            'photo_url': photo_url
        }, 'Profile photo uploaded successfully')

    except Exception as e:
        return api_error_response(f'Failed to upload photo: {str(e)}', 500)


@common_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get user notifications."""
    try:
        user_id = get_jwt_identity()
        unread_only = request.args.get('unread', 'false').lower() == 'true'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        skip = (page - 1) * limit

        notifications = Notification.find_by_user(user_id, unread_only, skip, limit)
        unread_count = Notification.count_unread(user_id)

        return api_success_response({
            'notifications': [Notification.to_dict(n) for n in notifications],
            'unread_count': unread_count
        })

    except Exception as e:
        return api_error_response(f'Failed to get notifications: {str(e)}', 500)


@common_bp.route('/notifications/<notification_id>/read', methods=['POST'])
@jwt_required()
def mark_notification_read(notification_id):
    """Mark notification as read."""
    try:
        Notification.mark_as_read(notification_id)
        return api_success_response(message='Notification marked as read')

    except Exception as e:
        return api_error_response(f'Failed to mark notification: {str(e)}', 500)


@common_bp.route('/notifications/read-all', methods=['POST'])
@jwt_required()
def mark_all_notifications_read():
    """Mark all notifications as read."""
    try:
        user_id = get_jwt_identity()
        count = Notification.mark_all_as_read(user_id)

        return api_success_response({
            'marked_count': count
        }, f'{count} notifications marked as read')

    except Exception as e:
        return api_error_response(f'Failed to mark notifications: {str(e)}', 500)


@common_bp.route('/uploads/<path:filename>', methods=['GET'])
def serve_upload(filename):
    """Serve uploaded files."""
    try:
        upload_folder = current_app.config['UPLOAD_FOLDER']
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        return api_error_response('File not found', 404)

